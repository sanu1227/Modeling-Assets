"""Validate the saved collection and each canonical GLB in one Blender process.

Run with Blender --background --factory-startup --python-exit-code 1 --python
scripts/verify_pokemon_starters.py after the source, roster and exports exist.
"""
import json
import hashlib
import struct
from datetime import datetime, timezone
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix


OUT = Path(__file__).resolve().parents[1] / 'assets' / 'PokemonStarters'
EXPECTED_MODELS = 32
AREA_EPSILON = 1e-12
BOUNDS_TOLERANCE = 1e-4
WELD_DISTANCE = 1e-6


def inspect(objects, coordinate_matrix, errors, source):
    """Measure evaluated vertices; source positions are relative to its root."""
    graph = bpy.context.evaluated_depsgraph_get()
    low, high = np.full(3, np.inf), np.full(3, -np.inf)
    triangles, vertices_count = 0, 0
    materials, used_materials = set(), set()
    missing_uv, topology, degenerates = [], [], []
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            if mesh is None or not mesh.vertices:
                errors.append(f'{obj.name}: empty mesh')
                continue
            transform = coordinate_matrix @ evaluated.matrix_world
            matrix = np.asarray(transform, dtype=np.float64)
            values = np.empty(len(mesh.vertices)*3, dtype=np.float64)
            mesh.vertices.foreach_get('co', values)
            points = values.reshape(-1, 3) @ matrix[:3, :3].T + matrix[:3, 3]
            vertices_count += len(mesh.vertices)
            if not np.isfinite(points).all():
                errors.append(f'{obj.name}: nonfinite evaluated coordinates')
                continue
            low = np.minimum(low, points.min(axis=0))
            high = np.maximum(high, points.max(axis=0))
            mesh.calc_loop_triangles()
            count = len(mesh.loop_triangles)
            triangles += count
            if not count:
                errors.append(f'{obj.name}: no triangles')
            else:
                indices = np.empty(count*3, dtype=np.int32)
                mesh.loop_triangles.foreach_get('vertices', indices)
                tri = points[indices.reshape(-1, 3)]
                areas = np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1)*.5
                bad = int(np.count_nonzero(areas <= AREA_EPSILON))
                if bad:
                    degenerates.append({'object': obj.name, 'triangles': bad})
                    errors.append(f'{obj.name}: {bad} triangles have area <= {AREA_EPSILON}')
            if not mesh.materials or any(mat is None for mat in mesh.materials):
                errors.append(f'{obj.name}: missing material slot')
            materials.update(mat.name for mat in mesh.materials if mat)
            for index in {face.material_index for face in mesh.polygons}:
                if index >= len(mesh.materials) or mesh.materials[index] is None:
                    errors.append(f'{obj.name}: invalid face material index {index}')
                else:
                    used_materials.add(mesh.materials[index].name)
            if not mesh.uv_layers:
                missing_uv.append(obj.name)
            bm = bmesh.new()
            try:
                bm.from_mesh(mesh)
                if not source:
                    # glTF splits vertices at material and normal seams. Weld only
                    # this temporary copy; never mutate imported or source data.
                    bm.transform(transform)
                    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=WELD_DISTANCE)
                nonmanifold = sum(not edge.is_manifold for edge in bm.edges)
                boundary = sum(edge.is_boundary for edge in bm.edges)
                inconsistent = sum(edge.is_manifold and not edge.is_contiguous for edge in bm.edges)
                if nonmanifold or inconsistent:
                    topology.append({'object': obj.name, 'nonmanifold_edges': nonmanifold,
                                     'boundary_edges': boundary,
                                     'inconsistent_winding_edges': inconsistent})
                    if source:
                        errors.append(f'{obj.name}: source topology has {nonmanifold} nonmanifold and '
                                      f'{inconsistent} inconsistent winding edges')
            finally:
                bm.free()
        finally:
            evaluated.to_mesh_clear()
    bounds = None
    if np.isfinite(low).all() and np.isfinite(high).all():
        bounds = {'min': low.tolist(), 'max': high.tolist(), 'size': (high-low).tolist()}
    if not triangles:
        errors.append('No model triangles')
    return {'objects': len(objects), 'vertices': vertices_count, 'triangles': triangles,
            'materials': sorted(materials), 'used_materials': sorted(used_materials),
            'bounds_m': bounds, 'degenerate_triangles': degenerates,
            'nonmanifold_edges': sum(item['nonmanifold_edges'] for item in topology),
            'inconsistent_winding_edges': sum(item['inconsistent_winding_edges'] for item in topology),
            'topology_details': topology,
            'topology_mode': 'source_components' if source else 'transient_welded_report_only',
            'objects_with_uv': len(objects)-len(missing_uv), 'objects_without_uv': missing_uv}


