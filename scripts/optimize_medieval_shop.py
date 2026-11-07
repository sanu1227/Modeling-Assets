"""Build a single-material PC asset, three LODs and simple collision from the editable source."""
import hashlib
import json
import math
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/MedievalShop/MedievalShop.blend'
OUT = SOURCE.parent / 'Optimized'
OUT.mkdir(exist_ok=True)
(OUT/'Textures').mkdir(exist_ok=True)
(OUT/'.temp').mkdir(exist_ok=True)
tempfile.tempdir = str(OUT/'.temp')
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
bpy.context.preferences.filepaths.temporary_directory = tempfile.tempdir
scene.cycles.samples = 16
scene.cycles.use_denoising = True
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type != 'CPU'
scene.cycles.device = 'GPU'

sources = [o for o in scene.objects if o.type == 'MESH' and o.parent]
game = bpy.data.collections.new('GAME_LOD0')
scene.collection.children.link(game)
depsgraph = bpy.context.evaluated_depsgraph_get()
parts = []
part_names = {}
remove_bevel = ('Slate_shingle','Annex_tile','Diamond_lead','Stave_joint','Door_rivet',
                'Bottle_cork','Counter_front_plank','Crate_slat','Crate_end','Herb_stem')
print('STAGE: simplifying bevels',flush=True)
for source in sources:
    for mod in source.modifiers:
        if mod.type == 'BEVEL':
            if source.name.startswith(remove_bevel):
                mod.show_viewport = mod.show_render = False
            else:
                mod.segments = 1
depsgraph.update()
print('STAGE: evaluating geometry',flush=True)
for index,source in enumerate(sources):
    data = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph),
                                         preserve_all_data_layers=True, depsgraph=depsgraph)
    # Primitives use UVMap while custom meshes use UV_Surface. Unify before joining.
    active_uv = data.uv_layers.active
    for layer in list(data.uv_layers):
        if layer != active_uv:
            data.uv_layers.remove(layer)
    active_uv.name = 'UV_Source'
    part_id = data.attributes.new('part_id','INT','FACE')
    part_id.data.foreach_set('value',[index]*len(data.polygons))
    part_names[index] = source.name.split('.')[0]
    obj = bpy.data.objects.new(source.name+'_Game', data)
    game.objects.link(obj)
    obj.matrix_world = source.matrix_world
    parts.append(obj)
    if index%400==0:
        print('GEOMETRY: '+str(index)+'/'+str(len(sources)),flush=True)
for source in sources:
    source.hide_render=True
    source.hide_set(True)

