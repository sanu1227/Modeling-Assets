"""Render draft or final views of the saved ship, without rebuilding geometry."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector

OUT=Path(__file__).resolve().parents[1]/'assets'/'PirateShip'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'BlackOath.blend'))
scene=bpy.context.scene
draft='--draft' in sys.argv
scene.cycles.samples=20 if draft else 48
scene.cycles.adaptive_threshold=.06 if draft else .035
scene.render.resolution_percentage=60 if draft else 100
views=[('hero',(-70,-105,40),(-4,0,19.5),52,1800,1300),
       ('stern_detail',(45,-43,25),(19,0,12.2),57,1600,1200),
       ('deck_detail',(-13,-26,30),(-2,0,8.5),48,1600,1200),
       ('profile',(0,-130,28),(-4,0,20),50,1900,1200),
       ('figurehead_detail',(-37.5,-7.6,11.5),(-29.0,0,9.35),55,1400,1200),
       ('figurehead_front',(-39,-1.65,9.6),(-29.0,0,9.35),58,1400,1400)]
selected=views[:1] if draft else (views[-2:] if '--skull-only' in sys.argv else
                                (views[:4] if '--ship-only' in sys.argv else views))
for name,loc,target,lens,w,h in selected:
    scene.camera.location=loc
    scene.camera.rotation_euler=(Vector(target)-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.camera.data.lens=lens
    scene.render.resolution_x=w
    scene.render.resolution_y=h
    scene.render.filepath=str(OUT/(name+('_draft' if draft else '')+'.png'))
    print('BLACK_OATH_RENDER: '+name,flush=True)
    bpy.ops.render.render(write_still=True)
print('BLACK_OATH_RENDER_OK',flush=True)
