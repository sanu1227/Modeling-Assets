"""Build an editable city from eight shared building designs and reusable street props."""
import json
import math
import random
import tempfile
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/AurelCity'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / '.temp').mkdir(exist_ok=True)
tempfile.tempdir = str(OUT / '.temp')
bpy.context.preferences.filepaths.temporary_directory = tempfile.tempdir
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.cycles.adaptive_threshold = .035
scene.cycles.max_bounces = 8
scene.cycles.transmission_bounces = 5
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'
prefs.get_devices()
for device in prefs.devices:
    device.use = device.type != 'CPU'
scene.cycles.device = 'GPU'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.exposure = -1.65
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_percentage = 100
random.seed(251024)


def collection(name, visible=True):
    result = bpy.data.collections.new(name)
    if visible:
        scene.collection.children.link(result)
    return result


buildings = collection('01_Buildings_34')
streets = collection('02_Streets_and_Sidewalks')
landscape = collection('03_Parks_and_Street_Trees')
furniture = collection('04_Street_Furniture')
traffic = collection('05_Vehicles_and_People')
rig = collection('90_Cameras_and_Lighting')
templates = {}
placements = []

# Evaluate the native source so hard edges retain connected topology in the city.
with bpy.data.libraries.load(str(ROOT / 'assets/ModernTower/Aurel_Day.blend'), link=False) as (source, imported):
    imported.collections = [name for name in source.collections if name[:2] in ('01', '02', '03', '04', '05', '06')]
for col in imported.collections:
    scene.collection.children.link(col)
bpy.context.view_layer.update()
aurel = collection('KIT_Aurel_Office', False)
graph = bpy.context.evaluated_depsgraph_get()
source_objects = {obj for col in imported.collections for obj in col.objects}
for col in imported.collections:
    bpy.ops.object.select_all(action='DESELECT')
    copies = []
    for original in list(col.objects):
        if original.type != 'MESH':
            continue
        data = bpy.data.meshes.new_from_object(original.evaluated_get(graph),
                                               preserve_all_data_layers=True, depsgraph=graph)
        obj = bpy.data.objects.new('City_Aurel_copy', data)
        scene.collection.objects.link(obj)
        obj.matrix_world = original.matrix_world
        obj.select_set(True)
        copies.append(obj)
    if copies:
        bpy.context.view_layer.objects.active = copies[0]
        bpy.ops.object.join()
        obj = copies[0]
        obj.name = 'Aurel_' + col.name[3:]
        scene.cursor.location = (0, 0, 0)
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        scene.collection.objects.unlink(obj)
        aurel.objects.link(obj)
for obj in source_objects:
    bpy.data.objects.remove(obj, do_unlink=True)
for col in imported.collections:
    bpy.data.collections.remove(col)
templates['Aurel'] = aurel


