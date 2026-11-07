"""Create an editable, posed Charizard fan model and studio renders.

Run with Blender --background --factory-startup --python-exit-code 1 --python.
Only assets/Charizard is written. No downloaded meshes or textures are used.
"""
import math
import struct
import zlib
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "Charizard"
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
asset = bpy.data.collections.new("Charizard")
scene.collection.children.link(asset)
studio = bpy.data.collections.new("90_Presentation")
scene.collection.children.link(studio)


def material(name, color, roughness=.42, emission=0):
    rgb = tuple(int(color[i:i+2], 16) / 255 for i in (0, 2, 4))
    linear = tuple(c / 12.92 if c < .04045 else ((c + .055) / 1.055)**2.4 for c in rgb)
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*linear, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*linear, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Specular IOR Level"].default_value = .32
    if emission:
        shader.inputs["Emission Color"].default_value = (*linear, 1)
        shader.inputs["Emission Strength"].default_value = emission
    return mat


orange = material("01 • Orange skin", "E88539")
cream = material("02 • Warm cream belly", "F5D995", .48)
teal = material("03 • Teal wing membrane", "228B9D", .46)
ivory = material("04 • Ivory claws and fangs", "FFF1D4", .29)
mouth_mat = material("05 • Mouth and nostrils", "42292C", .56)
white = material("06 • Eye whites", "FFFAE8", .25)
iris_mat = material("07 • Azure iris", "268FAB", .23)
pupil_mat = material("08 • Dark pupils", "102E3A", .24)
flame_red = material("09 • Flame orange", "FF6014", .37, .7)
flame_gold = material("10 • Flame gold", "FFB31F", .35, 1.3)
flame_core = material("11 • Flame heart", "FFF29A", .3, 2.0)
floor_mat = material("Studio • Midnight blue", "172733", .7)
plinth_mat = material("Studio • Slate", "293E4B", .43)
ring_mat = material("Studio • Copper rim", "BB733D", .3)

# Paint one UV eye image so the iris follows the eye surface without floating parts.
texture_dir=OUT/"Textures"
texture_dir.mkdir(exist_ok=True)
w,h=1024,512
vv,uu=np.mgrid[0:h,0:w]
eu=-.30+.58*uu/(w-1)
ev=.17-.30*vv/(h-1)
pixels=np.zeros((h,w,3),dtype=np.uint8);pixels[:]=(255,250,232)
distance=((eu+.07)/.067)**2+((ev+.005)/.103)**2
pixels[distance<1]=(23,103,131)
pixels[distance<.72]=(45,156,183)
pixels[((eu+.07)/.027)**2+((ev+.005)/.078)**2<1]=(13,39,52)
pixels[((eu+.090)/.013)**2+((ev-.040)/.023)**2<1]=(255,255,248)
def png_chunk(tag,data):
    return struct.pack(">I",len(data))+tag+data+struct.pack(">I",zlib.crc32(tag+data)&0xffffffff)
