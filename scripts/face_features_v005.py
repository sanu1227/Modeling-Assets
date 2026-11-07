"""Close the existing mouth aperture using its verified MakeHuman lip rings.

No topology, UV, materials, eyes, or other objects are changed.
"""
from math import isfinite


def _quad_loop(mesh, start, next_index):
    neighbors = [set() for _ in mesh.vertices]
    faces = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        neighbors[a].add(b)
        neighbors[b].add(a)
    for face in mesh.polygons:
        for vertex in face.vertices:
            faces[vertex].append(set(face.vertices))
    ring = [start, next_index]
    while len(ring) < 100:
        previous, current = ring[-2:]
        blocked = {previous}
        for face in faces[current]:
            if previous in face:
                blocked.update(face)
        candidates = neighbors[current] - blocked
        if len(candidates) != 1:
            raise ValueError(f'Lip ring is ambiguous at vertex {current}')
        following = candidates.pop()
        if following == start:
            return ring
        if following in ring:
            raise ValueError('Lip ring does not close at its starting vertex')
        ring.append(following)
    raise ValueError('Lip ring exceeded the expected local size')


def refine_features(head, eyes=None, collection=None):
    """Reduce the triangular mouth-corner holes, retaining a fine closed-lip seam."""
    mesh = head.data
    ids = mesh.attributes.get('source_vertex_id')
    if ids is None:
        raise ValueError('The verified source_vertex_id attribute is required')
    lookup = {item.value: i for i, item in enumerate(ids.data)}
    # Each is a complete mouth loop, including both upper and lower lips.
    # 474/520 are two depths of the upper lip, NOT upper/lower counterparts.
    rings = [(537, 538, .96), (520, 521, .92), (474, 473, .75), (468, 465, .18)]
    changes = {}
    ring_report = []
    for source_start, source_next, strength in rings:
        ring = _quad_loop(mesh, lookup[source_start], lookup[source_next])
        if len(ring) != 38:
            raise ValueError(f'Unexpected mouth ring size: {len(ring)}')
        for index in ring:
            p = mesh.vertices[index].co
            x = p.x + .012
            # Follow the existing gentle smile and whole-head tilt.
            seam = 1.54780 + .00110 * min(abs(x) / .020, 1.0) ** 1.4 + .065 * x
            delta = (seam - p.z) * strength
            if not isfinite(delta) or abs(delta) > .002:
                raise ValueError('Unexpected mouth coordinate or displacement')
            changes[index] = delta
        ring_report.append({'upper_source': source_start, 'count': len(ring), 'strength': strength})
    for index, delta in changes.items():
        mesh.vertices[index].co.z += delta
    mesh.update()
    return {'method': 'verified_quad_lip_rings', 'changed_vertices': len(changes),
            'max_displacement_mm': max(abs(v) for v in changes.values()) * 1000,
            'rings': ring_report, 'eyes_changed': False, 'uv_changed': False}
