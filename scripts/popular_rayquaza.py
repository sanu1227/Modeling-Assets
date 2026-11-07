"""Rayquaza in a curved aerial pose, with editable fins, claws and painted armor."""
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
import popular_tools as p
from popular_tools import c

NAME='Rayquaza'
col,out=p.initialize(NAME)
GREEN='388E68'; EDGE='234F3B'; GOLD='EDCE55'; RED='B86476'; IVORY='F4F0DB'


def paint_texture(name,pixels):
    h,w=pixels.shape[:2]
    im=bpy.data.images.new(name,width=w,height=h,alpha=True)
    im.pixels.foreach_set(pixels.ravel());im.filepath_raw=str(out/(name+'.png'));im.file_format='PNG';im.save();im.pack()
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Roughness'].default_value=.57;bs.inputs['Specular IOR Level'].default_value=.25
    tx=mat.node_tree.nodes.new('ShaderNodeTexImage');tx.image=im;mat.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color'])
    return mat


def armor_plate(name,outline,normal,thickness=.045,rim=RED):
    """Closed planar fin with a visible red rim and green inset faces."""
    poly=[Vector(v) for v in outline];normal=Vector(normal).normalized()
    center=sum(poly,Vector())/len(poly)
    inner=[center+(v-center)*.94 for v in poly]
    n=len(poly)
    vertices=[v+normal*thickness/2 for v in poly]+[v+normal*thickness/2 for v in inner]
    vertices += [v-normal*thickness/2 for v in poly]+[v-normal*thickness/2 for v in inner]
    faces=[];indices=[]
    for j in range(n):
        k=(j+1)%n
        faces.extend([(j,k,n+k,n+j),(2*n+k,2*n+j,3*n+j,3*n+k),(j,2*n+j,2*n+k,k)])
        indices.extend([1,1,1])
    faces += [tuple(range(n,2*n)),tuple(range(4*n-1,3*n-1,-1))];indices += [0,0]
    ob=c.mesh(name,vertices,faces,GREEN);ob.data.materials.append(c.material(rim))
    for f,idx in zip(ob.data.polygons,indices):f.material_index=idx;f.use_smooth=False
    mod=ob.modifiers.new('Soft armored edge','BEVEL');mod.width=.012;mod.segments=3;c.apply(ob,mod)
    return ob


def curved_fin(name,base,tangent,radial,normal):
    """A tapered, curved armored blade with real front/back thickness and red rim."""
    vertices=[];faces=[];materials=[];nu,nv=18,24
    for sign in (-1,1):
        for i in range(nu+1):
            u=i/nu
            for j in range(nv+1):
                v=j/nv*2-1
                point=base+radial*(.44*u)+tangent*(v*.32*(1-.34*u)-.07*u)
                point+=normal*(.105*u*u+.025*(1-v*v)*math.sin(math.pi*u)+sign*.018)
                vertices.append(point)
    side=(nu+1)*(nv+1)
    for layer in range(2):
        for i in range(nu):
            for j in range(nv):
                a=layer*side+i*(nv+1)+j;b=a+1
                faces.append((a,b,b+nv+1,a+nv+1) if layer else (a+nv+1,b+nv+1,b,a))
                materials.append(1 if i>=nu-2 or j==0 or j==nv-1 else 0)
    perimeter=list(range(nv+1))+[i*(nv+1)+nv for i in range(1,nu+1)]+[nu*(nv+1)+j for j in range(nv-1,-1,-1)]+[i*(nv+1) for i in range(nu-1,0,-1)]
    for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):faces.append((a,b,b+side,a+side));materials.append(1)
    ob=c.mesh(name,vertices,faces,GREEN);ob.data.materials.append(c.material(RED))
    for f,m in zip(ob.data.polygons,materials):f.material_index=m
    return ob


