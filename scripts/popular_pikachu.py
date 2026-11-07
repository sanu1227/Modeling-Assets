"""A dedicated Pikachu refinement, preserving the earlier starter collection."""
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
import popular_tools as p
from popular_tools import c

NAME='Pikachu'
col,out=p.initialize(NAME)
col['studio_exposure']=-1.40
YELLOW='F5CB34';BLACK='252C30';BROWN='94603A';RED='DC433E'

def lathe(name,rings):
    samples=c.catmull(rings,10);n=96;verts=[];faces=[]
    for z,rx,ry,cy in samples:
        for j in range(n):
            a=j*2*math.pi/n
            verts.append((rx*math.sin(a),cy-ry*math.cos(a),z))
    for i in range(len(samples)-1):
        for j in range(n):
            a=i*n+j;b=i*n+(j+1)%n;faces.append((a,b,b+n,a+n))
    start,end=len(verts),len(verts)+1;verts.extend([(0,samples[0][3],samples[0][0]),(0,samples[-1][3],samples[-1][0])])
    for j in range(n):
        faces.append((start,(j+1)%n,j));k=(len(samples)-1)*n;faces.append((end,k+j,k+(j+1)%n))
    return c.mesh(name,verts,faces,YELLOW)

parts=[lathe('Pear-shaped body',[(.16,.12,.14,.04),(.29,.36,.30,.04),(.55,.47,.36,.04),
    (.85,.43,.34,.03),(1.10,.35,.30,.0),(1.32,.32,.27,-.02),(1.47,.22,.20,-.04)]),
    lathe('Wide mouse cheeks',[(1.30,.10,.10,-.12),(1.40,.34,.27,-.12),(1.60,.52,.37,-.10),
    (1.82,.56,.39,-.07),(2.02,.49,.34,-.03),(2.18,.34,.25,.0),(2.25,.006,.006,.01)])]
# Unequal ear angles are characteristic of the lively official standing pose.
parts.append(c.tube('Tall left ear',[(-.32,.0,2.05),(-.43,.025,2.38),(-.55,.045,2.75),(-.57,.04,2.98)],
                    [(.14,.085),(.125,.075),(.085,.055),.004],YELLOW,32,10))
parts.append(c.tube('Tilted right ear',[(.33,.0,2.05),(.52,-.01,2.35),(.78,-.03,2.62),(.92,-.04,2.73)],
                    [(.14,.085),(.125,.075),(.085,.055),.004],YELLOW,32,10))
for s in (-1,1):
    parts.append(c.ell('Long little foot',(s*.30,-.22,.14),(.23,.38,.14),YELLOW,rot=(0,0,-s*12)))
    parts.append(c.ell('Round hind thigh',(s*.32,.015,.43),(.24,.28,.30),YELLOW))
parts.append(c.tube('Relaxed left arm',[(-.15,.01,1.15),(-.47,-.18,1.04),(-.48,-.32,.84)],
                    [.14,.15,.10],YELLOW,32,8))
parts.append(c.ell('Left paw',(-.48,-.32,.85),(.125,.13,.18),YELLOW,rot=(0,-18,0)))
parts.append(c.tube('Waving right arm',[(.15,.0,1.15),(.53,-.15,1.37),(.69,-.28,1.61)],
                    [.14,.145,.095],YELLOW,32,8))
parts.append(c.ell('Waving paw',(.69,-.28,1.62),(.115,.115,.155),YELLOW,rot=(0,18,0)))
# Three minute finger tips stay fused to each paw, avoiding detached bead fingers.
for j in range(3):
    parts.append(c.cone('Waving finger',(.65+(j-1)*.06,-.30,1.69),(.69+(j-1)*.07,-.31,1.79),.045,YELLOW))
body=c.union('01_Continuous Pikachu skin',parts,YELLOW,.012)
mod=body.modifiers.new('Adaptive sculpt mesh','DECIMATE');mod.ratio=.48;c.apply(body,mod)

