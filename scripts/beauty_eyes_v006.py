"""Procedural hazel eyes on the retained, fitted eyeball surfaces."""
from pathlib import Path
import math
import bpy


def eye_material(name, center, iris_radius=.0076):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.diffuse_color = (.24, .13, .035, 1)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Specular IOR Level'].default_value = .33
    shader.inputs['IOR'].default_value = 1.376
    shader.inputs['Coat Weight'].default_value = .45
    shader.inputs['Coat Roughness'].default_value = .05
    shader.inputs['Subsurface Weight'].default_value = .01
    shader.inputs['Subsurface Scale'].default_value = .001

    def math_node(operation, a, b=None):
        node = nodes.new('ShaderNodeMath')
        node.operation = operation
        for i, value in enumerate((a, b)):
            if value is None:
                continue
            if isinstance(value, (float, int)):
                node.inputs[i].default_value = value
            else:
                links.new(value, node.inputs[i])
        return node.outputs[0]

    position = nodes.new('ShaderNodeTexCoord')
    split = nodes.new('ShaderNodeSeparateXYZ')
    links.new(position.outputs['Object'], split.inputs[0])
    dx = math_node('SUBTRACT', split.outputs['X'], center[0])
    dz = math_node('SUBTRACT', split.outputs['Z'], center[2])
    # Account for the existing head tilt in the iris coordinate frame.
    dz = math_node('SUBTRACT', dz, math_node('MULTIPLY', dx, .065))
    radial = math_node('DIVIDE', math_node('SQRT', math_node('ADD',
        math_node('MULTIPLY', dx, dx), math_node('MULTIPLY', dz, dz))), iris_radius)
    angle = math_node('ARCTAN2', dz, dx)
    phase = math_node('ADD', math_node('MULTIPLY', angle, 87),
                      math_node('MULTIPLY', radial, 11))
    fibers = math_node('MULTIPLY', math_node('SINE', phase), .20)
    # Independent fine fibers vary the radial spokes without a bitmap source.
    secondary = math_node('SINE', math_node('ADD', math_node('MULTIPLY', angle, 151),
                         math_node('MULTIPLY', radial, 17)))
    fiber_value = math_node('ADD', math_node('ADD', fibers, math_node('MULTIPLY', secondary, .10)), .50)
    fiber_colors = nodes.new('ShaderNodeValToRGB')
    fiber_colors.color_ramp.elements[0].color = (.028, .012, .003, 1)
    fiber_colors.color_ramp.elements[1].color = (.15, .075, .014, 1)
    links.new(fiber_value, fiber_colors.inputs['Fac'])
    radial_colors = nodes.new('ShaderNodeValToRGB')
    ramp = radial_colors.color_ramp
    ramp.interpolation = 'LINEAR'
    ramp.elements.remove(ramp.elements[1])
    entries = [(0, (.0015,.0012,.0008,1)), (.36,(.0015,.0012,.0008,1)),
               (.39,(.075,.029,.007,1)), (.48,(.19,.090,.018,1)),
               (.81,(.070,.045,.012,1)), (.91,(.035,.020,.007,1)),
               (.965,(.018,.012,.007,1)), (.995,(.018,.012,.007,1)),
               (1,(.47,.49,.47,1))]
    for index,(position,color) in enumerate(entries):
        element=ramp.elements[0] if index==0 else ramp.elements.new(position)
        element.position=position
        element.color=color
    links.new(radial,radial_colors.inputs['Fac'])
    iris_only = math_node('MULTIPLY', math_node('GREATER_THAN',radial,.39),
                          math_node('LESS_THAN',radial,.93))
    mix=nodes.new('ShaderNodeMixRGB')
    mix.blend_type='MIX'
    links.new(math_node('MULTIPLY',iris_only,.55),mix.inputs[0])
    links.new(radial_colors.outputs['Color'],mix.inputs[1])
    links.new(fiber_colors.outputs['Color'],mix.inputs[2])
    lid_shadow=nodes.new('ShaderNodeMapRange')
    lid_shadow.clamp=True
    lid_shadow.inputs['From Min'].default_value=-.003
    lid_shadow.inputs['From Max'].default_value=.006
    lid_shadow.inputs['To Min'].default_value=1
    lid_shadow.inputs['To Max'].default_value=.35
    links.new(dz,lid_shadow.inputs['Value'])
    shaded=nodes.new('ShaderNodeMixRGB')
    shaded.blend_type='MULTIPLY'
    shaded.inputs[0].default_value=1
    links.new(mix.outputs[0],shaded.inputs[1])
    links.new(lid_shadow.outputs['Result'],shaded.inputs[2])
    links.new(shaded.outputs[0],shader.inputs['Base Color'])
    roughness = math_node('ADD',math_node('MULTIPLY',math_node('GREATER_THAN',radial,1),.10),.18)
    links.new(roughness,shader.inputs['Roughness'])
    return material


