"""Fit the CC0 MakeHuman bob01 hair to the editable adventurer head."""
import ast
from collections import defaultdict
import json
import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
HAIR = ROOT / "assets/Character/Source/Hair/hair/bob01"


def _smooth(value):
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def _sweep_fringe(point):
    """Sweep the curtain off both eyes, preserving the upper side-part roots."""
    p = point.copy()
    front = _smooth((.018 - p.y) / .045)
    below_root = 1.0 - _smooth((p.z - 1.640) / .080)
    left_fringe = 1.0 - _smooth((p.x - .018) / .035)
    inner_fringe = _smooth((p.x + .135) / .095)
    weight = front * below_root * left_fringe * inner_fringe
    # Rotate the hanging fringe around its part so the edge becomes a soft arc.
    angle = .46 * weight
    x, z = p.x - .031, p.z - 1.715
    p.x = .031 + x * math.cos(angle) + z * math.sin(angle)
    p.z = 1.715 - x * math.sin(angle) + z * math.cos(angle)
    p.y += .018 * weight
    if p.x < -.115:
        p.x = -.115 + (p.x + .115) * .45
    p.y += .032 * front * _smooth((-p.x - .080) / .050)
    # Keep the bob's outline soft; the crown and hairline stay fixed.
    side = _smooth((abs(p.x + .012) - .065) / .040)
    lower = 1.0 - _smooth((p.z - 1.620) / .075)
    wave = math.sin((p.z - 1.485) * 46.0 + p.y * 9.0)
    sign = -1.0 if p.x < -.012 else 1.0
    p.x += sign * .005 * wave * side * lower
    p.y += .004 * math.cos((p.z - 1.485) * 46.0) * side * lower
    return p


def _source_coordinates():
    """Reuse the original coordinate calculation without running scene edits."""
    path = ROOT / "scripts/build_adventurer.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    nodes, collecting = [], False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "obj_data":
            nodes.append(node)
        if isinstance(node, ast.Assign):
            names = {child.id for target in node.targets for child in ast.walk(target)
                     if isinstance(child, ast.Name)}
            if "native" in names:
                collecting = True
        if collecting:
            nodes.append(node)
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "coords" for t in node.targets):
                break
    namespace = {"Vector": Vector, "defaultdict": defaultdict, "math": math,
                 "SRC": ROOT / "assets/Character/Source/MakeHuman"}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    assert "coords" in namespace, "Original native coordinate calculation not found"
    return namespace


