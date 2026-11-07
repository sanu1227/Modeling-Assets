"""Inspect current-source rear joins at low CPU cost before final GPU renders."""
import sys
import importlib
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
for name,pos,target,zoom in [('Lucario',(1.65,4,1.45),(0,.04,.60),1.43),('Gardevoir',(1.8,4,1.65),(0,.04,.80),1.9)]:
    p=importlib.import_module('popular_'+name.lower())
    bpy.ops.wm.open_mainfile(filepath=str(p.OUT/(name+'.blend')))
    s=bpy.context.scene;s.cycles.device='CPU';s.cycles.samples=12;s.render.threads_mode='FIXED';s.render.threads=2
    s.render.resolution_x=800;s.render.resolution_y=900;s.render.resolution_percentage=100
    p.view(s.camera,pos,target,zoom);s.render.filepath=str(p.OUT/'renders'/(name+'_back_check.png'));bpy.ops.render.render(write_still=True)
print('REAR_JOINS_REVIEW_OK',flush=True)
