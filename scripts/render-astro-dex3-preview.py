#!/usr/bin/env python3
"""Render the sample model without advancing simulation (MUJOCO_GL=egl)."""
import os
os.environ.setdefault('MUJOCO_GL','egl')
from pathlib import Path
import struct
import zlib
import xml.etree.ElementTree as ET
import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'robots/astro_p2_43dof_dex3_1'

def png(path,pixels):
    h,w,_=pixels.shape
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    rows=b''.join(b'\0'+row.tobytes() for row in pixels)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b''))

def main():
    root=ET.parse(BUNDLE/(BUNDLE.name+'.xml')).getroot()
    for mesh in root.findall('asset/mesh'):
        mesh.set('file',str(BUNDLE/'meshes'/Path(mesh.get('file')).name))
    # Preview-only studio backdrop and lights; robot description stays unchanged.
    ET.SubElement(root.find('asset'),'texture',name='preview_sky',type='skybox',builtin='flat',
                  rgb1='.86 .89 .93',rgb2='.86 .89 .93',width='512',height='512')
    world=root.find('worldbody')
    ET.SubElement(world,'light',pos='1 1 3',dir='-1 -1 -3',directional='true',diffuse='.8 .8 .8')
    ET.SubElement(world,'light',pos='-1 -1 2',dir='1 1 -2',directional='true',diffuse='.6 .6 .6')
    model=mujoco.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'))
    model.vis.headlight.ambient[:]=(.5,.5,.5)
    model.vis.global_.offwidth=1000;model.vis.global_.offheight=800
    data=mujoco.MjData(model)
    mujoco.mj_forward(model,data)
    option=mujoco.MjvOption();option.geomgroup[:]=0;option.geomgroup[1]=1
    with mujoco.Renderer(model,height=800,width=1000) as renderer:
        camera=mujoco.MjvCamera();camera.type=mujoco.mjtCamera.mjCAMERA_FREE
        camera.lookat[:]=[0,0,0];camera.distance=2.1;camera.azimuth=135;camera.elevation=-12
        renderer.update_scene(data,camera=camera,scene_option=option)
        png(BUNDLE/'preview-whole.png',renderer.render())
        # Separate views avoid occluding one hand behind the torso.
        for side,azimuth in (('left',125),('right',235)):
            center=data.xpos[model.body(side+'_hand_palm_link').id].copy()
            center+=data.xmat[model.body(side+'_hand_palm_link').id].reshape(3,3)@np.array([.075,0,0])
            camera.lookat[:]=center;camera.distance=.45;camera.azimuth=azimuth;camera.elevation=-15
            renderer.update_scene(data,camera=camera,scene_option=option)
            png(BUNDLE/f'preview-{side}-open.png',renderer.render())
        for side in ('left','right'):
            for digit,count in (('thumb',3),('index',2),('middle',2)):
                for i in range(count):
                    joint=model.joint(f'{side}_hand_{digit}_{i}_joint')
                    lo,hi=joint.range
                    q=(hi if abs(hi)>abs(lo) else lo)*.45
                    data.qpos[joint.qposadr[0]]=q
        mujoco.mj_forward(model,data)
        for side,azimuth in (('left',125),('right',235)):
            center=data.xpos[model.body(side+'_hand_palm_link').id].copy()
            center+=data.xmat[model.body(side+'_hand_palm_link').id].reshape(3,3)@np.array([.075,0,0])
            camera.lookat[:]=center;camera.distance=.45;camera.azimuth=azimuth;camera.elevation=-15
            renderer.update_scene(data,camera=camera,scene_option=option)
            png(BUNDLE/f'preview-{side}-bent.png',renderer.render())
    print('Rendered sample assembly and open/bent hand previews in',BUNDLE)

if __name__=='__main__':main()
