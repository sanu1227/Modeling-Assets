"""Shared production utilities for the separately versioned popular Pokemon set."""
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pokemon_common as c


def initialize(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    c.MATERIALS.clear()
    c.PATCH_LAYERS.clear()
    col = bpy.data.collections.new('Pokemon_' + name)
    bpy.context.scene.collection.children.link(col)
    c.COLLECTION = col
    out = ROOT / 'assets' / 'PokemonPopular' / name
    (out / 'renders').mkdir(parents=True, exist_ok=True)
    return col, out


def uv_project(obj):
    """Stable front cylindrical coordinates; solid material parts also get UVs."""
    me = obj.data
    if me.uv_layers:
        return
    uv = me.uv_layers.new(name='SurfaceUV')
    co = [obj.matrix_world @ v.co for v in me.vertices]
    lo = Vector(tuple(min(v[i] for v in co) for i in range(3)))
    hi = Vector(tuple(max(v[i] for v in co) for i in range(3)))
    for p in me.polygons:
        for li in p.loop_indices:
            v = co[me.loops[li].vertex_index]
            uv.data[li].uv = ((v.x-lo.x)/max(hi.x-lo.x, .001), (v.z-lo.z)/max(hi.z-lo.z, .001))


def mesh_stats(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    low, high = np.full(3, np.inf), np.full(3, -np.inf)
    result = dict(objects=0, triangles=0, degenerate_triangles=0,
                  nonmanifold_edges=0, inconsistent_edges=0, missing_uv=[], missing_material=[], finite=True)
    for o in objects:
        if o.type != 'MESH':
            continue
        ob = o.evaluated_get(graph)
        me = ob.to_mesh()
        result['objects'] += 1
        a = np.empty(len(me.vertices)*3, dtype=np.float64)
        me.vertices.foreach_get('co', a)
        mat = np.array(ob.matrix_world)
        a = a.reshape(-1, 3) @ mat[:3, :3].T + mat[:3, 3]
        result['finite'] &= bool(np.isfinite(a).all())
        low, high = np.minimum(low, a.min(axis=0)), np.maximum(high, a.max(axis=0))
        me.calc_loop_triangles()
        inds = np.empty(len(me.loop_triangles)*3, dtype=np.int32)
        me.loop_triangles.foreach_get('vertices', inds)
        p = a[inds.reshape(-1, 3)]
        areas = np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1)*.5
        result['triangles'] += len(p)
        result['degenerate_triangles'] += int(np.count_nonzero(areas < 1e-12))
        bm = bmesh.new(); bm.from_mesh(me)
        result['nonmanifold_edges'] += sum(not e.is_manifold for e in bm.edges)
        result['inconsistent_edges'] += sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
        bm.free()
        if not me.uv_layers: result['missing_uv'].append(o.name)
        if not me.materials: result['missing_material'].append(o.name)
        ob.to_mesh_clear()
    result['bounds'] = {'min': low.tolist(), 'max': high.tolist(), 'size': (high-low).tolist()}
    return result


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def studio(col, name):
    c.COLLECTION = bpy.data.collections.new('90_Presentation')
    bpy.context.scene.collection.children.link(c.COLLECTION)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = col.get('studio_exposure', -.85)
    scene.world = bpy.data.worlds.new('Soft studio world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.65, .72, .85, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .32
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.035))
    ground = c.finish(bpy.context.object, 'Studio_floor', 'D7E2E5')
    stats = mesh_stats(col.objects)
    lo, hi = Vector(stats['bounds']['min']), Vector(stats['bounds']['max'])
    center = (lo+hi)*.5
    height = hi.z-lo.z
    def area(label, pos, power, size, color):
        data = bpy.data.lights.new(label, 'AREA'); data.energy=power; data.shape='DISK'; data.size=size; data.color=color
        ob = bpy.data.objects.new(label, data); c.COLLECTION.objects.link(ob); ob.location=pos; aim(ob, center)
    area('Large softbox', (-height*1.1, -height*1.7, height*2), 110*height**2, height*1.6, (1, .91, .83))
    area('Cool fill', (height*1.5, -height*.6, height), 55*height**2, height*1.7, (.83, .92, 1))
    area('Back rim', (-height*.2, height, height*1.8), 90*height**2, height*1.3, (1, 1, 1))
    data = bpy.data.cameras.new('Camera'); cam=bpy.data.objects.new('Camera', data); c.COLLECTION.objects.link(cam)
    data.type='ORTHO'; scene.camera=cam
    c.COLLECTION=col
    return stats


