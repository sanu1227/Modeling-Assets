"""Validate the saved Gardevoir model and reimport its standalone GLB."""
import json
from pathlib import Path
from datetime import datetime, timezone
import bpy
import bmesh
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets'/'PokemonPopular'/'Gardevoir'
errors=[]

def inspect(objects,label,weld=False):
    graph=bpy.context.evaluated_depsgraph_get()
    low=np.full(3,np.inf);high=np.full(3,-np.inf)
    triangles=0;vertices=0;bad_area=0;nonfinite=0;topology=[];materials=set();missing_uv=[]
    for obj in objects:
        ev=obj.evaluated_get(graph);mesh=ev.to_mesh()
        xyz=np.empty(len(mesh.vertices)*3,dtype=np.float64);mesh.vertices.foreach_get('co',xyz)
        matrix=np.asarray(ev.matrix_world)
        world=xyz.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]
        if not np.isfinite(world).all():nonfinite+=1
        low=np.minimum(low,world.min(axis=0));high=np.maximum(high,world.max(axis=0))
        vertices+=len(mesh.vertices);mesh.calc_loop_triangles();count=len(mesh.loop_triangles);triangles+=count
        indices=np.empty(count*3,dtype=np.int32);mesh.loop_triangles.foreach_get('vertices',indices)
        p=world[indices.reshape(-1,3)]
        area=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)*.5
        bad=int(np.count_nonzero(area<1e-13));bad_area+=bad
        if bad:errors.append(f'{label}/{obj.name}: {bad} degenerate triangles')
        if not mesh.materials or any(m is None for m in mesh.materials):errors.append(f'{label}/{obj.name}: missing material')
        materials.update(m.name for m in mesh.materials if m)
        if not mesh.uv_layers:missing_uv.append(obj.name)
        elif not all(np.isfinite(p.uv).all() for p in mesh.uv_layers.active.data):errors.append(f'{label}/{obj.name}: nonfinite UV')
        bm=bmesh.new();bm.from_mesh(mesh)
        if weld:bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
        boundary=sum(e.is_boundary for e in bm.edges);nonmanifold=sum(not e.is_manifold for e in bm.edges)
        inconsistent=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
        if nonmanifold or inconsistent:
            topology.append(dict(object=obj.name,boundary_edges=boundary,nonmanifold_edges=nonmanifold,inconsistent_edges=inconsistent))
        bm.free();ev.to_mesh_clear()
    if nonfinite:errors.append(f'{label}: nonfinite geometry')
    if topology:errors.append(f'{label}: nonmanifold or inconsistent components')
    if missing_uv:errors.append(f'{label}: missing UV')
    return dict(meshes=len(objects),vertices=vertices,triangles=triangles,materials=sorted(materials),bounds=dict(min=low.tolist(),max=high.tolist(),size=(high-low).tolist()),degenerate_triangles=bad_area,nonfinite_objects=nonfinite,topology_issues=topology,objects_without_uv=missing_uv)

bpy.ops.wm.open_mainfile(filepath=str(OUT/'Gardevoir.blend'))
col=bpy.data.collections.get('Pokemon_Gardevoir')
source=inspect([o for o in col.objects if o.type=='MESH'],'source')
images=[dict(name=i.name,packed=bool(i.packed_file),size=list(i.size)) for i in bpy.data.images if i.type=='IMAGE']
if any(not i['packed'] for i in images):errors.append('Unpacked image in source')
existing=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(OUT/'Gardevoir.glb'))
imported=[o for o in bpy.data.objects if o not in existing]
roundtrip=inspect([o for o in imported if o.type=='MESH'],'glb',weld=True)
if any(o.type in {'LIGHT','CAMERA','FONT'} or o.name.startswith(('Studio','Display')) for o in imported):errors.append('Presentation objects leaked to GLB')
if source['triangles']!=roundtrip['triangles']:errors.append('GLB triangle count mismatch')
delta=float(np.max(np.abs(np.array([source['bounds']['min'],source['bounds']['max']])-np.array([roundtrip['bounds']['min'],roundtrip['bounds']['max']]))))
if delta>1e-5:errors.append(f'GLB bounds mismatch {delta}')
if abs(source['bounds']['min'][2])>.003:errors.append('Ground position differs from zero')
result=dict(passed=not errors,checked_at=datetime.now(timezone.utc).isoformat(),blender_version=bpy.app.version_string,source=source,glb=roundtrip,bounds_max_difference_m=delta,packed_images=images,errors=errors,limitations=['Static fan sculpture, no rig or animation','Closed mesh components overlap; not a single 3D-printable solid','Generic UV coordinates on untextured parts; no deformation topology claim','No engine runtime test'])
(OUT/'validation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(dict(passed=not errors,errors=errors,triangles=source['triangles'],meshes=source['meshes'],bounds_delta=delta),indent=2),flush=True)
if errors:raise RuntimeError('GARDEVOIR_VALIDATION_FAILED')
print('GARDEVOIR_VALIDATION_OK',flush=True)

