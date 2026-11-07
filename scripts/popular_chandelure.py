"""Chandelure: pale lantern, black iron scrolls, yellow eyes and violet flames."""
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
import popular_tools as p
from popular_tools import c

NAME='Chandelure'
col,out=p.initialize(NAME);col['studio_exposure']=-.95
IRON='30323C';GLASS='B7C9E5';GOLD='F4D54C'

# The lantern is an opaque/frosted pale orb, avoiding a transparent empty shell.
bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=64,location=(0,0,1.58))
orb=c.finish(bpy.context.object,'01_Frosted spectral lantern',GLASS)
orb.scale=(.67,.52,.47);c.active(orb);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
mat=orb.data.materials[0];bs=mat.node_tree.nodes['Principled BSDF']
bs.inputs['Roughness'].default_value=.35;bs.inputs['Specular IOR Level'].default_value=.32
bs.inputs['Transmission Weight'].default_value=.08
bs.inputs['Emission Color'].default_value=(.20,.24,.44,1);bs.inputs['Emission Strength'].default_value=.16

# Meridians wrap the actual orb and join at the upper and lower iron collars.
for j in range(8):
    az=j*2*math.pi/8
    points=[]
    for k in range(30):
        a=.08+(math.pi-.16)*k/29
        points.append((.678*math.sin(a)*math.sin(az),.528*math.sin(a)*math.cos(az),1.58+.478*math.cos(a)))
    c.tube('02_Curved lantern rib',points,[.022]*len(points),IRON,12,2)

def band(name,z,rx,ry,radius):
    points=[(rx*math.cos(j*2*math.pi/80),ry*math.sin(j*2*math.pi/80),z) for j in range(81)]
    return c.tube(name,points,[radius]*len(points),IRON,12,1)

band('03_Lower rim',1.105,.43,.35,.049)
band('04_Upper rim',2.04,.30,.25,.035)

# A tapered bottom fin gives the chandelier its recognizable hanging silhouette.
profile=[(.42,.012),(.58,.105),(.79,.22),(.99,.30),(1.11,.43),(1.16,.37)]
verts=[];faces=[];n=64
for z,r in profile:
    for j in range(n):
        a=j*2*math.pi/n;verts.append((r*math.cos(a),r*.72*math.sin(a),z))
for k in range(len(profile)-1):
    for j in range(n):
        a=k*n+j;b=k*n+(j+1)%n;faces.append((a,b,b+n,a+n))
start,end=len(verts),len(verts)+1;verts.extend([(0,0,profile[0][0]),(0,0,profile[-1][0])])
for j in range(n):
    faces.append((start,(j+1)%n,j));k=(len(profile)-1)*n;faces.append((end,k+j,k+(j+1)%n))
c.mesh('05_Tapered hanging base',verts,faces,IRON)

# Eye disks curve around the front face; the yellow areas have no pupils.
for s in (-1,1):
    c.patch('06_Black eye rim',(0,0,1.58),(.67,.52,.47),(s*.31,1.70),(.128,.128),IRON)
    c.patch('07_Golden eye',(0,0,1.58),(.67,.52,.47),(s*.31,1.70),(.093,.093),GOLD)
points=[]
for j in range(30):
    xx=-.51+1.02*j/29;zz=1.55
    yy=c.front((0,0,1.58),(.67,.52,.47),xx,zz)-.018
    points.append((xx,yy,zz))
c.tube('08_Horizontal face grille',points,[.018]*len(points),IRON,12,1)
for xx in (-.21,0,.21):
    points=[]
    for zz in (1.43,1.55,1.68):points.append((xx,c.front((0,0,1.58),(.67,.52,.47),xx,zz)-.019,zz))
    c.tube('09_Short grille tooth',points,[.016]*3,IRON,12,4)

# One packed gradient is shared by all five real mesh flames and survives GLB export.
height,width=512,32
gradient=np.empty((height,width,4),np.float32)
colors=np.array([[.57,.80,.94],[.43,.54,.83],[.42,.36,.70],[.55,.43,.77]],np.float32)
for row in range(height):
    t=row/(height-1)*3;i=min(2,int(t));color=colors[i]*(1-(t-i))+colors[i+1]*(t-i)
    gradient[row,:,:3]=color;gradient[row,:,3]=1
