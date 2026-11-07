"""Import an original Tripo GLB and render honest, editable Blender previews.

Usage: blender --background --python scripts/import_tripo_character.py -- model.glb
       Add --rotate-z 180 if the imported character faces the other direction.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import sys

import bpy
from mathutils import Vector


parser = argparse.ArgumentParser()
parser.add_argument("glb", type=Path)
parser.add_argument("--rotate-z", type=float, default=0.0)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
source = args.glb.resolve()
assert source.is_file() and source.suffix.lower() == ".glb", "Expected an existing GLB"
out = Path(__file__).resolve().parents[1] / "assets" / "Character" / "Tripo_v002"
original = out / "Source" / "Adventurer_Tripo_source.glb"
original.parent.mkdir(parents=True, exist_ok=True)
if source != original:
    if original.exists():
        assert original.read_bytes() == source.read_bytes(), "A different source GLB is already preserved"
    else:
        shutil.copy2(source, original)
with original.open("rb") as source_file:
    source_hash = hashlib.file_digest(source_file, "sha256").hexdigest()

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
bpy.ops.import_scene.gltf(filepath=str(original))
imported = list(scene.objects)
meshes = [obj for obj in imported if obj.type == "MESH"]
assert meshes and sum(len(obj.data.polygons) for obj in meshes) > 0, "GLB has no visible mesh"

character = bpy.data.collections.new("01_Tripo_Character")
scene.collection.children.link(character)
root = bpy.data.objects.new("Character_Normalization", None)
character.objects.link(root)
root.empty_display_size = 0.1
for obj in imported:
    for old_collection in list(obj.users_collection):
        old_collection.objects.unlink(obj)
    character.objects.link(obj)
    if obj.parent is None:
        matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = matrix
    if obj.type in {"LIGHT", "CAMERA"}:
        obj.hide_render = True
        obj.hide_set(True)
root.rotation_euler.z = math.radians(args.rotate_z)
bpy.context.view_layer.update()


def bounds():
    low, high = Vector((math.inf,) * 3), Vector((-math.inf,) * 3)
    for obj in meshes:
        matrix = obj.matrix_world
        for vertex in obj.data.vertices:
            point = matrix @ vertex.co
            assert all(math.isfinite(value) for value in point), "Non-finite imported vertex"
            for axis in range(3):
                low[axis] = min(low[axis], point[axis])
                high[axis] = max(high[axis], point[axis])
    return low, high


low, high = bounds()
height = high.z - low.z
assert height > 0.00001, "Imported geometry has no height"
scale = 1.75 / height
center = (low + high) / 2
root.scale = (scale,) * 3
root.location = (-center.x * scale, -center.y * scale, -low.z * scale)
bpy.context.view_layer.update()
low, high = bounds()
assert abs(high.z - low.z - 1.75) < 0.0001 and abs(low.z) < 0.0001

studio = bpy.data.collections.new("02_Studio")
scene.collection.children.link(studio)


def to_studio(obj):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    studio.objects.link(obj)
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.001))
floor = to_studio(bpy.context.object)
floor.name = "Studio_Ground"
floor_mat = bpy.data.materials.new("Neutral studio floor")
floor_mat.diffuse_color = (0.27, 0.28, 0.30, 1)
floor_mat.use_nodes = True
floor_shader = floor_mat.node_tree.nodes.get("Principled BSDF")
floor_shader.inputs["Base Color"].default_value = floor_mat.diffuse_color
floor_shader.inputs["Roughness"].default_value = 0.85
floor.data.materials.append(floor_mat)
for name, position, power, size in (
    ("Key", (-3, -4, 4), 400, 4),
    ("Fill", (3, -2, 2.4), 150, 3),
    ("Rim", (1, 3, 3), 250, 3),
):
    data = bpy.data.lights.new(name, "AREA")
    light = bpy.data.objects.new(name, data)
    studio.objects.link(light)
    light.location, data.energy, data.shape, data.size = position, power, "DISK", size
    aim(light, (0, 0, 1))
scene.world = bpy.data.worlds.new("Neutral studio world")
scene.world.use_nodes = True
background = scene.world.node_tree.nodes["Background"]
background.inputs["Color"].default_value = (0.18, 0.18, 0.18, 1)
background.inputs["Strength"].default_value = 0.45
camera_data = bpy.data.cameras.new("Character_Camera")
camera = bpy.data.objects.new("Character_Camera", camera_data)
studio.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.lens = 70


def camera_view(position, target, ortho_scale, width=1024, height=1536):
    camera.location = position
    aim(camera, target)
    camera_data.ortho_scale = ortho_scale
    scene.render.resolution_x, scene.render.resolution_y = width, height


scene.render.engine = "CYCLES"
scene.cycles.samples = 40
scene.cycles.use_denoising = True
try:
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = "OPTIX"
    preferences.get_devices()
    for device in preferences.devices:
        device.use = device.type == "OPTIX"
    if any(device.use for device in preferences.devices):
        scene.cycles.device = "GPU"
except Exception as error:
    print("Cycles CPU fallback:", error)
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "AgX"
camera_view((2.4, -5, 1.9), (0, 0, 0.875), 1.95)
scene.render.filepath = str(out / "Adventurer_Tripo_ThreeQuarter.png")
scene["source"] = "Tripo image-to-3D GLB; imported materials preserved"
scene["source_sha256"] = source_hash
scene["stage"] = "Reference likeness review; game optimization and animation not verified"
bpy.ops.object.select_all(action="DESELECT")
active_mesh = max(meshes, key=lambda obj: len(obj.data.vertices))
active_mesh.select_set(True)
bpy.context.view_layer.objects.active = active_mesh
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.region_3d.view_rotation = camera.rotation_euler.to_quaternion()
            space.region_3d.view_location = (0, 0, 0.875)
            space.region_3d.view_distance = 2.5
            space.shading.type = "MATERIAL"
            space.overlay.show_extras = False
            space.overlay.show_relationship_lines = False
bpy.ops.file.pack_all()
blend_file = out / "Adventurer_Tripo_v002.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))

views = (
    ("Front", (0, -5, 0.875), (0, 0, 0.875), 1.90, 1024, 1536),
    ("ThreeQuarter", (2.4, -5, 1.9), (0, 0, 0.875), 1.95, 1024, 1536),
    ("Face", (0, -4, 1.57), (0, 0, 1.57), 0.43, 900, 900),
    ("Side", (5, 0, 0.875), (0, 0, 0.875), 1.90, 1024, 1536),
)
for name, position, target, ortho_scale, width, height in views:
    camera_view(position, target, ortho_scale, width, height)
    scene.render.filepath = str(out / f"Adventurer_Tripo_{name}.png")
    bpy.ops.render.render(write_still=True)

materials = {slot.material for obj in meshes for slot in obj.material_slots if slot.material}
images = {
    node.image for material in materials if material.use_nodes
    for node in material.node_tree.nodes if node.type == "TEX_IMAGE" and node.image
}
armatures = [obj for obj in imported if obj.type == "ARMATURE"]
report = {
    "passed": True,
    "blender_version": bpy.app.version_string,
    "blend_file": str(blend_file),
    "source_glb": str(original),
    "source_sha256": source_hash,
    "source_materials_preserved": True,
    "rotation_z_degrees": args.rotate_z,
    "mesh_objects": len(meshes),
    "vertices": sum(len(obj.data.vertices) for obj in meshes),
    "triangles": sum(len(face.vertices) - 2 for obj in meshes for face in obj.data.polygons),
    "bounds_min_m": list(low),
    "bounds_max_m": list(high),
    "mesh_uv_layers": {obj.name: len(obj.data.uv_layers) for obj in meshes},
    "materials": sorted(material.name for material in materials),
    "textures": [{"name": image.name, "size": list(image.size),
                  "packed": bool(image.packed_file or image.packed_files)} for image in sorted(images, key=lambda item: item.name)],
    "armatures": len(armatures),
    "bones": sum(len(obj.data.bones) for obj in armatures),
    "rig_added": False,
    "retopology_performed": False,
    "game_engine_tested": False,
    "likeness_review": "Needs visual comparison against Adventurer_Front_v003.png; not a numerical similarity score",
    "renders": [f"Adventurer_Tripo_{view[0]}.png" for view in views],
}
assert all((out / name).is_file() for name in report["renders"])
(out / "Adventurer_Tripo_Validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("TRIPO_IMPORT_RENDER_OK", json.dumps(report))
