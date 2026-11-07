"""Create a neutral Blender character workspace. Existing work is never replaced."""
from pathlib import Path
import json
import math

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "Character"
TARGET = OUT / "Character_Start.blend"
if TARGET.exists():
    raise FileExistsError(f"Keep existing work: {TARGET}")
OUT.mkdir(parents=True, exist_ok=True)
for name in ("References", "Source", "Textures"):
    (OUT / name).mkdir(exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
scene.unit_settings.length_unit = "METERS"
scene.render.fps = 30
scene.frame_end = 120
scene["stage"] = "Preparation only; character design pending"
scene["orientation"] = "Z up; character faces -Y; feet at Z=0"
scene["guide_height_m"] = 2.0
collections = {}
for name in ("01_Reference", "02_Source_High", "03_Character_Work", "04_Rig", "05_Studio"):
    collection = bpy.data.collections.new(name)
    scene.collection.children.link(collection)
    collections[name] = collection

# A scale reference, not a character or a prescribed character height.
curve = bpy.data.curves.new("Scale_2m", "CURVE")
curve.dimensions = "3D"
segments = [((-1, 0, 0), (-1, 0, 2))]
for step in range(21):
    height = step / 10
    width = 0.15 if step % 5 == 0 else 0.07
    segments.append(((-1, 0, height), (-1 + width, 0, height)))
for ends in segments:
    spline = curve.splines.new("POLY")
    spline.points.add(1)
    for point, coordinate in zip(spline.points, ends):
        point.co = (*coordinate, 1)
guide = bpy.data.objects.new("GUIDE_2m_NOT_CHARACTER", curve)
collections["01_Reference"].objects.link(guide)
guide.hide_select = True
guide.hide_render = True
guide.show_in_front = True
for height in (0, 0.5, 1, 1.5, 2):
    font = bpy.data.curves.new(f"Label_{height:g}m", "FONT")
    font.body = f"{height:g} m"
    font.size = 0.08
    label = bpy.data.objects.new(font.name, font)
    collections["01_Reference"].objects.link(label)
    label.location = (-1.4, 0, height)
    label.rotation_euler.x = math.pi / 2
    label.hide_select = label.hide_render = True

for name, location in (("Front", (0, -6, 1)), ("Right", (6, 0, 1)), ("Preview", (3, -5, 2.5))):
    data = bpy.data.cameras.new(f"Camera_{name}")
    data.type = "ORTHO"
    data.ortho_scale = 3.0
    camera = bpy.data.objects.new(data.name, data)
    collections["05_Studio"].objects.link(camera)
    camera.location = location
    camera.rotation_euler = (Vector((0, 0, 1)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.hide_set(True)
    if name == "Preview":
        scene.camera = camera

for name, location, energy in (("Key", (3, -4, 4), 500), ("Fill", (-3, -2, 2.5), 200), ("Rim", (0, 3, 3.5), 400)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = 3
    light = bpy.data.objects.new(name, data)
    collections["05_Studio"].objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, 0, 1)) - light.location).to_track_quat("-Z", "Y").to_euler()
    light.hide_set(True)

scene.world = bpy.data.worlds.new("Character_World")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.12, 0.12, 0.12, 1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.4
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = "//Character_Preview.png"
scene.view_settings.view_transform = "AgX"
scene.tool_settings.transform_pivot_point = "MEDIAN_POINT"
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children["03_Character_Work"]
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.region_3d.view_location = (0, 0, 1)
            space.region_3d.view_distance = 3.8
            space.region_3d.view_rotation = (math.sqrt(0.5), math.sqrt(0.5), 0, 0)
            space.region_3d.view_perspective = "ORTHO"
            space.overlay.show_stats = True
            space.clip_end = 100

guide_path = OUT / "Character_Prep.txt"
if guide_path.exists():
    bpy.data.texts.load(str(guide_path))
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))

# Verify the saved file, then exercise the bundled rig tool in memory only.
bpy.ops.wm.open_mainfile(filepath=str(TARGET))
assert bpy.context.scene.unit_settings.scale_length == 1.0
assert all(name in bpy.data.collections for name in collections)
assert not any(obj.type in {"MESH", "ARMATURE"} for obj in bpy.data.objects)
assert bpy.context.scene.camera.name == "Camera_Preview"
bpy.ops.preferences.addon_enable(module="rigify")
bpy.ops.object.armature_basic_human_metarig_add()
meta_count = len(bpy.context.object.data.bones)
bpy.ops.pose.rigify_generate()
rig_count = len(bpy.context.object.data.bones)
assert meta_count == 29 and rig_count > meta_count
report = {
    "passed": True,
    "blender_version": bpy.app.version_string,
    "template_reopened": True,
    "unit_scale_m": 1.0,
    "character_created": False,
    "rigify_generation_passed": True,
    "test_metarig_bones": meta_count,
    "test_generated_bones": rig_count,
    "test_rig_saved_in_template": False,
    "visual_character_review": "not applicable: no character yet",
}
(OUT / "Preparation_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("CHARACTER_PREPARATION_OK", json.dumps(report))
