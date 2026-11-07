"""Editable, layered chin-length bob for a Z-up character facing -Y."""
import math

import bpy
from mathutils import Vector


def build_hair(head_top, chin_z, head_width, head_depth, center_y, materials, collection):
    """Return hair objects; dimensions are full head width/depth, in scene units."""
    height = head_top - chin_z
    if min(height, head_width, head_depth) <= 0:
        raise ValueError("Head dimensions must be positive")
    objects = []
    rx, ry = head_width * 0.60, head_depth * 0.60
    cz, rz = head_top - height * 0.495, height * 0.53

    def mesh_object(name, vertices, faces, material, subdivision=1):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj.data.materials.append(material)
        for polygon in mesh.polygons:
            polygon.use_smooth = True
        if subdivision:
            modifier = obj.modifiers.new("Smooth hair clump", "SUBSURF")
            modifier.levels = subdivision
            modifier.render_levels = subdivision
        obj["part"] = "Hair"
        objects.append(obj)
        return obj

    def smoothstep(value):
        value = max(0.0, min(1.0, value))
        return value * value * (3 - 2 * value)

    def end_angle(theta):
        angle = abs((theta + math.pi) % (2 * math.pi) - math.pi)
        return 1.03 + 1.67 * smoothstep((angle - 0.45) / 0.60)

    def scalp(theta, phi, offset=0.0):
        # A fuller lower silhouette produces a bob instead of a spherical helmet.
        radius = math.sin(phi) if phi < 1.57 else 1 - 0.14 * ((phi - 1.57) / 1.13) ** 2
        ripple = 1 + 0.018 * math.cos(9 * theta + 1.4 * phi)
        x = (rx + offset) * radius * math.sin(theta) * ripple
        y = center_y - (ry + offset) * radius * math.cos(theta) * ripple
        z = cz + (rz + offset) * math.cos(phi)
        return Vector((x, y, z))

    # A closed crown and open face aperture. The boundary stops above the eyes.
    segments, rings = 48, 15
    vertices = [(0, center_y, cz + rz)]
    for ring in range(1, rings + 1):
        for segment in range(segments):
            theta = segment * 2 * math.pi / segments
            angle = abs((theta + math.pi) % (2 * math.pi) - math.pi)
            # Keep the underlayer behind the shaped fringe, not as a dark forehead band.
            cap_end = min(end_angle(theta) - 0.19,
                          0.72 + 1.85 * smoothstep((angle - 0.60) / 0.60))
            cap_end -= 0.075 * (0.5 + 0.5 * math.sin(7 * theta + 0.8)) * smoothstep(angle / 1.2)
            phi = cap_end * ring / rings
            point = scalp(theta, phi, -height * 0.015)
            point.y = center_y + (point.y - center_y) * (1 - 0.12 * max(0, math.cos(theta)) ** 4)
            vertices.append(tuple(point))
    faces = [(0, 1 + i, 1 + (i + 1) % segments) for i in range(segments)]
    for ring in range(rings - 1):
        first, following = 1 + ring * segments, 1 + (ring + 1) * segments
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((first + i, following + i, following + j, first + j))
    cap = mesh_object("Hair_Bob_Underlayer", vertices, faces, materials["hair"])
    solidify = cap.modifiers.new("Hair shell edge", "SOLIDIFY")
    solidify.thickness = height * 0.005
    solidify.offset = -1

    def sample_curve(points, sample_count=25):
        points = [Vector(point) for point in points]
        result = []
        for index in range(sample_count):
            parameter = index / (sample_count - 1) * (len(points) - 1)
            segment = min(len(points) - 2, int(parameter))
            t = parameter - segment
            p0 = points[max(0, segment - 1)]
            p1, p2 = points[segment], points[segment + 1]
            p3 = points[min(len(points) - 1, segment + 2)]
            result.append(0.5 * ((2 * p1) + (-p0 + p2) * t
                               + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                               + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
        return result

    def lock(name, controls, width, thickness, material, front=False):
        path = sample_curve(controls)
        vertices, faces = [], []
        sides = 8
        for i, point in enumerate(path):
            tangent = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
            if front:
                normal = Vector((0, -1, 0))
            else:
                normal = Vector((point.x / (rx * rx), (point.y - center_y) / (ry * ry),
                                 (point.z - cz) / (rz * rz))).normalized()
            normal = normal - tangent * normal.dot(tangent)
            if normal.length < 0.001:
                normal = Vector((0, -1, 0)) - tangent * tangent.dot(Vector((0, -1, 0)))
            normal.normalize()
            across = normal.cross(tangent).normalized()
            t = i / (len(path) - 1)
            taper = (0.38 + 0.62 * math.sin(math.pi * min(t * 1.25, 1))) * (1 - 0.91 * t ** 5)
            for j in range(sides):
                angle = j * 2 * math.pi / sides
                position = point + across * (width * taper * math.cos(angle))
                position += normal * (thickness * max(0.25, taper) * math.sin(angle))
                vertices.append(tuple(position))
        for i in range(len(path) - 1):
            for j in range(sides):
                k = (j + 1) % sides
                faces.append((i * sides + j, i * sides + k, (i + 1) * sides + k, (i + 1) * sides + j))
        faces.extend([tuple(range(sides - 1, -1, -1)),
                      tuple((len(path) - 1) * sides + j for j in range(sides))])
        return mesh_object(name, vertices, faces, material)

    # Separate broad locks create sculpted directional flow around the crown and nape.
    for index in range(23):
        theta = 0.86 + index * (2 * math.pi - 1.72) / 22
        end = end_angle(theta) - 0.025 + 0.025 * math.sin(index * 1.7)
        controls = []
        for step in range(6):
            t = step / 5
            phi = 0.23 + (end - 0.23) * t
            twist = 0.15 * math.sin(math.pi * t) * (1 if theta < math.pi else -1)
            controls.append(scalp(theta + twist, phi, height * (0.014 + 0.007 * math.sin(index))))
        material = materials["hair_highlight"] if index % 5 == 1 else materials["hair"]
        lock(f"Hair_Bob_Lock_{index + 1:02}", controls, head_width * 0.078,
             height * 0.016, material)

    # The longer fringe sweeps from a side part across the high forehead and around the cheek.
    for index in range(7):
        shift = (index - 3) / 6
        controls = [
            (head_width * (0.22 + 0.06 * shift), center_y - head_depth * (0.10 + 0.012 * index), head_top - height * (0.045 + 0.004 * index)),
            (head_width * (0.05 - 0.04 * shift), center_y - head_depth * (0.30 + 0.015 * index), head_top - height * (0.10 + 0.015 * index)),
            (-head_width * (0.28 + 0.025 * shift), center_y - head_depth * (0.43 + 0.009 * index), head_top - height * (0.23 + 0.018 * index)),
            (-head_width * (0.51 + 0.024 * shift), center_y - head_depth * (0.32 + 0.02 * shift), head_top - height * (0.40 + 0.025 * index)),
            (-head_width * (0.57 + 0.025 * shift), center_y - head_depth * (0.18 + 0.04 * shift), head_top - height * (0.69 + 0.018 * index)),
            (-head_width * (0.47 + 0.06 * shift), center_y - head_depth * (0.08 - 0.04 * shift), chin_z + height * (0.12 - 0.01 * index)),
        ]
        lock(f"Hair_Swept_Fringe_{index + 1:02}", controls, head_width * 0.067,
             height * 0.015, materials["hair_highlight"] if index in (1, 5) else materials["hair"], front=True)

    # Shorter, flatter locks flow behind the opposite ear instead of obscuring the face.
    for index in range(5):
        t = index / 4
        controls = [
            (head_width * (0.22 + 0.02 * index), center_y - head_depth * (0.10 + 0.015 * index), head_top - height * 0.045),
            (head_width * (0.48 + 0.01 * index), center_y - head_depth * (0.25 - 0.04 * t), head_top - height * 0.23),
            (head_width * 0.59, center_y - head_depth * (0.17 - 0.06 * t), head_top - height * 0.43),
            (head_width * 0.55, center_y + head_depth * (0.05 + 0.04 * t), head_top - height * 0.70),
            (head_width * (0.43 + 0.06 * t), center_y + head_depth * 0.10, chin_z + height * (0.14 + 0.035 * t)),
        ]
        lock(f"Hair_Tucked_Lock_{index + 1:02}", controls, head_width * 0.06,
             height * 0.012, materials["hair_highlight"] if index == 2 else materials["hair"], front=True)
    return objects
