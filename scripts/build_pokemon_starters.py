"""Build, export and render editable original-proportion Pokemon fan models.

Blender --background --factory-startup --python-exit-code 1 --python this.py
Use -- --render all|gen1,...|overview|front|clay to render an existing source.
Use -- --rebuild Name,Name to replace only those generated models.
"""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import pokemon_common as common
import pokemon_gen1_3, pokemon_gen4_6, pokemon_gen7_9, pokemon_bonus

OUT=ROOT/'assets'/'PokemonStarters'
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'models').mkdir(exist_ok=True)
(OUT/'renders').mkdir(exist_ok=True)
ROSTER=[]
rows=[
    [('Bulbasaur','이상해씨',1),('Charmander','파이리',4),('Squirtle','꼬부기',7)],
    [('Chikorita','치코리타',152),('Cyndaquil','브케인',155),('Totodile','리아코',158)],
    [('Treecko','나무지기',252),('Torchic','아차모',255),('Mudkip','물짱이',258)],
    [('Turtwig','모부기',387),('Chimchar','불꽃숭이',390),('Piplup','팽도리',393)],
    [('Snivy','주리비얀',495),('Tepig','뚜꾸리',498),('Oshawott','수댕이',501)],
    [('Chespin','도치마론',650),('Fennekin','푸호꼬',653),('Froakie','개구마르',656)],
    [('Rowlet','나몰빼미',722),('Litten','냐오불',725),('Popplio','누리공',728)],
    [('Grookey','흥나숭',810),('Scorbunny','염버니',813),('Sobble','울머기',816)],
    [('Sprigatito','나오하',906),('Fuecoco','뜨아거',909),('Quaxly','꾸왁스',912)],
    [('Browt','초로삐',None),('Pombon','포뭉이',None),('Gecqua','미초리',None)],
    [('Pikachu','피카츄',25),('Eevee','이브이',133)],
]
for g,row in enumerate(rows):
    for slot,(name,ko,dex) in enumerate(row):
        gx=(g%3-1)*10.5;gy=(g//3)*5.0
        offset=slot-(len(row)-1)/2
        ROSTER.append(dict(name=name,korean=ko,dex=dex,generation=g+1 if g<10 else None,
                           group='gen'+str(g+1) if g<10 else 'special',
                           type=['Grass','Fire','Water'][slot] if g<10 else 'Special',
                           gallery_position=[gx+offset*3.25,gy,0],
                           status='announced_2027' if g==9 else 'released',
                           glb='models/'+name+'.glb'))
BUILDERS={}
for module in (pokemon_gen1_3,pokemon_gen4_6,pokemon_gen7_9,pokemon_bonus):
    for item in ROSTER:
        fn=getattr(module,'build_'+item['name'].lower(),None)
        if fn:BUILDERS[item['name']]=fn
assert len(BUILDERS)==32


def collection(name):
    col=bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def build_model(item):
    name=item['name']
    old=bpy.data.collections.get('Pokemon_'+name)
    if old:
        for obj in list(old.objects):bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(old)
    col=collection('Pokemon_'+name)
    common.COLLECTION=col
    BUILDERS[name]()
    objs=list(col.objects)
    bpy.context.view_layer.update()
    coords=[o.matrix_world@v.co for o in objs if o.type=='MESH' for v in o.data.vertices]
    lo=Vector(tuple(min(p[i] for p in coords) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in coords) for i in range(3)))
    scale=min(2.6/(hi.z-lo.z),2.65/(hi.x-lo.x),2.85/(hi.y-lo.y))
    center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    root=bpy.data.objects.new('root_'+name,None);col.objects.link(root)
    root.empty_display_type='PLAIN_AXES';root.empty_display_size=.25
    for obj in objs:
        obj.location=(obj.location-center)*scale
        obj.scale*=scale
        common.active(obj);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        obj.name=name+'__'+obj.name
        obj.parent=root
        obj['pokemon']=name
    root['pokemon']=name;root['korean']=item['korean'];root['source']='Hand-authored fan model; official artwork reference'
    root['display_scale']='Individually normalized for the collection; not canonical real-world size'
    bpy.ops.object.select_all(action='DESELECT')
    for obj in col.objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.gltf(filepath=str(OUT/item['glb']),export_format='GLB',use_selection=True,
                             export_apply=True,export_animations=False,export_cameras=False,export_lights=False,
                             export_extras=True)
    root.location=item['gallery_position']
    root.rotation_euler.z=math.radians({'Snivy':-25,'Cyndaquil':-12,'Litten':-12,'Sprigatito':-12}.get(name,0))
    print('MODEL_READY '+name+' parts='+str(len(objs)),flush=True)


def text_label(col,name,body,location,size,color,font):
    data=bpy.data.curves.new(name,'FONT');data.body=body;data.size=size
    data.align_x='CENTER';data.align_y='CENTER';data.extrude=.0006;data.resolution_u=8;data.font=font
    obj=bpy.data.objects.new(name,data);col.objects.link(obj)
    obj.location=location;obj.rotation_euler=(math.pi/2,0,0)
    data.materials.append(common.material(color))
    return obj


