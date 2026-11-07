"""Editable exterior asset. Run with Blender --background --python this_file.

Only assets/MedievalShop is generated. No external assets or Python packages.
"""
import json
import math
import random
import tempfile
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'MedievalShop'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'Textures').mkdir(exist_ok=True)
(OUT / '.temp').mkdir(exist_ok=True)
tempfile.tempdir = str(OUT / '.temp')
bpy.context.preferences.filepaths.temporary_directory = tempfile.tempdir
random.seed(3184)
rng = np.random.default_rng(3184)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type != 'CPU'
    if any(d.use for d in prefs.devices):
        scene.cycles.device = 'GPU'
except (TypeError, RuntimeError):
    pass
scene.render.resolution_x = 1500
scene.render.resolution_y = 1500
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.38, .46, .52, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .38

collections = {}
for name in ['01_Structure', '02_Timber', '03_Roof', '04_Doors_Windows',
             '05_Shop_Details', '06_Props', '90_Presentation']:
    collection = bpy.data.collections.new(name)
    scene.collection.children.link(collection)
    collections[name] = collection
current = '01_Structure'
cache = {}


def move(obj, group=None):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    collections[group or current].objects.link(obj)
    return obj


def material(name, color, roughness=.7, metallic=0, texture=None, emission=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    p = mat.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Metallic'].default_value = metallic
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1)
        p.inputs['Emission Strength'].default_value = emission
    if texture:
        size = 512
        v, u = np.mgrid[0:size, 0:size].astype(np.float32) / size
        noise = rng.normal(0, .018, (size, size))
        if texture == 'wood':
            warp = .017 * np.sin(v * math.tau * 3 + np.sin(u * math.tau * 2))
            grain = .11 * np.sin((u + warp) * math.tau * 27)
            grain += .06 * np.sin((u + warp * .4) * math.tau * 93)
            grain += .06 * np.sin(u * math.tau * 5) + noise
        elif texture == 'cloth':
            grain = .025 * (np.sin(u * math.tau * 160) + np.sin(v * math.tau * 160)) + noise
        else:
            grain = .045 * np.sin(u * math.tau * 7 + np.sin(v * math.tau * 4))
            grain += .035 * np.cos(v * math.tau * 11 + u * math.tau * 3) + noise
        pixels = np.ones((size, size, 4), dtype=np.float32)
        pixels[:, :, :3] = np.clip(np.array(color)[None, None, :] * (1 + grain[:, :, None]), .006, .95)
        image = bpy.data.images.new(name + '_BaseColor', size, size, alpha=False)
        image.pixels.foreach_set(pixels.ravel())
        image.filepath_raw = str(OUT / 'Textures' / (name + '.png'))
        image.file_format = 'PNG'
        image.save()
        image.pack()
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = image
        tex.location = (-520, 100)
        mat.node_tree.links.new(tex.outputs['Color'], p.inputs['Base Color'])
        # Preview microrelief. The portable GLB retains base color and roughness.
        bump = mat.node_tree.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .15 if texture == 'wood' else .07
        bump.inputs['Distance'].default_value = .025 if texture == 'wood' else .004
        bump.location = (-220, -140)
        mat.node_tree.links.new(tex.outputs['Color'], bump.inputs['Height'])
        mat.node_tree.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    return mat


wood = material('Oak_dark', (.235, .107, .042), texture='wood')
lightwood = material('Oak_cut', (.49, .285, .105), texture='wood')
plaster = material('Lime_plaster', (.78, .66, .43), .88, texture='stone')
stone = [material('Stone_' + str(i), c, .87, texture='stone') for i, c in enumerate([
    (.36, .35, .29), (.43, .41, .34), (.50, .46, .37)])]
slate = [material('Slate_' + str(i), c, .66, texture='stone') for i, c in enumerate([
    (.065, .195, .19), (.085, .24, .225), (.11, .27, .25), (.055, .16, .17)])]
iron = material('Forged_iron', (.065, .075, .065), .47, .72)
brass = material('Aged_brass', (.53, .31, .075), .36, .65)
glass = material('Amber_window', (.34, .21, .065), .25, .15, emission=.16)
recess = material('Deep_recess', (.045, .035, .022), .9)
canvas = material('Canvas_olive', (.29, .37, .14), .93, texture='cloth')
linen = material('Canvas_linen', (.78, .70, .48), .92, texture='cloth')
terra = material('Terracotta', (.46, .17, .075), .8, texture='stone')
green = material('Herb_green', (.12, .24, .05), .78)
green2 = material('Herb_light', (.27, .36, .065), .78)
purple = material('Lavender', (.36, .15, .40), .7)
bottle_mat = material('Bottle_emerald', (.04, .25, .16), .2, .15)
groundmat = material('Display_ground', (.24, .28, .255), .95)
clay = material('Blockout_clay', (.52, .53, .48), .8)


