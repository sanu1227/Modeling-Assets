"""Build and verify Aurelia, an ornate royal game longsword.

Run with the workspace Blender: --background --factory-startup --python this_file
Only assets/Weapons/Aurelia is written. Dimensions are in metres.
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
OUT = ROOT / "assets" / "Weapons" / "Aurelia"
original_files = [ROOT / "assets" / "Weapons" / "Blackthorn" / filename
                  for filename in ("Blackthorn.blend", "Blackthorn_game.glb", "Blackthorn_game.fbx")]
original_files.append(ROOT / "scripts" / "build_blackthorn.py")
original_hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in original_files}
TEX = OUT / "Textures"
TEX.mkdir(parents=True, exist_ok=True)
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
asset_collection.name = "Aurelia - game mesh"
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


# Four 1024-pixel surface regions in one 2048-pixel material atlas.
n = 1024
v, u = np.mgrid[:n, :n].astype(np.float32) / n
base = np.zeros((n * 2, n * 2, 3), np.float32)
rough = np.zeros_like(base)
metal = np.zeros_like(base)
normal = np.zeros_like(base)
for tile, (rgb, roughness, metallic) in enumerate([
    ((0.59, 0.64, 0.70), 0.26, 1.0),
    ((0.026, 0.084, 0.20), 0.24, 0.55),
    ((0.018, 0.050, 0.125), 0.57, 0.0),
    ((0.78, 0.62, 0.34), 0.32, 1.0),
]):
    cloud = smooth_noise(n, 80)
    fine = smooth_noise(n, 2.5)
    grain = smooth_noise(n, 7)
    scratches = np.zeros((n, n), np.float32)
    for _ in range(160 if tile != 2 else 65):
        x = int(rng.integers(3, n - 3))
        start = int(rng.integers(0, n - 90))
        length = int(rng.integers(25, min(350, n - start)))
        scratches[start:start + length, x:x + 1] += rng.uniform(0.1, 0.6)
    if tile == 2:
        pores = np.maximum(-grain - 0.65, 0)
        variation = 1 + cloud * 0.06 + fine * 0.045 - pores * 0.11
        height = fine * 0.006 + grain * 0.018 - pores * 0.013
        local_rough = roughness + cloud * 0.025 + pores * 0.06
    else:
        brushed = np.sin(u * math.tau * 360 + np.sin(v * 13) * 0.18)
        variation = 1 + cloud * 0.025 + fine * 0.009 + scratches * 0.09
        height = fine * 0.0007 + brushed * 0.001 - scratches * 0.009
        local_rough = roughness + cloud * 0.018 + brushed * 0.016 + scratches * 0.16
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
    "BaseColor": save_image("Aurelia_BaseColor", base, True),
    "Roughness": save_image("Aurelia_Roughness", rough),
    "Metallic": save_image("Aurelia_Metallic", metal),
    "Normal": save_image("Aurelia_Normal", normal),
}
material = bpy.data.materials.new("M_Aurelia_PBR_2K")
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

gem_material = bpy.data.materials.new("M_Aurelia_Cut_Sapphire")
gem_material.use_nodes = True
gem_bsdf = gem_material.node_tree.nodes.get("Principled BSDF")
gem_bsdf.inputs["Base Color"].default_value = (.006, .095, .34, 1)
gem_bsdf.inputs["Metallic"].default_value = .25
gem_bsdf.inputs["Roughness"].default_value = .12
gem_bsdf.inputs["IOR"].default_value = 1.76
gem_bsdf.inputs["Coat Weight"].default_value = .8
gem_bsdf.inputs["Coat Roughness"].default_value = .08


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


# Double-edged blade: real recessed fuller, broad polished cutting bevels,
# distal taper, an unsharpened ricasso, and one welded tip vertex.
profile = [(-1, .025), (-.72, .8), (-.34, 1), (-.24, .61),
           (0, .55), (.24, .61), (.34, 1), (.72, .8), (1, .025)]
key_sections = [(0.006, .0335, .0047, 0), (.067, .0335, .0047, 0),
                (.100, .0326, .0045, .5), (.137, .0315, .0043, 1),
                (.54, .0265, .0035, 1), (.73, .023, .003, 1),
                (.82, .0185, .0025, 0), (.92, .0095, .0015, 0),
                (.962, .0034, .0007, 0)]
sections = []
for first, second in zip(key_sections, key_sections[1:]):
    for t in (0, .25, .5, .75):
        sections.append(tuple(a+(b-a)*t for a,b in zip(first,second)))
sections.append(key_sections[-1])
blade_rings = []
for z, width, thick, fuller in sections:
    front = []
    for xx, yy in profile:
        diamond = 1 - abs(xx)*.88
        depth = (yy*fuller + diamond*(1-fuller))*thick
        front.append((xx*width, -depth, z))
    blade_rings.append(front + [(x, -y, z) for x, y, z in reversed(front)])
count = len(blade_rings[0])
vertices = [point for ring in blade_rings for point in ring]
root_center = len(vertices)
vertices.append((0, 0, sections[0][0]))
faces = [(root_center, (j+1)%count, j) for j in range(count)]
for row in range(len(blade_rings)-1):
    for j in range(count):
        a, b = row*count+j, row*count+(j+1)%count
        faces.append((a, b, b+count, a+count))
tip = len(vertices)
vertices.append((0, 0, .987))
for j in range(count):
    faces.append(((len(blade_rings)-1)*count+j,
                  (len(blade_rings)-1)*count+(j+1)%count, tip))
blade = mesh("01_Blade_fuller_and_ricasso", vertices, faces, 0)
for polygon in blade.data.polygons:
    polygon.use_smooth = polygon.index >= count
for edge in blade.data.edges:
    a, b = edge.vertices
    edge.use_edge_sharp = (a < root_center and b < root_center and a//count != b//count)

# Smooth sampled curves keep the small filigree organic without subdivision.
def bezier(points, samples=18):
    a,b,c,d = [Vector(p) for p in points]
    return [(1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*d
            for t in np.linspace(0,1,samples)]


def gem(name, x, z, rx, rz, y, side):
    rings = []
    for distance, scale in ((0,1),(.0025,1),(.007,.64),(.0082,.42)):
        rings.append([(x+rx*scale*math.cos(j*math.tau/12),
                       side*(y+distance),z+rz*scale*math.sin(j*math.tau/12))
                      for j in range(12)])
    obj = rings_mesh(name, rings, 1)
    obj.data.materials.clear()
    obj.data.materials.append(gem_material)
    return obj


def leaf(name, x, z, length, width, angle, y, side):
    outline = [(0,-length*.5),(-width*.55,-length*.13),(-width*.50,length*.15),
               (0,length*.5),(width*.50,length*.15),(width*.55,-length*.13)]
    outline = [(x+xx*math.cos(angle)-zz*math.sin(angle),
                z+xx*math.sin(angle)+zz*math.cos(angle)) for xx,zz in outline]
    return plaque(name, outline, .0014, 3, center_y=side*y, bevel=.00025)


# Two broad swept wings, enamel fields, curled lower branches, and gilt veins.
wing = [(.023,.014),(.046,.012),(.075,.019),(.111,.041),(.145,.069),
        (.178,.084),(.169,.057),(.149,.030),(.119,.004),(.084,-.016),
        (.048,-.027),(.023,-.024)]
enamel = [(.042,.005),(.075,.011),(.108,.031),(.150,.062),(.147,.044),
          (.120,.016),(.083,-.008),(.050,-.017)]
for hand in (-1,1):
    plaque(f"02_Golden_wing_{hand}", [(hand*x,z) for x,z in wing], .021, 3, bevel=.0011)
    for side in (-1,1):
        plaque(f"03_Blue_enamel_wing_{hand}_{side}", [(hand*x,z) for x,z in enamel],
               .0014,1,center_y=side*.011,bevel=.0003)
        tube(f"04_Wing_gold_vein_{hand}_{side}",
             bezier([(hand*.036,side*.0128,-.012),(hand*.073,side*.0128,-.017),
                     (hand*.124,side*.0128,.034),(hand*.161,side*.0128,.067)],26), .001,3)
        for j in range(4):
            x,z = .062+j*.023, -.004+j*.015
            tube(f"05_Wing_barb_{hand}_{side}_{j}",
                 bezier([(hand*x,side*.013,z),(hand*(x+.007),side*.013,z+.009),
                         (hand*(x+.009),side*.013,z+.009),(hand*(x+.003),side*.013,z+.011)],12),
                 .00065,3)
        # A curled branch leaves a real open space below each wing.
        tube(f"06_Open_scroll_{hand}_{side}",
             bezier([(hand*.029,side*.004,-.025),(hand*.065,side*.004,-.067),
                     (hand*.112,side*.004,-.038),(hand*.088,side*.004,-.023)],25),.0022,3)
        leaf(f"07_Scroll_leaf_{hand}_{side}",hand*.091,-.026,.021,.009,
             hand*.7,.005,side)
        gem(f"08_Wing_sapphire_{hand}_{side}",hand*.153,.056,.0043,.0068,.012,side)

# Marquise centrepiece, crown prongs and paired engraved collar plates.
plaque("09_Guard_centre_gold",[(0,.047),(.026,.023),(.033,-.005),(.022,-.033),
       (0,-.051),(-.022,-.033),(-.033,-.005),(-.026,.023)],.030,3,bevel=.001)
for side in (-1,1):
    plaque(f"10_Centre_enamel_{side}",[(0,.037),(.021,.015),(.024,-.007),
           (0,-.040),(-.024,-.007),(-.021,.015)],.0018,1,center_y=side*.0155,bevel=.0005)
    oval_border = [(math.sin(t)*.0175,side*.018,-.001+math.cos(t)*.030)
                   for t in np.linspace(0,math.tau,49)]
    tube(f"11_Gem_gold_bezel_{side}",oval_border,.0015,3)
    gem(f"12_Central_sapphire_{side}",0,-.001,.0148,.026,.017,side)
    for hand in (-1,1):
        leaf(f"13_Crown_leaf_{hand}_{side}",hand*.020,.040,.030,.009,
             -hand*.45,.016,side)
        for z in (-.025,.022):
            leaf(f"14_Bezel_prong_{hand}_{side}_{z}",hand*.011,z,.010,.003,
                 hand*.45,.023,side)

# Gold damascene-style relief along the lower blade; cutting edges stay bare.
for side in (-1,1):
    for hand in (-1,1):
        tube(f"15_Blade_vine_{hand}_{side}",bezier([
             (hand*.008,side*.0048,.056),(hand*.026,side*.0048,.145),
             (-hand*.003,side*.004,.215),(hand*.006,side*.004,.300)],30),.00065,3)
        for j in range(5):
            z=.091+j*.032
            x=hand*(.012-.001*j)
            leaf(f"16_Blade_laurel_{hand}_{side}_{j}",x,z,.024,.005,
                 -hand*.72,.0048,side)
        tube(f"17_Fuller_gold_line_{hand}_{side}",
             [(hand*.0055,side*.0038,.28),(hand*.0047,side*.0036,.43),
              (hand*.0038,side*.0032,.57),(0,side*.0030,.615)],.00045,3)
    for j in range(5):
        z=.300+j*.059
        plaque(f"18_Blade_diamond_{side}_{j}",[(0,z+.010),(.0025,z),
               (0,z-.010),(-.0025,z)],.00035,3,center_y=side*(.004-.00015*j),bevel=0)

# Navy leather grip with a thin gilt braid and broad engraved end collars.
oval("19_Navy_grip_core",[(-.254,.0148,.0116),(-.220,.0157,.0121),
     (-.150,.0168,.0128),(-.080,.018,.0138),(-.044,.0185,.014)],2,24,smooth=True)
for z,rx,ry in [(-.048,.0203,.0155),(-.252,.0166,.0135)]:
    oval("20_Engraved_gold_ferrule",[(z-.009,rx,ry),(z+.009,rx,ry)],3,24,.0007,True)
    oval("21_Enamel_ferrule_band",[(z-.0032,rx+.0003,ry+.0003),
         (z+.0032,rx+.0003,ry+.0003)],1,24,.0003,True)
    for zz in (z-.007,z+.007):
        oval("22_Ferrule_beaded_rim",[(zz-.0009,rx+.00065,ry+.00065),
             (zz+.0009,rx+.00065,ry+.00065)],3,24,.0003,True)
    for side in (-1,1):
        for x in (-.009,0,.009):
            leaf("23_Ferrule_fleur",x,z,.007,.003,0,ry+.001,side)

rings=[]
turns,steps=14,14*32
pitch=.184/turns
braid=[]
for i in range(steps+1):
    f=i/steps
    angle=f*turns*math.tau
    z=-.242+f*.184
    rx,ry=.0155+f*.003,.012+f*.002
    section=[(-.0002,-pitch*.48),(.00065,-pitch*.40),(.00095,-pitch*.28),
             (.00095,pitch*.34),(.00045,pitch*.49),(-.0002,pitch*.49)]
    rings.append([((rx+r)*math.cos(angle),(ry+r)*math.sin(angle),z+dz) for r,dz in section])
    braid.append(((rx+.0012)*math.cos(angle),(ry+.0012)*math.sin(angle),z-pitch*.30))
rings_mesh("24_Navy_leather_wrap",rings,2,smooth=True)
tube("25_Gilt_spiral_braid",braid,.00048,3,5)

# A sunburst pommel: scalloped gold body, enamel disk, sapphire and fine rays.
pommel_z=-.300
outline=[]
for j in range(32):
    angle=j*math.tau/32
    radius=.031 if j%2==0 else .028
    outline.append((radius*math.cos(angle),pommel_z+radius*math.sin(angle)))
plaque("26_Sunburst_pommel",outline,.024,3,bevel=.0006)
oval("27_Pommel_neck",[(-.278,.014,.010),(-.258,.014,.010)],3,16,.0006,True)
plaque("28_Pommel_finial",[(0,-.343),(.009,-.325),(0,-.321),(-.009,-.325)],
       .014,3,bevel=.0006)
for side in (-1,1):
    disk=[(.023*math.cos(t),pommel_z+.023*math.sin(t)) for t in np.linspace(0,math.tau,32,endpoint=False)]
    plaque(f"29_Pommel_enamel_{side}",disk,.0016,1,center_y=side*.0128,bevel=.0003)
    for radius in (.025,.015):
        tube(f"30_Pommel_gold_ring_{side}_{radius}",
             [(radius*math.cos(t),side*.0145,pommel_z+radius*math.sin(t))
              for t in np.linspace(0,math.tau,49)],.001,3)
    for j in range(12):
        angle=j*math.tau/12
        tube(f"31_Sun_ray_{side}_{j}",
             [(r*math.cos(angle),side*.0147,pommel_z+r*math.sin(angle)) for r in (.0165,.023)],.00065,3)
    gem(f"32_Pommel_sapphire_{side}",0,pommel_z,.0127,.0127,.0148,side)

# One game mesh with an atlas material and a separate cut-gem material.
active(blade)
for obj in parts:
    obj.select_set(True)
bpy.ops.object.join()
sword = bpy.context.object
sword.name = "SM_Aurelia_Longsword"
for vertex in sword.data.vertices:
    vertex.co.z += .135
scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
sword["asset_name"] = "Aurelia / 아우렐리아 - Royal Dawn"
sword["pivot"] = "Grip centre; blade points along local +Z; front is -Y"
sword["units"] = "metres"
sword["textures"] = "2048px PBR atlas; OpenGL tangent-space normal (+Y)"
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
light("Grip fill", (0,-.45,-.10), (0,0,-.01), 9, (1,.94,.86), .25, .4)

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
scene.cycles.samples = 48
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


set_view((.14,-2.6,.83), (0,0,.455), 1.58, (1200,1800), -.16)
for obj in preview.objects:
    obj.hide_set(True)
active(sword)
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        space = area.spaces.active
        space.region_3d.view_location = Vector((0,0,.455))
        space.region_3d.view_distance = 1.75
        space.region_3d.view_rotation = camera.rotation_euler.to_quaternion()
        space.shading.type = "MATERIAL"
        space.overlay.show_overlays = False
        space.clip_end = 100
scene.render.filepath = str(OUT / "Aurelia_hero.png")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Aurelia.blend"))
bpy.ops.export_scene.gltf(filepath=str(OUT / "Aurelia_game.glb"), export_format="GLB",
    use_selection=True, export_materials="EXPORT", export_animations=False,
    export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
    export_tangents=True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "Aurelia_game.fbx"), use_selection=True,
    object_types={"MESH"}, axis_forward="-Z", axis_up="Y", global_scale=1.0,
    apply_unit_scale=True, bake_anim=False, use_mesh_modifiers=True,
    path_mode="COPY", embed_textures=False, mesh_smooth_type="FACE", add_leaf_bones=False)

report = {
    "blender_version": bpy.app.version_string, "render_device": device_info,
    "vertices": len(sword.data.vertices), "triangles": len(sword.data.loop_triangles),
    "dimensions_m": list(sword.dimensions), "pivot_m": list(sword.location),
    "material_count": len(sword.data.materials), "mesh_count": 1,
    "part_vertex_groups": len(sword.vertex_groups), "texture_resolution": [2048,2048],
    "normal_convention": "OpenGL tangent +Y", "uv_overlap": "Intentional surface tiling",
    "engine_runtime_tested": False, "roundtrip": {},
}
bm = bmesh.new()
bm.from_mesh(sword.data)
report["nonmanifold_edges"] = sum(not edge.is_manifold for edge in bm.edges)
bm.free()
assert report["nonmanifold_edges"] == 0, report
assert report["triangles"] < 40000, report
assert len(sword.data.materials) == 2
assert all(math.isfinite(value) for vertex in sword.data.vertices for value in vertex.co)
assert all(triangle.area > 1e-12 for triangle in sword.data.loop_triangles)
assert 1.32 < sword.dimensions.z < 1.34
assert sword.location.length < 1e-7
assert all(abs(value-1) < 1e-6 for value in sword.scale)
assert len(sword.data.uv_layers) == 1
print("AURELIA_GEOMETRY_OK " + json.dumps(report), flush=True)

render("Aurelia_hero.png", (.14,-2.6,.83), (0,0,.455), 1.58, (1200,1800), -.16)
render("Aurelia_detail.png", (.16,-1.8,.19), (0,0,.007), .56, (1600,1600), -.12)
render("Aurelia_front.png", (0,-3,.455), (0,0,.455), 1.50, (1100,1800))
render("Aurelia_side.png", (2.6,-.7,.55), (0,0,.455), 1.53, (900,1500))

# Inspect exported structure and reimport each actual deliverable into a clean scene.
glb = (OUT / "Aurelia_game.glb").read_bytes()
length = struct.unpack_from("<I", glb, 12)[0]
gltf = json.loads(glb[20:20+length])
assert len(gltf["meshes"]) == 1 and len(gltf["materials"]) == 2
assert not gltf.get("cameras") and not gltf.get("animations")
assert all("bufferView" in image for image in gltf["images"])
assert len(gltf["images"]) >= 3
report["glb_embedded_images"] = len(gltf["images"])
report["export_excludes_studio"] = True
for extension in ("glb", "fbx"):
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    path = str(OUT / ("Aurelia_game."+extension))
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
    assert len(obj.data.uv_layers) == 1 and len(obj.data.materials) == 2
    report["roundtrip"][extension] = {"passed": True, "dimensions_m": size,
        "triangles": len(obj.data.loop_triangles), "uv_layers": 1, "material_count": 2}

bpy.ops.wm.open_mainfile(filepath=str(OUT / "Aurelia.blend"))
obj = bpy.data.objects.get("SM_Aurelia_Longsword")
assert obj and obj.location.length < 1e-7
assert all(bpy.data.images.get("Aurelia_"+channel).packed_file for channel in images)
report["saved_blend_reopened"] = True
report["packed_pbr_textures"] = True
assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
           for path,digest in original_hashes.items())
report["blackthorn_unchanged"] = True
report["blackthorn_sha256"] = original_hashes
report["passed"] = True
(OUT / "Aurelia_validation.json").write_text(json.dumps(report,indent=2), encoding="utf-8")
print("AURELIA_VALIDATION_OK " + json.dumps(report), flush=True)
