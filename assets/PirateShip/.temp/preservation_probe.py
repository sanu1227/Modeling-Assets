import ast, hashlib, json
from pathlib import Path
import bpy
import numpy as np
root=Path(__file__).resolve().parents[3]
tree=ast.parse((root/'scripts'/'refine_black_oath_skull.py').read_text(encoding='utf-8'))
ns=dict(bpy=bpy,np=np,hashlib=hashlib,
        OLD_PREFIXES=('Figurehead_cranium','Skull_','Upper_skull_','Lower_skull_'),NEW_PREFIX='SkullV2_')
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'probe','exec'),ns)
states=[]
for path in [root/'assets/PirateShip/Revisions/Skull_v01/BlackOath.blend',root/'assets/PirateShip/BlackOath.blend']:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    signatures=ns['untouched_signatures']()
    mats=ns['untouched_materials']()
    details={}
    g=bpy.context.evaluated_depsgraph_get()
    for o in bpy.context.scene.objects:
        if ns['is_skull'](o):
            continue
        details[o.name]={'matrix':np.array(o.matrix_world).tolist(),
                         'collections':[c.name for c in o.users_collection],
                         'type':o.type,'hide':o.hide_render}
        if o.type in {'MESH','CURVE'}:
            e=o.evaluated_get(g)
            d=e.to_mesh()
            a=np.empty(len(d.vertices)*3,dtype=np.float32)
            d.vertices.foreach_get('co',a)
            details[o.name]['verts']=a
            details[o.name]['counts']=[len(d.vertices),len(d.polygons),len(d.loops)]
            details[o.name]['mats']=[m.name for m in d.materials]
            e.to_mesh_clear()
    states.append((signatures,mats,details))
a,b=states
changed=[n for n in a[0] if a[0][n]!=b[0].get(n)]
out=[]
for n in changed:
    x,y=a[2][n],b[2][n]
    item={'name':n,'matrix_delta':float(np.max(np.abs(np.array(x['matrix'])-y['matrix']))),
          'collections_equal':x['collections']==y['collections'],'hide_equal':x['hide']==y['hide']}
    if 'verts' in x:
        item['counts']=[x['counts'],y['counts']]
        item['vertex_delta']=float(np.max(np.abs(x['verts']-y['verts']))) if x['verts'].shape==y['verts'].shape else None
        item['materials_equal']=x['mats']==y['mats']
    out.append(item)
report={'changed_count':len(changed),'changed':out,
        'materials_equal':a[1]==b[1],'names_equal':set(a[0])==set(b[0])}
(root/'assets/PirateShip/.temp/preservation_probe.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2)[:8000],flush=True)
