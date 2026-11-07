"""Original hand-authored Dragonite model guided by official art and HOME render.

Front -Y, up Z. Build only by default; --draft makes two CPU review images.
"""
import sys
import math
import struct
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import eeveelutions_helpers as h

OUT=h.setup('Dragonite')
ORANGE='EFA139';CREAM='F8E9AE';STRIPE='A99A6F';TEAL='229F9C';TEALD='188A89';INK='27322E';CLAW='FFF9E6'


def lathe(name,profile,color):
    samples=h.catmull(profile,12);sides=96;verts=[];faces=[]
    for z,rx,ry,cy in samples:
        for j in range(sides):
            a=j*2*math.pi/sides
            verts.append((rx*math.sin(a),cy-ry*math.cos(a),z))
    for i in range(len(samples)-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
    start,end=len(verts),len(verts)+1
    verts.extend([(0,samples[0][3],samples[0][0]),(0,samples[-1][3],samples[-1][0])])
    for j in range(sides):
        faces.append((start,(j+1)%sides,j));k=(len(samples)-1)*sides
        faces.append((end,k+j,k+(j+1)%sides))
    return h.mesh(name,verts,faces,color)


def texture_core(obj):
    res=2048;zmax=3.55
    vv,uu=np.mgrid[0:res,0:res].astype(np.float32)/(res-1)
    z=zmax*(1-vv);angle=(uu-.5)*2*math.pi
    extent=np.interp(z,[.25,.35,.45,.65,1.0,1.45,1.9,2.3,2.60,2.69],[1.8,1.5,1.20,1.08,1.03,.95,.82,.74,.68,.55])
    mask=np.clip((extent-np.abs(angle))/.014+.5,0,1)
    mask*=np.clip((z-.25)/.014+.5,0,1)*np.clip((2.69-z)/.012+.5,0,1)
    def rgb(col):return np.array([int(col[i:i+2],16) for i in (0,2,4)],np.float32)
    cream=np.broadcast_to(rgb(CREAM),(res,res,3)).copy()
    curve=z+.085*np.cos(angle)
    distance=np.full((res,res),10,np.float32)
    for level in [.51,.70,.90,1.11,1.32,1.53,1.74,1.94,2.13,2.30,2.46,2.60,2.72]:distance=np.minimum(distance,np.abs(curve-level))
    line=np.clip((.006-distance)/.002+.5,0,1)
    cream=cream*(1-line[...,None])+rgb(STRIPE)*line[...,None]
    pixels=rgb(ORANGE)*(1-mask[...,None])+cream*mask[...,None]
    pixels=np.clip(pixels,0,255).astype(np.uint8)
    def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',res,res,8,2,0,0,0))
    raw+=chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in pixels)))+chunk(b'IEND',b'')
    tex=OUT/'Textures';tex.mkdir(exist_ok=True);path=tex/'Dragonite_belly.png';path.write_bytes(raw)
    image=bpy.data.images.load(str(path));image.pack()
    mat=bpy.data.materials.new('Dragonite | painted segmented belly');mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.55;shader.inputs['Specular IOR Level'].default_value=.24
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
    mat.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
    obj.data.materials.clear();obj.data.materials.append(mat)
    for p in obj.data.polygons:p.material_index=0
    while obj.data.uv_layers:obj.data.uv_layers.remove(obj.data.uv_layers[0])
    uv=obj.data.uv_layers.new(name='Continuous belly UV');coords=[]
    for vertex in obj.data.vertices:
        p=obj.matrix_world@vertex.co
        cy=float(np.interp(p.z,[0,1.5,2.2,2.7,3.55],[0,0,-.02,-.12,-.15]))
        a=math.atan2(p.x,-(p.y-cy));coords.append(((a+math.pi)/(2*math.pi),p.z/zmax))
    for face in obj.data.polygons:
        values=[coords[obj.data.loops[i].vertex_index] for i in face.loop_indices]
        seam=max(u for u,v in values)-min(u for u,v in values)>.5
        for i,(u,v) in zip(face.loop_indices,values):uv.data[i].uv=(u+1 if seam and u<.5 else u,v)


