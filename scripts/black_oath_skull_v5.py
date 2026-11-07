"""Anatomical pirate relic based on martinjario's CC BY 4.0 human skull.

Source geometry is preserved. Only orientation, uniform scale, island separation,
UV coordinates and surface materials are changed; gold is separate thin inlay.
"""
import math
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

SOURCE_URL='https://commons.wikimedia.org/wiki/File:3D-Sch%C3%A4del_eines_Menschen.stl'
SOURCE_PATH=Path(__file__).resolve().parents[1]/'assets/PirateShip/Source/Skull_v05/martinjario_skull.stl'


def build_skull(collection,center=(-29.2,0,9.37)):
    """Return only newly created SkullV5_* objects, facing -X, height 2.45m."""
    before=set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=str(SOURCE_PATH))
    source=bpy.context.object
    turn=Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Rotation(math.pi/2,4,'X')
    for v in source.data.vertices:v.co=turn@v.co
    points=[v.co for v in source.data.vertices]
    low=Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    scale=2.45/(high.z-low.z)
    for v in source.data.vertices:v.co=(v.co-(low+high)/2)*scale
    source.data.update()
    bpy.ops.object.select_all(action='DESELECT');source.select_set(True)
    bpy.context.view_layer.objects.active=source
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE');bpy.ops.object.mode_set(mode='OBJECT')
    bones=sorted((o for o in bpy.data.objects if o not in before),key=lambda o:-len(o.data.vertices))
    skull,jaw=bones[:2]
    skull.name='SkullV5_Cranium';jaw.name='SkullV5_Mandible'
    teeth=sorted(bones[2:],key=lambda o:(round(sum(v.co.z for v in o.data.vertices)/len(o.data.vertices),2),sum(v.co.y for v in o.data.vertices)/len(o.data.vertices)))
    for i,o in enumerate(teeth,1):o.name=f'SkullV5_Tooth_{i:02d}'
    made=[skull,jaw]+teeth
    for o in made:
        for c in list(o.users_collection):c.objects.unlink(o)
        collection.objects.link(o)
        o.location=Vector(center)
        o['figurehead_revision']=5
        o['source_asset']=SOURCE_URL
        o['source_author']='martinjario'
        o['source_license']='CC BY 4.0'
        o['source_modifications']='Uniform scale and orientation; separate original islands; new UV and relic materials. Anatomy unchanged.'
        for polygon in o.data.polygons:polygon.use_smooth=True
    bpy.ops.object.select_all(action='DESELECT')
    for o in made:o.select_set(True)
    bpy.context.view_layer.objects.active=skull
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.018,area_weight=.3)
    bpy.ops.object.mode_set(mode='OBJECT')

    def packed_image(name,rgb,noncolor=False):
        h,w=rgb.shape[:2]
        image=bpy.data.images.new(name,w,h,alpha=False)
        if noncolor:image.colorspace_settings.name='Non-Color'
        rgba=np.ones((h,w,4),dtype=np.float32);rgba[:,:,:3]=rgb
        image.pixels.foreach_set(rgba.ravel());image.pack()
        return image

    def material(name,base,metal,rough,seed):
        size=512;rng=np.random.default_rng(seed)
        fy,fx=np.meshgrid(np.fft.fftfreq(size),np.fft.fftfreq(size),indexing='ij')
        freq=fx*fx+fy*fy
        broad=np.fft.ifft2(np.fft.fft2(rng.standard_normal((size,size)))*np.exp(-freq*14000)).real
        broad=(broad-broad.mean())/broad.std()
        fine=rng.standard_normal((size,size))
        tone=np.clip(1+.17*broad+.025*fine,.52,1.48)
        rgb=np.array(base)[None,None,:]*tone[:,:,None]
        if 'Black' in name:
            patina=np.clip((broad-1.25)*.12,0,.18)[:,:,None]
            rgb=rgb*(1-patina)+np.array((.070,.078,.055))*patina
        base_image=packed_image(name+'_BaseColor',rgb.astype(np.float32))
        # Exportable tangent normal adds fine casting pores without losing anatomy.
        noise=np.fft.ifft2(np.fft.fft2(rng.standard_normal((size,size)))*np.exp(-freq*28)).real
        gy,gx=np.gradient(noise)
        normal=np.stack((-gx*.17,-gy*.17,np.ones_like(gx)),axis=2)
        normal/=np.linalg.norm(normal,axis=2,keepdims=True)
        normal_image=packed_image(name+'_Normal',((normal+1)/2).astype(np.float32),True)
        m=bpy.data.materials.new(name);m.diffuse_color=(*base,1);m.use_nodes=True
        p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
        tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=base_image
        m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
        tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=normal_image
        normal_node=m.node_tree.nodes.new('ShaderNodeNormalMap')
        m.node_tree.links.new(tex.outputs['Color'],normal_node.inputs['Color'])
        m.node_tree.links.new(normal_node.outputs['Normal'],p.inputs['Normal'])
        return m

    black=material('SkullV5_Blackened_Bronze',(.040,.043,.037),.48,.66,501)
    gold=material('SkullV5_Worn_Antique_Gold',(.34,.235,.075),.76,.49,502)
    ivory=material('SkullV5_Aged_Ivory',(.37,.315,.215),.05,.72,503)
    for o in made:
        o.data.materials.clear();o.data.materials.append(ivory if o in teeth else black)
    # Two old gilded teeth, selected spatially rather than changing dentition.
    for target in [Vector((-1.00,-.155,-.65)),Vector((-.83,.20,-.79))]:
        tooth=min(teeth,key=lambda o:(sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)-target).length)
        tooth.data.materials[0]=gold

    graph=BVHTree.FromObject(skull,bpy.context.evaluated_depsgraph_get())
    jaw_graph=BVHTree.FromObject(jaw,bpy.context.evaluated_depsgraph_get())
    def plate(name,outline,target=skull):
        """Closed, shallow plate projected pointwise onto the actual bone skin."""
        bm=bmesh.new();vs=[bm.verts.new((0,y,z)) for y,z in outline]
        bm.faces.new(vs);bmesh.ops.triangulate(bm,faces=list(bm.faces))
        for _ in range(4):
            bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=1,use_grid_fill=True)
            bmesh.ops.triangulate(bm,faces=list(bm.faces))
        bm.verts.ensure_lookup_table();bm.verts.index_update()
        faces=[tuple(v.index for v in f.verts) for f in bm.faces]
        edge_indices=[tuple(v.index for v in e.verts) for e in bm.edges if e.is_boundary]
        vertices=[];normals=[]
        bvh=jaw_graph if target==jaw else graph
        for v in bm.verts:
            hit,normal,_,_=bvh.ray_cast(Vector((-3,v.co.y,v.co.z)),Vector((1,0,0)),6)
            if hit is None:raise ValueError(f'Inlay {name} misses bone at {v.co.y},{v.co.z}')
            vertices.append(hit);normals.append(normal)
        bm.free()
        n=len(vertices)
        top=[p+normal*.0025 for p,normal in zip(vertices,normals)]
        bottom=[p-normal*.003 for p,normal in zip(vertices,normals)]
        closed=faces+[tuple(i+n for i in reversed(f)) for f in faces]
        closed += [(a,b,b+n,a+n) for a,b in edge_indices]
        data=bpy.data.meshes.new('SkullV5_'+name);data.from_pydata(top+bottom,[],closed);data.update()
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
        uv=data.uv_layers.new(name='InlayUV')
        for poly in data.polygons:
            poly.use_smooth=True
            for li in poly.loop_indices:
                p=data.vertices[data.loops[li].vertex_index].co
                uv.data[li].uv=(.5+p.y*.5,.5+p.z*.5)
        o=bpy.data.objects.new('SkullV5_'+name,data);collection.objects.link(o);o.location=Vector(center)
        data.materials.append(gold);o['figurehead_revision']=5;o['design']='New surface-following gilded relic inlay'
        made.append(o)
        return o

    # One connected, branching heraldic flame replaces the old separate wire curls.
    half=[(0,.34),(.045,.42),(.065,.55),(.25,.62),(.42,.75),(.48,.96),
          (.385,.865),(.33,.78),(.24,.725),(.14,.63),(.18,.80),(.24,1.045),
          (.14,.95),(.09,.82),(.065,.95),(0,1.13)]
    plate('Gold_Forehead_Flame',half+[(-y,z) for y,z in reversed(half[1:-1])])

    def strip(name,path,widths,target=skull):
        points=[Vector(p) for p in path];left=[];right=[]
        for i,(point,width) in enumerate(zip(points,widths)):
            tangent=(points[min(i+1,len(points)-1)]-points[max(i-1,0)]).normalized()
            side=Vector((-tangent.y,tangent.x))*width*.5
            left.append(tuple(point+side));right.append(tuple(point-side))
        return plate(name,left+list(reversed(right)),target)
    for side in [-1,1]:
        reflected=lambda path:[(side*y,z) for y,z in path]
        strip(f'Gold_Brow_{side}',reflected([(.12,.325),(.26,.37),(.42,.365),(.56,.30)]),[.005,.022,.025,.004])
        strip(f'Gold_Malar_{side}',reflected([(.69,-.18),(.61,-.255),(.48,-.285)]),[.004,.022,.005])
    strip('Gold_Chin_Keel',[(-.16,-1.13),(0,-1.17),(.16,-1.13)],[.004,.026,.004],jaw)
    return made


