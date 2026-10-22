#!/usr/bin/env python3
"""Build the Astro MJCF from its canonical URDF using MuJoCo and NumPy.

Run with .venv/bin/python scripts/build-astro-mjcf.py from any directory.
Capsules are recognized by same-link endpoint geometry, not naming alone.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import math
import tempfile
import argparse
import xml.etree.ElementTree as ET
import mujoco
import numpy as np

BUNDLE = Path(__file__).resolve().parents[1] / 'robots/astro_p2_29dof'
SOURCE = BUNDLE / 'astro_p2_29dof.urdf'
OUTPUT = BUNDLE / 'astro_p2_29dof.xml'

def vector(value):
    return np.fromstring(value, sep=' ')

def fmt(values):
    return ' '.join(f'{v:.12g}' for v in values)

def rotation(rpy):
    r, p, y = rpy
    cr,sr,cp,sp,cy,sy = math.cos(r),math.sin(r),math.cos(p),math.sin(p),math.cos(y),math.sin(y)
    return np.array([[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr],
                     [sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr],[-sp,cp*sr,cp*cr]])

def origin(node):
    o = node.find('origin')
    return (vector(o.get('xyz','0 0 0')), rotation(vector(o.get('rpy','0 0 0')))) if o is not None else (np.zeros(3),np.eye(3))

def main(bundle=BUNDLE, catalog_paths=False):
    bundle = Path(bundle).resolve()
    source = bundle / (bundle.name + '.urdf')
    output = bundle / (bundle.name + '.xml')
    urdf = ET.parse(source).getroot()
    imported = deepcopy(urdf)
    for mesh in imported.findall('.//mesh'):
        mesh.set('filename',str(bundle / mesh.get('filename')))
    compiler = imported.find('mujoco/compiler')
    compiler.attrib.clear()
    compiler.attrib.update(discardvisual='false',fusestatic='false',strippath='false')
    ET.SubElement(imported,'link',name='world')
    joint=ET.SubElement(imported,'joint',name='floating_base',type='floating')
    ET.SubElement(joint,'parent',link='world'); ET.SubElement(joint,'child',link='pelvis')
    baseline=mujoco.MjModel.from_xml_string(ET.tostring(imported,encoding='unicode'))
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'import.xml'
        mujoco.mj_saveLastXML(str(path),baseline)
        root=ET.parse(path).getroot()
    root.insert(0,ET.Comment(f' Generated from {source.name} by scripts/build-astro-mjcf.py. Visuals: group 1; primitive collisions: group 3. '))
    root.find('compiler').attrib.update(inertiafromgeom='false',fusestatic='false',discardvisual='false')
    if catalog_paths:
        root.find('compiler').set('meshdir','meshes')
    for mesh in root.findall('asset/mesh'):
        mesh.set('file',('' if catalog_paths else 'meshes/')+Path(mesh.get('file')).name)
    bodies={b.get('name'):b for b in root.findall('.//body')}
    # mj_saveLastXML rounds values. Restore high-precision vendor limits when
    # rounding exceeds the existing conversion tolerance (baseline unchanged).
    native_joints={j.get('name'):j for j in root.findall('.//joint')}
    for joint in urdf.findall("joint[@type='revolute']"):
        limit=joint.find('limit')
        bounds=np.array([float(limit.get('lower')),float(limit.get('upper'))])
        native=native_joints[joint.get('name')]
        if np.max(abs(vector(native.get('range'))-bounds))>1e-6:
            native.set('range',fmt(bounds))
    merged=[]
    for link in urdf.findall('link'):
        body=bodies[link.get('name')]
        # Do not infer inertia for fixed, geometry-only frames.
        for inertia in list(body.findall('inertial')):body.remove(inertia)
        source_inertia=link.find('inertial')
        if source_inertia is not None:
            pos,rot=origin(source_inertia); a=source_inertia.find('inertia').attrib
            I=np.array([[float(a['ixx']),float(a['ixy']),float(a['ixz'])],
                        [float(a['ixy']),float(a['iyy']),float(a['iyz'])],
                        [float(a['ixz']),float(a['iyz']),float(a['izz'])]])
            I=rot@I@rot.T
            body.insert(0,ET.Element('inertial',pos=fmt(pos),mass=source_inertia.find('mass').get('value'),fullinertia=fmt([I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]])))
        collisions=link.findall('collision')
        geoms={g.get('name'):g for g in body.findall('geom')}
        used=set()
        for collision in collisions:
            cylinder=collision.find('geometry/cylinder')
            if cylinder is None:continue
            pos,rot=origin(collision); radius=float(cylinder.get('radius')); length=float(cylinder.get('length'))
            ends=[pos-rot[:,2]*length/2,pos+rot[:,2]*length/2]
            caps=[]
            for end in ends:
                matches=[c for c in collisions if c.get('name') not in used and c.find('geometry/sphere') is not None
                         and abs(float(c.find('geometry/sphere').get('radius'))-radius)<1e-10
                         and np.linalg.norm(origin(c)[0]-end)<1e-8]
                if len(matches)!=1:break
                caps.append(matches[0])
            if len(caps)!=2 or caps[0] is caps[1]:continue
            geom=geoms[collision.get('name')]
            for key in ('pos','quat','euler','axisangle','xyaxes','zaxis'):geom.attrib.pop(key,None)
            geom.set('type','capsule');geom.set('size',fmt([radius]));geom.set('fromto',fmt(np.concatenate(ends)))
            name=collision.get('name').replace('_cylinder_collision_1','_capsule_collision').replace('_support_cylinder','_support_capsule')
            geom.set('name',name)
            for cap in caps:
                body.remove(geoms[cap.get('name')]);used.add(cap.get('name'))
            merged.append({'body':link.get('name'),'capsule':name,'source':[collision.get('name')]+[c.get('name') for c in caps],'radius':radius,'fromto':np.concatenate(ends).tolist()})
        for geom in body.findall('geom'):
            visual=geom.get('contype')=='0' and geom.get('conaffinity')=='0'
            geom.set('group','1' if visual else '3')
            if not visual:
                assert geom.get('type','sphere') in ('capsule','sphere','cylinder','box')
                geom.set('rgba','0.1 0.65 0.95 0.65')
    ET.indent(root,space='  ')
    output.write_text(ET.tostring(root,encoding='unicode')+'\n')
    model=mujoco.MjModel.from_xml_path(str(output))
    hinge_count=len(urdf.findall("joint[@type='revolute']"))
    assert (model.nq,model.nv)==(hinge_count+7,hinge_count+6)
    expected_mass=sum(float(i.find('mass').get('value')) for i in urdf.findall('link/inertial'))
    assert abs(model.body_mass.sum()-expected_mass)<1e-8
    for side in ('left','right'):
        assert model.body(side+'_foot_link').mass[0]==0
        assert len(bodies[side+'_foot_link'].findall('geom'))==11
    # Match all original named body frames and hinge limits after several joint configurations.
    max_error=0.0
    for fraction in (0.0,0.15,-0.15):
        d0=mujoco.MjData(baseline); d1=mujoco.MjData(model)
        for j in urdf.findall("joint[@type='revolute']"):
            j0=baseline.joint(j.get('name'));j1=model.joint(j.get('name'))
            np.testing.assert_allclose(j0.range,j1.range,atol=1e-6)
            q=float(np.clip(fraction,float(j.find('limit').get('lower')),float(j.find('limit').get('upper'))))
            d0.qpos[j0.qposadr[0]]=q;d1.qpos[j1.qposadr[0]]=q
        mujoco.mj_forward(baseline,d0);mujoco.mj_forward(model,d1)
        for link in urdf.findall('link'):
            name=link.get('name');a=baseline.body(name).id;b=model.body(name).id
            error=max(np.max(abs(d0.xpos[a]-d1.xpos[b])),np.max(abs(d0.xmat[a]-d1.xmat[b])))
            max_error=max(max_error,float(error));assert error<1e-5,(name,error)
    counts={}
    for geom in root.findall('.//geom'):
        if geom.get('group')=='3':counts[geom.get('type','sphere')]=counts.get(geom.get('type','sphere'),0)+1
    report={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'mjcf_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'mujoco_version':mujoco.__version__,'collision_counts':counts,'capsule_assemblies_converted':len(merged),'mass_kg':expected_mass,'max_body_pose_error':max_error,'nq':model.nq,'nv':model.nv,'capsules':merged}
    (bundle/'mjcf-conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='capsules'},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,default=BUNDLE,help='Astro-derived bundle with a same-named URDF')
    parser.add_argument('--catalog-paths',action='store_true',help='Use compiler meshdir with bare mesh filenames for catalog discovery')
    args=parser.parse_args()
    main(args.bundle,args.catalog_paths)
