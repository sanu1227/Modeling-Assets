"""Hand-authored Lucario fan sculpture; front -Y and ground Z=0.

Use Blender --background --factory-startup --python this.py -- --draft.
The official illustration is reference only, never a texture or imported mesh.
"""
import sys
import math
import json
import struct
import zlib
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pokemon_common as c

OUT = ROOT / 'assets' / 'PokemonPopular' / 'Lucario'
(OUT / 'renders').mkdir(parents=True, exist_ok=True)
(OUT / 'Textures').mkdir(exist_ok=True)
BLUE = '468FA9'
BLACK = '343B42'
CREAM = 'F0D995'
WHITE = 'F6F2DF'
RED = 'BB3C40'


def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.context.preferences.filepaths.save_version = 0


def loft(name, sections, color, axis='Z', sides=64, steps=7):
    """Sections: axis position, center horizontal, center depth, radii x/depth."""
    values = np.asarray(sections)
    samples = []
    for i in range(len(values)-1):
        a, b, cc, d = [values[k] for k in (max(0, i-1), i, i+1, min(len(values)-1, i+2))]
        for j in range(steps):
            t = j/steps
            samples.append(.5*((2*b)+(-a+cc)*t+(2*a-5*b+4*cc-d)*t*t+(-a+3*b-3*cc+d)*t*t*t))
    samples.append(values[-1])
    vertices, faces = [], []
    for pos, cx, cy, rx, ry in samples:
        rx, ry = max(.003, rx), max(.003, ry)
        for j in range(sides):
            theta = 2*math.pi*j/sides
            x, y = cx+rx*math.sin(theta), cy+ry*math.cos(theta)
            vertices.append((x, y, pos) if axis=='Z' else (x, pos, y))
    for i in range(len(samples)-1):
        for j in range(sides):
            a=i*sides+j; b=i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    a,b = len(vertices), len(vertices)+1
    for sample in (samples[0], samples[-1]):
        pos,cx,cy,rx,ry = sample
        vertices.append((cx,cy,pos) if axis=='Z' else (cx,pos,cy))
    for j in range(sides):
        faces.append((a,(j+1)%sides,j))
        k=(len(samples)-1)*sides
        faces.append((b,k+j,k+(j+1)%sides))
    obj=c.mesh(name,vertices,faces,color)
    return obj,np.asarray(samples)


def surf_patch(name, outline, bvh, color, depth=.008):
    """An editable, closed colored shape projected onto actual face geometry."""
    n=len(outline); rings=8
    x=sum(p[0] for p in outline)/n; z=sum(p[1] for p in outline)/n
    def project(px,pz):
        hit=bvh.ray_cast(Vector((px,-4,pz)),Vector((0,1,0)))
        if hit[0] is None:
            raise RuntimeError(f'{name}: face ray missed at {px}, {pz}')
        return (px,hit[0].y-depth,pz)
    vertices=[project(x,z)]
    for ring in range(1,rings+1):
        r=ring/rings
        for px,pz in outline: vertices.append(project(x+(px-x)*r,z+(pz-z)*r))
    faces=[(0,1+j,1+(j+1)%n) for j in range(n)]
    for i in range(rings-1):
        for j in range(n):
            a=1+i*n+j;b=1+i*n+(j+1)%n
            faces.append((a,b,b+n,a+n))
    obj=c.mesh(name,vertices,faces,color)
    # Mirrored outlines reverse winding. Always extrude their backing into the head.
    bm=bmesh.new();bm.from_mesh(obj.data)
    if sum(f.normal.y for f in bm.faces)>0:
        bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
        bm.to_mesh(obj.data);obj.data.update()
    bm.free()
    mod=obj.modifiers.new('Closed surface thickness','SOLIDIFY');mod.thickness=.008;mod.offset=-1
    c.apply(obj,mod)
    return obj


def ellipse(x,z,rx,rz,n=64):
    return [(x+rx*math.cos(i*2*math.pi/n),z+rz*math.sin(i*2*math.pi/n)) for i in range(n)]


