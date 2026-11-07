"""Build a small, editable game crate with Blender's bundled Python.

Run: blender --background --factory-startup --python scripts/create_crate.py
Outputs stay in assets/Crate. No third-party Python packages are required.
"""
import json
import math
import struct
import tempfile
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "Crate"
TEXTURES = OUT / "Textures"
TEXTURES.mkdir(parents=True, exist_ok=True)
# Keep exporter scratch images inside the writable project directory.
scratch = OUT / ".export_temp"
scratch.mkdir(exist_ok=True)
tempfile.tempdir = str(scratch)
bpy.context.preferences.filepaths.temporary_directory = str(scratch)
rng = np.random.default_rng(3184)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0

# Long fibers run vertically in texture space. UVs align them with each board.
size = 1024
v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
warp = 0.011 * np.sin(v * 15.0 + np.sin(u * 9.0))
warp += 0.004 * np.sin(v * 41.0 + u * 17.0)
fiber = np.sin((u + warp) * math.tau * 57.0)
fiber2 = np.sin((u + warp * 0.7) * math.tau * 133.0)
broad = np.sin(u * math.tau * 8.0 + np.sin(v * 8.0) * 0.4)
noise = rng.normal(0, 0.011, (size, size)).astype(np.float32)
grain = 0.038 * fiber + 0.016 * fiber2 + 0.047 * broad + noise
# Small elongated knots add variation without painted lighting or fake shadows.
for ku, kv, strength in [(0.23, 0.38, 0.10), (0.71, 0.76, 0.075)]:
    radius = np.sqrt(((u - ku) / 0.027) ** 2 + ((v - kv) / 0.10) ** 2)
    grain -= strength * np.exp(-radius * radius)
    grain += 0.018 * np.cos(radius * 15) * np.exp(-radius * 0.8)
wood_rgb = np.clip(np.array([0.49, 0.265, 0.105]) + grain[:, :, None]
                   * np.array([1.0, 0.67, 0.32]), 0.035, 0.85)


def save_image(name, rgb, filename, non_color=False):
    image = bpy.data.images.new(name, width=size, height=size, alpha=True)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    pixels = np.ones((size, size, 4), dtype=np.float32)
    pixels[:, :, :3] = rgb
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw = str(TEXTURES / filename)
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image


base_image = save_image("Crate_Wood_BaseColor", wood_rgb, "Crate_Wood_BaseColor.png")
rough = np.clip(0.76 + grain * 0.5, 0.63, 0.88)
rough_image = save_image("Crate_Wood_Roughness", np.repeat(rough[:, :, None], 3, axis=2),
                         "Crate_Wood_Roughness.png", True)

wood = bpy.data.materials.new("M_Crate_Wood")
wood.use_nodes = True
nodes = wood.node_tree.nodes
principled = nodes.get("Principled BSDF")
principled.inputs["Roughness"].default_value = 0.76
base_node = nodes.new("ShaderNodeTexImage")
base_node.image = base_image
base_node.location = (-500, 160)
rough_node = nodes.new("ShaderNodeTexImage")
rough_node.image = rough_image
rough_node.location = (-500, -130)
wood.node_tree.links.new(base_node.outputs["Color"], principled.inputs["Base Color"])
wood.node_tree.links.new(rough_node.outputs["Color"], principled.inputs["Roughness"])

iron = bpy.data.materials.new("M_Crate_Iron")
iron.use_nodes = True
iron_bsdf = iron.node_tree.nodes.get("Principled BSDF")
iron_bsdf.inputs["Base Color"].default_value = (0.055, 0.065, 0.075, 1)
iron_bsdf.inputs["Metallic"].default_value = 0.7
iron_bsdf.inputs["Roughness"].default_value = 0.38