def add_bevel(obj, width, segments=2):
    if width:
        mod = obj.modifiers.new('Editable edge bevel', 'BEVEL')
        mod.width = width
        mod.segments = segments
        mod.limit_method = 'ANGLE'
    return obj


def mesh(name, verts, faces, mat, bevel=0, group=None, uv=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    data.materials.append(mat)
    if uv:
        layer = data.uv_layers.new(name='UV_Surface')
        lengths = [max(v[i] for v in verts) - min(v[i] for v in verts) for i in range(3)]
        for poly in data.polygons:
            normal_axis = max(range(3), key=lambda a: abs(poly.normal[a]))
            axes = [a for a in range(3) if a != normal_axis]
            long_axis = max(axes, key=lambda a: lengths[a])
            short_axis = next(a for a in axes if a != long_axis)
            for index in poly.loop_indices:
                co = data.vertices[data.loops[index].vertex_index].co
                layer.data[index].uv = (co[short_axis] * .65, co[long_axis] * .65)
    obj = bpy.data.objects.new(name, data)
    collections[group or current].objects.link(obj)
    return add_bevel(obj, bevel)


def box(name, size, loc, mat=wood, bevel=.025, rot=None):
    key = (tuple(round(s, 5) for s in size), mat.name, bevel)
    if key in cache:
        obj = cache[key].copy()
        obj.name = name
        collections[current].objects.link(obj)
    else:
        x, y, z = (s / 2 for s in size)
        obj = mesh(name, [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
                         (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)],
                   [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)], mat, bevel)
        cache[key] = obj
    obj.location = loc
    obj.rotation_euler = rot or (0, 0, 0)
    obj.scale = (1, 1, 1)
    return obj


def beam(name, a, b, width=.16, depth=None, mat=wood):
    a, b = Vector(a), Vector(b)
    obj = box(name, (width, depth or width, (b-a).length), (a+b)/2, mat, min(.025, width*.15))
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return obj


def cylinder(name, loc, radius, depth, mat, vertices=12, rot=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = move(bpy.context.object)
    obj.name = name
    obj.data.materials.append(mat)
    if rot:
        obj.rotation_euler = rot
    return add_bevel(obj, min(.018, radius*.12, depth*.2))


def lathe(name, loc, profile, mat, n=16):
    verts = [(r*math.cos(i*math.tau/n), r*math.sin(i*math.tau/n), z)
             for z,r in profile for i in range(n)]
    faces = [tuple(reversed(range(n)))]
    for j in range(len(profile)-1):
        for i in range(n):
            a, b = j*n+i, j*n+(i+1)%n
            faces.append((a, b, b+n, a+n))
    faces.append(tuple(range((len(profile)-1)*n,len(profile)*n)))
    obj = mesh(name, verts, faces, mat, .008)
    obj.location = loc
    return obj


def torus(name, loc, radius, tube, mat, rot=None):
    bpy.ops.mesh.primitive_torus_add(major_segments=16, minor_segments=6,
        major_radius=radius, minor_radius=tube, location=loc)
    obj = move(bpy.context.object)
    obj.name = name
    obj.data.materials.append(mat)
    if rot:
        obj.rotation_euler = rot
    return obj


def prism(name, outline, depth, y, mat, bevel=.015):
    n = len(outline)
    verts = [(x, y+dy, z) for dy in (-depth/2,depth/2) for x,z in outline]
    faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name, verts, faces, mat, bevel)


def point_camera(loc, target=(.4,-.3,4.25), scale=15.3):
    camera.location = loc
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale = scale


current = '90_Presentation'
box('Studio_ground', (200,200,.15), (0,0,-.53), groundmat, .03)
bpy.ops.object.camera_add(location=(14,-20,13))
camera = move(bpy.context.object)
camera.name = 'Camera_Front'
camera.data.type = 'ORTHO'
scene.camera = camera
point_camera((14,-20,13))
for name, loc, energy, size, color in [
    ('Key_warm',(-6,-10,16),2300,8,(1,.82,.62)),
    ('Fill_cool',(8,-2,10),1500,9,(.66,.81,1)),
    ('Rim',(2,7,13),2600,7,(1,.88,.68))]:
    bpy.ops.object.light_add(type='AREA', location=loc)
    obj = move(bpy.context.object)
    obj.name = name
    obj.data.energy, obj.data.shape, obj.data.size, obj.data.color = energy, 'DISK', size, color
    obj.rotation_euler = (Vector((0,0,4))-obj.location).to_track_quat('-Z','Y').to_euler()

