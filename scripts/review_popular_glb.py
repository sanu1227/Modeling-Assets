"""Render the exported GLB in the saved source studio without modifying either asset."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy

sys.path.insert(0,str(Path(__file__).resolve().parent))
import popular_tools as p

parser=argparse.ArgumentParser()
parser.add_argument('--names',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
for name in args.names.split(','):
    out=p.ROOT/'assets'/'PokemonPopular'/name
    source=out/(name+'.blend');glb=out/(name+'.glb')
    before={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in (source,glb)}
    bpy.ops.wm.open_mainfile(filepath=str(source))
    col=bpy.data.collections['Pokemon_'+name]
    stats=p.mesh_stats(col.all_objects)
    for ob in list(col.all_objects):bpy.data.objects.remove(ob,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    scene=bpy.context.scene
    p.camera_view(name,stats['bounds'],'hero')
    scene.render.resolution_x=scene.render.resolution_y=800
    scene.render.resolution_percentage=100
    scene.cycles.device='CPU';scene.cycles.samples=20
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.filepath=str(out/'renders'/'glb_reimport.png')
    bpy.ops.render.render(write_still=True)
    after={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in (source,glb)}
    if before!=after:raise RuntimeError('Source modified unexpectedly: '+name)
    (out/'glb_visual_review.json').write_text(json.dumps({'source_sha256':before[source.name],
        'glb_sha256':before[glb.name],'render':'renders/glb_reimport.png',
        'source_files_unchanged':True,'note':'Rendered GLB in Blender, not a game-engine runtime test.'},indent=2),encoding='utf8')
    print('GLB_REVIEW_RENDER',name,flush=True)
