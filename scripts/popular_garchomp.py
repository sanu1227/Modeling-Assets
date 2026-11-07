"""Reference-led Garchomp fan sculpture, separate from all earlier models.

Front -Y, Z up. Run in Blender with -- --draft (CPU 2 threads, 800 px).
--full renders six final views; --render-only reads saved source; --gpu uses OPTIX.
"""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import pokemon_common as c
from popular_painting import paint_front
OUT=ROOT/'assets'/'PokemonPopular'/'Garchomp'
(OUT/'renders').mkdir(parents=True,exist_ok=True)
BLUE='465475';DARK='303D58';RED='D66550';GOLD='EBC44A';IVORY='FAF4DF';INK='202B3B'
PAINT_REGIONS=[]


def options():
    p=argparse.ArgumentParser()
    p.add_argument('--draft',action='store_true');p.add_argument('--full',action='store_true')
    p.add_argument('--render-only',action='store_true');p.add_argument('--gpu',action='store_true')
    p.add_argument('--view',default='preview')
    return p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


def lens(name,outline,color,thickness=.12):
    """Closed pillowed fin with a sharp silhouette and rounded broad faces."""
    border=[Vector(p) for p in outline];n=len(border)
    center=sum(border,Vector())/n
    # A local normal also works for sagittal dorsal and tail fins.
    normal=(border[1]-border[0]).cross(border[2]-border[0]).normalized()
    vertices=[];faces=[];rings=7
    for side in (-1,1):
        base=len(vertices);vertices.append(center+normal*side*thickness)
        for ring in range(1,rings+1):
            t=ring/rings
            for point in border:
                vertices.append(center.lerp(point,t)+normal*side*thickness*math.sqrt(max(0,1-t*t)))
        for j in range(n):faces.append((base,base+1+j,base+1+(j+1)%n))
        for ring in range(rings-1):
            for j in range(n):
                a,b=base+1+ring*n+j,base+1+ring*n+(j+1)%n
                faces.append((a,b,b+n,a+n))
    obj=c.mesh(name,vertices,faces,color)
    m=obj.modifiers.new('Shared watertight fin rim','WELD');m.merge_threshold=.00001;c.apply(obj,m)
    return obj


def ring_line(name,center,axis,radius_a,radius_b,color,thickness=.009):
    axis=Vector(axis).normalized()
    ref=Vector((0,0,1)) if abs(axis.z)<.95 else Vector((0,1,0))
    u=axis.cross(ref).normalized();v=axis.cross(u).normalized();center=Vector(center)
    # Mesh torus with closed periodic topology.
    vertices=[];faces=[];n=64;m=10
    for i in range(n):
        a=2*math.pi*i/n
        p=center+u*radius_a*math.cos(a)+v*radius_b*math.sin(a)
        normal=(u*math.cos(a)+v*math.sin(a)).normalized()
        for j in range(m):
            b=2*math.pi*j/m
            vertices.append(p+normal*thickness*math.cos(b)+axis*thickness*math.sin(b))
    for i in range(n):
        for j in range(m):faces.append((i*m+j,((i+1)%n)*m+j,((i+1)%n)*m+(j+1)%m,i*m+(j+1)%m))
    return c.mesh(name,vertices,faces,color)