def camera_view(name, bounds, view):
    lo, hi = Vector(bounds['min']), Vector(bounds['max'])
    center=(lo+hi)*.5
    span = max(hi.z-lo.z, (hi.x-lo.x)*1.04, (hi.y-lo.y)*1.05)
    directions = {'hero':(4,-9,3), 'front':(0,-10,.5), 'side':(10,0,.5), 'back':(4,9,2.5), 'clay':(4,-9,3)}
    cam=bpy.context.scene.camera
    cam.location=center+Vector(directions[view])*span
    aim(cam, center)
    cam.data.ortho_scale=span*1.24


def save_export(col, name, out):
    for ob in col.objects:
        if ob.type=='MESH': uv_project(ob)
    bpy.context.view_layer.update()
    stats = studio(col, name)
    camera_view(name, stats['bounds'], 'hero')
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_location=Vector(stats['bounds']['max'])*.5
                area.spaces.active.region_3d.view_distance=max(stats['bounds']['size'])*1.9
                area.spaces.active.region_3d.view_rotation=bpy.context.scene.camera.rotation_euler.to_quaternion()
                area.spaces.active.shading.type='MATERIAL'
                area.spaces.active.overlay.show_extras=False
    bpy.ops.object.select_all(action='DESELECT')
    for ob in col.objects: ob.select_set(True)
    bpy.context.view_layer.objects.active=next(o for o in col.objects if o.type=='MESH')
    bpy.ops.export_scene.gltf(filepath=str(out/(name+'.glb')), export_format='GLB', use_selection=True,
                            export_apply=True, export_animations=False, export_cameras=False, export_lights=False)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(name+'.blend')), compress=True)
    (out/'source_geometry.json').write_text(json.dumps(stats, indent=2), encoding='utf8')
    return stats


def render_views(name, out, stats, views, draft=False, resolution=None):
    if '--build-only' in sys.argv:
        return
    scene=bpy.context.scene
    scene.render.resolution_x=scene.render.resolution_y=800 if draft else (resolution or 1500)
    scene.render.resolution_percentage=100
    scene.cycles.samples=20 if draft else 64
    if '--samples' in sys.argv:
        scene.cycles.samples=int(sys.argv[sys.argv.index('--samples')+1])
    if '--gpu' in sys.argv:
        pref=bpy.context.preferences.addons['cycles'].preferences
        pref.compute_device_type='OPTIX';pref.get_devices()
        for device in pref.devices:device.use=device.type=='OPTIX'
        scene.cycles.device='GPU'
    for view in views:
        camera_view(name, stats['bounds'], view)
        scene.view_layers[0].material_override=c.material('A8B3BD', .72) if view=='clay' else None
        scene.render.filepath=str(out/'renders'/((view+'_draft' if draft else view)+'.png'))
        bpy.ops.render.render(write_still=True)
    scene.view_layers[0].material_override=None


def verify(name, out):
    bpy.ops.wm.open_mainfile(filepath=str(out/(name+'.blend')))
    source=mesh_stats(bpy.data.collections['Pokemon_'+name].all_objects)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(out/(name+'.glb')))
    imported=mesh_stats(bpy.context.scene.objects)
    diff=float(np.abs(np.array(source['bounds']['min']+source['bounds']['max'])-
                      np.array(imported['bounds']['min']+imported['bounds']['max'])).max())
    ok=(source['finite'] and imported['finite'] and source['degenerate_triangles']==0
        and imported['degenerate_triangles']==0 and source['nonmanifold_edges']==0
        and source['inconsistent_edges']==0 and not source['missing_uv'] and not source['missing_material']
        and diff<1e-4 and source['triangles']==imported['triangles'])
    report={'passed':bool(ok), 'source':source, 'glb_roundtrip':imported, 'max_bounds_difference':diff,
            'limits':['Static fan model, not an official extracted game asset.',
                      'Intersecting closed components; not a single printable solid.',
                      'No rigging or engine runtime test. GLB seams may split vertices.']}
    (out/'validation.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print('VALIDATION', name, ok, 'triangles', source['triangles'], flush=True)
    if not ok: raise RuntimeError('Geometry validation failed: '+name)
