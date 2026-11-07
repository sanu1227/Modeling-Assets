import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector

out=Path(__file__).resolve().parent
report={'objects':[],'images':[]}
for o in bpy.data.objects:
    entry={'name':o.name,'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale),'modifiers':[(m.name,m.type) for m in o.modifiers]}
    if o.type=='MESH':
        points=[o.matrix_world@v.co for v in o.data.vertices]
        o.data.calc_loop_triangles()
        bm=bmesh.new();bm.from_mesh(o.data)
        entry.update(vertices=len(o.data.vertices),triangles=len(o.data.loop_triangles),uvs=list(o.data.uv_layers.keys()),materials=[m.name if m else None for m in o.data.materials],nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),bounds_min=[min(p[i] for p in points) for i in range(3)],bounds_max=[max(p[i] for p in points) for i in range(3)])
        bm.free()
    report['objects'].append(entry)
for im in bpy.data.images:
    report['images'].append({'name':im.name,'path':im.filepath,'size':list(im.size),'packed':bool(im.packed_file)})
report['texts']=list(bpy.data.texts.keys())
(out/'source_inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
