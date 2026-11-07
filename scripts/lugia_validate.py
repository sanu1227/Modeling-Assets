"""Reopen and validate current Lugia source and GLB, without changing either."""
import hashlib
import json
from pathlib import Path
import struct

import bpy
import bmesh
import numpy as np

OUT=Path(__file__).resolve().parents[1]/'assets'/'PokemonPopular'/'Lugia'
EXPECTED_TEXTURES=2
errors=[]


def inspect(objects,label):
    graph=bpy.context.evaluated_depsgraph_get()
    lower=np.full(3,np.inf);upper=np.full(3,-np.inf)
    count=0;vertices=0;degenerate=[];topology=[];uv_missing=[];materials=set()
    for obj in objects:
        evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh()
        try:
            xyz=np.empty(len(mesh.vertices)*3,dtype=np.float64)
            mesh.vertices.foreach_get('co',xyz)
            matrix=np.array(evaluated.matrix_world)
            xyz=xyz.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]
            if not np.isfinite(xyz).all():errors.append(label+': nonfinite vertices in '+obj.name)
            lower=np.minimum(lower,xyz.min(axis=0));upper=np.maximum(upper,xyz.max(axis=0))
            vertices+=len(xyz)
            mesh.calc_loop_triangles();count+=len(mesh.loop_triangles)
            idx=np.empty(len(mesh.loop_triangles)*3,dtype=np.int32)
            mesh.loop_triangles.foreach_get('vertices',idx)
            pts=xyz[idx.reshape(-1,3)]
            area=np.linalg.norm(np.cross(pts[:,1]-pts[:,0],pts[:,2]-pts[:,0]),axis=1)*.5
            bad=int(np.count_nonzero(area<1e-12))
            if bad:
                degenerate.append({'object':obj.name,'triangles':bad,'minimum_area':float(area.min())})
                errors.append(label+': degenerate triangles in '+obj.name)
            if not mesh.materials or any(m is None for m in mesh.materials):
                errors.append(label+': missing material in '+obj.name)
            materials.update(m.name for m in mesh.materials if m)
            if not mesh.uv_layers:
                uv_missing.append(obj.name);errors.append(label+': missing UV in '+obj.name)
            bm=bmesh.new();bm.from_mesh(mesh)
            if label=='glb':
                # glTF splits vertices at normals/UV seams. Weld temporary copy only.
                bm.transform(evaluated.matrix_world)
                bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
            nonmanifold=sum(not e.is_manifold for e in bm.edges)
            inconsistent=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
            if nonmanifold or inconsistent:
                topology.append({'object':obj.name,'nonmanifold_edges':nonmanifold,'inconsistent_winding_edges':inconsistent})
                if label=='source':errors.append(label+': topology issue in '+obj.name)
            bm.free()
        finally:evaluated.to_mesh_clear()
    return {'objects':len(objects),'vertices':vertices,'triangles':count,
            'bounds_m':{'min':lower.tolist(),'max':upper.tolist(),'size':(upper-lower).tolist()},
            'materials':sorted(materials),'degenerate_triangles':degenerate,
            'nonmanifold_edges':sum(t['nonmanifold_edges'] for t in topology),
            'topology_details':topology,'objects_without_uv':uv_missing}


report={'passed':False,'errors':errors,'limits':[
    'Static fan sculpture. No rigging, deformation retopology or engine runtime validation.',
    'Closed individual components may overlap; not validated as a single printable watertight solid.',
    'Artistic resemblance assessed against local official-artwork references separately from geometry checks.',
    'GLB topology is checked after welding a temporary copy at 0.0000001 m; source geometry is untouched.']}
try:
    source=OUT/'Lugia.blend';glb=OUT/'Lugia.glb'
    report['sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,glb)}
    bpy.ops.wm.open_mainfile(filepath=str(source))
    collection=bpy.data.collections['Pokemon_Lugia']
    report['source']=inspect([o for o in collection.all_objects if o.type=='MESH'],'source')
    dorsal_plates=sum(o.name.startswith('05_Dorsal plate pair ') for o in collection.all_objects)
    tail_spikes=sum(o.name.startswith('06_') for o in collection.all_objects)
    report['source']['dorsal_plates']=dorsal_plates
    report['source']['blue_tail_spikes']=tail_spikes
    if dorsal_plates!=10 or tail_spikes!=2:errors.append('Canonical dorsal plate or tail spike count mismatch')
    images={node.image.name:node.image for obj in collection.all_objects if obj.type=='MESH'
            for material in obj.data.materials if material and material.use_nodes
            for node in material.node_tree.nodes if node.type=='TEX_IMAGE' and node.image}
    report['source']['packed_images']=[{'name':image.name,'size':list(image.size),'packed':bool(image.packed_file)} for image in images.values()]
    if len(images)!=EXPECTED_TEXTURES or any(not image.packed_file for image in images.values()):errors.append('Missing packed source painting textures')
    if abs(report['source']['bounds_m']['min'][2])>1e-5:errors.append('Source floor contact is not Z=0')
    raw=glb.read_bytes();magic,version,total=struct.unpack_from('<III',raw)
    if magic!=0x46546C67 or version!=2 or total!=len(raw):errors.append('Invalid GLB header')
    length,kind=struct.unpack_from('<II',raw,12)
    data=json.loads(raw[20:20+length])
    if data.get('cameras') or data.get('extensions',{}).get('KHR_lights_punctual'):errors.append('Presentation data in GLB')
    if any('uri' in image for image in data.get('images',[])):errors.append('External images required by GLB')
    if len(data.get('images',[]))!=EXPECTED_TEXTURES or any('bufferView' not in image for image in data.get('images',[])):errors.append('Missing embedded GLB painting textures')
    if any('Studio' in n.get('name','') or 'Display' in n.get('name','') for n in data.get('nodes',[])):errors.append('Stage objects exported')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    report['glb']=inspect([o for o in bpy.context.scene.objects if o.type=='MESH'],'glb')
    if report['source']['triangles']!=report['glb']['triangles']:errors.append('GLB triangle count mismatch')
    delta=max(abs(a-b) for key in ('min','max') for a,b in zip(report['source']['bounds_m'][key],report['glb']['bounds_m'][key]))
    report['glb']['max_bounds_difference_m']=delta
    if delta>1e-5:errors.append('GLB bounds mismatch > 0.00001 m')
    report['glb']['file_bytes']=len(raw)
except Exception as exc:errors.append(type(exc).__name__+': '+str(exc))
report['passed']=not errors
(OUT/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
print(json.dumps({'passed':report['passed'],'errors':errors,'source_triangles':report.get('source',{}).get('triangles')}),flush=True)
if errors:raise SystemExit(1)

