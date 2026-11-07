"""Validate saved Buizel geometry, materials, GLB roundtrip and prior assets."""
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path

import bmesh
import bpy
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'Buizel'
errors = []
warnings = []


def image_nodes(material):
    return ([node for node in material.node_tree.nodes
             if node.type == 'TEX_IMAGE' and node.image]
            if material and material.use_nodes else [])


def inspect(objects, label):
    graph = bpy.context.evaluated_depsgraph_get()
    low, high = np.full(3, np.inf), np.full(3, -np.inf)
    triangles = 0
    materials = set()
    topology, missing_uv, degenerates = [], [], []
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            if mesh is None or not mesh.vertices:
                errors.append(f'{label}/{obj.name}: empty geometry')
                continue
            vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
            mesh.vertices.foreach_get('co', vertices)
            transform = np.asarray(evaluated.matrix_world)
            world = vertices.reshape(-1, 3) @ transform[:3, :3].T + transform[:3, 3]
            if not np.isfinite(world).all():
                errors.append(f'{label}/{obj.name}: nonfinite world coordinates')
                continue
            low, high = np.minimum(low, world.min(axis=0)), np.maximum(high, world.max(axis=0))
            mesh.calc_loop_triangles()
            count = len(mesh.loop_triangles)
            triangles += count
            if not count:
                errors.append(f'{label}/{obj.name}: no triangles')
            else:
                indices = np.empty(count * 3, dtype=np.int32)
                mesh.loop_triangles.foreach_get('vertices', indices)
                points = world[indices.reshape(-1, 3)]
                area = np.linalg.norm(np.cross(points[:, 1] - points[:, 0],
                                               points[:, 2] - points[:, 0]), axis=1) * .5
                bad = int(np.count_nonzero(area < 1e-12))
                if bad:
                    degenerates.append({'object': obj.name, 'triangles': bad})
            if not mesh.materials or any(mat is None for mat in mesh.materials):
                errors.append(f'{label}/{obj.name}: missing material slot')
            if any(face.material_index >= len(mesh.materials) for face in mesh.polygons):
                errors.append(f'{label}/{obj.name}: invalid face material index')
            materials.update(mat.name for mat in mesh.materials if mat)
            if not mesh.uv_layers:
                missing_uv.append(obj.name)
                if any(image_nodes(mat) for mat in mesh.materials):
                    errors.append(f'{label}/{obj.name}: image-textured surface has no UV coordinates')
            else:
                for layer in mesh.uv_layers:
                    if not all(np.isfinite(item.uv).all() for item in layer.data):
                        errors.append(f'{label}/{obj.name}: nonfinite UV coordinates')
            bm = bmesh.new()
            try:
                bm.from_mesh(mesh)
                nonmanifold = sum(not edge.is_manifold for edge in bm.edges)
                boundary = sum(edge.is_boundary for edge in bm.edges)
                inconsistent = sum(edge.is_manifold and not edge.is_contiguous for edge in bm.edges)
                if nonmanifold or inconsistent:
                    topology.append({'object': obj.name, 'nonmanifold_edges': nonmanifold,
                                     'boundary_edges': boundary, 'inconsistent_winding_edges': inconsistent})
            finally:
                bm.free()
        finally:
            evaluated.to_mesh_clear()
    if not triangles:
        errors.append(f'{label}: no model triangles')
    if degenerates:
        errors.append(f'{label}: degenerate triangles present')
    bounds = None
    if np.isfinite(low).all() and np.isfinite(high).all():
        bounds = {'min': low.tolist(), 'max': high.tolist(), 'size': (high - low).tolist()}
    return {'objects': len(objects), 'triangles': triangles, 'materials': sorted(materials),
            'bounds_m': bounds, 'degenerate_triangles': degenerates,
            'nonmanifold_edges': sum(item['nonmanifold_edges'] for item in topology),
            'boundary_edges': sum(item['boundary_edges'] for item in topology),
            'topology_details': topology, 'objects_without_uv': missing_uv}