def board(name, dimensions, location, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    uv_layer = obj.data.uv_layers.active
    if uv_layer is None:
        uv_layer = obj.data.uv_layers.new(name="UVMap")
    offset_u, offset_v = rng.uniform(0.0, 0.6, 2)
    for face in obj.data.polygons:
        normal_axis = max(range(3), key=lambda axis: abs(face.normal[axis]))
        axes = [axis for axis in range(3) if axis != normal_axis]
        long_axis = max(axes, key=lambda axis: dimensions[axis])
        short_axis = next(axis for axis in axes if axis != long_axis)
        for loop_index in face.loop_indices:
            co = obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
            uv_layer.data[loop_index].uv = (
                (co[short_axis] / dimensions[short_axis] + 0.5) * 0.30 + offset_u,
                (co[long_axis] / dimensions[long_axis] + 0.5) * 0.82 + offset_v,
            )
    obj.rotation_euler = rotation
    obj.data.materials.append(wood)
    return obj


# Preserve the starting blockout separately, before detail and bevel edits.
source = board("Crate_Source_Blockout", (1, 1, 1), (0, 0, 0.5))
scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
source["stage"] = "Original 1 m cube before plank, frame, bevel, and nail edits"
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Crate_source.blend"))
bpy.data.objects.remove(source, do_unlink=True)

wood_parts = []
# Closed side panels: five boards per face, with thin readable seams.
for index in range(5):
    offset = (index - 2) * 0.178
    for sign in (-1, 1):
        wood_parts.append(board(f"Panel_Y{sign}_{index}", (0.174, 0.065, 0.80),
                                (offset, sign * 0.4275, 0.5)))
        wood_parts.append(board(f"Panel_X{sign}_{index}", (0.065, 0.174, 0.80),
                                (sign * 0.4275, offset, 0.5)))
        # End inside the surrounding rails; coplanar overlaps cause z-fighting.
        wood_parts.append(board(f"Lid_{sign}_{index}", (0.152, 0.78, 0.07),
                                ((index - 2) * 0.156, 0, 0.5 + sign * 0.465)))

for x in (-0.445, 0.445):
    for y in (-0.445, 0.445):
        wood_parts.append(board("Corner_Post", (0.11, 0.11, 1.0), (x, y, 0.5)))

for sign in (-1, 1):
    for z in (0.055, 0.945):
        wood_parts.append(board("Front_Back_Rail", (0.78, 0.10, 0.11),
                                (0, sign * 0.45, z)))
        wood_parts.append(board("Side_Rail", (0.10, 0.78, 0.11),
                                (sign * 0.45, 0, z)))

brace_length = math.hypot(0.62, 0.56)
brace_angle = math.atan2(0.56, 0.62)
for sign in (-1, 1):
    wood_parts.append(board("Front_Back_Diagonal", (brace_length, 0.06, 0.115),
                            (0, sign * 0.46, 0.5), (0, -brace_angle * sign, 0)))
    wood_parts.append(board("Side_Diagonal", (0.06, brace_length, 0.115),
                            (sign * 0.46, 0, 0.5), (brace_angle * sign, 0, 0)))

bpy.ops.object.select_all(action="DESELECT")
for obj in wood_parts:
    obj.select_set(True)
bpy.context.view_layer.objects.active = wood_parts[0]
bpy.ops.object.join()
crate = bpy.context.object
crate.name = "Crate_Game"
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bevel = crate.modifiers.new("Soft timber edges - 4 mm", "BEVEL")
bevel.width = 0.004
bevel.segments = 2
bevel.affect = "EDGES"
bpy.ops.object.modifier_apply(modifier=bevel.name)

# A few low-sided nail heads provide scale and readable construction detail.
nails = []
for sign in (-1, 1):
    for endpoint in (-1, 1):
        x = endpoint * 0.285
        z = 0.5 + endpoint * 0.257 * sign
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.014, depth=0.008,
                                           location=(x, sign * 0.494, z),
                                           rotation=(math.pi / 2, 0, 0))
        nail = bpy.context.object
        nail.name = "Forged_Nail"
        nail.data.materials.append(iron)
        nails.append(nail)
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.014, depth=0.008,
                                           location=(sign * 0.494, x, z),
                                           rotation=(0, math.pi / 2, 0))
        nail = bpy.context.object
        nail.name = "Forged_Nail"
        nail.data.materials.append(iron)
        nails.append(nail)

bpy.ops.object.select_all(action="DESELECT")
crate.select_set(True)
for nail in nails:
    nail.select_set(True)
bpy.context.view_layer.objects.active = crate
bpy.ops.object.join()
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
crate["units"] = "meters"
crate["pivot"] = "bottom center"
crate["workflow"] = "AI-authored Blender geometry; source cube preserved in Crate_source.blend"
crate["collision_hint"] = "One box collider, size 1 x 1 x 1 m, center Z 0.5 in Blender"
crate.data.calc_loop_triangles()

corners = [crate.matrix_world @ Vector(corner) for corner in crate.bound_box]
minimum = [min(corner[axis] for corner in corners) for axis in range(3)]
maximum = [max(corner[axis] for corner in corners) for axis in range(3)]
dimensions = [maximum[axis] - minimum[axis] for axis in range(3)]
assert all(abs(value - 1.0) < 0.00001 for value in dimensions), dimensions
assert all(abs(value) < 0.00001 for value in crate.location), list(crate.location)
assert abs(minimum[2]) < 0.00001, minimum
assert all(abs(value - 1.0) < 0.00001 for value in crate.scale)
assert len(crate.data.uv_layers) == 1
assert len(crate.data.loop_triangles) < 15000

asset_collection = crate.users_collection[0]
asset_collection.name = "Game Asset"
render_collection = bpy.data.collections.new("Preview Only - excluded from exports")
scene.collection.children.link(render_collection)


def move_to_preview(obj):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    render_collection.objects.link(obj)


floor_material = bpy.data.materials.new("Preview_Floor")
floor_material.diffuse_color = (0.115, 0.14, 0.155, 1)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.008))
floor = bpy.context.object
floor.name = "Preview_Floor"
floor.data.materials.append(floor_material)
move_to_preview(floor)

