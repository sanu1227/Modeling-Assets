"""Mimikyu: asymmetrical fabric disguise, scribbled face and wooden tail."""
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector, Matrix

sys.path.insert(0,str(Path(__file__).resolve().parent))
import popular_tools as p
from popular_tools import c

NAME='Mimikyu'
col,out=p.initialize(NAME)
col['studio_exposure']=-1.10
TAN='D9CEA0'; INK='292A25'; OCHRE='B97A27'


def cloth_material(mat):
    bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Roughness'].default_value=.92
    bs.inputs['Specular IOR Level'].default_value=.12
    bs.inputs['Sheen Weight'].default_value=.11
    noise=mat.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=190
    bump=mat.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.08;bump.inputs['Distance'].default_value=.008
    mat.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height'])
    mat.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])


def texture(name,pixels):
    h,w=pixels.shape[:2]
    im=bpy.data.images.new(name,width=w,height=h,alpha=True)
    im.pixels.foreach_set(pixels.ravel());im.filepath_raw=str(out/(name+'.png'));im.file_format='PNG';im.save();im.pack()
    mat=bpy.data.materials.new(name);mat.use_nodes=True;cloth_material(mat)
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=im
    mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    return mat


def head_uv(obj):
    uv=obj.data.uv_layers.new(name='Cloth face painting')
    for poly in obj.data.polygons:
        for li in poly.loop_indices:
            v=obj.data.vertices[obj.data.loops[li].vertex_index].co
            on_ear=poly.center.z>.82 or poly.center.x>.78
            uv.data[li].uv=((v.x+1.5)/3,(v.z+.7)/2.5) if poly.normal.y<.15 or on_ear else (.01,.01)


def lathe(name,profile,n=96):
    sampled=c.catmull(profile,8)
    verts=[];faces=[]
    for z,rx,ry in sampled:
        for j in range(n):
            a=j*2*math.pi/n
            wrinkle=.010*math.sin(a*7+z*3)+.006*math.sin(a*13-z*2)
            verts.append(((rx+wrinkle)*math.sin(a),-(ry+wrinkle*.5)*math.cos(a),z))
    for i in range(len(sampled)-1):
        for j in range(n):
            a=i*n+j;b=i*n+(j+1)%n;faces.append((a,b,b+n,a+n))
    start,end=len(verts),len(verts)+1
    verts.extend([(0,0,sampled[0].x),(0,0,sampled[-1].x)])
    for j in range(n):
        faces.append((start,(j+1)%n,j));k=(len(sampled)-1)*n
        faces.append((end,k+j,k+(j+1)%n))
    return c.mesh(name,verts,faces,TAN)


# Build the head around local origin before leaning the entire fabric assembly.
head=lathe('Disguise head cloth',[(-.54,.045,.07),(-.47,.32,.21),(-.28,.53,.29),
     (.00,.62,.32),(.25,.58,.29),(.43,.40,.21),(.52,.10,.08)])
head_parts=[head]
head_parts.append(c.tube('Upright cloth ear',[(-.29,.02,.36),(-.35,.015,.67),(-.35,.02,.95),
                         (-.29,.03,1.20),(-.34,.05,1.34)],[(.18,.11),(.145,.075),(.105,.055),(.08,.035),(.005,.004)],TAN,32,9))
head_parts.append(c.tube('Bent cloth ear',[(.45,.015,.19),(.75,.01,.32),(.99,.025,.34),
                         (1.14,.04,.21),(1.29,.06,.03)],[(.18,.10),(.15,.065),(.14,.055),(.09,.04),(.005,.004)],TAN,32,9))
head=c.union('01_Disguise head and asymmetric ears',head_parts,TAN,.012)
mod=head.modifiers.new('Reduce dense cloth surface','DECIMATE');mod.ratio=.6;c.apply(head,mod)
head_uv(head)

res=3072
v,u=np.mgrid[0:res,0:res].astype(np.float32)/(res-1)
x=u*3-1.5;z=v*2.5-.7
rgb=lambda h:np.array([int(h[i:i+2],16)/255 for i in (0,2,4)],np.float32)
pixels=np.empty((res,res,4),np.float32);pixels[:,:,:3]=rgb(TAN);pixels[:,:,3]=1
# Subtle uneven dye across the handmade sheet, deliberately avoiding realistic dirt.
dye=.009*np.sin(x*10+z*7)+.006*np.sin(x*27-z*5)
pixels[:,:,:3]+=dye[:,:,None]
def paint(mask,h):pixels[mask,:3]=rgb(h)
paint((x<-.18)&(z>.93+.035*np.sin(x*38)),'34362D')
paint((x>.95+.04*np.sin(z*28))&(z>.0),'34362D')