def texture_infos(value):
    """Find core and extension material texture references in glTF JSON."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key.endswith('Texture') and isinstance(child, dict) and 'index' in child:
                yield child
            else:
                yield from texture_infos(child)
    elif isinstance(value, list):
        for child in value:
            yield from texture_infos(child)


report = {'passed': False, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
          'errors': errors, 'warnings': warnings,
          'limits': ['Static model; no rigging, animation or game-engine runtime validation.',
                     'Independent component intersections are not tested as a single watertight union.',
                     'Image-textured surfaces require UV coordinates; solid PBR surfaces do not.',
                     'GLB material, UV and normal seams can split vertices; topology counts are reported.']}
try:
    snapshot = json.loads((OUT / 'preserved_assets.json').read_text(encoding='utf-8-sig'))
    preserved = {}
    for relative, expected in snapshot['sha256'].items():
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        preserved[relative] = {'expected_sha256': expected, 'actual_sha256': actual,
                               'unchanged': actual == expected}
        if actual != expected:
            errors.append(f'Prior asset changed: {relative}')
    report['preserved_assets'] = preserved
    report['previous_assets_unchanged'] = bool(preserved) and all(item['unchanged'] for item in preserved.values())

    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Buizel.blend'))
    collection = bpy.data.collections.get('Buizel')
    if collection is None:
        raise ValueError('Missing Buizel model collection')
    source_objects = [obj for obj in collection.all_objects if obj.type == 'MESH']
    report['source'] = inspect(source_objects, 'source')
    report['source']['armatures'] = sum(obj.type == 'ARMATURE' for obj in collection.all_objects)
    presentation = bpy.data.collections.get('90_Presentation')
    presentation_names = {obj.name for obj in presentation.all_objects} if presentation else set()
    image_records = {}
    textured_materials = set()
    for obj in source_objects:
        for material in obj.data.materials:
            nodes = image_nodes(material)
            if nodes:
                textured_materials.add(material.name)
            for node in nodes:
                img = node.image
                image_records[img.name] = {'name': img.name, 'size': list(img.size),
                                          'packed': bool(img.packed_file and img.packed_file.size > 0)}
                if not image_records[img.name]['packed'] or min(img.size) <= 0:
                    errors.append(f'Source image not packed or invalid: {img.name}')
    report['source']['images'] = list(image_records.values())
    report['source']['textured_materials'] = sorted(textured_materials)

    raw = (OUT / 'Buizel.glb').read_bytes()
    magic, version, size = struct.unpack_from('<III', raw)
    if magic != 0x46546C67 or version != 2 or size != len(raw):
        raise ValueError('Invalid GLB header')
    length, kind = struct.unpack_from('<II', raw, 12)
    if kind != 0x4E4F534A or length > len(raw) - 20:
        raise ValueError('Invalid GLB JSON chunk')
    gltf = json.loads(raw[20:20 + length])
    if gltf.get('cameras') or gltf.get('extensions', {}).get('KHR_lights_punctual'):
        errors.append('Presentation cameras or lights present in GLB')
    leaked = presentation_names.intersection(node.get('name') for node in gltf.get('nodes', []))
    if leaked:
        errors.append(f'Presentation objects present in GLB: {sorted(leaked)}')
    gltf_images = gltf.get('images', [])
    if any('uri' in image or 'bufferView' not in image for image in gltf_images):
        errors.append('GLB image is not embedded in its buffer')
    if any('uri' in buffer for buffer in gltf.get('buffers', [])):
        errors.append('GLB requires an external buffer')
    if image_records and not gltf_images:
        errors.append('Source has image textures but GLB contains no images')
    exported_textured_materials = set()
    for gltf_mesh in gltf.get('meshes', []):
        for primitive in gltf_mesh.get('primitives', []):
            material_index = primitive.get('material')
            if material_index is None:
                errors.append('GLB primitive has no material')
                continue
            mat = gltf['materials'][material_index]
            for texture_info in texture_infos(mat):
                exported_textured_materials.add(mat.get('name', ''))
                texture = gltf['textures'][texture_info['index']]
                if 'source' not in texture or texture['source'] >= len(gltf_images):
                    errors.append('GLB texture has no valid embedded image source')
                uv_set = texture_info.get('extensions', {}).get('KHR_texture_transform', {}).get(
                    'texCoord', texture_info.get('texCoord', 0))
                if f'TEXCOORD_{uv_set}' not in primitive.get('attributes', {}):
                    errors.append(f'GLB textured primitive has no TEXCOORD_{uv_set}')
    if textured_materials - exported_textured_materials:
        errors.append(f'GLB lost image textures on materials: {sorted(textured_materials-exported_textured_materials)}')

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(OUT / 'Buizel.glb'))
    imported = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    report['glb'] = inspect(imported, 'glb')
    report['glb'].update({'file_bytes': len(raw), 'embedded_images': len(gltf_images),
                          'presentation_objects': sorted(leaked),
                          'textured_materials': sorted(exported_textured_materials),
                          'armatures': sum(obj.type == 'ARMATURE' for obj in bpy.context.scene.objects)})
    if any(obj.type in {'CAMERA', 'LIGHT'} for obj in bpy.context.scene.objects):
        errors.append('Imported GLB contains cameras or lights')
    if report['source']['triangles'] != report['glb']['triangles']:
        errors.append('GLB triangle count differs from evaluated source')
    if set(report['source']['materials']) != set(report['glb']['materials']):
        errors.append('GLB material names differ from source')
    source_bounds, glb_bounds = report['source']['bounds_m'], report['glb']['bounds_m']
    if source_bounds and glb_bounds:
        delta = max(abs(a-b) for key in ('min', 'max')
                    for a, b in zip(source_bounds[key], glb_bounds[key]))
        report['glb']['max_bounds_difference_m'] = delta
        if delta > 1e-4:
            errors.append('GLB bounds differ from source by more than 0.0001 m')
    if report['source']['armatures'] or report['glb']['armatures']:
        warnings.append('Unexpected armature present; rigging behavior is not validated')
except Exception as exc:
    errors.append(f'{type(exc).__name__}: {exc}')

report['passed'] = not errors
(OUT / 'Buizel_validation.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
print(json.dumps({'passed': report['passed'], 'errors': errors,
                  'source_triangles': report.get('source', {}).get('triangles'),
                  'glb_triangles': report.get('glb', {}).get('triangles'),
                  'previous_assets_unchanged': report.get('previous_assets_unchanged')}, indent=2), flush=True)
assert report['passed'], 'See assets/Buizel/Buizel_validation.json'
print('BUIZEL_VERIFY_OK', flush=True)
