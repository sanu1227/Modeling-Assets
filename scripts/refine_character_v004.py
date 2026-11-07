"""Further visual refinement of the saved v003 character; never overwrites it."""
from pathlib import Path
import hashlib
import json
import math
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/Character/Refined_v003/Adventurer_Refined_v003.blend'
OUT = ROOT / 'assets/Character/Refined_v004'
OUT.mkdir(exist_ok=True)
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
sys.path.insert(0, str(ROOT / 'scripts'))
from refine_face_v004 import refine_face
from refine_hair_v004 import refine_hair
from refine_clothes_v004 import refine_clothes

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
collection = bpy.data.collections['01_Character_Refined']
head = bpy.data.objects['Head_Sculpted_ReferenceUV']
eyes = bpy.data.objects['Eyes_ReferenceUV']
hair = bpy.data.objects['Hair_Bob01_Chestnut']
body = bpy.data.objects['Body_Clothing_Tripo_Refined']


def camera_view(position, target, scale, width, height):
    scene.camera.location = position
    scene.camera.rotation_euler = (Vector(target) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera.data.ortho_scale = scale
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100


def studio():
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.cycles.transparent_max_bounces = 20
    scene.view_settings.view_transform = 'AgX'
    # Change the visible backdrop while keeping illumination identical for comparisons.
    world = scene.world
    nodes, links = world.node_tree.nodes, world.node_tree.links
    output = next(node for node in nodes if node.type == 'OUTPUT_WORLD')
    original = output.inputs['Surface'].links[0].from_socket
    camera_background = nodes.new('ShaderNodeBackground')
    camera_background.inputs['Color'].default_value = (.52, .56, .62, 1)
    camera_background.inputs['Strength'].default_value = .8
    ray = nodes.new('ShaderNodeLightPath')
    mix = nodes.new('ShaderNodeMixShader')
    links.new(ray.outputs['Is Camera Ray'], mix.inputs[0])
    links.new(original, mix.inputs[1])
    links.new(camera_background.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs['Surface'])


studio()
if '--before' in sys.argv or '--before-only' in sys.argv:
    camera_view((2.2, -4, 1.58), (0, .02, 1.58), .40, 1000, 1000)
    scene.render.filepath = str(OUT / 'Before_v003_SameLighting.png')
    bpy.ops.render.render(write_still=True)
    if '--before-only' in sys.argv:
        print('V004_COMPARISON_BASELINE_OK; v003 unchanged')
        raise SystemExit(0)

refine_clothes(body, collection)
refine_face(head, eyes, body, collection)
refine_hair(hair, head, collection)
scene['stage'] = 'v004 visual refinement: layered bob, cleaner face and clothing; not rigged or game optimized'
scene['previous_version'] = str(SOURCE)
scene['previous_version_sha256'] = source_hash

camera_view((2.2, -4, 1.58), (0, .02, 1.58), .40, 1000, 1000)
bpy.ops.object.select_all(action='DESELECT')
head.select_set(True)
bpy.context.view_layer.objects.active = head
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            space.region_3d.view_rotation = scene.camera.rotation_euler.to_quaternion()
            space.region_3d.view_location = (-.006, .03, 1.44)
            space.region_3d.view_distance = .85
            space.shading.type = 'MATERIAL'
            space.overlay.show_extras = False
            space.overlay.show_relationship_lines = False
            space.overlay.show_floor = False
            space.overlay.show_axis_x = False
            space.overlay.show_axis_y = False
blend_file = OUT / 'Adventurer_Refined_v004.blend'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))

views = (
    ('Face', (0, -4, 1.56), (0, 0, 1.56), .43, 1000, 1000),
    ('Face_ThreeQuarter', (2.2, -4, 1.58), (0, .02, 1.58), .40, 1000, 1000),
    ('Face_Side', (4, 0, 1.58), (0, .02, 1.58), .40, 900, 900),
    ('Front', (0, -5, .88), (0, 0, .88), 1.94, 1000, 1500),
    ('Back', (0, 5, .88), (0, 0, .88), 1.94, 1000, 1500),
)
if '--quick' in sys.argv:
    views = views[:2]
    scene.cycles.samples = 16
for name, position, target, scale, width, height in views:
    camera_view(position, target, scale, width, height)
    scene.render.filepath = str(OUT / f'Adventurer_Refined_{name}.png')
    bpy.ops.render.render(write_still=True)

# Validate the saved asset independently of the build-time object references.
bpy.ops.wm.open_mainfile(filepath=str(blend_file))
objects = [obj for obj in bpy.data.collections['01_Character_Refined'].all_objects
           if obj.type in {'MESH', 'CURVE'} and not obj.hide_render]
meshes = [obj for obj in objects if obj.type == 'MESH']
points = [obj.matrix_world @ vertex.co for obj in meshes for vertex in obj.data.vertices]
assert all(math.isfinite(axis) for point in points for axis in point)
images = {
    node.image for obj in objects for material in obj.data.materials if material and material.use_nodes
    for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image
}
assert images and all(image.packed_file or image.packed_files for image in images)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
assert all((OUT / f'Adventurer_Refined_{view[0]}.png').is_file() for view in views)
report = {
    'passed': True, 'saved_file_reopened': True, 'source_v003_unchanged': True,
    'blend': str(blend_file), 'source_sha256': source_hash,
    'mesh_vertices': sum(len(obj.data.vertices) for obj in meshes),
    'base_triangles': sum(len(p.vertices)-2 for obj in meshes for p in obj.data.polygons),
    'mesh_objects': len(meshes), 'curve_objects': len(objects)-len(meshes),
    'height_m': max(p.z for p in points)-min(p.z for p in points),
    'packed_images': [{'name': image.name, 'size': list(image.size)} for image in sorted(images, key=lambda i: i.name)],
    'rigged': False, 'game_optimized': False, 'engine_tested': False,
    'renders': [f'Adventurer_Refined_{view[0]}.png' for view in views],
}
(OUT / 'Validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('REFINED_V004_OK', json.dumps(report))
