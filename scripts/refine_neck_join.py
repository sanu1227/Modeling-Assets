"""Overlap-safe neck extension; preserves body UVs and clothing outside the join."""
import math
import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _smooth(t):
    t = min(1.0, max(0.0, t))
    return t*t*(3.0-2.0*t)


def repair_neck(body, head, skin_material):
    if head.get('NeckJoinRepairedV3'):
        return {'already_applied': True}
    center = Vector((.009, .0517, 0))
    coords = [v.co.copy() for v in body.data.vertices]
    surface = BVHTree.FromPolygons(coords, [tuple(p.vertices) for p in body.data.polygons])
    clothing_slot = next((i for i,m in enumerate(body.data.materials)
                          if m and m.name.startswith('Body_Clothing_Refined')), 0)
    skin_slot = next(i for i,m in enumerate(body.data.materials) if m == skin_material)

    # Restore the collar triangles recoloured by the earlier rectangular mask.
    # Actual bare neck is bounded by an ellipse, not a rectangular face region.
    for polygon in body.data.polygons:
        x,y,z = polygon.center
        radius = math.hypot((x-center.x)/.070, (y-center.y)/.066)
        if z > 1.425 and abs(x-center.x)<.09:
            if polygon.material_index == skin_slot and (radius>1.15 or y<-.015 and abs(x-center.x)>.036):
                polygon.material_index = clothing_slot
            elif radius < 1.10 and (y>-.015 or abs(x-center.x)<.036):
                polygon.material_index = skin_slot

    # Fade from the retained chest texture into the same skin as the new neck.
    # The colour test excludes the blue shirt inside this small spatial mask.
    tint = body.data.color_attributes.get('NeckSkinBlend')
    if tint is None:
        tint = body.data.color_attributes.new(name='NeckSkinBlend', type='FLOAT_COLOR', domain='POINT')
    for vertex, datum in zip(body.data.vertices, tint.data):
        factor = _smooth((vertex.co.z-1.390)/.035)
        datum.color=(factor,factor,factor,1)
    blend_material = body.data.materials[clothing_slot].copy()
    blend_material.name='Neck_Chest_ContinuousSkin'
    nodes,links=blend_material.node_tree.nodes,blend_material.node_tree.links
    shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    colour_input=shader.inputs['Base Color']
    source=colour_input.links[0].from_socket
    split=nodes.new('ShaderNodeSeparateColor')
    links.new(source,split.inputs[0])
    difference=nodes.new('ShaderNodeMath');difference.operation='SUBTRACT'
    links.new(split.outputs['Red'],difference.inputs[0])
    links.new(split.outputs['Green'],difference.inputs[1])
    skin_colour=nodes.new('ShaderNodeMapRange')
    skin_colour.clamp=True
    skin_colour.inputs['From Min'].default_value=.015
    skin_colour.inputs['From Max'].default_value=.085
    links.new(difference.outputs[0],skin_colour.inputs['Value'])
    # Leather is also red/brown, but much darker than the exposed chest.
    skin_light=nodes.new('ShaderNodeMapRange');skin_light.clamp=True
    skin_light.inputs['From Min'].default_value=.25
    skin_light.inputs['From Max'].default_value=.43
    links.new(split.outputs['Red'],skin_light.inputs['Value'])
    colour_gate=nodes.new('ShaderNodeMath');colour_gate.operation='MULTIPLY'
    links.new(skin_colour.outputs['Result'],colour_gate.inputs[0])
    links.new(skin_light.outputs['Result'],colour_gate.inputs[1])
    attribute=nodes.new('ShaderNodeVertexColor');attribute.layer_name=tint.name
    multiply=nodes.new('ShaderNodeMath');multiply.operation='MULTIPLY'
    links.new(attribute.outputs['Color'],multiply.inputs[0])
    links.new(colour_gate.outputs[0],multiply.inputs[1])
    mix=nodes.new('ShaderNodeMixRGB')
    links.new(multiply.outputs[0],mix.inputs[0])
    links.new(source,mix.inputs[1])
    mix.inputs[2].default_value=skin_material.diffuse_color
    links.new(mix.outputs[0],colour_input)
    roughness=nodes.new('ShaderNodeMath');roughness.operation='MULTIPLY_ADD'
    roughness.inputs[1].default_value=-.21;roughness.inputs[2].default_value=.73
    links.new(multiply.outputs[0],roughness.inputs[0])
    links.new(roughness.outputs[0],shader.inputs['Roughness'])
    sss=nodes.new('ShaderNodeMath');sss.operation='MULTIPLY';sss.inputs[1].default_value=.06
    links.new(multiply.outputs[0],sss.inputs[0])
    links.new(sss.outputs[0],shader.inputs['Subsurface Weight'])
    shader.inputs['Subsurface Radius'].default_value=(1,.45,.25)
    shader.inputs['Subsurface Scale'].default_value=.015
    strength=nodes.new('ShaderNodeMath');strength.operation='MULTIPLY_ADD'
    strength.inputs[1].default_value=-.15;strength.inputs[2].default_value=.18
    links.new(multiply.outputs[0],strength.inputs[0])
    for node in nodes:
        if node.type=='NORMAL_MAP':
            links.new(strength.outputs[0],node.inputs['Strength'])
    body.data.materials.append(blend_material)
    blend_slot=len(body.data.materials)-1
    for polygon in body.data.polygons:
        x,y,z=polygon.center
        radius=math.hypot((x-center.x)/.070,(y-center.y)/.075)
        chest_front=abs(x-center.x)<.043 and y<.030
        if 1.385<z<1.476 and (radius<1.16 or chest_front) and (y>-.015 or abs(x-center.x)<.043):
            polygon.material_index=blend_slot

    moved = 0
    for vertex in body.data.vertices:
        x,y,z = vertex.co
        if z <= 1.430 or z > 1.476:
            continue
        radius = math.hypot((x-center.x)/.075, (y-center.y)/.065)
        region = 1.0-_smooth((radius-1.02)/.26)
        # The projecting front collar remains leather with its original UVs.
        if y < -.015 and abs(x-center.x)>.036:
            region *= 1.0-_smooth((-.015-y)/.012)
        amount = .34*_smooth((z-1.430)/.025)*region
        if amount>0:
            vertex.co.x = center.x+(x-center.x)*(1-amount)
            vertex.co.y = center.y+(y-center.y)*(1-amount)
            moved += 1
    body.data.update()

    bm = bmesh.new()
    bm.from_mesh(head.data)
    bottom = min(v.co.z for v in bm.verts)
    edges = [e for e in bm.edges if e.is_boundary and all(abs(v.co.z-bottom)<.0001 for v in e.verts)]
    if not edges:
        bm.free()
        raise ValueError('Expected the fitted head boundary at z=1.465m')
    # The neck is the only boundary on this horizontal cut; preserve its order.
    adjacency = {}
    for edge in edges:
        a,b=edge.verts
        adjacency.setdefault(a,[]).append(b)
        adjacency.setdefault(b,[]).append(a)
    first = next(iter(adjacency))
    ordered,previous,current = [first],None,first
    while True:
        nxt = next(v for v in adjacency[current] if v != previous)
        if nxt == first:
            break
        ordered.append(nxt)
        previous,current=current,nxt
        if len(ordered)>len(adjacency):
            bm.free()
            raise ValueError('Neck boundary is not a simple loop')
    ring = ordered
    anchors = [v.co.copy() for v in ring]
    if skin_material.name not in head.data.materials:
        head.data.materials.append(skin_material)
    neck_material = next(i for i,m in enumerate(head.data.materials) if m == skin_material)
    created=0
    for z in [1.455,1.445,1.435,1.425]:
        next_ring=[]
        for anchor in anchors:
            origin=Vector((center.x,center.y,z))
            direction=Vector((anchor.x-center.x,anchor.y-center.y,0)).normalized()
            hit,normal,index,distance=surface.ray_cast(origin,direction,.20)
            if hit is None:
                hit=Vector((anchor.x,anchor.y,z))
            # Root stays just inside the retained torso, hiding the open rim.
            hit -= direction*.007
            blend=_smooth((bottom-z)/.040)
            point=Vector((anchor.x,anchor.y,z)).lerp(hit,blend)
            next_ring.append(bm.verts.new(point))
        for i in range(len(ring)):
            j=(i+1)%len(ring)
            face=bm.faces.new((ring[i],ring[j],next_ring[j],next_ring[i]))
            face.material_index=neck_material
            face.smooth=True
            created+=1
        ring=next_ring
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(head.data)
    bm.free()
    head.data.update()
    head['NeckJoinRepairedV3']=True
    head['NeckJoinRepair']='Four anatomical neck rings extend into torso; old overlapping neck inset; collar colour restored'
    return {'body_neck_vertices_inset':moved,'new_neck_faces':created,'neck_root_z':1.425}
