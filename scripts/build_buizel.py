"""Model Buizel from the official artwork and game appearance.

Front is -Y. Model components and painted markings remain editable.
Run with Blender --background --factory-startup --python-exit-code 1 --python.
Use -- --draft for a quick preview. Existing character assets are not changed.
"""
import math
import struct
import sys
import zlib
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import pokemon_common as c

OUT=ROOT/'assets'/'Buizel'
TEX=OUT/'Textures'
TEX.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
asset=bpy.data.collections.new('Buizel');scene.collection.children.link(asset)
studio=bpy.data.collections.new('90_Presentation');scene.collection.children.link(studio)
c.COLLECTION=asset
ORANGE='EC8C26'; CREAM='FFF0B0'; YELLOW='FFDA32'; BLUE='43A9C6'; INK='26313B'
for color in (ORANGE,CREAM,YELLOW,BLUE,INK,'FFFFFF','7DADBE'):
    mat=c.material(color)
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=.57
    shader.inputs['Specular IOR Level'].default_value=.22


def texture_material(name,pixels):
    h,w=pixels.shape[:2]
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))
    raw+=chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in pixels)))+chunk(b'IEND',b'')
    path=TEX/(name+'.png');path.write_bytes(raw)
    image=bpy.data.images.load(str(path));image.pack()
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=.58
    shader.inputs['Specular IOR Level'].default_value=.20
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
    mat.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
    return mat


def rgb(color):return np.array([int(color[i:i+2],16) for i in (0,2,4)],dtype=np.uint8)


def profile_samples(rings):return np.array([list(v) for v in c.catmull(rings,8)])


def profile_at(samples,z):
    return [np.interp(z,samples[:,0],samples[:,i]) for i in (1,2,3)]


def lathe(name,rings):
    samples=profile_samples(rings)
    vertices=[];faces=[];n=96
    for z,rx,ry,cy in samples:
        for j in range(n):
            a=2*math.pi*j/n
            y=cy-ry*math.cos(a)
            if name.startswith('Head'):
                y-=.39*math.exp(-((z-2.48)/.20)**2)*max(0,math.cos(a))**6
            vertices.append((rx*math.sin(a),y,z))
    for k in range(len(samples)-1):
        for j in range(n):
            a=k*n+j;b=k*n+(j+1)%n
            faces.append((a,b,b+n,a+n))
    start,end=len(vertices),len(vertices)+1
    vertices.extend([(0,samples[0,3],samples[0,0]),(0,samples[-1,3],samples[-1,0])])
    for j in range(n):
        faces.append((start,(j+1)%n,j))
        k=(len(samples)-1)*n
        faces.append((end,k+j,k+(j+1)%n))
    return c.mesh(name,vertices,faces,ORANGE),samples


def cylindrical_uv(obj,samples,zmin,zmax):
    uv=obj.data.uv_layers.new(name='Painted markings UV')
    coords=[]
    for vertex in obj.data.vertices:
        x,y,z=obj.matrix_world@vertex.co
        rx,ry,cy=profile_at(samples,z)
        angle=math.atan2(x/max(rx,.01),-(y-cy)/max(ry,.01))
        coords.append(((angle+math.pi)/(2*math.pi),(z-zmin)/(zmax-zmin)))
    for poly in obj.data.polygons:
        local=[coords[obj.data.loops[i].vertex_index] for i in poly.loop_indices]
        seam=max(u for u,v in local)-min(u for u,v in local)>.5
        for i,(u,v) in zip(poly.loop_indices,local):
            uv.data[i].uv=(u+1 if seam and u<.5 else u,v)


def painted_grid(samples,zmin,zmax,res=2048):
    v,u=np.mgrid[0:res,0:res].astype(np.float32)/(res-1)
    z=zmax-v*(zmax-zmin)
    angle=(u-.5)*(2*math.pi)
    rx,ry,cy=profile_at(samples,z)
    x=rx*np.sin(angle)
    pixels=np.empty((res,res,3),np.uint8);pixels[:]=rgb(ORANGE)
    return pixels,x,z,angle


