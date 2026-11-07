"""Original Gardevoir fan sculpture based on official artwork and game renders."""
import sys
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import pokemon_common as c
from popular_lucario import loft, surf_patch, ellipse, uv_for_untextured, png_texture

OUT=ROOT/'assets'/'PokemonPopular'/'Gardevoir'
(OUT/'renders').mkdir(parents=True,exist_ok=True)
GREEN='87B97C';WHITE='F3F2EC';RED='DA6C7A';INK='363F44'


def paint_face(face):
    """Paint anime eyes into the face surface with no overlapping mesh decals."""
    n=2048
    v,u=np.mgrid[0:n,0:n].astype(np.float32)/(n-1)
    x=(u-.5)*1.2;z=4.50-v*.65
    def rgb(value):return tuple(int(value[i:i+2],16) for i in (0,2,4))
    pixels=np.empty((n,n,3),np.uint8);pixels[:]=rgb(WHITE)
    def polygon(outline):
        inside=np.zeros(x.shape,dtype=bool)
        for i,(ax,az) in enumerate(outline):
            bx,bz=outline[(i+1)%len(outline)]
            inside^=((az>z)!=(bz>z))&(x<(bx-ax)*(z-az)/(bz-az+1e-12)+ax)
        return inside
    for s in (-1,1):
        outline=[(s*.095,4.15),(s*.31,4.30),(s*.33,4.20),(s*.29,4.09),(s*.19,4.09)]
        pixels[polygon(outline)]=rgb(INK)
        cx,cz=s*.235,4.194
        inner=[(cx+(px-cx)*.92,cz+(pz-cz)*.91) for px,pz in outline]
        sclera=polygon(inner);pixels[sclera]=rgb('FFFBF0')
        for px,pz,rx,rz,color in [(s*.242,4.187,.059,.092,RED),(s*.247,4.186,.023,.073,'252E34'),(s*.227,4.226,.013,.025,'FFFFFF')]:
            pixels[(((x-px)/rx)**2+((z-pz)/rz)**2<=1)&sclera]=rgb(color)
    face.data.materials.clear();face.data.materials.append(png_texture('Gardevoir_face',pixels,OUT))
    uv=face.data.uv_layers.new(name='Painted face UV')
    bpy.context.view_layer.update()
    for p in face.data.polygons:
        for i in p.loop_indices:
            xyz=face.matrix_world@face.data.vertices[face.data.loops[i].vertex_index].co
            uv.data[i].uv=((xyz.x+.6)/1.2,(xyz.z-3.85)/.65)


def closed_blade(name,outline,thickness,color,axis='X'):
    vertices=[]
    zmin=min(b for a,b in outline);zmax=max(b for a,b in outline)
    for side in (-1,1):
        for a,b in outline:
            width=thickness*(.20+.80*((b-zmin)/max(.01,zmax-zmin))**.45) if axis=='X' else thickness
            vertices.append((side*width/2,a,b) if axis=='X' else (a,side*width/2,b))
    n=len(outline)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    obj=c.mesh(name,vertices,faces,color)
    mod=obj.modifiers.new('Soft sculpted rim','BEVEL');mod.width=.014;mod.segments=3;c.apply(obj,mod)
    return obj


def gown():
    n=144;rings=72;verts=[];faces=[]
    for k in range(rings+1):
        t=k/rings
        gap=.008+.245*t**1.5
        for j in range(n+1):
            theta=gap+(2*math.pi-2*gap)*j/n
            wave=.035*math.sin(3*theta+.2)*t*t
            rx=.145+1.04*t**1.65+.32*t**6*abs(math.sin(theta))**8+wave
            ry=.12+.49*t**1.6+wave*.7
            # The lateral hem turns outward, while the split front panels hang low.
            hem=.035+.29*abs(math.sin(theta))**6+.08*max(0,-math.cos(theta))
            z=3.06*(1-t)+hem*t**5
            x=rx*math.sin(theta)-.06*t**3
            y=-ry*math.cos(theta)+.12*t**3
            verts.append((x,y,z))
    for k in range(rings):
        for j in range(n):
            a=k*(n+1)+j;b=a+1
            faces.append((a,b,b+n+1,a+n+1))
    obj=c.mesh('01_Long split white gown',verts,faces,WHITE)
    mod=obj.modifiers.new('Closed fabric thickness','SOLIDIFY');mod.thickness=.024;mod.offset=-1;c.apply(obj,mod)
    # A green inner skirt is visible through the central opening.
    inner,_=loft('02_Green inner gown',[(.09,0,.15,.40,.27),(.23,0,.12,.55,.31),(.65,0,.09,.60,.34),(1.25,0,.04,.46,.29),(2.0,0,0,.29,.20),(2.7,0,0,.17,.13),(3.06,0,0,.14,.105)],GREEN,sides=96,steps=8)
    inner.scale.y=.75
    for s in (-1,1):
        c.tube('White leg',[(s*.10,.015,1.38),(s*.10,-.005,.70),(s*.11,-.055,.12)],[.065,.052,.045],WHITE,24,7)
        c.ell('Small pointed foot',(s*.11,-.105,.07),(.055,.15,.07),WHITE)