def png_texture(name,pixels,output_dir=None):
    h,w=pixels.shape[:2]
    def chunk(tag,data):
        return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
    raw=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))
    raw+=chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in pixels)))+chunk(b'IEND',b'')
    target=output_dir or OUT
    (target/'Textures').mkdir(parents=True,exist_ok=True)
    path=target/'Textures'/(name+'.png');path.write_bytes(raw)
    image=bpy.data.images.load(str(path));image.pack()
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=.58
    p.inputs['Specular IOR Level'].default_value=.20
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
    mat.node_tree.links.new(node.outputs['Color'],p.inputs['Base Color'])
    return mat


def head_texture(head,samples):
    n=2048
    v,u=np.mgrid[0:n,0:n].astype(np.float32)/(n-1)
    y=.34-v*1.24
    angle=u*2*math.pi
    cx,cz,rx,rz=[np.interp(y,samples[:,0],samples[:,i]) for i in range(1,5)]
    x=cx+rx*np.sin(angle);z=cz+rz*np.cos(angle)
    pixels=np.empty((n,n,3),np.uint8)
    def rgb(value):return tuple(int(value[i:i+2],16) for i in (0,2,4))
    pixels[:]=rgb(BLUE)
    mask=(z>3.20)&(z<3.50+.13*np.clip(abs(x)/.32,0,1))
    mask|=(y<-.52)&(z>3.19)
    mask|=(y>-.04)&(z>3.32)
    pixels[mask]=rgb(BLACK)
    # A broad blue forehead stripe narrows into a sharp point above the muzzle.
    stripe=(abs(x)<np.clip((z-3.42)*.48,0,.115))&(z>3.42)&(y<.08)
    pixels[stripe]=rgb(BLUE)
    # Paint eyes into the actual head UV surface, avoiding stacked mesh edges.
    def polygon_mask(outline):
        inside=np.zeros(x.shape,dtype=bool)
        for i,(ax,az) in enumerate(outline):
            bx,bz=outline[(i+1)%len(outline)]
            inside^=((az>z)!=(bz>z))&(x<(bx-ax)*(z-az)/(bz-az+1e-12)+ax)
        return inside&(y<.10)
    for side in (-1,1):
        outline=[(side*px,pz) for px,pz in [(.115,3.475),(.210,3.525),(.316,3.562),(.331,3.490),(.309,3.430),(.227,3.433)]]
        pixels[polygon_mask(outline)]=rgb('151C22')
        cx,cz=side*.253,3.487
        inner=[(cx+(px-cx)*.91,cz+(pz-cz)*.86) for px,pz in outline]
        sclera=polygon_mask(inner)
        pixels[sclera]=rgb('F5F2DC')
        for px,pz,rx,rz,color in [(side*.252,3.483,.037,.056,RED),(side*.253,3.484,.016,.047,'151C22'),(side*.239,3.511,.008,.014,'FFFFFF')]:
            pixels[(((x-px)/rx)**2+((z-pz)/rz)**2<=1)&sclera]=rgb(color)
    head.data.materials.clear();head.data.materials.append(png_texture('Lucario_face_markings',pixels))
    uv=head.data.uv_layers.new(name='Head cylindrical UV')
    points=[]
    for vert in head.data.vertices:
        x,y,z=vert.co
        cz=np.interp(y,samples[:,0],samples[:,2]);rx=np.interp(y,samples[:,0],samples[:,3]);rz=np.interp(y,samples[:,0],samples[:,4])
        a=math.atan2(x/max(rx,.003),(z-cz)/max(rz,.003))%(2*math.pi)
        points.append((a/(2*math.pi),(y+.90)/1.24))
    for p in head.data.polygons:
        coords=[points[head.data.loops[i].vertex_index] for i in p.loop_indices]
        seam=max(p[0] for p in coords)-min(p[0] for p in coords)>.5
        for index,(u,v) in zip(p.loop_indices,coords):uv.data[index].uv=(u+1 if seam and u<.5 else u,v)


def uv_for_untextured(obj):
    if obj.data.uv_layers:return
    uv=obj.data.uv_layers.new(name='Reusable planar UV')
    xs=[v.co.x for v in obj.data.vertices];zs=[v.co.z for v in obj.data.vertices]
    x0,x1=min(xs),max(xs);z0,z1=min(zs),max(zs)
    for p in obj.data.polygons:
        for i in p.loop_indices:
            v=obj.data.vertices[obj.data.loops[i].vertex_index].co
            uv.data[i].uv=((v.x-x0)/max(x1-x0,1e-5),(v.z-z0)/max(z1-z0,1e-5))


