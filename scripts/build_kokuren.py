"""Build Kokuren: a Japanese-inspired katana and fitted lacquer saya.

Run with the workspace Blender: --background --factory-startup --python this_file
Only assets/Weapons/Kokuren is written. Dimensions are in metres.
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
OUT = ROOT / "assets" / "Weapons" / "Kokuren"
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
original_files.extend(ROOT / "assets" / "Weapons" / "AzureDragon_v2" / filename
                      for filename in ("AzureDragon_v2.blend", "AzureDragon_v2_game.glb", "AzureDragon_v2_game.fbx"))
original_files.append(ROOT / "scripts" / "build_azure_dragon_v2.py")
original_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in original_files}
TEX = OUT / "Textures"
TEX.mkdir(parents=True, exist_ok=True)
validation_path = OUT / "Kokuren_validation.json"
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
asset_collection.name = "Kokuren - game mesh"
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


# Eight surface regions in a 4096 x 2048 atlas share one exported material.
n = 1024
v, u = np.mgrid[:n, :n].astype(np.float32) / n
base = np.zeros((n * 2, n * 4, 3), np.float32)
rough = np.zeros_like(base)
metal = np.zeros_like(base)
normal = np.zeros_like(base)
for tile, (rgb, roughness, metallic) in enumerate([
    ((0.53, 0.59, 0.63), 0.23, 1.0),
    ((0.018, 0.020, 0.024), 0.24, 0.16),
    ((0.36, 0.006, 0.017), 0.52, 0.0),
    ((0.72, 0.54, 0.265), 0.30, 1.0),
    ((0.60, 0.63, 0.65), 0.34, 1.0),
    ((0.68, 0.62, 0.47), 0.58, 0.0),
    ((0.019, 0.020, 0.023), 0.65, 0.0),
    ((0.055, 0.060, 0.065), 0.41, 0.78),
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
    elif tile in (2,6):
        pores = np.maximum(-grain - 0.65, 0)
        weave = np.sin(u*math.tau*180)*np.sin(v*math.tau*130)
        variation = 1 + cloud * .025 + fine * .035 + weave * .06
        height = fine * .002 + weave * .003
        local_rough = roughness + cloud * 0.025 + pores * 0.06
    elif tile == 5:
        pebbles = np.sin(u*math.tau*52+np.sin(v*math.tau*26)) * np.sin(v*math.tau*52)
        variation = 1 + pebbles*.08 + fine*.025
        height = pebbles*.012 + fine*.002
        local_rough = roughness + grain*.025
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
    y, x = (tile // 4) * n, (tile % 4) * n
    block = np.s_[y:y+n, x:x+n]
    base[block] = np.array(rgb) * variation[:, :, None]
    rough[block] = np.clip(local_rough[:, :, None], 0.18, 0.9)
    metal[block] = metallic
    normal[block] = vectors * 0.5 + 0.5

images = {
    "BaseColor": save_image("Kokuren_BaseColor", base, True),
    "Roughness": save_image("Kokuren_Roughness", rough),
    "Metallic": save_image("Kokuren_Metallic", metal),
    "Normal": save_image("Kokuren_Normal", normal),
}
material = bpy.data.materials.new("M_Kokuren_PBR_4K")
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
            uv.data[loop].uv = ((tile % 4) * .25 + .006 + uu * .238,
                                (tile // 4) * .5 + .012 + vv * .476)
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


def bezier(points, samples=24):
    a,b,c,d=[Vector(p) for p in points]
    return [a*(1-t)**3+b*3*(1-t)**2*t+c*3*(1-t)*t*t+d*t**3
            for t in np.linspace(0,1,samples)]


def ellipsoid(name, centre, radii, tile):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, location=centre)
    obj=bpy.context.object
    obj.scale=radii
    return finish(obj,name,tile,smooth=True)


def flower(name, centre, radius, plane="XY"):
    centre=Vector(centre)
    u=Vector((1,0,0))
    v=Vector((0,1,0)) if plane=="XY" else Vector((0,0,1))
    normal=u.cross(v)
    for j in range(12):
        angle=j*math.tau/12
        direction=u*math.cos(angle)+v*math.sin(angle)
        across=-u*math.sin(angle)+v*math.cos(angle)
        rings=[]
        for t in np.linspace(0,1,7):
            width=radius*.15*(.05+.95*math.sin(math.pi*t)**.7)
            height=radius*.10*(.15+.85*math.sin(math.pi*t))
            middle=centre+direction*radius*(.16+.84*t)
            rings.append([middle+across*width*math.cos(a)+normal*height*math.sin(a)
                          for a in np.linspace(0,math.tau,8,endpoint=False)])
        rings_mesh(name+"_petal",rings,3,smooth=True)
    ellipsoid(name+"_heart",centre+normal*radius*.08,
              (radius*.20,radius*.20,radius*.12) if plane=="XY" else
              (radius*.20,radius*.12,radius*.20),3)


def rim(name, rx, ry, z, radius=.0007, tile=3, scallop=0):
    points=[]
    for a in np.linspace(0,math.tau,97):
        factor=1+scallop*math.cos(4*a)
        points.append((rx*math.cos(a)*factor,ry*math.sin(a)*factor,z))
    return tube(name,points,radius,tile,8)


def annulus(name, rx, ry, inner_x, inner_y, z, depth, tile, scallop=0):
    rings=[]
    for xx,yy,zz in ((rx,ry,z-depth/2),(rx,ry,z+depth/2),
                      (inner_x,inner_y,z+depth/2),(inner_x,inner_y,z-depth/2)):
        rings.append([(xx*math.cos(a)*(1+scallop*math.cos(4*a)),
                       yy*math.sin(a)*(1+scallop*math.cos(4*a)),zz)
                      for a in np.linspace(0,math.tau,96,endpoint=False)])
    vertices=[p for ring in rings for p in ring]
    faces=[]
    for i in range(4):
        for j in range(96):
            faces.append((i*96+j,i*96+(j+1)%96,((i+1)%4)*96+(j+1)%96,((i+1)%4)*96+j))
    return mesh(name,vertices,faces,tile,bevel=.00025,smooth=True)


def centre_x(z):
    return .065*(max(z,0)/.755)**2


# A single-edged shinogi blade. The wavy hamon is a change of surface region,
# integrated in the blade mesh rather than a floating wire or decal.
blade_z=np.linspace(.004,.704,241).tolist()+[.714,.725,.736,.746]
rings=[]
for z in blade_z:
    width=np.interp(z,[.004,.10,.65,.704,.746],[.033,.032,.027,.026,.009])
    thickness=np.interp(z,[.004,.65,.704,.746],[.0035,.0028,.0027,.0012])
    shift=np.interp(z,[.004,.704,.746],[0,0,.008])
    hamon=-.54+.07*math.sin(z*math.tau/.049)+.023*math.sin(z*math.tau/.017)
    # The hamon split remains coplanar with the cutting bevel.
    hamon_depth=.025+(hamon+1)/1.25*.975
    profile=[(-1,.025),(hamon,hamon_depth),(.25,1),(.90,.71),(1,.60)]
    front=[(centre_x(z)+shift+u*width/2,-depth*thickness,z) for u,depth in profile]
    rings.append(front+[(x,-y,zz) for x,y,zz in reversed(front)])
vertices=[p for ring in rings for p in ring]
faces=[tuple(reversed(range(10)))]
surface_tiles=[0]
for i in range(len(rings)-1):
    for j in range(10):
        faces.append((i*10+j,i*10+(j+1)%10,(i+1)*10+(j+1)%10,(i+1)*10+j))
        surface_tiles.append(4 if j in (0,8,9) else 0)
tip=len(vertices)
vertices.append((centre_x(.755)+.012,0,.755))
for j in range(10):
    faces.append(((len(rings)-1)*10+j,(len(rings)-1)*10+(j+1)%10,tip))
    surface_tiles.append(4 if j in (0,8,9) else 0)
blade=mesh("Blade_curved_shinogi_and_hamon",vertices,faces,0)
for polygon,tile in zip(blade.data.polygons,surface_tiles):
    polygon.use_smooth=polygon.index>0
    if tile==4:
        for loop in polygon.loop_indices:
            blade.data.uv_layers.active.data[loop].uv.y+=.5
for edge in blade.data.edges:
    a,b=edge.vertices
    edge.use_edge_sharp=a<tip and b<tip and a//10!=b//10

# Habaki and seppa: fitted metal collars on each side of the guard.
oval("Habaki_brushed_gold",[(.004,.0185,.0048),(.031,.0177,.0045)],3,24,.00045,True)
for z in (.007,.028):
    rim("Habaki_fine_border",.0186,.0049,z,.00032)
for side in (-1,1):
    for j in range(8):
        x=-.013+j*.0037
        tube("Habaki_diagonal_engraving",[(x,side*.00495,.012),(x+.003,side*.00495,.021)],.00015,7,5)
for z in (-.007,.007):
    oval("Seppa_gold_spacer",[(z-.001,.024,.010),(z+.001,.024,.010)],3,36,.00025,True)

# Pierced mokko-inspired tsuba: dark iron, gold rim, wave arms and flowers.
annulus("Tsuba_mokko_outer_iron",.048,.041,.041,.034,0,.005,7,.055)
annulus("Tsuba_inner_hub",.024,.012,.0189,.0049,0,.006,7)
for z in (-.0028,.0028):
    rim("Tsuba_gold_outer_lip",.048,.041,z,.0008,scallop=.055)
    rim("Tsuba_gold_inner_lip",.041,.034,z,.00055,scallop=.055)
    rim("Tsuba_gold_hub",.0238,.0118,z,.0005)
for j in range(8):
    a=j*math.tau/8
    path=bezier([(.022*math.cos(a),.011*math.sin(a),0),
                 (.032*math.cos(a+.27),.024*math.sin(a+.27),0),
                 (.037*math.cos(a-.16),.029*math.sin(a-.16),0),
                 (.043*math.cos(a),.036*math.sin(a),0)],18)
    tube("Tsuba_curved_iron_arm",path,.0032,7,8)
    for side in (-1,1):
        tube("Tsuba_wave_gold_inlay",[(p[0],p[1],side*.0031) for p in path],.00055,3,6)
for a in (.74,2.95,4.84):
    flower("Tsuba_gold_chrysanthemum",(.035*math.cos(a),.029*math.sin(a),.0042),.0082)
    flower("Tsuba_reverse_chrysanthemum",(.035*math.cos(a),.029*math.sin(a),-.0042),.006)

# Ivory samegawa underlay and actual crossed black silk ribbons.
oval("Tsuka_samegawa_core",[(-.260,.0167,.0125),(-.245,.0178,.0130),
     (-.15,.0163,.0123),(-.065,.0175,.0132),(-.016,.018,.0134)],5,40,smooth=True)
for row in range(9):
    mid=-.034-row*.025
    for side in (-1,1):
        for hand in (-1,1):
            rings=[]
            for t in np.linspace(0,1,27):
                angle=math.pi*t
                z=mid+hand*(t-.5)*.025
                rx=np.interp(z,[-.26,-.15,-.065,-.016],[.018,.0168,.018,.0185])
                ry=np.interp(z,[-.26,-.15,-.065,-.016],[.0134,.0129,.0138,.014])
                normal=Vector((math.cos(angle)/rx,side*math.sin(angle)/ry,0)).normalized()
                tangent=Vector((-rx*math.pi*math.sin(angle),
                                side*ry*math.pi*math.cos(angle),hand*.025)).normalized()
                across=tangent.cross(normal).normalized()
                crossing=.0009*math.sin(math.pi*t)**8 if hand==1 else 0
                point=Vector((rx*math.cos(angle),side*ry*math.sin(angle),z))+normal*crossing
                cross=[(-1,-.3),(-1,.3),(-.82,1),(.82,1),(1,.3),(1,-.3),(.82,-1),(-.82,-1)]
                rings.append([point+across*(w*.0047)+normal*(h*.00065) for w,h in cross])
            rings_mesh("Tsukamaki_crossed_black_silk",rings,6,smooth=True)
# Small actual pebbles in each exposed samegawa diamond improve close-up relief.
bead_bm=bmesh.new()
bmesh.ops.create_icosphere(bead_bm,subdivisions=1,radius=1)
bead_bm.verts.ensure_lookup_table()
bead_bm.verts.index_update()
bead_vertices=[tuple(v.co) for v in bead_bm.verts]
bead_faces=[tuple(v.index for v in f.verts) for f in bead_bm.faces]
bead_bm.free()
points=[]
for row in range(8):
    zmid=-.0465-row*.025
    for dz in np.linspace(-.0045,.0045,5):
        for x in np.linspace(-.007,.007,7):
            if abs(x)/.009+abs(dz)/.007>1:
                continue
            z=zmid+dz
            rx=np.interp(z,[-.26,-.15,-.065,-.016],[.0178,.0163,.0175,.018])
            ry=np.interp(z,[-.26,-.15,-.065,-.016],[.013,.0123,.0132,.0134])
            for side in (-1,1):
                points.append((x,side*(ry*math.sqrt(1-(x/rx)**2)+.00015),z))
verts=[]
faces=[]
for point in points:
    start=len(verts)
    verts.extend([(point[0]+x*.0006,point[1]+y*.00032,point[2]+z*.0006)
                  for x,y,z in bead_vertices])
    faces.extend([tuple(start+i for i in face) for face in bead_faces])
mesh("Samegawa_pebbled_diamonds",verts,faces,5,smooth=True)
for z in (-.018,-.260):
    oval("Fuchi_kashira_black_iron",[(z-.007,.019,.0145),(z+.006,.019,.0145)],7,40,.00065,True)
    for zz in (z-.0055,z+.0045):
        rim("Fuchi_kashira_gilded_edge",.0192,.0147,zz,.00055)
    for side in (-1,1):
        for j in range(3):
            x=-.010+j*.010
            points=[(x+.0035*math.cos(a),side*.0149,z+.002*math.sin(a))
                    for a in np.linspace(0,math.tau,25)]
            tube("Fuchi_engraved_wave",points,.0003,3,5)
flower("Menuki_gold_flower",(0,-.014,-.095),.007,"XZ")
flower("Menuki_gold_flower_lower",(0,-.014,-.193),.006,"XZ")
for z in (-.061,-.218):
    ellipsoid("Mekugi_dark_pin",(0,-.0137,z),(.0019,.00065,.0019),7)


def join_parts(name, shift_z=0):
    active(parts[0])
    for obj in parts:
        obj.select_set(True)
    bpy.ops.object.join()
    obj=bpy.context.object
    for vertex in obj.data.vertices:
        vertex.co.z+=shift_z
    scene.cursor.location=(0,0,0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    obj.name=name
    obj.modifiers.new("Stable game triangulation","TRIANGULATE")
    obj.data.calc_loop_triangles()
    parts.clear()
    return obj


sword=join_parts("SM_Kokuren_Katana",.140)
sword["pivot"]="Grip centre, blade +Z, cutting edge -X, front -Y"
sword["asset_name"]="Kokuren / 흑련 - Japanese-inspired fantasy katana"

# A separate hollow saya. Its local origin is the mouth, and translating it
# to (0,0,.140) seats it around the blade in this display coordinate system.
sheath_levels=[(.004,.0225,.0072),(.04,.0225,.0072),(.20,.022,.0070),
               (.43,.021,.0065),(.65,.0195,.0060),(.72,.0185,.0055),
               (.755,.0170,.0050),(.773,.0035,.0028)]
outer_levels=[(z,rx+.0032,ry+.0035) for z,rx,ry in sheath_levels]
outer_levels.append((.780,.003,.003))
count=48
outer=[[(centre_x(z)+rx*math.cos(a),ry*math.sin(a),z)
        for a in np.linspace(0,math.tau,count,endpoint=False)] for z,rx,ry in outer_levels]
inner=[[(centre_x(z)+rx*math.cos(a),ry*math.sin(a),z)
        for a in np.linspace(0,math.tau,count,endpoint=False)] for z,rx,ry in reversed(sheath_levels)]
rings=outer+inner
verts=[p for ring in rings for p in ring]
faces=[]
outer_last=len(outer)-1
inner_first=len(outer)
for i in list(range(outer_last))+list(range(inner_first,len(rings)-1)):
    for j in range(count):
        faces.append((i*count+j,i*count+(j+1)%count,(i+1)*count+(j+1)%count,(i+1)*count+j))
faces.append(tuple(range(outer_last*count,(outer_last+1)*count)))
faces.append(tuple(reversed(range(inner_first*count,(inner_first+1)*count))))
for j in range(count):
    faces.append((j,(len(rings)-1)*count+j,(len(rings)-1)*count+(j+1)%count,(j+1)%count))
mesh("Saya_hollow_black_lacquer",verts,faces,1,smooth=True)
annulus("Saya_koiguchi_gold_mouth",.0262,.0112,.0224,.0071,.009,.012,3)
for z in (.020,.027,.747,.755):
    rx=np.interp(z,[v[0] for v in outer_levels],[v[1] for v in outer_levels])
    ry=np.interp(z,[v[0] for v in outer_levels],[v[2] for v in outer_levels])
    obj=rim("Saya_gold_fine_bands",rx+.0004,ry+.0004,z,.0006)
    obj.location.x+=centre_x(z)
for side in (-1,1):
    # Gilded floral inlay and slender wave lines follow the lacquer surface.
    for z in (.24,.50,.68):
        flower("Saya_gold_flower_inlay",(centre_x(z),side*.0100,z),.008,"XZ")
    for hand in (-1,1):
        points=[]
        for z in np.linspace(.19,.72,120):
            x=hand*(.006+.004*math.sin(z*math.tau/.13))
            rx=np.interp(z,[v[0] for v in outer_levels],[v[1] for v in outer_levels])
            ry=np.interp(z,[v[0] for v in outer_levels],[v[2] for v in outer_levels])
            y=ry*math.sqrt(1-(x/rx)**2)+.00012
            points.append((centre_x(z)+x,side*y,z))
        tube("Saya_gold_wave_trail",points,.00020,3,5)
# A crimson sageo wraps around the saya and ties through the side fitting.
for z in np.linspace(.061,.104,8):
    obj=rim("Sageo_crimson_wrap",.0265,.0116,z,.0020,2)
    obj.location.x+=centre_x(z)
annulus("Kurikata_gold_loop",.009,.005,.006,.0023,.119,.004,3)
loop=parts[-1]
loop.rotation_euler.y=math.pi/2
loop.location=(.028,0,.119)
# Local annulus initially centred at .119; move its mesh centre before rotation.
for vertex in loop.data.vertices:
    vertex.co.z-=.119
for j in range(2):
    path=bezier([(.028,-.003,.119),(.065,-.020,.110+j*.009),
                 (.071,-.022,.163+j*.008),(.032,-.011,.136)],34)
    tube("Sageo_tied_bow",path,.0021,2,8)
for j in range(2):
    path=bezier([(.033,-.010,.128),(.058+j*.006,-.015,.164),
                 (.052+j*.009,-.011,.222),(.042+j*.018,-.009,.249+j*.024)],36)
    tube("Sageo_static_tail",path,.0020,2,8)
    for k in range(7):
        end=path[-1]
        tube("Sageo_small_fringe",[(end[0]+(k-3)*.0005,end[1],end[2]),
             (end[0]+(k-3)*.0008,end[1]-.001,end[2]+.009+(k%3)*.001)],.00023,2,5)
saya=join_parts("SM_Kokuren_Saya")
saya.location=(.170,.012,.140)
saya["pivot"]="Saya mouth, tip +Z"
saya["sheathed_location_m"]=[0,0,.140]
saya["cord_note"]="Static sageo geometry; no cloth simulation or rig"
assets=[sword,saya]
for obj in assets:
    obj["units"]="metres"
    obj["texture_note"]="4096x2048 PBR atlas, OpenGL normal +Y"
    obj["uv_note"]="Intentional shared surface UV; no unique lightmap UV"



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


set_view((.48,-2.8,1.00),(.105,0,.385),1.23,(1500,1900),-.16)
for obj in preview.objects:
    obj.hide_set(True)
active(sword)
saya.select_set(True)
for area in bpy.context.screen.areas:
    if area.type=="VIEW_3D":
        space=area.spaces.active
        space.region_3d.view_location=Vector((.105,0,.385))
        space.region_3d.view_distance=1.35
        space.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
        space.shading.type="MATERIAL"
        space.overlay.show_overlays=False
scene.render.filepath=str(OUT/"Kokuren_hero.png")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Kokuren.blend"))
bpy.ops.export_scene.gltf(filepath=str(OUT/"Kokuren_game.glb"),export_format="GLB",
    use_selection=True,export_materials="EXPORT",export_animations=False,export_yup=True,
    export_apply=True,export_texcoords=True,export_normals=True,export_tangents=True)
bpy.ops.export_scene.fbx(filepath=str(OUT/"Kokuren_game.fbx"),use_selection=True,
    object_types={"MESH"},axis_forward="-Z",axis_up="Y",global_scale=1.0,
    apply_unit_scale=True,bake_anim=False,use_mesh_modifiers=True,path_mode="COPY",
    embed_textures=False,mesh_smooth_type="FACE",add_leaf_bones=False)


def mesh_stats(obj):
    obj.data.calc_loop_triangles()
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    nonmanifold=sum(not edge.is_manifold for edge in bm.edges)
    bm.free()
    positions=[obj.matrix_world@vertex.co for vertex in obj.data.vertices]
    bounds=[[min(p[a] for p in positions) for a in range(3)],
            [max(p[a] for p in positions) for a in range(3)]]
    return {"vertices":len(obj.data.vertices),"triangles":len(obj.data.loop_triangles),
            "bounds_m":bounds,"dimensions_m":[b-a for a,b in zip(*bounds)],
            "origin_m":list(obj.matrix_world.translation),"nonmanifold_edges":nonmanifold,
            "vertex_groups":len(obj.vertex_groups),"material_count":len(obj.data.materials)}


bpy.context.view_layer.update()
report={"blender_version":bpy.app.version_string,"render_device":device_info,
        "mesh_count":2,"shared_material_count":1,"texture_resolution":[4096,2048],
        "normal_convention":"OpenGL tangent +Y","uv_overlap":"Intentional surface tiling",
        "engine_runtime_tested":False,"cord_rigged":False,"roundtrip":{},
        "meshes":{obj.name:mesh_stats(obj) for obj in assets}}
for obj in assets:
    stats=report["meshes"][obj.name]
    assert stats["nonmanifold_edges"]==0,(obj.name,stats)
    assert all(t.area>1e-12 for t in obj.data.loop_triangles),obj.name
    assert all(math.isfinite(v) for vertex in obj.data.vertices for v in vertex.co)
    assert len(obj.data.materials)==1 and len(obj.data.uv_layers)==1
    assert all(abs(v-1)<1e-6 for v in obj.scale)
report["triangles"]=sum(s["triangles"] for s in report["meshes"].values())
assert report["triangles"]<140000,report["triangles"]
assert 1.01<report["meshes"][sword.name]["dimensions_m"][2]<1.04
assert sword.location.length<1e-7
# Check every blade vertex against the actual hollow saya's elliptical bore.
blade_indices=[group.index for group in sword.vertex_groups if group.name.startswith("Blade_")]
fit_max=0
for vertex in sword.data.vertices:
    if not any(g.group in blade_indices for g in vertex.groups):
        continue
    x,y,z=vertex.co
    z-=.140
    rx=np.interp(z,[p[0] for p in sheath_levels],[p[1] for p in sheath_levels])
    ry=np.interp(z,[p[0] for p in sheath_levels],[p[2] for p in sheath_levels])
    fit_max=max(fit_max,((x-centre_x(z))/rx)**2+(y/ry)**2)
assert fit_max<1,fit_max
report["blade_fits_saya"]=True
report["max_bore_normalized_radius_squared"]=float(fit_max)
print("KOKUREN_GEOMETRY_OK "+json.dumps(report),flush=True)

render("Kokuren_hero.png",(.48,-2.8,1.00),(.105,0,.385),1.23,(1500,1900),-.16)
render("Kokuren_hilt.png",(.30,-.75,.51),(.030,0,.035),.46,(1700,1700),-.10)
render("Kokuren_tsuba.png",(.10,-.23,.41),(0,0,.14),.165,(1700,1500),-.08)
render("Kokuren_front.png",(.105,-3,.385),(.105,0,.385),1.17,(1300,1900))
render("Kokuren_blade_detail.png",(.35,-1.8,.77),(.045,0,.69),.43,(1400,1800),-.12)

# Export roundtrip: verify each separate object and its true vertex bounds.
raw=(OUT/"Kokuren_game.glb").read_bytes()
length=struct.unpack_from("<I",raw,12)[0]
gltf=json.loads(raw[20:20+length])
assert len(gltf["meshes"])==2 and len(gltf["materials"])==1
assert not gltf.get("cameras") and not gltf.get("animations")
assert len(gltf["images"])>=3 and all("bufferView" in im for im in gltf["images"])
report["glb_embedded_images"]=len(gltf["images"])
report["export_excludes_studio"]=True
for extension in ("glb","fbx"):
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj,do_unlink=True)
    path=str(OUT/("Kokuren_game."+extension))
    if extension=="glb":
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.import_scene.fbx(filepath=path)
    bpy.context.view_layer.update()
    imported=[obj for obj in scene.objects if obj.type=="MESH"]
    assert len(imported)==2
    checked={}
    for obj in imported:
        key=next(name for name in report["meshes"] if obj.name.startswith(name))
        expected=report["meshes"][key]
        actual=mesh_stats(obj)
        assert actual["triangles"]==expected["triangles"]
        assert all(abs(a-b)<1e-5 for a,b in zip(actual["origin_m"],expected["origin_m"]))
        assert all(abs(a-b)<1e-4 for row_a,row_b in zip(actual["bounds_m"],expected["bounds_m"])
                   for a,b in zip(row_a,row_b)),(extension,key,actual)
        assert len(obj.data.uv_layers)==1 and len(obj.data.materials)==1
        checked[key]={"passed":True,"triangles":actual["triangles"],"bounds_m":actual["bounds_m"]}
    report["roundtrip"][extension]=checked
bpy.ops.wm.open_mainfile(filepath=str(OUT/"Kokuren.blend"))
assert all(bpy.data.objects.get(name) is not None for name in report["meshes"])
assert all(bpy.data.images.get("Kokuren_"+channel).packed_file for channel in images)
report["saved_blend_reopened"]=True
report["packed_pbr_textures"]=True
assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
           for path,digest in original_hashes.items())
report["previous_swords_unchanged"]=True
report["previous_swords_sha256"]=original_hashes
report["passed"]=True
(OUT/"Kokuren_validation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("KOKUREN_VALIDATION_OK "+json.dumps({k:v for k,v in report.items()
      if k!="previous_swords_sha256"}),flush=True)


