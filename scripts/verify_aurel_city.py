"""Validate the saved city, export its portable geometry, and check a real import roundtrip."""
import json
import math
import struct
from collections import Counter
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/AurelCity'
manifest = json.loads((OUT / 'city_manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Aurel_City.blend'))
scene = bpy.context.scene
errors = []
source_objects = [o for c in scene.collection.children if not c.name.startswith('90_') for o in c.objects]
renderables = [o for o in source_objects if o.type in ('MESH', 'FONT')]
graph = bpy.context.evaluated_depsgraph_get()
mesh_cache = {}
export_meshes = {}
world_bounds = {}
total_triangles = 0
minimum, maximum = [math.inf]*3, [-math.inf]*3

for obj in renderables:
    key = (obj.data.as_pointer(), tuple((m.type, getattr(m, 'width', 0), getattr(m, 'segments', 0)) for m in obj.modifiers))
    if key not in mesh_cache:
        ev = obj.evaluated_get(graph)
        data = ev.to_mesh()
        data.calc_loop_triangles()
        if obj.type == 'MESH':
            bm = bmesh.new()
            bm.from_mesh(data)
            bad = {'degenerate_faces': sum(f.calc_area() < 1e-12 for f in bm.faces),
                   'open_or_nonmanifold_edges': sum(not e.is_manifold for e in bm.edges),
                   'inconsistent_edge_orientation': sum(e.is_manifold and not e.is_contiguous for e in bm.edges)}
            if any(bad.values()):
                errors.append({'object': obj.name, **bad})
            bm.free()
            if not data.uv_layers:
                errors.append({'object': obj.name, 'reason': 'missing UV'})
        if not data.materials or any(not math.isfinite(c) for v in data.vertices for c in v.co):
            errors.append({'object': obj.name, 'reason': 'missing materials or nonfinite geometry'})
        mesh_cache[key] = (len(data.loop_triangles), [v.co.copy() for v in data.vertices])
        export_meshes[key] = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=graph)
        ev.to_mesh_clear()
    triangles, coords = mesh_cache[key]
    total_triangles += triangles
    lo, hi = [math.inf]*3, [-math.inf]*3
    for vertex in coords:
        p = obj.matrix_world @ vertex
        for axis in range(3):
            lo[axis] = min(lo[axis], p[axis])
            hi[axis] = max(hi[axis], p[axis])
    world_bounds[obj.name] = (lo, hi)
    for axis in range(3):
        minimum[axis] = min(minimum[axis], lo[axis])
        maximum[axis] = max(maximum[axis], hi[axis])

building_bounds = {}
for item in manifest['placements']:
    parent = bpy.data.objects.get(item['name'])
    if not parent or parent.get('design') != item['design']:
        errors.append({'reason': 'missing building placement', 'name': item['name']})
        continue
    bounds = [world_bounds[o.name] for o in parent.children if o.name in world_bounds]
    lo = [min(b[0][axis] for b in bounds) for axis in range(3)]
    hi = [max(b[1][axis] for b in bounds) for axis in range(3)]
    building_bounds[parent.name] = [lo, hi]
    block = item['block']
    cx = [-184, -92, 0, 92, 184][int(block[1])-1]
    cy = [-138, -46, 46, 138][ord(block[0])-65]
    if lo[0] < cx-36.5 or hi[0] > cx+36.5 or lo[1] < cy-36.5 or hi[1] > cy+36.5:
        errors.append({'reason': 'building crosses its block boundary', 'name': parent.name})
    if abs(lo[2]-.23) > .02:
        errors.append({'reason': 'building ground mismatch', 'name': parent.name, 'bottom_z': lo[2]})

items = manifest['placements']
for i, a in enumerate(items):
    for b in items[i+1:]:
        if a['block'] != b['block']:
            continue
        aa, bb = building_bounds[a['name']], building_bounds[b['name']]
        if all(min(aa[1][k], bb[1][k])-max(aa[0][k], bb[0][k]) > 0 for k in (0, 1)):
            errors.append({'reason': 'building footprints overlap', 'names': [a['name'], b['name']]})
for x, y in manifest['people_locations']:
    if x*x+(y+46)**2 < 7**2 or (abs(x) < 9.6 and abs(y-24) < 4.2):
        errors.append({'reason': 'pedestrian placed in water', 'point': [x, y]})
assert len(items) == 34 and len(set(p['design'] for p in items)) == 8
for filename in ('city_aerial.png', 'city_avenue.png', 'city_park.png', 'city_layout.png'):
    if not (OUT / filename).exists() or (OUT / filename).stat().st_size < 10000:
        errors.append({'reason': 'missing preview', 'file': filename})