def build():
    clear()
    scene=bpy.context.scene
    asset=bpy.data.collections.new('Pokemon_Lucario');scene.collection.children.link(asset)
    studio=bpy.data.collections.new('90_Presentation');scene.collection.children.link(studio)
    c.COLLECTION=asset
    for value in (BLUE,BLACK,CREAM,WHITE,RED,'151C22'):
        mat=c.material(value,.58);mat.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.2
    # The slender torso is shaped independently from the large blue thighs.
    torso,_=loft('Cream torso',[(2.02,0,.015,.29,.23),(2.17,0,.01,.33,.27),(2.36,0,0,.235,.20),(2.59,0,0,.25,.21),(2.83,0,0,.34,.245),(2.99,0,.02,.28,.21),(3.12,0,.025,.15,.14)],CREAM)
    # Jagged chest fur ends; merged into the torso instead of separate beads.
    bodyparts=[torso]
    for s in (-1,1):
        bodyparts.append(c.cone('Collar pointed fur',(s*.12,-.04,3.04),(s*.21,-.06,3.23),.085,CREAM))
        bodyparts.append(c.cone('Collar side fur',(s*.23,-.025,2.99),(s*.36,-.04,3.10),.085,CREAM))
        bodyparts.append(c.cone('Front collar fur',(s*.075,-.15,3.025),(s*.13,-.17,3.16),.066,CREAM))
        bodyparts.append(c.cone('Low chest tufts',(s*.15,-.225,2.17),(s*.13,-.255,1.99),.075,CREAM))
    torso=c.union('01_Cream torso with chest fur',bodyparts,CREAM,.016)
    c.cone('Central lower chest fur',(0,-.25,2.16),(.025,-.28,1.97),.10,CREAM)
    hip,_=loft('02_Dark hip band',[(1.87,0,.06,.32,.25),(1.96,0,.04,.49,.31),(2.13,0,.025,.42,.29),(2.23,0,.01,.29,.235)],BLACK)
    for s in (-1,1):
        label='L' if s<0 else 'R'
        thigh,_=loft(label+'_Blue thigh',[(1.24,s*.43,.025,.23,.245),(1.29,s*.44,.025,.28,.285),(1.47,s*.40,.015,.315,.33),(1.76,s*.32,.035,.30,.33),(1.98,s*.25,.05,.23,.28),(2.08,s*.20,.065,.12,.18)],BLUE)
        shin=c.tube(label+'_Digitigrade lower leg',[(s*.44,.06,1.39),(s*.48,.10,1.17),(s*.52,.20,.88),(s*.60,.08,.49),(s*.65,-.04,.25)],[(.16,.18),(.145,.155),(.12,.13),(.14,.13),(.17,.18)],BLACK,32,9)
        footparts=[shin,c.ell(label+'_Long paw',(s*.65,-.17,.17),(.24,.38,.17),BLACK)]
        for offset in (-.13,0,.13):
            footparts.append(c.ell(label+'_Toe',(s*.65+offset,-.39,.14),(.105,.17,.135),BLACK))
        c.union(label+'_03_Lower leg and three toes',footparts,BLACK,.014)
        for x in (-.073,.073):
            c.tube(label+'_Toe groove',[(s*.65+x,-.537,.12),(s*.65+x,-.526,.18),(s*.65+x,-.475,.24)], [.008,.009,.006],'1C242B',10,4)
    # Arms use the official asymmetric relaxed battle stance.
    arm_specs=[(-1,(-.37,.015,2.88),(-.62,-.015,2.55),(-.80,-.12,2.25),(-.91,-.17,2.07)),
               (1,(.37,.015,2.88),(.76,.015,2.73),(1.10,-.07,2.59),(1.36,-.12,2.58))]
    for s,shoulder,elbow,wrist,palm in arm_specs:
        label='L' if s<0 else 'R'
        c.ell(label+'_Dark shoulder',shoulder,(.145,.185,.205),BLACK,rot=(0,s*13,0))
        mid=Vector(elbow).lerp(Vector(wrist),.35)
        c.tube(label+'_Blue upper arm',[shoulder,elbow,mid.lerp(Vector(wrist),.20)],[.11,.105,.153],BLUE,32,8)
        foreparts=[c.tube(label+'_Dark forearm',[mid,wrist,palm],[.125,.15,.16],BLACK,32,7),c.ell(label+'_Palm',palm,(.21,.19,.18),BLACK)]
        for j in range(3):
            pos=Vector(palm)+Vector((s*(.10+.035*(j==1)),-.085+(j-1)*.09,-.06))
            foreparts.append(c.ell(label+'_Finger',pos,(.105,.085,.115),BLACK))
        c.union(label+'_04_Forearm and three finger paw',foreparts,BLACK,.012)
        base=Vector(palm)+Vector((-.04*s,-.02,.12));tip=base+Vector((-.04*s,-.015,.37))
        c.tube(label+'_Ivory hand spike',[base,base.lerp(tip,.35),base.lerp(tip,.75),tip],[(.12,.105),(.095,.085),(.05,.045),.004],WHITE,32,6)
    c.tube('05_Ivory chest spike',[(0,-.20,2.84),(0,-.31,2.82),(0,-.46,2.78),(0,-.57,2.75)],[.106,.098,.051,.004],WHITE,40,6)
    # Canine head built as a smooth loft with a true projecting tapered muzzle.
    head,samples=loft('06_Head and long muzzle',[
        (-.90,0,3.255,.055,.035),(-.82,0,3.28,.115,.065),(-.66,0,3.32,.19,.095),
        (-.48,0,3.37,.265,.17),(-.25,0,3.42,.355,.27),(-.02,0,3.43,.37,.32),
        (.20,0,3.43,.29,.28),(.34,0,3.42,.015,.025)],BLUE,axis='Y',sides=96,steps=10)
    head_texture(head,samples)
    bvh=BVHTree.FromPolygons([v.co for v in head.data.vertices],[list(p.vertices) for p in head.data.polygons])
    c.ell('Small black nose',(0,-.899,3.27),(.040,.017,.022),'20282E')
    # Subtle mouth lines follow the underside of the snout without an added smile.
    for s in (-1,1):
        points=[]
        for t in np.linspace(0,1,25):
            x=s*(.055+.145*t);z=3.225+.025*t*t
            hit=bvh.ray_cast(Vector((x,-4,z)),Vector((0,1,0)))[0]
            points.append((x,hit.y-.006,z))
        c.tube('Closed mouth corner',points,[.0028]*len(points),'20282E',10,1)
    # Long jackal ears, a thin dark inset, and a blue brow leading into the crown.
    for s in (-1,1):
        label='L' if s<0 else 'R'
        ear,_=loft(label+'_Tall triangular blue ear',[(3.53,s*.235,.025,.105,.075),(3.69,s*.270,.025,.165,.080),(3.94,s*.330,.035,.135,.065),(4.21,s*.395,.045,.075,.040),(4.40,s*.43,.055,.004,.006)],BLUE,sides=64,steps=8)
        ear_bvh=BVHTree.FromPolygons([v.co for v in ear.data.vertices],[list(p.vertices) for p in ear.data.polygons])
        inner=[(s*.228,3.69),(s*.270,3.86),(s*.371,4.14),(s*.363,3.86),(s*.333,3.72),(s*.285,3.76)]
        surf_patch(label+'_Dark inner ear',inner,ear_bvh,BLACK,.004)
        # Two hanging aura feelers per side: four in total.
        for k in range(2):
            loft(label+'_Aura sensor '+str(k+1),[(2.92,s*(.50+k*.25),.34+k*.20,.004,.004),(2.97,s*(.50+k*.25),.34+k*.20,.095,.065),(3.07,s*(.53+k*.24),.32+k*.20,.165,.105),(3.22,s*(.49+k*.18),.29+k*.17,.15,.105),(3.38,s*(.38+k*.09),.21+k*.11,.12,.095),(3.48,s*.29,.13+k*.07,.085,.075)],BLACK,sides=48,steps=8)
    # Thick tapered canine tail swept away from the front silhouette.
    c.tube('07_Blue tapered tail',[(0,.23,2.04),(.25,.62,1.91),(.57,.89,1.95),(.85,1.0,2.10),(1.08,1.01,2.18),(1.28,1.02,2.13)],[(.20,.18),(.18,.15),(.16,.13),(.10,.08),(.06,.05),.004],BLUE,36,8)
    # Place at canonical height 1.2m; preserve editable parts and easy root transform.
    root=bpy.data.objects.new('root_Lucario',None);asset.objects.link(root)
    root['pokemon']='Lucario';root['korean']='루카리오';root['reference']='https://www.pokemon.com/us/pokedex/lucario'
    root['design']='Original hand-authored fan interpretation; not extracted game data'
    root['canonical_height_m']=1.2
    factor=1.2/4.4
    for obj in list(asset.objects):
        if obj.type!='MESH':continue
        uv_for_untextured(obj)
        obj.location*=factor;obj.scale*=factor;c.active(obj)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        obj.parent=root
        obj['pokemon']='Lucario'
    return asset,studio,root


