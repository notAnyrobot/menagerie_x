#!/usr/bin/env python3
"""Rebuild Astro's sample Dex3-1 assembly from bundled pinned vendor sources.

No network requests, retargeting, calibration, or hardware control are performed.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'robots/astro_p2_29dof'
NAME = 'astro_p2_43dof_dex3_1'
BUNDLE = ROOT / 'robots' / NAME
VENDOR = BUNDLE / 'upstream'
REVISION = '5994d4faef0a9cadd3287f8de0199a67eeb2a259'

def fmt(values):
    return ' '.join(f'{v:.12g}' for v in values)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def mesh_bounds(path):
    """Read binary STL vertices without a geometry dependency."""
    data = path.read_bytes()
    count = struct.unpack_from('<I', data, 80)[0]
    if len(data) != 84 + 50 * count:
        raise ValueError(f'Expected binary STL: {path}')
    low, high = [float('inf')]*3, [-float('inf')]*3
    for i in range(count):
        vertices = struct.unpack_from('<9f', data, 84 + 50*i + 12)
        for offset, value in enumerate(vertices):
            axis = offset % 3
            low[axis], high[axis] = min(low[axis], value), max(high[axis], value)
    return low, high

def main():
    urdf = ET.parse(BASE / 'astro_p2_29dof.urdf').getroot()
    urdf.set('name', NAME)
    urdf.find('mujoco/compiler').attrib.update(inertiafromgeom='false',fusestatic='false',strippath='false')
    source_files = {'LICENSE.Unitree': digest(BUNDLE/'LICENSE.Unitree')}
    for mesh in urdf.findall('.//mesh'):
        filename = mesh.get('filename')
        target = BUNDLE / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BASE / filename, target)
    # Keep the calibrated body attachment frames, remove the surrogate hand mass
    # and spheres. Adapter joints below are kinematic sample mounts with no mass.
    for side in ('left', 'right'):
        old = urdf.find(f"link[@name='{side}_hand_link']")
        old.clear(); old.set('name', side+'_hand_link')
    collision_shapes = []
    finger_order = {}
    for side, suffix in (('left','l'),('right','r')):
        path = VENDOR / f'dex3_1_{suffix}.urdf'
        vendor = ET.parse(path).getroot()
        source_files[str(path.relative_to(BUNDLE))] = digest(path)
        finger_order[side] = [j.get('name') for j in vendor.findall('joint')]
        joint = ET.SubElement(urdf,'joint',name=f'{side}_dex3_sample_adapter_joint',type='fixed')
        ET.SubElement(joint,'origin',xyz='0 0 0',rpy='0 0 0')
        ET.SubElement(joint,'parent',link=f'{side}_hand_link')
        ET.SubElement(joint,'child',link=f'{side}_hand_palm_link')
        for node in vendor:
            if node.tag not in ('link','joint'):
                continue
            node = deepcopy(node)
            if node.tag == 'link':
                for collision in list(node.findall('collision')):
                    node.remove(collision)
                for i, visual in enumerate(node.findall('visual')):
                    visual.set('name',node.get('name')+f'_visual_{i}')
                    material = visual.find('material')
                    material.clear(); material.set('name','dex3_dark')
                    ET.SubElement(material,'color',rgba='0.2 0.2 0.2 1')
                    mesh = visual.find('geometry/mesh')
                    filename = mesh.get('filename')
                    source = BUNDLE / filename
                    assert source.is_file(), source
                    source_files[filename] = digest(source)
                    low, high = mesh_bounds(source)
                    center = [(a+b)/2 for a,b in zip(low,high)]
                    size = [b-a for a,b in zip(low,high)]
                    name = node.get('name')
                    if name.endswith('palm_link'):
                        c = ET.SubElement(node,'collision',name=name+f'_bounds_collision_{i}')
                        ET.SubElement(c,'origin',xyz=fmt(center),rpy='0 0 0')
                        ET.SubElement(ET.SubElement(c,'geometry'),'box',size=fmt(size))
                        collision_shapes.append(dict(link=name,mesh=filename,type='box',center=center,size=size))
                    else:
                        # Round the segment envelope: preserve its longitudinal extent
                        # and largest transverse width, with one capsule per moving link.
                        axis = max(range(3), key=lambda k: size[k])
                        radius = max(size[k] for k in range(3) if k != axis)/2
                        distal = name.endswith(('thumb_2_link', 'index_1_link', 'middle_1_link'))
                        tip_trim = 0.004 if distal else 0.0
                        if distal:
                            # Fit the rounded core rather than the thick hinge/pad
                            # envelope. Leave the final 4 mm of tapered tip uncovered.
                            radius = 0.0095
                            direction = -1 if name.startswith('left_hand_thumb') else 1
                            center[axis] -= direction*tip_trim/2
                        length = size[axis]-tip_trim-2*radius
                        assert length > 0, (name, size)
                        rpy = ('0 1.5707963267948966 0', '1.5707963267948966 0 0', '0 0 0')[axis]
                        c = ET.SubElement(node,'collision',name=name+f'_cylinder_collision_{i}')
                        ET.SubElement(c,'origin',xyz=fmt(center),rpy=rpy)
                        ET.SubElement(ET.SubElement(c,'geometry'),'cylinder',radius=fmt([radius]),length=fmt([length]))
                        endpoints=[]
                        for end, sign in enumerate((-1,1)):
                            point=center.copy(); point[axis]+=sign*length/2
                            endpoints.append(point)
                            c=ET.SubElement(node,'collision',name=name+f'_cap_{i}_{end}')
                            ET.SubElement(c,'origin',xyz=fmt(point),rpy='0 0 0')
                            ET.SubElement(ET.SubElement(c,'geometry'),'sphere',radius=fmt([radius]))
                        collision_shapes.append(dict(link=name,mesh=filename,type='capsule',center=center,
                            axis=axis,radius=radius,cylinder_length=length,endpoints=endpoints,mesh_bounds=[low,high],distal_tip_trim=tip_trim))
            urdf.append(node)
    ET.indent(urdf,space='  ')
    output = BUNDLE / (NAME+'.urdf')
    output.write_text(ET.tostring(urdf,encoding='unicode')+'\n')
    # Explicit application order: original body order followed by left then right
    # vendor hand order. Native MJCF tree order is stored separately by validator.
    body_order=[]
    text=(BASE/'robot.yaml').read_text()
    block=text.split('dof_order:\n',1)[1].split('ik_map:',1)[0]
    body_order=[line[2:] for line in block.splitlines() if line.startswith('- ')]
    joint_order={'body_dof_order':body_order,'left_hand_dof_order':finger_order['left'],
                 'right_hand_dof_order':finger_order['right'],
                 'application_dof_order':body_order+finger_order['left']+finger_order['right'],
                 'note':'43 hinge coordinates; free-base coordinates are separate. Use joint names to map native MJCF tree order. No hand calibration or retargeting support is established.'}
    (BUNDLE/'joint-order.json').write_text(json.dumps(joint_order,indent=2)+'\n')
    yaml=['# Sample assembly only. No hand calibration or retargeting support established.',
          f'name: {NAME}','display_name: Astro P2 + Dex3-1 sample (29 body + 14 hand DOF)',
          f'urdf: {NAME}.urdf','mesh_search_paths:','- meshes','length_scale: 1.0','up_axis: Z','forward_axis: X','dof_order:']
    yaml += ['- '+name for name in joint_order['application_dof_order']]
    (BUNDLE/'robot.yaml').write_text('\n'.join(yaml)+'\n')
    base_mass=sum(float(x.get('value')) for x in ET.parse(BASE/'astro_p2_29dof.urdf').findall('link/inertial/mass'))
    total_mass=sum(float(x.get('value')) for x in urdf.findall('link/inertial/mass'))
    provenance={'preset':NAME,'base_bundle':'../astro_p2_29dof',
        'base_revision':'d6a0ee64526c3eaaa7e7beea11bb5ead9d3f44b5',
        'base_urdf_sha256':digest(BASE/'astro_p2_29dof.urdf'),
        'source_repository':'https://github.com/unitreerobotics/unitree_ros','source_revision':REVISION,
        'source_directory':'robots/dexterous_hand_description/dex3_1','license':'BSD-3-Clause',
        'license_file':'LICENSE.Unitree','vendor_files_sha256':source_files,
        'changes':['Replace old hand sphere geometry and surrogate inertia; retain original fixed hand frames.',
                   'Attach left/right official Dex3-1 palm roots at existing hand frames with identity sample adapters.',
                   'Preserve vendor visual meshes, link inertias, internal joints, limits, effort and velocity values.',
                   'Replace finger collisions with rounded mesh-bound capsule approximations; retain one AABB box per palm. Body collisions unchanged.'],
        'mounting':{'status':'Unverified sample: no mechanical fit, fasteners, adapter mass, wiring, clearance or load capacity established.',
                    'palm_from_astro_hand_frame_xyz':[0,0,0],'palm_from_astro_hand_frame_rpy':[0,0,0]},
        'mass_kg':{'base':base_mass,'removed_left_surrogate':0.13951244,'removed_right_surrogate':0.13947198,
                   'vendor_each_hand':0.69654599,'assembled':total_mass,'adapter':0},
        'calibration':'Not bundled; no hand retargeting/controller mapping is established.'}
    (BUNDLE/'SOURCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
    (BUNDLE/'hand-collision-shapes.json').write_text(json.dumps(collision_shapes,indent=2)+'\n')
    print(f'{output}: 29 body + 14 hand DOF, {total_mass:.8f} kg')

if __name__ == '__main__':
    main()
