"""Editable Sylveon fan model, based on official dex #700 illustration.

The ribbons are closed, thin, flattened meshes with coloured distal bands.
"""
import sys
import math
import struct
import zlib
import numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
from mathutils import Vector
import eeveelutions_helpers as h

OUT=h.setup('Sylveon')
CREAM='F4F3EF';PINK='E99AB5';PINKD='E28EAC';BLUE='5F8BC6';CYAN='67C7E0';INK='334957'


def smooth_loop(points,steps=8):
    pp=[Vector(p) for p in points];out=[]
    for i in range(len(pp)):
        a,b,c,d=pp[(i-1)%len(pp)],pp[i],pp[(i+1)%len(pp)],pp[(i+2)%len(pp)]
        for j in range(steps):
            t=j/steps
            out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return out


def pillow(name,outline,y,thickness,color,center=None):
    """Closed softly domed bow petal; outline lies in the XZ plane."""
    outline=smooth_loop([(x,z,0) for x,z in outline],8)
    n=len(outline);rings=10
    cx=sum(p.x for p in outline)/n;cz=sum(p.y for p in outline)/n
    verts=[];faces=[]
    for side in (-1,1):
        verts.append((cx,y+side*thickness,cz))
        for r in range(1,rings+1):
            t=r/rings
            for p in outline:
                verts.append((cx+(p.x-cx)*t,y+side*(thickness*.20+thickness*.8*math.sqrt(max(0,1-t*t))),cz+(p.y-cz)*t))
    count=1+n*rings
    for k in (0,count):
        for j in range(n):faces.append((k,k+1+j,k+1+(j+1)%n))
        for r in range(rings-1):
            for j in range(n):
                a=k+1+r*n+j;b=k+1+r*n+(j+1)%n
                faces.append((a,b,b+n,a+n))
    last=1+(rings-1)*n
    for j in range(n):
        a=last+j;b=last+(j+1)%n
        faces.append((a,b,b+count,a+count))
    return h.mesh(name,verts,faces,color)


def ribbon(name,points,widths,face_tip=False):
    """Ribbon with a shallow forked tip and continuous, flat colour bands."""
    path=h.catmull(points,16);ww=h.catmull([(w,0,0) for w in widths],16)
    cross=12;verts=[];faces=[];ts=[]
    frames=[];previous=None
    for i,p in enumerate(path):
        tangent=(path[min(i+1,len(path)-1)]-path[max(i-1,0)]).normalized()
        u=(Vector((tangent.z,0,-tangent.x)) if previous is None else previous-tangent*previous.dot(tangent))
        u.normalize()
        t=i/(len(path)-1)
        if face_tip and t>.65:
            desired=Vector((1,0,0));desired=(desired-tangent*desired.dot(tangent)).normalized()
            if desired.dot(u)<0:desired=-desired
            u=u.lerp(desired,((t-.65)/.35)**2).normalized()
        n=tangent.cross(u).normalized();previous=u
        frames.append((tangent,u,n))
    for side in (-1,1):
        for i,p in enumerate(path):
            tangent,u,n=frames[i]
            for j in range(cross+1):
                q=-1+2*j/cross
                notch=(i/(len(path)-1))**24*.10*abs(q)**1.4
                pos=p+u*ww[i].x*q+tangent*notch+n*side*(.009+.004*(1-q*q))
                verts.append(pos)
    rows=len(path);stride=cross+1;count=rows*stride
    for side in range(2):
        k=side*count
        for i in range(rows-1):
            for j in range(cross):
                a=k+i*stride+j;faces.append((a,a+1,a+1+stride,a+stride));ts.append((i+.5)/(rows-1))
    for i in range(rows-1):
        for j in (0,cross):
            a=i*stride+j;b=(i+1)*stride+j
            faces.append((a,b,b+count,a+count));ts.append((i+.5)/(rows-1))
    for i in (0,rows-1):
        for j in range(cross):
            a=i*stride+j;faces.append((a,a+1,a+1+count,a+count));ts.append(i/(rows-1))
    obj=h.mesh(name,verts,faces,CREAM)
    for col in (PINK,BLUE,CYAN):obj.data.materials.append(h.material(col))
    for poly,t in zip(obj.data.polygons,ts):
        poly.material_index=3 if t>.92 else 2 if t>.855 else 1 if t>.78 else 0
    return obj


