"""Mesh helpers for the original-artwork Pokemon model collection. Front is -Y."""
import math
import bpy
import bmesh
from mathutils import Vector

COLLECTION = None
MATERIALS = {}
PATCH_LAYERS = {}


def material(hex_color, roughness=.47):
    key = (hex_color, roughness)
    if key not in MATERIALS:
        rgb = [int(hex_color.lstrip('#')[i:i+2], 16)/255 for i in (0, 2, 4)]
        rgb = [c/12.92 if c < .04045 else ((c+.055)/1.055)**2.4 for c in rgb]
        mat = bpy.data.materials.new('Surface_' + hex_color)
        mat.diffuse_color = (*rgb, 1)
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get('Principled BSDF')
        shader.inputs['Base Color'].default_value = (*rgb, 1)
        shader.inputs['Roughness'].default_value = roughness
        shader.inputs['Specular IOR Level'].default_value = .25
        MATERIALS[key] = mat
    return MATERIALS[key]


def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply(obj, modifier):
    active(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def finish(obj, name, color):
    obj.name = name
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    COLLECTION.objects.link(obj)
    obj.data.materials.clear()
    obj.data.materials.append(material(color))
    if obj.type == 'MESH':
        for p in obj.data.polygons:
            p.use_smooth = True
    return obj


def ell(name, center, scale, color, rot=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=center)
    obj = finish(bpy.context.object, name, color)
    obj.scale = scale
    if rot:
        obj.rotation_euler = [math.radians(a) for a in rot]
    active(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def mesh(name, vertices, faces, color):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    COLLECTION.objects.link(obj)
    finish(obj, name, color)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    return obj


def catmull(points, steps):
    p = [Vector(v) for v in points]
    out = []
    for i in range(len(p)-1):
        a,b,c,d = p[max(0,i-1)],p[i],p[i+1],p[min(len(p)-1,i+2)]
        for j in range(steps):
            t = j/steps
            out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return out + [p[-1]]


def tube(name, points, radii, color, sides=16, steps=5):
    assert len(points) == len(radii) >= 2
    path = catmull(points, steps)
    rr = catmull([(r,r,0) if isinstance(r,(int,float)) else (r[0],r[1],0) for r in radii], steps)
    vertices, faces = [], []
    previous = None
    for i,p in enumerate(path):
        t = (path[min(i+1,len(path)-1)]-path[max(i-1,0)]).normalized()
        if previous is None:
            ref = Vector((0,0,1)) if abs(t.z)<.93 else Vector((0,1,0))
            u = t.cross(ref).normalized()
        else:
            u = (previous-t*previous.dot(t)).normalized()
        v = t.cross(u).normalized()
        previous = u
        rx,ry = max(.004,rr[i].x),max(.004,rr[i].y)
        for j in range(sides):
            a = 2*math.pi*j/sides
            vertices.append(p+u*rx*math.cos(a)+v*ry*math.sin(a))
    for i in range(len(path)-1):
        for j in range(sides):
            a = i*sides+j
            b = i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    # Center fans avoid triangulating tiny, nearly-collinear cap polygons.
    start,end = len(vertices),len(vertices)+1
    vertices.extend([path[0],path[-1]])
    for j in range(sides):
        faces.append((start,(j+1)%sides,j))
        a = (len(path)-1)*sides
        faces.append((end,a+j,a+(j+1)%sides))
    return mesh(name,vertices,faces,color)


def cone(name, base, tip, radius, color):
    a,b = Vector(base),Vector(tip)
    return tube(name,[a,a.lerp(b,.5),b],[radius,radius*.58,.005],color,20,4)


def leaf(name, base, tip, width, color, bend=.15):
    a,b = Vector(base),Vector(tip)
    delta = Vector((0,-bend,0))
    path=catmull([a,a.lerp(b,.25)+delta*.5,a.lerp(b,.55)+delta,a.lerp(b,.82)+delta*.7,b],6)
    widths=catmull([(.012,.012,0),(width*.75,width*.15,0),(width,width*.20,0),(width*.55,width*.10,0),(.005,.005,0)],6)
    vertices,faces=[],[]
    sides=20
    for i,p in enumerate(path):
        t=(path[min(i+1,len(path)-1)]-path[max(i-1,0)]).normalized()
        ref=Vector((0,1,0)) if abs(t.y)<.96 else Vector((0,0,1))
        u=t.cross(ref).normalized();v=t.cross(u).normalized()
        for j in range(sides):
            theta=2*math.pi*j/sides
            vertices.append(p+u*max(.004,widths[i].x)*math.cos(theta)+v*max(.004,widths[i].y)*math.sin(theta))
    for i in range(len(path)-1):
        for j in range(sides):
            aa,bb=i*sides+j,i*sides+(j+1)%sides
            faces.append((aa,bb,bb+sides,aa+sides))
    start,end=len(vertices),len(vertices)+1;vertices.extend([path[0],path[-1]])
    for j in range(sides):
        faces.append((start,(j+1)%sides,j));k=(len(path)-1)*sides
        faces.append((end,k+j,k+(j+1)%sides))
    return mesh(name,vertices,faces,color)


def front(center, scale, x, z):
    cx,cy,cz = center
    rx,ry,rz = scale
    q = max(.018,1-((x-cx)/rx)**2-((z-cz)/rz)**2)
    return cy-ry*math.sqrt(q)


def patch(name, center, scale, xz, radius, color):
    x,z = xz
    rx,rz = radius
    n,rings = 48,8
    key=(COLLECTION.name,tuple(center),tuple(scale))
    layer=PATCH_LAYERS.get(key,0)
    PATCH_LAYERS[key]=layer+1
    depth=.010+layer*.003
    vertices = [(x,front(center,scale,x,z)-depth,z)]
    for ring in range(1,rings+1):
        r = ring/rings
        for j in range(n):
            a = 2*math.pi*j/n
            px,pz = x+rx*r*math.cos(a),z+rz*r*math.sin(a)
            vertices.append((px,front(center,scale,px,pz)-depth,pz))
    faces = [(0,1+j,1+(j+1)%n) for j in range(n)]
    for ring in range(rings-1):
        for j in range(n):
            a,b = 1+ring*n+j,1+ring*n+(j+1)%n
            faces.append((a,b,b+n,a+n))
    obj = mesh(name,vertices,faces,color)
    mod = obj.modifiers.new('Inset closed thickness','SOLIDIFY')
    mod.thickness=.022
    mod.offset=-1
    apply(obj,mod)
    return obj


def eye(name, center, scale, x, z, size=(.13,.2), iris='202D35', white=True):
    y = front(center,scale,x,z)-.035
    n = Vector(((x-center[0])/scale[0]**2,(y-center[1])/scale[1]**2,(z-center[2])/scale[2]**2)).normalized()
    q = Vector((0,-1,0)).rotation_difference(n)
    def layer(label, sx, sy, sz, offset, color, dx=0, dz=0):
        p = Vector((x,y,z))+n*offset+q@Vector((dx,0,dz))
        obj = ell(name+'_'+label,p,(sx,sy,sz),color)
        obj.rotation_euler=q.to_euler()
        return obj
    sx,sz=size
    if white:
        layer('white',sx,.016,sz,0,'FFF9E9')
        layer('iris',sx*.82,.013,sz*.85,.014,iris)
        layer('pupil',sx*.43,.009,sz*.68,.026,'152631')
    else:
        layer('black',sx,.020,sz,0,iris)
    layer('catchlight',sx*.24,.0065,sz*.17,.041 if white else .021,'FFFFFF',-sx*.18,sz*.38)


def smile(name, center, width, color='382E37'):
    x,y,z = center
    return tube(name,[(x-width/2,y+.035,z+.06),(x-width*.25,y,z+.012),(x,y-.01,z),(x+width*.25,y,z+.012),(x+width/2,y+.035,z+.06)], [.012]*5,color,10,3)


def union(name, objects, color, voxel=.045):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.object.join()
    obj=bpy.context.object
    mod=obj.modifiers.new('Fused organic form','REMESH'); mod.mode='VOXEL'; mod.voxel_size=voxel
    apply(obj,mod)
    mod=obj.modifiers.new('Sculpt polish','SMOOTH');mod.factor=.62;mod.iterations=4
    apply(obj,mod)
    mod=obj.modifiers.new('Smooth silhouette','SUBSURF');mod.levels=1
    apply(obj,mod)
    return finish(obj,name,color)
