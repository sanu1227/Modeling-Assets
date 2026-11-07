"""Attach the approved character direction's AI reference images to a new work file."""
from pathlib import Path
import argparse
import json
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "Character"
parser = argparse.ArgumentParser()
parser.add_argument("--version", choices=("v001", "v002", "v003"), default="v001")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
TARGET = OUT / f"Character_References_{args.version}.blend"
if TARGET.exists():
    raise FileExistsError(f"Keep existing work: {TARGET}")
bpy.ops.wm.open_mainfile(filepath=str(OUT / "Character_Start.blend"))
scene = bpy.context.scene
scene["stage"] = "Design and image references ready; no character mesh yet"
scene["design"] = (
    "Idealized stylized adult adventurer, elegant face, approximately 7 heads tall; short brown hair, teal shirt, brown leather vest"
    if args.version == "v002" else
    "Stylized adult adventurer; short brown hair, teal shirt, brown leather vest"
)
scene["target_height_m"] = 1.75
if args.version == "v003":
    scene["design"] = "Beautiful feminine adult woman adventurer, age 23, chin-length chestnut bob, approximately 7 heads tall; teal shirt and fitted brown leather vest"
scene["reference_note"] = "AI reference images, approximate alignment; FRONT proportions take priority"
reference_collection = bpy.data.collections["01_Reference"]

# Image registration uses approximate normalized hair and boot-sole bounds from v001.
# These images are artistic references, not calibrated orthographic measurements.
views = [
    ("Front", (0, 0.65, 0), (0, -1, 0), 14 / 1536, 1474 / 1536),
    ("Side", (-0.65, 0, 0), (1, 0, 0), 14 / 1536, 1464 / 1536),
    ("Back", (0, -0.65, 0), (0, 1, 0), 12 / 1536, 1474 / 1536),
]
names = []
for name, position, normal, top, bottom in views:
    path = OUT / "References" / f"Adventurer_{name}_{args.version}.png"
    image = bpy.data.images.load(str(path), check_existing=True)
    assert image.size[0] > 0 and image.size[1] > 0, (path, tuple(image.size))
    obj = bpy.data.objects.new(f"REF_{name}", None)
    reference_collection.objects.link(obj)
    obj.empty_display_type = "IMAGE"
    obj.data = image
    obj.empty_display_size = 1.75 / (bottom - top)
    obj.location = position
    obj.location.z = obj.empty_display_size * (bottom - 0.5)
    obj.rotation_euler = Vector(normal).to_track_quat("Z", "Y").to_euler()
    obj.empty_image_depth = "BACK"
    obj.empty_image_side = "FRONT"
    obj.empty_image_offset = (-0.5, -0.5)
    obj.show_empty_image_orthographic = True
    obj.show_empty_image_perspective = False
    obj.show_empty_image_only_axis_aligned = True
    obj.use_empty_image_alpha = True
    obj.color = (1, 1, 1, 0.65)
    obj.hide_select = True
    obj["source"] = path.name
    obj["registration"] = "Approximate; compare landmarks with front before modeling"
    image.filepath = f"//References/{path.name}"
    image.pack()
    names.append(obj.name)

for name in ("Character_Prep.txt", "Character_Design.txt"):
    existing = bpy.data.texts.get(name)
    if existing:
        bpy.data.texts.remove(existing)
    bpy.data.texts.load(str(OUT / name))
bpy.ops.wm.save_as_mainfile(filepath=str(TARGET))

bpy.ops.wm.open_mainfile(filepath=str(TARGET))
for name in names:
    obj = bpy.data.objects[name]
    assert obj.type == "EMPTY" and obj.data.packed_file is not None
    assert obj.show_empty_image_only_axis_aligned and obj.empty_image_side == "FRONT"
assert not any(obj.type in {"MESH", "ARMATURE"} for obj in bpy.data.objects)
report = {
    "passed": True,
    "version": args.version,
    "file_reopened": True,
    "reference_images_packed": len(names),
    "references": names,
    "target_height_m": bpy.context.scene["target_height_m"],
    "registration": "approximate; manual landmark review needed during blockout",
    "character_mesh_created": False,
    "generator": "built-in image_gen",
}
report_name = "Reference_validation.json" if args.version == "v001" else f"Reference_validation_{args.version}.json"
(OUT / report_name).write_text(json.dumps(report, indent=2), encoding="utf-8")
print("CHARACTER_REFERENCES_OK", json.dumps(report))