def setup_stage(studio):
    scene=bpy.context.scene
    def move(obj,name,color):
        for col in list(obj.users_collection):col.objects.unlink(obj)
        studio.objects.link(obj);obj.name=name
        obj.data.materials.append(c.material(color,.7))
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=.59,depth=.025,location=(0,.04,-.014))
    obj=bpy.context.object;move(obj,'Display plinth','CAD8E0')
    mod=obj.modifiers.new('Soft rim','BEVEL');mod.width=.008;mod.segments=3;c.apply(obj,mod)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.030));move(bpy.context.object,'Studio floor','E5EBEE')
    for name,pos,power,size,color in [('Soft key',(-2,-3,4),165,3,(1,.95,.90)),('Fill',(2,-1,2),90,2.5,(.84,.92,1)),('Rim',(.5,2.5,3),150,2.5,(.90,.96,1))]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
        obj=bpy.data.objects.new(name,data);studio.objects.link(obj);obj.location=pos
        obj.rotation_euler=(Vector((0,0,.6))-obj.location).to_track_quat('-Z','Y').to_euler()
    world=scene.world or bpy.data.worlds.new('World');scene.world=world;world.use_nodes=True
    world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.50,.58,.64,1)
    world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.27
    data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);studio.objects.link(cam);data.type='ORTHO';scene.camera=cam
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=1400;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.1
    scene.unit_settings.system='METRIC'
    return cam


