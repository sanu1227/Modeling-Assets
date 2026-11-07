"""Refine Cheongun with sculptural twin dragons, black lacquer and warm gold.

Run with the workspace Blender: --background --factory-startup --python this_file
Only assets/Weapons/AzureDragon_v2 is written. Dimensions are in metres.
"""
import hashlib
import json
import math
import struct
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "Weapons" / "AzureDragon_v2"
original_files = [ROOT / "assets" / "Weapons" / "Blackthorn" / filename
                  for filename in ("Blackthorn.blend", "Blackthorn_game.glb", "Blackthorn_game.fbx")]
original_files.append(ROOT / "scripts" / "build_blackthorn.py")
original_files.extend(ROOT / "assets" / "Weapons" / "Aurelia" / filename
                      for filename in ("Aurelia.blend", "Aurelia_game.glb", "Aurelia_game.fbx"))
original_files.append(ROOT / "scripts" / "build_aurelia.py")
original_files.extend(ROOT / "assets" / "Weapons" / "Aurelia_v2" / filename
                      for filename in ("Aurelia_v2.blend", "Aurelia_v2_game.glb", "Aurelia_v2_game.fbx"))
original_files.append(ROOT / "scripts" / "build_aurelia_v2.py")
original_files.extend(ROOT / "assets" / "Weapons" / "AzureDragon" / filename
                      for filename in ("AzureDragon.blend", "AzureDragon_game.glb", "AzureDragon_game.fbx"))
original_files.append(ROOT / "scripts" / "build_azure_dragon.py")
original_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in original_files}
TEX = OUT / "Textures"
TEX.mkdir(parents=True, exist_ok=True)
validation_path = OUT / "AzureDragon_v2_validation.json"
if validation_path.exists():
    validation_path.unlink()
scratch = OUT / ".export_temp"
scratch.mkdir(exist_ok=True)
tempfile.tempdir = str(scratch)
bpy.context.preferences.filepaths.temporary_directory = str(scratch)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0
asset_collection = bpy.context.collection
asset_collection.name = "AzureDragon_v2 - game mesh"
parts = []
rng = np.random.default_rng(7319)


def smooth_noise(n, width):
    noise = rng.normal(size=(n, n))
    f = np.fft.fftfreq(n)
    kernel = np.exp(-(f[:, None] ** 2 + f[None, :] ** 2) * width ** 2)
    result = np.fft.ifft2(np.fft.fft2(noise) * kernel).real
    return (result / max(result.std(), 1e-6)).astype(np.float32)


