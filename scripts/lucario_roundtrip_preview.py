"""Visually inspect the actual character-only GLBs using the saved studio."""
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
for name in ('Lucario','Gardevoir','Tyranitar'):
    folder=ROOT/'assets'/'PokemonPopular'/name
    bpy.ops.wm.open_mainfile(filepath=str(folder/(name+'.blend')))
    for obj in list(bpy.data.collections['Pokemon_'+name].objects):
        bpy.data.objects.remove(obj,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(folder/(name+'.glb')))
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.resolution_x=800 if name=='Tyranitar' else 700
    scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.view_layers[0].material_override=None
    scene.render.filepath=str(folder/'renders'/(name+'_glb_check.png'))
    bpy.ops.render.render(write_still=True)
    print('GLB_VISUAL_CHECK_RENDERED '+name,flush=True)
