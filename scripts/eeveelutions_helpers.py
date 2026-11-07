"""Independent Blender modelling and review helpers for the popular Pokemon set.

All geometry is authored here. Official illustrations are reference only.
Coordinates: front -Y, up +Z. This module does not modify earlier assets.
"""
import math
import json
import hashlib
import struct
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
COL = None
STUDIO = None
OUT = None
NAME = None
MATS = {}


def material(hexcolor, roughness=.53):
    key = (hexcolor, roughness)
    if key in MATS:
        return MATS[key]
    rgb = [int(hexcolor[i:i+2], 16)/255 for i in (0, 2, 4)]
    rgb = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    mat = bpy.data.materials.new('Color_' + hexcolor)
    mat.diffuse_color = (*rgb, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*rgb, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Specular IOR Level'].default_value = .24
    MATS[key] = mat
    return mat


def setup(name):
    global COL, STUDIO, OUT, NAME
    NAME = name
    OUT = ROOT/'assets'/'PokemonPopular'/name
    (OUT/'renders').mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear()
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    COL = bpy.data.collections.new('Pokemon_' + name)
    STUDIO = bpy.data.collections.new('90_Presentation')
    scene.collection.children.link(COL)
    scene.collection.children.link(STUDIO)
    return OUT


def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply(obj, modifier):
    active(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def finish(obj, name, color, col=None):
    obj.name = name
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    (col or COL).objects.link(obj)
    obj.data.materials.clear()
    obj.data.materials.append(material(color))
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def ell(name, pos, scale, color, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=40, location=pos)
    o = finish(bpy.context.object, name, color)
    o.scale = scale
    o.rotation_euler = [math.radians(a) for a in rot]
    active(o)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return o


def mesh(name, vertices, faces, color):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    COL.objects.link(obj)
    finish(obj, name, color)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    return obj


def catmull(points, steps=10):
    pts = [Vector(p) for p in points]
    out = []
    for i in range(len(pts)-1):
        a, b, c, d = pts[max(0,i-1)], pts[i], pts[i+1], pts[min(len(pts)-1,i+2)]
        for j in range(steps):
            t = j/steps
            out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return out + [pts[-1]]


def tube(name, points, sizes, color, sides=40, steps=10, width_axis=(1,0,0), bands=None):
    """Smooth swept elliptical cross section; optional flush material bands."""
    path = catmull(points, steps)
    rr = catmull([(v,v,0) if isinstance(v,(int,float)) else (*v,0) for v in sizes], steps)
    verts, faces, ts = [], [], []
    for i, p in enumerate(path):
        tangent = (path[min(i+1,len(path)-1)]-path[max(i-1,0)]).normalized()
        u = Vector(width_axis)
        u = u - tangent*u.dot(tangent)
        if u.length < .1:
            u = tangent.cross(Vector((0,1,0)))
        u.normalize()
        v = tangent.cross(u).normalized()
        for j in range(sides):
            a = j*2*math.pi/sides
            verts.append(p+u*max(.002,rr[i].x)*math.cos(a)+v*max(.002,rr[i].y)*math.sin(a))
    for i in range(len(path)-1):
        for j in range(sides):
            a=i*sides+j; b=i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides));ts.append((i+.5)/(len(path)-1))
    start, end = len(verts), len(verts)+1
    verts.extend([path[0],path[-1]])
    for j in range(sides):
        faces.append((start,(j+1)%sides,j));ts.append(0)
        k=(len(path)-1)*sides
        faces.append((end,k+j,k+(j+1)%sides));ts.append(1)
    obj=mesh(name,verts,faces,color)
    if bands:
        for low,high,col in bands:
            obj.data.materials.append(material(col))
            idx=len(obj.data.materials)-1
            for poly,t in zip(obj.data.polygons,ts):
                if low <= t <= high:poly.material_index=idx
    return obj


def union(name, objects, color, voxel=.021):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.join()
    obj=bpy.context.object
    mod=obj.modifiers.new('Sculpt joined anatomy','REMESH');mod.mode='VOXEL';mod.voxel_size=voxel
    apply(obj,mod)
    mod=obj.modifiers.new('Organic surface polish','SMOOTH');mod.factor=.58;mod.iterations=12
    apply(obj,mod)
    mod=obj.modifiers.new('Final smooth silhouette','SUBSURF');mod.levels=1
    apply(obj,mod)
    return finish(obj,name,color)