# Save the massing stage before replacing it with the detailed construction.
current = '01_Structure'
block = [box('Blockout_ground_floor',(6.4,5.2,3.1),(0,0,1.55),clay),
         box('Blockout_upper_floor',(6.9,5.7,3.0),(0,0,4.6),clay),
         prism('Blockout_gable',[(-3.45,6.1),(3.45,6.1),(0,9.25)],5.7,0,clay),
         box('Blockout_side_annex',(1.6,3.7,3),(4, .35,1.5),clay),
         box('Door_scale_2_2m',(1.2,.2,2.2),(-1.85,-2.7,1.5),wood)]
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MedievalShop_blockout.blend'))
for obj in block:
    bpy.data.objects.remove(obj, do_unlink=True)
cache.clear()
print('STAGE: blockout saved', flush=True)

# Low masonry foundation and all four finished exterior elevations.
box('Foundation_core',(6.4,5.2,.65),(0,0,.325),stone[0],.05)
box('Ground_floor_lime',(6.2,5.0,2.65),(0,0,1.965),plaster,.035)
box('Upper_floor_lime',(6.65,5.45,2.8),(0,0,4.84),plaster,.035)
prism('Front_gable_lime',[(-3.325,6.24),(3.325,6.24),(0,9.12)],.18,-2.64,plaster)
prism('Back_gable_lime',[(-3.325,6.24),(3.325,6.24),(0,9.12)],.18,2.64,plaster)
for row in range(2):
    for front in (-1,1):
        for i in range(10):
            box('Foundation_front_block',(.62,.20,.29),(-2.88+i*.64,front*2.59,.17+row*.31),random.choice(stone),.035)
        for i in range(8):
            box('Foundation_side_block',(.20,.62,.29),(front*3.19,-2.24+i*.64,.17+row*.31),random.choice(stone),.035)
for z in (1.0,1.65,2.3,2.95):
    for x in (-3.12,3.12):
        for y in (-2.49,2.49):
            box('Corner_stone',(.37,.36,.27),(x,y,z),stone[1],.03)

current = '02_Timber'
for z,width,depth in [(.73,6.5,5.3),(3.22,6.65,5.5),(3.48,6.95,5.8),(6.25,6.95,5.8)]:
    for s in (-1,1):
        box('Horizontal_front_beam',(width,.22,.22),(0,s*depth/2,z))
        box('Horizontal_side_beam',(.22,depth,.22),(s*width/2,0,z))
for y in (-2.59,2.59):
    for x in (-3.14,-.55,3.14):
        beam('Ground_post',(x,y,.67),(x,y,3.25),.23)
for x in (-3.2,3.2):
    for y in (-.9,.9):
        beam('Side_ground_post',(x,y,.7),(x,y,3.22),.2)
for y in (-2.79,2.79):
    for x in (-3.38,-1.13,1.13,3.38):
        beam('Upper_post',(x,y,3.43),(x,y,6.3),.19)
    box('Front_midrail',(6.9,.16,.15),(0,y,4.25))
    for x in (-3.28,-1.02,1.23):
        beam('Upper_diagonal',(x,y,4.32),(x+1.92,y,6.12),.135)
for x in (-3.4,3.4):
    for y in (-2.7,-.9,.9,2.7):
        beam('Side_upper_post',(x,y,3.43),(x,y,6.3),.19)
    box('Side_midrail',(.16,5.65,.15),(x,0,4.25))
    for y in (-2.65,.95):
        beam('Side_upper_brace',(x,y,4.35),(x,y+1.55,6.08),.13)
for y in (-2.84,2.84):
    beam('Gable_center',(0,y,6.25),(0,y,9.18),.21)
    for s in (-1,1):
        beam('Gable_rake',(s*3.46,y,6.25),(0,y,9.23),.22)
        beam('Gable_fan',(s*.18,y,6.31),(s*1.82,y,7.59),.14)
        beam('Gable_upright',(s*1.2,y,6.3),(s*1.2,y,8.12),.14)
    box('Gable_tie',(5.02,.18,.16),(0,y,7.02))
for x in (-2.85,-1.7,-.55,.6,1.75,2.85):
    for s in (-1,1):
        box('Jetty_joist',(.18,.63,.20),(x,s*2.62,3.31),lightwood)
        beam('Jetty_bracket',(x,s*2.52,2.78),(x,s*2.87,3.26),.14)

