"""Editable belt, pouch and separate sword for the Blender adventurer."""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector


def build_accessories(waist_z, waist_rx, waist_ry, center_y, materials, collection):
    """Return linked objects; dimensions are meters, front is -Y, anatomical left +X."""
    if min(waist_rx, waist_ry) <= 0:
        raise ValueError("Waist radii must be positive")
    for key in ("leather", "leather_dark", "metal", "blade", "thread"):
        if key not in materials:
            raise KeyError(f"Missing accessory material: {key}")
    objects = []

    def mesh(name, vertices, faces, material, bevel=0, smooth=False, parent=None):
        data = bpy.data.meshes.new(name)
        data.from_pydata(vertices, [], faces)
        data.update()
        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(data)
        bm.free()
        obj = bpy.data.objects.new(name, data)
        collection.objects.link(obj)
        obj.data.materials.append(materials[material])
        obj.parent = parent
        for polygon in data.polygons:
            polygon.use_smooth = smooth
        if bevel:
            modifier = obj.modifiers.new("Soft edge", "BEVEL")
            modifier.width = bevel
            modifier.segments = 3
        objects.append(obj)
        return obj

    def root(name, kind, location, angle=0):
        obj = bpy.data.objects.new(name, None)
        collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler.z = angle
        obj.empty_display_size = 0.03
        obj["accessory"] = kind
        objects.append(obj)
        return obj

    def box(name, center, size, material, bevel=0.002, parent=None):
        vertices = [(center[0] + x * size[0] / 2,
                     center[1] + y * size[1] / 2,
                     center[2] + z * size[2] / 2)
                    for x, y, z in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                                    (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                 (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        return mesh(name, vertices, faces, material, bevel, parent=parent)

    def tube(name, points, radius, material, parent=None, closed=False, sides=8):
        points = [Vector(point) for point in points]
        vertices, faces = [], []
        for index, point in enumerate(points):
            previous = points[(index - 1) % len(points)] if closed or index else point
            following = points[(index + 1) % len(points)] if closed or index < len(points) - 1 else point
            tangent = (following - previous).normalized()
            axis = Vector((0, 0, 1)) if abs(tangent.z) < 0.9 else Vector((0, 1, 0))
            horizontal = tangent.cross(axis).normalized()
            vertical = tangent.cross(horizontal).normalized()
            vertices.extend(tuple(point + radius * (horizontal * math.cos(a * math.tau / sides)
                             + vertical * math.sin(a * math.tau / sides))) for a in range(sides))
        for index in range(len(points) if closed else len(points) - 1):
            next_index = (index + 1) % len(points)
            faces.extend((index * sides + j, index * sides + (j + 1) % sides,
                          next_index * sides + (j + 1) % sides, next_index * sides + j)
                         for j in range(sides))
        if not closed:
            faces.extend((tuple(range(sides - 1, -1, -1)),
                          tuple((len(points) - 1) * sides + j for j in range(sides))))
        return mesh(name, vertices, faces, material, smooth=True, parent=parent)

    def button(name, center, radius, material, parent=None):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1)
        scale = Matrix.Diagonal((radius, radius * 0.35, radius, 1))
        for vertex in bm.verts:
            vertex.co = scale @ vertex.co + Vector(center)
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()
        vertices = [tuple(vertex.co) for vertex in bm.verts]
        faces = [tuple(vertex.index for vertex in face.verts) for face in bm.faces]
        bm.free()
        return mesh(name, vertices, faces, material, smooth=True, parent=parent)

    # Hollow elliptical band keeps the interior editable and avoids a solid torso object.
    rx, ry, width, thickness, segments = waist_rx + 0.006, waist_ry + 0.006, 0.035, 0.004, 64
    vertices = []
    for radius_x, radius_y, z in ((rx, ry, waist_z - width / 2),
                                (rx, ry, waist_z + width / 2),
                                (rx - thickness, ry - thickness, waist_z + width / 2),
                                (rx - thickness, ry - thickness, waist_z - width / 2)):
        vertices.extend((radius_x * math.cos(i * math.tau / segments),
                         center_y + radius_y * math.sin(i * math.tau / segments), z)
                        for i in range(segments))
    faces = [(ring * segments + i, ring * segments + (i + 1) % segments,
              ((ring + 1) % 4) * segments + (i + 1) % segments,
              ((ring + 1) % 4) * segments + i) for ring in range(4) for i in range(segments)]
    belt = mesh("Belt_Leather", vertices, faces, "leather_dark", 0.0012, True)
    belt["accessory"] = "belt"
    for offset, suffix in ((-0.013, "Lower"), (0.013, "Upper")):
        points = [((rx + 0.0005) * math.cos(i * math.tau / segments),
                   center_y + (ry + 0.0005) * math.sin(i * math.tau / segments),
                   waist_z + offset) for i in range(segments)]
        tube("Belt_Seam_" + suffix, points, 0.00045, "thread", closed=True)

    front_y = center_y - ry - 0.004
    frame_points = []
    for cx, cz, start in ((0.019, 0.012, 0), (-0.019, 0.012, 90),
                          (-0.019, -0.012, 180), (0.019, -0.012, 270)):
        for step in range(5):
            angle = math.radians(start + step * 90 / 4)
            frame_points.append((cx + 0.005 * math.cos(angle), front_y - 0.002,
                                 waist_z + cz + 0.005 * math.sin(angle)))
    tube("Belt_Brass_Buckle", frame_points, 0.0028, "metal", closed=True)
    tube("Belt_Buckle_Pin", [(-0.016, front_y - 0.006, waist_z),
                             (0.019, front_y - 0.006, waist_z)], 0.0015, "metal")
    box("Belt_Keeper", (0.037, front_y + 0.001, waist_z), (0.007, 0.009, 0.039), "leather", 0.002)
    for index in range(3):
        angle = -math.pi / 2 - 0.43 - index * 0.13
        button(f"Belt_Hole_{index + 1:02}", (rx * math.cos(angle),
               center_y + (ry + 0.001) * math.sin(angle), waist_z), 0.0015, "leather_dark")

    pouch = root("Pouch_Left_Root", "pouch",
                 (waist_rx * 0.95 + 0.020, center_y - waist_ry * 0.55 - 0.023, waist_z - 0.060),
                 math.radians(22))
    box("Pouch_Left_Body", (0, 0, -0.003), (0.080, 0.038, 0.105), "leather", 0.012, pouch)
    for x in (-0.023, 0.023):
        box("Pouch_Belt_Loop", (x, 0.010, 0.055), (0.012, 0.011, 0.059), "leather_dark", 0.003, pouch)
    outline = [(-0.041, 0.055), (0.041, 0.055), (0.041, 0.018),
               (0.029, -0.004), (-0.029, -0.004), (-0.041, 0.018)]
    vertices = [(x, y, z) for y in (-0.027, -0.020) for x, z in outline]
    faces = [tuple(range(5, -1, -1)), tuple(range(6, 12))]
    faces += [(i, (i + 1) % 6, (i + 1) % 6 + 6, i + 6) for i in range(6)]
    mesh("Pouch_Flap", vertices, faces, "leather", 0.0035, parent=pouch)
    button("Pouch_Brass_Button", (0, -0.032, 0.011), 0.0055, "metal", pouch)
    tube("Pouch_Edge_Seam", [(-0.030, -0.021, 0.026), (-0.033, -0.021, -0.035),
                             (-0.025, -0.021, -0.045), (0.025, -0.021, -0.045),
                             (0.033, -0.021, -0.035), (0.030, -0.021, 0.026)],
         0.00065, "thread", pouch)

    sword = root("Sword_Separate_Root", "sword", (0.80, 0.05, 0))
    sword_start = len(objects)
    vertices = [(0, 0, 0.002)]
    for z, half_width in ((0.055, 0.018), (0.44, 0.021), (0.487, 0.018)):
        vertices.extend(((-half_width, 0, z), (0, -0.0035, z),
                         (half_width, 0, z), (0, 0.0035, z)))
    faces = [(0, 1 + i, 1 + (i + 1) % 4) for i in range(4)]
    faces += [(1 + ring * 4 + i, 1 + ring * 4 + (i + 1) % 4,
               1 + (ring + 1) * 4 + (i + 1) % 4, 1 + (ring + 1) * 4 + i)
              for ring in range(2) for i in range(4)]
    faces.append((9, 10, 11, 12))
    mesh("Sword_Blade", vertices, faces, "blade", 0.0005, parent=sword)
    tube("Sword_Guard", [(-0.068, 0, 0.485), (-0.050, 0, 0.494),
                          (0, 0, 0.501), (0.050, 0, 0.494), (0.068, 0, 0.485)],
         0.007, "metal", sword, sides=8)
    tube("Sword_Grip", [(0, 0, 0.509), (0, 0, 0.617)], 0.012, "leather_dark", sword, sides=12)
    for z in (0.511, 0.618):
        tube("Sword_Grip_Ferrule", [(0, 0, z - 0.003), (0, 0, z + 0.003)],
             0.014, "metal", sword, sides=16)
    spiral = [(0.0124 * math.cos(i * math.tau / 16), 0.0124 * math.sin(i * math.tau / 16),
               0.519 + i / 128 * 0.090) for i in range(129)]
    tube("Sword_Grip_Wrap", spiral, 0.00085, "leather", sword, sides=5)
    box("Sword_Pommel", (0, 0, 0.635), (0.033, 0.023, 0.028), "metal", 0.009, sword)
    for obj in objects[sword_start:]:
        obj["accessory"] = "sword"
    return objects
