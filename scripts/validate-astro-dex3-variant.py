#!/usr/bin/env python3
"""Check sample hand assembly provenance, body preservation and URDF/MJCF FK."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import mujoco
import numpy as np
from menagerie_x.assets import get_variant, validate_assets
from menagerie_x.assets.editions import list_mjcf_editions

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'astro_p2_29dof'
BUNDLE=ROOT/'astro_p2_43dof_dex3_1'
NAME=BUNDLE.name

def canonical(node):
    node=deepcopy(node)
    for element in node.iter():
        element.text=element.tail=None
    return ET.tostring(node)

def load_urdf(root,bundle):
    root=deepcopy(root)
    for mesh in root.findall('.//mesh'):
        mesh.set('filename',str(bundle/mesh.get('filename')))
    compiler=root.find('mujoco/compiler')
    compiler.attrib.clear()
    compiler.attrib.update(discardvisual='false',fusestatic='false',strippath='false',inertiafromgeom='false')
    ET.SubElement(root,'link',name='world')
    j=ET.SubElement(root,'joint',name='floating_base',type='floating')
    ET.SubElement(j,'parent',link='world');ET.SubElement(j,'child',link='pelvis')
    return mujoco.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'))

def main():
    source=ET.parse(BUNDLE/(NAME+'.urdf')).getroot()
    base=ET.parse(BASE/'astro_p2_29dof.urdf').getroot()
    provenance=json.loads((BUNDLE/'SOURCE.json').read_text())
    assert hashlib.sha256((BASE/'astro_p2_29dof.urdf').read_bytes()).hexdigest()==provenance['base_urdf_sha256']
    preserved=0
    for node in base:
        if node.tag not in ('link','joint'):continue
        other=source.find(f"{node.tag}[@name='{node.get('name')}']")
        assert other is not None
        if node.get('name') in ('left_hand_link','right_hand_link'):
            assert len(other)==0
        else:
            assert canonical(node)==canonical(other),node.get('name')
            preserved+=1
    for filename, expected in provenance['vendor_files_sha256'].items():
        assert hashlib.sha256((BUNDLE/filename).read_bytes()).hexdigest()==expected,filename
    for mesh in source.findall('.//mesh'):
        assert (BUNDLE/mesh.get('filename')).is_file()
    for mesh in base.findall('.//mesh'):
        filename=mesh.get('filename')
        assert (BASE/filename).read_bytes()==(BUNDLE/filename).read_bytes(),filename
    for suffix in ('l','r'):
        vendor=ET.parse(BUNDLE/'upstream'/f'dex3_1_{suffix}.urdf').getroot()
        for joint in vendor.findall('joint'):
            assert canonical(joint)==canonical(source.find(f"joint[@name='{joint.get('name')}']"))
        for link in vendor.findall('link'):
            out=source.find(f"link[@name='{link.get('name')}']")
            assert canonical(link.find('inertial'))==canonical(out.find('inertial'))
            np.testing.assert_equal(link.find('visual/geometry/mesh').attrib,out.find('visual/geometry/mesh').attrib)
    model=mujoco.MjModel.from_xml_path(str(BUNDLE/(NAME+'.xml')))
    direct_urdf=mujoco.MjModel.from_xml_path(str(BUNDLE/(NAME+'.urdf')))
    assert abs(direct_urdf.body_mass.sum()-provenance['mass_kg']['assembled'])<1e-9
    assert validate_assets(ROOT)==[]
    assert NAME in [item['id'] for item in list_mjcf_editions(get_variant(NAME,ROOT),ROOT)]
    reference=load_urdf(source,BUNDLE)
    assert (model.nq,model.nv,model.njnt,model.nu)==(50,49,44,0)
    native_order=[model.joint(i).name for i in range(1,model.njnt)]
    order=json.loads((BUNDLE/'joint-order.json').read_text())
    assert len(order['body_dof_order'])==29
    assert len(order['application_dof_order'])==43
    assert len(set(order['application_dof_order']))==43
    assert set(native_order)==set(order['application_dof_order'])
    max_error=0.0
    joints=source.findall("joint[@type='revolute']")
    rng=np.random.default_rng(43)
    cases=[np.zeros(43),*list(rng.uniform(0,1,(10,43)))]
    # Random fractions span each signed range, including mirrored right-hand limits.
    for case_index,case in enumerate(cases):
        d0=mujoco.MjData(reference);d1=mujoco.MjData(model)
        for i,j in enumerate(joints):
            a=reference.joint(j.get('name'));b=model.joint(j.get('name'))
            lo,hi=float(j.find('limit').get('lower')),float(j.find('limit').get('upper'))
            np.testing.assert_allclose(b.range,[lo,hi],atol=1e-6)
            np.testing.assert_allclose(a.axis,b.axis,atol=1e-6)
            q=0 if case_index==0 else lo+(hi-lo)*case[i]
            d0.qpos[a.qposadr[0]]=q;d1.qpos[b.qposadr[0]]=q
        mujoco.mj_forward(reference,d0);mujoco.mj_forward(model,d1)
        for link in source.findall('link'):
            name=link.get('name');a=reference.body(name).id;b=model.body(name).id
            err=max(abs(d0.xpos[a]-d1.xpos[b]).max(),abs(d0.xmat[a]-d1.xmat[b]).max())
            max_error=max(max_error,float(err));assert err<1e-5,(name,err)
            np.testing.assert_allclose(reference.body_mass[a],model.body_mass[b],atol=1e-10)
            # Compare principal inertias; poses may differ by equivalent quaternion signs.
            np.testing.assert_allclose(reference.body_inertia[a],model.body_inertia[b],atol=1e-10)
    assert abs(model.body_mass.sum()-provenance['mass_kg']['assembled'])<1e-9
    assert abs(model.body_mass.sum()-(provenance['mass_kg']['base']-.13951244-.13947198+2*.69654599))<1e-9
    for side in ('left','right'):
        assert model.body(side+'_hand_link').mass[0]==0
        palm=model.body(side+'_hand_palm_link').id
        d=mujoco.MjData(model);mujoco.mj_forward(model,d)
        np.testing.assert_allclose(d.xpos[palm],d.xpos[model.body(side+'_hand_link').id],atol=1e-12)
    # Run the generalized converter on a temporary baseline copy: never rewrite
    # canonical baseline output just to check compatibility.
    spec=importlib.util.spec_from_file_location('astro_converter',ROOT/'scripts/build-astro-mjcf.py')
    converter=importlib.util.module_from_spec(spec);spec.loader.exec_module(converter)
    with tempfile.TemporaryDirectory() as temp:
        import shutil
        copied=Path(temp)/BASE.name
        copied.mkdir();shutil.copy2(BASE/'astro_p2_29dof.urdf',copied/'astro_p2_29dof.urdf')
        (copied/'meshes').symlink_to(BASE/'meshes',target_is_directory=True)
        converter.main(copied)
        for name in ('astro_p2_29dof.xml','mjcf-conversion.json'):
            assert (copied/name).read_bytes()==(BASE/name).read_bytes(),name
    report={'mujoco_version':mujoco.__version__,'hinges':43,'body_hinges':29,'hand_hinges':14,
            'nq':model.nq,'nv':model.nv,'actuators':model.nu,'mass_kg':float(model.body_mass.sum()),
            'preserved_base_links_and_joints':preserved,'fk_configurations':len(cases),
            'max_pose_error':max_error,'baseline_regeneration_byte_identical':True,
            'native_mjcf_joint_order':native_order,'application_joint_order':order['application_dof_order']}
    (BUNDLE/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if 'joint_order' not in k},indent=2))

if __name__=='__main__':main()