current = '03_Roof'
slope = math.atan2(2.8,3.85)
for side in (-1,1):
    box('Roof_deck', (math.hypot(3.85,2.8),6.45,.16),
        (side*1.925,0,7.85),wood,.015,(0,side*slope,0))
    for row in range(12):
        x = side*(3.73-row*.325)
        z = 6.45+(3.85-abs(x))*2.8/3.85+.11
        for column in range(15):
            y = -3.12+column*.444+(row%2)*.035
            tile = box('Slate_shingle',(.50,.457,.065),(x,y,z+random.uniform(-.006,.006)),
                       random.choice(slate),.018,(0,side*slope,random.uniform(-.009,.009)))
            tile.modifiers[0].segments = 1
    for y in (-3.3,3.3):
        beam('Roof_verge',(side*3.96,y,6.4),(0,y,9.31),.20,mat=lightwood)
    box('Eave_fascia',(.18,6.7,.22),(side*3.91,0,6.43),wood)
for i in range(15):
    # Closed faceted ridge cap, with a consistent overlap across the roof seam.
    prism('Ridge_cap',[(-.25,9.22),(0,9.47),(.25,9.22),(.25,9.15),(0,9.38),(-.25,9.15)],
          .46,-3.16+i*.45,slate[2],.015)
for y in (-3.34,3.34):
    cylinder('Ridge_finial',(0,y,9.53),.09,.48,brass)

# Chimney is exposed above the roof; brick courses keep the scale legible.
box('Chimney_core',(.82,.9,3.8),(2.0,1.36,7.8),stone[0],.025)
for row in range(10):
    for j in range(2):
        for side in (-1,1):
            box('Chimney_brick',(.40,.14,.22),(1.79+j*.42,1.36+side*.47,7.3+row*.24),
                terra if (row+j)%3 else stone[1],.02)
            box('Chimney_end_brick',(.14,.44,.22),(2+side*.43,1.13+j*.46,7.3+row*.24),terra,.02)
box('Chimney_crown',(1.06,1.14,.18),(2,1.36,9.73),stone[1],.035)
for x in (1.78,2.22):
    lathe('Chimney_pot',(x,1.36,9.80),[(0,.17),(.40,.14),(.44,.2),(.5,.2)],terra)
    cylinder('Chimney_pot_dark_opening',(x,1.36,10.305),.145,.012,recess)

current = '04_Doors_Windows'
def window(loc, width=1.18, height=1.46, angle=0, shutters=True):
    previous = set(bpy.data.objects)
    box('Window_shadow',(width+.18,.12,height+.18),(0,0,0),recess,.015)
    box('Window_amber_glass',(width,.06,height),(0,-.075,0),glass,.006)
    for x in (-width/2,width/2):
        box('Window_jamb',(.11,.16,height+.16),(x,-.13,0),lightwood,.015)
    for z in (-height/2,height/2):
        box('Window_rail',(width+.12,.16,.10),(0,-.13,z),lightwood,.014)
    box('Window_center_mullion',(.065,.15,height),(0,-.15,0),wood,.008)
    box('Window_crossbar',(width,.15,.06),(0,-.15,.1),wood,.008)
    # Fine lead lattice clipped to the bounds of the rectangular glazing.
    w,h=width-.1,height-.1
    for direction in (-1,1):
        for offset in np.arange(-h/2-w/2,h/2+w/2,.30):
            points=[]
            for x in (-w/2,w/2):
                z=direction*x+offset
                if -h/2 <= z <= h/2: points.append((x,-.12,z))
            for z in (-h/2,h/2):
                x=(z-offset)/direction
                if -w/2 < x < w/2: points.append((x,-.12,z))
            if len(points)==2 and (Vector(points[1])-Vector(points[0])).length > .025:
                beam('Diamond_lead',points[0],points[1],.018,mat=brass)
    box('Window_sill',(width+.42,.34,.12),(0,-.19,-height/2-.10),lightwood)
    if shutters:
        for side in (-1,1):
            sx=side*(width*.72+.10)
            for j in range(3):
                box('Shutter_plank',(.16,.09,height),(sx+(j-1)*.17,-.06,0),wood,.012)
            for z in (-height*.32,height*.32):
                box('Shutter_hinge',(.50,.05,.065),(sx,-.13,z),iron,.008)
    rotation=Matrix.Rotation(angle,4,'Z')
    for obj in set(bpy.data.objects)-previous:
        obj.location=Vector(loc)+rotation.to_3x3()@obj.location
        obj.rotation_euler=(rotation.to_3x3()@obj.rotation_euler.to_matrix()).to_euler()

