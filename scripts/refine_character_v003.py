"""Fit an editable head and alpha-card bob to the retained Tripo clothing/body."""
from pathlib import Path
import json
import math
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/Character/Refined_v003'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / 'scripts'))
from refine_tripo_body import build_body_materials
from refine_bob_hair import build_bob_hair
from refine_head_shape import sculpt_head
from refine_neck_join import repair_neck

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'assets/Character/Tripo_v002/Adventurer_Tripo_v002.blend'))
scene = bpy.context.scene
collection = bpy.data.collections['01_Tripo_Character']
collection.name = '01_Character_Refined'
body = next(o for o in collection.objects if o.type == 'MESH')
world = body.matrix_world.copy()
body.parent = None
body.matrix_world = Matrix.Identity(4)
body.data.transform(world)
body.data.update()
body.name = 'Body_Clothing_Tripo_Refined'
materials = build_body_materials(body, collection)


def cut(obj, height, above):
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bmesh.ops.bisect_plane(mesh, geom=list(mesh.verts) + list(mesh.edges) + list(mesh.faces),
                          plane_co=(0, 0, height), plane_no=(0, 0, 1),
                          clear_outer=above, clear_inner=not above, dist=.000001)
    loose = [v for v in mesh.verts if not v.link_faces]
    bmesh.ops.delete(mesh, geom=loose, context='VERTS')
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()


cut(body, 1.475, True)
# Replace the final few millimeters of inherited face paint at the neck join.
skin_slot = next(i for i, mat in enumerate(body.data.materials) if mat == materials['skin'])
for face in body.data.polygons:
    if face.center.z > 1.445 and abs(face.center.x - .009) < .061 and face.center.y < .095:
        face.material_index = skin_slot

with bpy.data.libraries.load(str(ROOT / 'assets/Character/Adventurer_Model_v001.blend'), link=False) as (source, target):
    target.objects = ['Body_Female_Edit', 'Eyes_Sclera']
head, eyes = target.objects
for obj in (head, eyes):
    collection.objects.link(obj)
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    obj.hide_set(False)
    obj.hide_render = False
    for modifier in list(obj.modifiers):
        if modifier.type == 'ARMATURE':
            obj.modifiers.remove(modifier)
    obj.vertex_groups.clear()


def smooth(value):
    value = min(1, max(0, value))
    return value * value * (3 - 2 * value)


def head_transform(co):
    x, y, z = co
    blend = smooth((z - 1.455) / .060)
    x_shift = .009 * (1 - blend) - .012 * blend
    neck_weight = 1 - smooth((z - 1.455) / .045)
    y = -.0225 + (y + .0225) * (1 + .09 * neck_weight)
    return Vector((x + x_shift, y + .0742, z + .010 + .065 * x * blend))


# Fit before cutting: the hair asset uses MakeHuman helper anchors.
hair = build_bob_hair(collection, head_transform)
sculpt_head(head)
cut(head, 1.455, False)
for obj in (head, eyes):
    for vertex in obj.data.vertices:
        vertex.co = head_transform(vertex.co)
    obj.data.update()
head.name = 'Head_Sculpted_ReferenceUV'
eyes.name = 'Eyes_ReferenceUV'

reference = bpy.data.images.load(str(ROOT / 'assets/Character/References/Adventurer_Front_v003.png'), check_existing=True)
reference.name = 'Approved_Front_v003_FaceProjection'
reference.pack()
pixel_scale = 1.75 / (1484 - 16)


def projection_material(obj, eye=False):
    uv = obj.data.uv_layers.new(name='Reference_FrontUV')
    for loop in obj.data.loops:
        x, y, z = obj.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (.5 + x / (1024 * pixel_scale), (z / pixel_scale + 52) / 1536)
    obj.data.uv_layers.active = uv
    mask = obj.data.color_attributes.new(name='ReferenceBlend', type='FLOAT_COLOR', domain='POINT')
    for vertex, datum in zip(obj.data.vertices, mask.data):
        x, y, z = vertex.co
        # Keep the reference in the front-facing central face. Ears/back/neck remain real skin.
        amount = 1.0 if eye else (smooth((-.018 - y) / .025)
                                * smooth((.077 - abs(x + .012)) / .015)
                                * smooth((z - 1.494) / .022))
        datum.color = (amount, amount, amount, 1)
    mat = bpy.data.materials.new('Eyes_Projected_Hazel' if eye else 'Face_Reference_Projection')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = .3 if eye else .62
    bsdf.inputs['Specular IOR Level'].default_value = .18
    bsdf.inputs['Subsurface Weight'].default_value = 0 if eye else .035
    bsdf.inputs['Subsurface Scale'].default_value = .012
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = reference
    tex.interpolation = 'Linear'
    uv_node = nodes.new('ShaderNodeUVMap')
    uv_node.uv_map = uv.name
    links.new(uv_node.outputs['UV'], tex.inputs['Vector'])
    attr = nodes.new('ShaderNodeVertexColor')
    attr.layer_name = mask.name
    mix = nodes.new('ShaderNodeMixRGB')
    mix.inputs[1].default_value = materials['skin'].diffuse_color
    links.new(attr.outputs['Color'], mix.inputs[0])
    links.new(tex.outputs['Color'], mix.inputs[2])
    links.new(mix.outputs[0], bsdf.inputs['Base Color'])
    mat.diffuse_color = materials['skin'].diffuse_color
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for polygon in obj.data.polygons:
        polygon.material_index = 0
        polygon.use_smooth = True