# Combine at the shared ground pivot. All surface shaders explicitly keep their original UVs.
print('STAGE: joining geometry',flush=True)
bpy.ops.object.select_all(action='DESELECT')
for obj in parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
lod0 = parts[0]
lod0.name = 'MedievalShop_LOD0'
scene.cursor.location = (0,0,0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
lod0.data.uv_layers.active.name = 'UV_Source'
for mat in lod0.data.materials:
    if not mat: continue
    uv = mat.node_tree.nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'UV_Source'
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            mat.node_tree.links.new(uv.outputs['UV'], node.inputs['Vector'])
lod0.data.uv_layers.new(name='UV_Atlas')
lod0.data.uv_layers.active_index = 1
lod0.data.uv_layers[1].active_render = True
print('STAGE: packing unique atlas UVs',flush=True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.0015,
                         margin_method='ADD', area_weight=.5, correct_aspect=True)
bpy.ops.object.mode_set(mode='OBJECT')
scene.render.bake.use_selected_to_active = False
scene.render.bake.margin = 3
scene.render.bake.margin_type = 'EXTEND'
scene.render.bake.normal_space = 'TANGENT'
scene.render.bake.use_clear = True
materials = list(lod0.data.materials)
images = {}
original_links = {}
principled = {}
for mat in materials:
    tree = mat.node_tree
    shader = tree.nodes.get('Principled BSDF')
    principled[mat.name] = shader
    out = next(n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL')
    original_links[mat.name] = (out, out.inputs['Surface'].links[0].from_socket)


def bake(name, kind, noncolor=False, channel=None):
    image = bpy.data.images.new(name, width=2048, height=2048, alpha=False)
    if noncolor:
        image.colorspace_settings.name = 'Non-Color'
    for mat in materials:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        out, socket = original_links[mat.name]
        links.new(socket, out.inputs['Surface'])
        shader = principled[mat.name]
        if channel:
            emit = nodes.new('ShaderNodeEmission')
            if channel == 'base':
                inp = shader.inputs['Base Color']
                if inp.is_linked:
                    links.new(inp.links[0].from_socket, emit.inputs['Color'])
                else:
                    emit.inputs['Color'].default_value = inp.default_value
            elif channel == 'orm':
                emit.inputs['Color'].default_value = (1, shader.inputs['Roughness'].default_value,
                                                      shader.inputs['Metallic'].default_value, 1)
            elif channel == 'emission':
                color = shader.inputs['Emission Color'].default_value
                strength = shader.inputs['Emission Strength'].default_value
                emit.inputs['Color'].default_value = (*[c*strength for c in color[:3]], 1)
            links.new(emit.outputs[0], out.inputs['Surface'])
        target = nodes.new('ShaderNodeTexImage')
        target.image = image
        nodes.active = target
    print('BAKE_START: '+name, flush=True)
    bpy.ops.object.bake(type=kind)
    image.filepath_raw = str(OUT/'Textures'/(name+'.png'))
    image.file_format = 'PNG'
    image.save()
    image.pack()
    images[name] = image
    print('BAKE_DONE: '+name, flush=True)


# Self baking retains the wood/plaster bump while geometry bevels stay on the low model.
bake('Shop_Normal', 'NORMAL', True)
bake('Shop_BaseColor', 'EMIT', channel='base')
bake('Shop_ORM', 'EMIT', True, 'orm')
bake('Shop_Emission', 'EMIT', channel='emission')
for mat in materials:
    out, socket = original_links[mat.name]
    mat.node_tree.links.new(socket, out.inputs['Surface'])

atlasmat = bpy.data.materials.new('M_MedievalShop_Atlas')
atlasmat.use_nodes = True
nodes, links = atlasmat.node_tree.nodes, atlasmat.node_tree.links
shader = nodes.get('Principled BSDF')
shader.inputs['Emission Strength'].default_value = 1
uv = nodes.new('ShaderNodeUVMap'); uv.uv_map='UV_Atlas'
textures = {}
for name, image in images.items():
    tex = nodes.new('ShaderNodeTexImage'); tex.image=image
    links.new(uv.outputs['UV'],tex.inputs['Vector'])
    textures[name] = tex
links.new(textures['Shop_BaseColor'].outputs['Color'],shader.inputs['Base Color'])
links.new(textures['Shop_Emission'].outputs['Color'],shader.inputs['Emission Color'])
normal = nodes.new('ShaderNodeNormalMap'); normal.uv_map='UV_Atlas'
links.new(textures['Shop_Normal'].outputs['Color'],normal.inputs['Color'])
links.new(normal.outputs['Normal'],shader.inputs['Normal'])
split = nodes.new('ShaderNodeSeparateColor')
links.new(textures['Shop_ORM'].outputs['Color'],split.inputs[0])
links.new(split.outputs['Green'],shader.inputs['Roughness'])
links.new(split.outputs['Blue'],shader.inputs['Metallic'])
lod0.data.materials.clear()
lod0.data.materials.append(atlasmat)
for poly in lod0.data.polygons:
    poly.material_index=0
lod0.data.uv_layers.remove(lod0.data.uv_layers['UV_Source'])

# Triangulation before LOD generation makes export counts and tangent bases deterministic.
tri = lod0.modifiers.new('Explicit triangulation','TRIANGULATE')
bpy.ops.object.modifier_apply(modifier=tri.name)
bm=bmesh.new(); bm.from_mesh(lod0.data)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
bm.to_mesh(lod0.data); bm.free()
lods=[lod0]
drop_mid={'Sign_trade','Stave_joint','Diamond_lead','Door_rivet','Bottle_cork','Herb_stem','Lavender_flower'}
drop_far=drop_mid | {'Sign_name','Barrel_hoop','Apothecary_bottle','Clay_jar','Herb_leaf',
    'Door_ring','Window_center_mullion','Window_crossbar','Shutter_hinge',
    'Slate_shingle','Annex_tile','Foundation_front_block','Foundation_side_block',
    'Corner_stone','Chimney_brick','Chimney_end_brick','Door_plank_seam','Jetty_joist'}
# Far roofs become stable solid roof decks, not collapsed, torn individual tiles.
# Sample a small interior patch of a tile/brick island; keep the one shared atlas material.
patches={}
ids=lod0.data.attributes['part_id'].data
uvdata=lod0.data.uv_layers.active.data
for source_name in ('Slate_shingle','Chimney_end_brick'):
    faces=[p for p in lod0.data.polygons if part_names[ids[p.index].value]==source_name]
    face=max(faces,key=lambda p:p.area)
    coords=[uvdata[i].uv.copy() for i in face.loop_indices]
    center=sum(coords,Vector((0,0)))/len(coords)
    extent=Vector((max(c.x for c in coords)-min(c.x for c in coords),
                   max(c.y for c in coords)-min(c.y for c in coords)))*.05
    patches[source_name]=(center,extent)
for level in (1,2):
    collection = bpy.data.collections.new('GAME_LOD'+str(level))
    scene.collection.children.link(collection)
    obj=lod0.copy(); obj.data=lod0.data.copy()
    obj.name='MedievalShop_LOD'+str(level)
    collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bm=bmesh.new(); bm.from_mesh(obj.data)
    layer=bm.faces.layers.int.get('part_id')
    uv=bm.loops.layers.uv.active
    drop=drop_mid if level==1 else drop_far
    if level==2:
        for face in bm.faces:
            name=part_names[face[layer]]
            sample=('Slate_shingle' if name in ('Roof_deck','Annex_roof_deck') else
                    'Chimney_end_brick' if name=='Chimney_core' else None)
            if sample:
                center,extent=patches[sample]
                # Tiny, nonzero UV footprint preserves the normal-map tangent basis.
                for index,loop in enumerate(face.loops):
                    angle=math.tau*index/len(face.loops)
                    loop[uv].uv=center+Vector((math.cos(angle)*extent.x,math.sin(angle)*extent.y))
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if part_names[f[layer]] in drop],context='FACES')
    loose=[v for v in bm.verts if not v.link_faces]
    if loose: bmesh.ops.delete(bm,geom=loose,context='VERTS')
    bm.to_mesh(obj.data); bm.free()
    obj.hide_render=True
    obj.hide_set(True)
    lods.append(obj)

