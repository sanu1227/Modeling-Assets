"""Verify saved LOD geometry, collision hulls, PBR maps and portable roundtrips."""
import hashlib
import json
import math
import struct
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

BASE=Path(__file__).resolve().parents[1]/'assets/MedievalShop'
OUT=BASE/'Optimized'
report=json.loads((OUT/'optimization_report.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(OUT/'MedievalShop_Optimized.blend'))
errors=[]
result={}


def measures(obj):
    obj.data.calc_loop_triangles()
    points=[obj.matrix_world@v.co for v in obj.data.vertices]
    bounds=[[min(p[i] for p in points) for i in range(3)],
            [max(p[i] for p in points) for i in range(3)]]
    return len(obj.data.loop_triangles),bounds


for level in range(3):
    obj=bpy.data.objects['MedievalShop_LOD'+str(level)]
    triangles,bounds=measures(obj)
    bm=bmesh.new(); bm.from_mesh(obj.data)
    degenerate=sum(f.calc_area()<1e-12 for f in bm.faces)
    nonmanifold=sum(not e.is_manifold for e in bm.edges)
    inconsistent=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
    bm.free()
    if degenerate or nonmanifold or inconsistent:
        errors.append(f'LOD{level}: geometry {degenerate}/{nonmanifold}/{inconsistent}')
    if len(obj.data.materials)!=1 or len(obj.data.uv_layers)!=1:
        errors.append(f'LOD{level}: must have one material and one surface UV layer')
    if any(not math.isfinite(c) or c<-.0001 or c>1.0001 for u in obj.data.uv_layers.active.data for c in u.uv):
        errors.append(f'LOD{level}: invalid atlas UV')
    if any(not math.isfinite(c) for v in obj.data.vertices for c in v.co):
        errors.append(f'LOD{level}: nonfinite vertex')
    result['LOD'+str(level)]={'triangles':triangles,'bounds_m':bounds,
        'degenerate_faces':degenerate,'nonmanifold_edges':nonmanifold,
        'inconsistent_normals':inconsistent}

colliders=[o for o in bpy.data.objects if o.name.startswith('UCX_MedievalShop_LOD0_')]
for obj in colliders:
    bm=bmesh.new(); bm.from_mesh(obj.data)
    closed=all(e.is_manifold for e in bm.edges)
    volume=bm.calc_volume(signed=False)
    # Every vertex must lie on or behind every face of a convex hull.
    convex=all((v.co-f.verts[0].co).dot(f.normal)<1e-5 for f in bm.faces for v in bm.verts)
    if not closed or volume<=0 or not convex:
        errors.append(obj.name+': invalid collision hull')
    bm.free()
if len(colliders)!=7:
    errors.append('Expected seven simple collision hulls')
if not all(o.hide_render and o.hide_get() for o in colliders):
    errors.append('Collision hulls visible in saved default scene')
if not bpy.data.objects['MedievalShop_LOD1'].hide_render or not bpy.data.objects['MedievalShop_LOD2'].hide_render:
    errors.append('Multiple LODs enabled at the same time')
for name in ('Shop_BaseColor','Shop_Normal','Shop_ORM','Shop_Emission'):
    im=bpy.data.images.get(name)
    if not im or not im.packed_file or tuple(im.size)!=(2048,2048):
        errors.append(name+': missing packed 2K map')

for level in range(3):
    path=OUT/f'MedievalShop_LOD{level}.glb'
    raw=path.read_bytes()
    magic,version,total=struct.unpack_from('<III',raw)
    length,kind=struct.unpack_from('<II',raw,12)
    assert magic==0x46546C67 and version==2 and len(raw)==total and kind==0x4E4F534A
    gltf=json.loads(raw[20:20+length])
    primitives=sum(len(m['primitives']) for m in gltf['meshes'])
    if len(gltf['meshes'])!=1 or primitives!=1 or len(gltf['materials'])!=1:
        errors.append(f'LOD{level}: GLB must contain one mesh, primitive and material')
    mat=gltf['materials'][0]
    if not all(key in mat for key in ('normalTexture','emissiveTexture')):
        errors.append(f'LOD{level}: normal or emission texture missing')
    if not all(key in mat['pbrMetallicRoughness'] for key in ('baseColorTexture','metallicRoughnessTexture')):
        errors.append(f'LOD{level}: PBR texture missing')
    if gltf.get('cameras') or any('UCX_' in n.get('name','') for n in gltf.get('nodes',[])):
        errors.append(f'LOD{level}: render GLB contains collision or cameras')
    if any('uri' in image for image in gltf['images']):
        errors.append(f'LOD{level}: external texture dependency')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    if len(objects)!=1:
        errors.append(f'LOD{level}: imported object count')
    tris,bounds=measures(objects[0])
    original=result['LOD'+str(level)]
    difference=max(abs(a-b) for axis,other in zip(bounds,original['bounds_m']) for a,b in zip(axis,other))
    if tris!=original['triangles'] or difference>.0001:
        errors.append(f'LOD{level}: imported shape differs')
    original.update({'glb_primitives':primitives,'glb_roundtrip_passed':tris==original['triangles'] and difference<.0001,
                     'file_bytes':len(raw)})

# Collision FBX is checked independently; engine-specific automatic assignment is not assumed.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(OUT/'MedievalShop_LOD0_collision.fbx'))
imported_hulls=[o for o in bpy.context.scene.objects if o.name.startswith('UCX_')]
visual=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('UCX_')]
if len(imported_hulls)!=7 or len(visual)!=1:
    errors.append('FBX visual/collision object counts differ')
else:
    triangles,bounds=measures(visual[0])
    delta=max(abs(a-b) for axis,other in zip(bounds,result['LOD0']['bounds_m']) for a,b in zip(axis,other))
    if triangles!=result['LOD0']['triangles'] or delta>.001:
        errors.append('FBX scale or geometry changed')

if hashlib.sha256((BASE/'MedievalShop.blend').read_bytes()).hexdigest()!=report['source_sha256_before']:
    errors.append('Editable source file changed')
if not result['LOD2']['triangles']<result['LOD1']['triangles']<result['LOD0']['triangles']<167792:
    errors.append('LOD triangle counts not strictly decreasing')
report['validation']={'passed':not errors,'lods':result,'collision_hulls':len(colliders),
                      'fbx_roundtrip_checked':True,'errors':errors,
                      'engine_runtime_tested':False}
(OUT/'optimization_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report['validation'],indent=2),flush=True)
assert not errors, 'Optimization verification failed'
print('SHOP_OPTIMIZATION_VERIFY_OK',flush=True)
