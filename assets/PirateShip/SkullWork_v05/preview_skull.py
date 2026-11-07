import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix

out=Path(__file__).resolve().parent
root=out.parents[2]
source=root/'assets/PirateShip/Source/Skull_v05/martinjario_skull.stl'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
import sys
sys.path.insert(0,str(root/'scripts'))
from black_oath_skull_v5 import build_skull,validate_skull
collection=bpy.data.collections.new('SkullV5_Core');bpy.context.scene.collection.children.link(collection)
objects=build_skull(collection)
center=Vector((-29.2,0,9.37))
report=validate_skull(objects)
(out/'skull_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.20,.23,.26,1);scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.35
scene.view_settings.view_transform='AgX'
def aim(o,point):o.rotation_euler=(Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,size,color in [('Key',(-33,-4,13),1500,4,(1,.9,.78)),('Fill',(-32,4,10),700,4,(.7,.83,1)),('Rim',(-27,2,12),1300,3,(1,.91,.8))]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=loc;aim(o,center)
camera_data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',camera_data);bpy.context.collection.objects.link(camera);scene.camera=camera
camera_data.type='ORTHO';camera_data.ortho_scale=3.25
for label,loc in [('front',(-36,0,9.45)),('three_quarter',(-35,-5,10.3)),('profile',(-29.2,-7,9.45))]:
    camera.location=loc;aim(camera,center);scene.render.filepath=str(out/f'skull_{label}.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'skull_preview.blend'))
assert report['passed'],report
