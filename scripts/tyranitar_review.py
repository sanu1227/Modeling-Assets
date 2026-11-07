"""Low-cost saved-source review of Tyranitar's back, side and open mouth."""
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import popular_tyranitar as p
bpy.ops.wm.open_mainfile(filepath=str(p.OUT/'Tyranitar.blend'))
s=bpy.context.scene;s.cycles.device='CPU';s.cycles.samples=12;s.render.threads_mode='FIXED';s.render.threads=2
s.render.resolution_x=800;s.render.resolution_y=800;s.render.resolution_percentage=100
for name,pos,target,zoom in [('back',(3,5,2.75),(0,.35,1.0),2.8),('side',(5,0,1.2),(0,.4,1),2.8),('face',(2.6,-4.5,2.45),(0,-.08,1.73),.95)]:
    p.view(s.camera,pos,target,zoom);s.render.filepath=str(p.OUT/'renders'/('Tyranitar_'+name+'_check.png'));bpy.ops.render.render(write_still=True)
print('TYRANITAR_REVIEW_OK',flush=True)
