"""Replace only the figurehead; prove other ship objects survived unchanged."""
import hashlib
import json
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets'/'PirateShip'
BACKUP=OUT/'Revisions'/'Skull_v03'
sys.path.insert(0,str(Path(__file__).parent))
from black_oath_export import export_ship
from black_oath_skull_v4 import build_skull
from black_oath_skull_adornments_v4 import build_adornments

OLD_PREFIXES=('Figurehead_cranium','Skull_','Upper_skull_','Lower_skull_','SkullV2_','SkullV3_')
NEW_PREFIX='SkullV4_'


def is_skull(o):
    return o.name.startswith(OLD_PREFIXES+(NEW_PREFIX,))


def untouched_signatures():
    result={}
    graph=bpy.context.evaluated_depsgraph_get()
    for o in bpy.context.scene.objects:
        if is_skull(o):
            continue
        h=hashlib.sha256()
        h.update(np.asarray(o.matrix_world,dtype=np.float64).tobytes())
        h.update(repr((o.type,o.hide_render,tuple(c.name for c in o.users_collection))).encode())
        if o.type in {'MESH','CURVE'}:
            eo=o.evaluated_get(graph)
            d=eo.to_mesh()
            for collection,prop,dtype,size in [(d.vertices,'co',np.float32,3),
                                              (d.loops,'vertex_index',np.int32,1),
                                              (d.polygons,'loop_total',np.int32,1),
                                              (d.polygons,'material_index',np.int32,1)]:
                values=np.empty(len(collection)*size,dtype=dtype)
                collection.foreach_get(prop,values)
                h.update(values.tobytes())
            # Persisted UVs are exact. Bevel's evaluated UV interpolation can
            # vary by a float32 ULP after reopening, checked separately below.
            for layer in (o.data.uv_layers if o.type=='MESH' else d.uv_layers):
                values=np.empty(len(layer.data)*2,dtype=np.float32)
                layer.data.foreach_get('uv',values)
                h.update(values.tobytes())
            h.update(repr(tuple(m.name if m else None for m in d.materials)).encode())
            eo.to_mesh_clear()
        result[o.name]=h.hexdigest()
    return result


def evaluated_uvs():
    result={}
    graph=bpy.context.evaluated_depsgraph_get()
    for o in bpy.context.scene.objects:
        if is_skull(o) or o.type not in {'MESH','CURVE'}:
            continue
        eo=o.evaluated_get(graph)
        d=eo.to_mesh()
        for layer in d.uv_layers:
            values=np.empty(len(layer.data)*2,dtype=np.float32)
            layer.data.foreach_get('uv',values)
            result[(o.name,layer.name)]=values
        eo.to_mesh_clear()
    return result


def check_evaluated_uvs(before):
    after=evaluated_uvs()
    assert before.keys()==after.keys(),'Evaluated UV layer names changed'
    maximum=0
    for key,a in before.items():
        b=after[key]
        assert a.shape==b.shape,'Evaluated UV layout changed: '+str(key)
        delta=float(np.max(np.abs(a-b))) if a.size else 0
        assert delta<=1e-6,'Evaluated UV drift: '+str((key,delta))
        maximum=max(maximum,delta)
    return maximum


def untouched_materials():
    materials={m for o in bpy.context.scene.objects if not is_skull(o) and o.type in {'MESH','CURVE'}
               for m in o.data.materials if m}
    result={}
    for m in materials:
        data=[tuple(m.diffuse_color)]
        if m.use_nodes:
            for node in sorted(m.node_tree.nodes,key=lambda n:n.name):
                values=[]
                for socket in node.inputs:
                    if hasattr(socket,'default_value'):
                        v=socket.default_value
                        values.append((socket.name,tuple(v) if hasattr(v,'__len__') and not isinstance(v,str) else v))
                data.append((node.name,node.type,values))
                image=getattr(node,'image',None)
                if image:
                    data.append((image.name,hashlib.sha256(image.packed_file.data).hexdigest()
                                 if image.packed_file else image.filepath))
            data.append(sorted((link.from_node.name,link.from_socket.name,link.to_node.name,link.to_socket.name)
                               for link in m.node_tree.links))
        result[m.name]=hashlib.sha256(repr(data).encode()).hexdigest()
    return result