# A single continuous tube turns through a broad, readable coil in depth.
controls=[(-.55,.24,3.32),(-.08,.31,3.07),(.42,.32,2.59),(.48,.18,2.08),
          (.12,-.03,1.51),(-.58,-.12,1.13),(-1.22,-.02,1.13),(-1.50,.22,1.55),
          (-1.26,.48,1.99),(-.62,.69,2.16),(.14,.84,2.02),(.87,.87,1.61),
          (1.45,.76,1.10),(1.94,.65,.72),(2.35,.60,.47)]
radii=[.245,.285,.30,.295,.29,.275,.25,.235,.22,.20,.18,.155,.13,.10,.012]
path=c.catmull(controls,12)
rr=c.catmull([(r,0,0) for r in radii],12)
arc=[0.]
for a,b in zip(path[:-1],path[1:]):arc.append(arc[-1]+(b-a).length)
total=arc[-1]
frames=[];vertices=[];faces=[];sides=64
for i,point in enumerate(path):
    tangent=(path[min(i+1,len(path)-1)]-path[max(i-1,0)]).normalized()
    normal=Vector((0,-1,0));normal=(normal-tangent*normal.dot(tangent)).normalized()
    side=tangent.cross(normal).normalized();frames.append((tangent,normal,side))
    radius=max(.008,rr[i].x)
    banddist=abs((arc[i]+.24)%.88-.44)
    radius*=1-.04*math.exp(-(banddist/.025)**2)
    for j in range(sides):
        a=j*2*math.pi/sides
        u=math.copysign(abs(math.cos(a))**.93,math.cos(a))
        v=math.copysign(abs(math.sin(a))**.93,math.sin(a))
        vertices.append(point+normal*radius*u+side*radius*v)
for i in range(len(path)-1):
    for j in range(sides):
        a=i*sides+j;b=i*sides+(j+1)%sides;faces.append((a,b,b+sides,a+sides))
start,end=len(vertices),len(vertices)+1;vertices.extend([path[0],path[-1]])
for j in range(sides):
    faces.append((start,(j+1)%sides,j));k=(len(path)-1)*sides
    faces.append((end,k+j,k+(j+1)%sides))
body=c.mesh('01_Continuous coiled armor body',vertices,faces,GREEN)
uv=body.data.uv_layers.new(name='Armor segment paint')
for poly in body.data.polygons:
    js=[body.data.loops[li].vertex_index%sides for li in poly.loop_indices if body.data.loops[li].vertex_index<start]
    wrap=js and max(js)-min(js)>sides/2
    for li in poly.loop_indices:
        idx=body.data.loops[li].vertex_index
        if idx>=start:uv.data[li].uv=(0,0);continue
        row,j=divmod(idx,sides);v=j/sides
        uv.data[li].uv=(arc[row]/total,v+1 if wrap and v<.5 else v)
resx,resy=4096,1024
v,u=np.mgrid[0:resy,0:resx].astype(np.float32);u/=resx-1;v/=resy-1
distance=u*total;phase=(distance+.24)%.88
angle=v*2*math.pi
rgb=lambda h:np.array([int(h[i:i+2],16)/255 for i in (0,2,4)],np.float32)
pixels=np.empty((resy,resx,4),np.float32);pixels[:,:,:3]=rgb(GREEN);pixels[:,:,3]=1
band=np.abs(phase-.44)<.022
pixels[band,:3]=rgb(EDGE)
# Yellow oval circuit markings run along both sides of each body segment.
for ac in (.16,math.pi-.16):
    da=np.arctan2(np.sin(angle-ac),np.cos(angle-ac))
    q=((phase-.0)/.27)**2+(da/.40)**2
    q2=((phase-.88)/.27)**2+(da/.40)**2
    oval=((q>.65)&(q<1))|((q2>.65)&(q2<1))
    pixels[oval&~band,:3]=rgb(GOLD)
    line=(abs(da)<.035)&((phase>.22)&(phase<.66))
    pixels[line&~band,:3]=rgb(GOLD)
