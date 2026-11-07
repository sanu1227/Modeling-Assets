"""Inspect source and roundtrip the portable AUREL exterior."""
import json
import math
import struct
from pathlib import Path

import bmesh
import bpy

OUT=Path(__file__).resolve().parents[1]/'assets/ModernTower'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Aurel_Day.blend'))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.parent and o.parent.name=='AUREL_ROOT']
errors=[]
graph=bpy.context.evaluated_depsgraph_get()
cache={}
total=0
low,high=[math.inf]*3,[-math.inf]*3
for obj in objects:
    key=(obj.data.as_pointer(),tuple((m.type,getattr(m,'width',0),getattr(m,'segments',0)) for m in obj.modifiers))
    if key not in cache:
        evaluated=obj.evaluated_get(graph); data=evaluated.to_mesh(); data.calc_loop_triangles()
        bm=bmesh.new(); bm.from_mesh(data)
        bad={'degenerate':sum(f.calc_area()<1e-12 for f in bm.faces),
             'nonmanifold':sum(not e.is_manifold for e in bm.edges),
             'inconsistent_normals':sum(e.is_manifold and not e.is_contiguous for e in bm.edges)}
        if any(bad.values()): errors.append({'object':obj.name,**bad})
        bm.free()
        if not data.uv_layers or not data.materials:
            errors.append({'object':obj.name,'reason':'missing UV/material'})
        if any(not math.isfinite(c) for v in data.vertices for c in v.co):
            errors.append({'object':obj.name,'reason':'nonfinite vertex'})
        cache[key]=(len(data.loop_triangles),[v.co.copy() for v in data.vertices])
        evaluated.to_mesh_clear()
    triangles,coords=cache[key]; total+=triangles
    for co in coords:
        p=obj.matrix_world@co
        for i in range(3): low[i]=min(low[i],p[i]); high[i]=max(high[i],p[i])
materials={m.name for o in objects for m in o.data.materials if m}
source={'mesh_objects':len(objects),'unique_evaluated_meshes':len(cache),'triangles':total,
        'materials':len(materials),'bounds_m':[low,high],'size_m':[b-a for a,b in zip(low,high)]}
raw=(OUT/'Aurel.glb').read_bytes()
magic,version,length=struct.unpack_from('<III',raw)
json_length,kind=struct.unpack_from('<II',raw,12)
assert magic==0x46546C67 and version==2 and length==len(raw) and kind==0x4E4F534A
gltf=json.loads(raw[20:20+json_length])
if any('uri' in image for image in gltf.get('images',[])):
    errors.append({'reason':'external GLB image dependency'})
if gltf.get('cameras') or 'KHR_lights_punctual' in gltf.get('extensions',{}):
    errors.append({'reason':'render rig exported'})
if any('Context_' in n.get('name','') or 'Ground' in n.get('name','') for n in gltf.get('nodes',[])):
    errors.append({'reason':'presentation context exported'})
transmission=sum('KHR_materials_transmission' in m.get('extensions',{}) for m in gltf['materials'])
if transmission<4: errors.append({'reason':'glass transmission missing'})
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(OUT/'Aurel.glb'))
imported=[o for o in bpy.context.scene.objects if o.type=='MESH']
roundtrip=0; low2,high2=[math.inf]*3,[-math.inf]*3
for obj in imported:
    obj.data.calc_loop_triangles(); roundtrip+=len(obj.data.loop_triangles)
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co
        for i in range(3): low2[i]=min(low2[i],p[i]); high2[i]=max(high2[i],p[i])
delta=max(abs(a-b) for first,second in ((low,low2),(high,high2)) for a,b in zip(first,second))
if roundtrip!=total or len(imported)!=6 or delta>.001:
    errors.append({'reason':'GLB geometry mismatch','delta':delta})
report={'passed':not errors,'source':source,'glb':{'mesh_objects':len(imported),'triangles':roundtrip,
    'max_bounds_difference_m':delta,'embedded_images':len(gltf.get('images',[])),
    'transmission_materials':transmission,'file_bytes':len(raw)},'errors':errors,
    'limits':['Architectural visualization exterior; only limited visible interior detail.',
              'No structural engineering, collision, LOD or target-engine runtime validation.',
              'GLB supports transmission; target engine/importer must support the extension.',
              'Procedural image-based bump remains in Blender; not baked as a GLB normal map.']}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
assert not errors,'AUREL validation failed'
print('AUREL_VERIFY_OK',flush=True)
