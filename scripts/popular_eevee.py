"""Refined Eevee; separate from and preserving the earlier starter collection."""
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

OUT=h.setup('Eevee')
BROWN='B77B40';CREAM='F2E2B4';INNER='654020';INK='2B211B';IRIS='805027'


def fur(name,base,tip,width,depth,color):
    a,b=Vector(base),Vector(tip)
    return h.tube('Eevee | '+name,[a,a.lerp(b,.35),a.lerp(b,.72),b],
                  [(width*.82,depth*.70),(width,depth),(width*.48,depth*.48),(.0025,.0025)],
                  color,sides=32,steps=12)


def soft_union(name,objects,color,voxel=.012):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();obj=bpy.context.object
    mod=obj.modifiers.new('Continuous soft fur roots','REMESH');mod.mode='VOXEL';mod.voxel_size=voxel;h.apply(obj,mod)
    mod=obj.modifiers.new('Soft fur polish','SMOOTH');mod.factor=.43;mod.iterations=4;h.apply(obj,mod)
    mod=obj.modifiers.new('Soft silhouette','SUBSURF');mod.levels=1;h.apply(obj,mod)
    return h.finish(obj,name,color)


def ear(name,points,widths):
    """Closed ear with an actually recessed inner surface and raised outer rim."""
    path=h.catmull(points,20);rr=h.catmull([(w,d,0) for w,d in widths],20)
    count=len(path);across=24;stride=across+1;verts=[];faces=[];tags=[]
    for back in (False,True):
        for i,p in enumerate(path):
            tangent=(path[min(i+1,count-1)]-path[max(i-1,0)]).normalized()
            u=Vector((tangent.z,0,-tangent.x)).normalized()
            for j in range(across+1):
                q=-1+2*j/across
                y=rr[i].y*.55 if back else -rr[i].y*.78+rr[i].y*.80*(1-q*q)
                verts.append(p+u*max(.002,rr[i].x)*q+Vector((0,y,0)))
    total=count*stride
    for back in (0,1):
        base=back*total
        for i in range(count-1):
            for j in range(across):
                a=base+i*stride+j;faces.append((a,a+1,a+1+stride,a+stride))
                t=(i+.5)/(count-1);q=-1+2*(j+.5)/across
                inner=back==0 and abs(q)<.79 and .10<t<.95
                tags.append(1 if inner else 0)
    for i in range(count-1):
        for j in (0,across):
            a=i*stride+j;b=(i+1)*stride+j;faces.append((a,b,b+total,a+total));tags.append(0)
    for i in (0,count-1):
        for j in range(across):
            a=i*stride+j;faces.append((a,a+1,a+1+total,a+total));tags.append(0)
    obj=h.mesh('Eevee | '+name,verts,faces,BROWN)
    obj.data.materials.append(h.material(INNER));obj.data.materials.append(h.material('35291E'))
    for p,index in zip(obj.data.polygons,tags):p.material_index=index
    mod=obj.modifiers.new('Rounded ear rim','SUBSURF');mod.levels=1;h.apply(obj,mod)
    return obj


