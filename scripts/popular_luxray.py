"""Reference-led Luxray model with sculpted black mane and four-point tail star."""
import sys
import math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import eeveelutions_helpers as h

OUT=h.setup('Luxray')
BLACK='282C32';BLUE='54ACD2';GOLD='F7CF32';RED='D63442';INK='141B23'


def fur(name,base,tip,width,depth,bend=(0,0,0)):
    a,b=Vector(base),Vector(tip);offset=Vector(bend)
    return h.tube('Luxray | '+name,[a,a.lerp(b,.32)+offset,a.lerp(b,.68)+offset*.6,b],
                  [(width,depth*.55),(width*.82,depth*.72),(width*.44,depth*.40),(.0025,.0025)],
                  BLACK,sides=40,steps=16,width_axis=(1,0,0))


def rectangle(cx,z,rx,rz):
    corners=[(cx-rx,z-rz),(cx+rx,z-rz),(cx+rx,z+rz),(cx-rx,z+rz)]
    out=[]
    for i,a in enumerate(corners):
        b=corners[(i+1)%4]
        for j in range(8):out.append((a[0]+(b[0]-a[0])*j/8,a[1]+(b[1]-a[1])*j/8))
    return out


def almond(cx,z,rx,rz,side,n=96):
    out=[]
    for j in range(n):
        a=j*2*math.pi/n;x=rx*math.cos(a);q=math.sin(a)
        zz=rz*q*abs(q)**.5*(.76 if q>0 else 1)+side*x*.24
        out.append((cx+x,z+zz))
    return out


def fuse_black(name,objects,voxel=.013):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();obj=bpy.context.object
    mod=obj.modifiers.new('Continuous fur roots','REMESH');mod.mode='VOXEL';mod.voxel_size=voxel;h.apply(obj,mod)
    mod=obj.modifiers.new('Polished fur surfaces','SMOOTH');mod.factor=.42;mod.iterations=3;h.apply(obj,mod)
    mod=obj.modifiers.new('Smooth pointed silhouette','SUBSURF');mod.levels=1;h.apply(obj,mod)
    return h.finish(obj,name,BLACK)


# Blue torso and bent hind limbs are continuous underneath the black fur mantle.
blueparts=[h.ell('Blue torso',(0,.18,1.04),(.32,.64,.32),BLUE)]
for s in (-1,1):
    blueparts.append(h.ell('Hind thigh',(s*.22,.60,.85),(.18,.25,.31),BLUE))
    blueparts.append(h.tube('Hind leg',[(s*.23,.60,.91),(s*.28,.51,.57),(s*.27,.77,.28),(s*.27,.72,.12)],
                            [(.15,.17),(.13,.135),(.085,.09),(.085,.095)],BLUE))
    blueparts.append(h.ell('Rear paw',(s*.27,.61,.085),(.135,.215,.085),BLUE))
bluebody=h.union('Luxray | continuous blue torso and hind legs',blueparts,BLUE,.016)
bluebody.data.materials.append(h.material(BLACK))
for poly in bluebody.data.polygons:
    p=bluebody.matrix_world@poly.center
    blue_waist=(-.05<p.y<.38 and .98+.35*p.y<p.z<1.34-.50*p.y and abs(p.x)>.15)
    covered=(p.y<.40 and p.z>.62) or (p.y>=.40 and p.z>.94)
    if covered and not blue_waist:poly.material_index=1

# The front legs lean forward, with black paws and blue/gold inner shin markings.
forelegs=[]
for s in (-1,1):
    leg=h.union('Luxray | '+str(s)+' black foreleg',[
        h.tube('Foreleg',[(s*.10,-.33,1.28),(s*.225,-.50,.89),(s*.25,-.65,.47),(s*.26,-.74,.13)],
               [(.13,.145),(.12,.13),(.09,.10),(.095,.10)],BLACK),
        h.ell('Black front paw',(s*.26,-.84,.085),(.14,.235,.085),BLACK)],BLACK,.014)
    forelegs.append(leg)
    panel=[(s*.24-.060,1.035),(s*.24+.060,1.035),(s*.25+.060,.39),
           (s*.25+.048,.29),(s*.25+.010,.35),(s*.25-.035,.285),(s*.25-.055,.39)]
    h.paint('Luxray | blue shin panel '+str(s),leg,panel,BLUE,depth=.006,rings=16)
    for i,z in enumerate((.48,.65,.82,.99)):
        h.paint('Luxray | yellow shin bar '+str(s)+' '+str(i),leg,rectangle(s*.245,z,.061,.031),GOLD,depth=.010,rings=8)
    # Paw toes are suggested by tiny sculpted crease lines, without white claws.
    for dx in (-.045,.045):
        h.line('Luxray | front toe crease',[(s*.26+dx,-1.054,.066),(s*.26+dx,-1.044,.095),(s*.26+dx,-1.02,.12)],INK,.004)
        h.line('Luxray | rear toe crease',[(s*.27+dx,.410,.062),(s*.27+dx,.418,.087),(s*.27+dx,.44,.112)],'3D86AA',.004)