def hair_end(theta):
    a=abs((theta+math.pi)%(2*math.pi)-math.pi)
    return float(np.interp(a,[0,.28,.60,1.08,1.40,1.65,2.15,math.pi],[4.02,4.17,4.31,4.33,4.17,3.96,3.91,3.96]))


def hair_point(theta,t,offset=0):
    z0=4.28;rz=.58
    beta=math.acos((hair_end(theta)-z0)/rz)*t
    rx,ry=.575+offset,.445+offset
    return (rx*math.sin(beta)*math.sin(theta),-.045-ry*math.sin(beta)*math.cos(theta),z0+(rz+offset)*math.cos(beta))


def hair():
    sides=160;rings=64
    vertices=[(0,-.045,4.86)];faces=[]
    for k in range(1,rings+1):
        t=k/rings
        for j in range(sides):vertices.append(hair_point(2*math.pi*j/sides,t))
    for j in range(sides):faces.append((0,1+j,1+(j+1)%sides))
    for k in range(rings-1):
        for j in range(sides):
            a=1+k*sides+j;b=1+k*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    obj=c.mesh('07_Green helmet with pointed fringe',vertices,faces,GREEN)
    mod=obj.modifiers.new('Closed hair edge','SOLIDIFY');mod.thickness=.026;mod.offset=-1;c.apply(obj,mod)
    # Three quiet sculptural divisions follow the swept green crest.
    for s in (-1,0,1):
        points=[]
        for i in range(17):
            t=.16+.83*i/16
            theta=s*.74*(1-t)**.8
            points.append(hair_point(theta,t,.0025))
        c.tube('Hair crest division',points,[.0045]*len(points),'699D69',10,2)
    # Turned-in lower bob tips continue the helmet around the neck.
    for s in (-1,1):
        c.tube('Curved lower green bob',[(s*.40,.10,4.20),(s*.44,.13,3.95),(s*.34,.10,3.87),(s*.21,.06,3.92)],[(.055,.09),(.065,.10),(.052,.08),.006],GREEN,32,8)


def build():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene
    asset=bpy.data.collections.new('Pokemon_Gardevoir');scene.collection.children.link(asset)
    studio=bpy.data.collections.new('90_Presentation');scene.collection.children.link(studio)
    c.COLLECTION=asset
    for color in (GREEN,WHITE,RED,INK,'699D69'):
        c.material(color,.58).node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.20
    gown()
    green_torso,_=loft('03_Slender green upper body',[(3.02,0,0,.14,.11),(3.16,0,0,.17,.135),(3.40,0,.015,.22,.15),(3.61,0,.02,.235,.14),(3.68,0,.015,.14,.10)],GREEN)
    green_parts=[green_torso]
    chest=c.ell('White chest',(0,-.103,3.45),(.145,.095,.29),WHITE)
    neck=c.tube('Long white neck',[(0,-.075,3.53),(0,-.025,3.79),(0,-.045,4.04)],[.085,.073,.10],WHITE,32,8)
    center=c.tube('White central torso',[(0,-.09,3.27),(0,-.08,3.15),(0,-.05,3.03)],[.085,.082,.10],WHITE,28,7)
    c.union('04_White chest and neck',[chest,neck,center],WHITE,.009)
    # The red organ is a thin vertical fin, broad in profile, narrow from the front.
    closed_blade('05_Red chest fin',[(-.16,3.17),(-.48,3.35),(-.61,3.60),(-.53,3.66),(-.19,3.62)],.065,RED)
    closed_blade('06_Red back fin',[(.13,3.18),(.38,3.31),(.46,3.49),(.16,3.48)],.050,RED)
    for s in (-1,1):
        label='L' if s<0 else 'R'
        rise=.14 if s>0 else 0
        pts=[(s*.215,.015,3.61),(s*.42,.015,3.29+rise*.3),(s*.69,-.025,2.89+rise*.6),(s*.98,-.10,2.49+rise),(s*1.18,-.14,2.27+rise),(s*1.32,-.155,2.15+rise),(s*1.42,-.16,2.09+rise)]
        pieces=[c.tube(label+'_Long slender green arm',pts,[(.044,.060),(.042,.055),(.042,.061),(.063,.108),(.049,.101),(.030,.061),.004],GREEN,36,8)]
        for j in range(2):
            x=s*(1.19+.035*j);z=2.29+rise+.04*j
            tip=(s*(1.43+.015*j),-.16,2.19+rise+.08*j)
            pieces.append(c.tube(label+'_Pointed finger',[(x,-.14,z),((x+tip[0])/2,-.15,(z+tip[2])/2),tip],[(.031,.048),(.023,.032),.004],GREEN,20,5))
        green_parts.append(c.union(label+'_08_Arm and three tapered fingers',pieces,GREEN,.008))
    c.union('03_Green torso and seamless long arms',green_parts,GREEN,.009)
    # White angular face, under the green fringe. No human nose or separate lips.
    face_base,_=loft('White tapered face',[(3.93,0,-.14,.045,.075),(4.02,0,-.135,.26,.19),(4.17,0,-.135,.40,.265),(4.31,0,-.125,.34,.22),(4.43,0,-.10,.065,.09)],WHITE,sides=64,steps=8)
    faceparts=[face_base]
    for s in (-1,1):
        outline=[(s*.29,4.30),(s*.46,4.33),(s*.41,4.22),(s*.45,4.22),(s*.395,4.14),(s*.35,4.06),(s*.24,4.02)]
        cheek=closed_blade('Angular white cheek',outline,.19,WHITE,axis='Y');cheek.location.y=-.14
        faceparts.append(cheek)
    face=c.union('09_White angular face',faceparts,WHITE,.007)
    paint_face(face)
    loft('Green inner head volume',[(3.90,0,.18,.25,.13),(4.02,0,.12,.43,.20),(4.20,0,.06,.53,.32),(4.40,0,.04,.49,.33),(4.65,0,.03,.25,.22),(4.72,0,.03,.03,.03)],GREEN,sides=64,steps=8)
    hair()
    root=bpy.data.objects.new('root_Gardevoir',None);asset.objects.link(root)
    root['pokemon']='Gardevoir';root['korean']='가디안';root['canonical_height_m']=1.6
    root['reference']='https://www.pokemon.com/us/pokedex/gardevoir'
    root['design']='Hand-authored fan model; no extracted game meshes'
    factor=1.6/4.86
    for obj in list(asset.objects):
        if obj.type!='MESH':continue
        uv_for_untextured(obj);obj.location*=factor;obj.scale*=factor;c.active(obj)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);obj.parent=root;obj['pokemon']='Gardevoir'
    return asset,studio,root


