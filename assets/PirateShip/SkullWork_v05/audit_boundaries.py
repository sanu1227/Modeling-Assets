import bpy,bmesh,json
from pathlib import Path
o=bpy.data.objects['SkullV5_Anatomical_Source']
bm=bmesh.new();bm.from_mesh(o.data)
remaining=set(bm.verts);report=[]
while remaining:
    todo=[remaining.pop()];verts=set(todo)
    while todo:
        v=todo.pop()
        for e in v.link_edges:
            other=e.other_vert(v)
            if other in remaining:remaining.remove(other);verts.add(other);todo.append(other)
    edges={e for v in verts for e in v.link_edges}
    boundary={e for e in edges if e.is_boundary}
    loops=[]
    while boundary:
        todo=[boundary.pop()];loop=set(todo)
        while todo:
            e=todo.pop()
            for v in e.verts:
                for other in v.link_edges:
                    if other in boundary:boundary.remove(other);loop.add(other);todo.append(other)
        lv={v for e in loop for v in e.verts}
        loops.append({'edges':len(loop),'min':[min(v.co[i] for v in lv) for i in range(3)],'max':[max(v.co[i] for v in lv) for i in range(3)]})
    report.append({'vertices':len(verts),'faces':len({f for v in verts for f in v.link_faces}),'loops':loops})
report.sort(key=lambda item:-item['vertices'])
Path(__file__).with_name('boundary_classification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