def circle(cx,cz,rx,rz,angle=0,n=96):
    a=math.radians(angle)
    return [(cx+rx*math.cos(t)*math.cos(a)-rz*math.sin(t)*math.sin(a),
             cz+rx*math.cos(t)*math.sin(a)+rz*math.sin(t)*math.cos(a))
            for t in [2*math.pi*j/n for j in range(n)]]


def paint(name, target, outline, color, plane='front', side=1, depth=.006, hole=None, rings=10):
    """Closed thin marking, projected onto actual sculpt, including oval rings."""
    graph=bpy.context.evaluated_depsgraph_get()
    bpy.context.view_layer.update()
    bv=BVHTree.FromObject(target,graph)
    inv=target.matrix_world.inverted()
    mat=target.matrix_world
    def surface(a,b):
        if plane=='front':origin=Vector((a,-8,b));direction=Vector((0,1,0))
        elif plane=='side':origin=Vector((side*8,a,b));direction=Vector((-side,0,0))
        else:origin=Vector((a,8,b));direction=Vector((0,-1,0))
        p,normal,_,_=bv.ray_cast(inv@origin,inv.to_3x3()@direction,20)
        if p is None:
            raise ValueError(name+' marking misses anatomy at '+str((a,b)))
        normal=(mat.to_3x3()@normal).normalized()
        return mat@p+normal*depth
    n=len(outline)
    verts=[];faces=[]
    if hole:
        assert len(hole)==n
        for k in range(rings+1):
            f=k/rings
            for outer,inner in zip(outline,hole):
                a=inner[0]+(outer[0]-inner[0])*f;b=inner[1]+(outer[1]-inner[1])*f
                verts.append(surface(a,b))
        for k in range(rings):
            for j in range(n):
                a=k*n+j;b=k*n+(j+1)%n
                faces.append((a,b,b+n,a+n))
    else:
        cx=sum(p[0] for p in outline)/n;cz=sum(p[1] for p in outline)/n
        verts.append(surface(cx,cz))
        for k in range(1,rings+1):
            f=k/rings
            for a,b in outline:verts.append(surface(cx+(a-cx)*f,cz+(b-cz)*f))
        faces=[(0,1+j,1+(j+1)%n) for j in range(n)]
        for k in range(rings-1):
            for j in range(n):
                a=1+k*n+j;b=1+k*n+(j+1)%n
                faces.append((a,b,b+n,a+n))
    obj=mesh(name,verts,faces,color)
    mod=obj.modifiers.new('Closed inlaid marking','SOLIDIFY');mod.thickness=.009;mod.offset=-1
    apply(obj,mod)
    return obj


def line(name,points,color='1F252E',radius=.008):
    return tube(name,points,[radius]*len(points),color,sides=12,steps=5)


def add_uvs(obj):
    """Stable surface UVs for editable colour-only meshes and future painting."""
    if obj.type!='MESH' or obj.data.uv_layers:return
    layer=obj.data.uv_layers.new(name='SurfaceUV')
    coords=np.array([v.co[:] for v in obj.data.vertices])
    lo=coords.min(axis=0);size=np.maximum(coords.max(axis=0)-lo,1e-5)
    for face in obj.data.polygons:
        axis=max(range(3),key=lambda a:abs(face.normal[a]))
        dims=[a for a in range(3) if a!=axis]
        for index in face.loop_indices:
            p=coords[obj.data.loops[index].vertex_index]
            layer.data[index].uv=((p[dims[0]]-lo[dims[0]])/size[dims[0]],(p[dims[1]]-lo[dims[1]])/size[dims[1]])


def bounds(objects):
    graph=bpy.context.evaluated_depsgraph_get()
    coords=[]
    for o in objects:
        ev=o.evaluated_get(graph);me=ev.to_mesh()
        coords.extend(ev.matrix_world@v.co for v in me.vertices)
        ev.to_mesh_clear()
    lo=Vector(tuple(min(p[i] for p in coords) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in coords) for i in range(3)))
    return lo,hi


