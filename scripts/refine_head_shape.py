"""Small anatomical edits for the untransformed v001 MakeHuman head.

Call before fitting the head to Tripo. Coordinates are metres in the v001 world
space. This edits existing topology only; it does not cut, weld, add eyes, or
change materials. The parent assembly owns the head translation and UVs.
"""
import math


def _smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _curve(z, points):
    if z <= points[0][0] or z >= points[-1][0]:
        return 0.0
    for (za, a), (zb, b) in zip(points, points[1:]):
        if za <= z <= zb:
            t = _smooth((z - za) / (zb - za))
            return a + (b - a) * t
    return 0.0


def sculpt_head(body, *, chin_lift=0.018, mouth_lift=0.00615):
    """Refine v001 jaw/lips/nose while retaining the eye sockets and skull.

    Source mouth aperture: vertex 520 at z=1.531315 and 474 at z=1.532394.
    Source visible chin starts at z~1.490; the joint-jaw value 1.505 is not the
    lower silhouette. With the caller's +0.010m Z translation, the targets are
    chin~1.518 and mouth seam~1.548. The symmetric shape can be tilted/offset
    later without baking a pose into these edits.
    """
    if body.get("HeadShapeRefinedV3"):
        return {"already_applied": True}
    matrix = body.matrix_world.copy()
    inverse = matrix.inverted()
    mouth_line = (1.5313154459 + 1.5323941708) * 0.5
    lift_curve = [
        (1.455, 0.0), (1.470, 0.0), (1.490, chin_lift),
        (1.508, chin_lift * 0.72), (mouth_line, mouth_lift),
        (1.555, 0.004), (1.568, 0.003), (1.585, 0.0),
    ]
    changed = 0
    max_displacement = 0.0
    for vertex in body.data.vertices:
        p = matrix @ vertex.co
        x, y, z = p
        if not (1.465 < z < 1.642) or y > -0.055:
            continue
        before = p.copy()
        front = _smooth((-0.055 - y) / 0.050)
        # Explicit exclusion keeps the existing lids registered to the eyes.
        eye_distance = math.hypot(abs(x) - 0.0306743, z - 1.5986466)
        outside_eye = _smooth((eye_distance - 0.026) / 0.008)
        face = front * outside_eye

        # Shorten the lower face, leaving the cranium and neck join in place.
        p.z += _curve(z, lift_curve) * face

        # Reduce the outer cheek to ~0.125m; do not use ear-to-ear width.
        taper = _curve(z, [
            (1.477, 0.0), (1.497, 0.12), (1.530, 0.115),
            (1.575, 0.085), (1.615, 0.065), (1.642, 0.0),
        ])
        outside_features = _smooth((abs(x) - 0.023) / 0.022)
        p.x *= 1.0 - taper * face * outside_features

        # A monotonic squeeze narrows the real mouth opening to a fine seam.
        # Its derivative remains positive; there is no lip-loop inversion.
        mouth_side = 1.0 - _smooth((abs(x) - 0.018) / 0.016)
        mouth_front = _smooth((-0.120 - y) / 0.018)
        mouth_height = 1.0 - _smooth((abs(z - mouth_line) - 0.009) / 0.014)
        mouth_weight = mouth_side * mouth_front * mouth_height
        p.z -= 0.00060 * math.tanh((z - mouth_line) / 0.00070) * mouth_weight

        # Preserve the nose bridge; narrow the lower alae slightly.
        nose = math.exp(-((z - 1.559) / 0.012) ** 2 - (x / 0.024) ** 4)
        nose *= _smooth((-0.143 - y) / 0.010)
        p.x *= 1.0 - 0.06 * nose
        p.y += 0.0008 * nose

        distance = (p - before).length
        if distance > 1e-9:
            vertex.co = inverse @ p
            changed += 1
            max_displacement = max(max_displacement, distance)
    body.data.update()
    body["HeadShapeRefinedV3"] = True
    body["HeadShapeRefinement"] = "Closed lip seam; raised lower face; tapered jaw; delicate alae"
    return {
        "changed_vertices": changed,
        "maximum_displacement_m": max_displacement,
        "source_mouth_line_z": mouth_line,
        "target_mouth_line_after_fit_z": mouth_line + mouth_lift + 0.010,
        "target_chin_after_fit_z": 1.490 + chin_lift + 0.010,
    }