# Full chest and back-of-head understructure keeps fur roots attached and dense.
h.union('Luxray | black chest and mane core',[
    h.ell('Neck',(0,-.36,1.40),(.31,.32,.43),BLACK),
    h.ell('Mane core',(0,-.40,1.91),(.47,.34,.44),BLACK),
    h.ell('Upper chest',(0,-.33,1.16),(.32,.32,.31),BLACK)],BLACK,.017)

# Large flame-shaped mane locks, characteristic of the original silhouette.
for s in (-1,1):
    fur('upper side crown '+str(s),(s*.245,-.35,2.10),(s*.63,-.20,2.77),.245,.16,(s*.035,0,.015))
    fur('outer swept mane '+str(s),(s*.33,-.32,1.98),(s*.79,.005,2.37),.24,.145,(s*.04,.02,0))
    fur('cheek mane '+str(s),(s*.36,-.31,1.79),(s*.70,.11,1.91),.20,.13,(s*.02,.02,.01))
    fur('upper chest lock '+str(s),(s*.20,-.25,1.49),(s*.58,.20,1.55),.215,.14,(s*.02,0,.02))
    fur('lower chest lock '+str(s),(s*.18,-.22,1.24),(s*.54,.20,1.12),.19,.10,(s*.015,0,0))
fur('pointed chest bib',(0,-.50,1.50),(0,-.48,.90),.235,.16,(0,-.025,0))

# Black hindquarter mantle and the three prominent backward rump points.
h.ell('Luxray | black rump mantle',(0,.61,1.075),(.345,.35,.34),BLACK)
for s in (-1,1):
    h.ell('Luxray | full black haunch coat '+str(s),(s*.23,.62,.94),(.23,.30,.34),BLACK)
    fur('haunch drape '+str(s),(s*.23,.53,1.04),(s*.32,.54,.51),.22,.15,(s*.02,-.01,0))
    fur('outer rump spike '+str(s),(s*.18,.78,1.18),(s*.58,1.06,1.32),.16,.11,(s*.02,.02,0))
    fur('lower outer rump spike '+str(s),(s*.20,.84,1.02),(s*.55,1.15,.94),.15,.11,(s*.02,.015,0))
fur('upper rump spike',(0,.74,1.21),(0,1.08,1.73),.17,.13,(0,.015,.015))
fur('middle rump spike',(0,.81,1.15),(0,1.44,1.42),.22,.15,(0,.025,0))
fur('lower rump spike',(0,.83,1.04),(0,1.44,1.08),.20,.14,(0,.025,-.005))

# Blue lower face with pointed central black fringe. Eyes remain visible outside it.
face=h.union('Luxray | blue face',[
    h.ell('Blue face',(0,-.70,1.76),(.29,.30,.30),BLUE),
    h.ell('Blue muzzle',(0,-.93,1.49),(.16,.14,.095),BLUE),
    h.ell('Blue lower jaw',(0,-.86,1.435),(.17,.15,.07),BLUE)],BLUE,.012)
