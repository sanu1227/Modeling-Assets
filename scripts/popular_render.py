"""Render an already saved popular model; record exact source hash for freshness."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime,timezone
import bpy

sys.path.insert(0,str(Path(__file__).resolve().parent))
import popular_tools as p

parser=argparse.ArgumentParser()
parser.add_argument('--name',required=True)
parser.add_argument('--views',default='hero,front,side,back,clay')
parser.add_argument('--draft',action='store_true')
parser.add_argument('--gpu',action='store_true')
parser.add_argument('--samples',type=int)
parser.add_argument('--size',type=int,default=1400)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
out=p.ROOT/'assets'/'PokemonPopular'/args.name
source=out/(args.name+'.blend')
digest=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
stats=p.mesh_stats(bpy.data.collections['Pokemon_'+args.name].all_objects)
p.render_views(args.name,out,stats,args.views.split(','),args.draft,args.size)
stamp={'source_sha256':digest,'source':source.name,'rendered_at':datetime.now(timezone.utc).isoformat(),
       'views':args.views.split(','),'draft':args.draft,
       'pixels':[bpy.context.scene.render.resolution_x,bpy.context.scene.render.resolution_y],
       'samples':bpy.context.scene.cycles.samples}
(out/('draft_render_manifest.json' if args.draft else 'render_manifest.json')).write_text(json.dumps(stamp,indent=2),encoding='utf8')
print('RENDER_SOURCE_MATCH',args.name,digest,flush=True)