body.data.materials.clear();body.data.materials.append(paint_texture('Rayquaza_armor_paint',pixels))

# Four rows of broad armored fins remain independently editable.
for index in (30,64,92,129):
    point=path[index];t,n,s=frames[index];r=rr[index].x
    for sign in (-1,1):
        radial=s*sign
        base=point+radial*r*.74
        curved_fin('02_Curved red-edged body fin',base,t,radial,n)
# Three long tail blades form the characteristic arrow-shaped end.
point=path[-9];t,n,s=frames[-9]
for angle in (0,2*math.pi/3,4*math.pi/3):
    radial=n*math.cos(angle)+s*math.sin(angle)
    fn=t.cross(radial).normalized()
    base=point+radial*.06
    armor_plate('03_Tail vane',[base-t*.25,base+t*.55,base+t*.16+radial*.35,base-t*.22+radial*.22],fn,.025)

before=set(col.objects)
# Angular skull constructed from longitudinal polygon sections, not a round snake head.
sections=[(-1.16,.045,.025,.17),(-.94,.13,.07,.26),(-.67,.24,.12,.35),(-.31,.35,.10,.49),
          (.05,.32,.08,.52),(.30,.22,.06,.36)]
verts=[]
for y,w,bottom,top in sections:
    verts += [(-w,y,bottom),(w,y,bottom),(w*.83,y,top),(-w*.83,y,top)]
faces=[]
for i in range(len(sections)-1):
    for j in range(4):faces.append((i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j))
faces += [(3,2,1,0),tuple(range((len(sections)-1)*4,len(sections)*4))]
skull=c.mesh('04_Angular dragon skull',verts,faces,GREEN)
mod=skull.modifiers.new('Skull edge softness','BEVEL');mod.width=.025;mod.segments=4;c.apply(skull,mod)
for face in skull.data.polygons:face.use_smooth=False
# Dark mouth lining spans a truly open jaw, with pink tongue resting on its base.
mouth=c.mesh('05_Open mouth cavity',[(-.25,-.65,.14),(.25,-.65,.14),(-.27,-.06,.10),(.27,-.06,.10),
                  (-.19,-.73,-.34),(.19,-.73,-.34),(-.23,-.03,-.04),(.23,-.03,-.04)],
                  [(0,2,6,4),(3,1,5,7),(2,3,7,6),(4,6,7,5)],'512D39')
mod=mouth.modifiers.new('Mouth lining thickness','SOLIDIFY');mod.thickness=.012;c.apply(mouth,mod)
jaw=c.tube('06_Lower jaw',[ (0,.08,.04),(0,-.26,-.17),(0,-.79,-.35),(0,-.95,-.28)],
            [(.26,.09),(.25,.075),(.22,.065),(.16,.045)],GREEN,40,10)
pink=c.tube('Pink lower mouth',[(0,-.04,.025),(0,-.28,-.105),(0,-.70,-.275),(0,-.87,-.25)],
            [(.20,.021),(.20,.02),(.17,.018),(.10,.014)],'D993A4',32,8)
