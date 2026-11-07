"""Layer and wave the saved v003 bob without modifying its source files."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform


def smooth(value):
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def _ear_clearance(point):
    """Keep both the base cards and added locks behind the unmodified right ear."""
    point = point.copy()
    x_weight = smooth((point.x-.045)/.010) * (1-smooth((point.x-.077)/.013))
    z_weight = smooth((point.z-1.565)/.011) * (1-smooth((point.z-1.626)/.004))
    point.y += max(0.0, .073-point.y) * x_weight * z_weight
    return point


def _strand_material():
    material = bpy.data.materials.new('Hair_v004_Chestnut_Layers')
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .75
    shader.inputs['Specular IOR Level'].default_value = .07
    uv = nodes.new('ShaderNodeTexCoord')
    scale = nodes.new('ShaderNodeVectorMath')
    scale.operation = 'MULTIPLY'
    scale.inputs[1].default_value = (110, 2.5, 1)
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 1
    noise.inputs['Detail'].default_value = 2
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .15
    ramp.color_ramp.elements[0].color = (.015, .0038, .0015, 1)
    ramp.color_ramp.elements[1].position = .85
    ramp.color_ramp.elements[1].color = (.052, .014, .0045, 1)
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .035
    bump.inputs['Distance'].default_value = .00035
    links.new(uv.outputs['Generated'], scale.inputs[0])
    links.new(scale.outputs[0], noise.inputs['Vector'])
    links.new(noise.outputs['Fac'], ramp.inputs[0])
    links.new(ramp.outputs[0], shader.inputs['Base Color'])
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return material


def _sample_path(points, count=45):
    points = [Vector(p) for p in points]
    result = []
    for i in range(count):
        t = i / (count - 1) * (len(points) - 1)
        segment = min(len(points) - 2, int(t))
        u = t - segment
        a, b, c, d = (points[max(0, segment-1)], points[segment],
                      points[segment+1], points[min(len(points)-1, segment+2)])
        result.append((2*b + (-a+c)*u + (2*a-5*b+4*c-d)*u*u + (-a+3*b-3*c+d)*u*u*u) * .5)
    return result


def _lock(name, points, width, material, collection, surface, base, project=True):
    path = _sample_path(points)
    vertices, faces, source_uv, source_material = [], [], [], []
    sides = 7
    for i, point in enumerate(path):
        t = i / (len(path) - 1)
        tangent = (path[min(i+1, len(path)-1)] - path[max(i-1, 0)]).normalized()
        nearest_point, normal, _, _ = surface.find_nearest(point)
        if project:
            point = nearest_point
        radial = point - Vector((-.012, .028, 1.635))
        if normal.dot(radial) < 0:
            normal = -normal
        normal = (normal - tangent * normal.dot(tangent)).normalized()
        across = tangent.cross(normal).normalized()
        taper = (.34 + .66 * math.sin(math.pi*t) ** .55) * (1 - .97 * smooth((t-.72)/.28))
        for j in range(sides):
            across_amount = j / (sides-1) * 2 - 1
            candidate = point + across * (width * .5 * taper * across_amount)
            nearest, outward, face_index, _ = surface.find_nearest(candidate)
            if outward.dot(radial) < 0:
                outward = -outward
            ridge = .00045 + .00075 * (1-across_amount**2) * taper
            vertices.append(_ear_clearance((nearest if project else candidate) + outward * ridge))
            polygon = base.data.polygons[face_index]
            loops = list(polygon.loop_indices)[:3]
            positions = [base.data.vertices[base.data.loops[k].vertex_index].co for k in loops]
            texcoords = [Vector((*base.data.uv_layers.active.data[k].uv, 0)) for k in loops]
            mapped = barycentric_transform(nearest, *positions, *texcoords)
            source_uv.append((mapped.x, mapped.y))
            source_material.append(polygon.material_index)
    for i in range(len(path)-1):
        for j in range(sides-1):
            faces.append((i*sides+j, i*sides+j+1, (i+1)*sides+j+1, (i+1)*sides+j))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    uv = mesh.uv_layers.new(name='StrandUV')
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        polygon.material_index = source_material[mesh.loops[polygon.loop_start].vertex_index]
        for loop in polygon.loop_indices:
            index = mesh.loops[loop].vertex_index
            uv.data[loop].uv = source_uv[index]
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    mesh.materials.append(material)
    mesh.materials.append(base.data.materials[1])
    obj['part'] = 'Hair'
    obj['modeling'] = 'Editable tapered flattened hair lock with longitudinal strand texture'
    return obj


def refine_hair(hair, head, collection):
    """Modify the loaded hair in memory; return newly created lock objects."""
    assert hair.type == 'MESH' and head.type == 'MESH'
    hair.data = hair.data.copy()
    for vertex in hair.data.vertices:
        x, y, z = vertex.co
        side = smooth((abs(x + .012) - .058) / .045)
        lower = 1 - smooth((z - 1.625) / .065)
        sign = -1 if x < -.012 else 1
        vertex.co.x += sign * .007 * math.sin((z-1.49)*50 + y*11) * side * lower
        vertex.co.y += .006 * math.cos((z-1.49)*48 + x*8) * side * lower
        if z < 1.535:
            vertex.co.z = 1.535 + (z-1.535) * .40
        # Move the right-front layer behind the ear, not across the cheek.
        tuck = (smooth((x-.040)/.028) * (1-smooth((y-.015)/.045))
                * smooth((z-1.525)/.035) * (1-smooth((z-1.625)/.025)))
        vertex.co.y += .015 * tuck
        vertex.co.x += .003 * tuck
        vertex.co.z -= .003 * smooth((z-1.680)/.055)
        if vertex.index >= 5203:
            vertex.co.z += .005
            vertex.co.x = -.012 + (vertex.co.x + .012) * 1.04
        vertex.co = _ear_clearance(vertex.co)
    hair.data.update()
    bpy.context.view_layer.update()
    surface = BVHTree.FromObject(hair, bpy.context.evaluated_depsgraph_get())
    material = hair.data.materials[0].copy()
    material.name = 'Hair_v004_Matched_Chestnut'
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .80
    shader.inputs['Specular IOR Level'].default_value = .05
    hair.data.materials[0] = material
    crown_material = _strand_material()
    crown_material.name = 'Hair_v004_Inner_Crown_Strands'
    hair.data.materials[1] = crown_material
    created = []
    # Broad swept fringe layers follow the part, then curl out beside the left eye.
    for i in range(5):
        d = i * .010
        points = [(.028-d*.25, -.002+d*.45, 1.728+d*.16),
                  (-.015-d*.55, -.054+d*.35, 1.711+d*.08),
                  (-.063-d*.70, -.070+d*.40, 1.674-d*.06),
                  (-.104-d*.32, -.060+d*.55, 1.625-d*.20),
                  (-.117+d*.10, -.027+d*.60, 1.577-d*.23),
                  (-.092+d*.10, -.013+d*.65, 1.543-d*.20)]
        created.append(_lock(f'Hair_v004_Swept_{i+1:02}', points, .018-i*.0016, material, collection, surface, hair))
    # Side/back locks alternate outward waves and tucked ends.
    for side in (-1, 1):
        for i in range(4):
            y = .015 + .024*i
            x = -.012 + side * (.075 + .003*math.sin(i))
            points = [(x*.60, y*.50+.020, 1.718-.005*i),
                      (x+side*.014, y-.010, 1.673),
                      (x+side*.020, y+.006, 1.616),
                      (x+side*.004, y+.009, 1.570),
                      (x+side*.010, y-.003, 1.534+.005*math.sin(i*1.8))]
            created.append(_lock(f'Hair_v004_Side_{side}_{i+1:02}', points, .015, material, collection, surface, hair))
    temple = [(.046, -.035, 1.678), (.057, -.040, 1.656),
              (.066, -.025, 1.634), (.074, .012, 1.631), (.076, .074, 1.622)]
    created.append(_lock('Hair_v004_Right_Temple', temple, .020, crown_material, collection, surface, hair, project=False))
    hair['v004_changes'] = 'Soft side waves, shorter layered ends, right ear tuck; tapered swept and crown locks'
    bpy.context.view_layer.update()
    assert all(math.isfinite(c) for obj in created for vertex in obj.data.vertices for c in vertex.co)
    central = [v.co.y for obj in [hair, *created] for v in obj.data.vertices
               if .055 <= v.co.x <= .077 and 1.576 <= v.co.z <= 1.626]
    assert not central or min(central) >= .072999, min(central)
    print('HAIR_V004', json.dumps({'created_locks': len(created), 'new_vertices': sum(len(o.data.vertices) for o in created)}))
    return created


if __name__ == '__main__':
    hair = bpy.data.objects['Hair_Bob01_Chestnut']
    head = bpy.data.objects['Head_Sculpted_ReferenceUV']
    refine_hair(hair, head, hair.users_collection[0])
    scene = bpy.context.scene
    scene.cycles.samples = 20
    scene.render.resolution_x = scene.render.resolution_y = 700
    scene.render.resolution_percentage = 100
    output = Path(__file__).resolve().parents[1] / 'logs'
    output.mkdir(exist_ok=True)
    for name, location in [('front', (0,-4,1.58)), ('quarter', (2.2,-4,1.58)), ('side', (4,0,1.58))]:
        target = Vector((0,.02,1.58))
        scene.camera.location = location
        scene.camera.rotation_euler = (target-scene.camera.location).to_track_quat('-Z','Y').to_euler()
        scene.camera.data.ortho_scale = .42
        scene.render.filepath = str(output / f'hair-v004-{name}.png')
        bpy.ops.render.render(write_still=True)
    print('HAIR_V004_PREVIEW_OK; source blend not saved')
