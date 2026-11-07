"""Update presentation-only settings without rebuilding the verified architecture."""
from pathlib import Path
import bpy
from mathutils import Vector

OUT=Path(__file__).resolve().parents[1]/'assets/ModernTower'
for mode in ('Day','Night'):
    path=OUT/f'Aurel_{mode}.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene=bpy.context.scene
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX'; prefs.get_devices()
    for d in prefs.devices: d.use=d.type!='CPU'
    scene.cycles.device='GPU'
    scene.camera.data.clip_end=50000
    for obj in bpy.data.objects:
        if obj.name.startswith('Context_'):
            obj.visible_shadow=False
        if obj.type=='LIGHT' and obj.data.type=='AREA':
            obj.data.shape='RECTANGLE'
            obj.data.size_y=obj.data.size*.18
            obj.visible_glossy=False
            obj.visible_transmission=False
    scene.render.filepath=str(OUT/f'hero_{mode.lower()}.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    bpy.ops.render.render(write_still=True)
    if mode=='Day':
        c=scene.camera; c.location=(27,-43,10)
        c.rotation_euler=(Vector((0,-7.5,4.0))-c.location).to_track_quat('-Z','Y').to_euler()
        c.data.lens=48; c.data.shift_y=0
        scene.render.resolution_x=1700; scene.render.resolution_y=1100
        scene.render.filepath=str(OUT/'entrance_detail.png')
        bpy.ops.render.render(write_still=True)
print('AUREL_PRESENTATION_OK',flush=True)
