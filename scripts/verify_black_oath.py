"""Reopen the source and GLB; validate real evaluated geometry and scope."""
import json
import math
import struct
from pathlib import Path

import bpy
import bmesh
import numpy as np

OUT=Path(__file__).resolve().parents[1]/'assets'/'PirateShip'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'BlackOath.blend'))
attribution=bpy.context.scene.get('asset_attribution','')
embedded_credit=bpy.data.texts.get('SOURCE_LICENSE.txt')
embedded_credit=embedded_credit.as_string() if embedded_credit else ''
source_objects=[o for c in bpy.context.scene.collection.children if not c.name.startswith('90_')
                for o in c.objects if o.type in {'MESH','CURVE'}]
errors=[]
warnings=[]


def inspect(objects,topology=False):
    graph=bpy.context.evaluated_depsgraph_get()
    low=np.full(3,np.inf)
    high=np.full(3,-np.inf)
    triangles=0
    degenerates=[]
    boundaries=[]
    normals=[]
    material_names=set()
    for o in objects:
        eo=o.evaluated_get(graph)
        d=eo.to_mesh()
        if not d or not len(d.vertices):
            errors.append(o.name+': no evaluated geometry')
            eo.to_mesh_clear()
            continue
        xyz=np.empty(len(d.vertices)*3,dtype=np.float64)
        d.vertices.foreach_get('co',xyz)
        xyz=xyz.reshape(-1,3)
        if not np.isfinite(xyz).all():
            errors.append(o.name+': nonfinite vertex')
        matrix=np.array(eo.matrix_world)
        world=xyz@matrix[:3,:3].T+matrix[:3,3]
        low=np.minimum(low,world.min(axis=0))
        high=np.maximum(high,world.max(axis=0))
        d.calc_loop_triangles()
        triangles+=len(d.loop_triangles)
        bad=sum(t.area<1e-11 for t in d.loop_triangles)
        if bad:
            degenerates.append({'object':o.name,'triangles':bad})
        if not d.materials or any(m is None for m in d.materials):
            errors.append(o.name+': missing material')
        material_names.update(m.name for m in d.materials if m)
        if o.type=='MESH' and not d.uv_layers:
            errors.append(o.name+': missing UV')
        if topology:
            bm=bmesh.new()
            bm.from_mesh(d)
            n=sum(not e.is_manifold for e in bm.edges)
            if n:
                boundaries.append({'object':o.name,'edges':n})
            n=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
            if n:
                normals.append({'object':o.name,'edges':n})
            bm.free()
        eo.to_mesh_clear()
    return {'objects':len(objects),'triangles':triangles,'materials':len(material_names),
            'bounds_m':{'min':low.tolist(),'max':high.tolist(),'size':(high-low).tolist()},
            'degenerate_triangles':degenerates,'nonmanifold_edges':boundaries,
            'inconsistent_winding':normals}


print('BLACK_OATH_VERIFY: source geometry',flush=True)
source=inspect(source_objects,True)
if source['degenerate_triangles']:
    errors.append('Source has degenerate triangles')
if source['nonmanifold_edges']:
    errors.append('Source has nonmanifold component edges')
if source['inconsistent_winding']:
    errors.append('Source has inconsistent component normals')
cannons=[o for o in source_objects if o.name.startswith(('Cannon_port_','Cannon_starboard_'))]
if len(cannons)!=48:
    errors.append('Expected 48 bored cannon barrels')
sail_names=['Fore_course','Fore_topsail','Fore_topgallant','Main_course','Main_topsail',
            'Main_topgallant','Mizzen_lateen','Flying_jib','Inner_staysail']
if any(name not in bpy.data.objects for name in sail_names):
    errors.append('Missing named sail')
if any(f'Mast_{i}_lower' not in bpy.data.objects for i in range(1,4)):
    errors.append('Missing main mast')
images=[im for im in bpy.data.images if im.name.endswith('_BaseColor')]
if not images or not all(im.packed_file for im in images):
    errors.append('Missing or unpacked surface image')