def save_image(name, rgb, color=False):
    height, width = rgb.shape[:2]
    image = bpy.data.images.new(name, width=width, height=height, alpha=False)
    image.colorspace_settings.name = "sRGB" if color else "Non-Color"
    rgba = np.ones((height, width, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(rgb, 0, 1)
    image.pixels.foreach_set(rgba.ravel())
    image.filepath_raw = str(TEX / (name + ".png"))
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image


# Four 2048-pixel surface regions retain fine grain in close-up renders.
n = 2048
v, u = np.mgrid[:n, :n].astype(np.float32) / n
base = np.zeros((n * 2, n * 2, 3), np.float32)
rough = np.zeros_like(base)
metal = np.zeros_like(base)
normal = np.zeros_like(base)
for tile, (rgb, roughness, metallic) in enumerate([
    ((0.57, 0.63, 0.67), 0.28, 1.0),
    ((0.024, 0.025, 0.027), 0.31, 0.40),
    ((0.40, 0.005, 0.015), 0.43, 0.0),
    ((0.76, 0.58, 0.295), 0.30, 1.0),
]):
    cloud = smooth_noise(n, 420 if tile == 1 else 80)
    fine = smooth_noise(n, 2.5)
    grain = smooth_noise(n, 7)
    scratches = np.zeros((n, n), np.float32)
    for _ in range(420 if tile != 2 else 120):
        x = int(rng.integers(3, n - 3))
        start = int(rng.integers(0, n - 90))
        length = int(rng.integers(25, min(350, n - start)))
        scratches[start:start + length, x:x + 1] += rng.uniform(0.1, 0.6)
    if tile == 1:
        variation = 1+cloud*.025+fine*.008
        height = fine*.0005
        local_rough = roughness+cloud*.009
    elif tile == 2:
        pores = np.maximum(-grain - 0.65, 0)
        variation = 1 + cloud * 0.06 + fine * 0.045 - pores * 0.11
        height = fine * 0.006 + grain * 0.018 - pores * 0.013
        local_rough = roughness + cloud * 0.025 + pores * 0.06
    elif tile == 3:
        variation = 1 + cloud * .008 + fine * .003
        height = fine * .00015 - scratches * .001
        local_rough = roughness + cloud * .006 + scratches * .035
    else:
        brushed = np.sin(u * math.tau * 360 + np.sin(v * 13) * 0.18)
        variation = 1 + cloud * 0.025 + fine * 0.009 + scratches * 0.09
        height = fine * 0.0003 + brushed * 0.00015 - scratches * 0.002
        local_rough = roughness + cloud * 0.008 + brushed * 0.005 + scratches * 0.05
    dy, dx = np.gradient(height)
    vectors = np.stack((-dx * 7, -dy * 7, np.ones_like(dx)), axis=2)
    vectors /= np.linalg.norm(vectors, axis=2, keepdims=True)
    y, x = (tile // 2) * n, (tile % 2) * n
    block = np.s_[y:y+n, x:x+n]
    base[block] = np.array(rgb) * variation[:, :, None]
    rough[block] = np.clip(local_rough[:, :, None], 0.18, 0.9)
    metal[block] = metallic
    normal[block] = vectors * 0.5 + 0.5

images = {
    "BaseColor": save_image("AzureDragon_v2_BaseColor", base, True),
    "Roughness": save_image("AzureDragon_v2_Roughness", rough),
    "Metallic": save_image("AzureDragon_v2_Metallic", metal),
    "Normal": save_image("AzureDragon_v2_Normal", normal),
}
material = bpy.data.materials.new("M_AzureDragon_v2_PBR_4K")
material.use_nodes = True
nodes, links = material.node_tree.nodes, material.node_tree.links
bsdf = nodes.get("Principled BSDF")
for index, (channel, image) in enumerate(images.items()):
    tex = nodes.new("ShaderNodeTexImage")
    tex.name = channel
    tex.label = channel
    tex.image = image
    tex.location = (-650, 360 - index * 240)
    if channel == "Normal":
        mapping = nodes.new("ShaderNodeNormalMap")
        mapping.location = (-280, -300)
        links.new(tex.outputs["Color"], mapping.inputs["Color"])
        links.new(mapping.outputs["Normal"], bsdf.inputs["Normal"])
    else:
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color" if channel == "BaseColor" else channel])

def active(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def finish(obj, name, tile, bevel=0, smooth=False):
    obj.name = name
    active(obj)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("Small machined edge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    # Recalculate every closed component before assigning UVs and export normals.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    uv = obj.data.uv_layers.active or obj.data.uv_layers.new(name="UVMap")
    coords = np.array([tuple(vertex.co) for vertex in obj.data.vertices])
    low, span = coords.min(axis=0), np.maximum(np.ptp(coords, axis=0), 1e-7)
    for poly in obj.data.polygons:
        axis = max(range(3), key=lambda a: abs(poly.normal[a]))
        axes = [a for a in range(3) if a != axis]
        if 2 in axes:
            axes = [a for a in axes if a != 2] + [2]
        for loop in poly.loop_indices:
            co = obj.data.vertices[obj.data.loops[loop].vertex_index].co
            uu = (co[axes[0]] - low[axes[0]]) / span[axes[0]]
            vv = (co[axes[1]] - low[axes[1]]) / span[axes[1]]
            uv.data[loop].uv = ((tile % 2) * .5 + .012 + uu * .476,
                                (tile // 2) * .5 + .012 + vv * .476)
        poly.use_smooth = smooth
    if smooth:
        modifier = obj.modifiers.new("Weighted surface normals", "WEIGHTED_NORMAL")
        modifier.keep_sharp = True
        modifier.weight = 35
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.materials.clear()
    obj.data.materials.append(material)
    group = obj.vertex_groups.new(name=name)
    group.add(list(range(len(obj.data.vertices))), 1, "REPLACE")
    parts.append(obj)
    return obj


def mesh(name, vertices, faces, tile, bevel=0, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    asset_collection.objects.link(obj)
    return finish(obj, name, tile, bevel, smooth)


def rings_mesh(name, rings, tile, bevel=0, smooth=False):
    count = len(rings[0])
    vertices = [point for ring in rings for point in ring]
    faces = [tuple(reversed(range(count)))]
    for row in range(len(rings)-1):
        for j in range(count):
            a, b = row*count+j, row*count+(j+1)%count
            faces.append((a, b, b+count, a+count))
    faces.append(tuple(range((len(rings)-1)*count, len(rings)*count)))
    return mesh(name, vertices, faces, tile, bevel, smooth)


def oval(name, levels, tile, sides=16, bevel=0, smooth=False):
    rings = [[(rx*math.cos(math.tau*j/sides), ry*math.sin(math.tau*j/sides), z)
              for j in range(sides)] for z, rx, ry in levels]
    return rings_mesh(name, rings, tile, bevel, smooth)


def plaque(name, outline, depth, tile, center_y=0, bevel=.0006):
    rings = [[(x, center_y + sign*depth/2, z) for x, z in outline] for sign in (-1, 1)]
    return rings_mesh(name, rings, tile, bevel, True)


def tube(name, points, radius, tile, sides=6):
    points = [Vector(p) for p in points]
    cyclic = (points[0]-points[-1]).length < 1e-7
    if cyclic:
        points.pop()
    rings = []
    for i, point in enumerate(points):
        before = points[(i-1)%len(points)] if cyclic else points[max(0,i-1)]
        after = points[(i+1)%len(points)] if cyclic else points[min(i+1,len(points)-1)]
        tangent = (after-before).normalized()
        axis = Vector((0, 1, 0))
        if abs(tangent.dot(axis)) > .95:
            axis = Vector((1, 0, 0))
        right = tangent.cross(axis).normalized()
        up = tangent.cross(right).normalized()
        rings.append([point + radius*(right*math.cos(j*math.tau/sides) + up*math.sin(j*math.tau/sides))
                      for j in range(sides)])
    if cyclic:
        vertices = [p for ring in rings for p in ring]
        faces = []
        for i in range(len(rings)):
            next_i = (i+1)%len(rings)
            for j in range(sides):
                faces.append((i*sides+j,i*sides+(j+1)%sides,
                              next_i*sides+(j+1)%sides,next_i*sides+j))
        return mesh(name,vertices,faces,tile,smooth=True)
    return rings_mesh(name, rings, tile, smooth=True)


# A narrow straight double-edged blade with a raised central ridge.
profile=[(-1,.035),(-.76,.48),(-.33,.82),(-.10,1),(0,1.06),
         (.10,1),(.33,.82),(.76,.48),(1,.035)]
key_sections=[(.006,.026,.0043,0),(.070,.026,.0043,0),(.12,.025,.0041,0),
              (.43,.0225,.0036,0),(.65,.0195,.0030,0),(.75,.0135,.0022,0),
              (.813,.0055,.0011,0)]
sections=[]
for first,second in zip(key_sections,key_sections[1:]):
    for t in (0,.33,.66):
        sections.append(tuple(a+(b-a)*t for a,b in zip(first,second)))
sections.append(key_sections[-1])
rings=[]
for z,width,thickness,_ in sections:
    front=[(x*width,-d*thickness,z) for x,d in profile]
    rings.append(front+[(x,-y,z) for x,y,z in reversed(front)])
count=len(rings[0])
vertices=[p for ring in rings for p in ring]
root_center=len(vertices)
vertices.append((0,0,.006))
faces=[(root_center,(j+1)%count,j) for j in range(count)]
for i in range(len(rings)-1):
    for j in range(count):
        faces.append((i*count+j,i*count+(j+1)%count,(i+1)*count+(j+1)%count,(i+1)*count+j))
tip=len(vertices)
vertices.append((0,0,.846))
for j in range(count):
    faces.append(((len(rings)-1)*count+j,(len(rings)-1)*count+(j+1)%count,tip))
blade=mesh("Blade_Cheongun_double_edge",vertices,faces,0)
for polygon in blade.data.polygons:
    polygon.use_smooth=polygon.index>=count
for edge in blade.data.edges:
    a,b=edge.vertices
    edge.use_edge_sharp=a<root_center and b<root_center and a//count!=b//count

# Smooth sampled curves keep the small filigree organic without subdivision.
def bezier(points, samples=18):
    a,b,c,d = [Vector(p) for p in points]
    return [(1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*d
            for t in np.linspace(0,1,samples)]


def jade_inset(name,x,z,rx,rz,y,side,tile=1):
    rings=[]
    depth=min(rx,rz)*.30
    for height,scale in ((0,.97),(.2,1),(.60,.85),(.90,.55),(1,.15)):
        rings.append([(x+rx*scale*math.cos(t),side*(y+height*depth),
                       z+rz*scale*math.sin(t)) for t in np.linspace(0,math.tau,32,endpoint=False)])
    return rings_mesh(name,rings,tile,smooth=True)


def leaf(name, x, z, length, width, angle, y, side):
    rings=[]
    for t in np.linspace(0,1,8):
        spread=(.035+.965*math.sin(math.pi*t)**.75)*width*.5
        height=(.06+.94*math.sin(math.pi*t))*min(width*.19,.0016)
        zz=(t-.5)*length
        bend=width*.12*math.sin(math.pi*t)
        section=[(-1,0),(-.6,.62),(0,1),(.6,.62),(1,0),(.6,-.12),(0,-.18),(-.6,-.12)]
        rings.append([(x+(xx*spread+bend)*math.cos(angle)-zz*math.sin(angle),
                       side*(y+yy*height),
                       z+(xx*spread+bend)*math.sin(angle)+zz*math.cos(angle)) for xx,yy in section])
    return rings_mesh(name,rings,3,smooth=True)


# Twenty triangles per bead keep hundreds of milgrain dots inexpensive.
bead_bm=bmesh.new()
bmesh.ops.create_icosphere(bead_bm,subdivisions=1,radius=1)
bead_bm.verts.ensure_lookup_table()
bead_bm.verts.index_update()
bead_vertices=[tuple(v.co) for v in bead_bm.verts]
bead_faces=[tuple(v.index for v in f.verts) for f in bead_bm.faces]
bead_bm.free()


def beads(name,points,radius,tile=3):
    vertices=[]
    faces=[]
    for p in points:
        start=len(vertices)
        vertices.extend([(p[0]+x*radius,p[1]+y*radius,p[2]+z*radius) for x,y,z in bead_vertices])
        faces.extend([tuple(start+i for i in face) for face in bead_faces])
    return mesh(name,vertices,faces,tile,smooth=True)


def outline_points(outline,spacing):
    result=[]
    for a,b in zip(outline,outline[1:]+outline[:1]):
        length=math.hypot(b[0]-a[0],b[1]-a[1])
        count=max(1,round(length/spacing))
        result.extend([(a[0]+(b[0]-a[0])*t/count,a[1]+(b[1]-a[1])*t/count) for t in range(count)])
    return result


def rosette(name,x,z,radius,y,side):
    for j in range(6):
        angle=j*math.tau/6
        leaf(name+"_petal",x+math.sin(angle)*radius*.46,z+math.cos(angle)*radius*.46,
             radius*.86,radius*.37,-angle,y,side)
    beads(name+"_heart",[(x,side*(y+.0005),z)],radius*.20)


def blade_surface(x,z):
    width=np.interp(z,[s[0] for s in sections],[s[1] for s in sections])
    thickness=np.interp(z,[s[0] for s in sections],[s[2] for s in sections])
    xx=x/width
    depth=np.interp(xx,[p[0] for p in profile],[p[1] for p in profile])
    return depth*thickness


def blade_line(name,points,side,radius=.00028,tile=3):
    return tube(name,[(x,side*(blade_surface(x,z)+radius*.7),z) for x,z in points],radius,tile,5)


def cloud_points(x,z,scale=1,hand=1):
    segments=[[(0,0),(-.008,-.003),(-.017,.001),(-.015,.008)],
              [(-.015,.008),(-.014,.015),(-.008,.016),(-.006,.011)],
              [(-.006,.011),(-.009,.024),(.009,.024),(.006,.011)],
              [(.006,.011),(.009,.017),(.018,.012),(.015,.006)],
              [(.015,.006),(.011,-.002),(.006,.008),(.010,.010)]]
    points=[]
    for segment in segments:
        sampled=bezier([(x+hand*px*scale,0,z+pz*scale) for px,pz in segment],12)
        points.extend([(p[0],p[2]) for p in sampled[:-1]])
    p=sampled[-1]
    points.append((p[0],p[2]))
    return points


def face_line(name,points,y,side,radius=.0005,tile=3):
    return tube(name,[(x,side*y,z) for x,z in points],radius,tile,6)


def key_pattern(x,z,width,height):
    return [(x-width*.5,z-height*.5),(x+width*.5,z-height*.5),
            (x+width*.5,z+height*.5),(x-width*.3,z+height*.5),
            (x-width*.3,z-height*.15),(x+width*.18,z-height*.15),
            (x+width*.18,z+height*.15)]


def ellipsoid(name, centre, radii, tile):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=centre)
    obj=bpy.context.object
    obj.scale=radii
    return finish(obj,name,tile,smooth=True)


def tapered(name, controls, start_radius, end_radius, tile=3, samples=24, sides=10):
    points=[Vector(p) for p in bezier(controls,samples)]
    rings=[]
    for i,point in enumerate(points):
        tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        right=tangent.cross(Vector((0,1,0))).normalized()
        up=tangent.cross(right).normalized()
        radius=end_radius+(start_radius-end_radius)*(1-i/(len(points)-1))**.8
        rings.append([point+radius*(right*math.cos(t)+up*math.sin(t))
                      for t in np.linspace(0,math.tau,sides,endpoint=False)])
    return rings_mesh(name,rings,tile,smooth=True)


# Compact dark structural core, covered by rounded paired dragon necks.
core=[(-.037,.004),(0,.009),(.037,.004),(.035,-.019),(0,-.034),(-.035,-.019)]
plaque("Guard_black_structural_core",core,.022,1,bevel=.0018)
for hand in (-1,1):
    neck=[]
    for t in np.linspace(0,1,18):
        x=hand*(.020+.074*t)
        z=-.008+.020*t
        ry=.0125+.004*math.sin(math.pi*t)
        rz=.017-.003*t
        neck.append([(x,ry*math.cos(a),z+rz*math.sin(a))
                     for a in np.linspace(0,math.tau,20,endpoint=False)])
    rings_mesh("Guard_dragon_black_neck",neck,1,smooth=True)
    for side in (-1,1):
        for column in range(7):
            t=(column+.4)/7.5
            x=hand*(.022+.069*t)
            mid=-.008+.020*t
            ry=.0125+.004*math.sin(math.pi*t)
            rz=.017-.003*t
            for row in (-1,0,1):
                dz=row*.008
                y=ry*math.sqrt(max(.1,1-(dz/rz)**2))
                leaf("Guard_overlapping_dragon_scale",x+hand*(.002 if row else 0),
                     mid+dz,.014,.008,-hand*1.10,y,side)
        for j in range(4):
            leaf("Guard_dragon_mane",hand*(.064+j*.006),.020+j*.003,
                 .023,.009,hand*(.65+j*.14),.010,side)
    ellipsoid("Guard_dragon_sculpted_skull",(hand*.099,0,.016),(.025,.014,.015),3)
    ellipsoid("Guard_dragon_upper_muzzle",(hand*.123,0,.007),(.019,.010,.007),3)
    ellipsoid("Guard_dragon_dark_mouth",(hand*.125,0,-.001),(.014,.008,.0025),1)
    tapered("Guard_dragon_lower_jaw",[(hand*.094,0,.002),(hand*.110,0,-.008),
            (hand*.134,0,-.010),(hand*.140,0,-.003)],.0055,.0017,samples=22)
    for side in (-1,1):
        jade_inset("Guard_dragon_eye_socket",hand*.108,.018,.005,.0028,.0133,side,1)
        jade_inset("Guard_dragon_crimson_eye",hand*.109,.018,.0028,.00125,.0145,side,2)
        face_line("Guard_dragon_eye_slit",[(hand*.109,.0172),(hand*.109,.0188)],.0151,
                  side,.00024,1)
        tapered("Guard_dragon_brow",[(hand*.090,side*.010,.025),(hand*.101,side*.016,.027),
                (hand*.114,side*.016,.021),(hand*.123,side*.007,.014)],.0030,.0006)
        for j in range(3):
            leaf("Guard_dragon_cheek_armour",hand*(.089+j*.006),.012-j*.003,
                 .018,.007,-hand*.83,.0133,side)
        tapered("Guard_dragon_nasal_ridge",[(hand*.111,side*.005,.021),(hand*.119,side*.008,.020),
                (hand*.131,side*.007,.016),(hand*.139,side*.003,.012)],.0021,.0005)
        jade_inset("Guard_dragon_nostril",hand*.135,.010,.0024,.0017,.008,side,1)
        for x,z in ((.119,.001),(.132,.001)):
            tapered("Guard_dragon_fang",[(hand*x,side*.009,z),(hand*(x+.0006),side*.010,z-.003),
                    (hand*(x-.001),side*.009,z-.006),(hand*(x-.002),side*.008,z-.007)],
                    .0015,.0003,samples=10,sides=8)
        tapered("Guard_dragon_antler",[(hand*.083,side*.007,.029),(hand*.106,side*.012,.073),
                (hand*.057,side*.014,.091),(hand*.042,side*.014,.063)],.0046,.00055)
        tapered("Guard_dragon_antler_branch",[(hand*.087,side*.010,.061),(hand*.070,side*.014,.079),
                (hand*.063,side*.014,.099),(hand*.040,side*.014,.088)],.0025,.0004)
        tapered("Guard_dragon_whisker",[(hand*.135,side*.010,.007),(hand*.172,side*.013,-.017),
                (hand*.130,side*.017,-.055),(hand*.103,side*.016,-.029)],.0018,.0004,
                samples=36,sides=8)
        tapered("Guard_dragon_short_whisker",[(hand*.131,side*.010,.006),(hand*.159,side*.012,.014),
                (hand*.166,side*.012,-.014),(hand*.148,side*.012,-.022)],.0012,.0003,
                samples=24,sides=8)
        for x,z,scale in ((.052,-.043,1.02),(.081,-.031,.64)):
            face_line("Guard_openwork_ruyi_cloud",cloud_points(hand*x,z,scale,hand),.012,side,.0012)
        ridge=bezier([(hand*.023,side*.013,-.027),(hand*.045,side*.014,-.034),
                       (hand*.070,side*.014,-.020),(hand*.089,side*.014,-.015)],24)
        tube("Guard_cloud_lower_frame",ridge,.0014,3,8)
        beads("Guard_cloud_granulation",ridge[::2],.0006)

# Black enamel medallion with double gold rims and a small red accent.
for side in (-1,1):
    jade_inset("Guard_black_central_medallion",0,-.009,.024,.026,.015,side,1)
    for rx,rz,y,r in ((.0245,.0265,.016,.0011),(.0215,.0235,.021,.0005)):
        face_line("Guard_medallion_gold_rim",[(rx*math.cos(a),-.009+rz*math.sin(a))
                   for a in np.linspace(0,math.tau,73)],y,side,r)
    beads("Guard_medallion_milgrain",[(.0257*math.cos(a),side*.016,-.009+.0277*math.sin(a))
          for a in np.linspace(0,math.tau,48,endpoint=False)],.00055)
    face_line("Guard_medallion_ruyi_relief",cloud_points(0,-.021,.88),.023,side,.00085)
    jade_inset("Guard_crimson_central_seal",0,.007,.0038,.0048,.024,side,2)

# Black blade collar lets the gold engraving read as a fine border.
collar=[(-.027,.005),(-.027,.049),(.027,.049),(.027,.005)]
plaque("Guard_black_blade_collar",collar,.011,1,bevel=.0007)
for side in (-1,1):
    face_line("Guard_collar_gold_border",collar+[collar[0]],.0062,side,.0007)
    for x in (-.018,-.006,.006,.018):
        face_line("Guard_collar_thunder_key",key_pattern(x,.030,.008,.014),.0064,side,.00042)
    for z in (.011,.043):
        face_line("Guard_collar_edge_inlay",[(-.025,z),(.025,z)],.0063,side,.00036)

# Twin cloud bands and a restrained spine ornament follow the steel surface.
for side in (-1,1):
    for j in range(4):
        blade_line("Blade_auspicious_cloud",cloud_points(0,.082+j*.065,.95-j*.10),side,.00032)
    for hand in (-1,1):
        blade_line("Blade_gold_spine_frame",[(hand*(.007*(1-t)),.31+.34*t)
                   for t in np.linspace(0,1,48)],side,.00028)
        for j in range(8):
            z=.34+j*.031
            points=[(hand*(.002+.0018*math.sin(t)),z+.009*math.cos(t))
                    for t in np.linspace(-math.pi*.5,math.pi*.5,14)]
            blade_line("Blade_dragon_scale_arc",points,side,.00020)
    blade_line("Blade_top_cloud",cloud_points(0,.65,.40),side,.00025)

# Black lacquer handle with gold lozenges and fretwork collars.
oval("Grip_black_lacquer",[(-.190,.0145,.0115),(-.174,.016,.0125),
     (-.120,.0178,.0135),(-.070,.0182,.014),(-.030,.0175,.0138)],1,32,smooth=True)
for z,rx,ry in ((-.033,.019,.0153),(-.189,.0164,.0135)):
    oval("Grip_gold_ferrule",[(z-.009,rx,ry),(z+.009,rx,ry)],3,32,.0006,True)
    oval("Grip_black_ferrule_inset",[(z-.0045,rx+.00015,ry+.00015),
          (z+.0045,rx+.00015,ry+.00015)],1,32,.0002,True)
    for zz in (z-.007,z+.007):
        oval("Grip_beaded_gold_edge",[(zz-.00065,rx+.0007,ry+.0007),
              (zz+.00065,rx+.0007,ry+.0007)],3,32,.0002,True)
        beads("Grip_gold_granulation",[((rx+.0008)*math.cos(t),(ry+.0008)*math.sin(t),zz)
              for t in np.linspace(0,math.tau,44,endpoint=False)],.00048)
    for side in (-1,1):
        for x in (-.009,0,.009):
            face_line("Grip_fretwork",key_pattern(x,z,.006,.006),ry+.0009,side,.00032)
for side in (-1,1):
    for j in range(3):
        z=-.066-j*.041
        points=[]
        for a,b in zip([(0,z+.021),(.012,z),(0,z-.021),(-.012,z)],
                       [(.012,z),(0,z-.021),(-.012,z),(0,z+.021)]):
            for t in np.linspace(0,1,12,endpoint=False):
                x=a[0]+(b[0]-a[0])*t
                zz=a[1]+(b[1]-a[1])*t
                ry=np.interp(zz,[-.19,-.12,-.07,-.03],[.0115,.0135,.014,.0138])
                rx=np.interp(zz,[-.19,-.12,-.07,-.03],[.0145,.0178,.0182,.0175])
                points.append((x,side*(ry*math.sqrt(max(.01,1-(x/rx)**2))+.0005),zz))
        points.append(points[0])
        tube("Grip_gold_lattice",points,.00048,3,5)
        jade_inset("Grip_black_lozenge",0,z,.006,.011,.0141,side)
        face_line("Grip_lozenge_cloud",cloud_points(0,z-.006,.24),.0165,side,.00027)

# A black bi-shaped ring pommel has a true central opening for the red cord.
pommel_z=-.226
segments=64
cross=[(.009,-.006),(.011,-.009),(.024,-.009),(.028,-.005),
       (.028,.005),(.024,.009),(.011,.009),(.009,.006)]
vertices=[(radius*math.cos(t),y,pommel_z+radius*math.sin(t))
          for t in np.linspace(0,math.tau,segments,endpoint=False) for radius,y in cross]
faces=[]
for i in range(segments):
    for j in range(len(cross)):
        faces.append((i*8+j,i*8+(j+1)%8,((i+1)%segments)*8+(j+1)%8,((i+1)%segments)*8+j))
mesh("Pommel_open_black_bi",vertices,faces,1,smooth=True)
oval("Pommel_gold_neck",[(-.207,.013,.010),(-.195,.014,.011)],3,24,.0007,True)
for side in (-1,1):
    for radius in (.0105,.0255):
        face_line("Pommel_gold_ring_bezel",[(radius*math.cos(t),pommel_z+radius*math.sin(t))
                  for t in np.linspace(0,math.tau,65)],.0098,side,.0011)
    beads("Pommel_granulated_rim",[(.026*math.cos(t),side*.0105,pommel_z+.026*math.sin(t))
          for t in np.linspace(0,math.tau,56,endpoint=False)],.0005)
    for j in range(4):
        angle=j*math.tau/4
        points=key_pattern(0,0,.010,.006)
        points=[(.018*math.cos(angle)+x*math.cos(angle)-z*math.sin(angle),
                 pommel_z+.018*math.sin(angle)+x*math.sin(angle)+z*math.cos(angle)) for x,z in points]
        face_line("Pommel_four_thunder_keys",points,.0107,side,.00048)

# Woven crimson knot and two distinct hanging silk bundles, kept in named groups.
tube("Tassel_attachment_loop",[(.010*math.sin(t),.006*math.cos(t),-.239-.013*math.cos(t))
     for t in np.linspace(0,math.tau,49)],.00125,2,8)
tube("Tassel_main_cord",bezier([(0,-.004,-.250),(.008,-.006,-.288),
     (.045,-.006,-.277),(.045,-.006,-.307)],40),.0014,2,8)
knot=[(.045+.014*math.sin(2*t),-.006+.0018*math.cos(5*t),-.306+.014*math.sin(3*t))
      for t in np.linspace(0,math.tau,145)]
tube("Tassel_woven_endless_knot",knot,.0014,2,8)
beads("Tassel_knot_gold_bead",[(.045,-.006,-.327)],.004,3)
for index,(x,z) in enumerate(((.055,-.360),(.105,-.345))):
    tube(f"Tassel_split_cord_{index}",bezier([(.045,-.006,-.322),
         (.050+index*.025,-.006,-.337),(x,-.004,z+.024),(x,-.004,z+.010)],28),.0011,2,8)
    cap=oval(f"Tassel_cap_gold_{index}",[(z-.004,.008,.006),(z+.003,.008,.006),
             (z+.012,.0045,.004),(z+.015,.002,.002)],3,24,.0004,True)
    cap.location.x=x
    cap.location.y=-.004
    for offset in (-.002,.002):
        binding=oval(f"Tassel_cap_red_binding_{index}",[(z+offset-.0007,.0082,.0062),
                     (z+offset+.0007,.0082,.0062)],2,24,.0002,True)
        binding.location.x=x
        binding.location.y=-.004
    for strand in range(40):
        angle=strand*math.tau/40
        length=.132+rng.uniform(-.010,.010)
        path=[]
        for t in np.linspace(0,1,17):
            radius=.0045+.006*t
            path.append((x+math.cos(angle)*radius+.008*t*t+.0014*math.sin(t*8+angle)*t,
                         -.004+math.sin(angle)*radius*.65+.001*math.sin(t*11+angle),
                         z-.003-length*t))
        tube(f"Tassel_silk_strands_{index}",path,.00052,2,5)
    for j in range(5):
        angle=j*math.tau/5
        tube(f"Tassel_gold_thread_{index}",[(x+(.0048+.006*t)*math.cos(angle)+.008*t*t,
             -.004+(.0048+.006*t)*math.sin(angle)*.65,z-.004-.127*t)
             for t in np.linspace(0,1,17)],.00016,3,5)

# One game mesh and one shared PBR atlas, with separately named tassel groups.
active(blade)
for obj in parts:
    obj.select_set(True)
bpy.ops.object.join()
sword = bpy.context.object
sword.name = "SM_AzureDragon_v2_Jian"
for vertex in sword.data.vertices:
    vertex.co.z += .105
scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
sword["asset_name"] = "Cheongun v2 / 청운검 - Black Gold Twin Dragons"
sword["palette"] = "Black lacquer, warm gold, silver steel, crimson tassels"
sword["pivot"] = "Grip centre; blade points along local +Z; front is -Y"
sword["units"] = "metres"
sword["textures"] = "4096px PBR atlas; OpenGL tangent-space normal (+Y)"
sword["tassel_note"] = "Static silk ornament; Tassel vertex groups isolate it for later rigging"
sword["uv_note"] = "Intentional overlapping surface UVs; no unique lightmap UV"
sword["collision_hint"] = "Use engine weapon trace/capsule, not concave render mesh"
sword.modifiers.new("Stable game triangulation", "TRIANGULATE")
sword.data.calc_loop_triangles()

preview = bpy.data.collections.new("Studio - excluded from game exports")
scene.collection.children.link(preview)


def studio(obj):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    preview.objects.link(obj)


def light(name, location, target, power, color, width, height):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.color = power * .18, color
    data.shape, data.size, data.size_y = "RECTANGLE", width, height
    obj = bpy.data.objects.new(name, data)
    preview.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z", "Y").to_euler()


world = scene.world or bpy.data.worlds.new("Studio world")
scene.world = world
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs["Color"].default_value = (.11,.14,.19,1)
world.node_tree.nodes.get("Background").inputs["Strength"].default_value = .28
light("Tall warm softbox", (-.55,-.72,.72), (0,0,.4), 95, (1,.89,.76), .38, 1.65)
light("Cool edge strip", (.5,-.15,.48), (0,0,.4), 125, (.69,.82,1), .16, 1.6)
light("Rear rim", (-.25,.5,.55), (0,0,.4), 100, (1,.87,.69), .3, 1.4)
light("Grip fill", (0,-.45,-.10), (0,0,-.01), 14, (1,.94,.86), .25, .4)
light("Lacquer highlight", (-.19,-.36,.27), (0,0,.05), 2.5, (.83,.96,1), .035, .18)
light("Crimson silk fill", (.16,-.38,-.25), (.06,0,-.25), 8, (1,.90,.82), .25, .4)

backdrop = bpy.data.materials.new("Studio slate")
backdrop.use_nodes = True
surface = backdrop.node_tree.nodes.get("Principled BSDF")
surface.inputs["Base Color"].default_value = (.003,.005,.008,1)
surface.inputs["Roughness"].default_value = .92
bpy.ops.mesh.primitive_plane_add(size=200, location=(0,.13,.4), rotation=(math.pi/2,0,0))
wall = bpy.context.object
wall.name = "Studio background"
wall.data.materials.append(backdrop)
studio(wall)

bpy.ops.object.camera_add()
camera = bpy.context.object
camera.name = "Camera_Hero"
camera.data.type = "ORTHO"
scene.camera = camera
studio(camera)
scene.render.engine = "CYCLES"
scene.cycles.samples = 80
scene.cycles.use_denoising = True
device_info = "CPU"
try:
    preferences = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA", "HIP"):
        try:
            preferences.compute_device_type = backend
            preferences.get_devices()
            devices = [device for device in preferences.devices if device.type == backend]
            if devices:
                for device in preferences.devices:
                    device.use = device.type == backend
                scene.cycles.device = "GPU"
                device_info = backend + ": " + ", ".join(d.name for d in devices)
                break
        except (TypeError, RuntimeError):
            continue
except KeyError:
    pass
scene.view_settings.view_transform = "AgX"
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_percentage = 100
scene.render.film_transparent = False


def set_view(location, target, scale, resolution, roll=0):
    camera.location = location
    rotation = (Vector(target)-camera.location).to_track_quat("-Z", "Y")
    camera.rotation_euler = rotation.to_euler()
    if roll:
        from mathutils import Quaternion
        camera.rotation_euler = (rotation @ Quaternion((0,0,1),roll)).to_euler()
    camera.data.ortho_scale = scale
    scene.render.resolution_x, scene.render.resolution_y = resolution


def render(name, location, target, scale, resolution, roll=0):
    set_view(location, target, scale, resolution, roll)
    scene.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True)


set_view((.16,-2.6,.62), (.025,0,.275), 1.59, (1200,1900), -.13)
for obj in preview.objects:
    obj.hide_set(True)
active(sword)
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        space = area.spaces.active
        space.region_3d.view_location = Vector((.025,0,.275))
        space.region_3d.view_distance = 1.75
        space.region_3d.view_rotation = camera.rotation_euler.to_quaternion()
        space.shading.type = "MATERIAL"
        space.overlay.show_overlays = False
        space.clip_end = 100
scene.render.filepath = str(OUT / "AzureDragon_v2_hero.png")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "AzureDragon_v2.blend"))
bpy.ops.export_scene.gltf(filepath=str(OUT / "AzureDragon_v2_game.glb"), export_format="GLB",
    use_selection=True, export_materials="EXPORT", export_animations=False,
    export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
    export_tangents=True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "AzureDragon_v2_game.fbx"), use_selection=True,
    object_types={"MESH"}, axis_forward="-Z", axis_up="Y", global_scale=1.0,
    apply_unit_scale=True, bake_anim=False, use_mesh_modifiers=True,
    path_mode="COPY", embed_textures=False, mesh_smooth_type="FACE", add_leaf_bones=False)

report = {
    "blender_version": bpy.app.version_string, "render_device": device_info,
    "vertices": len(sword.data.vertices), "triangles": len(sword.data.loop_triangles),
    "dimensions_m": list(sword.dimensions), "pivot_m": list(sword.location),
    "material_count": len(sword.data.materials), "mesh_count": 1,
    "part_vertex_groups": len(sword.vertex_groups), "texture_resolution": [4096,4096],
    "normal_convention": "OpenGL tangent +Y", "uv_overlap": "Intentional surface tiling",
    "engine_runtime_tested": False, "roundtrip": {},
    "tassel_rigged": False,
}
body_vertices=[v.co for v in sword.data.vertices
               if not any(sword.vertex_groups[g.group].name.startswith("Tassel") for g in v.groups)]
report["sword_body_length_m"] = max(v.z for v in body_vertices)-min(v.z for v in body_vertices)
bm = bmesh.new()
bm.from_mesh(sword.data)
report["nonmanifold_edges"] = sum(not edge.is_manifold for edge in bm.edges)
bm.free()
assert report["nonmanifold_edges"] == 0, report
assert report["triangles"] < 140000, report
assert len(sword.data.materials) == 1
assert all(math.isfinite(value) for vertex in sword.data.vertices for value in vertex.co)
assert all(triangle.area > 1e-12 for triangle in sword.data.loop_triangles)
assert 1.33 < sword.dimensions.z < 1.37
assert abs(report["sword_body_length_m"]-1.10) < .001
assert sword.location.length < 1e-7
assert all(abs(value-1) < 1e-6 for value in sword.scale)
assert len(sword.data.uv_layers) == 1
print("AZURE_DRAGON_V2_GEOMETRY_OK " + json.dumps(report), flush=True)

render("AzureDragon_v2_hero.png", (.16,-2.6,.62), (.025,0,.275), 1.59, (1200,1900), -.13)
render("AzureDragon_v2_detail.png", (.13,-1.8,.09), (.03,0,-.115), .68, (1600,1700), -.08)
render("AzureDragon_v2_guard_macro.png", (.09,-1.8,.25), (0,0,.117), .37, (1900,1250), -.06)
render("AzureDragon_v2_front.png", (.025,-3,.275), (.025,0,.275), 1.55, (1100,1900))
render("AzureDragon_v2_side.png", (2.6,-.8,.45), (.025,0,.275), 1.56, (900,1600))

# Inspect exported structure and reimport each actual deliverable into a clean scene.
glb = (OUT / "AzureDragon_v2_game.glb").read_bytes()
length = struct.unpack_from("<I", glb, 12)[0]
gltf = json.loads(glb[20:20+length])
assert len(gltf["meshes"]) == 1 and len(gltf["materials"]) == 1
assert not gltf.get("cameras") and not gltf.get("animations")
assert all("bufferView" in image for image in gltf["images"])
assert len(gltf["images"]) >= 3
report["glb_embedded_images"] = len(gltf["images"])
report["export_excludes_studio"] = True
for extension in ("glb", "fbx"):
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    path = str(OUT / ("AzureDragon_v2_game."+extension))
    if extension == "glb":
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.import_scene.fbx(filepath=path)
    bpy.context.view_layer.update()
    objects = [obj for obj in scene.objects if obj.type == "MESH"]
    assert len(objects) == 1
    obj = objects[0]
    positions = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    size = [max(p[a] for p in positions)-min(p[a] for p in positions) for a in range(3)]
    assert all(abs(a-b)<1e-4 for a,b in zip(size,report["dimensions_m"])), (extension,size)
    obj.data.calc_loop_triangles()
    assert len(obj.data.loop_triangles) == report["triangles"]
    assert obj.matrix_world.translation.length < 1e-5
    assert len(obj.data.uv_layers) == 1 and len(obj.data.materials) == 1
    report["roundtrip"][extension] = {"passed": True, "dimensions_m": size,
        "triangles": len(obj.data.loop_triangles), "uv_layers": 1, "material_count": 1}

bpy.ops.wm.open_mainfile(filepath=str(OUT / "AzureDragon_v2.blend"))
obj = bpy.data.objects.get("SM_AzureDragon_v2_Jian")
assert obj and obj.location.length < 1e-7
assert all(bpy.data.images.get("AzureDragon_v2_"+channel).packed_file for channel in images)
report["saved_blend_reopened"] = True
report["packed_pbr_textures"] = True
assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
           for path,digest in original_hashes.items())
report["previous_swords_unchanged"] = True
report["previous_swords_sha256"] = original_hashes
report["passed"] = True
(OUT / "AzureDragon_v2_validation.json").write_text(json.dumps(report,indent=2), encoding="utf-8")
print("AZURE_DRAGON_V2_VALIDATION_OK " + json.dumps(report), flush=True)