def skin_surface(tree,name,outline,color,offset=.012,normal_sign=-1):
    """Record pigment in painter order; apply one packed texture to the skin."""
    PAINT_REGIONS.append((color,outline))


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene
    asset=bpy.data.collections.new('Pokemon_Garchomp');scene.collection.children.link(asset)
    c.COLLECTION=asset;c.MATERIALS.clear();PAINT_REGIONS.clear()
    for color in (BLUE,DARK,RED,GOLD,IVORY,INK,'702F37','E89789'):
        sh=c.material(color).node_tree.nodes.get('Principled BSDF')
        sh.inputs['Roughness'].default_value=.56;sh.inputs['Specular IOR Level'].default_value=.22

    # Athletic hourglass torso, long shark neck, wide hips and digitigrade legs.
    pieces=[c.tube('Continuous torso and long neck',
                   [(0,.16,1.18),(0,.14,1.64),(0,.04,2.03),(0,.015,2.42),
                    (0,.035,2.72),(0,.13,2.94),(0,.16,3.31),(0,.14,3.65),(0,.08,3.86)],
                   [(.28,.30),(.62,.47),(.44,.36),(.42,.34),(.37,.31),
                    (.32,.28),(.29,.26),(.30,.28),(.32,.28)],BLUE,56,10)]
    for s in (-1,1):
        pieces += [c.tube('Continuous digitigrade leg '+str(s),
                           [(s*.36,.17,1.65),(s*.64,.10,1.36),(s*.88,-.015,.94),(s*.78,.09,.61),(s*.88,-.01,.27)],
                           [.35,.34,.25,.20,.18],BLUE,40,10),
                   c.ell('Broad clawed foot '+str(s),(s*.89,-.22,.15),(.29,.40,.16),BLUE),
                   c.tube('Shoulder and upper arm '+str(s),[(s*.33,.02,2.71),(s*.74,-.025,2.55),(s*1.18,-.04,2.28)],
                           [.225,.20,.16],BLUE,36,10),
                   c.tube('Wing leading edge '+str(s),[(s*1.15,-.04,2.27),(s*1.58,-.08,2.35),(s*2.05,-.12,2.45)],
                           [.17,.16,.12],BLUE,36,10)]
    # Pointed shark-like upper jaw; the head is longer in Y than in Z.
    pieces.append(c.tube('Shark skull and upper muzzle',
        [(0,.45,3.87),(0,.12,3.96),(0,-.25,3.92),(0,-.58,3.80),(0,-.92,3.73)],
        [(.20,.20),(.45,.24),(.43,.22),(.34,.16),(.145,.08)],BLUE,48,10))
    pieces.append(c.ell('Lower jaw',(0,-.34,3.42),(.31,.43,.15),BLUE))
    for s in (-1,1):
        pieces.append(c.tube('Horizontal hammerhead horn '+str(s),
            [(s*.34,.12,3.96),(s*.63,.14,4.03),(s*.88,.15,4.12),(s*1.05,.14,4.22)],
            [(.185,.215),(.205,.24),(.155,.18),(.006,.008)],BLUE,40,10))

    # Thick tail curves behind the body and ends in a vertical shark fin.
    pieces.append(c.tube('Swept muscular tail',
        [(0,.40,1.46),(-.20,.83,1.24),(-.74,1.28,.95),(-1.43,1.61,.73),(-1.95,1.76,.69)],
        [(.35,.32),(.30,.28),(.22,.21),(.15,.15),(.10,.10)],BLUE,40,10))
    skin=c.union('01_Continuous shark-dragon skin',pieces,BLUE,.021)
    decimate=skin.modifiers.new('Balanced sculpt density','DECIMATE');decimate.ratio=.65;c.apply(skin,decimate)
    smooth=skin.modifiers.new('Gentle surface polish','SMOOTH');smooth.factor=.5;smooth.iterations=12;c.apply(skin,smooth)
    bpy.context.view_layer.update()
    tree=BVHTree.FromObject(skin,bpy.context.evaluated_depsgraph_get())

    # Canonical red throat/chest and the distinct golden shield on the lower belly.
    skin_surface(tree,'02_Red throat and chest',
        [(-.19,3.49),(-.25,3.26),(-.28,2.94),(-.34,2.76),(-.44,2.57),(-.33,2.31),(-.29,1.93),
         (0,1.83),(.29,1.93),(.33,2.31),(.44,2.57),(.34,2.76),(.28,2.94),(.25,3.26),(.19,3.49)],RED,.015)
    skin_surface(tree,'03_Golden lower belly shield',
        [(-.24,1.93),(-.336,1.80),(-.216,1.66),(0,1.48),(.216,1.66),(.336,1.80),(.24,1.93),(0,1.99)],GOLD,.026)
    # The forehead mark is a broad asymmetric star/arrow, not a raised ornament.
    skin_surface(tree,'04_Golden forehead marking',
        [(-.176,4.10),(.152,4.10),(.08,4.025),(.16,3.956),(.044,3.98),(-.044,3.812),(-.092,3.98),(-.164,3.996)],GOLD,.014)

    # A deep open mouth framed by the upper muzzle and sculpted lower jaw.
    c.ell('05_Mouth dark interior',(0,-.43,3.57),(.285,.37,.19),'702F37')
    c.ell('05_Lower tongue',(0,-.54,3.445),(.20,.23,.035),'E89789')
    for s in (-1,1):
        for k,(y,z) in enumerate([(-.66,3.665),(-.48,3.71),(-.28,3.74)]):
            x=s*(.19+.025*k)
            c.tube('06_Upper shark tooth '+str(s)+'_'+str(k),[(x,y,z),(x*.96,y-.005,z-.085),(x*.92,y+.015,z-.165)],
                   [.055,.038,.003],IVORY,18,6)
        for k,(y,z) in enumerate([(-.66,3.46),(-.46,3.44),(-.27,3.46)]):
            x=s*(.18+.022*k)
            c.tube('06_Lower shark tooth '+str(s)+'_'+str(k),[(x,y,z),(x*.97,y-.005,z+.065),(x*.92,y-.01,z+.125)],
                   [.050,.034,.003],IVORY,18,6)
        eye=[(s*.14,3.980),(s*.28,4.013),(s*.378,4.000),(s*.32,3.943),(s*.235,3.940)]
        skin_surface(tree,'07_Angular eye socket '+str(s),eye,INK,.020)
        mid=np.mean(eye,axis=0)
        inner=[tuple(mid+(np.array(p)-mid)*.72) for p in eye]
        skin_surface(tree,'07_Golden eye '+str(s),inner,GOLD,.034)
        skin_surface(tree,'07_Slit pupil '+str(s),
            [(s*.255,3.995),(s*.274,3.999),(s*.268,3.953),(s*.253,3.954)],INK,.043)
        # Narrow gill/neck segmentation, horn joints and ankle scale bands.
        ring_line('08_Horn seam outer '+str(s),(s*.87,.15,4.12),(s*.95,0,.25),.149,.173,DARK,.007)
        ring_line('08_Horn seam inner '+str(s),(s*.62,.14,4.03),(s*.95,0,.25),.204,.234,DARK,.007)
    ankle_regions=[]
    for s in (-1,1):
        for z in (.37,.52):
            ankle_regions.append((DARK,[(s*.60,z-.008),(s*1.14,z-.008),(s*1.14,z+.008),(s*.60,z+.008)]))
    PAINT_REGIONS.extend(ankle_regions)

    paint_front(skin,'Garchomp painted skin',OUT/'Textures'/'Garchomp_skin.png',
                BLUE,PAINT_REGIONS,(-2.6,2.6,0,4.45),3072)
    back_regions=ankle_regions+[(DARK,[(-.40,z-.008),(.40,z-.008),(.40,z+.008),(-.40,z+.008)]) for z in (3.18,3.36,3.54)]
    paint_front(skin,'Garchomp back scale markings',OUT/'Textures'/'Garchomp_back.png',
                BLUE,back_regions,(-2.6,2.6,0,4.45),2048,normal_sign=1)

    # Broad arm fins, single crescent hand claws and three toe claws.
    for s in (-1,1):
        lens('09_Arm fin '+str(s),
            [(s*1.16,.005,2.28),(s*2.055,-.12,2.45),(s*2.02,.015,1.80),
             (s*1.78,.14,.94),(s*1.63,.12,1.19),(s*1.36,.07,1.88)],BLUE,.09)
        c.tube('10_Single scythe hand claw '+str(s),
            [(s*2.04,-.12,2.45),(s*2.21,-.17,2.36),(s*2.39,-.22,2.13),(s*2.48,-.24,1.93)],
            [(.12,.075),(.105,.065),(.065,.04),(.003,.003)],IVORY,28,9)
        for k in range(3):
            x=s*(.90+.17*k);z=2.52-.02*k
            c.tube('11_Arm fin spine '+str(s)+'_'+str(k),
                [(x,-.06,z-.05),(x+s*.025,-.075,z+.11),(x+s*.04,-.09,z+.23-k*.025)],
                [.060,.045,.003],IVORY,18,6)
        for k in range(2):
            x=s*(.51+.23*k);z=1.66-.16*k
            c.tube('11_Hip spine '+str(s)+'_'+str(k),
                [(x,-.15,z),(x+s*.09,-.20,z+.14),(x+s*.13,-.22,z+.28)],
                [.075,.052,.003],IVORY,18,6)
        for k in (-1,0,1):
            x=s*.89+k*.17;y=-.47+abs(k)*.035
            c.tube('12_Toe claw '+str(s)+'_'+str(k),
                [(x,y,.16),(x,y-.16,.12),(x+k*.035,y-.30,.025)],
                [(.082,.10),(.067,.075),(.003,.003)],IVORY,24,8)

    # Sagittal dorsal fin and the broad vertical tail blade.
    lens('13_Dorsal shark fin',
        [(0,.32,2.30),(0,.44,3.03),(0,.90,3.43),(0,.86,3.00),
         (0,1.02,2.89),(0,.83,2.63),(0,.50,2.32)],BLUE,.085)
    lens('14_Tail terminal fin',
        [(-1.76,1.66,.79),(-2.08,1.83,1.36),(-2.02,1.87,.94),
         (-2.19,1.90,.91),(-2.08,1.88,.69),(-2.33,1.97,.18),
         (-1.93,1.80,.44),(-1.72,1.64,.58)],BLUE,.075)
    for i,(center,axis,ra,rb) in enumerate([
        ((-.67,1.22,1.00),(-.8,.6,-.3),.228,.22),
        ((-1.03,1.42,.86),(-.9,.4,-.25),.187,.185),
        ((-1.37,1.59,.75),(-.9,.4,-.12),.155,.153)]):
        ring_line('15_Tail scale ring '+str(i),center,axis,ra,rb,DARK,.007)

    # Reference proportion pass: longer shins and raised hips, with a shorter
    # chest. The arm-fin tips remain low, producing the characteristic long fins.
    for obj in list(asset.objects):
        if obj.type!='MESH':continue
        raw=np.empty(len(obj.data.vertices)*3,dtype=np.float64);obj.data.vertices.foreach_get('co',raw)
        matrix=np.array(obj.matrix_world);points=raw.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]
        original=points[:,2].copy()
        corrected=np.interp(original,[0,.25,.95,1.65,2.1,2.7,4.5],[0,.25,1.20,1.90,2.28,2.7,4.5])
        if obj.name.startswith('09_Arm fin'):
            corrected=original+(corrected-original)*np.clip((original-1.0)/.8,0,1)
        points[:,2]=corrected
        # Enlarge the shark wedge and shorten the exposed neck as one continuous
        # deformation, including eyes, teeth, markings and hammerhead horns.
        head_weight=np.clip((original-2.90)/.40,0,1)
        points[:,0]*=1+.18*head_weight
        points[:,1]=.10+(points[:,1]-.10)*(1+.20*head_weight)
        points[:,2]+=head_weight*(-.25+.15*(original-3.30))
        local=(points-matrix[:3,3])@np.linalg.inv(matrix[:3,:3]).T
        obj.data.vertices.foreach_set('co',local.ravel());obj.data.update()

    # Simple editable UVs for solid-color materials, with no external dependencies.
    for obj in asset.objects:
        if obj.type!='MESH':continue
        obj['pokemon']='Garchomp';obj['part']=obj.name
        if not obj.data.uv_layers:
            uv=obj.data.uv_layers.new(name='Editable planar UV')
            coords=np.array([list(v.co) for v in obj.data.vertices]);low=coords.min(axis=0)
            span=np.maximum(coords.max(axis=0)-low,.001)
            for loop in obj.data.loops:
                p=coords[loop.vertex_index];uv.data[loop.index].uv=((p[0]-low[0])/span[0],(p[2]-low[2])/span[2])
    bpy.context.view_layer.update()
    points=[o.matrix_world@v.co for o in asset.objects if o.type=='MESH' for v in o.data.vertices]
    low=min(p.z for p in points);high=max(p.z for p in points);factor=1.90/(high-low)
    for obj in asset.objects:
        obj.location.z-=low;obj.location*=factor;obj.scale*=factor
        c.active(obj);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    root=bpy.data.objects.new('root_Garchomp',None);asset.objects.link(root)
    root['korean']='한카리아스';root['dex']=445
    root['source']='Hand-authored sculpture from official artwork; no extracted game mesh'
    root['static_model']=True
    for obj in asset.objects:
        if obj!=root:obj.parent=root
    studio()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in asset.objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=skin
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Garchomp.blend'))
    bpy.ops.export_scene.gltf(filepath=str(OUT/'Garchomp.glb'),export_format='GLB',use_selection=True,
                             export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True)
    (OUT/'references'/'sources.json').write_text(json.dumps({
        'official_pokedex':'https://www.pokemon.com/us/pokedex/garchomp',
        'official_artwork':'https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/445.png',
        'official_japanese_reference':'https://www.pokemon.jp/special/dragontype/lab/pokemon04.html',
        'supplementary_home_artwork':'https://images.wikidexcdn.net/mwuploads/wikidex/4/4f/latest/20210524164708/Garchomp_HOME.png',
        'notes':'Artworks used for visual reference only.'},indent=2),encoding='utf-8')