for name, location, energy, light_size, color in [
    ("Key", (2.6, -3.7, 4.8), 550, 4.0, (1.0, 0.84, 0.65)),
    ("Fill", (-3.5, -1.5, 2.5), 350, 3.0, (0.70, 0.83, 1.0)),
    ("Rim", (1.0, 3.0, 3.5), 650, 2.5, (1.0, 0.92, 0.77)),
]:
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = light_size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    render_collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, 0.45)) - obj.location).to_track_quat("-Z", "Y").to_euler()

bpy.ops.object.camera_add(location=(2.25, -2.8, 2.0))
camera = bpy.context.object
camera.name = "Preview_Camera"
camera.rotation_euler = (Vector((0, 0, 0.48)) - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = 1.95
scene.camera = camera
move_to_preview(camera)

scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "Crate_preview.png")
scene.world.color = (0.22, 0.22, 0.22)
scene.view_settings.view_transform = "AgX"

bpy.ops.object.select_all(action="DESELECT")
crate.select_set(True)
bpy.context.view_layer.objects.active = crate
for area in bpy.context.screen.areas:
    if area.type == "VIEW_3D":
        area.spaces.active.region_3d.view_location = Vector((0, 0, 0.5))
        area.spaces.active.region_3d.view_distance = 2.4
        area.spaces.active.shading.type = "MATERIAL"

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Crate_work.blend"))
bpy.ops.export_scene.gltf(filepath=str(OUT / "Crate_game.glb"), export_format="GLB",
                           use_selection=True, export_materials="EXPORT",
                           export_animations=False, export_yup=True,
                           export_apply=True, export_texcoords=True,
                           export_normals=True)
bpy.ops.export_scene.fbx(filepath=str(OUT / "Crate_game.fbx"), use_selection=True,
                        object_types={"MESH"}, axis_forward="-Z", axis_up="Y",
                        global_scale=1.0, apply_unit_scale=True, bake_anim=False,
                        use_mesh_modifiers=True, path_mode="COPY", embed_textures=False,
                        mesh_smooth_type="FACE", add_leaf_bones=False)
bpy.ops.render.render(write_still=True)

report = {
    "blender_version": bpy.app.version_string,
    "creation_method": "AI-authored Blender Python; no external generative 3D service",
    "asset_mesh_count": 1,
    "vertices": len(crate.data.vertices),
    "triangles": len(crate.data.loop_triangles),
    "materials": [material.name for material in crate.data.materials],
    "uv_layers": [layer.name for layer in crate.data.uv_layers],
    "dimensions_m": dimensions,
    "world_bounds_min_m": minimum,
    "world_bounds_max_m": maximum,
    "origin_m": list(crate.location),
    "scale": list(crate.scale),
    "texture_resolution": [size, size],
    "export_excludes_preview_objects": True,
    "files": [],
}
for path in sorted(OUT.rglob("*")):
    if path.is_file() and not path.name.endswith(".blend1"):
        report["files"].append({"path": str(path.relative_to(OUT)), "bytes": path.stat().st_size})
for filename in ["Crate_source.blend", "Crate_work.blend", "Crate_game.glb", "Crate_game.fbx", "Crate_preview.png"]:
    assert (OUT / filename).stat().st_size > 1000, filename

# Re-import both deliverables. Validate the exported files, not only the source.
glb_bytes = (OUT / "Crate_game.glb").read_bytes()
json_length = struct.unpack_from("<I", glb_bytes, 12)[0]
gltf = json.loads(glb_bytes[20:20 + json_length].decode("utf-8"))
assert len(gltf["meshes"]) == 1
assert len(gltf["materials"]) == 2
assert not gltf.get("cameras")
assert all("bufferView" in image for image in gltf["images"])
report["glb_embedded_images"] = len(gltf["images"])
report["roundtrip"] = {}
for extension in ("glb", "fbx"):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    if extension == "glb":
        bpy.ops.import_scene.gltf(filepath=str(OUT / "Crate_game.glb"))
    else:
        bpy.ops.import_scene.fbx(filepath=str(OUT / "Crate_game.fbx"))
    bpy.context.view_layer.update()
    imported = [obj for obj in scene.objects if obj.type == "MESH"]
    assert len(imported) == 1, (extension, len(imported))
    imported_crate = imported[0]
    imported_corners = [imported_crate.matrix_world @ Vector(corner)
                        for corner in imported_crate.bound_box]
    low = [min(corner[axis] for corner in imported_corners) for axis in range(3)]
    high = [max(corner[axis] for corner in imported_corners) for axis in range(3)]
    imported_size = [high[axis] - low[axis] for axis in range(3)]
    assert all(abs(value - 1.0) < 0.0001 for value in imported_size), (extension, imported_size)
    assert abs(low[2]) < 0.0001, (extension, low)
    assert len(imported_crate.data.uv_layers) == 1
    assert len(imported_crate.data.materials) == 2
    report["roundtrip"][extension] = {
        "mesh_count": len(imported), "dimensions_m": imported_size,
        "bottom_z_m": low[2], "uv_layers": len(imported_crate.data.uv_layers),
        "material_count": len(imported_crate.data.materials), "passed": True,
    }
(OUT / "Crate_validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print("CRATE_VALIDATION_OK " + json.dumps(report, ensure_ascii=False))