# Simple convex collisions for a closed exterior building. Never rendered as visual geometry.
collision=bpy.data.collections.new('COLLISION')
scene.collection.children.link(collision)
colliders=[]
def collision_box(loc,size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    obj=bpy.context.object
    obj.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(obj.users_collection): c.objects.unlink(obj)
    collision.objects.link(obj)
    colliders.append(obj)
    return obj
collision_box((0,0,3.15),(6.8,5.6,6.3))
collision_box((4.02,.4,1.55),(1.6,3.65,3.1))
collision_box((1.38,-3.6,.5),(3.0,.85,1.0))
collision_box((-1.85,-3.05,.08),(1.95,.6,.16))
collision_box((-1.85,-2.74,.24),(1.8,.6,.16))
collision_box((2,1.36,8.6),(1.06,1.14,2.3))
data=bpy.data.meshes.new('RoofCollision')
data.from_pydata([(-3.95,-3.3,6.3),(3.95,-3.3,6.3),(0,-3.3,9.45),
                  (-3.95,3.3,6.3),(3.95,3.3,6.3),(0,3.3,9.45)],[],
                 [(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)])
roof=bpy.data.objects.new('RoofCollision',data); collision.objects.link(roof)
bm=bmesh.new(); bm.from_mesh(data)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(data); bm.free()
colliders.append(roof)
for i,obj in enumerate(colliders):
    obj.name=f'UCX_MedievalShop_LOD0_{i:02d}'
    obj.hide_render=True
    obj.display_type='WIRE'
    obj['collision_only']=True
    obj.hide_set(True)

# Remove editable source objects from this separate game file, keeping the presentation rig.
for obj in sources:
    bpy.data.objects.remove(obj,do_unlink=True)
for c in list(bpy.data.collections):
    if c.name.startswith(('01_','02_','03_','04_','05_','06_')):
        for obj in list(c.objects): bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(c)


def stats(obj):
    obj.data.calc_loop_triangles()
    return {'triangles':len(obj.data.loop_triangles),'vertices':len(obj.data.vertices),
            'materials':len(obj.data.materials)}


records={}
for level,obj in enumerate(lods):
    obj['lod_level']=level
    obj['usage']='Show exactly one LOD at a time. Engine switching must be configured.'
    obj.hide_set(False)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active=obj
    path=OUT/f'MedievalShop_LOD{level}.glb'
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                             export_apply=True,export_cameras=False,export_lights=False)
    records['LOD'+str(level)]={**stats(obj),'file_bytes':path.stat().st_size}
    obj.hide_set(level!=0)
    obj.hide_render=level!=0

