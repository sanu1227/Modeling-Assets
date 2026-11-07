"""Remove the circular cheek deformation while retaining the fitted lower face."""
from pathlib import Path
import math

import bpy
from mathutils import Vector


def _smooth(value):
    value=max(0.0,min(1.0,value))
    return value*value*(3.0-2.0*value)


def _fitted_source(co):
    x,y,z=co
    blend=_smooth((z-1.455)/.060)
    x_shift=.009*(1-blend)-.012*blend
    neck=1-_smooth((z-1.455)/.045)
    y=-.0225+(y+.0225)*(1+.09*neck)
    return Vector((x+x_shift,y+.0742,z+.010+.065*x*blend))


def refine_geometry(head,eyes):
    """Restore continuous upper-cheek topology from its uncreased source shape."""
    if head.get('FaceGeometryV005'):
        return {'already_applied':True}
    root=Path(__file__).resolve().parents[1]
    with bpy.data.libraries.load(str(root/'assets/Character/Adventurer_Model_v001.blend'),link=False) as (_,loaded):
        loaded.objects=['Body_Female_Edit']
    source=loaded.objects[0]
    source_ids=source.data.attributes['source_vertex_id'].data
    source_points={identifier.value:vertex.co.copy() for vertex,identifier in zip(source.data.vertices,source_ids)}
    eyes_before=[v.co.copy() for v in eyes.data.vertices]
    max_distance=0.0
    changed=0
    for vertex,identifier in zip(head.data.vertices,head.data.attributes['source_vertex_id'].data):
        original=source_points.get(identifier.value)
        if original is None or not 1.55<vertex.co.z<1.69:
            continue
        x,y,z=original
        # v003 protected a 26mm circle around each eye, then tapered the outer
        # cheek. That introduced a curved step in X/Z. Restore the continuous
        # source across the upper cheek, fading below it into the fitted jaw.
        weight=_smooth((z-1.555)/.025)*(1-_smooth((z-1.635)/.030))
        weight*=_smooth((abs(x)-.015)/.015)*_smooth((-.060-y)/.035)
        if weight<=0:
            continue
        desired=_fitted_source(original)
        delta=(desired-vertex.co)*weight
        if delta.length>1e-8:
            vertex.co+=delta
            changed+=1
            max_distance=max(max_distance,delta.length)
    head.data.update()
    # Keep the planar face texture aligned with the approved reference.
    uv=head.data.uv_layers.get('Reference_FrontUV')
    if uv:
        scale=1.75/(1484-16)
        for loop in head.data.loops:
            co=head.data.vertices[loop.vertex_index].co
            uv.data[loop.index].uv=(.5+co.x/(1024*scale),(co.z/scale+52)/1536)
    assert all((v.co-before).length==0 for v,before in zip(eyes.data.vertices,eyes_before))
    assert all(math.isfinite(c) for vertex in head.data.vertices for c in vertex.co)
    head['FaceGeometryV005']=True
    head['FaceGeometryFix']='Removed circular upper-cheek taper by restoring continuous source coordinates; jaw and eye aperture retained'
    # The appended source object is never linked into the scene or rendered.
    bpy.data.objects.remove(source,do_unlink=True)
    return {'changed_vertices':changed,'maximum_displacement_m':max_distance,
            'eye_geometry_unchanged':True,'source':'v001 source_vertex_id upper-cheek coordinates'}