# Slender quadruped anatomy. The head is large, with broad, softly pointed cheeks.
parts=[h.ell('Body',(0,.14,.88),(.32,.62,.31),CREAM),
       h.ell('Chest',(0,-.31,.95),(.255,.30,.37),CREAM),
       h.ell('Neck',(0,-.43,1.26),(.21,.25,.36),CREAM),
       h.ell('Head',(0,-.58,1.67),(.405,.32,.38),CREAM),
       h.ell('Cheeks',(0,-.66,1.54),(.385,.265,.25),CREAM),
       h.ell('Muzzle',(0,-.83,1.48),(.22,.145,.12),CREAM)]
for s in (-1,1):
    parts.append(h.tube('Foreleg',[(s*.16,-.31,1.02),(s*.22,-.37,.77),(s*.24,-.43,.41),(s*.25,-.49,.16)],
                        [(.13,.14),(.12,.12),(.08,.085),(.073,.08)],CREAM))
    parts.append(h.ell('Forepaw',(s*.25,-.54,.08),(.10,.165,.08),CREAM))
    parts.append(h.ell('Haunch',(s*.21,.55,.81),(.17,.25,.27),CREAM))
    parts.append(h.tube('Hind leg',[(s*.22,.59,.85),(s*.255,.42,.55),(s*.26,.65,.30),(s*.26,.60,.12)],
                        [(.14,.16),(.115,.13),(.068,.075),(.066,.075)],CREAM))
    parts.append(h.ell('Hind paw',(s*.26,.53,.065),(.09,.155,.065),CREAM))
skin=h.union('Sylveon | continuous cream skin',parts,CREAM,.017)

# Stocking colour is on the continuous skin, without raised shoe-like overlays.
skin.data.materials.append(h.material(PINKD))
for poly in skin.data.polygons:
    p=skin.matrix_world@poly.center
    if p.z<(.315 if p.y<0 else .20):poly.material_index=1

# Large pink ears with inset blue inner panels and pointed flared silhouettes.
ears=[]
for s in (-1,1):
    tip=(s*.77,-.46,2.68 if s>0 else 2.75)
    ear_points=[(s*.27,-.54,1.92),(s*.38,-.51,2.18),(s*.57,-.48,2.44),tip]
    ear=h.tube('Sylveon | pink ear '+str(s),ear_points,
               [(.13,.086),(.205,.070),(.16,.045),(.0025,.0025)],PINK,
               sides=56,steps=18)
    # Two soft indents on the outer rim reproduce the illustrated notched ears.
    path=h.catmull(ear_points,18)
    for i,p in enumerate(path):
        tangent=(path[min(i+1,len(path)-1)]-path[max(i-1,0)]).normalized()
        u=Vector((1,0,0));u=(u-tangent*u.dot(tangent)).normalized()
        t=i/(len(path)-1)
        notch=.32*math.exp(-((t-.64)/.035)**2)+.17*math.exp(-((t-.82)/.028)**2)
        for j in range(56):
            vertex=ear.data.vertices[i*56+j]
            width=(vertex.co-p).dot(u)
            if width*s>0:vertex.co-=u*width*notch
    inner=h.tube('Sylveon | blue ear inset '+str(s),[(s*.29,-.624,2.015),(s*.40,-.585,2.205),(s*.565,-.528,2.435),(s*.69,-.486,2.57 if s>0 else 2.62)],
                 [(.025,.009),(.105,.011),(.085,.009),(.0025,.0025)],BLUE,
                 sides=40,steps=16)
    ears.append(ear)

# Pink cap follows the head's upper surface; its scalloped boundary frames the eyes.
skin.data.materials.append(h.material(PINK))
for poly in skin.data.polygons:
    p=skin.matrix_world@poly.center
    if p.z>1.73+.21*min(1,abs(p.x)/.30):poly.material_index=2
for i,(base,tip) in enumerate([
    ((-.32,-.51,1.93),(-.51,-.50,2.00)),
    ((-.34,-.50,1.98),(-.53,-.48,2.08)),
    ((-.30,-.48,2.02),(-.43,-.46,2.16))]):
    mid=tuple((a+b)/2 for a,b in zip(base,tip))
    h.tube('Sylveon | crown fur point '+str(i),[base,mid,tip],[(.06,.03),(.045,.022),(.003,.003)],PINK,sides=32,steps=10)