def line(points,width,color):
    mask=np.zeros(x.shape,bool)
    for (ax,az),(bx,bz) in zip(points[:-1],points[1:]):
        dx,dz=bx-ax,bz-az
        t=np.clip(((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz),0,1)
        mask|=(x-ax-t*dx)**2+(z-az-t*dz)**2<width**2
    paint(mask,color)


# Uneven circles with looping crayon scribbles, as on the official costume.
for cx,cz,rx,rz in [(-.275,.11,.097,.135),(.285,.10,.098,.137)]:
    q=((x-cx)/rx)**2+((z-cz)/rz)**2
    paint(q<1.08,INK)
    for k in range(2):
        tt=np.linspace(0,2*math.pi,60)
        points=[(cx+(rx*(.45+k*.28))*math.cos(t)+.013*math.sin(t*3+k),
                 cz+(rz*(.44+k*.27))*math.sin(t)+.008*math.sin(t*4+k)) for t in tt]
        line(points,.0035,TAN)
    line([(cx-.038,cz-.055),(cx+.033,cz+.055)],.006,TAN)
    line([(cx-.05,cz-.01),(cx+.048,cz+.07)],.004,TAN)
# Angular wavy mouth, thick hand-drawn strokes rather than a smooth cat smile.
line([(-.405,-.02),(-.40,-.17),(-.22,-.16),(-.16,-.255),(-.055,-.25),
      (.015,-.345),(.13,-.33),(.21,-.285)],.021,INK)
for s in (-1,1):
    for k in range(5):
        cx=s*(.43+.012*math.sin(k));cz=.17-k*.032 if s<0 else -.19-k*.030
        line([(cx-.047,cz+.025),(cx+.040,cz-.022)],.015,OCHRE)
mat=texture('Mimikyu_disguise_paint',pixels)
head.data.materials.clear();head.data.materials.append(mat)
head.rotation_euler.y=math.radians(12)
head.location=(.04,-.035,1.40)

# Cloth skirt: a flared hollow-looking drape with an irregular pointed hem.
n=144;nr=48;verts=[];faces=[]
for k in range(nr+1):
    t=k/nr
    for j in range(n):
        a=j*2*math.pi/n
        hem=.045+.12*(.5+math.asin(math.sin(a*9+.4))/math.pi)
        zz=hem+(1.08-hem)*t
        radius=.69*(1-t)**1.14+.145*t+.075*math.sin(t*math.pi)
        folds=(.022*math.cos(a*9+.4)+.009*math.sin(a*15))*(1-t)**2
        # Two larger lateral fabric points help preserve the ragged Pikachu silhouette.
        radius+=(.13*abs(math.sin(a))**18)*(1-t)**7
        xx=(radius+folds)*math.sin(a)+.13*t
        yy=-(radius*.66+folds*.65)*math.cos(a)+.025*t
        verts.append((xx,yy,zz))
for k in range(nr):
    for j in range(n):
        a=k*n+j;b=k*n+(j+1)%n;faces.append((a,b,b+n,a+n))
body=c.mesh('02_Ragged cloth skirt',verts,faces,TAN)
mod=body.modifiers.new('Real cloth thickness','SOLIDIFY');mod.thickness=.018;mod.offset=-1;c.apply(body,mod)
uv=body.data.uv_layers.new(name='Body eye markings')
for face in body.data.polygons:
    for li in face.loop_indices:
        point=body.data.vertices[body.data.loops[li].vertex_index].co
        uv.data[li].uv=((point.x+1)/2,point.z/1.4) if face.normal.y<0 else (.01,.01)
res=1536;v,u=np.mgrid[0:res,0:res].astype(np.float32)/(res-1);x=u*2-1;z=v*1.4
pixels=np.empty((res,res,4),np.float32);pixels[:,:,:3]=rgb(TAN);pixels[:,:,3]=1
for cx in (-.14,.14):
    q=((x-cx)/.023)**2+((z-.56)/.080)**2
    pixels[q<1.45,:3]=rgb('A29A74');pixels[q<1,:3]=rgb('252621')
body.data.materials.clear();body.data.materials.append(texture('Mimikyu_true_eyes',pixels))
# Shadow body stays under the cloth; visible only through the hem and from below.
shadow=c.ell('03_Shadow under the hem',(0,0,.105),(.57,.34,.095),'242823')
for s in (-1,1):
    c.tube('Tiny shadow foot',[(s*.29,-.06,.09),(s*.43,-.26,.05),(s*.57,-.27,.045)], [.085,.064,.025],'242823',20,5)

# A rough wooden imitation lightning tail, behind the sheet.
shape=[(.45,.23),(.60,.42),(.56,.51),(.73,.66),(.66,.76),(.90,.95),
       (1.20,1.20),(1.36,1.18),(1.38,.99),(1.07,.80),(.86,.69),(.90,.58),(.72,.42),(.76,.34),(.55,.18)]
verts=[(xx,yy,zz) for yy in (.20,.34) for xx,zz in shape]
nn=len(shape);faces=[tuple(range(nn-1,-1,-1)),tuple(range(nn,nn*2))]
faces += [(i,(i+1)%nn,(i+1)%nn+nn,i+nn) for i in range(nn)]
tail=c.mesh('04_Carved wooden disguise tail',verts,faces,'79634B')
mod=tail.modifiers.new('Worn wood edges','BEVEL');mod.width=.015;mod.segments=3;c.apply(tail,mod)
# Parallel grooves are narrow inset-looking dark wood strokes, not black outlines.
for offset in (0,.045):
    c.tube('Wood grain',[(.90,.190,.84+offset),(1.06,.190,.96+offset),(1.25,.190,1.08+offset)],
           [.006,.005,.0025],'514836',10,5)

stats=p.save_export(col,NAME,out)
draft='--draft' in sys.argv
p.render_views(NAME,out,stats,['hero','front'] if draft else ['hero','front','side','back','clay'],draft)
p.verify(NAME,out)
