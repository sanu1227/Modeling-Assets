"""Rebuild cloth shading and fit small physical garment details to the v3 body."""
from pathlib import Path
from collections import Counter

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


def refine_clothes(body, collection):
    mesh = body.data
    original = (len(mesh.vertices), len(mesh.polygons), len(mesh.uv_layers))
    image = next(node.image for mat in mesh.materials if mat and mat.use_nodes
                 for node in mat.node_tree.nodes
                 if node.type == 'TEX_IMAGE' and node.image and 'basecolor' in node.image.name)
    width, height = image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    pixels = pixels.reshape(height, width, 4)
    uvs = np.array([loop.uv[:] for loop in mesh.uv_layers[0].data])
    centers = np.array([face.center[:] for face in mesh.polygons])
    face_uv = np.array([uvs[list(face.loop_indices)].mean(axis=0) for face in mesh.polygons])
    colors = pixels[(face_uv[:, 1] * height).astype(int) % height,
                    (face_uv[:, 0] * width).astype(int) % width, :3]
    old_slots = np.array([face.material_index for face in mesh.polygons])
    # Existing skin, repaired boots, and the joined neck remain untouched.
    eligible = np.isin(old_slots, [0, 1]) & (centers[:, 2] > .3)
    eligible &= ~((centers[:, 2] > 1.435) & (abs(centers[:, 0] - .009) < .058))
    red, green, blue = colors.T
    labels = np.full(len(mesh.polygons), -1, dtype=np.int32)
    labels[eligible & (centers[:, 2] < 1.054)] = 2
    top = eligible & (centers[:, 2] >= 1.054)
    leather = (red > blue * 1.12) & (red > green * 1.10)
    shirt = (blue > red * 1.05) & (green > red * 1.02)
    labels[top & leather] = 1
    labels[top & shirt] = 0
    # Keep the modeled pouch and belt while removing isolated brown texture errors on pants.
    pouch = eligible & (centers[:, 0] > .105) & (centers[:, 0] < .24)
    pouch &= (centers[:, 2] > .945) & (centers[:, 2] < 1.11) & (centers[:, 1] < -.025)
    labels[pouch & leather] = 1
    belt = eligible & (centers[:, 2] > 1.055) & (centers[:, 2] < 1.105)
    labels[belt & leather] = 1
    known = np.flatnonzero(top & (labels >= 0))
    tree = KDTree(len(known))
    for index in known:
        tree.insert(centers[index], int(index))
    tree.balance()
    # The white/gray generated shoulder patches have no reliable hue: inherit nearby cloth.
    for index in np.flatnonzero(eligible & (labels < 0)):
        neighbors = tree.find_n(centers[index], 7)
        votes = Counter(int(labels[neighbor]) for _, neighbor, _ in neighbors)
        labels[index] = votes.most_common(1)[0][0]
    # Brown pixels on sleeves were generated errors, not a second leather garment.
    sleeve = eligible & (abs(centers[:, 0]) > .19) & (centers[:, 2] > .98)
    labels[sleeve] = 0
    bare_cuff = sleeve & (.58 * abs(centers[:, 0]) - .815 * centers[:, 2] > -.775)
    labels[bare_cuff] = 3
    neckline = eligible & (centers[:, 2] > 1.355) & (abs(centers[:, 0] - .009) < .048)
    labels[neckline] = np.where(shirt[neckline], 0, 3)

    def surface(name, base, roughness, weave=False):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.diffuse_color = (*base, 1)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = nodes.get('Principled BSDF')
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Specular IOR Level'].default_value = .22
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 180 if weave else 95
        noise.inputs['Detail'].default_value = 2
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = tuple(v * .88 for v in base) + (1,)
        ramp.color_ramp.elements[1].color = tuple(v * 1.08 for v in base) + (1,)
        links.new(noise.outputs['Fac'], ramp.inputs[0])
        links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .11
        bump.inputs['Distance'].default_value = .00016
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs[0], bsdf.inputs['Normal'])
        return mat

    materials = [surface('V4_Shirt_Teal_Linen', (.075, .125, .15), .79, True),
                 surface('V4_Vest_Warm_Leather', (.18, .075, .028), .66),
                 surface('V4_Pants_Slate_Cloth', (.064, .069, .09), .82, True)]
    # Interpolate repaired region colors over shared vertices, avoiding sawtooth face borders.
    skin_mat = next(m for m in mesh.materials if m.name.startswith('Body_Skin_Refined'))
    palette = np.array([m.diffuse_color[:] for m in materials] + [skin_mat.diffuse_color[:]])
    vertex_color = np.zeros((len(mesh.vertices), 4), dtype=np.float64)
    weights = np.zeros(len(mesh.vertices), dtype=np.float64)
    for index in np.flatnonzero(eligible):
        for vertex in mesh.polygons[int(index)].vertices:
            vertex_color[vertex] += palette[labels[index]]
            weights[vertex] += 1
    occupied = weights > 0
    vertex_color[occupied] /= weights[occupied, None]
    # Two local averaging passes soften only the tiny polygon-scale classification steps.
    edges = np.array([edge.vertices[:] for edge in mesh.edges], dtype=np.int32)
    for _ in range(2):
        total, count = vertex_color.copy() * 3, occupied.astype(float) * 3
        for a, b in ((edges[:, 0], edges[:, 1]), (edges[:, 1], edges[:, 0])):
            good = occupied[a] & occupied[b]
            np.add.at(total, a[good], vertex_color[b[good]])
            np.add.at(count, a[good], 1)
        vertex_color[occupied] = total[occupied] / count[occupied, None]
    attribute = mesh.color_attributes.new(name='V4_Clean_Garment_Color', type='FLOAT_COLOR', domain='POINT')
    attribute.data.foreach_set('color', vertex_color.astype(np.float32).ravel())
    clean = mesh.materials[1].copy()
    clean.name = 'V4_Original_Garments_Local_Patch_Repair'
    nodes, links = clean.node_tree.nodes, clean.node_tree.links
    bsdf = next(node for node in nodes if node.type == 'BSDF_PRINCIPLED')
    original_color = bsdf.inputs['Base Color'].links[0].from_socket
    vertex_node = nodes.new('ShaderNodeVertexColor')
    vertex_node.layer_name = attribute.name
    repair_area = mesh.color_attributes.new(name='V4_Local_Repair_Areas', type='FLOAT_COLOR', domain='POINT')
    for vertex, datum in zip(mesh.vertices, repair_area.data):
        x, y, z = vertex.co
        shoulder = min(1, max(0, (z - 1.405) / .018)) if abs(x) > .065 else 0
        sleeve = float(abs(x) > .20 and 1.08 < z < 1.29 and .58 * abs(x) - .815 * z < -.80)
        datum.color = (shoulder, sleeve, 0, 1)
    area_node = nodes.new('ShaderNodeVertexColor'); area_node.layer_name = repair_area.name
    area_split = nodes.new('ShaderNodeSeparateColor'); links.new(area_node.outputs['Color'], area_split.inputs[0])
    split = nodes.new('ShaderNodeSeparateColor'); links.new(original_color, split.inputs[0])

    def math_node(operation, a, b):
        node = nodes.new('ShaderNodeMath'); node.operation = operation
        for value, socket in ((a, node.inputs[0]), (b, node.inputs[1])):
            if isinstance(value, (float, int)):
                socket.default_value = value
            else:
                links.new(value, socket)
        return node.outputs[0]

    def mapped(value, low, high):
        node = nodes.new('ShaderNodeMapRange'); node.clamp = True
        node.inputs['From Min'].default_value = low; node.inputs['From Max'].default_value = high
        links.new(value, node.inputs['Value'])
        return node.outputs['Result']

    brightest = math_node('MAXIMUM', math_node('MAXIMUM', split.outputs['Red'], split.outputs['Green']), split.outputs['Blue'])
    darkest = math_node('MINIMUM', math_node('MINIMUM', split.outputs['Red'], split.outputs['Green']), split.outputs['Blue'])
    saturation = math_node('SUBTRACT', brightest, darkest)
    gray = math_node('SUBTRACT', 1.0, mapped(saturation, .035, .16))
    bright = mapped(brightest, .23, .58)
    shoulder_patch = math_node('MULTIPLY', math_node('MULTIPLY', gray, bright), area_split.outputs['Red'])
    brown_error = mapped(math_node('SUBTRACT', split.outputs['Red'], split.outputs['Blue']), .007, .05)
    sleeve_patch = math_node('MULTIPLY', brown_error, area_split.outputs['Green'])
    factor = math_node('MAXIMUM', shoulder_patch, sleeve_patch)
    mix = nodes.new('ShaderNodeMixRGB')
    links.new(factor, mix.inputs[0]); links.new(original_color, mix.inputs[1]); links.new(vertex_node.outputs['Color'], mix.inputs[2])
    links.new(mix.outputs[0], bsdf.inputs['Base Color'])
    slot_start = len(mesh.materials)
    mesh.materials.append(clean)
    for index in np.flatnonzero(eligible):
        mesh.polygons[int(index)].material_index = slot_start

    coords = [v.co.copy() for v in mesh.vertices]
    bvh = BVHTree.FromPolygons(coords, [tuple(p.vertices) for p in mesh.polygons])
    added = []
    curve_groups = {}

    def front(x, z):
        point, normal, face_index, distance = bvh.ray_cast(Vector((x, -1, z)), Vector((0, 1, 0)))
        return (point, normal, face_index) if point is not None else None

    def curve(name, points, radius, material):
        if len(points) < 2:
            return
        key = material.name, radius
        obj = curve_groups.get(key)
        if obj is None:
            data = bpy.data.curves.new(name, 'CURVE')
            data.dimensions = '3D'
            data.resolution_u = 2
            data.bevel_depth = radius
            data.bevel_resolution = 2
            obj = bpy.data.objects.new(name, data)
            collection.objects.link(obj)
            data.materials.append(material)
            added.append(obj)
            curve_groups[key] = obj
        data = obj.data
        spline = data.splines.new('POLY')
        spline.points.add(len(points) - 1)
        for point, position in zip(spline.points, points):
            point.co = (*position, 1)
        return obj

    trim = surface('V4_Leather_Edge_Binding', (.12, .046, .018), .73)
    stitch = surface('V4_Leather_Stitch_Thread', (.40, .24, .12), .88)
    # Find the real inner vest edge at each height; smooth only its sideways route.
    for side in (-1, 1):
        found = []
        for z in np.linspace(1.160, 1.422, 42):
            for x in np.linspace(.035, .145, 80):
                hit = front(side * float(x), float(z))
                if hit and labels[hit[2]] == 1:
                    found.append((side * float(x + .003), float(z)))
                    break
        if len(found) < 20:
            continue
        xs = np.array([p[0] for p in found])
        xs = np.convolve(np.pad(xs, (2, 2), mode='edge'), np.ones(5) / 5, mode='valid')
        seam = []
        for x, (_, z) in zip(xs, found):
            hit = front(float(x), z)
            if hit:
                seam.append(hit[0] + hit[1] * .0009)
        curve(f'Vest_Edge_Binding_{side}', seam, .0010, trim)
        for index in range(0, len(seam) - 1, 2):
            a, b = seam[index], seam[index + 1]
            offset = Vector((side * .003, -.0005, 0))
            curve(f'Vest_Stitch_{side}_{index:02}', [a + offset, a.lerp(b, .62) + offset], .00038, stitch)

    # Bronze shirt buttons are actual shallow cylinders fitted to the front surface.
    brass = surface('V4_Aged_Brass_Buttons', (.25, .145, .047), .35)
    brass.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value = .7
    for index, (x, z) in enumerate(((-.038, 1.397), (-.028, 1.365), (-.018, 1.333))):
        hit = front(x, z)
        if hit and labels[hit[2]] != 0:
            candidates = [front(x + offset, z) for offset in (-.004, -.008, -.012, .004)]
            hit = next((candidate for candidate in candidates if candidate and labels[candidate[2]] == 0), None)
        if not hit or labels[hit[2]] != 0:
            continue
        point, normal, _ = hit
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=.0028, depth=.0013,
                                           location=point + normal * .0010)
        obj = bpy.context.object
        obj.name = f'Shirt_Brass_Button_{index + 1}'
        obj.rotation_euler = normal.to_track_quat('Z', 'Y').to_euler()
        for owner in list(obj.users_collection):
            owner.objects.unlink(obj)
        collection.objects.link(obj)
        obj.data.materials.append(brass)
        bevel = obj.modifiers.new('Rounded_Button_Edge', 'BEVEL')
        bevel.width, bevel.segments = .00035, 2
        for face in obj.data.polygons:
            face.use_smooth = True
        added.append(obj)

    # Round the exposed leather cut edge without introducing another collar silhouette.
    edge_faces = {}
    for face in mesh.polygons:
        if labels[face.index] != 1 or face.center.z < 1.455:
            continue
        for edge in face.edge_keys:
            edge_faces[edge] = edge_faces.get(edge, 0) + 1
    for index, (edge, count) in enumerate(edge_faces.items()):
        a, b = (mesh.vertices[i].co.copy() for i in edge)
        if count == 1 and min(a.z, b.z) > 1.4748:
            curve(f'Collar_Rounded_Leather_Edge_{index}', [a, b], .0012, trim)

    assert original == (len(mesh.vertices), len(mesh.polygons), len(mesh.uv_layers))
    body['v4_cloth_faces'] = {str(i): int(np.sum(labels == i)) for i in range(3)}
    body['v4_detail_objects'] = len(added)
    print('V4_CLOTHES_OK', body['v4_cloth_faces'].to_dict(), len(added))
    return added


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    bpy.ops.wm.open_mainfile(filepath=str(root / 'assets/Character/Refined_v003/Adventurer_Refined_v003.blend'))
    obj = bpy.data.objects['Body_Clothing_Tripo_Refined']
    refine_clothes(obj, bpy.data.collections['01_Character_Refined'])
    scene = bpy.context.scene
    scene.camera.location = (0, -4, 1.275)
    scene.camera.rotation_euler = (Vector((0, 0, 1.275)) - scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera.data.ortho_scale = .72
    scene.render.resolution_x, scene.render.resolution_y = 1100, 1000
    scene.cycles.samples = 24
    scene.render.filepath = str(root / 'logs/body_v4_preview.png')
    bpy.ops.render.render(write_still=True)
    print('V4_CLOTHES_PREVIEW_DONE')
