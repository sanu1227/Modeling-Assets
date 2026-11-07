import sys,json
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from black_oath_skull_v3 import build_skull,validate_skull
OUT=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
collection=bpy.data.collections.new('Skull')
bpy.context.scene.collection.children.link(collection)
objects=build_skull(collection)
bpy.context.view_layer.update()
report=validate_skull(objects)
(OUT/'skull_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=48
scene.cycles.use_denoising=True
try:
    p=bpy.context.preferences.addons['cycles'].preferences
    p.compute_device_type='OPTIX';p.get_devices()
    for d in p.devices:d.use=d.type!='CPU'
    scene.cycles.device='GPU'
except Exception: pass
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.21,.25,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure=.1
scene.render.resolution_x=1200
scene.render.resolution_y=1200
scene.render.image_settings.file_format='PNG'
center=Vector((-29.2,0,9.37))
for name,loc,power,size,color in [('Key',(-33,-4,13),1600,4,(1,.89,.72)),
                               ('Fill',(-32,4,9),900,4,(.65,.79,1)),
                               ('Rim',(-27,2,12),2000,3,(1,.65,.3))]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=loc
    o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=3.75
for label,loc in [('three_quarter',(-35,-5,10.8)),('front',(-36,0,9.5))]:
    cam.location=loc;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/('skull_'+label+'.png'))
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'skull_preview.blend'))
assert report['passed'],report

