"""Small continuous facial proportion edits; retain the fitted eye sockets."""
import math


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def improve_shape(head):
    before = [vertex.co.copy() for vertex in head.data.vertices]
    old_normals = [face.normal.copy() for face in head.data.polygons]
    for vertex, original in zip(head.data.vertices, before):
        x, y, z = original
        u = x + .012
        h = z - .065 * u
        front = smooth((.018 - y) / .065)
        lower_face = math.exp(-((h - 1.535) / .032) ** 4)
        outer = smooth((abs(u) - .020) / .025)
        # A gentle heart-shaped lower face, continuous across both cheeks.
        vertex.co.x -= u * .055 * lower_face * outer * front
        chin = math.exp(-(u / .023) ** 4 - ((h - 1.516) / .011) ** 2) * front
        vertex.co.z += .0013 * chin
        vertex.co.y += .0007 * chin
        # Lift the nose tip very slightly and narrow the alae, retaining the bridge.
        nose = math.exp(-(u / .019) ** 4 - ((h - 1.576) / .013) ** 2)
        nose *= smooth((-.052 - y) / .026)
        vertex.co.x -= u * .055 * nose
        vertex.co.y += .00065 * nose
        vertex.co.z += .00075 * nose
        # Lift the outer lip corners without reopening the closed lip rings.
        mouth = math.exp(-(u / .027) ** 6 - ((h - 1.548) / .014) ** 4)
        mouth *= smooth((-.045 - y) / .025)
        vertex.co.x += u * .035 * mouth
        vertex.co.z += .00055 * (abs(u) / .022) ** 2 * mouth
    head.data.update()
    displacements = [(vertex.co - old).length for vertex, old in zip(head.data.vertices, before)]
    assert all(math.isfinite(c) for vertex in head.data.vertices for c in vertex.co)
    assert max(displacements) < .004
    flipped = sum(a.dot(face.normal) < 0 for a, face in zip(old_normals, head.data.polygons))
    assert flipped == 0, f'Flipped facial polygons: {flipped}'
    head['BeautyShapeV006'] = 'Gentle jaw taper, rounded chin, delicate alae, subtle smile'
    return {'changed_vertices': sum(d > 1e-7 for d in displacements),
            'maximum_displacement_mm': max(displacements) * 1000,
            'flipped_polygons': flipped, 'uv_unchanged': True}
