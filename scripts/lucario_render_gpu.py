"""Render saved Lucario/Gardevoir models without rebuilding geometry.

Blender --background --python this.py -- Lucario
"""
import sys
import importlib
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Lucario']
name=args[0]
if name not in ('Lucario','Gardevoir','Tyranitar'):raise ValueError(name)
module=importlib.import_module('popular_'+name.lower())
path=ROOT/'assets'/'PokemonPopular'/name/(name+'.blend')
bpy.ops.wm.open_mainfile(filepath=str(path))
scene=bpy.context.scene
pref=bpy.context.preferences.addons['cycles'].preferences
pref.compute_device_type='OPTIX';pref.get_devices()
devices=[d for d in pref.devices if d.type=='OPTIX']
if not devices:raise RuntimeError('No OptiX GPU; CPU fallback intentionally disabled')
for d in pref.devices:d.use=d.type=='OPTIX'
scene.render.engine='CYCLES';scene.cycles.device='GPU';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1400;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
if name=='Tyranitar':scene.render.resolution_x=1600
scene.view_layers[0].material_override=None
print('GPU_RENDER_BEGIN '+name+' '+str([d.name for d in devices]),flush=True)
if name=='Lucario':module.render_views(scene.camera,False)
else:module.render(scene.camera,False)
print('GPU_RENDER_COMPLETE '+name,flush=True)