def stage():
    scene=bpy.context.scene
    font=bpy.data.fonts.load('C:/Windows/Fonts/malgunbd.ttf')
    regular=bpy.data.fonts.load('C:/Windows/Fonts/segoeui.ttf')
    for item in ROSTER:
        name=item['name'];col=collection('Display_'+name);common.COLLECTION=col
        x,y,z=item['gallery_position']
        accent={'Grass':'649871','Fire':'C9755B','Water':'5798B3','Special':'C8AA66'}[item['type']]
        bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=1.48,depth=.42,location=(x,y,-.23))
        obj=common.finish(bpy.context.object,'Pedestal '+name,'D8DED8')
        mod=obj.modifiers.new('Rounded rim','BEVEL');mod.width=.065;mod.segments=4;common.apply(obj,mod)
        bpy.ops.mesh.primitive_torus_add(major_segments=96,minor_segments=12,location=(x,y,-.36),major_radius=1.47,minor_radius=.014)
        common.finish(bpy.context.object,'Type accent '+name,accent)
        text_label(col,'Korean name '+name,item['korean'],(x,y-1.515,-.15),.18,'273C44',font)
        num=f'#{item["dex"]:03}  ' if item['dex'] else '2027  '
        text_label(col,'English name '+name,num+name.upper(),(x,y-1.515,-.31),.080,'52656A',regular)
    studio=collection('90_Presentation');common.COLLECTION=studio
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.47))
    common.finish(bpy.context.object,'Studio floor','263B43')
    def light(name,pos,energy,color,size):
        data=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,data);studio.objects.link(obj)
        obj.location=pos;obj.rotation_euler=(Vector((0,5,0))-obj.location).to_track_quat('-Z','Y').to_euler()
        data.energy=energy;data.color=color;data.shape='DISK';data.size=size
    light('Large warm key',(-10,-8,19),10000,(1,.93,.83),12)
    light('Soft cool fill',(16,-2,14),8500,(.80,.91,1),11)
    light('Wide upper rim',(0,17,18),13000,(.91,.98,1),12)
    world=bpy.data.worlds.new('Neutral studio world');scene.world=world;world.use_nodes=True
    node=world.node_tree.nodes.get('Background');node.inputs['Color'].default_value=(.32,.39,.42,1);node.inputs['Strength'].default_value=.45
    data=bpy.data.cameras.new('Collection camera');cam=bpy.data.objects.new('Collection camera',data);studio.objects.link(cam)
    cam.data.type='ORTHO';scene.camera=cam
    scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    try:
        pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
        if any(d.type=='OPTIX' for d in pref.devices):
            for device in pref.devices:device.use=device.type=='OPTIX'
            scene.cycles.device='GPU'
    except (KeyError,TypeError,RuntimeError):pass
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.unit_settings.system='METRIC'
    return scene


def camera(pos,target,scale):
    cam=bpy.context.scene.camera
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale


def visibility(group=None):
    for item in ROSTER:
        for prefix in ('Pokemon_','Display_'):
            bpy.data.collections[prefix+item['name']].hide_render=group is not None and item['group']!=group


def overview():
    visibility();camera((1,-31,31),(0,7.5,.6),35.8)
    scene=bpy.context.scene;scene.render.resolution_x=3000;scene.render.resolution_y=1600


def render(which):
    scene=bpy.context.scene
    groups=['gen'+str(i) for i in range(1,11)]+['special']
    tasks=groups+['overview','front','clay'] if which=='all' else which.split(',')
    for task in tasks:
        if task in groups:
            visibility(task)
            items=[x for x in ROSTER if x['group']==task]
            cx=sum(x['gallery_position'][0] for x in items)/len(items);cy=items[0]['gallery_position'][1]
            camera((cx+3.4,cy-12.0,5.6),(cx,cy,1.05),10.9 if len(items)==3 else 8.0)
            scene.render.resolution_x=1800;scene.render.resolution_y=960
            scene.view_layers[0].material_override=None
        elif task in ('overview','front','clay'):
            overview()
            if task=='front':camera((0,-40,33),(0,7.5,.6),35.8)
            scene.view_layers[0].material_override=common.material('A9B4B3',.65) if task=='clay' else None
        else:raise ValueError('Unknown render '+task)
        scene.render.resolution_percentage=100
        scene.render.filepath=str(OUT/'renders'/(task+'.png'))
        bpy.ops.render.render(write_still=True)
        print('RENDER_READY '+task,flush=True)
    scene.view_layers[0].material_override=None
    overview()


parser=argparse.ArgumentParser()
parser.add_argument('--render',default='')
parser.add_argument('--rebuild',default='')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.context.preferences.filepaths.save_version=0
source=OUT/'Pokemon_Starters.blend'
if args.render and not args.rebuild:
    bpy.ops.wm.open_mainfile(filepath=str(source));render(args.render)
else:
    if args.rebuild:
        bpy.ops.wm.open_mainfile(filepath=str(source))
        names=args.rebuild.split(',')
        for item in ROSTER:
            if item['name'] in names:build_model(item)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        for item in ROSTER:build_model(item)
        stage()
    overview()
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_location=(0,7.5,0)
                area.spaces.active.region_3d.view_distance=36
                area.spaces.active.region_3d.view_rotation=bpy.context.scene.camera.rotation_euler.to_quaternion()
                area.spaces.active.shading.type='MATERIAL'
                area.spaces.active.overlay.show_extras=False
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(source),compress=True)
    (OUT/'roster.json').write_text(json.dumps(ROSTER,ensure_ascii=False,indent=2),encoding='utf-8')
    if args.render:render(args.render)
print('POKEMON_STARTERS_READY',flush=True)