def stage(studio):
    scene=bpy.context.scene
    def move(obj,name,color):
        for col in list(obj.users_collection):col.objects.unlink(obj)
        studio.objects.link(obj);obj.name=name;obj.data.materials.append(c.material(color,.7))
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=.73,depth=.025,location=(0,.04,-.015))
    obj=bpy.context.object;move(obj,'Display plinth','D8DFD7');mod=obj.modifiers.new('Soft rim','BEVEL');mod.width=.01;mod.segments=3;c.apply(obj,mod)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.031));move(bpy.context.object,'Studio floor','E7EBE4')
    for name,pos,power,size,color in [('Soft key',(-3,-4,5),240,3.5,(1,.96,.90)),('Fill',(3,-1,3),140,3,(.90,.96,1)),('Rim',(1,3,4),230,3,(.94,1,.96))]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
        obj=bpy.data.objects.new(name,data);studio.objects.link(obj);obj.location=pos;obj.rotation_euler=(Vector((0,0,.8))-obj.location).to_track_quat('-Z','Y').to_euler()
    world=scene.world or bpy.data.worlds.new('World');scene.world=world;world.use_nodes=True
    world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.54,.61,.54,1);world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.30
    data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);studio.objects.link(cam);data.type='ORTHO';scene.camera=cam
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=1400;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.10
    scene.unit_settings.system='METRIC'
    return cam


def view(cam,pos,target,zoom):
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=zoom


def render(cam,draft=False):
    scene=bpy.context.scene
    views=[('preview',(2.1,-4,1.75),(0,.02,.80),1.90),('front',(0,-4,.82),(0,0,.80),1.90),('back',(1.8,4,1.65),(0,.04,.80),1.90),('side',(4,0,.90),(0,.02,.80),1.90),('face',(1.4,-3,1.55),(0,-.035,1.38),.67)]
    if draft:scene.cycles.samples=16;scene.render.resolution_percentage=55;views=views[:2]
    for name,pos,target,zoom in views:
        view(cam,pos,target,zoom);scene.render.filepath=str(OUT/'renders'/('Gardevoir_'+name+('_draft' if draft else '')+'.png'));bpy.ops.render.render(write_still=True)
    if not draft:
        scene.view_layers[0].material_override=c.material('B8C3B7',.70)
        view(cam,(2.1,-4,1.75),(0,.02,.80),1.90);scene.render.filepath=str(OUT/'renders'/'Gardevoir_clay.png');bpy.ops.render.render(write_still=True)
        scene.view_layers[0].material_override=None


if __name__=='__main__':
    asset,studio,root=build();cam=stage(studio);view(cam,(2.1,-4,1.75),(0,.02,.80),1.90)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.region_3d.view_distance=2.3;space.region_3d.view_location=(0,0,.80);space.region_3d.view_rotation=cam.rotation_euler.to_quaternion();space.shading.type='MATERIAL';space.overlay.show_extras=False
    c.active(root);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Gardevoir.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in asset.objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.gltf(filepath=str(OUT/'Gardevoir.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True)
    if '--no-render' not in sys.argv:render(cam,'--draft' in sys.argv)
    print('GARDEVOIR_BUILD_OK',flush=True)
