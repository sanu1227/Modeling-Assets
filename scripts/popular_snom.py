"""Snom's soft white face and eleven rounded ice spikes, hand-authored in Blender."""
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0,str(Path(__file__).resolve().parent))
import popular_tools as p
from popular_tools import c

NAME='Snom'
col,out=p.initialize(NAME);col['studio_exposure']=-1.10
WHITE='F2F2F7';ICE='A8DDEB'

def sphere(name,pos,scale,color):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=80,ring_count=52,location=pos)
    ob=c.finish(bpy.context.object,name,color);ob.scale=scale;c.active(ob)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return ob

parts=[sphere('Round white head',(0,-.35,.43),(.445,.325,.42),WHITE),
       sphere('Left soft mouth lobe',(-.14,-.63,.21),(.16,.13,.13),WHITE),
       sphere('Right soft mouth lobe',(.14,-.63,.21),(.16,.13,.13),WHITE)]
face=c.union('01_Soft two-lobed white face',parts,WHITE,.009)
c.active(face);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
mod=face.modifiers.new('Smooth head reduction','DECIMATE');mod.ratio=.40;c.apply(face,mod)
tree=BVHTree.FromObject(face,bpy.context.evaluated_depsgraph_get())
for s in (-1,1):
    hit,normal,_,_=tree.ray_cast(Vector((s*.325,-2,.205)),Vector((0,1,0)))
    if hit is None:raise ValueError('Snom eye surface not found')
    eye=c.ell('02_Tiny black eye',hit+normal*.004,(.028,.010,.029),'202629')
    eye.rotation_euler=Vector((0,-1,0)).rotation_difference(normal).to_euler()

shell=sphere('03_Pale icy body',(0,.20,.43),(.46,.59,.425),ICE)
ice= shell.data.materials[0]
bs=ice.node_tree.nodes['Principled BSDF'];bs.inputs['Roughness'].default_value=.30
bs.inputs['Transmission Weight'].default_value=.22;bs.inputs['IOR'].default_value=1.34
bs.inputs['Specular IOR Level'].default_value=.34
bs.inputs['Subsurface Weight'].default_value=.045

def crystal(name,base,tip,radius):
    base,tip=Vector(base),Vector(tip);t=(tip-base).normalized()
    u=t.cross(Vector((0,1,0))).normalized();v=t.cross(u).normalized()
    vertices=[];faces=[];sides=5
    for factor,r in ((0,radius),(.43,radius*.84),(.84,radius*.30)):
        center=base.lerp(tip,factor)
        for j in range(sides):
            angle=j*2*math.pi/sides
            vertices.append(center+u*r*math.cos(angle)+v*r*.84*math.sin(angle))
    point=len(vertices);vertices.append(tip)
    bottom=len(vertices);vertices.append(base)
    for row in range(2):
        for j in range(sides):
            a=row*sides+j;b=row*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
    for j in range(sides):
        faces.append((bottom,(j+1)%sides,j));faces.append((point,2*sides+j,2*sides+(j+1)%sides))
    ob=c.mesh(name,vertices,faces,ICE)
    mod=ob.modifiers.new('Rounded frozen tips','BEVEL');mod.width=.026;mod.segments=4;c.apply(ob,mod)
    mod=ob.modifiers.new('Soft ice facets','SUBSURF');mod.levels=1;c.apply(ob,mod)
    return ob

number=0
for yy,angles in [(-.08,(-66,-22,22,66)),(.27,(-65,0,65)),(.55,(-57,-18,18,57))]:
    for deg in angles:
        a=math.radians(deg)
        base=Vector((.32*math.sin(a),yy,.43+.30*math.cos(a)))
        direction=Vector((math.sin(a),.25 if yy>.3 else -.05,math.cos(a))).normalized()
        length=.38 if yy<.1 else .34
        tip=base+direction*length
        crystal('04_Rounded ice spike %02d'%number,base,tip,.205 if yy<.1 else .19)
        number+=1
assert number==11
for s in (-1,1):
    for yy in (-.01,.38):
        sphere('05_Tiny hidden grub foot',(s*.19,yy,.035),(.08,.115,.035),WHITE)

stats=p.save_export(col,NAME,out)
draft='--draft' in sys.argv
p.render_views(NAME,out,stats,['hero','front'] if draft else ['hero','front','side','back','clay'],draft)
p.verify(NAME,out)
