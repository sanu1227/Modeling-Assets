"""Export evaluated ship geometry without altering the editable source."""
import bpy
import numpy as np

def export_ship(scene, groups, out):
    OUT = out
    def log(message):
        print('BLACK_OATH_EXPORT: ' + message, flush=True)
    export_group=bpy.data.collections.new('_EXPORT_TEMP')
    scene.collection.children.link(export_group)
    exports=[]
    triangle_count=0
    for name,collection in groups.items():
        if name.startswith('90_') or not any(o.type in {'MESH','CURVE'} for o in collection.objects):
            continue
        verts,faces,uvs,mi,sm=[],[],[],[],[]
        materials=[]
        graph=bpy.context.evaluated_depsgraph_get()
        for o in list(collection.objects):
            if o.type not in {'MESH','CURVE'}:
                continue
            evaluated=o.evaluated_get(graph)
            d=evaluated.to_mesh()
            if not d or not d.polygons:
                evaluated.to_mesh_clear()
                continue
            offset=len(verts)
            matmap={}
            for index,m in enumerate(d.materials):
                if m not in materials:
                    materials.append(m)
                matmap[index]=materials.index(m)
            verts.extend([tuple(evaluated.matrix_world@v.co) for v in d.vertices])
            source_uv=d.uv_layers.active
            for p in d.polygons:
                faces.append(tuple(offset+i for i in p.vertices))
                mi.append(matmap.get(p.material_index,0))
                sm.append(p.use_smooth)
                for li in p.loop_indices:
                    if source_uv:
                        uvs.append(tuple(source_uv.data[li].uv))
                    else:
                        v=d.vertices[d.loops[li].vertex_index].co
                        uvs.append((v.x*.2,v.z*.2))
            evaluated.to_mesh_clear()
        data=bpy.data.meshes.new('BlackOath_'+name)
        data.from_pydata(verts,[],faces)
        data.update()
        for m in materials:
            data.materials.append(m)
        data.polygons.foreach_set('material_index',mi)
        data.polygons.foreach_set('use_smooth',sm)
        layer=data.uv_layers.new(name='SurfaceUV')
        layer.data.foreach_set('uv',np.asarray(uvs,dtype=np.float32).ravel())
        data.calc_loop_triangles()
        triangle_count+=len(data.loop_triangles)
        o=bpy.data.objects.new('BlackOath_'+name,data)
        export_group.objects.link(o)
        exports.append(o)
        log('export collection ready: '+name)
    bpy.ops.object.select_all(action='DESELECT')
    for o in exports:
        o.select_set(True)
    bpy.context.view_layer.objects.active=exports[0]
    bpy.ops.export_scene.gltf(filepath=str(OUT/'BlackOath.glb'),export_format='GLB',use_selection=True,
                             export_apply=False,export_cameras=False,export_lights=False,
                             export_copyright=scene.get('asset_attribution',''))
    for o in exports:
        d=o.data
        bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.meshes.remove(d)
    bpy.data.collections.remove(export_group)
    return triangle_count