body_rings=[(.28,.16,.18,.05),(.42,.58,.34,.04),(.65,.75,.41,.04),
            (1.02,.68,.42,.025),(1.40,.53,.36,.01),(1.78,.37,.29,0),
            (2.04,.30,.255,0),(2.18,.27,.23,0)]
torso,body_samples=lathe('Body block',body_rings)
body_parts=[torso]
for s in (-1,1):
    body_parts.append(c.tube('Short leg',[(s*.44,.04,.48),(s*.51,-.04,.29),(s*.51,-.12,.18)], [.21,.18,.16],ORANGE,24,6))
    body_parts.append(c.ell('Rounded foot',(s*.53,-.22,.145),(.25,.40,.145),ORANGE,rot=(0,0,-s*12)))
    body_parts.append(c.tube('Arm',[(s*.33,.0,1.94),(s*.49,-.04,1.70),(s*.68,-.13,1.40),(s*.80,-.22,1.19)], [.205,.19,.175,.155],ORANGE,24,8))
    body_parts.append(c.ell('Round paw',(s*.79,-.22,1.22),(.15,.155,.20),ORANGE,rot=(0,s*24,0)))
body=c.union('01_Body • seamless torso and limbs',body_parts,ORANGE,.022)
cylindrical_uv(body,body_samples,0,2.22)
pixels,x,z,angle=painted_grid(body_samples,0,2.22)
width=np.where(z<.94,.37*np.sqrt(np.clip(1-((z-.94)/.25)**2,0,1)),.37*(1-.29*np.clip((z-1.0)/1.0,0,1)))
belly=(abs(x)<width)&(np.cos(angle)>.22)&(z>.69)
pixels[belly]=rgb(CREAM)
for s in (-1,1):
    spot=((x-s*.19)/.088)**2+((z-1.52)/.285)**2<1
    pixels[spot&(np.cos(angle)<-.55)]=rgb(CREAM)
mat=texture_material('Buizel_body',pixels)
body.data.materials.clear();body.data.materials.append(mat)

# Head surface narrows into a wedge-shaped muzzle; ear roots are fused into it.
head_rings=[(2.12,.07,.10,-.18),(2.22,.34,.32,-.12),(2.40,.54,.47,-.055),
            (2.63,.59,.49,.02),(2.87,.55,.45,.055),(3.09,.43,.36,.07),
            (3.24,.26,.23,.075),(3.31,.015,.015,.075)]
head,head_samples=lathe('Head block',head_rings)
head_parts=[head]
for s in (-1,1):
    head_parts.append(c.tube('Tapered ear',[(s*.285,.18,3.09),(s*.36,.24,3.37),(s*.46,.31,3.64),(s*.45,.35,3.77)],[(.16,.11),(.155,.105),(.095,.07),(.005,.005)],ORANGE,32,8))
    head_parts.append(c.tube('Ear lower lobe',[(s*.38,.20,3.11),(s*.47,.27,3.21),(s*.49,.31,3.31)], [.10,.078,.004],ORANGE,20,5))
head=c.union('02_Head • muzzle and ears',head_parts,ORANGE,.014)
cylindrical_uv(head,head_samples,2.10,3.86)
pixels,x,z,angle=painted_grid(head_samples,2.10,3.86)
front=np.cos(angle)>.40
cheek_top=2.42+.205*np.exp(-((abs(x)-.43)/.19)**2)
pixels[(z<cheek_top)&(np.cos(angle)>-.20)]=rgb(CREAM)
for s in (-1,1):
    # Eye contours and pupil are painted on the real head surface.
    eye=((x-s*.305)/.124)**2+((z-2.785)/.220)**2
    pixels[(eye<1.075)&front]=rgb(INK)
    pixels[(eye<1)&front]=(255,253,241)
    pupil=((x-s*.296)/.067)**2+((z-2.778)/.162)**2
    pixels[(pupil<1)&front]=(29,34,41)
    highlight=((x-(s*.296-.020))/.021)**2+((z-2.857)/.043)**2
    pixels[(highlight<1)&front]=(255,255,255)
    brow=((x-s*.300)/.088)**2+((z-3.065)/.060)**2
    pixels[(brow<1)&front]=rgb(CREAM)
    for height in (2.49,2.55):
        stripe=((x-s*.441)/.071)**6+((z-(height+.10*(abs(x)-.44)))/.0125)**2
        pixels[(stripe<1)&front]=rgb(INK)
