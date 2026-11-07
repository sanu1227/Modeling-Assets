"""Render a saved model without rebuilding it. GPU use is scheduled by root."""
import sys
import argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import eeveelutions_helpers as h

parser=argparse.ArgumentParser()
parser.add_argument('name',choices=('Umbreon','Sylveon','Dragonite','Luxray','Eevee'))
parser.add_argument('--gpu',action='store_true')
parser.add_argument('--draft',action='store_true')
parser.add_argument('--views',default='hero,front,side,back,clay')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
h.NAME=args.name;h.OUT=h.ROOT/'assets'/'PokemonPopular'/args.name
bpy.ops.wm.open_mainfile(filepath=str(h.OUT/(args.name+'.blend')))
h.COL=bpy.data.collections['Pokemon_'+args.name]
h.STUDIO=bpy.data.collections['90_Presentation']
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=2
if args.gpu:
    pref=bpy.context.preferences.addons['cycles'].preferences
    pref.compute_device_type='OPTIX';pref.get_devices()
    available=[device for device in pref.devices if device.type=='OPTIX']
    if not available:raise RuntimeError('No OPTIX device; GPU slot requires GPU')
    for device in pref.devices:device.use=device.type=='OPTIX'
    scene.cycles.device='GPU'
    print('GPU_RENDER '+args.name+' '+','.join(device.name for device in available),flush=True)
h.render(tuple(args.views.split(',')),args.draft)
if not h.validate()['passed']:raise RuntimeError(args.name+' validation failed')