image=bpy.data.images.new('Chandelure_flame_gradient',width=width,height=height,alpha=True)
image.pixels.foreach_set(gradient.ravel());image.filepath_raw=str(out/'Chandelure_flames.png');image.file_format='PNG';image.save();image.pack()
flame_mat=bpy.data.materials.new('Blue to violet spectral fire');flame_mat.use_nodes=True
shader=flame_mat.node_tree.nodes['Principled BSDF'];shader.inputs['Roughness'].default_value=.8
shader.inputs['Emission Strength'].default_value=.65
tx=flame_mat.node_tree.nodes.new('ShaderNodeTexImage');tx.image=image
flame_mat.node_tree.links.new(tx.outputs['Color'],shader.inputs['Base Color'])
flame_mat.node_tree.links.new(tx.outputs['Color'],shader.inputs['Emission Color'])

def cup(name,center,radius,height,jagged=None):
    verts=[];faces=[];n=64;rings=16
    for k in range(rings+1):
        t=k/rings
        for j in range(n):
            a=j*2*math.pi/n
            amplitude=.075*radius/.15 if jagged is None else jagged
            zz=center.z+height*t+amplitude*max(0,(t-.60)/.40)*math.cos(a*5)
            rr=radius*(.20+.80*math.sin(t*math.pi*.53))
            verts.append(center+Vector((rr*math.cos(a),rr*math.sin(a),zz-center.z)))
    for k in range(rings):
        for j in range(n):
            aa=k*n+j;bb=k*n+(j+1)%n;faces.append((aa,bb,bb+n,aa+n))
    ob=c.mesh(name,verts,faces,IRON)
    mod=ob.modifiers.new('Thick candle cup','SOLIDIFY');mod.thickness=.025;mod.offset=-1;c.apply(ob,mod)
    return ob

def flame(name,base,height,width,lean):
    points=[base,base+Vector((-.08*lean,0,height*.20)),base+Vector((.10*lean,0,height*.47)),
            base+Vector((.18*lean,0,height*.69)),base+Vector((-.01*lean,0,height*.91)),
            base+Vector((.09*lean,0,height))]
    ob=c.tube(name,points,[(width*.34,width*.32),(width,width*.70),(width*.68,width*.51),
               (width*.46,width*.30),(width*.15,width*.12),.003],'8B72C7',40,10)
    uv=ob.data.uv_layers.new(name='Flame height gradient')
    for f in ob.data.polygons:
        for li in f.loop_indices:
            v=ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv=(.5,max(0,min(1,(v.z-base.z)/height)))
    ob.data.materials.clear();ob.data.materials.append(flame_mat)
    return ob

cup('10_Crown cup',Vector((0,0,2.04)),.27,.12,.04)
flame('11_Main dancing flame',Vector((0,0,2.13)),1.25,.20,1)
for j,angle in enumerate((math.radians(30),math.radians(150),math.radians(215),math.radians(325))):
    radial=Vector((math.cos(angle),math.sin(angle),0))
    # Behind candles are slightly higher, as in the asymmetrical official illustration.
    top=2.05+(.22 if radial.y>0 else -.03)
    points=[Vector((0,0,.91)),radial*.65+Vector((0,0,.76)),radial*1.06+Vector((0,0,.96)),
            radial*1.25+Vector((0,0,1.40)),radial*1.30+Vector((0,0,top))]
    c.tube('12_Swept candelabra arm',points,[.049,.045,.041,.038,.030],IRON,20,10)
    curls=[radial*r+Vector((0,0,z)) for r,z in [(1.15,1.03),(1.18,1.50),(1.05,1.82),
           (.82,1.92),(.65,1.79),(.69,1.59),(.86,1.56),(.98,1.66),(.93,1.78),(.82,1.79)]]
    c.tube('13_Inner iron scroll',curls,[r*.75 for r in [.055,.055,.052,.05,.048,.045,.042,.038,.032,.018]],IRON,20,7)
    center=radial*1.30+Vector((0,0,top-.04))
    cup('14_Five-point candle cup',center,.15,.22)
    flame('15_Side violet flame',center+Vector((0,0,.16)),.53,.090,.25 if j%2 else -.25)

stats=p.save_export(col,NAME,out)
draft='--draft' in sys.argv
p.render_views(NAME,out,stats,['hero','front'] if draft else ['hero','front','side','back','clay'],draft)
p.verify(NAME,out)
