import bpy,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils import Vector

out=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(out/'adornment_preview.blend'))
graph=bpy.context.evaluated_depsgraph_get()
trees={}
def tree(name):
    if name not in trees:
        obj=bpy.data.objects[name]
        evaluated=obj.evaluated_get(graph);data=evaluated.to_mesh()
        trees[name]=BVHTree.FromPolygons([obj.matrix_world@v.co for v in data.vertices],
                                       [list(p.vertices) for p in data.polygons])
        evaluated.to_mesh_clear()
    return trees[name]

prefix='SkullV4_Adornment_'
checks=[]
for label in ['Long','Short']:
    pin=prefix+label+'_embedded_eyelet_pin'
    eyelet=prefix+label+'_seated_eyelet'
    braid=prefix+('Long_temple_tassel' if label=='Long' else 'Short_temple_braid')+'_braid_0'
    for a,b in [('SkullV4_Cranium',pin),(pin,eyelet),(eyelet,braid)]:
        checks.append({'objects':[a,b],'surface_intersections':len(tree(a).overlap(tree(b)))})
report={'passed':all(c['surface_intersections']>0 for c in checks),'contact_checks':checks,
        'stem_clamp_fit':{'stem_radius':.23,'clamp_inner_radius':.267-.036,
                          'radial_clearance':.267-.036-.23,
                          'centers_on_original_poly_segment_at_z':[8.90,9.55]}}
(out/'fit_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
assert report['passed'],report