def wing(s):
    # Curved leading edge and two trailing membrane points, rather than a triangle.
    outline=[(.34,2.12),(.55,2.31),(.74,2.57),(.87,2.83),(.96,2.79),
             (1.17,2.57),(1.34,2.27),(1.42,1.96),(1.28,2.10),
             (1.14,2.09),(1.02,1.96),(.86,2.09),(.72,2.12),(.57,2.04),(.40,2.02)]
    # Catmull interpolation retains the lobes while making the silhouette supple.
    pts=[Vector(p) for p in outline];border=[]
    for i in range(len(pts)):
        a,b,c,d=pts[(i-1)%len(pts)],pts[i],pts[(i+1)%len(pts)],pts[(i+2)%len(pts)]
        for j in range(6):
            t=j/6;border.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    n=len(border);rings=12;cx,cz=.91,2.34;verts=[];faces=[]
    for side in (-1,1):
        verts.append((s*cx,.43+side*.014,cz))
        for k in range(1,rings+1):
            r=k/rings
            for p in border:
                x=cx+(p.x-cx)*r;z=cz+(p.y-cz)*r
                y=.27+.13*(x-.34)/1.08+.07*(1-r*r)
                verts.append((s*x,y+side*.013,z))
    count=1+n*rings
    for base in (0,count):
        for j in range(n):faces.append((base,base+1+j,base+1+(j+1)%n))
        for k in range(rings-1):
            for j in range(n):
                a=base+1+k*n+j;b=base+1+k*n+(j+1)%n;faces.append((a,b,b+n,a+n))
    k=1+(rings-1)*n
    for j in range(n):
        a=k+j;b=k+(j+1)%n;faces.append((a,b,b+count,a+count))
    membrane=h.mesh('Dragonite | '+str(s)+' teal wing membrane',verts,faces,TEAL)
    h.tube('Dragonite | '+str(s)+' orange leading wing edge',
           [(s*.34,.27,2.12),(s*.55,.296,2.31),(s*.74,.32,2.57),(s*.87,.333,2.83),
            (s*1.10,.361,2.66),(s*1.29,.385,2.38),(s*1.39,.398,2.14),(s*1.42,.40,1.96)],
           [.042,.037,.033,.035,.031,.027,.020,.006],ORANGE,sides=32,steps=12)
    h.tube('Dragonite | '+str(s)+' wing membrane fold',
           [(s*.87,.31,2.79),(s*.92,.34,2.51),(s*.96,.36,2.22),(s*1.02,.37,1.97)],
           [.013,.017,.014,.006],TEALD,sides=20,steps=10)


profile=[(.34,.19,.22,.02),(.47,.44,.36,.02),(.78,.61,.46,.015),(1.15,.65,.49,.01),
         (1.52,.57,.44,0),(1.91,.43,.34,-.005),(2.25,.32,.27,-.03),(2.55,.28,.25,-.07),(2.76,.245,.23,-.10)]
torso=lathe('Dragonite | pear torso and long neck',profile,ORANGE)
core=h.union('Dragonite | continuous body and head',[
    torso,h.ell('Head',(0,-.15,2.96),(.345,.31,.37),ORANGE),
    h.ell('Snout',(0,-.405,2.78),(.29,.34,.215),ORANGE),
    h.ell('Lower jaw',(0,-.35,2.67),(.25,.29,.125),ORANGE)],ORANGE,.017)

# Thick rounded haunches, tapering ankles and three distinct toe claws per foot.
for s in (-1,1):
    h.union('Dragonite | '+str(s)+' leg',[
        h.ell('Thigh',(s*.51,.015,.73),(.30,.34,.46),ORANGE,(0,s*-7,0)),
        h.tube('Shin',[(s*.53,.01,.68),(s*.56,-.045,.39),(s*.58,-.12,.18)],
               [(.20,.22),(.16,.17),(.17,.18)],ORANGE),
        h.ell('Broad foot',(s*.59,-.265,.13),(.255,.355,.14),ORANGE)],ORANGE,.016)
    for i,dx in enumerate((-.16,0,.16)):
        h.tube('Dragonite | foot claw '+str(s)+' '+str(i),
               [(s*.59+dx,-.535,.15),(s*.59+dx,-.66,.12),(s*.59+dx,-.77,.065)],
               [(.078,.072),(.061,.050),(.003,.003)],CLAW,sides=40,steps=12)

# The asymmetric gentle wave is the pose used in the official illustration.
arms=[]
for s in (-1,1):
    if s<0:
        points=[(-.41,-.005,2.09),(-.67,-.12,1.96),(-.91,-.24,2.07),(-1.04,-.29,2.25)]
        palm=(-1.035,-.29,2.25);scale=(.185,.15,.20)
    else:
        points=[(.42,-.005,2.08),(.64,-.08,1.91),(.81,-.18,1.67),(.97,-.29,1.47)]
        palm=(.97,-.29,1.47);scale=(.18,.15,.18)
    arm=h.union('Dragonite | '+str(s)+' arm',[
        h.tube('Arm',points,[(.19,.20),(.19,.19),(.17,.17),(.15,.15)],ORANGE),
        h.ell('Palm',palm,scale,ORANGE)],ORANGE,.014)
    arms.append(arm)
    for i,dx in enumerate((-.12,0,.12)):
        if s<0:points=[(palm[0]+dx,palm[1]-.02,2.39),(palm[0]+dx,palm[1]-.065,2.48),(palm[0]+dx,palm[1]-.10,2.54)]
        else:points=[(palm[0]+dx,palm[1]-.055,1.37),(palm[0]+dx,palm[1]-.10,1.28),(palm[0]+dx,palm[1]-.15,1.25)]
        h.tube('Dragonite | hand claw '+str(s)+' '+str(i),points,[.057,.041,.003],CLAW,sides=32,steps=10)