projection_material(head)
projection_material(eyes, True)
neck_report = repair_neck(body, head, materials['skin'])

for obj in (head, eyes):
    for modifier in obj.modifiers:
        if modifier.type == 'SUBSURF':
            modifier.levels = modifier.render_levels = 2
scene['stage'] = 'Blender refinement; separate sculpted head, reference-projected face, fitted CC0 hair cards; no rig or retopology'
head['texture_method'] = 'Front reference projected onto UVs; side/back blend to skin. Source image lighting remains in texture.'
head['geometry_changes'] = 'Replacement quad head; fitted eyes/lips/jaw; neck taper fitted to retained body'
hair['source_license'] = 'MakeHuman bob01 CC0; Source/Hair/bob01-source-manifest.json'
scene.cycles.samples = 32
scene.cycles.transparent_max_bounces = 16
scene.cycles.use_denoising = True
scene.view_settings.view_transform = 'AgX'


def camera_view(position, target, scale, width, height):
    scene.camera.location = position
    scene.camera.rotation_euler = (Vector(target) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera.data.ortho_scale = scale
    scene.render.resolution_x, scene.render.resolution_y = width, height


camera_view((0, -4, 1.56), (0, 0, 1.56), .43, 900, 900)
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
bpy.ops.file.pack_all()
blend_file = OUT / 'Adventurer_Refined_v003.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))

views = (
    ('Face', (0, -4, 1.56), (0, 0, 1.56), .43, 900, 900),
    ('Face_ThreeQuarter', (2.2, -4, 1.58), (0, .02, 1.58), .40, 900, 900),
    ('Face_Side', (4, 0, 1.58), (0, .02, 1.58), .40, 900, 900),
    ('Front', (0, -5, .88), (0, 0, .88), 1.94, 1000, 1500),
    ('Side', (5, 0, .88), (0, 0, .88), 1.94, 800, 1200),
)
if '--quick' in sys.argv:
    views = views[:2]
    scene.cycles.samples = 16
for name, position, target, scale, width, height in views:
    camera_view(position, target, scale, width, height)
    scene.render.filepath = str(OUT / f'Adventurer_Refined_{name}.png')
    bpy.ops.render.render(write_still=True)

objects = [body, head, eyes, hair]
points = [obj.matrix_world @ v.co for obj in objects for v in obj.data.vertices]
assert all(math.isfinite(axis) for point in points for axis in point)
report = {
    'blend': str(blend_file), 'passed': True,
    'vertices': sum(len(o.data.vertices) for o in objects),
    'base_triangles': sum(len(p.vertices) - 2 for o in objects for p in o.data.polygons),
    'bounds_min': [min(p[i] for p in points) for i in range(3)],
    'bounds_max': [max(p[i] for p in points) for i in range(3)],
    'meshes': {o.name: {'vertices': len(o.data.vertices), 'uv_layers': len(o.data.uv_layers)} for o in objects},
    'rig_added': False, 'retopology_performed': False, 'engine_tested': False,
    'face_texture': 'Approved reference front projection with side blend; painted lighting remains',
    'neck': 'Locally fitted neck join; head and body remain separately editable',
    'neck_repair': neck_report,
    'hair': 'CC0 MakeHuman bob01 fitted and sculpted; alpha texture',
    'renders': [f'Adventurer_Refined_{v[0]}.png' for v in views],
}
bpy.ops.wm.open_mainfile(filepath=str(blend_file))
reopened = bpy.data.collections['01_Character_Refined']
assert all(bpy.data.objects.get(name) in reopened.objects[:] for name in report['meshes'])
used_images = {
    node.image for obj in reopened.objects if obj.type == 'MESH'
    for material in obj.data.materials if material and material.use_nodes
    for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image
}
assert len(used_images) >= 5
assert all(image.packed_file or image.packed_files for image in used_images)
report['saved_file_reopened'] = True
report['packed_images'] = [{'name': image.name, 'size': list(image.size)} for image in sorted(used_images, key=lambda i: i.name)]
assert all((OUT / name).is_file() for name in report['renders'])
(OUT / 'Validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('REFINED_V003_OK', json.dumps(report))
