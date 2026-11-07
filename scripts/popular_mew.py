"""Mew floating inside its long looping tail, based on the official illustration."""
import math
import sys
from pathlib import Path
import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
import popular_tools as p
from popular_tools import c

NAME='Mew'
col,out=p.initialize(NAME);col['studio_exposure']=-1.05
PINK='E7AEC2'

def ell(name,pos,scale):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=40,location=pos)
    ob=c.finish(bpy.context.object,name,PINK);ob.scale=scale;c.active(ob)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return ob

parts=[ell('Small pear body',(0,.03,1.13),(.31,.25,.46)),
       ell('Narrow chest',(0,.00,1.47),(.185,.18,.27)),
       ell('Large feline head',(0,-.09,1.98),(.465,.335,.395)),
       ell('Small chin',(0,-.22,1.76),(.24,.15,.12))]
for s in (-1,1):
    parts.append(c.tube('Short triangular ear',[(s*.285,-.015,2.18),(s*.345,.005,2.31),(s*.40,.02,2.41)],
                        [(.175,.095),(.105,.063),.005],PINK,32,8))
    parts.append(ell('Round hip',(s*.22,.015,.95),(.22,.22,.285)))
    if s<0:
        knee=(-.25,-.05,.64);foot=(-.30,-.22,.39);end=(-.31,-.32,.24)
    else:
        knee=(.33,-.01,.55);foot=(.39,-.10,.29);end=(.44,-.18,.08)
    parts.append(c.tube('Long hind leg',[(s*.22,.02,.98),knee,foot,end],
                       [.15,.10,(.105,.14),.040],PINK,32,9))
    parts.append(ell('Rounded long foot',foot,(.11,.14,.24)))
    palm=(s*.55,-.13,1.54 if s>0 else 1.40)
    parts.append(c.tube('Short outstretched arm',[(s*.15,-.01,1.52),(s*.34,-.06,1.48),palm],
                       [.10,.084,.065],PINK,28,8))
    parts.append(ell('Little hand',palm,(.09,.065,.075)))
    for j in (-1,0,1):
        parts.append(c.tube('Tiny three fingers',[palm,(palm[0]+s*.125,palm[1]-.02+(j*.025),palm[2]+j*.039)],
                            [.030,.018],PINK,16,4))
body=c.union('01_Smooth Mew body',parts,PINK,.010)
mod=body.modifiers.new('Adaptive sculpt mesh','DECIMATE');mod.ratio=.48;c.apply(body,mod)
uv=body.data.uv_layers.new(name='Mew eye paint')
for poly in body.data.polygons:
    for li in poly.loop_indices:
        pt=body.matrix_world@body.data.vertices[body.data.loops[li].vertex_index].co
        uv.data[li].uv=((pt.x+.75)/1.5,pt.z/2.7) if poly.normal.y<.10 else (.01,.01)
res=3072
x=np.linspace(-.75,.75,res,dtype=np.float32)[None,:]
z=np.linspace(0,2.7,res,dtype=np.float32)[:,None]
rgb=lambda h:np.array([int(h[i:i+2],16)/255 for i in (0,2,4)],np.float32)
pixels=np.empty((res,res,4),np.float32);pixels[:,:,:3]=rgb(PINK);pixels[:,:,3]=1
for s in (-1,1):
    xx=x-s*.218
    zz=z-1.99
    tilted_x=xx+s*.18*zz
    shape=(tilted_x/.102)**2+(zz/.158)**2
    pixels[shape<1.10,:3]=rgb('4C3E50');pixels[shape<1,:3]=rgb('FBF6FA')
    iris=((x-s*.236)/.067)**2+((z-1.983)/.138)**2<1
    pixels[iris&(shape<1),:3]=rgb('5A93BB')
    lower=((x-s*.236)/.060)**2+((z-1.939)/.095)**2<1
    pixels[lower&iris&(shape<1),:3]=rgb('83B7D6')
    pupil=((x-s*.229)/.031)**2+((z-2.017)/.096)**2<1
    pixels[pupil&(shape<1),:3]=rgb('283341')
    highlight=((x-(s*.229-.014))/.024)**2+((z-2.074)/.036)**2<1
    pixels[highlight&(shape<1),:3]=rgb('FFFFFF')
mouth=(abs(z-(1.766+.80*x*x))<.0037)&(abs(x)<.096)
pixels[mouth,:3]=rgb('986479')
image=bpy.data.images.new('Mew_blue_eyes',width=res,height=res,alpha=True)
image.pixels.foreach_set(pixels.ravel());image.filepath_raw=str(out/'Mew_face.png');image.file_format='PNG';image.save();image.pack()
mat=bpy.data.materials.new('Mew soft pink and blue eye paint');mat.use_nodes=True
bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Roughness'].default_value=.61;bs.inputs['Specular IOR Level'].default_value=.22
tx=mat.node_tree.nodes.new('ShaderNodeTexImage');tx.image=image;mat.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color'])
body.data.materials.clear();body.data.materials.append(mat)

c.tube('02_Long looping tail',[(0,.08,.94),(.62,.36,1.36),(1.17,.50,1.95),(1.26,.55,2.20),
    (.73,.58,2.27),(-.22,.60,2.16),(-1.00,.55,1.88),(-1.28,.50,1.74),
    (-1.34,.50,1.99),(-1.10,.50,2.53),(-.86,.50,2.79),(-.66,.50,2.98),(-.55,.50,3.06),(-.52,.50,3.07)],
    [.075,.045,.030,.029,.027,.026,.028,.030,.034,(.035,.07),(.040,.125),(.040,.105),(.025,.055),.004],PINK,32,12)

stats=p.save_export(col,NAME,out)
draft='--draft' in sys.argv
p.render_views(NAME,out,stats,['hero','front'] if draft else ['hero','front','side','back','clay'],draft)
p.verify(NAME,out)