for y,angle in [(-2.9,0),(2.9,math.pi)]:
    for x in (-2.2,2.2):
        window((x,y,5.12),1.0,1.5,angle)
for x,angle in [(3.51,math.pi/2),(-3.51,-math.pi/2)]:
    window((x,0,5.15),1.1,1.48,angle)
window((1.28,-2.64,1.94),2.35,1.45,0,False)
window((1.25,2.64,1.95),1.22,1.25,math.pi)
window((-3.26,0,1.95),1.22,1.25,-math.pi/2)
# Attic oculus masks the central crossing and gives a clear focal accent.
for y in (-2.96,2.96):
    cylinder('Attic_dark_round',(0,y,7.85),.43,.10,recess,24,(math.pi/2,0,0))
    torus('Attic_round_frame',(0,y*1.015,7.85),.44,.065,lightwood,(math.pi/2,0,0))
    for x in (-.22,0,.22):
        length=2*math.sqrt(.38**2-x**2)
        beam('Attic_vent',(x,y*1.022,7.85-length/2),(x,y*1.022,7.85+length/2),.052)

dx=-1.85
doorbase=.43
outline=[(dx-.64,doorbase),(dx+.64,doorbase),(dx+.64,1.99)]
outline += [(dx+.64*math.cos(a),1.99+.64*math.sin(a)) for a in np.linspace(0,math.pi,17)[1:]]
prism('Arched_oak_door',outline,.15,-2.65,lightwood)
for i in range(7):
    x=dx+(i-3)*.165
    top=1.99+math.sqrt(.64**2-(x-dx)**2)-.035
    box('Door_plank_seam',(.012,.014,top-doorbase-.04),(x,-2.734,(top+doorbase)/2),wood,.002)
for i in range(11):
    a=i*math.pi/10
    obj=box('Arch_stone',(.24,.24,.25),(dx+.79*math.cos(a),-2.65,1.99+.79*math.sin(a)),stone[1],.025)
    obj.rotation_euler[1]=math.pi/2-a
for x in (dx-.79,dx+.79):
    for j in range(5):
        box('Door_stone_jamb',(.23,.24,.28),(x,-2.65,.58+j*.30),stone[j%3],.025)
for z in (.91,1.69):
    box('Door_strap',(.99,.055,.08),(dx,-2.76,z),iron,.015)
    for x in (dx-.4,dx+.4):
        cylinder('Door_rivet',(x,-2.798,z),.026,.02,brass,8,(math.pi/2,0,0))
torus('Door_ring',(dx+.37,-2.82,1.35),.09,.021,brass,(math.pi/2,0,0))
for i in range(2):
    box('Entry_step',(1.95-i*.15,.60,.16),(dx,-3.05+i*.31,.08+i*.16),stone[1],.035)

# Low right-hand storage annex and its single-pitch tiled roof.
current='01_Structure'
box('Annex_lime',(1.50,3.55,2.65),(4.01,.40,1.55),plaster,.03)
box('Annex_stone_base',(1.60,3.65,.44),(4.01,.40,.22),stone[0],.04)
current='02_Timber'
for y in (-1.43,2.23):
    beam('Annex_corner',(4.78,y,.42),(4.78,y,2.93),.20)
    beam('Annex_cross_brace',(4.80,y,.65),(3.4,y,2.85),.14)
box('Annex_outer_toprail',(.18,3.9,.18),(4.83,.4,2.96))
current='03_Roof'
angle=math.atan2(.85,1.85)
box('Annex_roof_deck',(2.12,4.05,.13),(4.1,.4,3.4),wood,.015,(0,angle,0))
for row in range(6):
    x=5.0-row*.33
    z=3.0+(5.0-x)*.85/1.85+.12
    for j in range(10):
        tile=box('Annex_tile',(.49,.42,.065),(x,-1.48+j*.42,z),random.choice(slate),.016,(0,angle,0))
        tile.modifiers[0].segments=1
current='04_Doors_Windows'
window((4.86,.40,1.85),1.12,1.18,math.pi/2,False)
print('STAGE: architecture complete', flush=True)

current='05_Shop_Details'
# Segmented canvas canopy with a soft sag and a scalloped hem.
for x in (-.35,3.25):
    beam('Awning_front_post',(x,-4.35,.08),(x,-4.35,2.78),.11,mat=lightwood)
    beam('Awning_support',(x,-2.71,3.13),(x,-4.40,2.75),.08,mat=iron)
