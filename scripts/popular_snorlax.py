"""Snorlax in the iconic seated pose, with rounded continuous silhouette."""
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0,str(Path(__file__).resolve().parent))
import popular_tools as p
from popular_tools import c

NAME='Snorlax'
col,out=p.initialize(NAME)
col['studio_exposure']=-1.10
BLUE='397D91';CREAM='E8DFCD';CLAW='F1EEE5';PAD='81715E'

def sphere(name,center,scale,color):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=48,location=center)
    ob=c.finish(bpy.context.object,name,color);ob.scale=scale;c.active(ob)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    return ob

parts=[sphere('Very broad body',(0,.05,1.20),(1.30,.77,1.12),BLUE),
       sphere('Broad sleeping head',(0,-.24,2.40),(.67,.46,.57),BLUE)]
for s in (-1,1):
    parts.append(c.tube('Short pointed cat ear',[(s*.40,-.14,2.73),(s*.49,-.11,2.99),(s*.57,-.075,3.13)],
                       [(.225,.15),(.145,.10),.007],BLUE,32,8))
    parts.append(c.tube('Heavy outstretched arm',[(s*.43,.05,1.83),(s*1.08,-.05,1.88),
                      (s*1.42,-.17,1.65),(s*1.53,-.24,1.54)], [.30,.33,.23,.15],BLUE,32,9))
    parts.append(c.ell('Round hand end',(s*1.48,-.22,1.56),(.23,.22,.18),BLUE))
body=c.union('01_Continuous sleeping body',parts,BLUE,.018)
mod=body.modifiers.new('Smooth round silhouette','SMOOTH');mod.factor=.6;mod.iterations=5;c.apply(body,mod)
mod=body.modifiers.new('Adaptive sculpt mesh','DECIMATE');mod.ratio=.50;c.apply(body,mod)
c.active(body);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)

uv=body.data.uv_layers.new(name='Snorlax cream markings')
for poly in body.data.polygons:
    for li in poly.loop_indices:
        v=body.matrix_world@body.data.vertices[body.data.loops[li].vertex_index].co
        uv.data[li].uv=((v.x+1.8)/3.6,v.z/3.3) if poly.center.y<-.10 else (.01,.01)
res=3072
x=np.linspace(-1.8,1.8,res,dtype=np.float32)[None,:]
z=np.linspace(0,3.3,res,dtype=np.float32)[:,None]
rgb=lambda h:np.array([int(h[i:i+2],16)/255 for i in (0,2,4)],np.float32)
pixels=np.empty((res,res,4),np.float32);pixels[:,:,:3]=rgb(BLUE);pixels[:,:,3]=1
belly=(x/1.105)**2+((z-1.075)/.995)**2<1
pixels[belly,:3]=rgb(CREAM)
face=(x/.595)**2+((z-2.39)/.405)**2<1
top=2.79-.25*np.exp(-(x/.20)**2)
face&=z<top
pixels[face,:3]=rgb(CREAM)
for s in (-1,1):
    localx=(x-s*.245)/.155
    eyelid=2.395+.025*localx*localx-s*.010*localx
    mask=(abs(z-eyelid)<.006)&(abs(localx)<1)
    pixels[mask&face,:3]=rgb('393F40')
mouth=2.195+.22*x*x
pixels[(abs(z-mouth)<.006)&(abs(x)<.245)&face,:3]=rgb('464745')
im=bpy.data.images.new('Snorlax_cream_face',width=res,height=res,alpha=True)
im.pixels.foreach_set(pixels.ravel());im.filepath_raw=str(out/'Snorlax_markings.png');im.file_format='PNG';im.save();im.pack()
mat=bpy.data.materials.new('Snorlax blue and cream skin');mat.use_nodes=True
bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Roughness'].default_value=.76;bs.inputs['Specular IOR Level'].default_value=.18
tx=mat.node_tree.nodes.new('ShaderNodeTexImage');tx.image=im;mat.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color'])
body.data.materials.clear();body.data.materials.append(mat)

# Seated soles face forward; the brown pads are shallow curved color surfaces.
for s in (-1,1):
    center=(s*.91,-.66,.40);scale=(.38,.30,.40)
    foot=sphere('02_Cream seated foot',center,scale,CREAM)
    c.patch('03_Round sole pad',center,scale,(s*.91,.31),(.245,.225),PAD)
    for j in (-1,0,1):
        x0=s*.91+j*.235;z0=.66 if j else .74
        c.tube('04_Three ivory foot claws',[(x0,-.73,z0),(x0+j*.025,-.79,z0+.105),
                    (x0+j*.045,-.76,z0+.20)], [.082,.060,.004],CLAW,24,7)
    for j in (-1,0,1):
        x0=s*(1.53+j*.080)
        c.cone('05_Three tiny hand claws',(x0,-.37,1.48),(x0+s*.020,-.47,1.36),.034,CLAW)
tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
for s in (-1,1):
    hit,normal,_,_=tree.ray_cast(Vector((s*.208,-2,2.205)),Vector((0,1,0)))
    c.cone('06_Small upward mouth fang',hit+Vector((0,-.012,0)),hit+Vector((s*.006,-.028,.070)),.030,CLAW)

stats=p.save_export(col,NAME,out)
draft='--draft' in sys.argv
p.render_views(NAME,out,stats,['hero','front'] if draft else ['hero','front','side','back','clay'],draft)
p.verify(NAME,out)
