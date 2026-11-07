"""Build and inspect one character refinement stage at a time."""
from pathlib import Path
from array import array
import hashlib
import json
import math
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/Character/Beauty_v006'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / 'scripts'))
stage = sys.argv[sys.argv.index('--stage') + 1] if '--stage' in sys.argv else 'shape'
source = ROOT / 'assets/Character/Face_v005/Adventurer_Face_v005.blend'
if stage != 'shape':
    previous = {'eyes': 'shape', 'brows': 'eyes', 'lips': 'brows',
                'hair': 'lips', 'outfit': 'hair'}[stage]
    source = OUT / f'Adventurer_{previous}_v006.blend'
source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
collection = bpy.data.collections['01_Character_Refined']
head = bpy.data.objects['Head_Sculpted_ReferenceUV']
eyes = bpy.data.objects['Eyes_ReferenceUV']
body = bpy.data.objects['Body_Clothing_Tripo_Refined']


def signature(obj):
    points = array('f', [0]) * (len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get('co', points)
    return hashlib.sha256(points.tobytes()).hexdigest()


preserved = {obj.name: signature(obj) for obj in collection.all_objects
             if obj.type == 'MESH' and obj != head}
if stage == 'shape':
    from beauty_shape_v006 import improve_shape
    report = improve_shape(head)
elif stage == 'eyes':
    from beauty_eyes_v006 import improve_eyes
    report = improve_eyes(head, eyes, collection)
elif stage == 'brows':
    from beauty_brows_v006 import improve_brows
    report = improve_brows(head, collection)
elif stage == 'lips':
    from beauty_lips_v006 import improve_lips
    report = improve_lips(head)
elif stage == 'hair':
    from beauty_hair_v006 import improve_hair
    report = improve_hair(collection, head)
else:
    from beauty_outfit_v006 import improve_outfit
    report = improve_outfit(body, collection)

preferences = bpy.context.preferences.addons['cycles'].preferences
preferences.compute_device_type = 'OPTIX'
preferences.get_devices()
for device in preferences.devices:
    device.use = device.type == 'OPTIX'
scene.cycles.device = 'GPU' if any(d.use for d in preferences.devices) else 'CPU'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.cycles.transparent_max_bounces = 24
scene.view_settings.view_transform = 'AgX'


def view(location, target=(-.012, .02, 1.605), scale=.325, width=1000, height=1000):
    scene.camera.location = location
    scene.camera.rotation_euler = (Vector(target) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera.data.ortho_scale = scale
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100


view((1.65, -4, 1.61))
bpy.ops.object.select_all(action='DESELECT')
head.select_set(True)
bpy.context.view_layer.objects.active = head
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            space.region_3d.view_rotation = scene.camera.rotation_euler.to_quaternion()
            space.region_3d.view_location = (-.012, .02, 1.605)
            space.region_3d.view_distance = .45
            space.shading.type = 'MATERIAL'
blend = OUT / f'Adventurer_{stage}_v006.blend'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
views = [('Front', (-.012, -4, 1.605)), ('ThreeQuarter', (1.65, -4, 1.61)),
         ('Profile', (4, .02, 1.605))]
for name, location in views:
    view(location)
    scene.render.filepath = str(OUT / f'{stage}_{name}.png')
    bpy.ops.render.render(write_still=True)
if stage == 'shape':
    clay = bpy.data.materials.new('Shape_Inspection_Clay')
    clay.use_nodes = True
    shader = clay.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.48, .43, .38, 1)
    shader.inputs['Roughness'].default_value = .7
    for i in range(len(head.data.materials)):
        head.data.materials[i] = clay
    view((1.65, -4, 1.61))
    scene.render.filepath = str(OUT / 'shape_Clay.png')
    bpy.ops.render.render(write_still=True)
if stage == 'outfit':
    view((0, -5, .88), (0, 0, .88), 1.94, 1100, 1650)
    scene.render.filepath = str(OUT / 'outfit_FullBody.png')
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=str(blend))
collection = bpy.data.collections['01_Character_Refined']
assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
if stage == 'shape':
    assert all(signature(bpy.data.objects[name]) == digest for name, digest in preserved.items())
assert all(math.isfinite(c) for obj in collection.all_objects if obj.type == 'MESH'
           for vertex in obj.data.vertices for c in vertex.co)
report.update({'stage': stage, 'source_unchanged': True, 'saved_file_reopened': True,
               'blend': str(blend)})
(OUT / f'{stage}_Validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('BEAUTY_STAGE_OK', json.dumps(report, ensure_ascii=False))