# FBX LOD0 includes UCX hulls for Unreal import; Unity requires explicit collider assignment.
bpy.ops.object.select_all(action='DESELECT')
lod0.select_set(True); bpy.context.view_layer.objects.active=lod0
for obj in colliders:
    obj.hide_set(False); obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'MedievalShop_LOD0_collision.fbx'),
    use_selection=True,object_types={'MESH'},bake_anim=False,add_leaf_bones=False,
    apply_unit_scale=True,axis_forward='-Z',axis_up='Y',path_mode='COPY',embed_textures=True)
bpy.ops.object.select_all(action='DESELECT')
for obj in colliders:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'MedievalShop_collision.glb'),export_format='GLB',
                         use_selection=True,export_materials='NONE',export_cameras=False,export_lights=False)
for obj in colliders:
    obj.hide_set(True); obj.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
lod0.select_set(True); bpy.context.view_layer.objects.active=lod0
scene['LOD_switching']='Only LOD0 enabled. LOD1/2 and COLLISION are hidden. Never enable all LODs together.'
scene['atlas']='2048 PBR: BaseColor, tangent +Y Normal, ORM (AO=1), Emission. Opaque material.'
scene.render.resolution_x=1200; scene.render.resolution_y=1200
scene.cycles.samples=32
scene.render.filepath=str(OUT/'preview_LOD0.png')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MedievalShop_Optimized.blend'))
for level,obj in enumerate(lods):
    for other in lods:
        other.hide_render = other!=obj
    obj.hide_set(False)
    scene.render.filepath=str(OUT/f'preview_LOD{level}.png')
    bpy.ops.render.render(write_still=True)
    obj.hide_set(level!=0)
for obj in lods: obj.hide_render=obj!=lod0

report={'source_sha256_before':source_hash,
        'source_sha256_after':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'original_triangles':167792,'original_materials':21,
        'original_glb_bytes':(SOURCE.parent/'MedievalShop.glb').stat().st_size,
        'lods':records,'collision_hulls':len(colliders),
        'collision_triangles':sum(stats(o)['triangles'] for o in colliders),
        'texture_resolution':2048,'texture_maps':list(images),
        'runtime_engine_tested':False}
assert report['source_sha256_before']==report['source_sha256_after']
(OUT/'optimization_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
print('SHOP_OPTIMIZATION_BUILD_OK',flush=True)
