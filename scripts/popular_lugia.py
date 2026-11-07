"""Official-artwork-inspired Lugia landing pose with five-finger wings.

Front -Y, Z up. --draft uses two CPU threads at 800 px. --full --gpu renders
six final views with OPTIX; --render-only reads the saved editable source.
"""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector,Quaternion
from mathutils.geometry import tessellate_polygon
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import pokemon_common as c
from popular_painting import paint_front,ellipse
OUT=ROOT/'assets'/'PokemonPopular'/'Lugia'
(OUT/'renders').mkdir(parents=True,exist_ok=True)
WHITE='EFF3F5';BELLY='87ABDF';BLUE='354B8B';INK='18263B';PINK='CF8996'


def options():
    p=argparse.ArgumentParser()
    p.add_argument('--draft',action='store_true');p.add_argument('--full',action='store_true')
    p.add_argument('--render-only',action='store_true');p.add_argument('--gpu',action='store_true')
    p.add_argument('--view',default='preview')
    return p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


def flipper(name,points,widths,depths):
    """Flattened, broad fingers with stable thickness along the wing plane."""
    path=c.catmull(points,8);sizes=c.catmull([(w,d,0) for w,d in zip(widths,depths)],8)
    n=32;vertices=[];faces=[]
    for i,p in enumerate(path):
        t=(path[min(i+1,len(path)-1)]-path[max(i-1,0)]).normalized()
        depth=Vector((0,1,0));depth=(depth-t*depth.dot(t)).normalized()
        width=depth.cross(t).normalized()
        for j in range(n):
            a=2*math.pi*j/n
            # The soft rectangular section reads as Lugia's finger feathers.
            ca,sa=math.cos(a),math.sin(a)
            ca=math.copysign(abs(ca)**.67,ca);sa=math.copysign(abs(sa)**.67,sa)
            vertices.append(p+width*max(.006,sizes[i].x)*ca+depth*max(.006,sizes[i].y)*sa)
    for i in range(len(path)-1):
        for j in range(n):
            a,b=i*n+j,i*n+(j+1)%n;faces.append((a,b,b+n,a+n))
    a,b=len(vertices),len(vertices)+1;vertices.extend([path[0],path[-1]])
    for j in range(n):
        faces.append((a,(j+1)%n,j));k=(len(path)-1)*n;faces.append((b,k+j,k+(j+1)%n))
    return c.mesh(name,vertices,faces,WHITE)


def fin(name,outline,color=BLUE,thickness=.045):
    points=[Vector(p) for p in outline];border=[]
    for i in range(len(points)):
        a,b,cc,d=points[(i-1)%len(points)],points[i],points[(i+1)%len(points)],points[(i+2)%len(points)]
        for j in range(5):
            t=j/5;border.append(.5*((2*b)+(-a+cc)*t+(2*a-5*b+4*cc-d)*t*t+(-a+3*b-3*cc+d)*t*t*t))
    center=sum(border,Vector())/len(border);n=len(border)
    normal=(points[1]-points[0]).cross(points[2]-points[0]).normalized()
    vertices=[];faces=[];rings=7
    for s in (-1,1):
        base=len(vertices);vertices.append(center+normal*s*thickness)
        for ring in range(1,rings+1):
            t=ring/rings
            for p in border:vertices.append(center.lerp(p,t)+normal*s*thickness*math.sqrt(max(0,1-t*t)))
        for j in range(n):faces.append((base,base+1+j,base+1+(j+1)%n))
        for ring in range(rings-1):
            for j in range(n):
                a,b=base+1+ring*n+j,base+1+ring*n+(j+1)%n;faces.append((a,b,b+n,a+n))
    obj=c.mesh(name,vertices,faces,color)
    m=obj.modifiers.new('Shared closed fin rim','WELD');m.merge_threshold=.00001;c.apply(obj,m)
    return obj