def tail_material(tail,rows,sides):
    res=2048
    vv,uu=np.mgrid[0:res,0:res].astype(np.float32)/(res-1);t=1-vv
    theta=uu*2*math.pi
    wave=2/np.pi*np.arcsin(np.sin(theta*6+.8))
    boundary=.715+.042*wave+.018*np.sin(theta*3)
    mask=np.clip((t-boundary)/.0025+.5,0,1)
    def rgb(c):return np.array([int(c[i:i+2],16) for i in (0,2,4)],np.float32)
    pixels=(rgb(BROWN)*(1-mask[...,None])+rgb(CREAM)*mask[...,None]).astype(np.uint8)
    def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',res,res,8,2,0,0,0))
    raw+=chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in pixels)))+chunk(b'IEND',b'')
    tex=OUT/'Textures';tex.mkdir(exist_ok=True);path=tex/'Eevee_tail_tip.png';path.write_bytes(raw)
    image=bpy.data.images.load(str(path));image.pack()
    mat=bpy.data.materials.new('Eevee | jagged cream tail tip');mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.55;shader.inputs['Specular IOR Level'].default_value=.24
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
    mat.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
    tail.data.materials.clear();tail.data.materials.append(mat)
    uv=tail.data.uv_layers.new(name='Continuous tail marking UV')
    for face in tail.data.polygons:
        values=[]
        for loopindex in face.loop_indices:
            index=tail.data.loops[loopindex].vertex_index
            if index>=rows*sides:values.append((.5,0 if index==rows*sides else 1))
            else:values.append(((index%sides)/sides,(index//sides)/(rows-1)))
        seam=max(u for u,v in values)-min(u for u,v in values)>.5
        for index,(u,v) in zip(face.loop_indices,values):uv.data[index].uv=(u+1 if seam and u<.5 else u,v)


# Compact body with short paws, broad cheeks, and a modest feline muzzle.
parts=[h.ell('Body',(0,.22,.72),(.37,.57,.36),BROWN),
       h.ell('Brown neck',(0,-.19,1.05),(.245,.26,.30),BROWN),
       h.ell('Head',(0,-.50,1.48),(.49,.37,.47),BROWN),
       h.ell('Broad cheeks',(0,-.59,1.33),(.455,.30,.29),BROWN),
       h.ell('Soft muzzle',(0,-.79,1.25),(.28,.16,.14),BROWN)]
for s in (-1,1):
    parts.append(h.tube('Front leg',[(s*.20,-.12,.78),(s*.20,-.18,.44),(s*.20,-.21,.16)],
                        [(.135,.15),(.12,.14),(.10,.12)],BROWN))
    parts.append(h.ell('Front paw',(s*.20,-.27,.085),(.14,.215,.085),BROWN))
    parts.append(h.ell('Hind haunch',(s*.24,.56,.52),(.17,.22,.28),BROWN))
    parts.append(h.tube('Rear ankle',[(s*.25,.58,.50),(s*.26,.60,.28),(s*.26,.54,.13)],
                        [(.13,.15),(.095,.12),(.10,.11)],BROWN))
    parts.append(h.ell('Rear paw',(s*.26,.46,.075),(.13,.20,.075),BROWN))
skin=h.union('Eevee | continuous brown skin',parts,BROWN,.013)

# Small crown points break the forehead silhouette without oversized spikes.
crown=[]
heights=(.08,.13,.11,.16,.10,.12,.07)
leans=(-.015,-.020,.010,.025,.030,.020,.040)
for i,x in enumerate((-.27,-.18,-.09,0,.09,.18,.27)):
    z=1.91-.07*(abs(x)/.27)**2
    crown.append(fur('little crown tuft '+str(i),(x,-.46,z),(x+leans[i],-.435,z+heights[i]),.055,.042,BROWN))
skin=soft_union('Eevee | continuous brown skin and crown',[skin,*crown],BROWN,.011)

# One upright and one outward ear reproduce the official asymmetrical alert pose.
ear('upright left ear',[(-.31,-.46,1.79),(-.48,-.43,2.14),(-.58,-.39,2.49),(-.70,-.35,2.88)],
    [(.075,.060),(.195,.070),(.145,.052),(.0025,.003)])
ear('outward right ear',[(.31,-.46,1.79),(.60,-.42,2.04),(.90,-.36,2.25),(1.22,-.30,2.45)],
    [(.075,.060),(.20,.070),(.15,.052),(.0025,.003)])

# A generous cream collar with a pointed front bib and many soft lower fur tips.
ruff=[h.ell('Ruff ring',(0,-.17,1.105),(.565,.43,.285),CREAM),
      h.ell('Front chest fluff',(0,-.47,.99),(.39,.27,.32),CREAM)]
for i in range(12):
    a=2*math.pi*i/12
    base=(.35*math.cos(a),-.17+.27*math.sin(a),1.10)
    tip=(.60*math.cos(a),-.17+.44*math.sin(a),.91-.10*(1-math.sin(a))*.5)
    ruff.append(fur('collar tuft '+str(i),base,tip,.13,.10,CREAM))
for i,(x,z) in enumerate(((-.28,.77),(-.15,.67),(0,.565),(.15,.67),(.28,.77))):
    ruff.append(fur('front bib point '+str(i),(x*.75,-.47,1.04),(x,-.47,z),.12,.11,CREAM))
for i,x in enumerate((-.25,0,.25)):
    low=.57 if i==1 else .75
    width=.22 if i==1 else .18
    ruff.append(h.tube('Eevee | deep front ruff lobe '+str(i),[(x*.7,-.52,1.18),(x,-.68,1.00),(x,-.66,.83),(x,-.54,low)],
                       [(width*.75,.12),(width,.15),(width*.66,.12),(.003,.003)],CREAM,sides=40,steps=14))
soft_union('Eevee | continuous fluffy cream collar',ruff,CREAM,.012)

# Large raised brush tail, with its painted cream zigzag continuing all around it.
tail_points=[(0,.62,.76),(.065,.94,.88),(.15,1.25,1.08),(.26,1.48,1.43),(.40,1.57,1.82)]
tail=h.tube('Eevee | bushy raised tail',tail_points,
            [(.135,.13),(.285,.24),(.36,.30),(.255,.24),(.003,.003)],BROWN,sides=96,steps=28,width_axis=(1,0,0))
tail_material(tail,len(h.catmull(tail_points,28)),96)

# Warm brown lower irises under deep pupils; single bright artwork catchlight.
for s in (-1,1):
    x=s*.215;z=1.485
    h.paint('Eevee | eye edge '+str(s),skin,h.circle(x,z,.108,.185,s*-7),INK,depth=.004)
    h.paint('Eevee | warm brown iris '+str(s),skin,h.circle(x,z-.046,.092,.128,s*-7),IRIS,depth=.007)
    h.paint('Eevee | deep pupil '+str(s),skin,h.circle(x,z+.022,.079,.145,s*-7),'141311',depth=.010)
    h.paint('Eevee | eye highlight '+str(s),skin,h.circle(x-s*.027,z+.096,.026,.039,s*-7),'FFFFFF',depth=.013)
    for dx in (-.04,.04):
        h.line('Eevee | front paw toe crease',[(s*.20+dx,-.468,.064),(s*.20+dx,-.46,.092),(s*.20+dx,-.44,.116)],'8C5C32',.0035)
        h.line('Eevee | rear paw toe crease',[(s*.26+dx,.272,.056),(s*.26+dx,.28,.084),(s*.26+dx,.30,.103)],'8C5C32',.0035)

h.ell('Eevee | little nose',(0,-.940,1.295),(.033,.018,.019),INK)
bpy.context.view_layer.update();bv=BVHTree.FromObject(skin,bpy.context.evaluated_depsgraph_get())
mouth=[]
for x,z in [(-.145,1.225),(-.085,1.200),(0,1.216),(.085,1.200),(.145,1.225)]:
    p,n,_,_=bv.ray_cast(skin.matrix_world.inverted()@Vector((x,-6,z)),Vector((0,1,0)),15)
    mouth.append(skin.matrix_world@p+n*.004)
h.line('Eevee | gentle smile',mouth,INK,.0045)

h.stage();h.save_export()
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if '--draft' in args:h.render(('hero','front','side'),True)
if '--all' in args:h.render(('hero','front','side','back','clay'))
if not h.validate()['passed']:raise RuntimeError('Eevee validation failed')
