"""Repair lower-body material assignments without changing Tripo geometry or UVs."""
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def build_body_materials(obj, collection):
    """Accept a mesh with its world transform applied; preserve everything above 1.45m."""
    assert obj.type == 'MESH' and obj.data.materials
    mesh = obj.data
    original_count = len(mesh.vertices), len(mesh.polygons), len(mesh.uv_layers)
    source = mesh.materials[0]
    clothing = source.copy()
    clothing.name = 'Body_Clothing_Refined_OriginalColor'
    shader = next(n for n in clothing.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    for name in ('Metallic', 'Roughness'):
        for link in list(shader.inputs[name].links):
            clothing.node_tree.links.remove(link)
    shader.inputs['Metallic'].default_value = 0
    shader.inputs['Roughness'].default_value = .73
    shader.inputs['Specular IOR Level'].default_value = .28
    for node in clothing.node_tree.nodes:
        if node.type == 'NORMAL_MAP':
            node.inputs['Strength'].default_value = .18

    def material(name, color, roughness, leather=False):
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        mat.diffuse_color = (*color, 1)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = (*color, 1)
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Metallic'].default_value = 0
        bsdf.inputs['Specular IOR Level'].default_value = .25
        if leather:
            noise = nodes.new('ShaderNodeTexNoise')
            noise.inputs['Scale'].default_value = 420
            noise.inputs['Detail'].default_value = 2
            bump = nodes.new('ShaderNodeBump')
            bump.inputs['Strength'].default_value = .12
            bump.inputs['Distance'].default_value = .0004
            links.new(noise.outputs['Fac'], bump.inputs['Height'])
            links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
        return mat

    skin = material('Body_Skin_Refined', (.62, .33, .19), .52)
    skin_shader = skin.node_tree.nodes.get('Principled BSDF')
    skin_shader.inputs['Subsurface Weight'].default_value = .06
    skin_shader.inputs['Subsurface Radius'].default_value = (1, .45, .25)
    skin_shader.inputs['Subsurface Scale'].default_value = .015
    boots = material('Body_Boot_Leather_Refined', (.23, .103, .046), .61, True)
    cuffs = material('Body_Boot_Cuff_Refined', (.29, .133, .062), .66, True)
    soles = material('Body_Boot_Sole_Refined', (.064, .025, .012), .8)
    materials = {'clothing': clothing, 'skin': skin, 'boots': boots, 'cuffs': cuffs, 'soles': soles}
    slots = {}
    for name, mat in materials.items():
        slots[name] = len(mesh.materials)
        mesh.materials.append(mat)

    counts = Counter()
    # This cuff plane follows the observed A-pose rather than painting the sleeves skin-colored.
    # The generated gray forearm patches are within the bare-arm side of the plane.
    for face in mesh.polygons:
        if max(mesh.vertices[index].co.z for index in face.vertices) >= 1.45:
            continue
        point = face.center
        x, z = abs(point.x), point.z
        name = 'clothing'
        if .76 < z < 1.22 and x > .22 and .58 * x - .815 * z > -.745:
            name = 'skin'
        elif z < .300:
            name = 'soles' if z < .024 else ('cuffs' if z > .245 else 'boots')
        face.material_index = slots[name]
        counts[name] += 1
    assert original_count == (len(mesh.vertices), len(mesh.polygons), len(mesh.uv_layers))
    assert counts['skin'] > 100 and counts['boots'] > 100
    obj['body_material_repair'] = 'Original clothes color retained; matte PBR; repaired forearms and leather boots'
    obj['body_material_faces'] = dict(counts)
    print('BODY_MATERIAL_REPAIR_OK', dict(counts))
    return materials


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    bpy.ops.wm.open_mainfile(filepath=str(root / 'assets/Character/Tripo_v002/Adventurer_Tripo_v002.blend'))
    collection = bpy.data.collections['01_Tripo_Character']
    obj = next(o for o in collection.objects if o.type == 'MESH')
    transform = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    obj.data.transform(transform)
    obj.data.update()
    build_body_materials(obj, collection)
    scene = bpy.context.scene
    camera = scene.camera
    camera.location = (0, -5, .875)
    camera.rotation_euler = (Vector((0, 0, .875)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = 1.9
    scene.cycles.samples = 24
    scene.render.resolution_x, scene.render.resolution_y = 900, 1350
    scene.render.filepath = str(root / 'logs/body_refine_preview.png')
    bpy.ops.render.render(write_still=True)
    print('BODY_REFINE_PREVIEW_DONE')