png=b"\x89PNG\r\n\x1a\n"+png_chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))
png+=png_chunk(b"IDAT",zlib.compress(b"".join(b"\0"+row.tobytes() for row in pixels)))+png_chunk(b"IEND",b"")
eye_path=texture_dir/"Charizard_eyes.png"
eye_path.write_bytes(png)
eye_image=bpy.data.images.load(str(eye_path));eye_image.pack()
eye_mat=material("06 • Painted eye", "FFFAE8",.32)
tex=eye_mat.node_tree.nodes.new("ShaderNodeTexImage");tex.image=eye_image
eye_mat.node_tree.links.new(tex.outputs["Color"],eye_mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"])


def move_collection(obj, collection=asset):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def finish(obj, name, mat, collection=asset):
    obj.name = name
    move_collection(obj, collection)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    if obj.type == "MESH":
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_modifier(obj, modifier):
    active(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def mesh(name, vertices, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    asset.objects.link(obj)
    finish(obj, name, mat)
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    return obj


def ellipsoid(name, center, scale, mat, segments=40, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=center)
    obj = finish(bpy.context.object, name, mat)
    obj.scale = scale
    active(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def catmull(points, steps=6):
    points = [Vector(p) for p in points]
    result = []
    for i in range(len(points)-1):
        p0, p1, p2, p3 = points[max(0, i-1)], points[i], points[i+1], points[min(len(points)-1, i+2)]
        for j in range(steps):
            t = j / steps
            result.append(.5 * ((2*p1) + (-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t*t + (-p0+3*p1-3*p2+p3)*t*t*t))
    result.append(points[-1])
    return result


def tube(name, points, radii, mat, sides=16, steps=6, underside=False):
    path = catmull(points, steps)
    radius = catmull([(r, 0, 0) if isinstance(r, (int, float)) else (r[0], r[1], 0) for r in radii], steps)
    vertices, faces = [], []
    previous_u = None
    for i, p in enumerate(path):
        tangent = (path[min(i+1, len(path)-1)]-path[max(0, i-1)]).normalized()
        if previous_u is None:
            ref = Vector((0, 0, 1)) if abs(tangent.z) < .93 else Vector((0, 1, 0))
            u = tangent.cross(ref).normalized()
        else:
            u = (previous_u-tangent*previous_u.dot(tangent)).normalized()
        previous_u = u
        v = tangent.cross(u).normalized()
        rx = max(.001, radius[i].x)
        ry = max(.001, radius[i].y) if radius[i].y > 0 else rx
        for j in range(sides):
            a = 2*math.pi*j/sides
            vertices.append(p + u*rx*math.cos(a) + v*ry*math.sin(a))
    for i in range(len(path)-1):
        for j in range(sides):
            faces.append((i*sides+j, i*sides+(j+1)%sides, (i+1)*sides+(j+1)%sides, (i+1)*sides+j))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((len(path)-1)*sides+j for j in range(sides)))
    obj = mesh(name, vertices, faces, mat)
    if underside:
        obj.data.materials.append(cream)
        for poly in obj.data.polygons:
            if poly.index < (len(path)-1)*sides and sides*.10 <= poly.index%sides <= sides*.39:
                poly.material_index = 1
    return obj


def union(name, objects, voxel=.045):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    remesh = obj.modifiers.new("Organic junctions", "REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = voxel
    remesh.use_smooth_shade = True
    apply_modifier(obj, remesh)
    smooth = obj.modifiers.new("Sculpt polish", "SMOOTH")
    smooth.factor = .65
    smooth.iterations = 5
    apply_modifier(obj, smooth)
    sub = obj.modifiers.new("Smooth skin", "SUBSURF")
    sub.levels = 1
    apply_modifier(obj, sub)
    finish(obj, name, orange)
    return obj


# Pear-shaped torso. Each ring is z, half-width, half-depth, center-y.
body_rings = [(.48,.13,.18,.13),(.64,.59,.47,.10),(.95,.89,.68,.07),
              (1.40,1.04,.81,.02),(1.88,.99,.79,0),(2.29,.82,.65,.01),
              (2.64,.59,.49,.04),(2.97,.44,.38,.08),(3.16,.30,.28,.09)]
body_samples = catmull(body_rings, 5)
vertices, faces = [], []
for z, rx, ry, cy in body_samples:
    for j in range(64):
        a = j*2*math.pi/64
        vertices.append((rx*math.sin(a),cy-ry*math.cos(a),z))
for i in range(len(body_samples)-1):
    for j in range(64):
        faces.append((i*64+j,i*64+(j+1)%64,(i+1)*64+(j+1)%64,(i+1)*64+j))
faces += [tuple(reversed(range(64))),tuple((len(body_samples)-1)*64+j for j in range(64))]
skin_parts = [mesh("Torso block", vertices, faces, orange)]
skin_parts.append(tube("Neck block", [(0,.10,2.70),(0,.13,3.22),(0,.03,3.80),(0,-.20,4.29),(0,-.40,4.53)], [.54,.405,.32,.33,.41],orange,24,8))
skin_parts.append(ellipsoid("Cranium block", (0,-.42,4.64),(.55,.64,.39),orange))
skin_parts.append(ellipsoid("Upper muzzle block", (0,-.99,4.55),(.45,.63,.225),orange))
skin_parts.append(ellipsoid("Nose bridge block", (0,-.85,4.71),(.33,.46,.22),orange))
for s in (-1, 1):
    skin_parts.append(tube("Horn block", [(s*.37,-.04,4.86),(s*.43,.30,4.96),(s*.48,.68,5.09),(s*.50,.91,5.12)], [.21,.16,.085,.008], orange,20))
    skin_parts.append(ellipsoid("Haunch block", (s*.81,.02,1.03),(.56,.57,.73),orange))
    skin_parts.append(tube("Ankle block", [(s*.91,-.07,1.05),(s*1.04,-.25,.60),(s*1.06,-.42,.29)], [.37,.29,.27],orange,20))
    skin_parts.append(ellipsoid("Foot block", (s*1.07,-.64,.24),(.40,.59,.235),orange))
    skin_parts.append(tube("Arm block", [(s*.48,.04,2.78),(s*.88,-.02,2.77),(s*1.25,-.16,2.50),(s*1.35,-.45,2.33)], [.29,.245,.20,.18],orange,20))
    skin_parts.append(ellipsoid("Palm block", (s*1.37,-.54,2.30),(.25,.20,.22),orange))
    for j in range(3):
        skin_parts.append(tube("Finger block", [(s*(1.17+j*.19),-.56,2.29),(s*(1.12+j*.25),-.72,2.12),(s*(1.08+j*.29),-.78,2.00-.045*(j==1))], [.098,.078,.058],orange,12))
body = union("01_Body • sculpted skin",skin_parts)
from mathutils.bvhtree import BVHTree
body_tree=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())


def body_surface(x,z):
    hit,_,_,_=body_tree.ray_cast(Vector((x,-5,z)),Vector((0,1,0)))
    assert hit is not None,(x,z)
    return hit.y-.012


# Cream patch follows the torso surface; thin closed shell keeps the border clean.
verts=[(0,body_surface(0,1.70),1.70)]
patch_faces=[]
for i in range(1,17):
    r=i/16
    for j in range(64):
        a=j*2*math.pi/64
        z=1.70+1.08*r*math.sin(a)
        x=.94*r*math.cos(a)*(1-.15*(z-1.7))
        verts.append((x,body_surface(x,z),z))
for j in range(64):
    patch_faces.append((0,1+j,1+(j+1)%64))
for i in range(15):
    for j in range(64):
        a=1+i*64+j;b=1+i*64+(j+1)%64
        patch_faces.append((a,b,b+64,a+64))
belly=mesh("02_Belly • cream inset",verts,patch_faces,cream)
solid=belly.modifiers.new("Inset thickness","SOLIDIFY");solid.thickness=.055;solid.offset=-1
apply_modifier(belly,solid)
sub=belly.modifiers.new("Soft belly edge","SUBSURF");sub.levels=1
apply_modifier(belly,sub)

# Mouth, gently lowered jaw, side smiles, nostrils and four small teeth.
ellipsoid("03_Mouth • dark opening",(0,-.95,4.365),(.395,.47,.052),mouth_mat)
ellipsoid("03_Jaw",(0,-.89,4.285),(.415,.61,.13),orange)
for s in (-1,1):
    for x,y,z,r in [(s*.31,-1.28,4.43,.062),(s*.365,-.82,4.40,.046)]:
        tube("03_Fang",[(x,y,z),(x,y-.015,z-.09),(x-s*.013,y-.025,z-.155)],[r,r*.65,.003],ivory,16,4)


def eye_patch(name,center,normal,u,outline,mat,bulge=.018):
    center,normal,u=Vector(center),Vector(normal).normalized(),Vector(u).normalized()
    v=normal.cross(u).normalized()
    if v.z<0:v=-v
    def conform(point,offset):
        hit,_,_,_=body_tree.ray_cast(point+normal*.7,-normal)
        return hit+normal*offset if hit is not None else point
    center=conform(center,.015)
    vertices=[center+normal*bulge]
    outline=catmull([(*p,0) for p in outline+[outline[0]]],5)[:-1]
    for p in outline:
        vertices.append(conform(center+u*p.x+v*p.y,.013))
    faces=[(0,j+1,(j+1)%len(outline)+1) for j in range(len(outline))]
    obj=mesh(name,vertices,faces,mat)
    uv=obj.data.uv_layers.new(name="Eye UV")
    coords=[(0,0)]+[(p.x,p.y) for p in outline]
    for loop in obj.data.loops:
        x,y=coords[loop.vertex_index]
        uv.data[loop.index].uv=((x+.30)/.58,(y+.13)/.30)
    solid=obj.modifiers.new("Eye shell","SOLIDIFY");solid.thickness=.018
    apply_modifier(obj,solid)
    return obj,center,normal,u,v


for s in (-1,1):
    normal=Vector((s*.83,-.54,.13)).normalized()
    u=Vector((s*.54,.83,0)).normalized()
    center=Vector((s*.468,-.66,4.795))
    outline=[(-.26,.015),(-.10,.065),(.19,.105),(.235,.025),(.17,-.085),(-.07,-.075)]
    eye,center,normal,u,v=eye_patch("04_Eye",center,normal,u,outline,eye_mat)
    brow_points=[]
    for a,b in [(-.29,.045),(-.09,.10),(.14,.14),(.25,.10)]:
        point=center+u*a+v*b
        hit,_,_,_=body_tree.ray_cast(point+normal*.7,-normal)
        brow_points.append(hit+normal*.015 if hit is not None else point)
    tube("04_Brow ridge",brow_points,[.055,.063,.062,.025],orange,14,5)
    outline=[(.030*math.cos(a*math.pi/4),.055*math.sin(a*math.pi/4)) for a in range(8)]
    eye_patch("03_Nostril",(s*.247,-1.42,4.705),(s*.20,-.62,.75),(1,0,0),outline,mouth_mat,.002)

for s in (-1,1):
    for j in range(3):
        x=s*(.82+j*.245)
        y=-1.02-(.07 if j==1 else 0)
        tube("05_Foot claw",[(x,y,.24),(x,y-.18,.16),(x,y-.32,.09)],[.112,.078,.004],ivory,20,5)
        x=s*(1.08+j*.29)
        z=2.01-.045*(j==1)
        tube("05_Hand claw",[(x,-.78,z),(x,-.84,z-.08),(x-s*.014,-.90,z-.10)],[.060,.040,.003],ivory,16,5)

tail=tube("06_Tail • curled",[(0,.15,1.10),(.32,.95,.86),(1.14,1.56,.57),(2.01,1.30,.57),(2.66,.72,.94),(3.02,.12,1.49),(3.11,-.10,1.95)], [.50,.44,.32,.235,.17,.11,.065],orange,32,10,True)


def bezier(a,b,c,d,steps=12):
    a,b,c,d=map(Vector,(a,b,c,d))
    return [(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d for t in [i/steps for i in range(steps)]]


def curve(a,b,c,d,t):
    return (1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d


for s in (-1,1):
    def p(x,y,z):return Vector((s*x,y,z))
    root=p(.40,.25,2.76); elbow=p(1.72,.61,4.66)
    corner=p(3.22,.54,3.91);outer=p(3.68,.48,1.96);middle=p(2.10,.58,2.37)
    boundary=[]
    boundary+=bezier(root,p(.92,.58,3.23),p(1.19,.60,4.13),elbow)
    boundary+=bezier(elbow,p(2.17,.62,4.48),p(2.75,.58,4.05),corner)
    boundary+=bezier(corner,p(3.57,.53,3.41),p(3.71,.49,2.58),outer)
    boundary+=bezier(outer,p(3.30,.58,3.11),p(2.65,.61,3.23),middle)
    boundary+=bezier(middle,p(1.73,.62,3.05),p(1.03,.57,3.15),root)
    def outer_edge(t):
        if t<=.5:return curve(elbow,p(2.17,.62,4.48),p(2.75,.58,4.05),corner,t*2)
        return curve(corner,p(3.57,.53,3.41),p(3.71,.49,2.58),outer,(t-.5)*2)
    def middle_edge(t):return curve(elbow,p(1.98,.55,4.12),p(2.15,.54,3.17),middle,t)
    def root_edge(t):return curve(elbow,p(1.19,.60,4.13),p(.92,.58,3.23),root,t)
    def outer_bottom(t):return curve(outer,p(3.30,.58,3.11),p(2.65,.61,3.23),middle,t)
    def inner_bottom(t):return curve(middle,p(1.73,.62,3.05),p(1.03,.57,3.15),root,t)
    for panel,(edge_a,edge_b,bottom) in enumerate([(outer_edge,middle_edge,outer_bottom),(middle_edge,root_edge,inner_bottom)]):
        vertices=[elbow]
        n=32
        for row in range(1,n+1):
            t=row/n
            for col in range(n+1):
                u=col/n
                q=elbow.lerp(bottom(u),t)+(1-u)*(edge_a(t)-elbow.lerp(edge_a(1),t))+u*(edge_b(t)-elbow.lerp(edge_b(1),t))
                q.y+=.055*math.sin(math.pi*u)*math.sin(math.pi*t)
                vertices.append(q)
        faces=[(0,1+j,2+j) for j in range(n)]
        for row in range(n-1):
            for col in range(n):
                a=1+row*(n+1)+col
                faces.append((a,a+1,a+n+2,a+n+1))
        wing=mesh("07_Wing membrane "+("L" if s<0 else "R")+str(panel),vertices,faces,teal)
        solid=wing.modifiers.new("Membrane thickness","SOLIDIFY");solid.thickness=.045
        apply_modifier(wing,solid)
        sub=wing.modifiers.new("Membrane smoothness","SUBSURF");sub.levels=1
        apply_modifier(wing,sub)
    edge=boundary[:13]
    tube("07_Wing arm",edge,[.19-.07*i/(len(edge)-1) for i in range(len(edge))],orange,20,2)
    edge=boundary[12:37]
    tube("07_Leading wing finger",edge,[.135-.12*i/(len(edge)-1) for i in range(len(edge))],orange,18,2)
    tube("07_Middle wing finger",[middle_edge(i/24) for i in range(25)],[.085-.075*i/24 for i in range(25)],orange,16,2)
    tube("07_Wing thumb",[elbow,p(1.65,.60,4.90),p(1.61,.59,5.02)],[.105,.073,.006],orange,16)
    for edge in (boundary[36:48]+[middle],boundary[48:]+[root]):
        tube("07_Trailing wing edge",edge,[.028]*len(edge),orange,10,2)


# Three sculpted, nested flame layers plus side tongues, all actual meshes.
def flame(name,center,height,width,mat,lean=.18):
    x,y,z=center
    obj=tube(name,[(x,y,z),(x-.08*width,y,z+height*.25),(x+.10*width,y,z+height*.53),(x+lean*.5,y,z+height*.79),(x+lean,y,z+height)],
             [(.18*width,.16*width),(.50*width,.31*width),(.36*width,.24*width),(.19*width,.13*width),(.002,.002)],mat,24,8)
    return obj

flame("08_Flame outer",(3.11,-.09,1.91),1.22,.73,flame_red,.14)
flame("08_Flame fork left",(2.98,-.10,2.05),.77,.42,flame_red,-.36)
flame("08_Flame fork right",(3.28,-.09,2.10),.70,.40,flame_red,.30)
flame("08_Flame golden center",(3.11,-.285,1.94),.93,.53,flame_gold,.09)
flame("08_Flame golden fork",(2.99,-.255,2.04),.62,.27,flame_gold,-.21)
flame("08_Flame bright heart",(3.11,-.423,1.97),.59,.31,flame_core,.055)
flame("08_Flame rear gold",(3.11,.105,1.94),.93,.53,flame_gold,.09)
flame("08_Flame rear fork",(2.99,.075,2.04),.62,.27,flame_gold,-.21)
flame("08_Flame rear heart",(3.11,.243,1.97),.59,.31,flame_core,.055)

# Model dimensions are scaled from sculpt units to roughly 1.7 m head height.
SCALE=.32
for obj in list(asset.objects):
    obj.location*=SCALE
    obj.scale*=SCALE
    active(obj)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    obj["asset"]="Charizard fan model"
    obj["part"]=obj.name

# Presentation stays separate from the GLB.
bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=1.14,depth=.075,location=(0,0,-.045))
plinth=finish(bpy.context.object,"Display plinth",plinth_mat,studio)
bevel=plinth.modifiers.new("Rounded display edge","BEVEL");bevel.width=.028;bevel.segments=3
apply_modifier(plinth,bevel)
bpy.ops.mesh.primitive_torus_add(major_segments=128,minor_segments=12,location=(0,0,-.031),major_radius=1.135,minor_radius=.006)
finish(bpy.context.object,"Copper display ring",ring_mat,studio)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.087))
finish(bpy.context.object,"Studio floor",floor_mat,studio)


def light(name,position,energy,color,size,target=(0,0,.9)):
    data=bpy.data.lights.new(name,"AREA")
    obj=bpy.data.objects.new(name,data);studio.objects.link(obj)
    obj.location=position;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()
    data.energy=energy;data.color=color;data.shape="DISK";data.size=size


light("Key • warm softbox",(-3.5,-4.5,6),650,(1,.86,.70),4.0)
light("Fill • cool softbox",(4,-2.8,3.6),450,(.69,.85,1),3)
light("Rim • wings",(0,3.3,4.8),950,(.79,.90,1),3)
data=bpy.data.lights.new("Tail flame glow","POINT")
obj=bpy.data.objects.new("Tail flame glow",data);studio.objects.link(obj)
obj.location=(.995,-.04,.78);data.energy=5;data.color=(1,.22,.02);data.shadow_soft_size=.15
world=scene.world or bpy.data.worlds.new("Studio world");scene.world=world;world.use_nodes=True
world.node_tree.nodes.get("Background").inputs["Color"].default_value=(.18,.23,.30,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value=.4
camera_data=bpy.data.cameras.new("Camera")
camera=bpy.data.objects.new("Camera",camera_data);studio.objects.link(camera)
scene.camera=camera;camera.data.type="ORTHO"


def view(position,target,ortho):
    camera.location=position
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.data.ortho_scale=ortho


scene.render.engine="CYCLES"
scene.cycles.samples=48
scene.cycles.use_denoising=True
try:
    pref=bpy.context.preferences.addons["cycles"].preferences
    pref.compute_device_type="OPTIX";pref.get_devices()
    if any(d.type=="OPTIX" for d in pref.devices):
        for device in pref.devices:device.use=device.type=="OPTIX"
        scene.cycles.device="GPU"
except (KeyError,TypeError,RuntimeError):
    pass
scene.view_settings.view_transform="AgX"
scene.render.resolution_x=1500;scene.render.resolution_y=1500
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.film_transparent=False
scene.unit_settings.system="METRIC"
scene.unit_settings.scale_length=1
view((3.0,-6.7,2.65),(0,0,.86),2.95)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=="VIEW_3D":
            space=area.spaces.active
            space.region_3d.view_distance=3.6
            space.region_3d.view_location=(0,0,.85)
            space.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
            space.clip_end=300
            space.shading.type="MATERIAL"
            space.overlay.show_extras=False
            space.overlay.show_floor=False

active(body)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Charizard.blend"))
bpy.ops.object.select_all(action="DESELECT")
for obj in asset.objects:obj.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.gltf(filepath=str(OUT/"Charizard.glb"),export_format="GLB",use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False)

import sys
if "--draft" in sys.argv:
    scene.cycles.samples=20;scene.render.resolution_percentage=55
    scene.render.filepath=str(OUT/"Charizard_draft.png")
    bpy.ops.render.render(write_still=True)
else:
    for name,position,target,ortho in [
        ("Charizard_preview",(3.0,-6.7,2.65),(0,0,.86),2.95),
        ("Charizard_front",(0,-7,2.3),(0,0,.85),2.95),
        ("Charizard_back",(3,6.7,2.75),(0,0,.85),2.95),
        ("Charizard_face",(2.7,-5.7,2.45),(0,-.20,1.40),.95)]:
        view(position,target,ortho)
        scene.render.filepath=str(OUT/(name+".png"))
        bpy.ops.render.render(write_still=True)
    clay=material("Studio • Clay","A7B7C0",.65)
    scene.view_layers[0].material_override=clay
    view((3,-6.7,2.65),(0,0,.86),2.95)
    scene.render.filepath=str(OUT/"Charizard_clay.png")
    bpy.ops.render.render(write_still=True)
print("CHARIZARD_BUILD_OK",flush=True)
