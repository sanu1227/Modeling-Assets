"""Reopen source, validate geometry, then import and compare the delivered GLB."""
import json
import math
import struct
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

OUT = Path(__file__).resolve().parents[1] / 'assets' / 'MedievalShop'
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'MedievalShop.blend'))
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH'
           and any(c.name != '90_Presentation' for c in o.users_collection)]
errors = []
warnings = []
unique = set()
evaluated_triangles = 0
degenerate_count = 0
boundary_count = 0
bad_normals = 0
depsgraph = bpy.context.evaluated_depsgraph_get()


def bounds(items):
    # Rotated group bounding boxes overestimate the joined model. Compare actual vertices.
    graph = bpy.context.evaluated_depsgraph_get()
    low, high = [math.inf]*3, [-math.inf]*3
    for obj in items:
        evaluated = obj.evaluated_get(graph)
        data = evaluated.to_mesh()
        for vertex in data.vertices:
            co = evaluated.matrix_world @ vertex.co
            for i in range(3):
                low[i] = min(low[i], co[i])
                high[i] = max(high[i], co[i])
        evaluated.to_mesh_clear()
    return {'min': low, 'max': high, 'size': [b-a for a, b in zip(low, high)]}


for obj in objects:
    if not obj.data.uv_layers:
        errors.append(obj.name + ': missing UV')
    if not obj.data.materials or any(m is None for m in obj.data.materials):
        errors.append(obj.name + ': missing material')
    if not all(math.isfinite(value) for v in obj.data.vertices for value in v.co):
        errors.append(obj.name + ': nonfinite coordinate')
    if obj.data not in unique:
        unique.add(obj.data)
        copy = obj.data.copy()
        if copy.validate(clean_customdata=False):
            errors.append(obj.name + ': invalid base mesh')
        bpy.data.meshes.remove(copy)
    evaluated = obj.evaluated_get(depsgraph)
    data = evaluated.to_mesh()
    data.calc_loop_triangles()
    evaluated_triangles += len(data.loop_triangles)
    degenerates = sum(p.area < 1e-12 for p in data.polygons)
    degenerate_count += degenerates
    if degenerates:
        errors.append(obj.name + ': degenerate faces ' + str(degenerates))
    bm = bmesh.new()
    bm.from_mesh(data)
    boundary = sum(not e.is_manifold for e in bm.edges)
    boundary_count += boundary
    inconsistent = sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
    bad_normals += inconsistent
    if boundary:
        errors.append(obj.name + ': nonmanifold edges ' + str(boundary))
    if inconsistent:
        errors.append(obj.name + ': inconsistent face orientation')
    bm.free()
    evaluated.to_mesh_clear()

original_bounds = bounds(objects)
images = [im for im in bpy.data.images if im.name.endswith('_BaseColor')]
if not all(im.packed_file for im in images):
    errors.append('Unpacked material images')
source = {
    'mesh_objects': len(objects), 'unique_base_meshes': len(unique),
    'linked_mesh_instances_saved': len(objects)-len(unique),
    'evaluated_triangles': evaluated_triangles,
    'materials': len({m.name for o in objects for m in o.data.materials if m}),
    'packed_base_color_images': len(images),
    'bounds_m': original_bounds,
    'degenerate_faces': degenerate_count,
    'nonmanifold_edges': boundary_count,
    'inconsistent_normal_edges': bad_normals,
}

# Read the GLB manifest to verify export scope and embedded textures.
raw = (OUT / 'MedievalShop.glb').read_bytes()
magic, version, total = struct.unpack_from('<III', raw, 0)
assert magic == 0x46546C67 and version == 2 and total == len(raw)
length, kind = struct.unpack_from('<II', raw, 12)
assert kind == 0x4E4F534A
gltf = json.loads(raw[20:20+length])
if gltf.get('cameras') or 'KHR_lights_punctual' in gltf.get('extensions', {}):
    errors.append('Presentation cameras/lights leaked into GLB')
if any('Studio_ground' in n.get('name','') or 'Courtyard_cobble' in n.get('name','') for n in gltf.get('nodes', [])):
    errors.append('Presentation ground leaked into GLB')
if any('uri' in i for i in gltf.get('images', [])):
    errors.append('GLB has external image dependencies')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(OUT / 'MedievalShop.glb'))
imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']
triangles = 0
for obj in imported:
    obj.data.calc_loop_triangles()
    triangles += len(obj.data.loop_triangles)
    if not obj.data.uv_layers or not obj.data.materials:
        errors.append('GLB lost UV/material: ' + obj.name)
import_bounds = bounds(imported)
delta = max(abs(a-b) for key in ('min','max') for a,b in zip(original_bounds[key],import_bounds[key]))
if len(imported) != 6:
    errors.append('GLB must contain six combined exterior groups')
if triangles != evaluated_triangles:
    errors.append('GLB triangle count mismatch')
if delta > .005:
    errors.append('GLB bounds mismatch exceeds 5 mm')
for file in ('preview_front.png', 'preview_back.png'):
    im = bpy.data.images.load(str(OUT / file), check_existing=False)
    if min(im.size) < 1000:
        errors.append(file + ': low resolution')
report = {
    'passed': not errors,
    'source': source,
    'glb': {'mesh_objects':len(imported), 'triangles':triangles,
            'bounds_m':import_bounds, 'max_bounds_difference_m':delta,
            'embedded_images':len(gltf.get('images',[])), 'file_bytes':len(raw)},
    'errors':errors,
    'limits':['Exterior only; no interiors or architectural construction validation.',
              'Tiled surface UVs; no lightmap UV, LOD, collision, engine runtime test.',
              'GLB base color/metallic/roughness exported; Blender bump not baked.',
              'Separate intersecting closed parts are intentional; no watertight union claim.'],
}
(OUT / 'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report,indent=2,ensure_ascii=False),flush=True)
assert not errors, 'Model verification failed; see validation.json'
print('MEDIEVAL_SHOP_VERIFY_OK',flush=True)