def read_glb(path):
    """Check the container before Blender sees it and return its glTF document."""
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError('Truncated GLB header')
    magic, version, size = struct.unpack_from('<III', raw)
    if magic != 0x46546C67 or version != 2 or size != len(raw):
        raise ValueError('Invalid GLB magic, version or declared size')
    length, kind = struct.unpack_from('<II', raw, 12)
    if kind != 0x4E4F534A or length > len(raw)-20 or length % 4:
        raise ValueError('Invalid GLB JSON chunk')
    document = json.loads(raw[20:20+length])
    offset = 12
    chunks = []
    while offset < len(raw):
        if len(raw)-offset < 8:
            raise ValueError('Truncated GLB chunk header')
        chunk_length, chunk_kind = struct.unpack_from('<II', raw, offset)
        offset += 8
        if chunk_length % 4 or offset+chunk_length > len(raw):
            raise ValueError('Invalid GLB chunk extent')
        chunks.append(chunk_kind)
        offset += chunk_length
    if not document.get('meshes'):
        raise ValueError('GLB contains no meshes')
    if document.get('buffers') and 0x004E4942 not in chunks:
        raise ValueError('GLB is missing its binary chunk')
    return document, len(raw)


def validate_export(name, model):
    errors = model['errors']
    path = OUT / 'models' / f'{name}.glb'
    document, size = read_glb(path)
    if document.get('cameras') or document.get('extensions', {}).get('KHR_lights_punctual'):
        errors.append('GLB contains presentation cameras or lights')
    if any('camera' in node or 'KHR_lights_punctual' in node.get('extensions', {})
           for node in document.get('nodes', [])):
        errors.append('GLB node references a camera or light')
    if any('uri' in item for kind in ('images', 'buffers') for item in document.get(kind, [])):
        errors.append('GLB references external image or buffer files')
    if document.get('skins') or document.get('animations'):
        errors.append('Unexpected rig or animation in static GLB')
    allowed = set(model.get('source_object_names', []))
    unexpected = [node.get('name', '<unnamed>') for node in document.get('nodes', [])
                  if 'mesh' in node and node.get('name') not in allowed]
    if unexpected:
        errors.append('GLB has meshes outside its source model collection: '+', '.join(unexpected))
    presentation = [node.get('name', '') for node in document.get('nodes', [])
                    if any(token in node.get('name', '').lower()
                           for token in ('presentation', 'pedestal', 'stage_floor', 'gallery_label'))]
    if presentation:
        errors.append('GLB includes presentation nodes: '+', '.join(presentation))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    imported = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    exported = inspect(imported, Matrix.Identity(4), errors, source=False)
    model['glb'] = exported
    exported['file_bytes'] = size
    exported['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    exported['path'] = str(path.relative_to(OUT))
    exported['document_materials'] = sorted(item.get('name', '') for item in document.get('materials', []))
    if any(obj.type in {'CAMERA', 'LIGHT', 'ARMATURE'} for obj in bpy.context.scene.objects):
        errors.append('Imported GLB contains a camera, light or armature')
    source = model.get('source')
    if source:
        if source['triangles'] != exported['triangles']:
            errors.append(f"Triangle count differs: source {source['triangles']}, GLB {exported['triangles']}")
        a, b = source['bounds_m'], exported['bounds_m']
        if a and b:
            delta = max(abs(x-y) for key in ('min', 'max') for x, y in zip(a[key], b[key]))
            exported['max_bounds_difference_m'] = delta
            if delta > BOUNDS_TOLERANCE:
                errors.append(f'Canonical GLB bounds differ by {delta:.9g} m')
        missing = sorted(set(source['used_materials'])-set(exported['materials']))
        exported['missing_source_materials'] = missing
        if missing:
            errors.append('GLB is missing source materials: '+', '.join(missing))


def main():
    report = {
        'passed': False, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'expected_models': EXPECTED_MODELS, 'errors': [], 'models': {},
        'thresholds': {'triangle_area_m2': AREA_EPSILON, 'bounds_difference_m': BOUNDS_TOLERANCE,
                       'glb_topology_weld_m': WELD_DISTANCE},
        'limits': ['Static meshes; no rigging, animation or game-engine runtime validation.',
                   'Source topology is checked per component; component intersections are not a single watertight union.',
                   'Solid PBR materials do not require UVs; UV presence is reported.',
                   'GLB topology after transient vertex welding is informational; normal/material seams may split vertices.',
                   'Source bounds use root-local evaluated vertices; GLB bounds use imported world vertices.']}
    names = []
    try:
        roster = json.loads((OUT / 'roster.json').read_text(encoding='utf-8-sig'))
        if not isinstance(roster, list):
            raise ValueError('roster.json must contain a list')
        names = [item['name'] for item in roster]
        if any(not isinstance(name, str) or not name or Path(name).name != name for name in names):
            raise ValueError('Roster has an invalid model name')
        if len(names) != EXPECTED_MODELS or len(set(names)) != EXPECTED_MODELS:
            raise ValueError(f'Expected {EXPECTED_MODELS} unique roster entries; got {len(names)} entries / {len(set(names))} unique')
        source_path = OUT / 'Pokemon_Starters.blend'
        bpy.ops.wm.open_mainfile(filepath=str(source_path))
        report['source_file_bytes'] = source_path.stat().st_size
        report['source_sha256'] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        expected_collections = {'Pokemon_'+name for name in names}
        actual_collections = {collection.name for collection in bpy.data.collections
                              if collection.name.startswith('Pokemon_')}
        missing = sorted(expected_collections-actual_collections)
        extra = sorted(actual_collections-expected_collections)
        if missing:
            report['errors'].append('Missing source collections: '+', '.join(missing))
        if extra:
            report['errors'].append('Unexpected source model collections: '+', '.join(extra))
        # Collect all source measurements before resetting the scene for imports.
        for name in names:
            model = {'passed': False, 'errors': []}
            report['models'][name] = model
            try:
                collection = bpy.data.collections.get('Pokemon_'+name)
                root = bpy.data.objects.get('root_'+name)
                if collection is None or root is None or root.type != 'EMPTY':
                    raise ValueError('Missing source collection or Empty model root')
                objects = [obj for obj in collection.all_objects if obj.type == 'MESH']
                if root.name not in collection.all_objects:
                    model['errors'].append('Model root is outside its source collection')
                for obj in objects:
                    parent = obj.parent
                    while parent is not None and parent != root:
                        parent = parent.parent
                    if parent is None:
                        model['errors'].append(f'{obj.name}: mesh is not parented under model root')
                model['source_object_names'] = [obj.name for obj in objects]
                model['source_root_world_translation'] = list(root.matrix_world.translation)
                model['source'] = inspect(objects, root.matrix_world.inverted(), model['errors'], source=True)
                model['source']['armatures'] = sum(obj.type == 'ARMATURE' for obj in collection.all_objects)
                if model['source']['armatures']:
                    model['errors'].append('Unexpected armature in static source model')
            except Exception as exc:
                model['errors'].append(f'Source {type(exc).__name__}: {exc}')
            print(f'SOURCE_INSPECTED {name}', flush=True)
        for name in names:
            model = report['models'][name]
            try:
                validate_export(name, model)
            except Exception as exc:
                model['errors'].append(f'GLB {type(exc).__name__}: {exc}')
            model['passed'] = not model['errors']
            print(f"MODEL_VERIFIED {name} passed={model['passed']} errors={len(model['errors'])}", flush=True)
    except Exception as exc:
        report['errors'].append(f'{type(exc).__name__}: {exc}')
    report['checked_models'] = len(report['models'])
    report['source_triangles'] = sum(model.get('source', {}).get('triangles', 0) for model in report['models'].values())
    report['glb_triangles'] = sum(model.get('glb', {}).get('triangles', 0) for model in report['models'].values())
    report['failed_models'] = [name for name, model in report['models'].items() if not model['passed']]
    report['passed'] = (not report['errors'] and not report['failed_models'] and
                        report['checked_models'] == EXPECTED_MODELS)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('passed', 'errors', 'checked_models', 'failed_models',
                                                   'source_triangles', 'glb_triangles')}, indent=2), flush=True)
    assert report['passed'], 'See assets/PokemonStarters/validation.json'
    print('POKEMON_STARTERS_VERIFY_OK', flush=True)


if __name__ == '__main__':
    main()