for s in (-1,1):
    for j,(yy,zz) in enumerate([(-.66,.12),(-.42,.115),(-.18,.09)]):
        xx=s*(.21 if j==0 else .26)
        c.cone('Ivory upper fang',(xx,yy,zz),(xx*.94,yy-.02,zz-(.11 if j==0 else .085)),.037,IVORY)
    c.cone('Ivory lower fang',(s*.17,-.59,-.27),(s*.17,-.62,-.15),.032,IVORY)
    # Four long head horns, upper pair swept far back; lower pair frames the jaw.
    armor_plate('07_Upper head horn',[(s*.22,.0,.35),(s*.44,.08,.40),(s*.95,.62,1.20),
                                    (s*.59,.29,1.00),(s*.38,.10,.83)],(0,-1,.10),.065,GREEN)
    armor_plate('08_Lower head horn',[(s*.27,.02,.19),(s*.37,.13,.20),(s*.69,.22,-.54),
                                    (s*.46,-.04,-.35)],(0,-1,.10),.065,GREEN)
    # Black eye shape follows the side of the skull, with a small yellow iris.
    verts=[(s*.302,-.62,.23),(s*.350,-.33,.39),(s*.322,-.08,.37),(s*.341,-.32,.23)]
    eye=c.mesh('09_Black angular eye',verts,[tuple(range(4))],'142F2B')
    mod=eye.modifiers.new('Closed eye paint surface','SOLIDIFY');mod.thickness=.007;c.apply(eye,mod)
    c.ell('Yellow iris',(s*.357,-.32,.312),(.009,.040,.042),'F4DB61')
    c.ell('Vertical black pupil',(s*.365,-.329,.315),(.005,.013,.027),'102C27')
    c.ell('Eye reflection',(s*.370,-.340,.331),(.003,.008,.008),'FFFBEA')
    # Small nostrils flank the wedge tip.
    c.ell('Nostril',(s*.135,-.80,.271),(.026,.055,.008),EDGE)
# Forehead V ridge and gold oval crown marking.
for s in (-1,1):
    c.tube('Raised forehead ridge',[(s*.18,-.05,.50),(s*.13,-.35,.47),(s*.025,-.75,.30)],
            [.033,.026,.008],GREEN,20,7)
verts=[];faces=[];nn=80;mm=12
for j in range(nn):
    a=j*2*math.pi/nn
    yy=.025+.16*math.sin(a)
    zz=float(np.interp(yy,[-.31,.05,.30],[.49,.52,.36]))+.010
    point=Vector((.24*math.cos(a),yy,zz))
    normal=Vector((math.cos(a),math.sin(a),0))
    for k in range(mm):
        b=k*2*math.pi/mm;verts.append(point+normal*.018*math.cos(b)+Vector((0,0,.007*math.sin(b))))
for j in range(nn):
    for k in range(mm):faces.append((j*mm+k,((j+1)%nn)*mm+k,((j+1)%nn)*mm+(k+1)%mm,j*mm+(k+1)%mm))
c.mesh('10_Gold forehead ring',verts,faces,GOLD)
for ob in set(col.objects)-before:ob.location+=Vector((-.55,-.10,3.20))

# The two short arms attach below the neck and end in three white talons.
for s in (-1,1):
    shoulder=(.33+s*.21,.02,2.69)
    elbow=(.33+s*.53,-.10,2.29)
    wrist=(.33+s*.50,-.42,2.14)
    parts=[c.ell('Round shoulder pad',shoulder,(.16,.15,.19),GREEN),
           c.tube('Slender bent forelimb',[shoulder,elbow,wrist],[.12,.085,.08],GREEN,32,10),
           c.ell('Three fingered paw',(.33+s*.49,-.48,2.13),(.16,.15,.085),GREEN)]
    arm=c.union('11_Arm and palm',parts,GREEN,.016)
    for j in range(3):
        xx=.33+s*.49+(j-1)*.105
        c.tube('Articulated green finger',[(xx,-.48,2.13),(xx,-.66,2.12),(xx,-.72,2.16)],
               [.064,.052,.032],GREEN,20,5)
        c.tube('Curved ivory hand talon',[(xx,-.68,2.16),(xx,-.79,2.13),(xx,-.85,2.03)],
               [.046,.030,.003],IVORY,20,6)

# Keep the display origin on the lowest tail vane; this is an aerial pose.
bpy.context.view_layer.update()
lo=min((ob.matrix_world@v.co).z for ob in col.objects if ob.type=='MESH' for v in ob.data.vertices)
for ob in col.objects:ob.location.z-=lo
stats=p.save_export(col,NAME,out)
draft='--draft' in sys.argv
p.render_views(NAME,out,stats,['hero','front'] if draft else ['hero','front','side','back','clay'],draft)
p.verify(NAME,out)