beam('Awning_front_rail',(-.44,-4.36,2.76),(3.34,-4.36,2.76),.09,mat=lightwood)
for stripe in range(10):
    x0=-.45+stripe*.38
    verts=[]
    for j in range(9):
        t=j/8
        y=-2.77-1.62*t
        z=3.18-.39*t-.15*math.sin(math.pi*t)
        verts.extend([(x0,y,z),(x0+.382,y,z)])
    faces=[(j*2,j*2+1,j*2+3,j*2+2) for j in range(8)]
    obj=mesh('Awning_canvas',verts,faces,canvas if stripe%2==0 else linen)
    mod=obj.modifiers.new('Canvas thickness','SOLIDIFY'); mod.thickness=.018
    outline=[(x0,2.79),(x0+.382,2.79),(x0+.382,2.60)]
    outline += [(x0+.191+.191*math.cos(a),2.60-.095*math.sin(a)) for a in np.linspace(0,math.pi,10)[1:]]
    prism('Scalloped_canvas_hem',outline,.024,-4.405,canvas if stripe%2==0 else linen,.008)

# Hanging carved sign, oriented to read from the approach.
beam('Sign_bracket',(-3.05,-2.65,3.4),(-4.22,-3.03,3.4),.07,mat=iron)
beam('Sign_brace',(-3.05,-2.65,3.86),(-4.17,-3.02,3.4),.06,mat=iron)
for x in (-4.03,-3.50):
    beam('Sign_hanger',(x,-3.0,3.39),(x,-3.0,3.02),.026,mat=iron)
sign=box('Shop_sign',(1.5,.14,.86),(-3.77,-3.0,2.65),wood,.13)
box('Sign_inset',(1.32,.035,.67),(-3.77,-3.088,2.65),canvas,.09)
font_path=Path('C:/Windows/Fonts/georgiab.ttf')
font=bpy.data.fonts.load(str(font_path)) if font_path.exists() else None
def text_obj(name,body,loc,size,mat):
    curve=bpy.data.curves.new(name,'FONT')
    curve.body,curve.size,curve.align_x,curve.align_y=body,size,'CENTER','CENTER'
    curve.extrude=.0025
    curve.bevel_depth=.0008
    curve.resolution_u=2
    curve.render_resolution_u=2
    curve.bevel_resolution=0
    if font: curve.font=font
    obj=bpy.data.objects.new(name,curve)
    collections[current].objects.link(obj)
    obj.location=loc
    obj.rotation_euler=(math.pi/2,0,0)
    curve.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    obj.select_set(False)
    bm=bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    # Text receives UVs for downstream tools, although it uses a flat material.
    if not obj.data.uv_layers: obj.data.uv_layers.new(name='UV_Surface')
    return obj
text_obj('Sign_name','MOSS & OAK',(-3.77,-3.12,2.77),.165,linen)
text_obj('Sign_trade','APOTHECARY',(-3.77,-3.12,2.53),.10,linen)

# Wall lanterns: metal frame, warm glass and a real point light.
for x in (-2.88,.0):
    box('Lantern_wall_mount',(.14,.14,.32),(x,-2.75,2.24),iron)
    beam('Lantern_arm',(x,-2.74,2.48),(x,-3.02,2.48),.045,mat=iron)
    box('Lantern_glass',(.22,.20,.31),(x,-3.02,2.19),glass,.015)
    for z in (2.01,2.37):
        box('Lantern_cap',(.30,.28,.065),(x,-3.02,z),iron,.025)
    for dx2 in (-.12,.12):
        for dy in (-.11,.11):
            beam('Lantern_corner',(x+dx2,-3.02+dy,2.02),(x+dx2,-3.02+dy,2.36),.023,mat=iron)
    bpy.ops.object.light_add(type='POINT',location=(x,-3.18,2.2))
    lamp=move(bpy.context.object,'90_Presentation')
    lamp.data.energy=12
    lamp.data.color=(1,.52,.13)
    lamp.data.shadow_soft_size=.2

current='06_Props'
def barrel(loc, scale=1):
    start=set(bpy.data.objects)
    profile=[(0,.35),(.10,.38),(.40,.43),(.78,.41),(1.0,.35)]
    lathe('Barrel_body',(0,0,0),profile,lightwood,16)
    for z,r in ((.12,.389),(.78,.419),(.95,.368)):
        torus('Barrel_hoop',(0,0,z),r,.032,iron)
    for i in range(16):
        a=i*math.tau/16
        for (z1,r1),(z2,r2) in zip(profile,profile[1:]):
            beam('Stave_joint',(r1*math.cos(a),r1*math.sin(a),z1),
                 (r2*math.cos(a),r2*math.sin(a),z2),.011,mat=wood)
    cylinder('Barrel_lid',(0,0,1.005),.337,.025,wood,16)
    for obj in set(bpy.data.objects)-start:
        obj.location=Vector(loc)+obj.location*scale
        obj.scale*=scale