# A packed, antialiased surface texture makes the V cap and stockings smooth at
# close range. The original illustration is not used as a texture.
def skin_texture():
    resolution=2048;zmax=2.25
    vv,uu=np.mgrid[0:resolution,0:resolution].astype(np.float32)/(resolution-1)
    z=zmax*(1-vv);angle=(uu-.5)*2*math.pi
    radius=.405*np.sqrt(np.maximum(0,1-((z-1.67)/.38)**2))
    x=radius*np.sin(angle)
    cap_boundary=1.73+.21*np.minimum(1,np.abs(x)/.30)
    cap=np.clip((z-cap_boundary)/.0025+.5,0,1)
    foot_boundary=np.where(np.cos(angle)>0,.315,.20)
    feet=np.clip((foot_boundary-z)/.0025+.5,0,1)
    def rgb(value):return np.array([int(value[i:i+2],16) for i in (0,2,4)],dtype=np.float32)
    pixels=np.broadcast_to(rgb(CREAM),(resolution,resolution,3)).copy()
    pixels=pixels*(1-cap[...,None])+rgb(PINK)*cap[...,None]
    pixels=pixels*(1-feet[...,None])+rgb(PINKD)*feet[...,None]
    pixels=np.clip(pixels,0,255).astype(np.uint8)
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',resolution,resolution,8,2,0,0,0))
    raw+=chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in pixels)))+chunk(b'IEND',b'')
    directory=OUT/'Textures';directory.mkdir(exist_ok=True)
    path=directory/'Sylveon_skin.png';path.write_bytes(raw)
    image=bpy.data.images.load(str(path));image.pack()
    mat=bpy.data.materials.new('Sylveon | painted cap and stockings');mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=.53;shader.inputs['Specular IOR Level'].default_value=.24
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image;node.interpolation='Linear'
    mat.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
    skin.data.materials.clear();skin.data.materials.append(mat)
    for face in skin.data.polygons:face.material_index=0
    while skin.data.uv_layers:skin.data.uv_layers.remove(skin.data.uv_layers[0])
    uv=skin.data.uv_layers.new(name='Continuous painted skin UV')
    coords=[]
    for vertex in skin.data.vertices:
        p=skin.matrix_world@vertex.co
        cy=-.58 if p.z>1.3 else 0
        angle=math.atan2(p.x,-(p.y-cy))
        coords.append(((angle+math.pi)/(2*math.pi),p.z/zmax))
    for face in skin.data.polygons:
        values=[coords[skin.data.loops[i].vertex_index] for i in face.loop_indices]
        seam=max(v[0] for v in values)-min(v[0] for v in values)>.5
        for index,(u,v) in zip(face.loop_indices,values):uv.data[index].uv=(u+1 if seam and u<.5 else u,v)
skin_texture()

# The tail has a broad swept blade and two little trailing tips.
tail=h.tube('Sylveon | lifted pink tail',[(0,.64,.97),(.03,.99,1.10),(.06,1.28,1.34),(.10,1.43,1.63),(.14,1.45,1.88)],
            [(.07,.06),(.15,.065),(.16,.055),(.105,.035),(.0025,.0025)],PINK,
            sides=48,steps=18,width_axis=(0,0,1))
h.tube('Sylveon | tail lower fork',[(.05,1.07,1.18),(.10,1.29,1.17),(.16,1.45,1.27)],
       [(.10,.045),(.085,.035),(.0025,.0025)],PINK,sides=40,steps=16,width_axis=(0,0,1))