def stage():
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True
    scene.cycles.device='CPU';scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=1000;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    world=bpy.data.worlds.new('Soft neutral studio');scene.world=world;world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.34,.40,.47,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.30 if NAME=='Sylveon' else .35 if NAME=='Dragonite' else .5
    bpy.ops.mesh.primitive_plane_add(size=200)
    floor=finish(bpy.context.object,'Studio floor','BDCCD5' if NAME=='Sylveon' else 'D5DFE1',STUDIO)
    floor.location.z=-.005
    def light(name,pos,power,size,color):
        d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color
        o=bpy.data.objects.new(name,d);STUDIO.objects.link(o);o.location=pos
        o.rotation_euler=(Vector((0,0,1.2))-o.location).to_track_quat('-Z','Y').to_euler()
    light('Large softbox',(-3,-4,6),350 if NAME=='Sylveon' else 400 if NAME=='Dragonite' else 500,4,(1,.94,.87))
    light('Face fill',(4,-2,3),170 if NAME=='Sylveon' else 200 if NAME=='Dragonite' else 300,3,(.84,.93,1))
    light('Upper edge',(1,4,5),450 if NAME=='Sylveon' else 550 if NAME=='Dragonite' else 700,3,(.93,.97,1))
    d=bpy.data.cameras.new('Review camera');o=bpy.data.objects.new('Review camera',d);STUDIO.objects.link(o)
    d.type='ORTHO';scene.camera=o
    scene.unit_settings.system='METRIC'
    camera('hero')


def camera(view):
    objs=[o for o in COL.objects if o.type=='MESH']
    lo,hi=bounds(objs);target=(lo+hi)/2
    target.z=(lo.z+hi.z)/2
    positions={'hero':(4,-7,3.2),'front':(0,-8,1.8),'back':(0,8,2.8),'side':(8,0,2.3),'clay':(4,-7,3.2)}
    o=bpy.context.scene.camera;o.location=Vector(positions[view])+Vector((0,0,target.z-1.3))
    o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
    o.data.ortho_scale=max(hi.z-lo.z,(hi.y-lo.y)*.93,hi.x-lo.x)*1.29


def render(views=('hero','front','back','clay'),draft=False):
    scene=bpy.context.scene
    scene.cycles.samples=20 if draft else 64
    scene.render.resolution_percentage=64 if draft else 100
    for view in views:
        camera(view)
        scene.view_layers[0].material_override=material('A2AEB6',.65) if view=='clay' else None
        scene.render.filepath=str(OUT/'renders'/((view+'_draft' if draft else view)+'.png'))
        bpy.ops.render.render(write_still=True)
        print('EEVEELUTIONS_RENDER '+NAME+' '+view,flush=True)
    scene.view_layers[0].material_override=None
    camera('hero')


def save_export():
    objects=[o for o in COL.objects if o.type=='MESH']
    for o in objects:add_uvs(o)
    lo,hi=bounds(objects)
    for o in objects:o.location.z-=lo.z
    root=bpy.data.objects.new('root_'+NAME,None);COL.objects.link(root)
    root['source']='Hand-authored fan model based on official Pokemon illustration'
    root['front_axis']='-Y';root['units']='Metres; display scale rather than canonical height'
    for o in objects:o.parent=root
    bpy.ops.object.select_all(action='DESELECT')
    for o in COL.objects:o.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.gltf(filepath=str(OUT/(NAME+'.glb')),export_format='GLB',use_selection=True,
        export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True)
    bpy.ops.object.select_all(action='DESELECT')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_location=(0,0,1.4)
                area.spaces.active.region_3d.view_distance=6
                area.spaces.active.region_3d.view_rotation=bpy.context.scene.camera.rotation_euler.to_quaternion()
                area.spaces.active.shading.type='MATERIAL'
                area.spaces.active.overlay.show_extras=False
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(NAME+'.blend')),compress=True)


