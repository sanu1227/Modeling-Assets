import json, math, struct
from pathlib import Path
import bpy
import numpy as np

OUT=Path(__file__).resolve().parents[1]
changed=json.loads((OUT/'.temp/preservation_probe.json').read_text())['changed']
names=[v['name'] for v in changed]

def arr(collection,prop,n,dtype):
    a=np.empty(len(collection)*n,dtype=dtype)
    collection.foreach_get(prop,a)
    return a

def snapshot(data):
    arrays={
      'co':arr(data.vertices,'co',3,np.float32),
      'loop_vertex_index':arr(data.loops,'vertex_index',1,np.int32),
      'poly_loop_start':arr(data.polygons,'loop_start',1,np.int32),
      'poly_loop_total':arr(data.polygons,'loop_total',1,np.int32),
      'poly_material_index':arr(data.polygons,'material_index',1,np.int32),
      'poly_use_smooth':arr(data.polygons,'use_smooth',1,np.bool_),
      'edge_vertices':arr(data.edges,'vertices',2,np.int32),
    }
    for layer in data.uv_layers:
        arrays['uv:'+layer.name]=arr(layer.data,'uv',2,np.float32)
    return arrays

def modifier_properties(o):
    out=[]
    for modifier in o.modifiers:
        props={}
        for p in modifier.bl_rna.properties:
            if p.identifier=='rna_type' or p.type not in {'BOOLEAN','INT','FLOAT','STRING','ENUM'}:
                continue
            value=getattr(modifier,p.identifier)
            if hasattr(value,'__len__') and not isinstance(value,(str,set)):
                value=list(value)
            if isinstance(value,set): value=sorted(value)
            props[p.identifier]=value
        out.append(props)
    return out

states=[]
files=[OUT/'Revisions/Skull_v01/BlackOath.blend',OUT/'BlackOath.blend']*2
for file in files:
    bpy.ops.wm.open_mainfile(filepath=str(file))
    graph=bpy.context.evaluated_depsgraph_get()
    state={}
    for name in names:
        o=bpy.data.objects[name]
        e=o.evaluated_get(graph)
        d=e.to_mesh()
        state[name]={'evaluated':snapshot(d),'base':snapshot(o.data) if o.type=='MESH' else None,
                     'modifiers':[(m.name,m.type) for m in o.modifiers],
                     'modifier_properties':modifier_properties(o)}
        e.to_mesh_clear()
    states.append(state)

def canonical_faces(a):
    result={}
    layers=[k for k in a if k.startswith('uv:')]
    for start,total,material,smooth in zip(a['poly_loop_start'],a['poly_loop_total'],a['poly_material_index'],a['poly_use_smooth']):
        loopids=list(range(int(start),int(start+total)))
        vertices=[int(a['loop_vertex_index'][i]) for i in loopids]
        rotation=min(range(len(vertices)),key=lambda j:vertices[j:]+vertices[:j])
        vertices=vertices[rotation:]+vertices[:rotation]
        loopids=loopids[rotation:]+loopids[:rotation]
        key=(tuple(vertices),int(material),bool(smooth))
        assert key not in result, 'duplicate face key'
        result[key]={k:a[k].reshape(-1,2)[loopids] for k in layers}
    return result

report=[]
allfield={}
max_uv=0
max_ulp=0
for name in names:
    a,b=(s[name] for s in states[:2])
    item={'name':name,'modifiers':a['modifiers'],'modifier_list_equal':a['modifiers']==b['modifiers'],
          'fields':{},'base_exact':True,
          'modifier_properties_equal':a['modifier_properties']==b['modifier_properties']}
    for stage in ['base','evaluated']:
        if a[stage] is None: continue
        for key,x in a[stage].items():
            y=b[stage][key]
            if x.tobytes()==y.tobytes(): continue
            if stage=='base': item['base_exact']=False
            mismatch=np.flatnonzero(x!=y)
            bits=np.flatnonzero(x.view(np.uint8)!=y.view(np.uint8))
            delta=np.abs(x.astype(np.float64)-y.astype(np.float64))
            k=stage+':'+key
            item['fields'][k]={'unequal_values':len(mismatch),'unequal_bytes':len(bits),'max_abs':float(delta.max()),
                              'examples':[[int(i),float(x[i]),float(y[i])] for i in mismatch[:6]]}
            if stage=='evaluated' and key.startswith('uv:'):
                def ordered(v):
                    u=v.view(np.uint32)
                    return np.where(u&0x80000000,(~u)&0xffffffff,u|0x80000000).astype(np.int64)
                ulp=np.abs(ordered(x)-ordered(y))
                ulp[(x==0)&(y==0)]=0
                item['fields'][k]['max_ulp']=int(ulp.max())
                max_ulp=max(max_ulp,int(ulp.max()))
            allfield[k]=allfield.get(k,0)+1
    af,bf=canonical_faces(a['evaluated']),canonical_faces(b['evaluated'])
    item['oriented_face_topology_equal']=set(af)==set(bf)
    item['uv_delta_by_corresponding_corner']=0
    item['uv_numeric_equal']=True
    if set(af)==set(bf):
        for key in af:
            for layer in af[key]:
                x,y=af[key][layer],bf[key][layer]
                delta=float(np.max(np.abs(x-y)))
                item['uv_delta_by_corresponding_corner']=max(item['uv_delta_by_corresponding_corner'],delta)
                item['uv_numeric_equal'] &= bool(np.array_equal(x,y))
    max_uv=max(max_uv,item['uv_delta_by_corresponding_corner'])
    report.append(item)
summary={'changed_objects':len(names),'different_fields':allfield,
         'all_base_data_exact':all(v['base_exact'] for v in report),
         'all_oriented_topology_equal':all(v['oriented_face_topology_equal'] for v in report),
         'all_corresponding_uv_numeric_equal':all(v['uv_numeric_equal'] for v in report),
         'max_corresponding_uv_abs_difference':max_uv,'max_uv_ulp':max_ulp,
         'all_modifier_properties_equal':all(v['modifier_properties_equal'] for v in report),
         'same_file_repeat_differences':{},'objects':report}
for i,label in [(0,'original'),(1,'current')]:
    changes=[]
    for name in names:
        a,b=states[i][name]['evaluated'],states[i+2][name]['evaluated']
        for key in a:
            if a[key].tobytes()!=b[key].tobytes():
                changes.append({'name':name,'field':key,'max_abs':float(np.max(np.abs(a[key].astype(float)-b[key].astype(float))))})
    summary['same_file_repeat_differences'][label]=changes
(OUT/'.temp/preservation_fields_probe.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='objects'},indent=2))
print(json.dumps(report[:3],indent=2))