# Huge blue eyes: light sclera, blue irises, navy edge, drawn highlights.
for s in (-1,1):
    x=s*.195;z=1.655
    h.paint('Sylveon | eye outline '+str(s),skin,h.circle(x,z,.142,.177,s*-13),INK,depth=.004)
    h.paint('Sylveon | eye white '+str(s),skin,h.circle(x,z,.130,.164,s*-13),'FFFFFF',depth=.006)
    h.paint('Sylveon | blue iris '+str(s),skin,h.circle(x+s*.013,z+.002,.091,.143,s*-8),CYAN,depth=.008)
    h.paint('Sylveon | iris depth '+str(s),skin,h.circle(x+s*.021,z+.013,.061,.125,s*-8),'419CC7',depth=.010)
    h.paint('Sylveon | large eye highlight '+str(s),skin,h.circle(x+s*.027,z+.048,.039,.067,s*-8),'FCFFFF',depth=.012)
    h.paint('Sylveon | low eye highlight '+str(s),skin,h.circle(x-s*.015,z-.088,.021,.016),'B7E8F2',depth=.014)
h.ell('Sylveon | little nose',(0,-.967,1.49),(.028,.018,.017),INK)
h.line('Sylveon | smile',[(-.080,-.930,1.415),(-.037,-.958,1.404),(0,-.967,1.414),(.037,-.958,1.404),(.080,-.930,1.415)],INK,.0055)

# Neck bow: softly folded white butterfly lobes with inset pink wings.
for s in (-1,1):
    outline=[(s*.025,1.265),(s*.10,1.50),(s*.255,1.57),(s*.29,1.45),(s*.24,1.24),(s*.11,1.17)]
    pillow('Sylveon | neck bow white '+str(s),outline,-1.010,.055,CREAM)
    outline2=[(s*.035,1.28),(s*.105,1.44),(s*.21,1.49),(s*.22,1.38),(s*.18,1.25),(s*.10,1.215)]
    pillow('Sylveon | neck bow pink '+str(s),outline2,-1.068,.012,PINK)
h.ell('Sylveon | neck bow knot',(0,-1.075,1.28),(.075,.054,.09),PINK)
for obj in h.COL.objects:
    if obj.name.startswith('Sylveon | neck bow'):
        obj.location.z-=.15;obj.location.y+=.30

# Ear bow: asymmetric two-lobed bow attached at the left ear root.
pillow('Sylveon | ear bow upright',[(.21,1.975),(.135,2.15),(.18,2.36),(.26,2.38),(.35,2.19),(.34,2.01)],-.645,.045,CREAM)
pillow('Sylveon | ear bow outer',[(.29,1.99),(.43,2.15),(.64,2.18),(.68,2.12),(.55,1.97),(.37,1.94)],-.65,.043,CREAM)
pillow('Sylveon | ear bow pink upright',[(.235,2.02),(.20,2.15),(.235,2.25),(.29,2.14),(.30,2.035)],-.696,.010,PINK)
pillow('Sylveon | ear bow pink outer',[(.345,1.995),(.455,2.10),(.57,2.12),(.52,2.025),(.395,1.98)],-.70,.010,PINK)
h.ell('Sylveon | ear bow knot',(.31,-.715,2.005),(.070,.043,.067),PINK)

# Four long sensory feelers. Their white/pink/blue/cyan bands continue around edges.
ribbon('Sylveon | ear feeler swept right',[(.34,-.62,2.0),(.67,-.52,1.98),(1.00,-.43,2.15),(1.18,-.40,2.35),(1.35,-.39,2.43)],
       [.075,.090,.095,.095,.10])
ribbon('Sylveon | ear feeler over crown',[(.24,-.35,2.03),(-.05,-.28,1.95),(-.40,-.30,2.13),(-.62,-.60,2.42),(-.53,-.65,2.72),(-.30,-.62,2.96)],
       [.065,.085,.095,.10,.10,.11])
ribbon('Sylveon | neck feeler low curl',[(-.025,-.715,1.14),(-.35,-.75,1.01),(-.49,-.84,.78),(-.45,-.71,.46),(-.25,-.79,.30)],
       [.066,.085,.09,.095,.10])
ribbon('Sylveon | neck feeler high curl',[(.02,-.715,1.14),(.36,-.65,1.10),(.62,-.35,1.45),(.56,.35,1.40),(.44,.82,1.15),(.42,.95,.65),(.32,.90,.28)],
       [.07,.085,.09,.095,.095,.10,.10],face_tip=True)

h.stage()
h.save_export()
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if '--draft' in args:h.render(('hero','front','side'),True)
if '--all' in args:h.render(('hero','front','side','back','clay'))
h.validate()
