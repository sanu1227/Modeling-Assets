"""Render texture and geometry separately; leave the imported blend unchanged."""
from pathlib import Path
import bpy
from mathutils import Vector

out = Path(__file__).resolve().parents[1] / 'assets' / 'Character' / 'Tripo_v002'
bpy.ops.wm.open_mainfile(filepath=str(out / 'Adventurer_Tripo_v002.blend'))
scene = bpy.context.scene
camera = scene.camera
camera.location = (0, -4, 1.57)
camera.rotation_euler = (Vector((0, 0, 1.57)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.ortho_scale = .43
scene.render.resolution_x = scene.render.resolution_y = 800
scene.cycles.samples = 24
objects = [o for o in bpy.data.collections['01_Tripo_Character'].objects if o.type == 'MESH']
original = {o.name: list(o.data.materials) for o in objects}

for mode in ('BaseColor', 'Matte', 'Clay'):
    for obj in objects:
        for index, source in enumerate(original[obj.name]):
            material = source.copy()
            obj.data.materials[index] = material
            nodes, links = material.node_tree.nodes, material.node_tree.links
            shader = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
            if mode == 'BaseColor':
                emission = nodes.new('ShaderNodeEmission')
                if shader.inputs['Base Color'].is_linked:
                    links.new(shader.inputs['Base Color'].links[0].from_socket, emission.inputs['Color'])
                else:
                    emission.inputs['Color'].default_value = shader.inputs['Base Color'].default_value
                output = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
                links.new(emission.outputs[0], output.inputs['Surface'])
            else:
                for name in ('Metallic', 'Roughness', 'Normal'):
                    for link in list(shader.inputs[name].links):
                        links.remove(link)
                shader.inputs['Metallic'].default_value = 0
                shader.inputs['Roughness'].default_value = .65
                shader.inputs['Specular IOR Level'].default_value = .25
                if mode == 'Clay':
                    for link in list(shader.inputs['Base Color'].links):
                        links.remove(link)
                    shader.inputs['Base Color'].default_value = (.40, .40, .40, 1)
    scene.view_settings.view_transform = 'Standard' if mode == 'BaseColor' else 'AgX'
    scene.render.filepath = str(out / f'Diagnostic_{mode}_Face.png')
    bpy.ops.render.render(write_still=True)
print('TRIPO_SURFACE_DIAGNOSTICS_DONE')
