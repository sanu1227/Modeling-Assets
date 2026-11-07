"""Subtle facial color and surface-fitted brows/lashes for the HM08 body."""
import math

import bpy
from mathutils import Vector


def build_face(body, joints, materials, collection):
    """Keep facial topology; return the separate editable brow and lash objects."""
    created = []
    eye_z = (joints["joint-l-eye"].z + joints["joint-r-eye"].z) / 2
    mouth_z = eye_z - 0.0645
    skin = tuple(materials["skin"].diffuse_color[:3])
    rose = (0.46, 0.125, 0.105)
    blush = (0.56, 0.235, 0.17)
    mesh = body.data

    def smooth(value):
        value = max(0.0, min(1.0, value))
        return value * value * (3 - 2 * value)

    # Enlarge the aperture and its fitted eyes together, without changing depth.
    # A broad falloff keeps the surrounding cheek and forehead continuous.
    if not body.get("FaceEyeRefinementApplied"):
        centers = [Vector(joints[f"joint-{side}-eye"]) for side in ("l", "r")]
        for vertex in mesh.vertices:
            x, y, z = vertex.co
            center = centers[0 if x >= 0 else 1]
            dx, dz = x - center.x, z - center.z
            distance = math.hypot(dx, dz)
            amount = (0.12 * smooth((0.038 - distance) / 0.016)
                      * smooth((-0.075 - y) / 0.030) * smooth(abs(x) / 0.010))
            vertex.co.x += dx * amount
            vertex.co.z += dz * amount
            # Restrict the small alar reduction to the protruding lower nose.
            nose = math.exp(-((z - (eye_z - 0.040)) / 0.012) ** 2
                            - (x / 0.022) ** 4) * smooth((-0.140 - y) / 0.012)
            vertex.co.x *= 1 - 0.08 * nose
        for name in ("Eyes_Sclera", "Iris_l", "Iris_r"):
            eye = bpy.data.objects.get(name)
            if eye is not None and not eye.get("FaceEyeRefinementApplied"):
                for vertex in eye.data.vertices:
                    center = centers[0 if vertex.co.x >= 0 else 1]
                    vertex.co.x = center.x + (vertex.co.x - center.x) * 1.12
                    vertex.co.z = center.z + (vertex.co.z - center.z) * 1.12
                eye.data.update()
                eye["FaceEyeRefinementApplied"] = True
        body["FaceEyeRefinementApplied"] = True
        mesh.update()
    if not body.get("FaceSmileApplied"):
        for vertex in mesh.vertices:
            x, y, z = vertex.co
            if y < -0.13 and 1.51 < z < 1.56 and abs(x) < 0.035:
                corner = math.exp(-((abs(x) - 0.021) / 0.008) ** 2 - ((z - mouth_z) / 0.010) ** 2)
                vertex.co.z += 0.0028 * corner
        body["FaceSmileApplied"] = True
        mesh.update()
    colors = mesh.color_attributes.get("FaceTint")
    if colors is None:
        colors = mesh.color_attributes.new(name="FaceTint", type="FLOAT_COLOR", domain="POINT")

    # The lip border follows the existing mouth region, with a soft cupid's bow.
    # No extra geometry is pasted over the existing lips.
    for vertex, color in zip(mesh.vertices, colors.data):
        x, y, z = vertex.co
        col = list(skin)
        if z > 1.49 and y < -0.08:
            cheek = math.exp(-((abs(x) - 0.045) / 0.023) ** 2 - ((z - (eye_z - 0.024)) / 0.018) ** 2)
            amount = 0.15 * cheek * smooth((-0.085 - y) / 0.035)
            col = [a * (1 - amount) + b * amount for a, b in zip(col, blush)]
            if abs(x) < 0.024:
                arc = math.sqrt(max(0.0, 1 - (x / 0.024) ** 2))
                smile = 0.0028 * math.exp(-((abs(x) - 0.021) / 0.008) ** 2)
                top = mouth_z + 0.009 * arc - 0.0017 * math.exp(-(x / 0.004) ** 2) + smile
                bottom = mouth_z - 0.0160 * arc + smile
                edge = min(top - z, z - bottom)
                amount = 0.80 * smooth((edge + 0.0006) / 0.0018) * smooth((-0.140 - y) / 0.008)
                col = [a * (1 - amount) + b * amount for a, b in zip(col, rose)]
        color.color = (*col, 1)
    face_skin = materials["skin"].copy()
    face_skin.name = "Skin with editable face tint"
    node = face_skin.node_tree.nodes.new("ShaderNodeVertexColor")
    node.layer_name = "FaceTint"
    shader = face_skin.node_tree.nodes.get("Principled BSDF")
    face_skin.node_tree.links.new(node.outputs["Color"], shader.inputs["Base Color"])
    body.data.materials[0] = face_skin

    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    surface = body.evaluated_get(graph)
    sclera = bpy.data.objects.get("Eyes_Sclera")
    if sclera is not None:
        sclera = sclera.evaluated_get(graph)
    brow_material = materials["hair"].copy()
    brow_material.name = "Brows soft chestnut"
    brow_shader = brow_material.node_tree.nodes.get("Principled BSDF")
    brow_shader.inputs["Roughness"].default_value = 0.85
    brow_shader.inputs["Specular IOR Level"].default_value = 0.10
    lash_material = materials["dark"].copy()
    lash_material.name = "Lashes matte brown"
    lash_shader = lash_material.node_tree.nodes.get("Principled BSDF")
    lash_shader.inputs["Roughness"].default_value = 0.8
    lash_shader.inputs["Specular IOR Level"].default_value = 0.08

    def front_hit(obj, x, z):
        hit, point, _, _ = obj.ray_cast(Vector((x, -0.6, z)), Vector((0, 1, 0)))
        return point if hit else None

    def line(name, points, radius, material):
        data = bpy.data.curves.new(name, "CURVE")
        data.dimensions = "3D"
        data.resolution_u = 12
        data.bevel_depth = radius
        data.bevel_resolution = 2
        spline = data.splines.new("BEZIER")
        spline.bezier_points.add(len(points) - 1)
        for point, co in zip(spline.bezier_points, points):
            point.co = co
            point.handle_left_type = point.handle_right_type = "AUTO"
        obj = bpy.data.objects.new(name, data)
        collection.objects.link(obj)
        data.materials.append(material)
        created.append(obj)
        return obj

    # Angular fibers and fine variation keep the iris readable as an eye at close range.
    iris_nodes = materials["iris"].node_tree.nodes
    iris_links = materials["iris"].node_tree.links
    tex = iris_nodes.new("ShaderNodeTexCoord")
    shift = iris_nodes.new("ShaderNodeVectorMath")
    shift.operation = "SUBTRACT"
    shift.inputs[1].default_value = (0.5, 0.5, 0.5)
    split = iris_nodes.new("ShaderNodeSeparateXYZ")
    angle = iris_nodes.new("ShaderNodeMath")
    angle.operation = "ARCTAN2"
    frequency = iris_nodes.new("ShaderNodeMath")
    frequency.operation = "MULTIPLY"
    frequency.inputs[1].default_value = 105
    wave = iris_nodes.new("ShaderNodeMath")
    wave.operation = "SINE"
    noise = iris_nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 38
    noise.inputs["Detail"].default_value = 2
    mixed = iris_nodes.new("ShaderNodeMath")
    mixed.operation = "MULTIPLY_ADD"
    mixed.inputs[1].default_value = 0.24
    ramp = iris_nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.1
    ramp.color_ramp.elements[0].color = (0.045, 0.022, 0.008, 1)
    ramp.color_ramp.elements[1].position = 0.9
    ramp.color_ramp.elements[1].color = (0.32, 0.22, 0.075, 1)
    iris_links.new(tex.outputs["Generated"], shift.inputs[0])
    iris_links.new(shift.outputs["Vector"], split.inputs[0])
    iris_links.new(split.outputs["Z"], angle.inputs[0])
    iris_links.new(split.outputs["X"], angle.inputs[1])
    iris_links.new(angle.outputs[0], frequency.inputs[0])
    iris_links.new(frequency.outputs[0], wave.inputs[0])
    iris_links.new(tex.outputs["Generated"], noise.inputs["Vector"])
    iris_links.new(wave.outputs[0], mixed.inputs[0])
    iris_links.new(noise.outputs["Fac"], mixed.inputs[2])
    iris_links.new(mixed.outputs[0], ramp.inputs["Fac"])
    iris_links.new(ramp.outputs["Color"], iris_nodes.get("Principled BSDF").inputs["Base Color"])

    for side, sign in (("l", 1), ("r", -1)):
        center = Vector(joints[f"joint-{side}-eye"])
        iris = bpy.data.objects.get(f"Iris_{side}")
        if iris is not None:
            front = min(v.co.y for v in iris.data.vertices)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.00085,
                location=(center.x - 0.003, front - 0.0005, center.z + 0.004))
            glint = bpy.context.object
            glint.name = f"Eye_glint_{side}"
            for old in list(glint.users_collection):
                old.objects.unlink(glint)
            collection.objects.link(glint)
            glint.data.materials.append(materials["eyes"])
            for polygon in glint.data.polygons:
                polygon.use_smooth = True
            created.append(glint)
        # Surface-fitted ribbon with tapered ends; no floating cylindrical eyebrows.
        verts, faces = [], []
        for i in range(25):
            t = i / 24
            x = sign * (0.012 + 0.048 * t)
            z = center.z + 0.015 + 0.006 * math.sin(math.pi * t) - 0.004 * t
            thickness = 0.00045 + 0.0032 * math.sin(math.pi * t) ** 0.55
            for dz in (-thickness / 2, thickness / 2):
                hit = front_hit(surface, x, z + dz)
                verts.append((x, (hit.y if hit is not None else -0.12) - 0.0007, z + dz))
            if i:
                faces.append((2 * i - 2, 2 * i, 2 * i + 1, 2 * i - 1))
        brow_mesh = bpy.data.meshes.new(f"Brow_{side}")
        brow_mesh.from_pydata(verts, [], faces)
        brow_mesh.update()
        brow = bpy.data.objects.new(f"Brow_{side}", brow_mesh)
        collection.objects.link(brow)
        brow_mesh.materials.append(brow_material)
        for polygon in brow_mesh.polygons:
            polygon.use_smooth = True
        solid = brow.modifiers.new("Fine brow thickness", "SOLIDIFY")
        solid.thickness = 0.0003
        created.append(brow)

        if sclera is None:
            continue
        upper = []
        # Find the actual upper lid/eyeball occlusion boundary, rather than guessing
        # an ellipse. This also follows the supplied eye enlargement morph.
        for i in range(45):
            x = center.x + (i / 44 - 0.5) * 0.042
            visible = []
            for j in range(51):
                z = center.z - 0.021 + j / 50 * 0.042
                skin_hit, eye_hit = front_hit(surface, x, z), front_hit(sclera, x, z)
                if eye_hit is not None and (skin_hit is None or eye_hit.y < skin_hit.y - 0.00005):
                    visible.append(z)
            if not visible:
                continue
            low, high = max(visible), max(visible) + 0.00084
            for _ in range(8):
                z = (low + high) / 2
                skin_hit, eye_hit = front_hit(surface, x, z), front_hit(sclera, x, z)
                if eye_hit is not None and (skin_hit is None or eye_hit.y < skin_hit.y - 0.00005):
                    low = z
                else:
                    high = z
            z = (low + high) / 2
            hit = front_hit(surface, x, z)
            if hit is not None:
                upper.append(Vector((x, hit.y - 0.00045, z)))
        if len(upper) >= 4:
            line(f"Upper_lid_{side}", upper, 0.00035, lash_material)
            outer_first = sorted(upper, key=lambda p: abs(p.x), reverse=True)
            for n, index in enumerate((2, 5, 8, 11, 14, 17)):
                if index >= len(outer_first):
                    break
                p = outer_first[index]
                length = 0.0035 - 0.00022 * n
                line(f"Lash_{side}_{n+1}", (p, p + Vector((sign * length * .22, -length * .48, length * .6)), p + Vector((sign * length * .4, -length * .75, length))), 0.00012, lash_material)
    return created
