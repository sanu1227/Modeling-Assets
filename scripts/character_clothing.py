"""Fit editable clothing to the posed MakeHuman tights helper without changing it."""
import math

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import convex_hull_2d
from mathutils.bvhtree import BVHTree


def build_clothes(helper, body, joints, materials, collection):
    """Return garment meshes and edge trims. Inputs use meters, +Z up and -Y front."""
    for key in ("cloth", "pants", "leather", "leather_dark", "metal", "thread"):
        if key not in materials:
            raise KeyError(f"Missing clothing material: {key}")
    joints = {name: Vector(value) for name, value in joints.items()}
    objects = []
    waist = 1.06
    neck = joints["joint-neck"]

    def cut(bm, point, normal, keep_positive):
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                              plane_co=point, plane_no=normal, dist=0.00001,
                              clear_inner=keep_positive, clear_outer=not keep_positive)

    def clean(bm):
        loose = [vertex for vertex in bm.verts if not vertex.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.normal_update()

    def source(offset):
        bm = bmesh.new()
        bm.from_mesh(helper.data)
        bm.transform(helper.matrix_world)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.normal_update()
        for vertex in bm.verts:
            vertex.co += vertex.normal * offset
        return bm

    def finish(name, bm, material, thickness=0.0025, subdivision=1):
        clean(bm)
        if not bm.faces:
            bm.free()
            raise ValueError(f"Clothing region is empty: {name}")
        data = bpy.data.meshes.new(name)
        bm.to_mesh(data)
        bm.free()
        obj = bpy.data.objects.new(name, data)
        collection.objects.link(obj)
        data.materials.append(materials[material])
        for polygon in data.polygons:
            polygon.use_smooth = True
        if subdivision:
            smooth = obj.modifiers.new("Editable smooth cloth", "SUBSURF")
            smooth.levels = smooth.render_levels = subdivision
        if thickness:
            solidify = obj.modifiers.new("Fabric thickness", "SOLIDIFY")
            solidify.thickness = thickness
            solidify.offset = 0
            solidify.use_even_offset = True
        obj["garment"] = name
        objects.append(obj)
        return obj

    def boundary_trim(obj, name, material, radius=0.0008):
        bm = bmesh.new()
        # Trace the same subdivided surface that is rendered, before Solidify closes its borders.
        solidifiers = [(modifier, modifier.show_viewport) for modifier in obj.modifiers
                       if modifier.type == "SOLIDIFY"]
        for modifier, _ in solidifiers:
            modifier.show_viewport = False
        bpy.context.view_layer.update()
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        evaluated_mesh = evaluated.to_mesh()
        try:
            bm.from_mesh(evaluated_mesh)
        finally:
            evaluated.to_mesh_clear()
            for modifier, visible in solidifiers:
                modifier.show_viewport = visible
            bpy.context.view_layer.update()
        bm.normal_update()
        edges = {edge for edge in bm.edges if edge.is_boundary}
        paths = []
        while edges:
            first = next(iter(edges))
            edges.remove(first)
            first_vertex, current = first.verts
            path = [first_vertex, current]
            while current != first_vertex:
                candidates = [edge for edge in current.link_edges if edge in edges]
                if not candidates:
                    break
                edge = candidates[0]
                edges.remove(edge)
                current = edge.other_vert(current)
                path.append(current)
            if len(path) > 3:
                thickness = max((modifier.thickness / 2 for modifier, _ in solidifiers), default=0)
                offset = thickness + (0.0007 if material == "thread" else 0.0002)
                paths.append(([tuple(vertex.co + vertex.normal * offset) for vertex in path],
                              current == first_vertex))
        bm.free()
        if not paths:
            return None
        curve = bpy.data.curves.new(name, "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = radius
        curve.bevel_resolution = 2
        curve.resolution_u = 3
        for coordinates, cyclic in paths:
            if cyclic:
                coordinates = coordinates[:-1]
            spline = curve.splines.new("POLY")
            spline.points.add(len(coordinates) - 1)
            spline.use_cyclic_u = cyclic
            for point, coordinate in zip(spline.points, coordinates):
                point.co = (*coordinate, 1)
        trim = bpy.data.objects.new(name, curve)
        collection.objects.link(trim)
        curve.materials.append(materials[material])
        objects.append(trim)
        return trim

    # The helper is a continuous clothed body surface; cuts preserve its armhole topology.
    shirt = source(0.012)
    cut(shirt, (0, 0, waist - 0.022), (0, 0, 1), True)
    # Cut on the narrow neck, above the shoulder silhouette, then lower the front only.
    neckline_z = neck.z + 0.025
    cut(shirt, (0, 0, neckline_z), (0, 0, 1), False)
    sleeve_ends = []
    for side in ("l", "r"):
        elbow, hand = joints[f"joint-{side}-elbow"], joints[f"joint-{side}-hand"]
        direction = (hand - elbow).normalized()
        end = elbow.lerp(hand, 0.28)
        sleeve_ends.append((side, end, direction))
        cut(shirt, end, direction, False)
    for vertex in shirt.verts:
        if abs(vertex.co.z - neckline_z) < 0.0001:
            front = max(0, min(1, (neck.y - vertex.co.y) / 0.065))
            vertex.co.z -= 0.025 * front * max(0, 1 - abs(vertex.co.x) / 0.060)
    shirt_obj = finish("Shirt_Teal", shirt, "cloth")
    boundary_trim(shirt_obj, "Shirt_Hem_And_Neck_Seam", "cloth", 0.0010)

    for side, end, direction in sleeve_ends:
        bm = source(0.017)
        sign = 1 if side == "l" else -1
        cut(bm, (sign * 0.235, 0, 0), (sign, 0, 0), True)
        cut(bm, end - direction * 0.028, direction, True)
        cut(bm, end + direction * 0.010, direction, False)
        cuff = finish(f"Shirt_Rolled_Cuff_{side.upper()}", bm, "cloth", 0.004)
        boundary_trim(cuff, f"Sleeve_Cuff_Seam_{side.upper()}", "cloth", 0.0010)

    pants = source(0.011)
    cut(pants, (0, 0, 0.215), (0, 0, 1), True)
    cut(pants, (0, 0, waist + 0.017), (0, 0, 1), False)
    cut(pants, (0.26, 0, 0), (1, 0, 0), False)
    cut(pants, (-0.26, 0, 0), (-1, 0, 0), False)
    pants_obj = finish("Trousers_Slate", pants, "pants", 0.002)
    boundary_trim(pants_obj, "Trousers_Waist_And_Hem", "pants", 0.0008)

    vest = source(0.024)
    cut(vest, (0, 0, waist + 0.025), (0, 0, 1), True)
    cut(vest, (0, 0, neck.z + 0.010), (0, 0, 1), False)
    cut(vest, (0.21, 0, 0), (1, 0, 0), False)
    cut(vest, (-0.21, 0, 0), (-1, 0, 0), False)
    remove = []
    for face in vest.faces:
        point = face.calc_center_median()
        side = "l" if point.x > 0 else "r"
        shoulder = joints[f"joint-{side}-shoulder"]
        height = (point.z - (shoulder.z - 0.015)) / 0.105
        armhole_limit = abs(shoulder.x) + 0.060
        if abs(height) < 1:
            armhole_limit -= 0.100 * math.sqrt(1 - height * height)
        front_gap = 0.025 + 0.035 * max(0, (point.z - 1.22) / 0.22)
        if abs(point.x) > armhole_limit or (point.y < -0.035 and abs(point.x) < front_gap):
            remove.append(face)
    bmesh.ops.delete(vest, geom=remove, context="FACES")
    clean(vest)
    # Face selection may leave small sleeve fragments. Keep the connected torso only.
    remaining = set(vest.faces)
    components = []
    while remaining:
        seed = remaining.pop()
        component, pending = {seed}, [seed]
        while pending:
            for edge in pending.pop().edges:
                for adjacent in edge.link_faces:
                    if adjacent in remaining:
                        remaining.remove(adjacent)
                        component.add(adjacent)
                        pending.append(adjacent)
        components.append(component)
    largest = max(components, key=lambda faces: sum(face.calc_area() for face in faces))
    scraps = [face for component in components if component is not largest for face in component]
    if scraps:
        bmesh.ops.delete(vest, geom=scraps, context="FACES")
    clean(vest)

    surface = BVHTree.FromPolygons([helper.matrix_world @ vertex.co for vertex in helper.data.vertices],
                                  [tuple(face.vertices) for face in helper.data.polygons])
    boundary = {vertex for edge in vest.edges if edge.is_boundary for vertex in edge.verts}
    front_edge = {vertex for vertex in boundary if vertex.co.y < -0.035 and abs(vertex.co.x) < 0.09
                  and vertex.co.z > waist + 0.030}
    # Smooth each actual boundary loop; resnap onto the fitted helper to avoid floating piping.
    for _ in range(18):
        changes = {}
        for vertex in boundary:
            if vertex.co.z < waist + 0.028:
                continue
            adjacent = [edge.other_vert(vertex) for edge in vertex.link_edges if edge.is_boundary]
            if len(adjacent) == 2:
                changes[vertex] = vertex.co.lerp((adjacent[0].co + adjacent[1].co) / 2, 0.45)
        for vertex, coordinate in changes.items():
            location, normal, _, _ = surface.find_nearest(coordinate)
            vertex.co = location + normal * 0.024 if location is not None else coordinate
        for vertex in front_edge:
            z = vertex.co.z
            sign = 1 if vertex.co.x > 0 else -1
            x = sign * (0.026 + 0.030 * max(0, (z - 1.22) / 0.24))
            location, _, _, _ = surface.ray_cast(Vector((x, -1, z)), Vector((0, 1, 0)), 2)
            if location is not None:
                vertex.co = (x, location.y - 0.026, z)
    vest_obj = finish("Vest_Open_Leather", vest, "leather", 0.004)
    boundary_trim(vest_obj, "Vest_Edge_Piping", "leather_dark", 0.0018)
    boundary_trim(vest_obj, "Vest_Stitching", "thread", 0.00055)

    for side in ("l", "r"):
        sign = 1 if side == "l" else -1
        ankle = joints[f"joint-{side}-ankle"]
        boot = source(0.009)
        cut(boot, (0, 0, 0.240), (0, 0, 1), False)
        cut(boot, (0, 0, 0), (sign, 0, 0), True)
        for vertex in boot.verts:
            vertex.co.z = max(0.025, vertex.co.z)
        clean(boot)
        footprint = [Vector((vertex.co.x, vertex.co.y)) for vertex in boot.verts
                     if vertex.co.z < ankle.z + 0.025]
        hull = [footprint[index] for index in convex_hull_2d(footprint)]
        center = sum(hull, Vector((0, 0))) / len(hull)
        hull = [point + (point - center).normalized() * 0.004 for point in hull]
        boot_obj = finish(f"Boot_Leather_{side.upper()}", boot, "leather", 0.003)
        boundary_trim(boot_obj, f"Boot_Top_Seam_{side.upper()}", "leather_dark", 0.001)

        sole = bmesh.new()
        lower = [sole.verts.new((point.x, point.y, 0.002)) for point in hull]
        upper = [sole.verts.new((point.x, point.y, 0.031)) for point in hull]
        sole.faces.new(lower[::-1])
        sole.faces.new(upper)
        for index in range(len(hull)):
            next_index = (index + 1) % len(hull)
            sole.faces.new((lower[index], lower[next_index], upper[next_index], upper[index]))
        bmesh.ops.recalc_face_normals(sole, faces=list(sole.faces))
        sole_obj = finish(f"Boot_Sole_{side.upper()}", sole, "leather_dark", 0, 0)
        bevel = sole_obj.modifiers.new("Rounded sole edge", "BEVEL")
        bevel.width, bevel.segments = 0.004, 3

        cuff = source(0.018)
        cut(cuff, (0, 0, 0.208), (0, 0, 1), True)
        cut(cuff, (0, 0, 0.267), (0, 0, 1), False)
        cut(cuff, (0, 0, 0), (sign, 0, 0), True)
        cuff_obj = finish(f"Boot_Folded_Cuff_{side.upper()}", cuff, "leather", 0.005)
        boundary_trim(cuff_obj, f"Boot_Cuff_Stitch_{side.upper()}", "thread", 0.0008)
    return objects