assert (BACKUP/'BlackOath.blend').exists(),'Missing protected original'
bpy.ops.wm.open_mainfile(filepath=str(BACKUP/'BlackOath.blend'))
bpy.context.preferences.filepaths.save_version=0
before=untouched_signatures()
before_materials=untouched_materials()
before_evaluated_uvs=evaluated_uvs()
old_names=[o.name for o in bpy.context.scene.objects if is_skull(o)]
for name in old_names:
    obj=bpy.data.objects[name]
    data=obj.data if obj.type in {'MESH','CURVE'} else None
    kind=obj.type
    bpy.data.objects.remove(obj,do_unlink=True)
    if data and data.users==0:
        (bpy.data.meshes if kind=='MESH' else bpy.data.curves).remove(data)
for material in list(bpy.data.materials):
    if material.name.startswith(('SkullV2_','SkullV3_')) and material.users==0:
        bpy.data.materials.remove(material)
for image in list(bpy.data.images):
    if image.name.startswith(('SkullV2_','SkullV3_')) and image.users==0:
        bpy.data.images.remove(image)
ornaments=bpy.data.collections['08_Ornament']
created=build_skull(ornaments)+build_adornments(ornaments)
bpy.context.view_layer.update()
after=untouched_signatures()
assert before==after,'Unexpected change outside the skull'
assert before_materials==untouched_materials(),'Unexpected material change outside the skull'
check_evaluated_uvs(before_evaluated_uvs)
assert created and all(o.name.startswith(NEW_PREFIX) for o in created)
new_names=[o.name for o in created]
graph=bpy.context.evaluated_depsgraph_get()
bad=[]
connected_components={}
for o in created:
    if o.type not in {'MESH','CURVE'}:
        continue
    eo=o.evaluated_get(graph)
    d=eo.to_mesh()
    d.calc_loop_triangles()
    bm=bmesh.new()
    bm.from_mesh(d)
    nonmanifold=sum(not e.is_manifold for e in bm.edges)
    degenerate=sum(t.area<1e-11 for t in d.loop_triangles)
    if o.name in {'SkullV4_Cranium','SkullV4_Mandible'}:
        unseen=set(bm.verts)
        count=0
        while unseen:
            count+=1
            pending=[unseen.pop()]
            while pending:
                vertex=pending.pop()
                for edge in vertex.link_edges:
                    neighbor=edge.other_vert(vertex)
                    if neighbor in unseen:
                        unseen.remove(neighbor)
                        pending.append(neighbor)
        connected_components[o.name]=count
        if count!=1:
            bad.append({'object':o.name,'disconnected_components':count})
    if nonmanifold or degenerate or not d.uv_layers:
        bad.append({'object':o.name,'nonmanifold':nonmanifold,
                    'degenerate':degenerate,'uv':bool(d.uv_layers)})
    bm.free()
    eo.to_mesh_clear()
assert not bad,repr(bad)
assert len(connected_components)==2,'Missing unified cranium or mandible'
bpy.context.scene['figurehead_revision']='v04 / angular anatomical skull and weathered nautical fittings'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BlackOath.blend'))
groups={c.name:c for c in bpy.context.scene.collection.children}
triangles=export_ship(bpy.context.scene,groups,OUT)
manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
manifest['evaluated_triangles']=triangles
manifest['figurehead_revision']='v04'
manifest['figurehead_reference']='Concepts/skull_reference_v03.png'
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.ops.wm.open_mainfile(filepath=str(OUT/'BlackOath.blend'))
reopened=untouched_signatures()
assert before==reopened,'Saved-file preservation failure'
assert before_materials==untouched_materials(),'Saved-file material preservation failure'
evaluated_uv_delta=check_evaluated_uvs(before_evaluated_uvs)
report={'passed':True,'untouched_objects':len(before),'other_geometry_uv_material_assignment_unchanged':True,
        'other_shader_parameters_and_packed_images_unchanged':True,
        'base_uvs_bit_exact':True,'max_evaluated_uv_delta':evaluated_uv_delta,
        'evaluated_uv_tolerance':1e-6,
        'old_skull_objects':old_names,'new_skull_objects':new_names,'new_skull_topology_errors':bad,
        'core_connected_components':connected_components,
        'backup':'Revisions/Skull_v03/BlackOath.blend','evaluated_triangles':triangles,
        'revision':'v04','reference':'Concepts/skull_reference_v03.png'}
(OUT/'skull_revision_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('BLACK_OATH_SKULL_REVISION_OK '+json.dumps({'untouched_objects':len(before),'triangles':triangles}),flush=True)