smile=(abs(z-(2.311+.66*x*x))<.007)&(abs(x)<.27)&(np.cos(angle)>.35)
philtrum=(abs(x)<.007)&(z>2.31)&(z<2.465)&(np.cos(angle)>.7)
pixels[smile|philtrum]=rgb(INK)
mat=texture_material('Buizel_face',pixels)
head.data.materials.clear();head.data.materials.append(mat)
head_tree=BVHTree.FromObject(head,bpy.context.evaluated_depsgraph_get())
hit,normal,_,_=head_tree.ray_cast(Vector((0,-3,2.478)),Vector((0,1,0)))
nose=c.ell('03_Nose • small black oval',hit+Vector((0,-.016,.004)),(.087,.033,.043),INK)

# Continuous elliptical flotation sac, intentionally flatter than a round torus.
vertices=[];faces=[];major=128;minor=32
for i in range(major):
    a=i*2*math.pi/major
    center=Vector((.585*math.cos(a),.435*math.sin(a),2.105+.023*math.sin(a)))
    radial=Vector((math.cos(a),math.sin(a),0))
    for j in range(minor):
        b=j*2*math.pi/minor
        vertices.append(center+radial*.165*math.cos(b)+Vector((0,0,.175*math.sin(b))))
for i in range(major):
    for j in range(minor):
        faces.append((i*minor+j,((i+1)%major)*minor+j,((i+1)%major)*minor+(j+1)%minor,i*minor+(j+1)%minor))
collar=c.mesh('04_Flotation sac • yellow ring',vertices,faces,YELLOW)


def closed_patch(name,points,center,color,thickness=.04):
    border=c.catmull(points+[points[0]],6)[:-1]
    center=Vector(center)
    n=len(border);rings=10
    verts=[];faces=[]
    for side in (-1,1):
        base=len(verts)
        verts.append(center+Vector((0,side*thickness,0)))
        for row in range(1,rings+1):
            t=row/rings
            for p in border:
                q=center.lerp(p,t)
                q.y+=side*thickness*math.sqrt(max(0,1-t*t))
                verts.append(q)
        for j in range(n):faces.append((base,base+1+j,base+1+(j+1)%n))
        for row in range(rings-1):
            for j in range(n):
                a=base+1+row*n+j;b=base+1+row*n+(j+1)%n
                faces.append((a,b,b+n,a+n))
    obj=c.mesh(name,verts,faces,color)
    # Both hemispheres share the rim after welding, giving a closed leaf surface.
    weld=obj.modifiers.new('Shared fin rim','WELD');weld.merge_threshold=.0001;c.apply(obj,weld)
    return obj


for s in (-1,1):
    points=[(s*.51,.10,1.78),(s*.74,.20,1.81),(s*.965,.24,1.61),(s*.98,.20,1.40),(s*.83,.08,1.18),(s*.65,.08,1.42)]
    fin=closed_patch('05_Arm fin '+('L' if s<0 else 'R'),points,(s*.78,.15,1.52),BLUE,.038)
    for vertex in fin.data.vertices:
        vertex.co=Vector((s*.70,.11,1.49))+(vertex.co-Vector((s*.70,.11,1.49)))*.88
    for k in (0,1):
        lines=[Vector((s*(.68+k*.05),.107,1.35+k*.02)),Vector((s*(.77+k*.085),.116,1.52+k*.01)),Vector((s*(.78+k*.15),.18,1.78-k*.12))]
        lines=[Vector((s*.70,.11,1.49))+(p-Vector((s*.70,.11,1.49)))*.88 for p in lines]
        c.tube('05_Fin crease',lines,[.004,.004,.002],'26748E',10,5)

