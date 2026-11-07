import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
s=bpy.data.objects['SkullV2_Cranium']
b=BVHTree.FromObject(s,bpy.context.evaluated_depsgraph_get())
for o in bpy.data.objects:
    if not o.name.startswith('SkullV2_UpperTooth'): continue
    p=o.matrix_world@Vector((0,0,max(v.co.z for v in o.data.vertices)))
    q=s.matrix_world.inverted()@p
    co,normal,index,distance=b.find_nearest(q)
    print(o.name,round((q-co).dot(normal),6))