def build_bob_hair(collection, transform):
    """Return hair; transform maps original v001 world positions to final head."""
    source = _source_coordinates()
    native, coords = source["native"], source["coords"]
    body = bpy.data.objects.get("Body_Female_Edit")
    assert body and body.type == "MESH", "Load original Body_Female_Edit before fitting hair"
    ids = body.data.attributes.get("source_vertex_id")
    assert ids is not None, "Body must preserve MakeHuman source_vertex_id"
    for vertex, identifier in zip(body.data.vertices, ids.data):
        coords[identifier.value] = body.matrix_world @ vertex.co

    hair_native, uv, faces, _ = source["obj_data"](HAIR / "bob01.obj")
    offset_scale = Vector((1, 1, 1))
    mapping, reading = [], False
    for line in (HAIR / "bob01.mhclo").read_text(encoding="utf-8").splitlines():
        row = line.split()
        if not row or row[0].startswith("#"):
            continue
        if row[0] in {"x_scale", "y_scale", "z_scale"}:
            axis = "xyz".index(row[0][0])
            a, b, divisor = int(row[1]), int(row[2]), float(row[3])
            offset_scale[axis] = abs(native[a][axis] - native[b][axis]) / divisor
        elif row[0] == "verts":
            reading = True
        elif reading and len(row) == 9 and row[0].isdigit():
            mapping.append((tuple(map(int, row[:3])), tuple(map(float, row[3:6])), tuple(map(float, row[6:9]))))
        elif reading and len(row) == 1 and row[0].isdigit():
            mapping.append(((int(row[0]),), (1.0,), (0.0, 0.0, 0.0)))
        elif reading and mapping:
            break
    assert len(mapping) == len(hair_native), (len(mapping), len(hair_native))
    fitted = []
    for anchors, weights, offset in mapping:
        assert max(anchors) < len(coords) and abs(sum(weights) - 1) < .0001
        native_anchor = sum((native[i] * w for i, w in zip(anchors, weights)), Vector())
        world_anchor = sum((coords[i] * w for i, w in zip(anchors, weights)), Vector())
        native_offset = Vector(tuple(offset[i] * offset_scale[i] for i in range(3)))
        world_offset = source["transform"](native_anchor + native_offset) - source["transform"](native_anchor)
        fitted.append(_sweep_fringe(Vector(transform(world_anchor + world_offset))))

    mesh = bpy.data.meshes.new("Bob01_Fitted_Mesh")
    mesh.from_pydata(fitted, [], [[i for i, _ in face] for face in faces])
    mesh.update()
    layer = mesh.uv_layers.new(name="UVMap")
    for polygon, face in zip(mesh.polygons, faces):
        polygon.use_smooth = True
        for loop, (_, texcoord) in zip(polygon.loop_indices, face):
            assert texcoord is not None
            layer.data[loop].uv = uv[texcoord]
    obj = bpy.data.objects.new("Hair_Bob01_Chestnut", mesh)
    collection.objects.link(obj)
    obj["part"] = "Hair"
    obj["source"] = "MakeHuman system bob01, CC0-1.0; Source/Hair/bob01-source-manifest.json"

    material = bpy.data.materials.new("Bob01_Chestnut_Alpha")
    material.use_nodes = True
    material.use_backface_culling = False
    material.surface_render_method = "DITHERED"
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value = .72
    shader.inputs["Specular IOR Level"].default_value = .12
    for name in ("Anisotropic IOR Level", "Anisotropic"):
        if name in shader.inputs:
            shader.inputs[name].default_value = .28
            break
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(HAIR / "bob01_diffuse.png"), check_existing=True)
    texture.image.pack()
    texture.location = (-600, 120)
    luminance = nodes.new("ShaderNodeRGBToBW")
    luminance.location = (-360, 150)
    tint = nodes.new("ShaderNodeValToRGB")
    ramp = tint.color_ramp
    ramp.elements[0].color = (.018, .0048, .0022, 1)
    ramp.elements[1].color = (.29, .12, .05, 1)
    ramp.elements.new(.10).color = (.075, .022, .008, 1)
    ramp.elements.new(.40).color = (.18, .063, .022, 1)
    tint.location = (-150, 150)
    links.new(texture.outputs["Color"], luminance.inputs["Color"])
    links.new(luminance.outputs["Val"], tint.inputs["Fac"])
    links.new(tint.outputs["Color"], shader.inputs["Base Color"])
    links.new(texture.outputs["Alpha"], shader.inputs["Alpha"])
    mesh.materials.append(material)

    # A matte inner crown prevents transparent card gaps from exposing the scalp.
    cap_material = bpy.data.materials.new("Bob01_Inner_Crown")
    cap_material.use_nodes = True
    cap_shader = cap_material.node_tree.nodes.get("Principled BSDF")
    cap_shader.inputs["Base Color"].default_value = (.025, .006, .002, 1)
    cap_shader.inputs["Roughness"].default_value = .80
    cap_shader.inputs["Specular IOR Level"].default_value = .08
    mesh.materials.append(cap_material)
    edit = bmesh.new()
    edit.from_mesh(mesh)
    original_faces = set(edit.faces)
    crown = bmesh.ops.create_uvsphere(edit, u_segments=40, v_segments=24, radius=1)["verts"]
    for vertex in crown:
        x, y, z = vertex.co
        vertex.co = (-.012 + .078 * x, .042 + .094 * y, 1.635 + .101 * z)
    crown_edges = {edge for vertex in crown for edge in vertex.link_edges}
    crown_faces = set(edit.faces) - original_faces
    bmesh.ops.bisect_plane(edit, geom=list(crown) + list(crown_edges) + list(crown_faces),
                          plane_co=(0, 0, 1.665), plane_no=(0, 0, 1),
                          clear_inner=True, clear_outer=False, dist=.000001)
    for face in set(edit.faces) - original_faces:
        face.material_index = 1
        face.smooth = True
    edit.to_mesh(mesh)
    edit.free()
    mesh.update()

    report = {"native_vertices": len(native), "body_overrides": len(body.data.vertices),
              "hair_vertices": len(fitted), "hair_faces": len(faces),
              "total_vertices_with_crown": len(mesh.vertices), "total_faces_with_crown": len(mesh.polygons),
              "maximum_anchor": max(max(row[0]) for row in mapping),
              "offset_scale": list(offset_scale),
              "minimum": [min(p[i] for p in fitted) for i in range(3)],
              "maximum": [max(p[i] for p in fitted) for i in range(3)]}
    (HAIR.parent.parent / "bob01-fit-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert all(math.isfinite(v) for p in fitted for v in p)
    print("BOB01_FIT", json.dumps(report))
    return obj


if __name__ == "__main__":
    # Open Adventurer_Model_v001.blend before running; this check never saves it.
    result = build_bob_hair(bpy.context.scene.collection, lambda p: p)
    bpy.context.view_layer.update()
    assert .12 < result.dimensions.x < .45
    assert .12 < result.dimensions.z < .45
    assert len(result.data.uv_layers["UVMap"].data) == len(result.data.loops)
    print("BOB01_SELF_CHECK_OK")