# Small wrist markings follow the fused skin; no separate white pads.
body_tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
def skin_patch(name,cx,cz,rx,rz):
    n=48;rings=8;vertices=[];faces=[]
    for row in range(rings+1):
        r=row/rings
        for j in range(n if row else 1):
            a=j*2*math.pi/n
            x=cx+rx*r*math.cos(a);z=cz+rz*r*math.sin(a)
            hit,_,_,_=body_tree.ray_cast(Vector((x,-3,z)),Vector((0,1,0)))
            assert hit is not None,(name,x,z)
            vertices.append(hit+Vector((0,-.002,0)))
    for j in range(n):faces.append((0,1+j,1+(j+1)%n))
    for row in range(rings-1):
        for j in range(n):
            a=1+row*n+j;b=1+row*n+(j+1)%n
            faces.append((a,b,b+n,a+n))
    obj=c.mesh(name,vertices,faces,CREAM)
    mod=obj.modifiers.new('Marking inset','SOLIDIFY');mod.thickness=.008;mod.offset=-1;c.apply(obj,mod)
    return obj
for s in (-1,1):skin_patch('06_Wrist spot',s*.79,1.24,.073,.035)

# Tail paint has the rounded, lobed cream boundary visible in the reference art.
v,u=np.mgrid[0:1024,0:512].astype(np.float32)
t=1-v/1023;theta=u/511*2*math.pi
pixels=np.empty((1024,512,3),np.uint8);pixels[:]=rgb(ORANGE)
pixels[t>.72+.035*np.cos(theta*3)+.012*np.sin(theta)]=rgb(CREAM)
tail_mat=texture_material('Buizel_tail_tips',pixels)
for s in (-1,1):
    lift=.28 if s<0 else 0
    points=[(s*.22,.26,.61),(s*.35,.76,.61),(s*.56,1.24,.80),(s*.76,1.72,1.14+lift),(s*.83,2.00,1.43+lift)]
    if s<0:points=[(-.22,.26,.61),(-.12,.80,.67),(.08,1.30,1.03),(.20,1.80,1.65),(.18,2.08,2.02)]
    radii=[.20,.19,.165,.11,.004]
    sides=32;steps=12
    obj=c.tube('07_Tail '+('L' if s<0 else 'R'),points,radii,ORANGE,sides,steps)
    obj.data.materials.clear();obj.data.materials.append(tail_mat)
    rows=(len(points)-1)*steps+1
    uv=obj.data.uv_layers.new(name='Tail paint UV')
    for poly in obj.data.polygons:
        coords=[]
        for vi in poly.vertices:
            coords.append((vi%sides/sides,vi//sides/(rows-1)) if vi<rows*sides else (.5,0 if vi==rows*sides else 1))
        seam=max(u for u,v in coords)-min(u for u,v in coords)>.5
        for li,(u,v) in zip(poly.loop_indices,coords):uv.data[li].uv=(u+1 if seam and u<.5 else u,v)

# Two short toe divisions on each foot are narrow grooves represented by dark lines.
for s in (-1,1):
    for offset in (-.075,.075):
        x=s*.53+offset
        c.tube('08_Toe division',[(x,-.57,.13),(x,-.54,.20),(x,-.47,.255)],[.004,.005,.002],'B36824',10,5)

# Normalize overall standing height to the canonical 0.7 m.
bpy.context.view_layer.update()
positions=[obj.matrix_world@v.co for obj in asset.objects for v in obj.data.vertices]
low=min(p.z for p in positions);high=max(p.z for p in positions)
scale=.7/(high-low)
root=bpy.data.objects.new('Buizel • move whole character',None);asset.objects.link(root)
for obj in list(asset.objects):
    if obj.type!='MESH':continue
    obj.location.z-=low;obj.location*=scale;obj.scale*=scale
    c.active(obj);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj.parent=root
root['character']='Buizel / 브이젤 / #0418'
root['variant']='Male: two cream back markings'
root['reference_height_m']=.7
root['rigged']=False


def stage(obj,name,color):
    for col in list(obj.users_collection):col.objects.unlink(obj)
    studio.objects.link(obj);obj.name=name
    obj.data.materials.clear();obj.data.materials.append(c.material(color,.65))
    return obj


bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=.42,depth=.025,location=(0,.06,-.015))
obj=stage(bpy.context.object,'Display pedestal','D5E5E6')
mod=obj.modifiers.new('Soft edge','BEVEL');mod.width=.010;mod.segments=3;c.apply(obj,mod)
for p in obj.data.polygons:p.use_smooth=True
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.030))
stage(bpy.context.object,'Studio floor','DCE9EC')
def area(name,position,power,size,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    obj=bpy.data.objects.new(name,data);studio.objects.link(obj);obj.location=position
    obj.rotation_euler=(Vector((0,0,.38))-obj.location).to_track_quat('-Z','Y').to_euler()
area('Soft key',(-2,-3,4),300,3,(1,.94,.86))
area('Soft fill',(3,-1,2),160,3,(.88,.94,1))
area('Top rim',(.5,2.5,3),250,2,(1,1,1))
world=scene.world or bpy.data.worlds.new('Studio world');scene.world=world;world.use_nodes=True
world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.50,.62,.70,1)
world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.35
data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',data);studio.objects.link(camera)
camera.data.type='ORTHO';scene.camera=camera
def view(position,target,ortho):
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=ortho
view((2.0,-3.5,1.18),(0,.06,.35),.96)
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
try:
    pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
    if any(d.type=='OPTIX' for d in pref.devices):
        for d in pref.devices:d.use=d.type=='OPTIX'
        scene.cycles.device='GPU'
