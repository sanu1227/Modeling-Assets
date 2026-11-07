"""Finish face geometry and shading while preserving the v004 body and hair."""
from array import array
from pathlib import Path
import hashlib
import json
import math
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/Character/Refined_v004/Adventurer_Refined_v004.blend'
OUT = ROOT / 'assets/Character/Face_v005'
OUT.mkdir(exist_ok=True)
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
sys.path.insert(0, str(ROOT / 'scripts'))
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
collection = bpy.data.collections['01_Character_Refined']
head = bpy.data.objects['Head_Sculpted_ReferenceUV']
eyes = bpy.data.objects['Eyes_ReferenceUV']
body = bpy.data.objects['Body_Clothing_Tripo_Refined']


def signature(obj):
    coordinates = array('f', [0.0]) * (len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get('co', coordinates)
    return hashlib.sha256(coordinates.tobytes()).hexdigest()


preserved = {obj.name: signature(obj) for obj in collection.all_objects
             if obj.type == 'MESH' and obj not in (head, eyes)}
try:
    preferences = bpy.context.preferences.addons['cycles'].preferences
    preferences.compute_device_type = 'OPTIX'
    preferences.get_devices()
    for device in preferences.devices:
        device.use = device.type == 'OPTIX'
    scene.cycles.device = 'GPU' if any(device.use for device in preferences.devices) else 'CPU'
except Exception as error:
    print('GPU unavailable, using CPU:', error)
    scene.cycles.device = 'CPU'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.cycles.transparent_max_bounces = 20
scene.view_settings.view_transform = 'AgX'


def camera_view(position, target=(-.012, .02, 1.605), scale=.325, size=1100):
    scene.camera.location = position
    scene.camera.rotation_euler = (Vector(target) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera.data.ortho_scale = scale
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.resolution_percentage = 100


if '--before-only' in sys.argv:
    camera_view((1.65, -4, 1.61))
    scene.render.filepath = str(OUT / 'Before_v004_SameLighting.png')
    bpy.ops.render.render(write_still=True)
    raise SystemExit(0)

from face_geometry_v005 import refine_geometry
from face_features_v005 import refine_features
from face_material_v005 import refine_materials

geometry_report = refine_geometry(head, eyes)
features_report = refine_features(head, eyes, collection)
material_report = refine_materials(head, eyes, body)
bpy.context.view_layer.update()
assert all(signature(bpy.data.objects[name]) == digest for name, digest in preserved.items())
scene['stage'] = 'Face v005: under-eye surface, lip closure, warm skin; body and hair geometry preserved'
scene['face_source'] = str(SOURCE)
camera_view((-.012, -4, 1.605))
bpy.ops.object.select_all(action='DESELECT')
head.select_set(True)
bpy.context.view_layer.objects.active = head
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            space.region_3d.view_rotation = scene.camera.rotation_euler.to_quaternion()
            space.region_3d.view_location = (-.012, .02, 1.605)
            space.region_3d.view_distance = .53
            space.shading.type = 'MATERIAL'
            space.overlay.show_extras = False
            space.overlay.show_relationship_lines = False
            space.overlay.show_floor = False
            space.overlay.show_axis_x = space.overlay.show_axis_y = False
blend_file = OUT / 'Adventurer_Face_v005.blend'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))

views = [('Front', (-.012, -4, 1.605)), ('ThreeQuarter', (1.65, -4, 1.61)),
         ('Profile', (4, .02, 1.605))]
if '--quick' in sys.argv:
    views = views[:2]
    scene.cycles.samples = 24
    size = 900
else:
    size = 1100
for name, position in views:
    camera_view(position, size=size)
    scene.render.filepath = str(OUT / f'Face_{name}.png')
    bpy.ops.render.render(write_still=True)

# A neutral surface view checks real facial shape independently of the reference texture.
if '--quick' not in sys.argv:
    clay = bpy.data.materials.new('Verification_Clay_Only')
    clay.use_nodes = True
    shader = clay.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.48, .43, .38, 1)
    shader.inputs['Roughness'].default_value = .70
    for i in range(len(head.data.materials)):
        head.data.materials[i] = clay
    camera_view((1.65, -4, 1.61), size=1000)
    scene.render.filepath = str(OUT / 'Face_Clay_ThreeQuarter.png')
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.open_mainfile(filepath=str(blend_file))
head = bpy.data.objects['Head_Sculpted_ReferenceUV']
assert all(math.isfinite(value) for vertex in head.data.vertices for value in vertex.co)
assert all(signature(bpy.data.objects[name]) == digest for name, digest in preserved.items())
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
images = {
    node.image for obj in bpy.data.collections['01_Character_Refined'].all_objects
    if obj.type in {'MESH', 'CURVE'} for material in obj.data.materials if material and material.use_nodes
    for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image
}
assert all(image.packed_file or image.packed_files for image in images)
renders = [f'Face_{name}.png' for name, _ in views]
if '--quick' not in sys.argv:
    renders.append('Face_Clay_ThreeQuarter.png')
assert all((OUT / name).is_file() for name in renders)
report = {
    'passed': True, 'saved_file_reopened': True, 'source_v004_unchanged': True,
    'body_and_hair_geometry_unchanged': True, 'source_sha256': source_hash,
    'blend': str(blend_file), 'face_vertices': len(head.data.vertices),
    'geometry': geometry_report, 'features': features_report, 'materials': material_report,
    'packed_images': [{'name': image.name, 'size': list(image.size)} for image in sorted(images, key=lambda i: i.name)],
    'renders': renders, 'rigged': False, 'engine_tested': False,
}
(OUT / 'Validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('FACE_V005_OK', json.dumps(report, ensure_ascii=False))