def broad_wing(name,outline,right=False):
    """Five broad finger feathers: an authored closed concave wing silhouette."""
    poly=[Vector((x,z,0)) for x,z in outline];n=len(poly)
    triangles=tessellate_polygon([poly]);vertices=[]
    for side in (-1,1):
        for x,z in outline:
            y=(.08+.025*x) if right else (-.10-.08*abs(x))
            depth=(.16-.055*min(max(z-2.7,0),1.6)) if right else (.19-.045*min(abs(x),3))
            vertices.append((x,y+side*depth,z))
    faces=[]
    for triangle in triangles:
        idx=[p if isinstance(p,int) else poly.index(p) for p in triangle]
        faces.append(tuple(idx));faces.append(tuple(n+i for i in reversed(idx)))
    for i in range(n):faces.append((i,(i+1)%n,(i+1)%n+n,i+n))
    obj=c.mesh(name,vertices,faces,WHITE)
    m=obj.modifiers.new('Rounded finger feather tips','BEVEL');m.width=.070;m.segments=5;c.apply(obj,m)
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=5,use_grid_fill=True)
    fingers=([((1.45,3.22),(1.06,3.52),.65),((1.76,3.55),(1.44,4.15),.90),
              ((2.04,3.61),(2.03,4.40),1.05),((2.30,3.56),(2.56,4.21),1.10),
              ((2.54,3.35),(3.08,3.84),1.00)] if right else
             [((-1.77,2.45),(-1.64,3.04),.75),((-2.12,2.47),(-2.30,3.17),.90),
              ((-2.40,2.33),(-3.14,2.70),1.05),((-2.43,2.10),(-3.28,2.04),1.00),
              ((-2.25,1.95),(-2.75,1.60),.85)])
    for vertex in bm.verts:
        x,y,z=vertex.co
        center_x,center_z=(2.02,3.34) if right else (-2.07,2.20)
        fullness=math.exp(-((x-center_x)/.55)**2-((z-center_z)/.46)**2)
        baseline=(.08+.025*x) if right else (-.10-.08*abs(x))
        y=baseline+(y-baseline)*(1+.35*fullness)
        vertex.co.y=y
        p=Vector((x,z));choices=[]
        for start,end,angle in fingers:
            a,b=Vector(start),Vector(end);axis=(b-a).normalized();length=(b-a).length
            q=(p-a).dot(axis);across=p-a-axis*q
            if q>0 and q<length+.22 and across.length<.28:
                choices.append((across.length,a,axis,q,across,length,angle))
        if choices:
            _,a,axis,q,across,length,angle=min(choices,key=lambda item:item[0])
            radius=length/angle;theta=q/radius
            base_y=(.08+.025*a.x) if right else (-.10-.08*abs(a.x))
            depth=y-base_y
            bent=a+axis*(radius*math.sin(theta)+depth*math.sin(theta))+across
            vertex.co.x=bent.x;vertex.co.z=bent.y
            vertex.co.y=base_y-radius*(1-math.cos(theta))+depth*math.cos(theta)
        # Cup and twist the entire palm independently from the finger curl.
        if right:
            pivot=Vector((1.0,.105,2.6));axis=Vector((.65,0,.76)).normalized()
            angle=-.35*min(1,max(0,(z-2.5)/.7))
        else:
            pivot=Vector((-1.35,-.208,2.20));axis=Vector((-1,0,0))
            angle=-.55*min(1,max(0,(-x-1.1)/1.0))
        vertex.co=pivot+Quaternion(axis,angle)@(vertex.co-pivot)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
    return obj


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;asset=bpy.data.collections.new('Pokemon_Lugia');scene.collection.children.link(asset)
    c.COLLECTION=asset;c.MATERIALS.clear()
    for color in (WHITE,BELLY,BLUE,INK,PINK,'6E4257'):
        sh=c.material(color).node_tree.nodes.get('Principled BSDF')
        sh.inputs['Roughness'].default_value=.54;sh.inputs['Specular IOR Level'].default_value=.21

    parts=[c.ell('Pear-shaped aquatic body',(0,.14,1.63),(.75,.54,.83),WHITE),
           c.tube('Long flowing neck',[(0,-.02,2.06),(-.10,-.31,2.40),(-.24,-.69,2.77),(-.34,-1.00,3.12),(-.42,-1.14,3.34)],
                  [(.32,.29),(.25,.24),(.20,.19),(.16,.17),(.16,.16)],WHITE,48,10)]
    # Asymmetric arms create the characteristic one-up / one-out flying silhouette.
    parts.append(broad_wing('Left five-finger wing',
        [(-.35,2.35),(-1.10,2.43),(-1.65,2.40),(-1.50,2.98),(-1.78,3.10),(-1.97,2.63),
         (-2.15,3.22),(-2.45,3.13),(-2.27,2.51),(-3.08,2.84),(-3.20,2.57),(-2.40,2.21),
         (-3.29,2.18),(-3.26,1.89),(-2.30,2.00),(-2.80,1.68),(-2.70,1.52),
         (-1.70,1.77),(-1.30,1.95),(-.45,1.98)]))
    parts.append(broad_wing('Right five-finger wing',
        [(.40,2.35),(.95,2.65),(1.35,2.95),(1.40,3.10),(.98,3.33),(.94,3.57),(1.18,3.65),
         (1.65,3.28),(1.68,3.44),(1.32,4.05),(1.55,4.24),(1.92,3.65),(1.89,4.40),
         (2.17,4.40),(2.20,3.66),(2.44,4.28),(2.69,4.14),(2.43,3.51),(2.98,3.96),
         (3.17,3.73),(2.62,3.15),(2.20,2.91),(1.60,2.65),(.95,2.03),(.40,1.98)],True))

    # Powerful but compact hind legs, each ending in three broad white toes.
    for s in (-1,1):
        by=-.05 if s<0 else .22
        parts.append(c.tube('Landing leg '+str(s),[(s*.40,.12,1.12),(s*.57,.12,.74),(s*.52,by,.41),(s*.52,by-.13,.23)],
                            [.30,.26,.15,.13],WHITE,36,10))
        parts.append(c.ell('Three-toed foot '+str(s),(s*.52,by-.22,.20),(.25,.33,.15),WHITE))
        for k in (-1,0,1):
            parts.append(c.tube('Broad toe '+str(s)+' '+str(k),
                [(s*.52+k*.14,by-.32,.19),(s*.52+k*.165,by-.54,.145),(s*.52+k*.17,by-.62,.14)],
                [(.075,.08),(.07,.065),(.03,.035)],WHITE,24,8))

    parts.append(c.tube('Long curved tail',
        [(0,.43,1.38),(.29,.93,1.16),(.65,1.63,.91),(.93,2.31,.89),(.77,2.91,1.06),(.32,3.24,1.34)],
        [(.32,.29),(.25,.23),(.17,.16),(.12,.11),(.075,.07),(.009,.009)],WHITE,40,10))
    body=c.union('01_Continuous white body • neck wings legs tail',parts,WHITE,.021)
    m=body.modifiers.new('Balanced sculpt density','DECIMATE');m.ratio=.60;c.apply(body,m)
    m=body.modifiers.new('Smooth aquatic silhouette','SMOOTH');m.factor=.5;m.iterations=12;c.apply(body,m)
    belly=[(0,2.12),(-.23,2.31),(-.40,2.15),(-.54,1.95),(-.56,1.67),(-.48,1.42),(-.31,1.19),
           (-.15,1.10),(0,1.07),(.15,1.10),(.31,1.19),(.48,1.42),(.56,1.67),(.54,1.95),(.40,2.15),(.23,2.31)]
    belly=[(x*1.13,z) for x,z in belly]
    belly_center=np.array((0,1.72))
    belly_inner=[tuple(belly_center+(np.array(p)-belly_center)*.975) for p in belly]
    paint_front(body,'Lugia pale blue belly',OUT/'Textures'/'Lugia_belly.png',WHITE,
                [('5577AF',belly),(BELLY,belly_inner)],(-3.5,3.3,0,4.55),3072)

    # Slender water-bird head, hooked beak and swept white crest.
    head_parts=[c.tube('Water bird skull and hooked beak',
        [(0,-.97,3.47),(0,-1.28,3.48),(0,-1.53,3.42),(0,-1.73,3.36),(0,-1.83,3.25)],
        [(.15,.18),(.20,.19),(.17,.13),(.095,.075),(.009,.009)],WHITE,48,10),
        c.tube('White rear head crest',[(0,-1.05,3.55),(0,-.87,3.70),(0,-.69,3.81)],
        [(.14,.12),(.10,.075),(.006,.006)],WHITE,32,8),
        c.tube('Lower bird jaw',[(0,-1.11,3.30),(0,-1.35,3.13),(0,-1.60,3.12),(0,-1.70,3.17)],
        [(.15,.12),(.14,.075),(.08,.05),(.012,.012)],WHITE,36,9)]
    head=c.union('02_Streamlined head and lower beak',head_parts,WHITE,.010)
    m=head.modifiers.new('Head sculpt polish','SMOOTH');m.factor=.50;m.iterations=7;c.apply(head,m)
    face=[]
    for s in (-1,1):
        mask=[(s*.045,3.385),(s*.095,3.59),(s*.27,3.70),(s*.285,3.51),(s*.21,3.355)]
        face.append((BLUE,mask))
        eye=[(s*.075,3.465),(s*.22,3.496),(s*.197,3.454),(s*.146,3.440)]
        face.append(('FFFFFF',eye));face.append((INK,ellipse(s*.160,3.463,.011,.018)))
        face.append(('FFFFFF',ellipse(s*.157,3.470,.0035,.0045)))
        face.append((INK,ellipse(s*.065,3.375,.012,.009)))
        c.tube('03_Long swept blue eye crest '+str(s),
            [(s*.16,-1.37,3.43),(s*.16,-1.10,3.57),(s*.09,-.72,3.74)],
            [(.075,.025),(.070,.020),(.003,.003)],BLUE,24,8)
    paint_front(head,'Lugia painted eyes',OUT/'Textures'/'Lugia_face.png',WHITE,face,(-.31,.31,3.04,3.90),2048)
    c.ell('04_Mouth cavity',(0,-1.42,3.275),(.135,.25,.175),'6E4257')
    c.ell('04_Pink tongue',(0,-1.57,3.18),(.09,.105,.028),PINK)
    for s in (-1,1):
        for k in range(2):
            c.tube('04_Small beak tooth '+str(s)+' '+str(k),
                [(s*(.085+.018*k),-1.59+k*.14,3.345),(s*(.080+.015*k),-1.59+k*.14,3.285)],
                [.025,.003],WHITE,16,6)

    # Five pairs of blue dorsal plates, running from shoulders to tail base.
    bpy.context.view_layer.update();body_tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
    for i,(x,y,z) in enumerate([(.25,.28,2.37),(.35,.42,2.13),(.38,.53,1.89),(.34,.66,1.64),(.26,.84,1.40)]):
        for s in (-1,1):
            ray_origin=body.matrix_world.inverted()@Vector((s*x,8,z))
            hit,_,_,_=body_tree.ray_cast(ray_origin,Vector((0,-1,0)))
            root_y=(body.matrix_world@hit).y-.045 if hit is not None else y
            fin('05_Dorsal plate pair '+str(i+1)+' '+str(s),
                [(s*x,root_y,z-.08),(s*(x+.28),root_y+.38,z-.10),(s*(x+.40),root_y+.48,z-.01),
                 (s*(x+.36),root_y+.47,z+.12),(s*(x+.13),root_y+.18,z+.12),(s*x,root_y,z+.08)],BLUE,.035)
    # The long white tail has two blue terminal spikes; it is not a split tail.
    fin('06_Left blue tail spike',[(.55,2.76,1.01),(.53,2.94,1.20),(.40,3.05,1.49),(.66,2.97,1.15)],BLUE,.040)
    fin('06_Right blue tail spike',[(.82,2.73,1.00),(.91,2.93,1.20),(1.06,3.02,1.46),(.78,2.97,1.14)],BLUE,.040)

    for obj in asset.objects:
        if obj.name.startswith(('02_','03_','04_')):
            obj.location.x-=.42
            pivot=Vector((-.42,-1.15,3.42))
            obj.location=pivot+(obj.location-pivot)*1.15;obj.scale*=1.15

    # Every component has UV data. Colored paintings are packed and embedded.
    for obj in asset.objects:
        if obj.type!='MESH':continue
        obj['pokemon']='Lugia';obj['part']=obj.name
        if not obj.data.uv_layers:
            uv=obj.data.uv_layers.new(name='Editable planar UV')
            points=np.array([list(v.co) for v in obj.data.vertices]);low=points.min(axis=0)
            span=np.maximum(points.max(axis=0)-low,.001)
            for loop in obj.data.loops:
                p=points[loop.vertex_index];uv.data[loop.index].uv=((p[0]-low[0])/span[0],(p[2]-low[2])/span[2])
    bpy.context.view_layer.update()
    points=[o.matrix_world@v.co for o in asset.objects if o.type=='MESH' for v in o.data.vertices]
    low=min(p.z for p in points);high=max(p.z for p in points);scale=5.2/(high-low)
    for obj in asset.objects:
        obj.location.z-=low;obj.location*=scale;obj.scale*=scale
        c.active(obj);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    root=bpy.data.objects.new('root_Lugia',None);asset.objects.link(root)
    root['korean']='루기아';root['dex']=249;root['wing_fingers_per_side']=5;root['dorsal_fin_pairs']=5
    root['pose']='Landing pose based on official asymmetrically spread-wing artwork'
    root['scale_note']='Total posed height normalized to 5.2 m; wing tip height is not anatomical standing height'
    for obj in asset.objects:
        if obj!=root:obj.parent=root
    studio()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in asset.objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=body
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Lugia.blend'))
    bpy.ops.export_scene.gltf(filepath=str(OUT/'Lugia.glb'),export_format='GLB',use_selection=True,export_apply=True,
                             export_animations=False,export_cameras=False,export_lights=False,export_extras=True)
    (OUT/'references'/'sources.json').write_text(json.dumps({
        'official_pokedex':'https://www.pokemon.com/us/pokedex/lugia',
        'official_artwork':'https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/249.png',
        'official_go_artwork':'https://www.pokemon.com/static-assets/content-assets/cms2/img/video-games/_tiles/pokemon-go/art/lugia.png',
        'notes':'Hand-authored geometry; references used for visual comparison only.'},indent=2),encoding='utf-8')