except (KeyError,TypeError,RuntimeError):pass
scene.view_settings.view_transform='Standard'
scene.view_settings.exposure=-.90
scene.render.resolution_x=1600;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.unit_settings.system='METRIC'
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.region_3d.view_distance=1.35
            a.spaces.active.region_3d.view_location=(0,.06,.35)
            a.spaces.active.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
            a.spaces.active.shading.type='MATERIAL'
            a.spaces.active.overlay.show_extras=False
            a.spaces.active.overlay.show_floor=False
c.active(root)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Buizel.blend'))
bpy.ops.object.select_all(action='DESELECT')
for obj in asset.objects:obj.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.gltf(filepath=str(OUT/'Buizel.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False)
if '--draft' in sys.argv:
    scene.cycles.samples=24;scene.render.resolution_percentage=55
    scene.render.filepath=str(OUT/'Buizel_draft.png');bpy.ops.render.render(write_still=True)
else:
    for name,pos,target,zoom in [
        ('Buizel_preview',(2.0,-3.5,1.18),(0,.06,.35),.96),
        ('Buizel_front',(0,-4,.9),(0,0,.35),.90),
        ('Buizel_back',(1.5,3.6,1.1),(0,.12,.34),1.02),
        ('Buizel_side',(3.6,0,1.0),(0,.11,.34),1.02),
        ('Buizel_face',(1.5,-3.5,1.12),(0,-.02,.54),.45)]:
        view(pos,target,zoom);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    scene.view_layers[0].material_override=c.material('ABBCC4',.65)
    view((1.45,-3.5,1.35),(0,.06,.35),.96)
    scene.render.filepath=str(OUT/'Buizel_clay.png');bpy.ops.render.render(write_still=True)
print('BUIZEL_BUILD_OK',flush=True)
