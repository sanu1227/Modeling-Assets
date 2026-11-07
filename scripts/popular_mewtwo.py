"""Mewtwo in the official outstretched-hand psychic pose; hand-authored geometry."""
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

NAME='Mewtwo'
col,out=p.initialize(NAME)
SKIN='D0CBD9';PURPLE='9667A4';DARK='42374E'


def lathe(name,rings,color,sides=80):
    samples=c.catmull(rings,9);verts=[];faces=[]
    for z,rx,ry,cy in samples:
        for j in range(sides):
            a=j*math.pi*2/sides
            verts.append((rx*math.sin(a),cy-ry*math.cos(a),z))
    for i in range(len(samples)-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
    start,end=len(verts),len(verts)+1
    verts.extend([(0,samples[0][3],samples[0][0]),(0,samples[-1][3],samples[-1][0])])
    for j in range(sides):
        faces.append((start,(j+1)%sides,j));k=(len(samples)-1)*sides
        faces.append((end,k+j,k+(j+1)%sides))
    return c.mesh(name,verts,faces,color)


torso=lathe('Sculpt torso block',[(1.45,.12,.14,.07),(1.64,.35,.28,.07),(1.85,.40,.29,.07),
    (2.08,.32,.25,.04),(2.31,.205,.18,0),(2.57,.25,.19,-.015),(2.80,.39,.23,-.01),
    (2.98,.33,.205,.03),(3.10,.17,.16,.07),(3.34,.105,.12,.08)],SKIN)
parts=[torso,c.ell('Rounded pelvis',(0,.07,1.58),(.30,.29,.28),SKIN),
       c.tube('Neck into the skull',[(0,.07,3.19),(0,.06,3.38),(0,.04,3.50)], [.105,.11,.13],SKIN,32,8)]
for s in (-1,1):
    parts.append(c.ell('Subtle pectoral muscle',(s*.17,-.13,2.86),(.22,.145,.23),SKIN))
for s in (-1,1):
    parts.append(c.ell('Large feline thigh',(s*.36,.025,1.62),(.32,.33,.60),SKIN,rot=(0,-s*15,0)))
    parts.append(c.tube('Long digitigrade shin',[(s*.42,-.01,1.35),(s*.45,-.12,.91),
                       (s*.48,-.20,.52),(s*.55,-.32,.23)], [.19,.115,.085,.10],SKIN,32,10))
    parts.append(c.ell('Foot pad',(s*.57,-.46,.145),(.18,.33,.14),SKIN,rot=(0,0,s*14)))
    for j in (-1,1):
        parts.append(c.tube('Two long rounded toes',[(s*.57+j*.075,-.45,.15),(s*.59+j*.085,-.72,.11),
                   (s*.60+j*.08,-.85,.12)], [.095,.085,.05],SKIN,24,6))
    parts.append(c.ell('Round rear toe',(s*.45,-.19,.21),(.105,.13,.105),SKIN))
# Left arm reaches toward the viewer, the right arm hangs with curved open fingers.
arms=[((-0.32,-.015,2.94),(-.64,-.28,2.90),(-.87,-.66,2.98),(-.92,-.86,3.00)),
      ((.32,.01,2.94),(.66,-.01,2.65),(.91,-.16,2.33),(1.00,-.23,2.18))]
for shoulder,elbow,wrist,palm in arms:
    parts.append(c.ell('Deltoid',shoulder,(.19,.19,.22),SKIN))
    parts.append(c.tube('Slender arm',[shoulder,elbow,wrist,palm],[.135,.105,.075,.115],SKIN,32,9))
    parts.append(c.ell('Three-finger hand palm',palm,(.16,.14,.15),SKIN))
# Smooth connected clavicle and neck remain part of the body, with clean elbows.
body=c.union('01_Continuous body and limbs',parts,SKIN,.015)
mod=body.modifiers.new('Adaptive body mesh','DECIMATE');mod.ratio=.48;c.apply(body,mod)

# Smooth purple abdomen sits on the front of the pelvis as a real curved color patch.
tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
outline=[(0,2.22),(.14,2.15),(.28,1.93),(.33,1.69),(.22,1.43),(0,1.32),
         (-.22,1.43),(-.33,1.69),(-.28,1.93),(-.14,2.15)]
verts=[];faces=[];n=100;rings=18
boundary=c.catmull(outline+[outline[0]],10)[:-1]
# Ray projection conforms the painted patch to the fused belly instead of a floating oval.
cx,cz=0,1.77
def surf(x,z):
    hit,norm,_,_=tree.ray_cast(Vector((x,-2,z)),Vector((0,1,0)))
    if hit is None:return (x,-.25,z)
    return hit+Vector((0,-.002,0))
verts=[surf(cx,cz)]
for r in range(1,rings+1):
    for xx,zz in boundary:verts.append(surf(cx+(xx-cx)*r/rings,cz+(zz-cz)*r/rings))
n=len(boundary)
faces=[(0,1+j,1+(j+1)%n) for j in range(n)]
for r in range(rings-1):
    for j in range(n):
        a=1+r*n+j;b=1+r*n+(j+1)%n;faces.append((a,b,b+n,a+n))
belly=c.mesh('02_Purple abdomen surface',verts,faces,PURPLE)
mod=belly.modifiers.new('Closed color patch','SOLIDIFY');mod.thickness=.005;mod.offset=-1;c.apply(belly,mod)

# The tail grows from the pelvis, loops high to the left, then ends in a soft heavy tip.
tail=c.tube('03_Long muscular psychic tail',[(0,.04,1.64),(-.38,.47,1.54),(-.97,.51,1.62),
    (-1.51,.43,1.92),(-1.79,.20,2.47),(-1.94,-.04,2.74),(-2.14,-.16,2.56),
    (-2.20,-.22,2.10),(-2.04,-.22,1.65),(-1.73,-.16,1.25),(-1.65,-.14,1.20)],
    [.24,.31,.26,.18,.105,.075,.075,.085,.11,.14,.13],PURPLE,40,12)
tip=c.ell('Rounded tail end',(-1.65,-.14,1.20),(.17,.135,.14),PURPLE)
tail=c.union('03_Long muscular psychic tail',[tail,tip],PURPLE,.009)
mod=tail.modifiers.new('Smooth tail end transition','SMOOTH');mod.factor=.55;mod.iterations=5;c.apply(tail,mod)
mod=tail.modifiers.new('Adaptive tail surface','DECIMATE');mod.ratio=.52;c.apply(tail,mod)

# Exactly three fingers per hand. Each fingertip has the characteristic round pad.
finger_sets=[[
    [(-1.03,-.91,3.06),(-1.21,-1.06,3.20),(-1.23,-1.15,3.40)],
    [(-.93,-.99,2.99),(-.92,-1.24,3.02),(-.90,-1.43,3.06)],
    [(-.80,-.90,2.96),(-.60,-1.02,2.91),(-.48,-1.15,2.95)]
], [
    [(.91,-.27,2.15),(.84,-.38,2.01),(.88,-.44,1.93)],
    [(1.00,-.31,2.13),(1.03,-.40,1.94),(1.00,-.49,1.88)],
    [(1.10,-.27,2.15),(1.21,-.34,2.00),(1.20,-.43,1.91)]
]]
for hand,sets in enumerate(finger_sets):
    for points in sets:
        c.tube('04_Three articulated fingers',points,[.063,.057,.053],SKIN,24,7)
        c.ell('Round fingertip',points[-1],(.10,.095,.10) if hand==0 else (.065,.060,.065),SKIN)

# The skull has high rounded ear horns and a small angular feline muzzle.
head=lathe('Skull block',[(3.27,.07,.10,-.19),(3.34,.21,.22,-.14),(3.49,.32,.30,-.06),
    (3.69,.37,.31,.0),(3.91,.30,.25,.035),(4.02,.14,.13,.05)],SKIN,96)
head_parts=[head,c.ell('Short feline muzzle',(0,-.29,3.39),(.215,.235,.14),SKIN)]
for s in (-1,1):
    head_parts.append(c.tube('Rounded rectangular ear horn',[(s*.23,.05,3.87),(s*.28,.07,4.13),(s*.30,.08,4.29)],
                           [(.12,.11),(.095,.085),(.07,.065)],SKIN,32,8))
head=c.union('05_Catlike skull and ear horns',head_parts,SKIN,.011)
mod=head.modifiers.new('Adaptive head mesh','DECIMATE');mod.ratio=.45;c.apply(head,mod)
# The second neck tube joins the rear of the head and the shoulder blades.
c.tube('06_Secondary neck connection',[(0,.25,3.56),(0,.39,3.40),(0,.36,3.19),(0,.20,3.03)],
       [.095,.082,.073,.10],SKIN,28,10)

# Surface-painted angular eyes avoid the protruding, friendly toy-eye appearance.
uv=head.data.uv_layers.new(name='Mewtwo facial paint')
for face in head.data.polygons:
    for li in face.loop_indices:
        v=head.matrix_world@head.data.vertices[head.data.loops[li].vertex_index].co
        uv.data[li].uv=((v.x+.6)/1.2,(v.z-3.15)/1.2) if face.normal.y<.2 else (.01,.01)
res=2048
x=np.linspace(-.6,.6,res,dtype=np.float32)[None,:]
z=np.linspace(3.15,4.35,res,dtype=np.float32)[:,None]
rgb=lambda h:np.array([int(h[i:i+2],16)/255 for i in (0,2,4)],np.float32)
pixels=np.empty((res,res,4),np.float32);pixels[:,:,:3]=rgb(SKIN);pixels[:,:,3]=1
def polygon(points):
    mask=np.zeros((res,res),bool)
    for (ax,az),(bx,bz) in zip(points,points[1:]+points[:1]):
        if abs(bz-az)<1e-8:continue
        mask^=((az>z)!=(bz>z))&(x<(bx-ax)*(z-az)/(bz-az)+ax)
    return mask
for s in (-1,1):
    outline=[(s*.075,3.515),(s*.295,3.690),(s*.300,3.595),(s*.275,3.515),
             (s*.210,3.470),(s*.140,3.473)]
    center=(s*.208,3.565)
    rim=polygon([(center[0]+(a-center[0])*1.08,center[1]+(b-center[1])*1.08) for a,b in outline])
    eye=polygon(outline)
    pixels[rim,:3]=rgb('4A4056');pixels[eye,:3]=rgb('F8F6F8')
    iris=((x-s*.212)/.050)**2+((z-3.565)/.087)**2<1
    pixels[iris&eye,:3]=rgb('8555A0')
    lower=((x-s*.212)/.043)**2+((z-3.542)/.062)**2<1
    pixels[lower&iris&eye,:3]=rgb('A67ABA')
    pupil=((x-s*.212)/.021)**2+((z-3.572)/.067)**2<1
    pixels[pupil&eye,:3]=rgb('24232F')
    shine=((x-(s*.212-.012))/.014)**2+((z-3.604)/.023)**2<1
    pixels[shine&eye,:3]=rgb('FFFFFF')
    nostril=((x-s*.061)/.010)**2+((z-3.39)/.006)**2<1
    pixels[nostril,:3]=rgb('817889')
mouth=(abs(z-(3.321+.35*x*x))<.0028)&(abs(x)<.12)
pixels[mouth,:3]=rgb('82798B')
image=bpy.data.images.new('Mewtwo_face_paint',width=res,height=res,alpha=True)
image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(out/'Mewtwo_face.png');image.file_format='PNG';image.save();image.pack()
mat=bpy.data.materials.new('Mewtwo skin and violet eyes');mat.use_nodes=True
bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Roughness'].default_value=.63;bs.inputs['Specular IOR Level'].default_value=.23
tx=mat.node_tree.nodes.new('ShaderNodeTexImage');tx.image=image;mat.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color'])
head.data.materials.clear();head.data.materials.append(mat)

stats=p.save_export(col,NAME,out)
draft='--draft' in sys.argv
p.render_views(NAME,out,stats,['hero','front'] if draft else ['hero','front','side','back','clay'],draft)
p.verify(NAME,out)