def studio():
    scene=bpy.context.scene;collection=bpy.data.collections.new('90_Presentation');scene.collection.children.link(collection)
    def move(obj):
        for old in list(obj.users_collection):old.objects.unlink(obj)
        collection.objects.link(obj)
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=3.7,depth=.12,location=(0,.70,-.075))
    obj=bpy.context.object;obj.name='Display • broad slate plinth';move(obj);obj.data.materials.append(c.material('263746'))
    m=obj.modifiers.new('Rounded rim','BEVEL');m.width=.04;m.segments=3;c.apply(obj,m)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.14))
    obj=bpy.context.object;obj.name='Studio floor';move(obj);obj.data.materials.append(c.material('182431'))
    for name,position,power,color,size in [
        ('Key softbox',(-6,-8,10),2200,(1,.91,.82),6),
        ('Cool fill',(8,-5,7),1500,(.72,.85,1),6),
        ('Back rim',(0,8,10),2800,(.70,.84,1),5)]:
        data=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
        obj.location=position;obj.rotation_euler=(Vector((0,.5,2.4))-obj.location).to_track_quat('-Z','Y').to_euler()
        data.energy=power;data.color=color;data.shape='DISK';data.size=size
    world=bpy.data.worlds.new('Studio world');world.use_nodes=True;scene.world=world
    world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.16,.21,.28,1)
    world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.40
    data=bpy.data.cameras.new('Camera');obj=bpy.data.objects.new('Camera',data);collection.objects.link(obj);scene.camera=obj;data.type='ORTHO'
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=1600;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.unit_settings.system='METRIC'
    set_view('preview')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_distance=9.0
                area.spaces.active.region_3d.view_location=(0,.5,2.4)
                area.spaces.active.region_3d.view_rotation=obj.rotation_euler.to_quaternion()


