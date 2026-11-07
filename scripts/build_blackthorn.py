"""Build and verify Blackthorn, an engine-neutral realistic game longsword.

Run with the workspace Blender: --background --factory-startup --python this_file
Only assets/Weapons/Blackthorn is written. Dimensions are in metres.
"""
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
OUT = ROOT / "assets" / "Weapons" / "Blackthorn"
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
asset_collection.name = "Blackthorn - game mesh"
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
    ((0.63, 0.66, 0.69), 0.28, 1.0),
    ((0.105, 0.125, 0.15), 0.36, 1.0),
    ((0.068, 0.021, 0.009), 0.67, 0.0),
    ((0.50, 0.32, 0.125), 0.34, 1.0),
]):
    cloud = smooth_noise(n, 80)
    fine = smooth_noise(n, 2.5)
    grain = smooth_noise(n, 7)
    scratches = np.zeros((n, n), np.float32)
    for _ in range(240 if tile != 2 else 65):
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
        height = fine * 0.0015 + brushed * 0.002 - scratches * 0.022
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
    "BaseColor": save_image("Blackthorn_BaseColor", base, True),
    "Roughness": save_image("Blackthorn_Roughness", rough),
    "Metallic": save_image("Blackthorn_Metallic", metal),
    "Normal": save_image("Blackthorn_Normal", normal),
}
material = bpy.data.materials.new("M_Blackthorn_PBR_2K")
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
    rings = []
    for i, point in enumerate(points):
        tangent = (points[min(i+1, len(points)-1)] - points[max(0, i-1)]).normalized()
        axis = Vector((0, 1, 0))
        if abs(tangent.dot(axis)) > .95:
            axis = Vector((1, 0, 0))
        right = tangent.cross(axis).normalized()
        up = tangent.cross(right).normalized()
        rings.append([point + radius*(right*math.cos(j*math.tau/sides) + up*math.sin(j*math.tau/sides))
                      for j in range(sides)])
    return rings_mesh(name, rings, tile, smooth=True)


# Double-edged blade: real recessed fuller, broad polished cutting bevels,
# distal taper, an unsharpened ricasso, and one welded tip vertex.
profile = [(-1, .025), (-.72, .8), (-.34, 1), (-.24, .61),
           (0, .55), (.24, .61), (.34, 1), (.72, .8), (1, .025)]
sections = [(0.006, .028, .0042, 0), (.061, .028, .0042, 0),
            (.082, .0276, .0041, .35), (.111, .027, .0040, 1),
            (.51, .0228, .0033, 1), (.69, .0192, .0028, .8),
            (.77, .0167, .0024, 0), (.855, .0093, .0016, 0),
            (.900, .0037, .0008, 0)]
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
vertices.append((0, 0, .927))
for j in range(count):
    faces.append(((len(blade_rings)-1)*count+j,
                  (len(blade_rings)-1)*count+(j+1)%count, tip))
blade = mesh("01_Blade_fuller_and_ricasso", vertices, faces, 0)
for polygon in blade.data.polygons:
    polygon.use_smooth = polygon.index >= count