def material(name, color, rough=.5, metal=0, transmission=0, emission=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    node = mat.node_tree.nodes.get('Principled BSDF')
    for key, value in [('Base Color', (*color, 1)), ('Roughness', rough),
                       ('Metallic', metal), ('Transmission Weight', transmission), ('IOR', 1.46)]:
        node.inputs[key].default_value = value
    node.inputs['Emission Color'].default_value = (*color, 1)
    node.inputs['Emission Strength'].default_value = emission
    return mat


def existing(name, fallback):
    return bpy.data.materials.get(name) or material(name, fallback)


stone = existing('Limestone', (.7, .665, .575))
concrete = existing('Concrete', (.47, .49, .48))
bronze = existing('Satin_bronze', (.36, .28, .17))
dark = existing('Anodized_dark', (.065, .085, .095))
wood = existing('Smoked_oak', (.29, .18, .095))
clear = existing('Low_iron_glass', (.92, .97, .97))
steel = material('CITY_Brushed_aluminum', (.5, .57, .59), .26, .8)
white = material('CITY_Porcelain', (.76, .77, .72), .44)
terra = material('CITY_Terracotta', (.43, .16, .085), .7)
terra2 = material('CITY_Clay_light', (.6, .3, .17), .68)
blue = material('CITY_Blue_vision_glass', (.52, .72, .80), .04, 0, 1)
smoke = material('CITY_Smoke_vision_glass', (.55, .62, .64), .055, 0, 1)
teal = material('CITY_Teal_vision_glass', (.47, .72, .66), .045, 0, 1)
glasses = [blue, smoke, teal]
core = material('CITY_Interior_wall', (.085, .105, .12), .82)
ceiling = material('CITY_Ceiling', (.58, .59, .55), .7)
roadmat = material('CITY_Asphalt', (.075, .085, .1), .94)
paving = material('CITY_Sidewalk', (.5, .52, .49), .85)
stripe = material('CITY_Road_paint', (.85, .85, .75), .72)
yellow = material('CITY_Median_paint', (.68, .43, .07), .78)
grass = material('CITY_Lawn', (.13, .235, .075), .94)
soil = material('CITY_Planting_soil', (.11, .08, .045), .99)
foliage = [material('CITY_Foliage_' + str(i), c, .8) for i, c in enumerate([
    (.09, .19, .045), (.17, .29, .08), (.24, .34, .10), (.12, .23, .07)])]
bark = material('CITY_Bark', (.20, .14, .075), .85)
warm = material('CITY_Interior_light', (1.0, .70, .34), .4, emission=2.5)
led = material('CITY_Lamp_diffuser', (.96, .87, .63), .4, emission=4)
water = material('CITY_Water', (.045, .27, .31), .12, .26, .28)
awning = material('CITY_Store_awning', (.07, .16, .19), .8)
rubber = material('CITY_Tire', (.018, .022, .025), .88)


class Batch:
    """One mesh per design layer, with shared data at every city placement."""
    def __init__(self):
        self.verts, self.faces, self.indices, self.materials = [], [], [], []

    def add(self, vertices, faces, mat):
        start = len(self.verts)
        if mat not in self.materials:
            self.materials.append(mat)
        index = self.materials.index(mat)
        self.verts.extend(vertices)
        self.faces.extend(tuple(start + k for k in face) for face in faces)
        self.indices.extend([index] * len(faces))

    def box(self, size, location, mat, angle=0):
        x, y, z = (s / 2 for s in size)
        ca, sa = math.cos(angle), math.sin(angle)
        vertices = [(location[0] + a * ca - b * sa, location[1] + a * sa + b * ca,
                     location[2] + c) for a, b, c in [
            (-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
            (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]]
        self.add(vertices, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                            (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)

    def prism(self, outline, bottom, top, mat):
        n = len(outline)
        self.add([(x, y, z) for z in (bottom, top) for x, y in outline],
                 [tuple(reversed(range(n))), tuple(range(n, 2*n))] +
                 [(i, (i+1) % n, (i+1) % n+n, i+n) for i in range(n)], mat)

    def tube(self, a, b, radius, mat, sides=10):
        a, b = Vector(a), Vector(b)
        direction = (b-a).normalized()
        u = direction.cross(Vector((0, 0, 1)))
        if u.length < .01:
            u = Vector((1, 0, 0))
        u.normalize()
        v = direction.cross(u)
        vertices = [tuple(p + radius*(u*math.cos(i*math.tau/sides)+v*math.sin(i*math.tau/sides)))
                    for p in (a, b) for i in range(sides)]
        self.add(vertices, [tuple(reversed(range(sides))), tuple(range(sides, 2*sides))] +
                 [(i, (i+1) % sides, (i+1) % sides+sides, i+sides) for i in range(sides)], mat)

    def finish(self, name, target, bevel=0):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.verts, [], self.faces)
        mesh.update()
        for mat in self.materials:
            mesh.materials.append(mat)
        uv = mesh.uv_layers.new(name='UV_Surface')
        for poly, index in zip(mesh.polygons, self.indices):
            poly.material_index = index
            axis = max(range(3), key=lambda i: abs(poly.normal[i]))
            a, b = [i for i in range(3) if i != axis]
            for loop in poly.loop_indices:
                p = mesh.vertices[mesh.loops[loop].vertex_index].co
                uv.data[loop].uv = (p[a]*.35, p[b]*.35)
        obj = bpy.data.objects.new(name, mesh)
        target.objects.link(obj)
        if bevel:
            mod = obj.modifiers.new('Small edge highlights', 'BEVEL')
            mod.width = bevel
            mod.segments = 1
        return obj


def face_box(batch, side, along, distance, z, width, depth, height, mat):
    angle = side * math.pi/2
    batch.box((width, depth, height),
              (along*math.cos(angle)+distance*math.sin(angle),
               along*math.sin(angle)-distance*math.cos(angle), z), mat, angle)


def label(text, loc, size, target, mat=bronze):
    data = bpy.data.curves.new(text, 'FONT')
    data.body = text
    data.align_x = 'CENTER'
    data.size = size
    data.extrude = .012
    data.resolution_u = 3
    data.materials.append(mat)
    obj = bpy.data.objects.new('Sign_' + text, data)
    target.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (math.pi/2, 0, 0)
    # The text stays editable in the building kit; GLB converts curves on export.
    return obj


def rooftop(b, w, d, z):
    b.box((w-1, d-1, .25), (0, 0, z), concrete)
    for side in range(4):
        span, depth = (w, d) if side % 2 == 0 else (d, w)
        face_box(b, side, 0, depth/2-.2, z+.5, span, .18, 1.0, dark)
    b.box((w*.35, d*.28, 2.2), (0, 1, z+1.22), dark)
    for h in range(9):
        b.box((w*.36, .13, .07), (0, 1-d*.14-.08, z+.3+h*.23), steel)
    for x in (-w*.27, w*.27):
        b.box((2.2, 3.5, 1.1), (x, 1, z+.67), steel)
        for y in (0, 1.8):
            b.tube((x, y, z+1.22), (x, y, z+1.3), .72, dark, 16)


def podium(b, g, w, d, mat=stone):
    b.box((w+.7, d+.7, .25), (0, 0, .125), mat)
    b.box((w+.7, d+.7, .38), (0, 0, 4.6), mat)
    b.box((w-5, d-5, 4.0), (0, .6, 2.2), core)
    for side in range(4):
        span, depth = (w, d) if side % 2 == 0 else (d, w)
        count = round(span/3)
        bay = span/count
        for k in range(count):
            p = -span/2+(k+.5)*bay
            face_box(g, side, p, depth/2-.13, 2.35, bay-.12, .055, 4.25, clear)
            face_box(b, side, p-bay/2, depth/2, 2.35, .14, .28, 4.4, dark)
            if k % 3 == 0:
                face_box(b, side, p-bay/2, depth/2+.03, 2.35, .45, .6, 4.45, mat)
            face_box(b, side, p, depth/2-1, 4.2, bay*.65, .2, .055, warm)
    b.box((8, 2.8, .22), (0, -d/2-.7, 3.45), bronze)
    for x in (-1.5, 0, 1.5):
        b.box((.05, .12, 3.1), (x, -d/2-.20, 1.8), bronze)
        b.box((.035, .1, .85), (x+.5, -d/2-.27, 1.65), bronze)


def rect_tier(b, g, w, d, n, z0, style, seed):
    rng = random.Random(seed)
    h = 3.35 if style in ('Terra', 'Arcade') else 3.65
    wall = terra if style in ('Terra', 'Arcade') else white if style == 'Civic' else stone if style == 'Lumen' else dark
    frame = bronze if style == 'Lumen' else white if style == 'Vela' else steel
    b.box((w-2.0, d-2.0, n*h), (0, 0, z0+n*h/2), core)
    for level in range(n):
        z = z0 + level*h
        b.box((w+.3, d+.3, .24), (0, 0, z+.12), wall if style != 'Vela' else ceiling)
        for side in range(4):
            span, depth = (w, d) if side % 2 == 0 else (d, w)
            bay_count = max(3, round(span/(3.3 if style != 'Lumen' else 2.7)))
            bay = span/bay_count
            for k in range(bay_count):
                p = -span/2 + (k+.5)*bay
                gap = .65 if style in ('Terra', 'Arcade', 'Lumen') else .13
                face_box(g, side, p, depth/2-.08, z+h*.57, bay-gap, .06, h*.73, glasses[(k+level//3+seed) % 3])
                face_box(b, side, p, depth/2+.01, z+.47, bay-.03, .16, .70, wall if style != 'Vela' else dark)
                face_box(b, side, p-bay/2, depth/2+.06, z+h/2, gap*.65, .24, h, frame if style == 'Vela' else wall)
                face_box(b, side, p, depth/2+.04, z+h-.06, bay, .19, .095, dark)
                face_box(b, side, p, depth/2-.52, z+h-.34, bay-.3, .85, .06, ceiling)
                # Shallow furnished window bays retain depth without duplicating complete interiors.
                if (level+k) % 4 == 0:
                    face_box(b, side, p, depth/2-.65, z+.85, bay*.55, .5, .065, wood)
                    face_box(b, side, p, depth/2-.62, z+1.10, .42, .06, .32, dark)
                if rng.random() < .23:
                    face_box(b, side, p, depth/2-.45, z+h-.4, bay*.63, .22, .04, warm)
                if style == 'Terra' and (k+level//2) % 3 != 1:
                    face_box(b, side, p, depth/2+.5, z+.24, bay-.3, 1.35, .18, white)
                    face_box(g, side, p, depth/2+1.15, z+.81, bay-.35, .045, .95, smoke)
                    face_box(b, side, p, depth/2+1.16, z+1.30, bay-.28, .055, .05, dark)
                if style == 'Arcade':
                    face_box(b, side, p, depth/2+.09, z+.90, bay-.52, .32, .12, stone)
            if style == 'Civic':
                face_box(b, side, 0, depth/2+.38, z+.42, span+.65, .85, .28, white)
    if style in ('Vela', 'Lumen'):
        for side in range(4):
            span, depth = (w, d) if side % 2 == 0 else (d, w)
            count = round(span/(3.3 if style == 'Vela' else 2.7))
            for k in range(count+1):
                face_box(b, side, -span/2+k*span/count, depth/2+.23, z0+n*h/2,
                         .13 if style == 'Vela' else .24, .5, n*h, frame)
    return z0+n*h


specs = [('Vela', 30, 27, 0), ('Terra', 25, 32, 14), ('Lumen', 25, 30, 20),
         ('Civic', 28, 32, 8), ('Arcade', 27, 32, 5)]
for design, w, d, floors in specs:
    kit = collection('KIT_' + design, False)
    b, g = Batch(), Batch()
    podium(b, g, w, d, terra if design == 'Arcade' else stone)
    if design == 'Vela':
        z = 4.8
        for k, (tw, td, levels) in enumerate([(30, 27, 18), (24, 22, 8), (18, 17, 5)]):
            z = rect_tier(b, g, tw, td, levels, z, design, k+1)
            rooftop(b, tw, td, z)
    else:
        z = rect_tier(b, g, w, d, floors, 4.8, design, floors)
        rooftop(b, w, d, z)
    if design == 'Arcade':
        for x in (-9, 0, 9):
            b.box((7.5, 2.1, .16), (x, -d/2-.85, 3.25), awning)
            b.box((7.5, .12, .35), (x, -d/2-1.85, 3.10), awning)
    b.finish(design + '_Architecture', kit, .012)
    g.finish(design + '_Glazing', kit)
    label({'Vela': 'V E L A', 'Terra': 'TERRA RESIDENCES', 'Lumen': 'LUMEN HOTEL',
           'Civic': 'STUDIO / 08', 'Arcade': 'MARKET & COFFEE'}[design], (0, -d/2-.22, 3.85), .6, kit)
    templates[design] = kit
    print('DESIGN_READY', design, flush=True)

# Harbor: an elliptical office tower with continuous silver floor ribbons.
kit = collection('KIT_Harbor', False)
b, g = Batch(), Batch()
n = 36
outline = [(17*math.cos(i*math.tau/n), 14*math.sin(i*math.tau/n)) for i in range(n)]
b.prism([(x*1.035, y*1.035) for x, y in outline], 0, .3, stone)
b.prism([(x*.88, y*.88) for x, y in outline], .2, 87.5, core)
for level in range(24):
    z = .3 + level*3.65
    b.prism([(x*1.025, y*1.025) for x, y in outline], z, z+.27, steel)
    for i in range(n):
        a, c = Vector(outline[i]), Vector(outline[(i+1) % n])
        mid, delta = (a+c)/2, c-a
        angle = math.atan2(delta.y, delta.x)
        g.box((delta.length-.08, .06, 3.23), (mid.x, mid.y, z+1.94), blue, angle)
        b.box((.09, .3, 3.65), (a.x, a.y, z+1.83), white, angle)
        b.box((delta.length, .16, .52), (mid.x, mid.y, z+.48), dark, angle)
        if (i+level) % 5 == 0:
            b.box((delta.length*.65, .28, .06), (mid.x*.95, mid.y*.95, z+3.4), warm, angle)
b.prism(outline, 87.9, 88.2, steel)
for z in (88.6, 89.2, 89.8):
    for i in range(n):
        a, c = Vector(outline[i]), Vector(outline[(i+1) % n])
        delta, mid = c-a, (a+c)/2
        b.box((delta.length+.05, .25, .14), (mid.x, mid.y, z), steel, math.atan2(delta.y, delta.x))
rooftop(b, 16, 12, 88.2)
b.box((12, 4, .25), (0, -15, 4.0), white)
b.finish('Harbor_Architecture', kit, .01)
g.finish('Harbor_Glazing', kit)
label('H A R B O R', (0, -14.4, 4.6), .85, kit, white)
templates['Harbor'] = kit

# Public library in the civic square.
kit = collection('KIT_Library', False)
b, g = Batch(), Batch()
podium(b, g, 40, 24)
b.box((32, 17, 5), (0, 1, 7.3), core)
for z in (5.0, 10.1):
    b.box((43, 27, .5), (0, 0, z), white)
for side in range(4):
    w, d = (40, 24) if side % 2 == 0 else (24, 40)
    for k in range(round(w/.7)):
        p = -w/2+k*.7
        face_box(b, side, p, d/2+.2, 7.55, .12, .45, 4.8, wood)
    face_box(g, side, 0, d/2-.12, 7.55, w, .08, 4.6, clear)
rooftop(b, 32, 17, 10.2)
b.finish('Library_Architecture', kit, .012)
g.finish('Library_Glazing', kit)
label('AUREL CITY LIBRARY', (0, -12.3, 4.0), .85, kit)
templates['Library'] = kit
print('STAGE: eight building designs including the existing Aurel', flush=True)


def place(design, name, location, angle=0, scale=(1, 1, 1), target=buildings):
    parent = bpy.data.objects.new(name, None)
    target.objects.link(parent)
    parent.location = location
    parent.rotation_euler.z = angle
    parent.scale = scale
    parent['design'] = design
    for original in templates[design].objects:
        obj = original.copy()
        obj.data = original.data
        obj.name = name + '__' + original.name
        target.objects.link(obj)
        obj.parent = parent
        obj.matrix_parent_inverse.identity()
    return parent


def building(design, x, y, block, angle=0, scale=(1, 1, 1)):
    name = f'B{len(placements)+1:02d}_{design}'
    parent = place(design, name, (x, y, .23), angle, scale)
    parent['block'] = block
    placements.append({'name': name, 'design': design, 'block': block,
                       'location': [x, y, .23], 'rotation_z': angle, 'scale': list(scale)})


xs = [-184, -92, 0, 92, 184]
ys = [-138, -46, 46, 138]
for j, y in enumerate(ys):
    for i, x in enumerate(xs):
        block = f'{chr(65+j)}{i+1}'
        if (i, j) == (2, 1):
            continue
        if (i, j) == (2, 2):
            building('Library', x, y+12, block)
        elif (i, j) == (1, 1):
            building('Aurel', x, y, block)
        elif (i, j) == (1, 2):
            building('Harbor', x, y, block)
        elif (i, j) == (3, 2):
            building('Vela', x, y, block)
        else:
            choices = ['Arcade', 'Civic'] if j == 0 else ['Terra', 'Lumen'] if j == 3 else ['Civic', 'Terra', 'Lumen', 'Arcade']
            for k, dx in enumerate((-18, 18)):
                design = choices[(i+j+k) % len(choices)]
                scale = (1, 1, [.85, .94, 1, 1.08, 1.14][(i*3+j+k) % 5])
                building(design, x+dx, y, block, math.pi if (j == 3) else 0, scale)
assert len(placements) == 34

# Continuous road mesh, separate raised sidewalks, and coherent four-way intersections.
b, markings, paths = Batch(), Batch(), Batch()
b.box((480, 388, .32), (0, 0, -.21), roadmat)
for x in xs:
    for y in ys:
        b.box((74, 74, .28), (x, y, .09), paving)
        for side in (-1, 1):
            b.box((74, .22, .12), (x, y+side*36.85, .25), stone)
            b.box((.22, 74, .12), (x+side*36.85, y, .25), stone)
        # Regular expansion joints keep ground close-ups readable.
        for t in range(-34, 35, 4):
            paths.box((.035, 5.0, .012), (x+t, y-33.8, .237), concrete)
            paths.box((.035, 5.0, .012), (x+t, y+33.8, .237), concrete)
            paths.box((5.0, .035, .012), (x-33.8, y+t, .237), concrete)
            paths.box((5.0, .035, .012), (x+33.8, y+t, .237), concrete)
roads_x = [-230, -138, -46, 46, 138, 230]
roads_y = [-184, -92, 0, 92, 184]
for x in roads_x:
    for y in ys:
        for dx in (-.24, .24):
            markings.box((.11, 66, .008), (x+dx, y, -.043), yellow)
        for dy in range(-30, 31, 9):
            for dx in (-4.7, 4.7):
                markings.box((.10, 3.4, .008), (x+dx, y+dy, -.043), stripe)
for y in roads_y:
    for x in xs:
        for dy in (-.24, .24):
            markings.box((66, .11, .008), (x, y+dy, -.043), yellow)
        for dx in range(-30, 31, 9):
            for dy in (-4.7, 4.7):
                markings.box((3.4, .10, .008), (x+dx, y+dy, -.043), stripe)
for x in roads_x:
    for y in roads_y:
        for direction in (-1, 1):
            if -184 < y+direction*13 < 184:
                for t in range(-7, 8):
                    markings.box((.45, 3.0, .008), (x+t, y+direction*13, -.039), stripe)
            if -230 < x+direction*13 < 230:
                for t in range(-7, 8):
                    markings.box((3.0, .45, .008), (x+direction*13, y+t, -.039), stripe)
b.finish('Roads_and_Block_Sidewalks', streets, .015)
markings.finish('Lane_Markings_and_Crosswalks', streets)
paths.finish('Sidewalk_Joints', streets)

# Reusable broadleaf trees: closed, individually angled leaves rather than solid green spheres.
for variation in range(3):
    kit = collection('KIT_Tree_' + str(variation), False)
    tree = Batch()
    rng = random.Random(500+variation)
    tree.tube((0, 0, 0), (.08, .05, 4.4), .14, bark, 10)
    for i in range(12):
        angle = i*2.4
        center = Vector((math.cos(angle)*1.25, math.sin(angle)*1.25, 3.4+i*.14))
        tree.tube((0, 0, 2.3+i*.16), center, .045, bark, 6)
        for k in range(54):
            p = center + Vector((rng.gauss(0, .64), rng.gauss(0, .64), rng.gauss(0, .6)))
            axis = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-.4, .8))).normalized()
            u = axis.cross(Vector((0, 0, 1))).normalized()
            normal = axis.cross(u)*.014
            length = rng.uniform(.15, .26)
            verts = [tuple(p-axis*length), tuple(p+u*length*.44), tuple(p+axis*length),
                     tuple(p-u*length*.44), tuple(p+normal), tuple(p-normal)]
            tree.add(verts, [(c, a, 4) for a, c in [(0, 1), (1, 2), (2, 3), (3, 0)]] +
                     [(a, c, 5) for a, c in [(0, 1), (1, 2), (2, 3), (3, 0)]], foliage[rng.randrange(4)])
    tree.finish('Tree_' + str(variation), kit)
    templates['Tree_' + str(variation)] = kit

plants, park, props = Batch(), Batch(), Batch()
tree_count = 0


def plant(x, y, scale=1, planter=False):
    global tree_count
    if planter:
        plants.box((2.6, 2.6, .45), (x, y, .45), stone)
        plants.box((2.35, 2.35, .035), (x, y, .69), soil)
    else:
        plants.box((2.3, 2.3, .035), (x, y, .25), soil)
    parent = place('Tree_' + str(tree_count % 3), f'Tree_{tree_count:03}',
                   (x, y, .71 if planter else .28), tree_count*2.4, (scale, scale, scale), landscape)
    tree_count += 1
    return parent


def bench(x, y, angle=0):
    for dy in (-.4, -.2, 0, .2, .4):
        props.box((2.5, .16, .07), (x-dy*math.sin(angle), y+dy*math.cos(angle), .72), wood, angle)
    for dx in (-.85, .85):
        props.box((.14, .78, .45), (x+dx*math.cos(angle), y+dx*math.sin(angle), .45), dark, angle)


for j, y in enumerate(ys):
    for i, x in enumerate(xs):
        for dx in (-26, 0, 26):
            plant(x+dx, y-31, .96+(i % 3)*.06)
            plant(x+dx, y+31, 1.0)
        for dy in (-15, 15):
            plant(x-34.5, y+dy, .9)
            plant(x+34.5, y+dy, 1.05)
        bench(x-9, y-32)
        bench(x+9, y+32)

# Central park block B3: crossed paths, flower beds, water garden, and a raised timber pavilion.
for x, y, w, d in [(-19, -65, 25, 25), (19, -65, 25, 25), (-19, -27, 25, 25), (19, -27, 25, 25)]:
    park.box((w, d, .07), (x, y, .27), grass)
    for dx, dy in [(-7, -7), (7, 7), (-7, 7)]:
        plant(x+dx, y+dy, 1.15+(tree_count % 3)*.09)
park.box((10, 65, .035), (0, -46, .255), stone)
park.box((65, 9, .035), (0, -46, .255), stone)
park.tube((0, -46, .27), (0, -46, .55), 7.0, stone, 64)
park.tube((0, -46, .56), (0, -46, .60), 6.5, water, 64)
park.tube((0, -46, .61), (0, -46, 1.25), 1.8, stone, 32)
park.tube((0, -46, 1.26), (0, -46, 1.31), 1.65, water, 32)
for x in (-9, 9):
    for y in (-57, -35):
        bench(x, y, math.pi/2)
for x in (-23, 23):
    park.box((10, 8, .18), (x, -46, .4), wood)
    for dx in (-4, 4):
        for dy in (-3, 3):
            park.box((.2, .2, 3.1), (x+dx, -46+dy, 2), bronze)
    for t in range(-10, 11):
        park.box((.16, 8.3, .18), (x+t*.48, -46, 3.6), wood)

# Library square C3 and landmark forecourts.
park.box((55, 20, .06), (0, 24, .28), stone)
park.box((19, 8, .4), (0, 24, .52), dark)
park.box((18.5, 7.5, .045), (0, 24, .75), water)
for x in (-24, 24):
    plant(x, 22, 1.05, True)
    plant(x, 35, 1.05, True)
for x in (-92, 92):
    for dx in (-25, 25):
        park.box((9, 37, .06), (x+dx, 46, .28), grass)
        plant(x+dx, 36, 1.1)
        plant(x+dx, 56, 1.15)
park.finish('Parks_Plazas_and_Water', landscape, .012)
plants.finish('Tree_Pits_and_Planters', landscape, .01)

# Lamps, traffic signals and litter bins share consolidated meshes.
for y in ys:
    for x in roads_x[1:-1]:
        for sign in (-1, 1):
            px, py = x+sign*11, y
            props.tube((px, py, .25), (px, py, 7.6), .075, dark, 10)
            props.tube((px, py, 7.6), (px-sign*2, py, 7.6), .06, dark, 8)
            props.box((1.0, .35, .13), (px-sign*1.7, py, 7.55), dark)
            props.box((.8, .25, .025), (px-sign*1.7, py, 7.47), led)
red = material('CITY_Traffic_red', (.8, .02, .01), .4, emission=2)
green = material('CITY_Traffic_green', (.04, .7, .32), .4, emission=2)
for x in roads_x[1:-1]:
    for y in roads_y[1:-1]:
        for sign in (-1, 1):
            px, py = x+sign*11, y+sign*11
            props.tube((px, py, .25), (px, py, 5.1), .07, dark)
            props.box((.35, .35, 1.1), (px, py, 4.8), dark)
            for dz in (-.32, 0, .32):
                active = red if sign > 0 and dz == .32 else green if sign < 0 and dz == -.32 else rubber
                props.box((.18, .018, .18), (px, py-.19, 4.8+dz), active)
for y in ys:
    for x in xs:
        props.box((.75, .65, 1.1), (x+14, y-32, .8), dark)
        props.box((.65, .52, .035), (x+14, y-32, 1.37), steel)
props.finish('Benches_Lamps_Signals_Bins', furniture, .01)

# Compact car prototypes, reused without duplicated mesh data.
paints = [( .11, .17, .23), (.62, .12, .07), (.72, .73, .70), (.025, .04, .05), (.60, .43, .13)]
for k, color in enumerate(paints):
    kit = collection(f'KIT_Car_{k}', False)
    c = Batch()
    paint = material('CITY_Car_paint_' + str(k), color, .22, .5)
    c.box((1.85, 4.4, .62), (0, 0, .75), paint)
    # Sloped closed cabin volume.
    c.add([(-.86, -1.15, 1.04), (.86, -1.15, 1.04), (.86, 1.35, 1.04), (-.86, 1.35, 1.04),
           (-.7, -.65, 1.65), (.7, -.65, 1.65), (.7, .78, 1.65), (-.7, .78, 1.65)],
          [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], smoke)
    c.box((1.43, 1.45, .05), (0, .05, 1.67), paint)
    for x in (-.89, .89):
        for y in (-1.35, 1.35):
            c.tube((x-.09, y, .48), (x+.09, y, .48), .37, rubber, 16)
            c.tube((x-.095, y, .48), (x+.095, y, .48), .21, steel, 12)
    for x in (-.62, .62):
        c.box((.42, .045, .16), (x, -2.22, .85), led)
        c.box((.42, .045, .16), (x, 2.22, .85), red)
    c.finish(f'Car_{k}', kit, .006)
    templates[f'Car_{k}'] = kit
car_count = 0
for row, y in enumerate(roads_y):
    for i, x in enumerate(xs):
        for side in (-1, 1):
            px = x+random.choice([-24, -13, 8, 22])
            place(f'Car_{car_count % 5}', f'Car_{car_count:03}', (px, y+side*3, -.04),
                  math.pi/2 if side > 0 else -math.pi/2, target=traffic)
            car_count += 1
for x in roads_x[1:-1]:
    for y in ys:
        place(f'Car_{car_count % 5}', f'Car_{car_count:03}', (x+3, y-18, -.04), target=traffic)
        car_count += 1

# Restrained scale figures, primarily in the park and library square.
people = Batch()
clothes = [dark, terra, awning, white]
people_locations = []
for i in range(32):
    x = random.choice([-6, 6] if i < 22 else [-25, -14, 14, 25]) + random.uniform(-1.5, 1.5)
    y = random.uniform(-74, -15) if i < 22 else random.uniform(11, 35)
    if i < 22 and abs(y+46) < 9:
        y += 16
    people_locations.append([x, y])
    z = .27
    shirt = clothes[i % len(clothes)]
    for dx in (-.12, .12):
        people.tube((x+dx, y, z+.1), (x+dx, y, z+.83), .075, dark, 6)
    people.box((.43, .25, .58), (x, y, z+1.11), shirt)
    people.tube((x, y, z+1.42), (x, y, z+1.70), .13, stone, 10)
    for dx in (-.28, .28):
        people.tube((x+dx, y, z+.80), (x+dx, y, z+1.36), .065, shirt, 6)
people.finish('Pedestrians_for_scale', traffic, .012)
print('STAGE: 34 buildings, 20 blocks, roads, parks and street props ready', flush=True)

# A neutral studio world keeps the complete city legible; streets retain natural sun shadows.
world = bpy.data.worlds.new('City_daylight')
scene.world = world
world.use_nodes = True
nodes, links = world.node_tree.nodes, world.node_tree.links
sky = nodes.new('ShaderNodeTexSky')
sky.sky_type = 'MULTIPLE_SCATTERING'
sky.sun_elevation = math.radians(32)
sky.sun_rotation = math.radians(140)
nodes['Background'].inputs['Strength'].default_value = .4
links.new(sky.outputs['Color'], nodes['Background'].inputs['Color'])
ground = Batch()
ground.box((20000, 20000, .1), (0, 0, -.49), material('CITY_Backdrop', (.31, .36, .37), .93))
ground.finish('Studio_ground_EXCLUDE_EXPORT', rig)


def camera(name, location, target, lens, ortho=None):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    rig.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()
    data.lens = lens
    data.clip_end = 30000
    if ortho:
        data.type = 'ORTHO'
        data.ortho_scale = ortho
    return obj


hero = camera('Camera_01_City_Aerial', (470, -650, 490), (0, 0, 26), 48, 620)
avenue = camera('Camera_02_Central_Avenue', (46, -205, 6), (46, 38, 27), 28)
parkcam = camera('Camera_03_Park_and_Library', (68, -143, 51), (-10, 29, 29), 40)
top = camera('Camera_04_Layout', (0, 0, 650), (0, 0, 0), 50, 510)
scene.camera = hero
scene.render.resolution_x = 2200
scene.render.resolution_y = 1700
scene.render.filepath = str(OUT / 'city_aerial.png')
scene['city_name'] = 'AUREL CITY'
scene['description'] = '34 buildings, eight designs, 20 blocks; streets, central park and civic square'
scene['units'] = 'meters; 460 x 368m between perimeter road center lines'
scene['instancing'] = 'Building and tree mesh data are shared across placements. Edit one mesh to change all copies.'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_location = (0, 0, 25)
            area.spaces.active.region_3d.view_distance = 610
            area.spaces.active.region_3d.view_rotation = hero.rotation_euler.to_quaternion()
            area.spaces.active.shading.type = 'MATERIAL'
            area.spaces.active.clip_end = 10000
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Aurel_City.blend'))
# Save a native, linked-data building kit separately, without forcing a second full city copy.
building_designs = ['Aurel', 'Vela', 'Harbor', 'Terra', 'Lumen', 'Civic', 'Arcade', 'Library']
bpy.data.libraries.write(str(OUT / 'Aurel_Building_Kit.blend'), {templates[n] for n in building_designs}, fake_user=True)
manifest = {'city': 'AUREL CITY', 'building_count': len(placements), 'designs': building_designs,
            'blocks': 20, 'road_center_extent_m': [460, 368], 'ground_extent_m': [480, 388],
            'trees_added': tree_count, 'cars': car_count, 'scale_figures': 32,
            'placements': placements, 'people_locations': people_locations}
(OUT / 'city_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('STAGE: native city and building kit saved', flush=True)

for cam, filename, resolution in [(hero, 'city_aerial.png', (2200, 1700)),
                                  (avenue, 'city_avenue.png', (1920, 1280)),
                                  (parkcam, 'city_park.png', (1920, 1280)),
                                  (top, 'city_layout.png', (1600, 1300))]:
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)
    print('RENDER_READY', filename, flush=True)
print('AUREL_CITY_BUILD_OK', flush=True)
