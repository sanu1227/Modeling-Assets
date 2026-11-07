"""Reopen Charizard source and GLB and validate evaluated geometry."""
import json
import struct
from pathlib import Path

import bmesh
import bpy
import numpy as np


OUT = Path(__file__).resolve().parents[1] / 'assets' / 'Charizard'
errors = []
warnings = []


def inspect(objects, label):
    graph = bpy.context.evaluated_depsgraph_get()
    low, high = np.full(3, np.inf), np.full(3, -np.inf)
    triangles = 0
    materials = set()
    topology = []
    missing_uv = []
    degenerates = []
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
            low = np.minimum(low, world.min(axis=0))
            high = np.maximum(high, world.max(axis=0))
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
                if any(mat and mat.use_nodes and any(node.type == 'TEX_IMAGE' and node.image
                           for node in mat.node_tree.nodes) for mat in mesh.materials):
                    errors.append(f'{label}/{obj.name}: image-textured surface has no UV coordinates')
            bm = bmesh.new()
            try:
                bm.from_mesh(mesh)
                nonmanifold = sum(not edge.is_manifold for edge in bm.edges)
                inconsistent = sum(edge.is_manifold and not edge.is_contiguous for edge in bm.edges)
                if nonmanifold or inconsistent:
                    topology.append({'object': obj.name, 'nonmanifold_edges': nonmanifold,
                                     'inconsistent_winding_edges': inconsistent})
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
            'topology_details': topology, 'objects_without_uv': missing_uv}


report = {'passed': False, 'errors': errors, 'warnings': warnings,
          'limits': ['Static model; no rigging, animation or game-engine runtime validation.',
                     'Independent component intersections are not tested as a single watertight union.',
                     'Only image-textured surfaces need UV coordinates; most surfaces use solid PBR materials.',
                     'Topology counts are reported; GLB material and normal seams can split vertices.']}
try:
    bpy.ops.wm.open_mainfile(filepath=str(OUT / 'Charizard.blend'))
    collection = bpy.data.collections.get('Charizard')
    if collection is None:
        raise ValueError('Missing Charizard model collection')
    source_objects = [obj for obj in collection.all_objects if obj.type == 'MESH']
    report['source'] = inspect(source_objects, 'source')
    report['source']['armatures'] = sum(obj.type == 'ARMATURE' for obj in collection.all_objects)
    eye_material = bpy.data.materials.get('06 • Painted eye')
    eye_images = ([node.image for node in eye_material.node_tree.nodes
                   if node.type == 'TEX_IMAGE' and node.image]
                  if eye_material and eye_material.use_nodes else [])
    report['source']['packed_eye_images'] = [
        {'name': image.name, 'size': list(image.size), 'packed': bool(image.packed_file)}
        for image in eye_images]
    if not eye_images or not all(image.packed_file and image.packed_file.size > 0
                                and min(image.size) > 0 for image in eye_images):
        errors.append('Source eye material is missing a packed image')

    raw = (OUT / 'Charizard.glb').read_bytes()
    magic, version, size = struct.unpack_from('<III', raw)
    if magic != 0x46546C67 or version != 2 or size != len(raw):
        raise ValueError('Invalid GLB header')
    length, kind = struct.unpack_from('<II', raw, 12)
    if kind != 0x4E4F534A or length > len(raw) - 20:
        raise ValueError('Invalid GLB JSON chunk')
    gltf = json.loads(raw[20:20 + length])
    if gltf.get('cameras') or gltf.get('extensions', {}).get('KHR_lights_punctual'):
        errors.append('Presentation cameras or lights present in GLB')
    if any('uri' in image for image in gltf.get('images', [])):
        errors.append('GLB requires external image files')
    gltf_eye = next((mat for mat in gltf.get('materials', [])
                     if mat.get('name') == '06 • Painted eye'), {})
    eye_texture = gltf_eye.get('pbrMetallicRoughness', {}).get('baseColorTexture', {})
    embedded_eye = False
    if 'index' in eye_texture:
        texture = gltf['textures'][eye_texture['index']]
        image = gltf['images'][texture['source']]
        embedded_eye = 'bufferView' in image and 'uri' not in image
    if not embedded_eye:
        errors.append('GLB eye material is missing its embedded base-color image')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(OUT / 'Charizard.glb'))
    imported = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    report['glb'] = inspect(imported, 'glb')
    report['glb']['file_bytes'] = len(raw)
    report['glb']['embedded_eye_texture'] = embedded_eye
    report['glb']['armatures'] = sum(obj.type == 'ARMATURE' for obj in bpy.context.scene.objects)
    if any(obj.type in {'CAMERA', 'LIGHT'} for obj in bpy.context.scene.objects):
        errors.append('Imported GLB contains cameras or lights')
    if report['source']['triangles'] != report['glb']['triangles']:
        errors.append('GLB triangle count differs from evaluated source')
    source_bounds, glb_bounds = report['source']['bounds_m'], report['glb']['bounds_m']
    if source_bounds and glb_bounds:
        delta = max(abs(a - b) for key in ('min', 'max')
                    for a, b in zip(source_bounds[key], glb_bounds[key]))
        report['glb']['max_bounds_difference_m'] = delta
        if delta > 1e-4:
            errors.append('GLB bounds differ from source by more than 0.0001 m')
    if report['source']['armatures'] or report['glb']['armatures']:
        warnings.append('Unexpected armature present; rigging behavior is not validated')
except Exception as exc:
    errors.append(f'{type(exc).__name__}: {exc}')

report['passed'] = not errors
(OUT / 'Charizard_validation.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
print(json.dumps({'passed': report['passed'], 'errors': errors,
                  'source_triangles': report.get('source', {}).get('triangles'),
                  'glb_triangles': report.get('glb', {}).get('triangles')}, indent=2), flush=True)
assert report['passed'], 'See assets/Charizard/Charizard_validation.json'
print('CHARIZARD_VERIFY_OK', flush=True)