def studio():
    scene=bpy.context.scene;collection=bpy.data.collections.new('90_Presentation');scene.collection.children.link(collection)
    def move(obj):
        for old in list(obj.users_collection):old.objects.unlink(obj)
        collection.objects.link(obj)
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=1.23,depth=.05,location=(0,.12,-.032))
    obj=bpy.context.object;obj.name='Display • slate plinth';move(obj);obj.data.materials.append(c.material('263746'))
    m=obj.modifiers.new('Rounded rim','BEVEL');m.width=.018;m.segments=3;c.apply(obj,m)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.06))
    obj=bpy.context.object;obj.name='Studio floor';move(obj);obj.data.materials.append(c.material('182431'))
    for name,position,power,color,size in [
        ('Key softbox',(-3,-4,5.5),650,(1,.90,.79),4),
        ('Cool fill',(4,-2,3.4),450,(.70,.84,1),3),
        ('Back rim',(0,3.5,4.5),750,(.70,.85,1),3)]:
        data=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,data);collection.objects.link(obj)
        obj.location=position;obj.rotation_euler=(Vector((0,0,1))-obj.location).to_track_quat('-Z','Y').to_euler()
        data.energy=power;data.color=color;data.shape='DISK';data.size=size
    world=bpy.data.worlds.new('Studio world');world.use_nodes=True;scene.world=world
    world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.16,.21,.28,1)
    world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.45
    data=bpy.data.cameras.new('Camera');obj=bpy.data.objects.new('Camera',data);collection.objects.link(obj);scene.camera=obj;data.type='ORTHO'
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=1600;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    scene.unit_settings.system='METRIC';set_view('preview')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_distance=3.4
                area.spaces.active.region_3d.view_location=(0,0,.95)
                area.spaces.active.region_3d.view_rotation=obj.rotation_euler.to_quaternion()


VIEWS={'preview':((3,-7,2.8),(0,.05,.94),2.75),
       'front':((0,-8,1.02),(0,0,.94),2.75),
       'back':((-3,7,2.8),(0,.20,.94),2.75),
       'side':((7,-.5,2.2),(0,.18,.94),2.55),
       'face':((2.7,-7,2.4),(0,-.1,1.64),1.14),
       'clay':((3,-7,2.8),(0,.05,.94),2.75)}


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
    scene.cycles.samples=12 if opt.draft else 48
    scene.render.resolution_percentage=50 if opt.draft else 100
    for name in (VIEWS if opt.full else [opt.view]):
        set_view(name);scene.view_layers[0].material_override=None
        if name=='clay':scene.view_layers[0].material_override=c.material('9BAABB',.68)
        scene.render.filepath=str(OUT/'renders'/(name+('_draft' if opt.draft else '')+'.png'))
        bpy.ops.render.render(write_still=True)
    scene.view_layers[0].material_override=None


if __name__=='__main__':
    opt=options()
    if opt.render_only:bpy.ops.wm.open_mainfile(filepath=str(OUT/'Garchomp.blend'))
    else:build()
    render(opt)
    print('GARCHOMP_BUILD_OK',flush=True)
