"""Gengar sculpt with continuous skin and surface-painted eyes and grin."""
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import popular_tools as p
from popular_tools import c

NAME='Gengar'
col,out=p.initialize(NAME)
PURPLE='69568F'

# A squat, pear-shaped ghost, with ears and dorsal spines fused into the skin.
bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=64,location=(0,0,1.37))
base=c.finish(bpy.context.object,'Body sculpt',PURPLE)
base.scale=(1.00,.70,1.08);c.active(base);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for v in base.data.vertices:
    z=v.co.z
    v.co.x*=1+.11*math.exp(-((z+.25)/.55)**2)-.03*max(0,z)
parts=[base]
for s in (-1,1):
    parts.append(c.tube('Swept pointed ear',[(s*.48,.02,1.95),(s*.78,.08,2.43),(s*1.13,.13,2.90)],
                        [(.40,.28),(.23,.17),.006],PURPLE,36,12))
    parts.append(c.tube('Short arm',[(s*.82,.02,1.45),(s*1.15,-.03,1.32),(s*1.36,-.14,1.43)],
                       [.30,.24,.15],PURPLE,32,9))
    # Three little pointed fingers, broader than claws, all the same purple skin.
    for k in range(3):
        parts.append(c.tube('Three pointed fingers',[(s*1.25,-.11,1.50-k*.10),
                         (s*(1.49+.035*(1-abs(k-1))),-.14,1.56-k*.16),
                         (s*(1.75-.085*k),-.12,1.65-k*.23)], [.125,.085,.005],PURPLE,24,8))
    parts.append(c.ell('Haunch',(s*.59,-.03,.49),(.36,.41,.42),PURPLE,rot=(0,-s*16,0)))
    parts.append(c.ell('Foot',(s*.62,-.22,.21),(.32,.43,.21),PURPLE))
    for j in range(3):
        parts.append(c.cone('Purple pointed toe',(s*.62+(j-1)*.17,-.47,.18),
                            (s*.62+(j-1)*.19,-.68,.075),.105,PURPLE))
# Staggered spines along the crown and the back, pointing away from the face.
for x,y,z,tx,ty,tz,rad in [(-.32,.26,2.20,-.40,.50,2.43,.17),
    (0,.38,2.20,0,.72,2.47,.18),(.32,.26,2.20,.40,.50,2.51,.17),
    (-.55,.47,2.02,-.82,.85,2.30,.24),(.55,.47,2.02,.82,.85,2.30,.24),
    (0,.60,1.85,0,1.10,2.06,.27),(-.47,.60,1.58,-.76,1.01,1.69,.22),
    (.47,.60,1.58,.76,1.01,1.69,.22),(0,.65,1.23,0,1.18,1.32,.26)]:
    if z<=2.02:
        # Place the full root disk inside the torso; the visible spike tips stay fixed.
        x*=.85;y-=.23;z-=.05;rad*=1.35
    parts.append(c.cone('Dorsal spine',(x,y,z),(tx,ty,tz),rad,PURPLE))
parts.append(c.tube('Short pointed tail',[(0,.44,.60),(0,.83,.47),(0,1.14,.35)], [.31,.22,.005],PURPLE,32,8))
body=c.union('Gengar • continuous sculpt',parts,PURPLE,.016)
coords=np.empty(len(body.data.vertices)*3,np.float64);body.data.vertices.foreach_get('co',coords)
matrix=np.array(body.matrix_world);coords=coords.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]
weights=np.zeros(len(coords))
for center,sigma in [((s*1.10,-.08,1.37),.27) for s in (-1,1)]+[((s*.61,-.19,.32),.24) for s in (-1,1)]:
    weights=np.maximum(weights,np.exp(-np.sum((coords-np.array(center))**2,axis=1)/sigma**2))
group=body.vertex_groups.new(name='Smooth wrist and ankle transitions')
bins=(weights*15).astype(np.int32)
for level in range(1,16):
    indices=np.flatnonzero(bins==level).tolist()
    if indices:group.add(indices,level/15,'REPLACE')
mod=body.modifiers.new('Local joint sculpt polish','SMOOTH');mod.factor=.9;mod.iterations=18;mod.vertex_group=group.name;c.apply(body,mod)
mod=body.modifiers.new('Final silhouette polish','SMOOTH');mod.factor=.7;mod.iterations=5;c.apply(body,mod)
mod=body.modifiers.new('Adaptive sculpt reduction','DECIMATE');mod.ratio=.45;c.apply(body,mod)

# Front-projected UVs prevent facial paint leaking onto the tapered horn surfaces.
uv=body.data.uv_layers.new(name='Gengar painted face')
coords=[]
for v in body.data.vertices:
    x,y,z=body.matrix_world@v.co
    coords.append(((x+1.8)/3.6,z/3.15))
for poly in body.data.polygons:
    points=[coords[body.data.loops[i].vertex_index] for i in poly.loop_indices]
    center=body.matrix_world@poly.center
    for li,(u,v) in zip(poly.loop_indices,points):
        uv.data[li].uv=(u,v) if center.y<-.19 else (.01,.01)

res=4096
z=np.linspace(0,3.15,res,dtype=np.float32)[:,None]
x=np.linspace(-1.8,1.8,res,dtype=np.float32)[None,:]
front=True
pixels=np.empty((res,res,4),np.float32)
def rgb(h):return np.array([int(h[i:i+2],16)/255 for i in (0,2,4)],np.float32)
pixels[:,:,:3]=rgb(PURPLE);pixels[:,:,3]=1
def paint(mask,color):pixels[mask,:3]=rgb(color)

# Angular red eyes: high outer corners and low inner corners.
ax=np.abs(x)
upper=1.77+.66*(ax-.20)
lower=1.695-.08*(ax-.40)+2.2*(ax-.44)**2
eyes=(ax>.19)&(ax<.70)&(z<upper)&(z>lower)&front
eye_edge=(ax>.175)&(ax<.717)&(z<upper+.017)&(z>lower-.018)&front
paint(eye_edge,'29243E');paint(eyes,'ED706F')
inner=(ax>.21)&(ax<.68)&(z<upper-.035)&(z>lower+.025)&front
paint(inner,'F28983')
pupil=((ax-.445)/.020)**2+((z-1.87)/.110)**2<1
paint(pupil&eyes,'291E34')
# The teeth form one broad crescent, with five fine vertical tooth divisions.
upper=1.18+.54*x*x
lower=.91+.88*x*x
mouth=(np.abs(x)<.79)&(z<upper)&(z>lower)&front
outline=(np.abs(x)<.805)&(z<upper+.020)&(z>lower-.021)&front
paint(outline,'30243D');paint(mouth,'F1F4E8')
for divider in [-.56,-.30,0,.30,.56]:
    slant=divider+.12*divider*(z-1.1)
    paint((np.abs(x-slant)<.009)&mouth,'453D56')

image=bpy.data.images.new('Gengar_face_paint',width=res,height=res,alpha=True)
image.pixels.foreach_set(pixels.ravel())
image.filepath_raw=str(out/'Gengar_face.png');image.file_format='PNG';image.save();image.pack()
mat=bpy.data.materials.new('Purple skin with painted red eyes and teeth');mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.70;bs.inputs['Specular IOR Level'].default_value=.20
tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
body.data.materials.clear();body.data.materials.append(mat)

stats=p.save_export(col,NAME,out)
draft='--draft' in sys.argv
views=['hero','front'] if draft else ['hero','front','side','back','clay']
p.render_views(NAME,out,stats,views,draft)
p.verify(NAME,out)
