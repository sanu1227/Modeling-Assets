"""Render a native-scene before/after comparison without modifying either blend."""
import hashlib
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"assets"/"Weapons"/"Aurelia_v2"
old_path=ROOT/"assets"/"Weapons"/"Aurelia"/"Aurelia.blend"
new_path=OUT/"Aurelia_v2.blend"
hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (old_path,new_path)}
bpy.ops.wm.open_mainfile(filepath=str(new_path))
scene=bpy.context.scene
new=bpy.data.objects["SM_Aurelia_v2_Longsword"]
new.location.x=.222
with bpy.data.libraries.load(str(old_path),link=False) as (source,target):
    target.objects=["SM_Aurelia_Longsword"]
old=target.objects[0]
scene.collection.objects.link(old)
old.location.x=-.222
old.hide_set(False)
camera=scene.camera
camera.location=(0,-2.6,.12)
camera.rotation_euler=(Vector((0,0,.002))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.ortho_scale=.96
scene.render.resolution_x=2200
scene.render.resolution_y=1450
scene.cycles.samples=80
preferences=bpy.context.preferences.addons["cycles"].preferences
preferences.compute_device_type="OPTIX"
preferences.get_devices()
for device in preferences.devices:
    device.use=device.type=="OPTIX"
scene.cycles.device="GPU"
label_material=bpy.data.materials.new("Comparison captions")
label_material.use_nodes=True
bsdf=label_material.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value=(.5,.58,.68,1)
bsdf.inputs["Emission Color"].default_value=(.35,.4,.5,1)
bsdf.inputs["Emission Strength"].default_value=.6
for x,label in ((-.222,"AURELIA  /  ORIGINAL"),(.222,"AURELIA  /  V2")):
    data=bpy.data.curves.new(label,"FONT")
    data.body=label
    data.align_x="CENTER"
    data.size=.011
    obj=bpy.data.objects.new(label,data)
    scene.collection.objects.link(obj)
    obj.location=(x,-.06,-.263)
    obj.rotation_euler=(math.pi/2,0,0)
    data.materials.append(label_material)
scene.render.filepath=str(OUT/"Aurelia_v2_comparison.png")
bpy.ops.render.render(write_still=True)
assert all(hashlib.sha256(p.read_bytes()).hexdigest()==digest for p,digest in hashes.items())
assert (OUT/"Aurelia_v2_comparison.png").stat().st_size>10000
print("AURELIA_COMPARISON_OK; both source blends unchanged",flush=True)