# A front/back atlas puts color directly on the sculpt, including ear tips and stripes.
uv=body.data.uv_layers.new(name='Pikachu front and back paint')
for poly in body.data.polygons:
    backside=poly.normal.y>0
    for li in poly.loop_indices:
        pt=body.matrix_world@body.data.vertices[body.data.loops[li].vertex_index].co
        uu=(pt.x+1.6)/3.2
        uv.data[li].uv=((uu+(1 if backside else 0))*.5,pt.z/3.2)
height,width=3072,4096
xlocal=np.linspace(-1.6,1.6,width//2,dtype=np.float32)[None,:]
x=np.concatenate([xlocal,xlocal],axis=1)
z=np.linspace(0,3.2,height,dtype=np.float32)[:,None]
back=np.arange(width)[None,:]>=width//2
rgb=lambda h:np.array([int(h[i:i+2],16)/255 for i in (0,2,4)],np.float32)
pixels=np.empty((height,width,4),np.float32);pixels[:,:,:3]=rgb(YELLOW);pixels[:,:,3]=1
ear_black=((x<-.25)&(z>2.70-.15*(x+.5)))|((x>.40)&(z>2.47+.34*(x-.55)))
pixels[ear_black,:3]=rgb(BLACK)
for s in (-1,1):
    eye=((x-s*.245)/.078)**2+((z-1.878)/.101)**2<1
    pixels[eye&~back,:3]=rgb('262A2F')
    shine=((x-(s*.245-.020))/.021)**2+((z-1.917)/.028)**2<1
    pixels[shine&~back,:3]=rgb('FFFFFF')
    cheek=((x-s*.415)/.105)**2+((z-1.665)/.115)**2<1
    pixels[cheek&~back,:3]=rgb(RED)
nose=(z<1.772)&(z>1.735)&(abs(x)<.036*(z-1.735)/.037)
pixels[nose&~back,:3]=rgb('272A2E')
smile=1.633+3.2*(abs(x)-.076)**2
pixels[(abs(z-smile)<.0045)&(abs(x)<.155)&~back,:3]=rgb('4B3637')
for zz in (.72,.97):
    stripes=(abs(z-zz)<.061+.013*np.sin(x*30))&(abs(x)<.33-.18*abs(z-zz))
    pixels[stripes&back,:3]=rgb(BROWN)
image=bpy.data.images.new('Pikachu_surface_paint',width=width,height=height,alpha=True)
image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(out/'Pikachu_surface.png');image.file_format='PNG';image.save();image.pack()
mat=bpy.data.materials.new('Pikachu painted yellow skin');mat.use_nodes=True
bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Roughness'].default_value=.63;bs.inputs['Specular IOR Level'].default_value=.22
tx=mat.node_tree.nodes.new('ShaderNodeTexImage');tx.image=image;mat.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color'])
body.data.materials.clear();body.data.materials.append(mat)

# Broad angular male lightning tail, with a brown base extending from the back.
shape=[(.26,.48),(.54,.64),(.45,.86),(.77,.98),(.65,1.17),(1.20,1.74),
       (1.47,1.49),(1.01,1.05),(1.17,.83),(.79,.69),(.85,.51),(.37,.34)]
n=len(shape);verts=[(x,y,z) for y in (.34,.46) for x,z in shape]
faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]
faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
tail=c.mesh('02_Lightning tail',verts,faces,YELLOW)
mod=tail.modifiers.new('Soft lightning edges','BEVEL');mod.width=.017;mod.segments=3;c.apply(tail,mod)
for face in tail.data.polygons:face.use_smooth=False
c.tube('03_Brown tail root',[(.12,.27,.47),(.35,.37,.49),(.56,.40,.64)],
       [(.13,.085),(.115,.065),(.085,.05)],BROWN,24,6)

stats=p.save_export(col,NAME,out)
draft='--draft' in sys.argv
p.render_views(NAME,out,stats,['hero','front'] if draft else ['hero','front','side','back','clay'],draft)
p.verify(NAME,out)