def inspect(objects,weld_export_seams=False):
    graph=bpy.context.evaluated_depsgraph_get();report={'objects':len(objects),'triangles':0,'nonfinite':0,'nonfinite_uv':0,'degenerate':0,'nonmanifold_edges':0,'inconsistent_edges':0,'missing_uv':[],'materials':set(),'image_textures':{},'details':[]}
    low=np.full(3,np.inf);high=np.full(3,-np.inf)
    for obj in objects:
        ev=obj.evaluated_get(graph);me=ev.to_mesh()
        vertices=np.array([ev.matrix_world@v.co for v in me.vertices]);me.calc_loop_triangles()
        low=np.minimum(low,vertices.min(axis=0));high=np.maximum(high,vertices.max(axis=0))
        report['nonfinite']+=int((~np.isfinite(vertices)).sum())
        tri=np.array([t.vertices[:] for t in me.loop_triangles]);p=vertices[tri]
        area=np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)*.5
        bad=int((area<1e-12).sum());report['degenerate']+=bad;report['triangles']+=len(tri)
        bm=bmesh.new();bm.from_mesh(me)
        if weld_export_seams:
            bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
        nm=sum(not e.is_manifold for e in bm.edges);iw=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
        report['nonmanifold_edges']+=nm;report['inconsistent_edges']+=iw;bm.free()
        if not me.uv_layers:report['missing_uv'].append(obj.name)
        for layer in me.uv_layers:
            data=np.empty(len(layer.data)*2,dtype=np.float32);layer.data.foreach_get('uv',data)
            report['nonfinite_uv']+=int((~np.isfinite(data)).sum())
        report['materials'].update(m.name for m in me.materials if m)
        for mat in me.materials:
            if mat and mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type=='TEX_IMAGE' and node.image:
                        image=node.image
                        report['image_textures'][image.name]={'size':list(image.size),'packed':bool(image.packed_file)}
        if bad or nm or iw:report['details'].append({'object':obj.name,'degenerate':bad,'nonmanifold':nm,'inconsistent':iw})
        ev.to_mesh_clear()
    report['bounds']={'min':low.tolist(),'max':high.tolist(),'size':(high-low).tolist()}
    report['materials']=sorted(report['materials'])
    return report


def validate():
    global COL
    bpy.ops.wm.open_mainfile(filepath=str(OUT/(NAME+'.blend')))
    COL=bpy.data.collections['Pokemon_'+NAME]
    source=inspect([o for o in COL.objects if o.type=='MESH'])
    # Scene is discarded only after the editable file has been saved.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(OUT/(NAME+'.glb')))
    imported=inspect([o for o in bpy.context.scene.objects if o.type=='MESH'],weld_export_seams=True)
    diff=max(abs(a-b) for key in ('min','max') for a,b in zip(source['bounds'][key],imported['bounds'][key]))
    errors=[]
    for label,data in [('source',source),('glb',imported)]:
        for field in ('nonfinite','nonfinite_uv','degenerate','nonmanifold_edges','inconsistent_edges'):
            if data[field]:errors.append(label+': '+field)
        if data['missing_uv']:errors.append(label+': missing UV')
    if source['triangles']!=imported['triangles']:errors.append('triangle count mismatch')
    if diff>1e-5:errors.append('bounds mismatch')
    if any(o.type in ('LIGHT','CAMERA') for o in bpy.context.scene.objects):errors.append('presentation leaked')
    blob=(OUT/(NAME+'.glb')).read_bytes();json_length=struct.unpack_from('<I',blob,12)[0]
    gltf=json.loads(blob[20:20+json_length].decode('utf-8'))
    embedded=all('bufferView' in item or item.get('uri','').startswith('data:') for item in gltf.get('images',[]))
    if not embedded:errors.append('external GLB texture dependency')
    if any(not image['packed'] for image in source['image_textures'].values()):errors.append('unpacked source texture')
    report={'passed':not errors,'errors':errors,'source':source,'glb':imported,'bounds_max_error_m':diff,
            'glb_topology_note':'GLB material/UV seam splits welded at 1e-6 m only for topology inspection',
            'saved_blend_reopened':True,
            'glb_textures_embedded':embedded,
            'sha256':{extension:hashlib.sha256((OUT/(NAME+'.'+extension)).read_bytes()).hexdigest() for extension in ('blend','glb')},
            'limitations':['Static model; no rig or animation','Separate closed overlapping parts; not a single printable volume','No game-engine runtime verification']}
    (OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('EEVEELUTIONS_VALIDATION '+NAME+' '+str(report['passed'])+' '+str(errors),flush=True)
    return report