# Fuse shoulder transitions into the main skin. Arms remain orange because they
# lie outside the angular front-belly mask.
core=h.union('Dragonite | continuous body head and arms',[core,*arms],ORANGE,.016)
texture_core(core)

# Swept tail, with the same cream transverse underside plates as the belly.
tail_points=[(0,.37,.69),(.02,.89,.60),(.13,1.45,.68),(.29,1.96,.96),(.40,2.28,1.31),(.43,2.42,1.55)]
tail=h.tube('Dragonite | long swept tail',tail_points,
            [(.34,.29),(.31,.28),(.25,.23),(.17,.17),(.085,.095),(.003,.003)],ORANGE,
            sides=64,steps=20,width_axis=(1,0,0))
tail.data.materials.append(h.material(CREAM));tail.data.materials.append(h.material(STRIPE))
path=h.catmull(tail_points,20)
for i in range(len(path)-1):
    for j in range(64):
        if math.sin((j+.5)*2*math.pi/64)>.26:
            tail.data.polygons[i*64+j].material_index=2 if i%7==0 else 1

wing(-1);wing(1)

# Tall black eyes with a fine cream sclera rim, not mammalian irises.
for s in (-1,1):
    x=s*.216;z=3.035
    h.paint('Dragonite | eye outline '+str(s),core,h.circle(x,z,.084,.139,s*-8),INK,depth=.004)
    h.paint('Dragonite | eye white '+str(s),core,h.circle(x,z,.075,.130,s*-8),CLAW,depth=.007)
    h.paint('Dragonite | dark eye '+str(s),core,h.circle(x+s*.009,z+.001,.055,.117,s*-8),'1F2A22',depth=.010)
    h.paint('Dragonite | eye highlight '+str(s),core,h.circle(x-s*.012,z+.066,.020,.035,s*-8),'FFFFFF',depth=.013)
    h.paint('Dragonite | nostril '+str(s),core,h.circle(s*.115,2.805,.018,.010,s*20),'65502C',depth=.004)

bpy.context.view_layer.update();bv=BVHTree.FromObject(core,bpy.context.evaluated_depsgraph_get())
mouth=[]
for x,z in [(-.235,2.69),(-.18,2.635),(-.09,2.61),(0,2.606),(.09,2.61),(.18,2.635),(.235,2.69)]:
    p,n,_,_=bv.ray_cast(core.matrix_world.inverted()@Vector((x,-6,z)),Vector((0,1,0)),15)
    mouth.append(core.matrix_world@p+n*.004)
h.line('Dragonite | gentle smile',mouth,'7B6339',.005)

h.tube('Dragonite | short crown horn',[(0,-.02,3.24),(0,-.005,3.39),(0,.0,3.49)],[.085,.060,.003],ORANGE,sides=40,steps=12)
h.tube('Dragonite | left antenna',[(-.19,-.13,3.19),(-.30,-.11,3.40),(-.54,-.08,3.43),(-.77,-.05,3.39),(-.88,-.02,3.51),(-.88,0,3.65)],
       [.026,.025,.023,.021,.019,.012],CREAM,sides=24,steps=14)
h.tube('Dragonite | right antenna',[(.19,-.13,3.19),(.30,-.11,3.40),(.54,-.08,3.45),(.78,-.03,3.47),(.88,.02,3.65)],
       [.026,.025,.023,.020,.012],CREAM,sides=24,steps=14)

# Match the broad, short-necked original silhouette without stretching markings.
for obj in h.COL.objects:
    if obj.type!='MESH':continue
    world=obj.matrix_world;inverse=world.inverted()
    for vertex in obj.data.vertices:
        p=world@vertex.co
        p.x*=1+.13*max(0,min(1,(2.0-p.z)/.55))
        if p.z>1.8:p.z=1.8+(p.z-1.8)*.83
        vertex.co=inverse@p
    obj.data.update()

h.stage();h.save_export()
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if '--draft' in args:h.render(('hero','front'),True)
if '--all' in args:h.render(('hero','front','side','back','clay'))
if not h.validate()['passed']:raise RuntimeError('Dragonite validation failed')
