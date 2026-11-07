"""Check current saved assets, render freshness, packed GLBs and gallery source hashes."""
import argparse
import ast
import hashlib
import json
import struct
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets'/'PokemonPopular'
parser=argparse.ArgumentParser()
parser.add_argument('--draft',action='store_true',help='Report incomplete delivery without raising.')
args=parser.parse_args()
syntax=ast.parse((ROOT/'scripts'/'build_popular_gallery.py').read_text(encoding='utf8'))
roster=next(ast.literal_eval(node.value) for node in syntax.body if isinstance(node,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=='ROSTER' for t in node.targets))
errors=[];warnings=[];models=[]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def png_size(path):
    raw=path.read_bytes()[:24]
    if raw[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Invalid PNG '+str(path))
    return list(struct.unpack('>II',raw[16:24]))

for name,korean,dex,rank in roster:
    folder=ROOT/'assets'/'Charizard' if name=='Charizard' else OUT/name
    source=folder/(name+'.blend');glb=folder/(name+'.glb')
    if not source.exists():continue
    item={'name':name,'korean':korean,'dex':dex,'vote_2020_rank':rank,'errors':[],
          'source':str(source.relative_to(ROOT)),'source_sha256':sha(source),'source_bytes':source.stat().st_size}
    if not glb.is_file():item['errors'].append('Missing GLB')
    else:
        raw=glb.read_bytes();magic,version,length=struct.unpack_from('<III',raw)
        if (magic,version,length)!=(0x46546c67,2,len(raw)):item['errors'].append('Invalid GLB header')
        n,kind=struct.unpack_from('<II',raw,12)
        if kind!=0x4e4f534a:item['errors'].append('Missing GLB JSON chunk')
        else:
            doc=json.loads(raw[20:20+n])
            if doc.get('cameras') or doc.get('extensions',{}).get('KHR_lights_punctual'):item['errors'].append('Presentation camera or light in GLB')
            if any('uri' in b for b in doc.get('buffers',[])):item['errors'].append('External GLB buffer')
            if any('uri' in im or 'bufferView' not in im for im in doc.get('images',[])):item['errors'].append('External or missing GLB image')
            item['embedded_images']=len(doc.get('images',[]));item['glb_meshes']=len(doc.get('meshes',[]))
        item['glb_sha256']=sha(glb);item['glb_bytes']=len(raw)
    validation=folder/('Charizard_validation.json' if name=='Charizard' else 'validation.json')
    if not validation.is_file():item['errors'].append('Missing geometry validation')
    else:
        item['geometry_passed']=load(validation).get('passed') is True
        if not item['geometry_passed']:item['errors'].append('Geometry validation did not pass')
        if validation.stat().st_mtime+1<max(source.stat().st_mtime,glb.stat().st_mtime if glb.exists() else 0):
            item['errors'].append('Geometry validation older than current source/export')
    renders=[]
    for view in (['hero','front','back','clay'] if name=='Charizard' else ['hero','front','side','back','clay']):
        base=folder if name=='Charizard' else folder/'renders'
        candidates=([base/'hero.png',base/'preview.png',base/(name+'_preview.png')] if view=='hero'
                    else [base/(view+'.png'),base/(name+'_'+view+'.png')])
        path=next((x for x in candidates if x.is_file()),None)
        if path is None:item['errors'].append('Missing final '+view+' render');continue
        fresh=path.stat().st_mtime+1>=source.stat().st_mtime
        if not fresh:item['errors'].append('Stale '+view+' render')
        renders.append({'view':view,'path':str(path.relative_to(ROOT)),'pixels':png_size(path),'fresh':fresh})
    item['renders']=renders
    render_manifest=folder/'render_manifest.json'
    if render_manifest.is_file() and load(render_manifest).get('source_sha256')!=item['source_sha256']:
        item['errors'].append('Render source hash differs from current blend')
    models.append(item)
    errors.extend(name+': '+error for error in item['errors'])

new_count=sum(item['name']!='Charizard' for item in models)
if new_count!=20:errors.append(f'Expected 20 new models, found {new_count}')
preservation={}
observed_changes=load(OUT/'observed_prior_asset_changes.json')
for relative,expected in load(OUT/'preserved_assets.json')['sha256'].items():
    path=ROOT/relative;actual=sha(path) if path.is_file() else None
    preservation[relative]={'unchanged':actual==expected.lower(),'expected':expected.lower(),'actual':actual}
    if not preservation[relative]['unchanged']:
        if actual==observed_changes['sha256'].get(relative):
            warnings.append('Documented prior build changed initial snapshot: '+relative)
            preservation[relative]['documented_exception']='observed_prior_asset_changes.json'
        else:errors.append('Unexplained prior asset change: '+relative)

gallery={}
manifest=OUT/'gallery_manifest.json'
if not manifest.is_file() or not (OUT/'Pokemon_Popular.blend').is_file():errors.append('Gallery not built')
else:
    gallery=load(manifest)
    for item in gallery['models']:
        if sha(ROOT/item['source'])!=item['source_sha256']:errors.append('Gallery has stale model: '+item['name'])
    if gallery['count']!=len(models):errors.append('Gallery model count differs from delivered model count')
    gallery_file=OUT/'Pokemon_Popular.blend'
    native_check=OUT/'gallery_validation.json'
    if not native_check.is_file():errors.append('Missing saved gallery validation')
    else:
        native_result=load(native_check)
        if not native_result.get('passed'):errors.append('Saved gallery verification failed')
        if native_result.get('source_sha256')!=sha(gallery_file):errors.append('Saved gallery validation is stale')
    rows=max(x['row'] for x in gallery['models'])+1
    for relative in ['overview.png']+[f'row_{i+1:02d}.png' for i in range(rows)]:
        path=OUT/'renders'/relative
        if not path.exists():errors.append('Missing gallery render: '+relative)
        elif path.stat().st_mtime+1<gallery_file.stat().st_mtime:errors.append('Stale gallery render: '+relative)

report={'passed':not errors,'checked_at':datetime.now(timezone.utc).isoformat(),
        'new_models':new_count,'gallery_models':len(models),'models':models,'errors':errors,'warnings':warnings,
        'previous_assets':preservation,'previous_assets_unchanged':all(x['unchanged'] for x in preservation.values()),
        'gallery':gallery,'limits':['Static fan models, no rigs or animations.',
        'No game-engine runtime or deformation test. Components may intersect.',
        'Display scale is normalized independently; canonical relative heights are not asserted.']}
(OUT/'catalog_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'passed':report['passed'],'new_models':new_count,'gallery_models':len(models),
                  'previous_assets_unchanged':report['previous_assets_unchanged'],'errors':errors,'warnings':warnings},ensure_ascii=False,indent=2))
if errors and not args.draft:raise SystemExit(1)