def validate_skull(objects):
    bpy.context.view_layer.update()
    report={'objects':len(objects),'triangles':0,'degenerate_triangles':0,'nonmanifold_edges':0,
            'inconsistent_winding':0,'missing_uv':[],'components':{},'bounds_min':[1e9]*3,'bounds_max':[-1e9]*3,
            'source_anatomy_vertices':sum(len(o.data.vertices) for o in objects if o.get('source_asset')),
            'source_anatomy_triangles':sum(len(o.data.polygons) for o in objects if o.get('source_asset'))}
    for o in objects:
        d=o.data;d.calc_loop_triangles();report['triangles']+=len(d.loop_triangles)
        report['degenerate_triangles']+=sum(t.area<1e-11 for t in d.loop_triangles)
        if not d.uv_layers:report['missing_uv'].append(o.name)
        bm=bmesh.new();bm.from_mesh(d)
        report['nonmanifold_edges']+=sum(not e.is_manifold for e in bm.edges)
        report['inconsistent_winding']+=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
        remaining=set(bm.verts);components=0
        while remaining:
            todo=[remaining.pop()];components+=1
            while todo:
                v=todo.pop()
                for e in v.link_edges:
                    other=e.other_vert(v)
                    if other in remaining:remaining.remove(other);todo.append(other)
        report['components'][o.name]=components;bm.free()
        for v in d.vertices:
            p=o.matrix_world@v.co
            for i in range(3):
                report['bounds_min'][i]=min(report['bounds_min'][i],p[i])
                report['bounds_max'][i]=max(report['bounds_max'][i],p[i])
    report['passed']=(not any(report[k] for k in ['degenerate_triangles','nonmanifold_edges','inconsistent_winding','missing_uv'])
                      and all(n==1 for n in report['components'].values()))
    return report