for edge in blade.data.edges:
    a, b = edge.vertices
    edge.use_edge_sharp = (a < root_center and b < root_center and a//count != b//count)

# Swept octagonal guard; thick at the centre, tapered at its downturned ends.
guard_rings = []
for x, z, rz, ry in [(-.145,-.042,.008,.007),(-.137,-.038,.011,.009),
                     (-.108,-.019,.009,.009),(-.064,-.004,.011,.011),
                     (0,0,.016,.014),(.064,-.004,.011,.011),
                     (.108,-.019,.009,.009),(.137,-.038,.011,.009),
                     (.145,-.042,.008,.007)]:
    guard_rings.append([(x, ry*math.cos(math.tau*j/8+math.pi/8),
                        z+rz*math.sin(math.tau*j/8+math.pi/8)) for j in range(8)])
rings_mesh("02_Swept_blackened_crossguard", guard_rings, 1, .0008, True)
plaque("03_Guard_centre", [(-.027,-.004),(-.020,.015),(0,.023),(.020,.015),
                            (.027,-.004),(.017,-.025),(0,-.033),(-.017,-.025)],
       .028, 1, bevel=.0012)
for side in (-1, 1):
    # A narrow inset-looking warm metal line is the only guard ornament.
    tube(f"04_Guard_inlay_{side}",
         [(x, side*y, z) for x,y,z in [(-.126,.0091,-.030),(-.098,.011,-.015),
                                      (-.060,.012,-.001),(-.030,.014,.003)]], .00055, 3)
    tube(f"04_Guard_inlay_R_{side}",
         [(-x, side*y, z) for x,y,z in [(-.126,.0091,-.030),(-.098,.011,-.015),
                                       (-.060,.012,-.001),(-.030,.014,.003)]], .00055, 3)
    plaque(f"05_Centre_silver_shield_{side}", [(0,.013),(.011,.004),(.008,-.011),
             (0,-.021),(-.008,-.011),(-.011,.004)], .0011, 0,
           center_y=side*.0146, bevel=.0005)
    # Small maker's diamond, physically inset-style and visible from both sides.
    tube(f"06_Maker_mark_{side}", [(0,side*.00435,.057),(.003,side*.004,.048),
          (0,side*.00435,.039),(-.003,side*.004,.048),(0,side*.00435,.057)], .00035, 1)

# Grip core and ferrules. The grip narrows at the pommel and has a slight waist.
oval("07_Leather_grip_core", [(-.247,.0138,.011),(-.220,.0144,.0115),
     (-.150,.0152,.012),(-.082,.0172,.013),(-.034,.0182,.0134)], 2, 24, smooth=True)
for z, rx, ry in [(-.034,.0192,.0144),(-.247,.0150,.0123)]:
    oval("08_Blackened_grip_ferrule", [(z-.006,rx,ry),(z+.006,rx,ry)], 1, 16, .0006, True)
    for zz in (z-.0041,z+.0041):
        oval("09_Ferrule_brass_hairline", [(zz-.0006,rx+.00025,ry+.00025),
             (zz+.0006,rx+.00025,ry+.00025)], 3, 16, .0002, True)

# A single continuous leather ribbon; rounded lip and a shallow helical seam.
rings = []
turns, steps = 17, 17*40
pitch = .199/turns
for i in range(steps+1):
    f = i/steps
    angle = f*turns*math.tau
    z = -.239 + f*.199
    rx = .014 + f*.0042
    ry = .0113 + f*.0021
    section = [(-.0002,-pitch*.48),(.00065,-pitch*.40),(.00095,-pitch*.28),
               (.00095,pitch*.34),(.00045,pitch*.49),(-.0002,pitch*.49)]
    rings.append([((rx+radial)*math.cos(angle),(ry+radial)*math.sin(angle),z+dz)
                  for radial,dz in section])
rings_mesh("10_Continuous_leather_wrap", rings, 2, smooth=True)

# Faceted scent-stopper pommel with a restrained steel cap and brass collars.
oval("11_Faceted_pommel", [(-.309,.009,.008),(-.302,.0185,.0145),
     (-.280,.023,.017),(-.265,.021,.016),(-.254,.014,.011),(-.250,.0135,.0105)],
     1, 12, .0008, True)
oval("12_Pommel_steel_crown", [(-.310,.008,.007),(-.306,.014,.011),
     (-.301,.0187,.0147)], 0, 12, .0004, True)
oval("13_Pommel_brass_seam", [(-.299,.0193,.0151),(-.297,.020,.0156)], 3, 12, .0002, True)
for side in (-1, 1):
    plaque(f"14_Pommel_silver_lozenge_{side}", [(0,-.265),(.006,-.277),
        (0,-.290),(-.006,-.277)], .0007, 0, center_y=side*.0166, bevel=.0001)

# One game mesh and material. Named vertex groups preserve part selection.
active(blade)
for obj in parts:
    obj.select_set(True)
bpy.ops.object.join()
sword = bpy.context.object
sword.name = "SM_Blackthorn_Longsword"
for vertex in sword.data.vertices:
    vertex.co.z += .135
scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
sword["asset_name"] = "Blackthorn / 흑가시"
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


set_view((.20,-2.6,.85), (0,0,.438), 1.48, (1100,1700), -.20)
for obj in preview.objects:
    obj.hide_set(True)
active(sword)
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        space = area.spaces.active
        space.region_3d.view_location = Vector((0,0,.43))
        space.region_3d.view_distance = 1.65
        space.region_3d.view_rotation = camera.rotation_euler.to_quaternion()
        space.shading.type = "MATERIAL"
        space.overlay.show_overlays = False
        space.clip_end = 100
scene.render.filepath = str(OUT / "Blackthorn_hero.png")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Blackthorn.blend"))
bpy.ops.export_scene.gltf(filepath=str(OUT / "Blackthorn_game.glb"), export_format="GLB",
    use_selection=True, export_materials="EXPORT", export_animations=False,
    export_yup=True, export_apply=True, export_texcoords=True, export_normals=True,
    export_tangents=True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "Blackthorn_game.fbx"), use_selection=True,
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
assert report["triangles"] < 18000, report
assert len(sword.data.materials) == 1
assert all(math.isfinite(value) for vertex in sword.data.vertices for value in vertex.co)
assert all(triangle.area > 1e-12 for triangle in sword.data.loop_triangles)
assert 1.23 < sword.dimensions.z < 1.25
assert sword.location.length < 1e-7
assert all(abs(value-1) < 1e-6 for value in sword.scale)
assert len(sword.data.uv_layers) == 1
print("BLACKTHORN_GEOMETRY_OK " + json.dumps(report), flush=True)

render("Blackthorn_hero.png", (.20,-2.6,.85), (0,0,.438), 1.48, (1100,1700), -.20)
render("Blackthorn_detail.png", (.25,-1.8,.25), (0,0,-.006), .49, (1400,1400), -.15)
render("Blackthorn_front.png", (0,-3,.438), (0,0,.438), 1.40, (1000,1700))
render("Blackthorn_side.png", (2.6,-.7,.55), (0,0,.438), 1.42, (900,1500))

# Inspect exported structure and reimport each actual deliverable into a clean scene.
glb = (OUT / "Blackthorn_game.glb").read_bytes()
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
    path = str(OUT / ("Blackthorn_game."+extension))
    if extension == "glb":
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.import_scene.fbx(filepath=path)
    bpy.context.view_layer.update()
    objects = [obj for obj in scene.objects if obj.type == "MESH"]
    assert len(objects) == 1
    obj = objects[0]
    corners = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    size = [max(p[a] for p in corners)-min(p[a] for p in corners) for a in range(3)]
    assert all(abs(a-b)<1e-4 for a,b in zip(size,report["dimensions_m"])), (extension,size)
    obj.data.calc_loop_triangles()
    assert len(obj.data.loop_triangles) == report["triangles"]
    assert obj.matrix_world.translation.length < 1e-5
    assert len(obj.data.uv_layers) == 1 and len(obj.data.materials) == 1
    report["roundtrip"][extension] = {"passed": True, "dimensions_m": size,
        "triangles": len(obj.data.loop_triangles), "uv_layers": 1, "material_count": 1}

bpy.ops.wm.open_mainfile(filepath=str(OUT / "Blackthorn.blend"))
obj = bpy.data.objects.get("SM_Blackthorn_Longsword")
assert obj and obj.location.length < 1e-7
assert all(bpy.data.images.get("Blackthorn_"+channel).packed_file for channel in images)
report["saved_blend_reopened"] = True
report["packed_pbr_textures"] = True
report["passed"] = True
(OUT / "Blackthorn_validation.json").write_text(json.dumps(report,indent=2), encoding="utf-8")
print("BLACKTHORN_VALIDATION_OK " + json.dumps(report), flush=True)