def crate(loc, scale=1):
    start=set(bpy.data.objects)
    box('Crate_dark_inside',(.7,.6,.5),(0,0,.25),recess,.01)
    for i in range(4):
        for y in (-.34,.34):
            box('Crate_slat',(.82,.065,.11),(0,y,.08+i*.135),lightwood,.01)
        for x in (-.40,.40):
            box('Crate_end',(.065,.64,.11),(x,0,.08+i*.135),lightwood,.01)
    for x in (-.37,.37):
        for y in (-.32,.32):
            box('Crate_corner',(.07,.07,.57),(x,y,.28),wood,.01)
    for obj in set(bpy.data.objects)-start:
        obj.location=Vector(loc)+obj.location*scale
        obj.scale*=scale

barrel((3.97,-2.20,.05))
barrel((4.77,-1.85,.05),.74)
barrel((-3.78,.80,.02),.9)
crate((3.6,-3.7,.04))
crate((3.62,-3.67,.63),.82)
crate((-3.85,-1.8,.04),.8)
# Merchant's counter: raised boards, legs and front cladding.
for x in (.0,2.75):
    for y in (-3.28,-3.88):
        box('Counter_leg',(.11,.11,.87),(x,y,.46),wood)
for j in range(5):
    box('Counter_top',(3.0,.16,.07),(1.38,-3.26-j*.16,.95),lightwood,.012)
for j in range(13):
    box('Counter_front_plank',(.21,.08,.67),(.04+j*.225,-3.96,.56),wood,.012)
for x in (.25,1.2,2.2):
    box('Counter_display_tray',(.72,.59,.10),(x,-3.57,1.05),lightwood,.015)