def view(cam,pos,target,scale):
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale


def render_views(cam,draft=False):
    scene=bpy.context.scene
    views=[('preview',(2.7,-4,1.45),(0,.015,.60),1.43),('front',(0,-4,.62),(0,0,.60),1.42),('back',(1.65,4,1.45),(0,.04,.60),1.43),('side',(4,.02,.68),(0,.02,.60),1.43),('face',(1.8,-3,1.35),(0,-.045,.99),.64)]
    if draft:
        scene.render.resolution_percentage=55;scene.cycles.samples=16;views=views[:2]
    for name,pos,target,scale in views:
        view(cam,pos,target,scale);scene.render.filepath=str(OUT/'renders'/('Lucario_'+name+('_draft' if draft else '')+'.png'))
        bpy.ops.render.render(write_still=True)
    if not draft:
        scene.view_layers[0].material_override=c.material('AEBAC1',.7)
        view(cam,(1.8,-4,1.45),(0,.015,.60),1.43);scene.render.filepath=str(OUT/'renders'/'Lucario_clay.png');bpy.ops.render.render(write_still=True)
        scene.view_layers[0].material_override=None


if __name__=='__main__':
    asset,studio,root=build();cam=setup_stage(studio)
    view(cam,(2.7,-4,1.45),(0,.015,.60),1.43)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.region_3d.view_distance=1.8;space.region_3d.view_location=(0,0,.60)
                space.region_3d.view_rotation=cam.rotation_euler.to_quaternion();space.shading.type='MATERIAL';space.overlay.show_extras=False
    c.active(root)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Lucario.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in asset.objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.gltf(filepath=str(OUT/'Lucario.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True)
    if '--no-render' not in sys.argv:render_views(cam,'--draft' in sys.argv)
    print('LUCARIO_BUILD_OK',flush=True)