unique_triangles = sum(entry[0] for entry in mesh_cache.values())
source = {'renderable_objects': len(renderables), 'unique_evaluated_meshes': len(mesh_cache),
          'unique_triangles': unique_triangles, 'placed_triangles': total_triangles,
          'bounds_m': [minimum, maximum], 'building_design_counts': dict(Counter(p['design'] for p in items)),
          'building_heights_m': {name: round(b[1][2]-b[0][2], 3) for name, b in building_bounds.items()}}
print('SOURCE_CHECK', json.dumps({'triangles': total_triangles, 'unique_meshes': len(mesh_cache), 'errors': errors}), flush=True)

bpy.ops.object.select_all(action='DESELECT')
temporary = bpy.data.collections.new('EXPORT_TEMP')
scene.collection.children.link(temporary)
export_objects = []
for original in renderables:
    key = (original.data.as_pointer(), tuple((m.type, getattr(m, 'width', 0), getattr(m, 'segments', 0)) for m in original.modifiers))
    obj = bpy.data.objects.new(original.name, export_meshes[key])
    temporary.objects.link(obj)
    obj.matrix_world = original.matrix_world
    obj.select_set(True)
    export_objects.append(obj)
bpy.context.view_layer.objects.active = export_objects[0]
bpy.ops.export_scene.gltf(filepath=str(OUT / 'Aurel_City.glb'), export_format='GLB', use_selection=True,
                         export_apply=False, export_cameras=False, export_lights=False, export_animations=False)
raw = (OUT / 'Aurel_City.glb').read_bytes()
magic, version, length = struct.unpack_from('<III', raw)
json_length, kind = struct.unpack_from('<II', raw, 12)
assert magic == 0x46546C67 and version == 2 and length == len(raw) and kind == 0x4E4F534A
gltf = json.loads(raw[20:20+json_length])
if len(gltf.get('meshes', [])) > len(mesh_cache):
    errors.append({'reason': 'shared mesh data was duplicated during export'})
if any('uri' in image for image in gltf.get('images', [])):
    errors.append({'reason': 'external image dependency in GLB'})
if gltf.get('cameras') or 'KHR_lights_punctual' in gltf.get('extensions', {}):
    errors.append({'reason': 'presentation rig exported'})
if any('Studio_ground' in node.get('name', '') for node in gltf.get('nodes', [])):
    errors.append({'reason': 'studio ground exported'})

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(OUT / 'Aurel_City.glb'))
lo2, hi2 = [math.inf]*3, [-math.inf]*3
roundtrip_triangles = 0
imported = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for obj in imported:
    obj.data.calc_loop_triangles()
    roundtrip_triangles += len(obj.data.loop_triangles)
    for vertex in obj.data.vertices:
        p = obj.matrix_world @ vertex.co
        for axis in range(3):
            lo2[axis] = min(lo2[axis], p[axis])
            hi2[axis] = max(hi2[axis], p[axis])
delta = max(abs(a-b) for lhs, rhs in ((minimum, lo2), (maximum, hi2)) for a, b in zip(lhs, rhs))
if roundtrip_triangles != total_triangles or delta > .002:
    errors.append({'reason': 'GLB geometry roundtrip mismatch', 'triangles': roundtrip_triangles, 'bounds_delta': delta})

with bpy.data.libraries.load(str(OUT / 'Aurel_Building_Kit.blend'), link=False) as (available, imported_kit):
    names = [name for name in available.collections if name.startswith('KIT_')]
    imported_kit.collections = names.copy()
if len(imported_kit.collections) != 8 or any(not c or len(c.objects) < 2 for c in imported_kit.collections):
    errors.append({'reason': 'building kit cannot be appended', 'collections': names})

report = {'passed': not errors, 'city': manifest['city'], 'building_count': 34, 'design_count': 8,
          'source': source, 'glb': {'bytes': len(raw), 'unique_meshes': len(gltf.get('meshes', [])),
          'placed_mesh_objects': len(imported), 'triangles': roundtrip_triangles,
          'max_bounds_difference_m': delta, 'embedded_images': len(gltf.get('images', []))},
          'kit_collections': names, 'errors': errors,
          'limits': ['Static exterior city. New buildings use shallow window bays, not walkable complete interiors.',
                     'No engine-specific LOD, collisions, traffic simulation or FPS benchmark.',
                     'GLB glass appearance depends on importer support for KHR_materials_transmission.']}
(OUT / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2), flush=True)
assert not errors, 'AUREL city validation failed'
print('AUREL_CITY_VERIFY_OK', flush=True)