source['packed_images']=len(images)
source['cannons']=len(cannons)
source['sails']=len(sail_names)
source['masts']=3

raw=(OUT/'BlackOath.glb').read_bytes()
magic,version,total=struct.unpack_from('<III',raw,0)
if magic!=0x46546C67 or version!=2 or total!=len(raw):
    errors.append('Invalid GLB container')
length,kind=struct.unpack_from('<II',raw,12)
assert kind==0x4E4F534A
gltf=json.loads(raw[20:20+length])
if any('uri' in im for im in gltf.get('images',[])):
    errors.append('GLB has external images')
if gltf.get('cameras') or 'KHR_lights_punctual' in gltf.get('extensions',{}):
    errors.append('Presentation camera/light exported')
if any('Presentation' in n.get('name','') for n in gltf.get('nodes',[])):
    errors.append('Presentation sea leaked into GLB')

print('BLACK_OATH_VERIFY: GLB roundtrip',flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(OUT/'BlackOath.glb'))
imported=[o for o in bpy.context.scene.objects if o.type=='MESH']
delivery=inspect(imported)
if len(imported)!=9:
    errors.append('Expected nine logical GLB meshes')
if delivery['triangles']!=source['triangles']:
    errors.append('GLB triangle count differs from evaluated source')
delta=max(abs(a-b) for k in ['min','max']
          for a,b in zip(source['bounds_m'][k],delivery['bounds_m'][k]))
if delta>.005:
    errors.append('GLB bounds difference exceeds 5 mm')
if delivery['degenerate_triangles']:
    errors.append('GLB has degenerate triangles')
delivery['max_bounds_difference_m']=delta
delivery['embedded_images']=len(gltf.get('images',[]))
delivery['file_bytes']=len(raw)
render_sizes={}
render_files=['hero.png','stern_detail.png','deck_detail.png','profile.png']
manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
if manifest.get('figurehead_revision') in {'v02','v03','v04','v05'}:
    render_files+=['figurehead_detail.png','figurehead_front.png']
if manifest.get('figurehead_revision')=='v05':
    credit=(OUT/'SOURCE_LICENSE.txt').read_text(encoding='utf-8')
    if not credit or embedded_credit!=credit or attribution!=credit:
        errors.append('Source attribution is missing from the saved Blender file')
    if gltf.get('asset',{}).get('copyright')!=credit:
        errors.append('GLB attribution does not match SOURCE_LICENSE.txt')
for file in render_files:
    path=OUT/file
    if not path.exists():
        errors.append('Missing final render: '+file)
        continue
    if path.stat().st_mtime < (OUT/'BlackOath.blend').stat().st_mtime:
        errors.append('Render predates current Blender source: '+file)
    im=bpy.data.images.load(str(path),check_existing=False)
    render_sizes[file]=list(im.size)
    if min(im.size)<1000:
        errors.append('Render resolution too low: '+file)
report={'passed':not errors,'source':source,'glb':delivery,'renders':render_sizes,
        'errors':errors,'warnings':warnings,
        'limits':['Static exterior and exposed decks; no walkable cabin interior or sailing simulation.',
                  'Independent closed parts overlap intentionally; not a single watertight union.',
                  'Tiled UVs; no lightmap UV, engine LOD, collision or runtime performance test.',
                  'Base color images embedded in GLB; Blender procedural micro-bump is not baked.',
                  'Presentation water is static and excluded from GLB.']}
(OUT/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'passed':report['passed'],'triangles':source['triangles'],
                  'bounds':source['bounds_m'],'errors':errors,
                  'degenerates':source['degenerate_triangles'][:12],
                  'nonmanifold':source['nonmanifold_edges'][:12],
                  'winding':source['inconsistent_winding'][:12]},ensure_ascii=False,indent=2),flush=True)
assert not errors,'See assets/PirateShip/validation.json'
print('BLACK_OATH_VERIFY_OK',flush=True)
