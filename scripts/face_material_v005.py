"""Warm, editable facial skin shading that retains the approved facial features."""
import math

import bpy


def _smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def refine_materials(head, eyes, body):
    """Modify materials/colour attributes only, never geometry or external files."""
    if head.get('FaceMaterialsV005'):
        return {'already_applied': True}
    original_vertices = [tuple(v.co) for v in head.data.vertices]
    skin = (.66, .34, .205, 1)
    blush = (.70, .245, .175)
    face = head.data.materials[0].copy()
    face.name = 'Face_WarmSkin_Features_v005'
    head.data.materials[0] = face
    face.diffuse_color = skin
    nodes, links = face.node_tree.nodes, face.node_tree.links
    shader = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    shader.inputs['Roughness'].default_value = .52
    shader.inputs['Specular IOR Level'].default_value = .25
    shader.inputs['Subsurface Weight'].default_value = .055
    shader.inputs['Subsurface Radius'].default_value = (1, .43, .22)
    shader.inputs['Subsurface Scale'].default_value = .012

    tint = head.data.color_attributes.new(name='FaceSkinTintV005', type='FLOAT_COLOR', domain='POINT')
    lip = head.data.color_attributes.new(name='LipFinishV005', type='FLOAT_COLOR', domain='POINT')
    for vertex, colour, finish in zip(head.data.vertices, tint.data, lip.data):
        x, y, z = vertex.co
        front = _smooth((-.015-y)/.040)
        cheek = math.exp(-((abs(x+.012)-.043)/.021)**2-((z-1.579)/.019)**2)
        amount = .12 * cheek * front
        colour.color = tuple(a*(1-amount)+b*amount for a,b in zip(skin[:3],blush))+(1,)
        # Surface finish follows the mouth region without changing its projected colour.
        mouth = math.exp(-((x+.012)/.022)**6-((z-1.548)/.010)**4)
        mouth *= _smooth((-.050-y)/.014)
        finish.color = (mouth,mouth,mouth,1)
    tint_node = nodes.new('ShaderNodeVertexColor')
    tint_node.layer_name = tint.name
    mix = next(n for n in nodes if n.type == 'MIX_RGB')
    links.new(tint_node.outputs['Color'],mix.inputs[1])
    lip_node = nodes.new('ShaderNodeVertexColor')
    lip_node.layer_name = lip.name
    roughness = nodes.new('ShaderNodeMapRange')
    roughness.inputs['To Min'].default_value = .52
    roughness.inputs['To Max'].default_value = .34
    roughness.clamp = True
    links.new(lip_node.outputs['Color'],roughness.inputs['Value'])
    links.new(roughness.outputs['Result'],shader.inputs['Roughness'])

    # Unify the neck and ear skin while retaining their own geometry and materials.
    for index, material in enumerate(list(head.data.materials)[1:], start=1):
        if not material:
            continue
        material = material.copy()
        head.data.materials[index] = material
        material.name = material.name.split('.')[0] + '_v005'
        material.diffuse_color = skin
        bsdf = next((n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
        if bsdf is None:
            continue
        bsdf.inputs['Base Color'].default_value = skin
        bsdf.inputs['Roughness'].default_value = .52
        bsdf.inputs['Specular IOR Level'].default_value = .25
        bsdf.inputs['Subsurface Weight'].default_value = .055
        bsdf.inputs['Subsurface Radius'].default_value = (1,.43,.22)
        bsdf.inputs['Subsurface Scale'].default_value = .012
        if 'Ear_' in material.name:
            bsdf.inputs['Subsurface Weight'].default_value = .10
            bsdf.inputs['Emission Strength'].default_value = 0
    ear_tint = head.data.color_attributes.get('EarTintV004')
    if ear_tint:
        for vertex, datum in zip(head.data.vertices,ear_tint.data):
            x,y,z=vertex.co
            weight = _smooth((x-.045)/.014)*_smooth((y+.004)/.018)
            weight *= _smooth((z-1.558)/.012)*(1-_smooth((z-1.626)/.012))
            inner=math.exp(-((y-.024)/.015)**2-((z-1.597)/.016)**2)
            amount=.14*inner*weight
            datum.color=tuple(a*(1-amount)+b*amount for a,b in zip(skin[:3],(.65,.255,.18)))+(1,)
    for material in body.data.materials:
        if not material or not material.name.startswith('Neck_Chest_ContinuousSkin'):
            continue
        for node in material.node_tree.nodes:
            if node.type == 'MIX_RGB':
                node.inputs[2].default_value = skin
            elif node.type == 'MATH' and node.operation == 'MULTIPLY' and abs(node.inputs[1].default_value-.035)<1e-6:
                node.inputs[1].default_value = .055
            elif node.type == 'MATH' and node.operation == 'MULTIPLY_ADD' and abs(node.inputs[2].default_value-.73)<1e-6:
                node.inputs[1].default_value = -.21
    # Keep the hazel iris and painted eyelashes, adjusting only surface response.
    eye_material = eyes.data.materials[0].copy()
    eye_material.name = 'Eyes_ApprovedHazel_v005'
    eyes.data.materials[0] = eye_material
    eye_shader = next(n for n in eye_material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    eye_shader.inputs['Roughness'].default_value = .22
    eye_shader.inputs['Specular IOR Level'].default_value = .25
    eye_shader.inputs['Coat Weight'].default_value = .06
    eye_shader.inputs['Coat Roughness'].default_value = .18
    assert original_vertices == [tuple(v.co) for v in head.data.vertices]
    head['FaceMaterialsV005'] = True
    return {'skin_linear_rgb':list(skin[:3]),'cheek_blush_max':.12,
            'skin_roughness':.52,'lip_roughness':.34,
            'approved_eye_texture_preserved':True,'geometry_unchanged':True}


if __name__ == '__main__':
    from pathlib import Path
    from mathutils import Vector
    import json
    root=Path(__file__).resolve().parents[1]
    bpy.ops.wm.open_mainfile(filepath=str(root/'assets/Character/Refined_v004/Adventurer_Refined_v004.blend'))
    head=bpy.data.objects['Head_Sculpted_ReferenceUV']
    result=refine_materials(head,bpy.data.objects['Eyes_ReferenceUV'],bpy.data.objects['Body_Clothing_Tripo_Refined'])
    scene=bpy.context.scene
    scene.cycles.samples=24
    try:
        preferences=bpy.context.preferences.addons['cycles'].preferences
        preferences.compute_device_type='OPTIX'
        preferences.get_devices()
        for device in preferences.devices:
            device.use=device.type=='OPTIX'
        if any(device.use for device in preferences.devices):
            scene.cycles.device='GPU'
    except (RuntimeError,TypeError):
        pass
    scene.render.resolution_x=scene.render.resolution_y=800
    for name,location in [('front',(0,-4,1.59)),('quarter',(2.2,-4,1.59))]:
        scene.camera.location=location
        scene.camera.rotation_euler=(Vector((0,.02,1.59))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
        scene.camera.data.ortho_scale=.36
        scene.render.filepath=str(root/f'logs/face_v005_material_{name}.png')
        bpy.ops.render.render(write_still=True)
    print('FACE_MATERIAL_V005_OK',json.dumps(result))