for i in range(15):
    x=.02+(i%5)*.18
    y=-3.77+(i//5)*.17
    lathe('Apothecary_bottle',(x,y,1.10),[(0,.055),(.16,.06),(.21,.027),(.29,.027)],bottle_mat,10)
    cylinder('Bottle_cork',(x,y,1.4),.029,.055,lightwood,8)
for i in range(8):
    x=1.0+(i%4)*.14
    y=-3.70+(i//4)*.23
    lathe('Clay_jar',(x,y,1.10),[(0,.055),(.12,.09),(.19,.065),(.22,.065)],terra,12)

def leaf(a,b,width,mat):
    a,b=Vector(a),Vector(b)
    axis=(b-a).normalized()
    cross=axis.cross(Vector((0,0,1)))
    if cross.length<.01: cross=Vector((1,0,0))
    cross.normalize()
    middle=(a+b)/2
    # Closed four-sided leaf keeps both sides visible and the exported shell manifold.
    verts=[a,middle+cross*width,b,middle-cross*width,middle+Vector((0,0,.035))]
    return mesh('Herb_leaf',verts,[(0,3,2,1),(0,1,4),(1,2,4),(2,3,4),(3,0,4)],mat)

def planter(loc,scale=1):
    x,y,z=loc
    lathe('Clay_planter',loc,[(0,.19*scale),(.12*scale,.22*scale),(.45*scale,.30*scale),
          (.50*scale,.31*scale)],terra,14)
    cylinder('Planter_soil',(x,y,z+.51*scale),.265*scale,.025,recess,14)
    for i in range(9):
        angle=i*2.4
        top=Vector((x+math.cos(angle)*.25*scale,y+math.sin(angle)*.25*scale,z+random.uniform(.8,1.18)*scale))
        base=Vector((x,y,z+.5*scale))
        beam('Herb_stem',base,top,.015*scale,mat=green)
        for j in (0,1):
            a=base.lerp(top,.4+j*.25)
            b=a+Vector((math.cos(angle+j)*.25*scale,math.sin(angle+j)*.25*scale,.13*scale))
            leaf(a,b,.075*scale,green2 if i%2 else green)
        if i%2==0:
            lathe('Lavender_flower',top,[(0,.045*scale),(.12*scale,.06*scale),(.2*scale,.015*scale)],purple,8)

planter((-2.95,-3.50,.02),1)
planter((5.04,1.74,.02),1.1)
planter((2.26,-3.54,1.10),.45)
for x in (-2.2,2.2):
    box('Window_flowerbox',(1.32,.34,.25),(x,-3.07,4.16),wood,.02)
    for j in range(5):
        base=(x-.5+j*.25,-3.1,4.3)
        leaf(base,(base[0]+.13,base[1]-.2,base[2]+.34),.12,green)
        leaf(base,(base[0]-.12,base[1]+.1,base[2]+.25),.10,green2)

# Ground is a removable presentation collection, not part of the export.
current='90_Presentation'
outline=[(-5.35,-4.70),(-4.65,-5.25),(4.45,-5.25),(5.65,-4.15),
         (5.7,3.8),(4.8,4.6),(-4.9,4.5),(-5.45,3.8)]
verts=[(x,y,z) for z in (-.42,-.07) for x,y in outline]
n=len(outline)
mesh('Presentation_plinth',verts,[tuple(reversed(range(n))),tuple(range(n,2*n))]+
     [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],stone[0],.08)
for row in range(20):
    y=-4.85+row*.46
    for col in range(22):
        x=-5.02+col*.48+(row%2)*.20
        if abs(x)<3.2 and abs(y)<2.65: continue
        if x>3.2 and x<4.8 and -1.45<y<2.25: continue
        if abs(x)>4.65 and abs(y)>4.0: continue
        obj=box('Courtyard_cobble',(.44,.415,.105),(x,y,-.025+random.uniform(-.01,.01)),random.choice(stone),.045)
        obj.rotation_euler.z=random.uniform(-.035,.035)
print('STAGE: detailing complete',flush=True)

# Export receives only the exterior building and props, never the display rig.
asset_objects=[o for name,c in collections.items() if name!='90_Presentation' for o in c.objects if o.type=='MESH']
root=bpy.data.objects.new('MOSS_AND_OAK_ROOT',None)
collections['01_Structure'].objects.link(root)
root.empty_display_type='PLAIN_AXES'
root['asset']='Moss & Oak - medieval apothecary exterior'
root['units']='meters; root at ground center'
root['scope']='Exterior only. No collision, LOD or lightmap UV.'
for obj in asset_objects:
    obj.parent=root
    obj['part']=obj.name.split('.')[0]
scene['workflow']='Reference research > blockout > modular geometry > UV/materials > dress > render/verify'
scene['texture_note']='Packed base-color images; tiled UVs. Preview bump is not baked into GLB.'
bpy.ops.object.select_all(action='DESELECT')
root.select_set(True)
bpy.context.view_layer.objects.active=root
point_camera((14,-20,13))
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.region_3d.view_distance=20
            space.region_3d.view_location=(.3,0,4.2)
            space.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
            space.region_3d.view_perspective='PERSP'
            space.shading.type='MATERIAL'
            space.overlay.show_floor=False
            space.clip_end=500
scene.render.filepath=str(OUT/'preview_front.png')
scene.render.film_transparent=False
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MedievalShop.blend'))

# Combine evaluated copies by collection for delivery; the saved .blend stays editable.
export_collection=bpy.data.collections.new('TEMP_EXPORT')
scene.collection.children.link(export_collection)
export_objects=[]
depsgraph=bpy.context.evaluated_depsgraph_get()
for name, collection in collections.items():
    if name=='90_Presentation':
        continue
    bpy.ops.object.select_all(action='DESELECT')
    copies=[]
    for original in list(collection.objects):
        if original.type!='MESH':
            continue
        data=bpy.data.meshes.new_from_object(original.evaluated_get(depsgraph),
                                            preserve_all_data_layers=True,depsgraph=depsgraph)
        obj=bpy.data.objects.new(original.name+'_Export',data)
        export_collection.objects.link(obj)
        obj.matrix_world=original.matrix_world
        obj.select_set(True)
        copies.append(obj)
    if copies:
        bpy.context.view_layer.objects.active=copies[0]
        bpy.ops.object.join()
        obj=copies[0]
        obj.name='Shop_'+name[3:]
        scene.cursor.location=(0,0,0)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        export_objects.append(obj)
bpy.ops.object.select_all(action='DESELECT')
for obj in export_objects:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'MedievalShop.glb'),export_format='GLB',
    use_selection=True,export_apply=True,export_cameras=False,export_lights=False,
    export_texcoords=True,export_normals=True,export_materials='EXPORT')
for obj in export_objects:
    bpy.data.objects.remove(obj,do_unlink=True)
bpy.data.collections.remove(export_collection)
print('STAGE: blend and glb saved',flush=True)
bpy.ops.object.select_all(action='DESELECT')
scene.render.filepath=str(OUT/'preview_front.png')
bpy.ops.render.render(write_still=True)
point_camera((-13,18,11.5),target=(.3,0,4.4),scale=15.1)
scene.render.filepath=str(OUT/'preview_back.png')
scene.render.resolution_x=1200
scene.render.resolution_y=1200
bpy.ops.render.render(write_still=True)
print('MEDIEVAL_SHOP_BUILD_OK',flush=True)