def improve_eyes(head,eyes,collection):
    """Replace eye paint only; retain every mesh coordinate and head material."""
    before=[tuple(v.co) for v in eyes.data.vertices]
    original_head=[tuple(v.co) for v in head.data.vertices]
    centers=[]
    for sign in (-1,1):
        points=[v.co for v in eyes.data.vertices if (v.co.x+.012)*sign>0]
        center=[sum(p[i] for p in points)/len(points) for i in range(3)]
        # Both irises look ahead; their small vertical offset follows head tilt.
        center[2]+=.0008
        centers.append(center)
    eyes.data.materials.clear()
    for side,center in zip(('R','L'),centers):
        eyes.data.materials.append(eye_material(f'Eye_Hazel_Clear_{side}_v006',center))
    for polygon in eyes.data.polygons:
        polygon.material_index = 0 if polygon.center.x<-.012 else 1
        polygon.use_smooth=True
    assert before==[tuple(v.co) for v in eyes.data.vertices]
    assert original_head==[tuple(v.co) for v in head.data.vertices]
    eyes['EyeDetailV006']='Procedural hazel iris fibers, round pupils, limbal ring and physical gloss'
    return {'eye_geometry_unchanged':True,'head_unchanged':True,'iris_diameter_mm':15.2,
            'pupil_diameter_mm':5.472,'centers':centers,'painted_glints_removed':True}


if __name__=='__main__':
    import json
    from mathutils import Vector
    root=Path(__file__).resolve().parents[1]
    bpy.ops.wm.open_mainfile(filepath=str(root/'assets/Character/Beauty_v006/Adventurer_shape_v006.blend'))
    head=bpy.data.objects['Head_Sculpted_ReferenceUV']
    eyes=bpy.data.objects['Eyes_ReferenceUV']
    result=improve_eyes(head,eyes,bpy.data.collections['01_Character_Refined'])
    scene=bpy.context.scene
    preferences=bpy.context.preferences.addons['cycles'].preferences
    preferences.compute_device_type='OPTIX'
    preferences.get_devices()
    for device in preferences.devices:device.use=device.type=='OPTIX'
    scene.cycles.device='GPU'
    scene.cycles.samples=24
    scene.cycles.use_denoising=True
    scene.render.resolution_x=scene.render.resolution_y=850
    scene.render.resolution_percentage=100
    for name,location in [('front',(-.012,-4,1.605)),('quarter',(1.65,-4,1.61)),('profile',(4,.02,1.605))]:
        target=Vector((-.012,.02,1.605))
        scene.camera.location=location
        scene.camera.rotation_euler=(target-scene.camera.location).to_track_quat('-Z','Y').to_euler()
        scene.camera.data.ortho_scale=.325
        scene.render.filepath=str(root/f'logs/beauty_eyes_{name}.png')
        bpy.ops.render.render(write_still=True)
    (root/'logs/beauty_eyes_validation.json').write_text(json.dumps(result,indent=2))
    print('BEAUTY_EYES_OK',json.dumps(result))