for s in (-1,1):
    x=s*.17;z=1.762
    h.paint('Luxray | black eye edge '+str(s),face,almond(x,z,.104,.085,s),INK,depth=.004)
    h.paint('Luxray | golden sclera '+str(s),face,almond(x,z,.093,.073,s),GOLD,depth=.007)
    h.paint('Luxray | red iris '+str(s),face,h.circle(x+s*.022,z,.040,.064,s*10),RED,depth=.010)
    h.paint('Luxray | dark slit pupil '+str(s),face,h.circle(x+s*.023,z,.012,.052,s*10),INK,depth=.013)
    h.paint('Luxray | eye glint '+str(s),face,h.circle(x+s*.009,z+.034,.014,.018),'FFF9D9',depth=.016)
    ear=h.ell('Luxray | blue ear '+str(s),(s*.365,-.724,2.18),(.16,.045,.235),BLUE,(0,s*27,0))
    h.ell('Luxray | golden ear '+str(s),(s*.365,-.771,2.18),(.100,.011,.163),GOLD,(0,s*27,0))

h.tube('Luxray | long central crown and forehead fringe',[(0,-.25,2.91),(0,-.35,2.59),(0,-.60,2.28),
       (0,-.84,2.06),(0,-.982,1.80),(0,-1.055,1.535)],
       [(.003,.003),(.20,.090),(.27,.095),(.23,.065),(.13,.040),(.004,.004)],BLACK,sides=48,steps=20)
h.paint('Luxray | red nose',face,[(-.025,1.529),(.025,1.529),(0,1.495)],'A93649',depth=.008,rings=8)

bpy.context.view_layer.update();bv=BVHTree.FromObject(face,bpy.context.evaluated_depsgraph_get())
mouth=[]
for x,z in [(-.095,1.445),(-.052,1.413),(0,1.409),(.052,1.413),(.095,1.445)]:
    p,n,_,_=bv.ray_cast(face.matrix_world.inverted()@Vector((x,-6,z)),Vector((0,1,0)),15)
    mouth.append(face.matrix_world@p+n*.005)
h.line('Luxray | mouth',mouth,INK,.0045)

# A continuous fur surface avoids separate cone caps at the roots of the locks.
head_fur=[o for o in h.COL.objects if o.type=='MESH' and any(word in o.name for word in ('mane','crown','chest','fringe','forehead bridge','black foreleg'))]
fuse_black('Luxray | unified black mane and forelegs',head_fur,.013)
rump_fur=[o for o in h.COL.objects if o.type=='MESH' and any(word in o.name for word in ('rump','haunch'))]
fuse_black('Luxray | unified rump mantle and fur points',rump_fur,.014)

# A modest forward pitch gives the vigilant, slightly lowered feline head pose.
for obj in h.COL.objects:
    if obj.type!='MESH' or any(word in obj.name for word in ('torso','shin','toe','rump','haunch')):continue
    world=obj.matrix_world;inverse=world.inverted()
    for vertex in obj.data.vertices:
        p=world@vertex.co
        angle=math.radians(8)*max(0,min(1,(p.z-1.15)/.4))
        y,z=p.y+.45,p.z-1.45
        p.y=y*math.cos(angle)-z*math.sin(angle)-.45
        p.z=y*math.sin(angle)+z*math.cos(angle)+1.45
        vertex.co=inverse@p
    obj.data.update()

# Thin arched tail, ending in the four-pointed gold star seen in official artwork.
h.tube('Luxray | arched black tail',[(0,.85,1.18),(.015,1.05,1.48),(.03,1.35,1.76),(.045,1.70,1.83),
       (.035,1.97,1.62),(.015,1.96,1.29),(0,1.91,1.06),(-.02,1.98,.88)],
       [.045,.044,.042,.041,.038,.036,.034,.030],BLACK,sides=32,steps=18)
center=Vector((-.02,1.98,.78));outline=[]
for j in range(8):
    angle=math.radians(23)+j*math.pi/4;r=.285 if j%2==0 else .105
    outline.append((center.x+r*math.cos(angle),center.z+r*math.sin(angle)))
verts=[(x,center.y+y,z) for y in (-.045,.045) for x,z in outline]
faces=[tuple(range(7,-1,-1)),tuple(range(8,16))]+[(j,(j+1)%8,(j+1)%8+8,j+8) for j in range(8)]
star=h.mesh('Luxray | four point golden tail star',verts,faces,GOLD)
mod=star.modifiers.new('Soft star edges','BEVEL');mod.width=.022;mod.segments=4;h.apply(star,mod)

h.stage();h.save_export()
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if '--draft' in args:h.render(('hero','front','side'),True)
if '--all' in args:h.render(('hero','front','side','back','clay'))
if not h.validate()['passed']:raise RuntimeError('Luxray validation failed')