VIEWS={'preview':((7,-13,7),(0,.55,2.45),10.0),
       'front':((0,-15,2.6),(0,.3,2.45),10.0),
       'back':((-7,13,7),(0,.7,2.45),10.0),
       'side':((15,-1,6),(0,.7,2.45),8.8),
       'face':((5,-12,6.4),(0,-1.55,3.75),2.45),
       'clay':((7,-13,7),(0,.55,2.45),10.0)}


def set_view(name):
    scene=bpy.context.scene;camera=scene.camera;position,target,scale=VIEWS[name]
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale


def render(opt):
    scene=bpy.context.scene
    if opt.gpu:
        pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
        for device in pref.devices:device.use=device.type=='OPTIX'
        if not any(d.type=='OPTIX' for d in pref.devices):raise RuntimeError('No OPTIX GPU')
        scene.cycles.device='GPU'
    scene.cycles.samples=12 if opt.draft else 48;scene.render.resolution_percentage=50 if opt.draft else 100
    for name in (VIEWS if opt.full else [opt.view]):
        set_view(name);scene.view_layers[0].material_override=None
        if name=='clay':scene.view_layers[0].material_override=c.material('9BAABB',.68)
        scene.render.filepath=str(OUT/'renders'/(name+('_draft' if opt.draft else '')+'.png'));bpy.ops.render.render(write_still=True)
    scene.view_layers[0].material_override=None


if __name__=='__main__':
    opt=options()
    if opt.render_only:bpy.ops.wm.open_mainfile(filepath=str(OUT/'Lugia.blend'))
    else:build()
    render(opt)
    print('LUGIA_BUILD_OK',flush=True)
