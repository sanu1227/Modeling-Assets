"""Append native Pokemon sources into an editable, labeled collection gallery."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from datetime import datetime,timezone
import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import pokemon_common as c

OUT=ROOT/'assets'/'PokemonPopular'
DISPLAY_COLUMNS=6
ROSTER=[('Greninja','개굴닌자',658,1),('Lucario','루카리오',448,2),('Mimikyu','따라큐',778,3),
 ('Charizard','리자몽',6,4),('Umbreon','블래키',197,5),('Sylveon','님피아',700,6),
 ('Garchomp','한카리아스',445,7),('Rayquaza','레쿠쟈',384,8),('Gardevoir','가디안',282,9),
 ('Gengar','팬텀',94,10),('Tyranitar','마기라스',248,12),('Lugia','루기아',249,15),
 ('Pikachu','피카츄',25,19),('Eevee','이브이',133,20),('Luxray','렌트라',405,21),('Snom','누니머기',872,30),
 ('Dragonite','망나뇽',149,None),('Mewtwo','뮤츠',150,None),('Snorlax','잠만보',143,None),
 ('Mew','뮤',151,None),('Chandelure','샹델라',609,18)]

def bounds(objects):
    lo,hi=np.full(3,np.inf),np.full(3,-np.inf);triangles=0
    graph=bpy.context.evaluated_depsgraph_get()
    for ob in objects:
        if ob.type!='MESH':continue
        evaluated=ob.evaluated_get(graph);me=evaluated.to_mesh()
        co=np.empty(len(me.vertices)*3,np.float64);me.vertices.foreach_get('co',co)
        mat=np.array(evaluated.matrix_world);co=co.reshape(-1,3)@mat[:3,:3].T+mat[:3,3]
        lo=np.minimum(lo,co.min(axis=0));hi=np.maximum(hi,co.max(axis=0))
        me.calc_loop_triangles();triangles+=len(me.loop_triangles);evaluated.to_mesh_clear()
    return Vector(lo),Vector(hi),triangles

def collection(name):
    col=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(col);return col

def aim(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()

def text_object(name,text,position,size,font,color):
    data=bpy.data.curves.new(name,'FONT');data.body=text;data.font=font;data.size=size
    data.align_x='CENTER';data.align_y='CENTER';data.extrude=.0005
    ob=bpy.data.objects.new(name,data);c.COLLECTION.objects.link(ob);ob.location=position
    ob.rotation_euler=(math.pi/2,0,0);data.materials.append(c.material(color));return ob

def setup_camera(roster,row=None):
    scene=bpy.context.scene;cam=scene.camera
    rows=max(x['row'] for x in roster)+1;cy=(rows-1)*3
    for item in roster:
        for prefix in ('Pokemon_','Display_'):
            col=bpy.data.collections.get(prefix+item['name'])
            if col:col.hide_render=row is not None and item['row']!=row
    if row is None:
        cam.location=(1.4,-27,max(20,rows*5+5));aim(cam,(0,cy,1.25))
        scene.render.resolution_x=3200;scene.render.resolution_y=2200 if rows>2 else 1700
    else:
        yy=row*6.0;cam.location=(1.1,yy-24,6.1);aim(cam,(0,yy,1.55))
        scene.render.resolution_x=3200;scene.render.resolution_y=900
    bpy.context.view_layer.update()
    rotation=cam.rotation_euler.to_matrix();inverse=rotation.transposed()
    points=[]
    for item in roster:
        if row is not None and item['row']!=row:continue
        for prefix in ('Pokemon_','Display_'):
            col=bpy.data.collections.get(prefix+item['name'])
            if col:
                for ob in col.all_objects:
                    if ob.type in {'MESH','FONT'}:
                        points.extend(inverse@(ob.matrix_world@Vector(p)-cam.location) for p in ob.bound_box)
    lo=Vector((min(p.x for p in points),min(p.y for p in points),0))
    hi=Vector((max(p.x for p in points),max(p.y for p in points),0))
    cam.location+=rotation@((lo+hi)*.5)
    aspect=scene.render.resolution_x/scene.render.resolution_y
    cam.data.ortho_scale=max(hi.x-lo.x,(hi.y-lo.y)*aspect)*1.10

parser=argparse.ArgumentParser()
parser.add_argument('--render',action='store_true');parser.add_argument('--draft',action='store_true')
parser.add_argument('--gpu',action='store_true');parser.add_argument('--existing',action='store_true')
parser.add_argument('--samples',type=int,default=80)
parser.add_argument('--scale',type=int,default=50,help='Output percentage; 50 gives a 1600px gallery preview, 100 gives 3200px.')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])

if args.existing:
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Pokemon_Popular.blend'))
    roster=json.loads((OUT/'gallery_manifest.json').read_text(encoding='utf8'))['models']
else:
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
    c.MATERIALS.clear();scene=bpy.context.scene
    font=bpy.data.fonts.load('C:/Windows/Fonts/malgunbd.ttf')
    small=bpy.data.fonts.load('C:/Windows/Fonts/segoeui.ttf')
    roster=[]
    available=sum(((ROOT/'assets'/'Charizard'/'Charizard.blend') if item[0]=='Charizard' else OUT/item[0]/(item[0]+'.blend')).is_file() for item in ROSTER)
    for name,korean,dex,rank in ROSTER:
        source=(ROOT/'assets'/'Charizard'/'Charizard.blend') if name=='Charizard' else OUT/name/(name+'.blend')
        if not source.is_file():continue
        collection_name='Charizard' if name=='Charizard' else 'Pokemon_'+name
        with bpy.data.libraries.load(str(source),link=False) as (data_from,data_to):
            if collection_name not in data_from.collections:raise ValueError('Missing model collection '+name)
            data_to.collections=[collection_name]
        col=data_to.collections[0];scene.collection.children.link(col);col.name='Pokemon_'+name
        bpy.context.view_layer.update();lo,hi,triangles=bounds(col.all_objects)
        size=hi-lo;scale=min(3.25/size.z,3.32/size.x,3.35/size.y)
        center=Vector(((lo.x+hi.x)*.5,(lo.y+hi.y)*.5,lo.z))
        index=len(roster);row,slot=divmod(index,DISPLAY_COLUMNS);row_count=min(DISPLAY_COLUMNS,available-row*DISPLAY_COLUMNS)
        position=Vector(((slot-(row_count-1)*.5)*4.6,row*6,.31))
        root=bpy.data.objects.new('Move_'+name,None);col.objects.link(root);root.empty_display_type='PLAIN_AXES';root.empty_display_size=.20
        for ob in list(col.all_objects):
            if ob!=root and ob.parent is None:ob.parent=root
        root.location=position-center*scale;root.scale=(scale,)*3
        root['display_scale_note']='Each model individually normalized, not canonical relative height.'
        root['name_ko']=korean;root['source_blend']=str(source.relative_to(ROOT))
        c.COLLECTION=collection('Display_'+name)
        bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=1.88,depth=.29,location=(position.x,position.y,.145))
        pedestal=c.finish(bpy.context.object,'Pedestal_'+name,'CCD6DA')
        mod=pedestal.modifiers.new('Soft display edge','BEVEL');mod.width=.055;mod.segments=4;c.apply(pedestal,mod)
        for face in pedestal.data.polygons:face.use_smooth=True
        bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=1.88,depth=.026,location=(position.x,position.y,.027))
        ring=c.finish(bpy.context.object,'Pedestal accent_'+name,'7F9CA8')
        mod=ring.modifiers.new('Rounded accent','BEVEL');mod.width=.009;mod.segments=3;c.apply(ring,mod)
        text_object('Name_'+name,korean,(position.x,position.y-1.876,.175),.166,font,'223C49')
        text_object('Dex_'+name,f'#{dex:03d}  {name.upper()}',(position.x,position.y-1.878,.071),.057,small,'4E6873')
        roster.append({'name':name,'korean':korean,'dex':dex,'vote_2020_rank':rank,'row':row,'slot':slot,
                       'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                       'triangles':triangles,'display_scale':scale,'display_position':list(position)})
        print('APPENDED',name,triangles,flush=True)
    if not roster:raise ValueError('No available model sources')
    c.COLLECTION=collection('90_Presentation')
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.02));c.finish(bpy.context.object,'Studio_floor','263947')
    cy=(math.ceil(len(roster)/DISPLAY_COLUMNS)-1)*3
    def area(name,position,power,size,color):
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
        ob=bpy.data.objects.new(name,data);c.COLLECTION.objects.link(ob);ob.location=position;aim(ob,(0,cy,1))
    area('Gallery key',(-9,-8,18),4200,13,(1,.94,.87))
    area('Gallery fill',(12,-3,15),3000,15,(.84,.92,1))
    area('Gallery top',(0,cy+8,19),4500,15,(1,1,1))
    world=bpy.data.worlds.new('Gallery world');scene.world=world;world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.58,.67,.76,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.50
    data=bpy.data.cameras.new('Gallery camera');data.type='ORTHO'
    camera=bpy.data.objects.new('Gallery camera',data);c.COLLECTION.objects.link(camera);scene.camera=camera
    scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=-.40
    scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100
    scene.unit_settings.system='METRIC'
    setup_camera(roster)
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                a.spaces.active.region_3d.view_location=(0,cy,1)
                a.spaces.active.region_3d.view_distance=29
                a.spaces.active.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
                a.spaces.active.shading.type='MATERIAL'
                a.spaces.active.overlay.show_extras=False
    bpy.ops.object.select_all(action='DESELECT');bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Pokemon_Popular.blend'),compress=True)
    manifest={'built_at':datetime.now(timezone.utc).isoformat(),'models':roster,
              'count':len(roster),'total_triangles':sum(x['triangles'] for x in roster),
              'original_source_files_modified':False,
              'note':'Native sources appended; each display normalized independently; no rigs or animations.'}
    (OUT/'gallery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print('GALLERY_SAVED',len(roster),flush=True)

if args.render:
    scene=bpy.context.scene
    if args.gpu:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for d in prefs.devices:d.use=d.type=='OPTIX'
        scene.cycles.device='GPU'
    render_dir=OUT/'renders';render_dir.mkdir(exist_ok=True)
    tasks=[None] if args.draft else [None]+list(range(max(x['row'] for x in roster)+1))
    for row in tasks:
        setup_camera(roster,row);scene.cycles.samples=20 if args.draft else args.samples
        scene.render.resolution_percentage=40 if args.draft else args.scale
        scene.render.filepath=str(render_dir/(('overview_draft' if args.draft else 'overview')+'.png' if row is None else f'row_{row+1:02d}.png'))
        bpy.ops.render.render(write_still=True)
    setup_camera(roster)
