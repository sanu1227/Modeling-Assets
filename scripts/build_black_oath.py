"""Build an editable dark-fantasy galleon. Only writes assets/PirateShip."""
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
OUT = ROOT / 'assets' / 'PirateShip'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'Textures').mkdir(exist_ok=True)
(OUT / '.temp').mkdir(exist_ok=True)
tempfile.tempdir = str(OUT / '.temp')
bpy.context.preferences.filepaths.temporary_directory = tempfile.tempdir
bpy.context.preferences.filepaths.save_version = 0
random.seed(23184)
rng = np.random.default_rng(23184)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
groups = {}
for name in ['01_Hull', '02_Decks', '03_Sterncastle', '04_Artillery',
             '05_Masts', '06_Sails', '07_Rigging', '08_Ornament',
             '09_Deck_Equipment', '90_Presentation']:
    c = bpy.data.collections.new(name)
    scene.collection.children.link(c)
    groups[name] = c
current = '01_Hull'
cache = {}


def log(message):
    print('BLACK_OATH: ' + message, flush=True)


def put(obj, group=None):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    groups[group or current].objects.link(obj)
    return obj


def uv_project(data):
    layer = data.uv_layers.new(name='SurfaceUV')
    for p in data.polygons:
        axis = max(range(3), key=lambda k: abs(p.normal[k]))
        axes = [k for k in range(3) if k != axis]
        for li in p.loop_indices:
            v = data.vertices[data.loops[li].vertex_index].co
            layer.data[li].uv = (v[axes[0]] * .22, v[axes[1]] * .7)


def mesh(name, verts, faces, mat, bevel=0, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    bm = bmesh.new()
    bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(data)
    bm.free()
    data.materials.append(mat)
    uv_project(data)
    if smooth:
        for p in data.polygons:
            p.use_smooth = True
    obj = bpy.data.objects.new(name, data)
    groups[current].objects.link(obj)
    if bevel:
        m = obj.modifiers.new('Small edge wear', 'BEVEL')
        m.width = bevel
        m.segments = 2
    return obj


def box(name, size, loc, mat, bevel=.02, rot=None):
    key = ('box', tuple(round(float(s), 5) for s in size), mat.name, bevel)
    if key in cache:
        obj = cache[key].copy()
        obj.name = name
        groups[current].objects.link(obj)
    else:
        x, y, z = (s / 2 for s in size)
        obj = mesh(name, [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
                         (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)],
                   [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),
                    (2,3,7,6),(3,0,4,7)], mat, bevel)
        cache[key] = obj
    obj.location = loc
    obj.rotation_euler = rot or (0, 0, 0)
    return obj


def beam(name, a, b, width, mat, depth=None):
    a, b = Vector(a), Vector(b)
    o = box(name, (width, depth or width, (b-a).length), (a+b)/2,
            mat, min(.025, width * .1))
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return o


def cylinder(name, a, b, radius, mat, top=None, n=14):
    a, b = Vector(a), Vector(b)
    length = (b-a).length
    r2 = radius if top is None else top
    key = ('cylinder', round(length, 5), radius, r2, n, mat.name)
    if key in cache:
        o = cache[key].copy()
        o.name = name
        groups[current].objects.link(o)
    else:
        verts = [(r*math.cos(i*math.tau/n), r*math.sin(i*math.tau/n), z)
                 for z, r in [(0, radius), (length, r2)] for i in range(n)]
        faces = [tuple(reversed(range(n))), tuple(range(n, 2*n))]
        faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
        o = mesh(name, verts, faces, mat, smooth=True)
        cache[key] = o
    o.location = a
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return o


def rope(name, points, radius=.035, mat=None, closed=False):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 1
    data.bevel_depth = radius
    data.bevel_resolution = 1
    data.use_fill_caps = True
    spline = data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1)
    spline.use_cyclic_u = closed
    data.materials.append(mat or rope_mat)
    o = bpy.data.objects.new(name, data)
    groups[current].objects.link(o)
    if not closed:
        weld = o.modifiers.new('Weld curve cap vertices', 'WELD')
        weld.merge_threshold = .00001
    return o


def sag(name, a, b, drop=.3, radius=.035, mat=None):
    a, b = Vector(a), Vector(b)
    points = [a.lerp(b, t) + Vector((0, 0, -drop*4*t*(1-t)))
              for t in np.linspace(0, 1, 12)]
    return rope(name, points, radius, mat)


def ring(name, center, radius, tube, mat, axis='Z', n=40):
    center = Vector(center)
    points = []
    for a in np.linspace(0, math.tau, n, endpoint=False):
        c, s = radius*math.cos(a), radius*math.sin(a)
        p = (c,s,0) if axis == 'Z' else ((c,0,s) if axis == 'Y' else (0,c,s))
        points.append(center + Vector(p))
    return rope(name, points, tube, mat, True)


def sphere(name, loc, size, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=loc)
    o = put(bpy.context.object)
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def material(name, color, rough=.65, metal=0, texture=None, emission=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    p = nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1)
        p.inputs['Emission Strength'].default_value = emission
    if texture:
        size = 1024
        v, u = np.mgrid[0:size, 0:size].astype(np.float32)/size
        noise = rng.normal(0, .022, (size, size))
        if texture == 'wood':
            warp = v + .012*np.sin(u*math.tau*2) + .005*np.sin(u*math.tau*7)
            grain = .10*np.sin(warp*math.tau*45) + .06*np.sin(warp*math.tau*137)
            grain += .10*np.sin(warp*math.tau*7) + noise
            for _ in range(10):
                cy, cx = rng.random(2)
                grain -= .12*np.exp(-((v-cy)/.012)**2 - ((u-cx)/.14)**2)
        else:
            grain = .055*(np.sin(u*math.tau*250)+np.sin(v*math.tau*250))
            grain += .10*np.sin(u*math.tau*3)*np.cos(v*math.tau*4) + noise
            grain += .04*np.sin(v*math.tau*18+np.sin(u*math.tau*5))
        rgba = np.ones((size, size, 4), dtype=np.float32)
        rgba[:,:,:3] = np.clip(np.array(color)*(1+grain[:,:,None]), .002, .95)
        image = bpy.data.images.new(name+'_BaseColor', size, size, alpha=False)
        image.pixels.foreach_set(rgba.ravel())
        image.filepath_raw = str(OUT/'Textures'/(name+'.png'))
        image.file_format = 'PNG'
        image.save()
        image.pack()
        t = nodes.new('ShaderNodeTexImage')
        t.image = image
        t.location = (-480, 80)
        links.new(t.outputs['Color'], p.inputs['Base Color'])
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .20 if texture == 'wood' else .13
        bump.inputs['Distance'].default_value = .018 if texture == 'wood' else .008
        links.new(t.outputs['Color'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], p.inputs['Normal'])
    return m


wood = [material('Tarred_oak_'+str(i), c, .72, texture='wood')
        for i, c in enumerate([(.080,.052,.032),(.105,.070,.042),(.055,.041,.029),(.087,.067,.047)])]
deckwood = material('Weathered_deck', (.22,.145,.085), .8, texture='wood')
mastwood = material('Oiled_mast', (.14,.09,.045), .58, texture='wood')
cloth = material('Black_sailcloth', (.019,.022,.027), .92, texture='cloth')
patchmat = material('Sail_repairs', (.034,.036,.040), .95, texture='cloth')
brass = material('Weathered_bronze', (.29,.18,.065), .45, .72)
iron = material('Blackened_iron', (.035,.043,.05), .48, .78)
rope_mat = material('Hemp_rope', (.065,.043,.025), .88)
stitchmat = material('Muted_flax_stitches', (.046,.039,.029), .88)
recess = material('Unlit_recess', (.008,.009,.009), 1)
bone = material('Aged_figurehead_bronze', (.18,.11,.04), .52, .65)
amber = material('Amber_lantern_glass', (1,.31,.045), .26, .1, emission=2.5)
windowmat = material('Smoky_amber_windows', (.36,.14,.035), .33, .15, emission=.28)


def width(x, level=0):
    t = max(.0005, min(1, (x+27)/52))
    return 6.65*math.sin(math.pi*.88*t)**.62*(1-.025*max(level-1, 0))


def sheer(x):
    return .0021*(x+3)**2


def hull_point(x, level, side, inset=0):
    return (x, side*(width(x, level)-inset), level+sheer(x))


def strip_solid(name, outside, inside, mat):
    # Both lists contain corresponding points around one perimeter.
    n = len(outside)
    faces = [tuple(range(n)), tuple(reversed(range(n, 2*n)))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name, outside+inside, faces, mat)


def platform(name, x0, x1, halfwidth, z, thickness=.22):
    def deck_width(x):
        return min(halfwidth,width(x,7.8)-.12) if name=='Forecastle' else halfwidth
    if name=='Forecastle':
        stations=np.linspace(x0,x1,32)
        top=[(float(x),-deck_width(x),z) for x in stations]
        top += [(float(x),deck_width(x),z) for x in reversed(stations)]
        o=strip_solid(name,top,[(x,y,h-thickness) for x,y,h in top],deckwood)
    else:
        o = box(name, (x1-x0,halfwidth*2,thickness),
                ((x0+x1)/2,0,z-thickness/2), deckwood, .035)
    for y in np.arange(-halfwidth+.25, halfwidth, .38):
        path=[(float(x),y,z+.009) for x in np.linspace(x0+.05,x1-.05,40)
              if abs(y)<deck_width(x)-.04]
        if len(path)>1:
            rope(name+'_plank_seam',path,.009,recess)
    for x in np.arange(x0+1, x1, 3.7):
        w=deck_width(x)
        rope(name+'_butt_seam', [(x,-w+.04,z+.01),(x,w-.04,z+.01)],
             .009, recess)
    return o


def rail_path(name, points, height=1.05):
    rope(name+'_toprail', [(x,y,z+height) for x,y,z in points], .085, wood[1])
    rope(name+'_lowerrail', [(x,y,z+.36) for x,y,z in points], .045, brass)
    for i, p in enumerate(points):
        x,y,z = p
        beam(name+'_baluster', (x,y,z), (x,y,z+height), .12, wood[0])
        if i % 3 == 0:
            sphere(name+'_finial', (x,y,z+height+.08), (.12,.12,.12), brass)


def rectangular_rail(name, x0, x1, w, z, front=True):
    for side in [-1,1]:
        rail_path(name, [(x,side*w,z) for x in np.linspace(x0,x1,max(3,int((x1-x0)/1.2)+1))])
    rail_path(name, [(x1,y,z) for y in np.linspace(-w,w,9)])
    if front:
        rail_path(name, [(x0,y,z) for y in np.linspace(-w,w,9)])


log('materials and reusable geometry ready')

# The side planks are closed curved solids. Gunports are omitted geometry.
gun_x = [-20.9 + i*3.8 for i in range(12)]
port_levels = [(2.2,3.55), (5.0,6.35)]
xs = sorted(set([-26.95,25.0] + [float(x) for x in np.arange(-26,25,2.0)]
                + [x+d for x in gun_x for d in [-.78,.78]]))
levels = sorted(set([0.,7.8] + list(np.arange(.35,7.8,.35))
                    + [z for pair in port_levels for z in pair]))
for side in [-1,1]:
    for row, (lo,hi) in enumerate(zip(levels,levels[1:])):
        verts, faces = [], []
        for a,b in zip(xs,xs[1:]):
            xc, zc = (a+b)/2, (lo+hi)/2
            if any(abs(xc-g)<.78 for g in gun_x) and any(l<zc<h for l,h in port_levels):
                continue
            a, b = a+.008, b-.008
            zz0,zz1 = lo+.009,hi-.009
            coords = [(a,zz0),((a+b)/2,zz0),(b,zz0),(b,zz1),((a+b)/2,zz1),(a,zz1)]
            outer = [hull_point(x,z,side) for x,z in coords]
            inner = [hull_point(x,z,side,.24) for x,z in coords]
            base = len(verts)
            verts += outer + inner
            faces += [tuple(base+i for i in range(6)),tuple(base+i for i in range(11,5,-1))]
            faces += [(base+i,base+(i+1)%6,base+(i+1)%6+6,base+i+6) for i in range(6)]
        mesh('Port_planking' if side<0 else 'Starboard_planking',verts,faces,wood[row%4])
    for level in [.25,1.7,4.2,4.55,7.1,7.85]:
        points = [hull_point(float(x),level,side,-.09) for x in np.linspace(-26.9,25,100)]
        rope('Continuous_wale', points, .13 if level in [1.7,4.2,7.1] else .07, wood[2])
        if level in [4.55,7.85]:
            rope('Bronze_stringer', [Vector(p)+Vector((0,side*.045,.045)) for p in points],
                 .025,brass)
    # Frame straps and fastening heads follow the tumblehome.
    for x in np.arange(-23,24,3.8):
        rope('Hull_iron_strap',[hull_point(float(x),z,side,-.035) for z in np.linspace(.1,7.7,12)],
             .055,iron)
        for z in [.6,1.5,4.0,4.5,7.3]:
            p = hull_point(float(x),z,side,-.1)
            cylinder('Hull_fastener',p,Vector(p)+Vector((0,side*.045,0)),.055,iron,n=8)

bottom_x = np.linspace(-26.95,25,75)
arc_n = 29
verts = []
for x in bottom_x:
    depth = 4.6*(.58+.42*math.sin(math.pi*(x+27)/52))
    for theta in np.linspace(0,math.pi,arc_n):
        verts.append((float(x),width(x)*math.cos(theta),sheer(x)-depth*math.sin(theta)**.82))
faces = []
for j in range(len(bottom_x)-1):
    for i in range(arc_n-1):
        a = j*arc_n+i
        faces.append((a,a+1,a+1+arc_n,a+arc_n))
    faces.append((j*arc_n,(j+1)*arc_n,(j+2)*arc_n-1,(j+1)*arc_n-1))
faces += [tuple(reversed(range(arc_n))),tuple(range((len(bottom_x)-1)*arc_n,len(bottom_x)*arc_n))]
mesh('Rounded_lower_hull',verts,faces,wood[2],smooth=True)
rope('Keel',[(float(x),0,sheer(x)-4.6*(.58+.42*math.sin(math.pi*(x+27)/52)))
             for x in bottom_x],.19,wood[2])
for z in np.arange(.18,7.8,.36):
    box('Transom_plank',(.25,2*width(25,z),.34),(25,0,z+sheer(25)),wood[int(z*3)%4])
rope('Stempost',[(-26.8,0,-.5),(-27,0,4),(-27.5,0,7.5),(-29.3,0,10.4)],.23,wood[1])

current = '02_Decks'
# A curved closed deck, with separate long seams and staggered end joints.
verts = []
deck_x = np.linspace(-26.7,25,80)
ny = 13
for offset in [0,-.22]:
    for x in deck_x:
        w = max(.05,width(x,7.8)-.20)
        for y in np.linspace(-w,w,ny):
            verts.append((float(x),float(y),7.8+sheer(x)+offset))
N = len(deck_x)*ny
faces = []
for j in range(len(deck_x)-1):
    for i in range(ny-1):
        a = j*ny+i
        faces += [(a,a+ny,a+ny+1,a+1),(a+N,a+N+1,a+N+ny+1,a+N+ny)]
    for i in [0,ny-1]:
        a,b = j*ny+i,(j+1)*ny+i
        faces.append((a,a+N,b+N,b))
for j in [0,len(deck_x)-1]:
    for i in range(ny-1):
        a = j*ny+i
        faces.append((a,a+1,a+1+N,a+N))
mesh('Cambered_main_deck',verts,faces,deckwood)
for y in np.arange(-5.45,5.5,.36):
    path = [(float(x),float(y),7.815+sheer(x)) for x in np.linspace(-26.5,24.9,180)
            if abs(y)<width(x,7.8)-.25]
    if len(path)>1:
        rope('Longitudinal_deck_seam',path,.009,recess)
for i,y in enumerate(np.arange(-5.1,5.2,.36)):
    for x in np.arange(-22+(i%3)*1.4,24,4.2):
        if abs(y)+.18<width(x,7.8)-.3:
            rope('Deck_plank_joint',[(x,y-.17,7.82+sheer(x)),(x,y+.17,7.82+sheer(x))],.009,recess)
for side in [-1,1]:
    rail_path('Main_deck_rail',[hull_point(float(x),7.87,side,.14)
                              for x in np.linspace(-26,24.8,45)])
platform('Forecastle',-25,-16,3.6,10.1)
for side in [-1,1]:
    rail_path('Forecastle_rail',[(float(x),side*min(3.5,width(x,7.8)-.22),10.1)
                                for x in np.linspace(-24.8,-16.1,10)])

current = '04_Artillery'
def barrel_mesh():
    profile = [(0,.13),(.13,.23),(.35,.28),(.58,.28),(.65,.245),
               (1.4,.22),(2.1,.19),(2.32,.25),(2.48,.25),(2.48,.155),(1.92,.155)]
    n = 24
    verts = [(r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n),z) for z,r in profile for i in range(n)]
    faces = [tuple(reversed(range(n)))]
    for j in range(len(profile)-1):
        faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for i in range(n)]
    faces += [tuple(range((len(profile)-1)*n,len(profile)*n))]
    return mesh('Cannon_barrel_master',verts,faces,iron,smooth=True)

barrel_master = barrel_mesh()
for side in [-1,1]:
    for tier,(lo,hi) in enumerate(port_levels):
        level = (lo+hi)/2
        for index,x in enumerate(gun_x):
            w,z = width(x,level),level+sheer(x)
            for dx in [-.86,.86]:
                beam('Gunport_side_frame',hull_point(x+dx,lo-.06,side,-.09),
                     hull_point(x+dx,hi+.06,side,-.09),.15,wood[1])
            for h in [lo-.03,hi+.03]:
                beam('Gunport_lintel',hull_point(x-.88,h,side,-.10),
                     hull_point(x+.88,h,side,-.10),.16,wood[1])
            lid = box('Raised_gunport_lid',(1.55,.12,1.33),
                      (x,side*(width(x,hi)+.53),hi+sheer(x)+.40),wood[2],
                      rot=(-side*math.radians(65),0,0))
            for dx in [-.49,.49]:
                beam('Gunport_hinge',(x+dx,side*(width(x,hi)+.05),hi+sheer(x)),
                     (x+dx,side*(width(x,hi)+.30),hi+sheer(x)+.18),.085,iron)
            o = barrel_master.copy()
            o.name = f'Cannon_{"port" if side<0 else "starboard"}_{tier+1}_{index+1:02}'
            groups[current].objects.link(o)
            o.location = (x,side*(w-1.55),z)
            o.rotation_euler = Vector((0,side,.025)).to_track_quat('Z','Y').to_euler()
            box('Cannon_carriage',(1.05,1.5,.28),(x,side*(w-1.0),z-.34),wood[1])
            for dx in [-.45,.45]:
                for dy in [-.47,.47]:
                    a=(x+dx,side*(w-1.0)+dy,z-.52)
                    cylinder('Carriage_wheel',Vector(a)-Vector((.09,0,0)),
                             Vector(a)+Vector((.09,0,0)),.20,wood[1],n=12)
bpy.data.objects.remove(barrel_master,do_unlink=True)
log('curved hull, 48 open gunports and bored cannons complete')

current = '03_Sterncastle'
box('Lower_captains_cabin',(10.5,8.7,3.5),(20,0,10.5),wood[0],.08)
box('Upper_captains_cabin',(6.8,8.0,2.65),(22.3,0,13.7),wood[2],.07)
platform('Quarterdeck',13.2,26,5.1,12.32)
platform('Poop_deck',18.8,26.3,4.65,15.15)
rectangular_rail('Quarterdeck_gallery',13.3,26,5.0,12.32,False)
rectangular_rail('Poop_deck_gallery',18.9,26.2,4.55,15.15,False)
for side in [-1,1]:
    for z,x0,x1,w in [(9.1,14.8,25.3,4.48),(12.0,14.8,25.3,4.48),
                       (12.65,18.9,25.8,4.13),(14.9,18.9,25.8,4.13)]:
        beam('Cabin_bronze_cornice',(x0,side*w,z),(x1,side*w,z),.11,brass)
    for x in np.arange(15,26,1.75):
        beam('Cabin_carved_pilaster',(x,side*4.45,9.1),(x,side*4.45,12.1),.17,wood[1])
        beam('Pilaster_bronze_inlay',(x,side*4.55,9.3),(x,side*4.55,11.9),.04,brass)
    for x in [19.2,21.0,22.8,24.6,25.5]:
        beam('Upper_pilaster',(x,side*4.12,12.65),(x,side*4.12,14.95),.14,brass)


def gothic_window(name, center, horizontal, normal, w=1.1, h=1.7):
    c, H, N = Vector(center),Vector(horizontal),Vector(normal)
    outline = [(-w/2,-h/2),(w/2,-h/2),(w/2,h*.16),
               (w*.35,h*.34),(0,h*.54),(-w*.35,h*.34),(-w/2,h*.16)]
    front = [c+H*u+Vector((0,0,v))+N*.025 for u,v in outline]
    back = [p-N*.08 for p in front]
    strip_solid(name,front,back,windowmat)
    rope(name+'_gothic_surround',front,.065,brass,True)
    beam(name+'_center_mullion',c+Vector((0,0,-h/2))+N*.09,
         c+Vector((0,0,h*.50))+N*.09,.045,brass)
    beam(name+'_transom',c-H*w*.48+N*.09,c+H*w*.48+N*.09,.045,brass)
    for v in [-.32,.32]:
        beam(name+'_diamond',c-H*w*.44+Vector((0,0,v-h*.17))+N*.10,
             c+H*w*.44+Vector((0,0,v+h*.17))+N*.10,.019,brass)


for side in [-1,1]:
    for x in [15.9,17.65,19.4,21.15,22.9,24.6]:
        gothic_window('Lower_gallery_window',(x,side*4.39,10.65),(1,0,0),(0,side,0),1.2,1.85)
    for x in [20.0,21.85,23.7]:
        gothic_window('Upper_gallery_window',(x,side*4.05,13.65),(1,0,0),(0,side,0),1.25,1.75)
for z,x,w in [(10.65,25.31,1.3),(13.65,25.72,1.25)]:
    for y in [-2.8,-1.4,0,1.4,2.8]:
        gothic_window('Stern_transom_window',(x,y,z),(0,1,0),(1,0,0),w,1.75)
for x,z in [(14.68,10.3),(18.83,13.5)]:
    box('Cabin_door',(.10,1.15,2.1),(x,0,z),wood[1],.035)
    for y in [-.61,.61]:
        beam('Door_jamb',(x-.05,y,z-1.1),(x-.05,y,z+1.2),.13,brass)
    ring('Door_ring_handle',(x-.13,.36,z),.10,.025,brass,'X',20)


def stairs(name, a, b, y, w=1.25, count=10):
    x0,z0=a
    x1,z1=b
    for i in range(count):
        t=(i+.5)/count
        box(name+'_tread',((x1-x0)/count+.08,w,.12),
            (x0+(x1-x0)*t,y,z0+(z1-z0)*(i+1)/count),deckwood)
    for side in [-1,1]:
        beam(name+'_stringer',(x0,y+side*w*.45,z0-.15),(x1,y+side*w*.45,z1-.15),.18,wood[0])
        beam(name+'_handrail',(x0,y+side*w*.5,z0+.9),(x1,y+side*w*.5,z1+.9),.09,wood[1])
        for t in [0,.5,1]:
            x,z=x0+(x1-x0)*t,z0+(z1-z0)*t
            beam(name+'_post',(x,y+side*w*.5,z),(x,y+side*w*.5,z+.9),.10,wood[0])


for y in [-3.45,3.45]:
    stairs('Quarterdeck_stairs',(9.2,8.15),(13.8,12.32),y,count=13)
    stairs('Poop_stairs',(15.8,12.32),(19.6,15.15),y,count=10)
stairs('Forecastle_stairs',(-12.8,8.05),(-16.5,10.1),0,count=8)
log('stepped stern galleries, windows, deck access complete')

current = '05_Masts'
masts = [(-13,39,25.8,.53),(1.5,44,29.8,.65),(17,32,23,.43)]
for index,(x,top,collar,r) in enumerate(masts):
    foot = 7.8+sheer(x) if x<13 else 12.32
    cylinder(f'Mast_{index+1}_lower',(x,0,foot),(x,0,collar+1),r,mastwood,top=r*.67,n=24)
    cylinder(f'Mast_{index+1}_top',(x,0,collar-.8),(x,0,top),r*.55,mastwood,top=.12,n=20)
    for z in np.arange(foot+.6,collar,2.3):
        ring('Mast_iron_binding',(x,0,z),r*(1-.30*(z-foot)/(collar+1-foot))+.025,.055,iron)
    cylinder('Mast_partner',(x,0,foot),(x,0,foot+.3),r*1.65,wood[1],n=20)
    cylinder('Fighting_top_bowl',(x,0,collar-.4),(x,0,collar),r*1.5,wood[0],top=r*2.8,n=24)
    cylinder('Fighting_top_floor',(x,0,collar),(x,0,collar+.13),r*3.0,deckwood,n=24)
    ring('Fighting_top_rail',(x,0,collar+1),r*3,.065,wood[1])
    for a in np.linspace(0,math.tau,16,endpoint=False):
        p=Vector((x+r*3*math.cos(a),r*3*math.sin(a),collar+.13))
        beam('Fighting_top_post',p,p+Vector((0,0,.87)),.075,wood[1])
    sphere('Mast_finial',(x,0,top+.2),(.17,.17,.23),brass)
cylinder('Bowsprit',(-22,0,9.1),(-38,0,14.0),.43,mastwood,top=.17,n=20)
cylinder('Bowsprit_jibboom',(-34.5,0,13.0),(-42,0,15.9),.20,mastwood,top=.075,n=16)
for t in np.linspace(.1,.88,9):
    p=Vector((-22,0,9.1)).lerp(Vector((-38,0,14.0)),float(t))
    ring('Bowsprit_binding',p,.37*(1-t)+.17*t,.035,iron,'X',24)

span = Vector((.54,-.842,0))
wind = Vector((-.842,-.54,0))


def sail_point(x,top,bottom,halfwidth,u,v):
    width_here=halfwidth*(1.04-.08*v)
    billow=2.0*(halfwidth/8)*math.sin(math.pi*u)**.8*math.sin(math.pi*v)**.7
    z=bottom+(top-bottom)*v+1.15*math.sin(math.pi*u)*(1-v)**5
    z += .10*(math.sin(u*math.pi*23)+.45*math.sin(u*math.pi*47))*(1-v)**10
    p=Vector((x,0,z))+span*((2*u-1)*width_here)+wind*(.22+billow)
    p += wind*(.045*math.sin(u*math.pi*38)*math.sin(v*math.pi))
    return p


def square_sail(name,x,top,bottom,halfwidth):
    global current
    current='06_Sails'
    nu,nv=36,26
    points=[sail_point(x,top,bottom,halfwidth,i/nu,j/nv)
            for j in range(nv+1) for i in range(nu+1)]
    faces=[]
    for j in range(nv):
        for i in range(nu):
            # Small wear holes near the lower hem; solidify also closes their rims.
            if (i,j) in {(3,1),(4,1),(30,2),(31,2),(32,2),(9,3)}:
                continue
            a=j*(nu+1)+i
            faces.append((a,a+1,a+nu+2,a+nu+1))
    o=mesh(name,points,faces,cloth,smooth=True)
    uv=o.data.uv_layers.active
    for poly in o.data.polygons:
        for li in poly.loop_indices:
            k=o.data.loops[li].vertex_index
            uv.data[li].uv=(k%(nu+1)/nu,k//(nu+1)/nv)
    m=o.modifiers.new('Canvas thickness', 'SOLIDIFY')
    m.thickness=.028
    m.offset=0
    for u in np.linspace(0,1,17):
        rope(name+'_vertical_seam',[sail_point(x,top,bottom,halfwidth,float(u),float(v))+wind*.022
                                   for v in np.linspace(.01,.99,30)],.012,stitchmat)
    for v in [.035,.25,.55,.96]:
        rope(name+'_horizontal_seam',[sail_point(x,top,bottom,halfwidth,float(u),v)+wind*.024
                                     for u in np.linspace(0,1,45)],.014,stitchmat)
    for u in [0,1]:
        rope(name+'_boltrope',[sail_point(x,top,bottom,halfwidth,u,float(v)) for v in np.linspace(0,1,40)],
             .042,rope_mat)
    for v in [0,1]:
        rope(name+'_hem',[sail_point(x,top,bottom,halfwidth,float(u),v) for u in np.linspace(0,1,55)],
             .035,rope_mat)
    # Sewn repair patches use the same curved surface, slightly offset.
    for u0,v0,du,dv in [(.17,.13,.08,.12),(.72,.32,.07,.14),(.40,.62,.055,.09)]:
        pv=[sail_point(x,top,bottom,halfwidth,u0+i*du/4,v0+j*dv/4)+wind*.042
            for j in range(5) for i in range(5)]
        pf=[(j*5+i,j*5+i+1,j*5+i+6,j*5+i+5) for j in range(4) for i in range(4)]
        patch=mesh(name+'_repair_patch',pv,pf,patchmat,smooth=True)
        mod=patch.modifiers.new('Patch thickness','SOLIDIFY')
        mod.thickness=.012
        for u in [u0,u0+du]:
            rope('Patch_stitch',[sail_point(x,top,bottom,halfwidth,u,float(v))+wind*.054
                                 for v in np.linspace(v0,v0+dv,10)],.009,stitchmat)
    current='05_Masts'
    middle=Vector((x,0,top+.14))
    cylinder(name+'_yard',middle-span*(halfwidth+1),middle+span*(halfwidth+1),
             .19 if halfwidth>7 else .13,mastwood,n=16)
    current='07_Rigging'
    for sign in [-1,1]:
        tip=middle+span*sign*(halfwidth+.7)
        mast_top=next(m[1] for m in masts if m[0]==x)
        sag('Yard_lift',tip,(x,0,min(top+3.1,mast_top-.3)),.12,.035)
        corner=sail_point(x,top,bottom,halfwidth,0 if sign<0 else 1,0)
        sag('Sail_sheet',corner,(min(x+5,23),-sign*min(5,width(x,7)),8.6+sheer(x)),.3,.045)
    for u in np.linspace(.08,.92,11):
        p=sail_point(x,top,bottom,halfwidth,float(u),.25)+wind*.06
        sag('Reef_point',p,p+Vector((.07,.03,-.55)),.035,.012)


for args in [('Fore_course',-13,25.0,13.2,8.4),('Fore_topsail',-13,33.8,27.5,6.3),
             ('Fore_topgallant',-13,37.5,35.0,4.4),
             ('Main_course',1.5,29.0,14.1,10.0),('Main_topsail',1.5,38.0,31.6,7.3),
             ('Main_topgallant',1.5,42.4,39.4,5.0)]:
    square_sail(*args)


def triangle_sail(name,a,b,c,bulge=2.0):
    global current
    current='06_Sails'
    a,b,c=Vector(a),Vector(b),Vector(c)
    n=24
    vertices,lookup,uvs=[],{},[]
    def at(u,v):
        return a*(1-u-v)+b*u+c*v+Vector((0,-bulge*27*u*v*(1-u-v),0))
    for i in range(n+1):
        for j in range(n+1-i):
            lookup[i,j]=len(vertices)
            vertices.append(at(i/n,j/n))
            uvs.append((i/n,j/n))
    faces=[]
    for i in range(n):
        for j in range(n-i):
            faces.append((lookup[i,j],lookup[i+1,j],lookup[i,j+1]))
            if j<n-i-1:
                faces.append((lookup[i+1,j],lookup[i+1,j+1],lookup[i,j+1]))
    o=mesh(name,vertices,faces,cloth,smooth=True)
    for p in o.data.polygons:
        for li in p.loop_indices:
            o.data.uv_layers.active.data[li].uv=uvs[o.data.loops[li].vertex_index]
    m=o.modifiers.new('Canvas thickness','SOLIDIFY')
    m.thickness=.026
    rope(name+'_hem',[a,b,c],.045,rope_mat,True)
    for u in np.linspace(.08,.9,13):
        rope(name+'_seam',[at(float(u),float(v))+Vector((0,-.025,0))
                          for v in np.linspace(.005,1-u-.005,28)],.012,stitchmat)
    current='07_Rigging'
    return o


triangle_sail('Mizzen_lateen',(15.5,.2,30.6),(28,.2,17.6),(16.5,.2,16.2),2.1)
current='05_Masts'
cylinder('Mizzen_lateen_yard',(14.7,.4,31.5),(28.8,.4,16.7),.16,mastwood,top=.11,n=16)
triangle_sail('Flying_jib',(-40,0,16),(-13,0,34),(-23,0,17),1.5)
triangle_sail('Inner_staysail',(-31,0,13.1),(-13,0,24),(-15,0,12.8),1.7)

current='07_Rigging'
for x,top,collar,r in masts:
    for side in [-1,1]:
        basez=8.05+sheer(x) if x<13 else 12.45
        w=min(width(x,7.8)+.10,5.6)
        tops=[]
        bases=[]
        for dx in np.linspace(-2.8,2.8,6):
            foot=Vector((x+dx,side*w,basez))
            head=Vector((x+dx*.055,side*.42,collar+.2))
            bases.append(foot)
            tops.append(head)
            rope('Standing_shroud',[foot,head],.047,rope_mat)
            cylinder('Chainplate',foot-Vector((0,0,1.65)),foot,.055,iron,n=8)
            ring('Deadeye',foot+Vector((0,0,.18)),.17,.055,wood[1],'Y',20)
        for t in np.arange(.035,.90,.035):
            rope('Ratline_ladder',[bases[0].lerp(tops[0],float(t)),bases[-1].lerp(tops[-1],float(t))],
                 .023,rope_mat)
        sag('Topmast_backstay',(x,0,top-.7),(min(x+8,25),side*w,basez),.25,.042)
    sag('Mast_fore_stay',(x,0,top-1),(-40,0,15.6) if x<0 else (x-16,0,12),.20,.065)
    sag('Lower_fore_stay',(x,0,collar),(-28,0,10) if x<0 else (x-13,0,10),.1,.055)
sag('Bobstay',(-40,0,15.6),(-26,0,1.6),.15,.09)
for side in [-1,1]:
    sag('Bowsprit_side_stay',(-38,0,14),(-22,side*4.2,8.4),.18,.055)
    sag('Bowsprit_safety_net_edge',(-35,side*1.1,13),(-23,side*2.0,9.3),.6,.05)

current='06_Sails'
for x,top,_,_ in masts:
    nu,nv=22,6
    verts=[]
    for j in range(nv+1):
        for i in range(nu+1):
            u,v=i/nu,j/nv
            end=.25*math.sin(v*math.pi*5)*u**8
            verts.append((x-4.2*u+end,.35*math.sin(u*math.tau*1.25)*u,
                          top-.15-1.1*v-.28*u))
    faces=[(j*(nu+1)+i,j*(nu+1)+i+1,(j+1)*(nu+1)+i+1,(j+1)*(nu+1)+i)
           for j in range(nv) for i in range(nu)]
    flag=mesh('Tattered_black_pennant',verts,faces,cloth,smooth=True)
    flag.modifiers.new('Flag thickness','SOLIDIFY').thickness=.015
log('three masts, nine billowing sails, repairs and standing rigging complete')

current='08_Ornament'
# Sculpted replacement for the approved dark-fantasy figurehead.
import sys
sys.path.insert(0, str(Path(__file__).parent))
from black_oath_skull_v5 import build_skull
from black_oath_skull_adornments_v5 import build_adornments
build_skull(groups[current],center=(-29.2,0,9.465))
build_adornments(groups[current])
for side in [-1,1]:
    # Scrollwork follows the curved ship skin rather than floating on a flat card.
    for cx,cz,radius in [(-24,8.15,1.15),(-21,7.25,.8),(-17.2,7.55,.65),
                         (15.8,8.2,.7),(20.5,8.3,.9),(23,8.7,.7)]:
        points=[]
        for t in np.linspace(0,math.tau*1.5,70):
            r=radius*(1-t/(math.tau*1.75))
            x=cx+r*math.cos(t)
            z=cz+r*.6*math.sin(t)
            points.append(hull_point(x,z,side,-.16))
        rope('Bronze_acanthus_scroll',points,.045,brass)
    rope('Figurehead_sweeping_support',
         [(-29,side*.8,9.6),(-26,side*1.9,9.4),(-24,side*3.1,9.4),
          (-21,side*4.1,9.0),(-18,side*4.8,8.4)],.11,brass)
    for x in np.arange(-19,23,3.8):
        p=Vector(hull_point(float(x),7.55,side,-.12))
        ring('Broadside_medallion',p,.19,.028,brass,'Y',24)
        sphere('Medallion_center',p,(.10,.055,.10),brass)
    for x in np.arange(15.5,25.2,1.8):
        rope('Gallery_arch_decoration',[(x-.5,side*4.58,11.9),(x,side*4.65,12.25),
                                        (x+.5,side*4.58,11.9)],.042,brass)

box('Stern_name_board',(.14,4.6,.62),(26.08,0,12.18),wood[2])
font=bpy.data.curves.new('Stern_lettering','FONT')
font.body='BLACK OATH'
font.align_x='CENTER'
font.size=.38
font.extrude=.012
font.bevel_depth=.003
font.materials.append(brass)
obj=bpy.data.objects.new('BLACK OATH',font)
groups[current].objects.link(obj)
obj.location=(26.17,0,12.02)
obj.rotation_euler=(math.pi/2,0,math.pi/2)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active=obj
bpy.ops.object.convert(target='MESH')
uv_project(obj.data)
obj.modifiers.new('Weld letter cap vertices','WELD').merge_threshold=.00001


def lantern(loc,scale=1):
    x,y,z=loc
    cylinder('Lantern_base',(x,y,z),(x,y,z+.12*scale),.29*scale,brass,n=8)
    box('Lantern_amber_glass',(.34*scale,.34*scale,.66*scale),
        (x,y,z+.46*scale),amber,.035)
    for dx in [-.21,.21]:
        for dy in [-.21,.21]:
            beam('Lantern_cage',(x+dx*scale,y+dy*scale,z+.1*scale),
                 (x+dx*scale,y+dy*scale,z+.83*scale),.045*scale,iron)
    cylinder('Lantern_roof',(x,y,z+.84*scale),(x,y,z+1.13*scale),.36*scale,brass,top=.025,n=8)
    sphere('Lantern_finial',(x,y,z+1.18*scale),(.07*scale,.07*scale,.1*scale),brass)
    data=bpy.data.lights.new('Warm_lantern_light','POINT')
    data.energy=65*scale
    data.color=(1,.36,.11)
    data.shadow_soft_size=.3
    o=bpy.data.objects.new(data.name,data)
    groups['90_Presentation'].objects.link(o)
    o.location=(x,y,z+.55*scale)


for y in [-4.4,-2.2,0,2.2,4.4]:
    lantern((25.9,y,16.3),1.05 if abs(y)>3 else .85)
for x,z,w in [(-24,11.18,3.4),(14,13.42,4.9)]:
    if x<0:
        w=min(w,width(x,7.8)-.22)
    for side in [-1,1]:
        lantern((x,side*w,z),.7)

current='09_Deck_Equipment'
for side in [-1,1]:
    # Anchors hang from catheads with curved arms and broad flukes.
    a=Vector((-21,side*5.0,4.4))
    cylinder('Anchor_shank',a,a+Vector((0,0,3.0)),.12,iron,n=12)
    beam('Anchor_stock',a+Vector((-1.25,0,2.2)),a+Vector((1.25,0,2.2)),.24,wood[1])
    ring('Anchor_ring',a+Vector((0,0,3.35)),.28,.07,iron,'Y',28)
    for sign in [-1,1]:
        path=[a+Vector((0,0,0)),a+Vector((sign*.65,0,-.15)),
              a+Vector((sign*1.15,0,.2)),a+Vector((sign*1.4,0,.75))]
        rope('Anchor_arm',path,.12,iron)
        p=path[-1]
        mesh('Anchor_fluke',[p+Vector((-.32,-.20,-.2)),p+Vector((.32,-.20,-.2)),
                            p+Vector((0,-.20,.42)),p+Vector((-.32,.20,-.2)),
                            p+Vector((.32,.20,-.2)),p+Vector((0,.20,.42))],
             [(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],iron)
    beam('Cathead',(-21,side*3.3,10),(-21,side*6,10.6),.25,wood[0])
    sag('Anchor_fall',a+Vector((0,0,3.5)),(-21,side*6,10.6),.15,.10)


def capstan(x,y,z):
    cylinder('Capstan_base',(x,y,z),(x,y,z+.20),.85,wood[0],n=20)
    cylinder('Capstan_drum',(x,y,z+.18),(x,y,z+1.1),.39,wood[1],top=.48,n=16)
    cylinder('Capstan_cap',(x,y,z+1.1),(x,y,z+1.25),.61,iron,n=20)
    for a in np.linspace(0,math.tau,8,endpoint=False):
        beam('Capstan_bar',(x+.3*math.cos(a),y+.3*math.sin(a),z+1.0),
             (x+1.55*math.cos(a),y+1.55*math.sin(a),z+1.0),.10,mastwood)
    for h in np.arange(.35,.9,.085):
        ring('Capstan_rope_wrap',(x,y,z+h),.43,.035,rope_mat)


capstan(-20,0,10.1)
capstan(6,0,8.0)
# Wheel faces forward, with separate spokes, handles and a sturdy pedestal.
box('Helm_pedestal',(.48,.65,1.2),(15.6,0,12.92),wood[1])
wheel=Vector((15.25,0,13.85))
ring('Helm_wheel',wheel,.84,.075,wood[1],'X',48)
cylinder('Helm_hub',wheel-Vector((.18,0,0)),wheel+Vector((.18,0,0)),.19,brass,n=16)
for a in np.linspace(0,math.tau,10,endpoint=False):
    p=wheel+Vector((0,math.cos(a),math.sin(a)))
    cylinder('Helm_spoke',wheel,p,.045,mastwood,n=10)
    sphere('Helm_handle',p,(.065,.065,.10),wood[1])


def barrel(loc):
    x,y,z=loc
    n=18
    profile=[(0,.36),(.1,.40),(.55,.48),(1.0,.40),(1.1,.36)]
    verts=[(x+r*math.cos(a),y+r*math.sin(a),z+h)
           for h,r in profile for a in np.linspace(0,math.tau,n,endpoint=False)]
    faces=[tuple(reversed(range(n))),tuple(range((len(profile)-1)*n,len(profile)*n))]
    faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i)
              for j in range(len(profile)-1) for i in range(n)]
    mesh('Deck_barrel',verts,faces,wood[1])
    for h,r in [(.13,.414),(.32,.454),(.78,.454),(.98,.414)]:
        ring('Barrel_hoop',(x,y,z+h),r,.035,iron,'Z',32)
    for a in np.linspace(0,math.tau,n,endpoint=False):
        rope('Barrel_stave_joint',[(x+(r+.006)*math.cos(a),y+(r+.006)*math.sin(a),z+h)
                                   for h,r in profile],.007,recess)


for x,y in [(8,2.7),(8.9,2.9),(8.4,3.8),(-10,3.4),(-9,3.55),(-18,-2.3)]:
    barrel((x,y,10.1 if x<-16 else 7.8+sheer(x)))
for x,y in [(-9,-3.3),(8,-3.0)]:
    z=7.8+sheer(x)
    box('Supply_chest',(1.5,.9,.8),(x,y,z+.4),wood[1])
    for dx in [-.5,.5]:
        box('Chest_iron_band',(.085,.94,.84),(x+dx,y,z+.42),iron,.008)
for x,y in [(-7,-2.4),(3,-2.5)]:
    z=7.85+sheer(x)
    box('Hatch_dark_well',(2.3,1.4,.10),(x,y,z),recess)
    for dx in np.arange(-1.1,1.15,.22):
        beam('Hatch_grating',(x+dx,y-.7,z+.09),(x+dx,y+.7,z+.09),.07,wood[1])
    for dy in np.arange(-.7,.75,.23):
        beam('Hatch_grating',(x-1.15,y+dy,z+.13),(x+1.15,y+dy,z+.13),.07,wood[1])
    for dy in [-.77,.77]:
        beam('Hatch_frame',(x-1.2,y+dy,z+.12),(x+1.2,y+dy,z+.12),.14,wood[0])
for x,_,_,_ in masts:
    z=7.8+sheer(x) if x<13 else 12.32
    for side in [-1,1]:
        beam('Belaying_rail',(x-.9,side*1.5,z+.85),(x+.9,side*1.5,z+.85),.18,wood[1])
        for dx in [-.8,.8]:
            beam('Belaying_rail_leg',(x+dx,side*1.5,z),(x+dx,side*1.5,z+.85),.16,wood[0])
        for dx in np.linspace(-.65,.65,5):
            cylinder('Belaying_pin',(x+dx,side*1.5,z+.6),(x+dx,side*1.5,z+1.08),.045,mastwood,n=8)
        for dx in [-.5,.5]:
            points=[]
            for t in np.linspace(0,math.tau*3.5,100):
                r=.19+.009*t
                points.append((x+dx+r*math.cos(t),side*2.15+r*.65*math.sin(t),z+.055+t*.001))
            rope('Coiled_running_rope',points,.035,rope_mat)
# A small open ship's boat sits on cradles amidships.
boat_center=Vector((-5,1.45,8.45))
verts=[]
for k in range(17):
    t=k/16
    x=-2.7+5.4*t
    w=.12+.86*math.sin(math.pi*t)**.7
    for i in range(13):
        a=i/12*math.pi
        verts.append(boat_center+Vector((x,w*math.cos(a),-.62*math.sin(a))))
faces=[(k*13+i,k*13+i+1,(k+1)*13+i+1,(k+1)*13+i) for k in range(16) for i in range(12)]
boat=mesh('Open_ships_boat',verts,faces,wood[1])
boat.modifiers.new('Boat plank thickness','SOLIDIFY').thickness=.09
for x in [-6.6,-5,-3.4]:
    box('Boat_thwart',( .25,1.5,.10),(x,1.45,8.39),deckwood)
    box('Boat_cradle',(.22,2.1,.28),(x,1.45,7.99),wood[0])
for side in [-1,1]:
    rope('Boat_gunwale',[boat_center+Vector((-2.7+5.4*t,side*(.12+.86*math.sin(math.pi*t)**.7),.03))
                         for t in np.linspace(0,1,50)],.06,wood[1])
log('carved skull, scrollwork, anchors, helm and deck equipment complete')

current='90_Presentation'
water=material('Presentation_sea',(.018,.043,.058),.23,.30)
pn=water.node_tree.nodes.get('Principled BSDF')
pn.inputs['IOR'].default_value=1.333
pn.inputs['Transmission Weight'].default_value=.10
noise=water.node_tree.nodes.new('ShaderNodeTexNoise')
noise.inputs['Scale'].default_value=1.4
noise.inputs['Detail'].default_value=3
geometry=water.node_tree.nodes.new('ShaderNodeNewGeometry')
water.node_tree.links.new(geometry.outputs['Position'],noise.inputs['Vector'])
bump=water.node_tree.nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value=.35
bump.inputs['Distance'].default_value=.18
water.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height'])
water.node_tree.links.new(bump.outputs['Normal'],pn.inputs['Normal'])
n=181
coords=np.linspace(-160,160,n)
verts=[]
for y in coords:
    for x in coords:
        z=-.75+.22*math.sin(x*.32+y*.16)+.14*math.sin(y*.7-x*.12)+.08*math.cos(x*1.6+y*.3)
        verts.append((float(x),float(y),float(z)))
faces=[(j*n+i,j*n+i+1,(j+1)*n+i+1,(j+1)*n+i) for j in range(n-1) for i in range(n-1)]
mesh('Presentation_sea_waves',verts,faces,water,smooth=True)
box('Presentation_far_sea',(10000,10000,.1),(0,0,-.85),water,0)
foam=material('Presentation_foam',(.58,.64,.66),.75)
for side in [-1,1]:
    for i,x in enumerate(np.linspace(-26,25,38)):
        w=width(x)*(.86 if abs(x)>20 else .99)
        points=[(float(x+t),side*(w+.12*math.sin(t*5+i)), -.48+.06*math.sin(t*7+i))
                for t in np.linspace(-.35,.4,9)]
        # Small foamy fragments remain optional presentation geometry.
        o=rope('Presentation_broken_foam',points,.035+(i%3)*.012,foam)
        o.hide_render=True
        o.hide_set(True)

scene.render.engine='CYCLES'
scene.cycles.samples=64
scene.cycles.use_denoising=True
scene.cycles.adaptive_threshold=.035
scene.cycles.max_bounces=8
scene.cycles.transmission_bounces=4
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX'
    prefs.get_devices()
    for d in prefs.devices:
        d.use=d.type!='CPU'
    if any(d.use for d in prefs.devices):
        scene.cycles.device='GPU'
except (RuntimeError,TypeError):
    pass
scene.render.resolution_x=1800
scene.render.resolution_y=1300
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure=.35
scene.world.use_nodes=True
wn=scene.world.node_tree.nodes
wl=scene.world.node_tree.links
bg=wn.get('Background')
bg.inputs['Strength'].default_value=.5
tex=wn.new('ShaderNodeTexNoise')
tex.inputs['Scale'].default_value=3.2
tex.inputs['Detail'].default_value=3.0
coord=wn.new('ShaderNodeTexCoord')
wl.new(coord.outputs['Normal'],tex.inputs['Vector'])
ramp=wn.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position=.25
ramp.color_ramp.elements[0].color=(.11,.15,.20,1)
ramp.color_ramp.elements[1].position=.72
ramp.color_ramp.elements[1].color=(.52,.57,.63,1)
wl.new(tex.outputs['Fac'],ramp.inputs['Fac'])
wl.new(ramp.outputs['Color'],bg.inputs['Color'])


def area(name,loc,energy,size,color):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=energy
    data.shape='DISK'
    data.size=size
    data.color=color
    o=bpy.data.objects.new(name,data)
    groups['90_Presentation'].objects.link(o)
    o.location=loc
    o.rotation_euler=(Vector((0,0,12))-o.location).to_track_quat('-Z','Y').to_euler()


area('Cold_soft_key',(-30,-45,60),90000,55,(.79,.88,1))
area('Warm_stern_rim',(30,30,48),100000,42,(1,.72,.44))
area('Broad_front_fill',(-60,25,28),45000,42,(.75,.84,1))
data=bpy.data.lights.new('Low_overcast_sun','SUN')
data.energy=1.3
data.angle=math.radians(18)
sun=bpy.data.objects.new(data.name,data)
groups[current].objects.link(sun)
sun.rotation_euler=(math.radians(22),math.radians(-30),math.radians(-25))
data=bpy.data.cameras.new('Ship_camera')
camera=bpy.data.objects.new('Camera_Hero',data)
groups[current].objects.link(camera)
scene.camera=camera
camera.location=(-70,-105,40)
camera.rotation_euler=(Vector((-4,0,19.5))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.lens=52
camera.data.clip_end=20000
scene.render.filepath=str(OUT/'hero.png')
scene['asset']='BLACK OATH / 검은 맹세'
scene['reference']='Concepts/01_dark_fantasy.png'
scene['scope']='Static editable exterior and exposed decks; 48 guns, three masts, nine sails.'
scene['materials_note']='Packed base-color maps; Blender micro-bump is not baked into GLB.'
scene['presentation_note']='Collection 90_Presentation contains sea, foam, camera and lighting; excluded from GLB.'
for screen in bpy.data.screens:
    for ar in screen.areas:
        if ar.type=='VIEW_3D':
            ar.spaces.active.clip_end=20000
            ar.spaces.active.region_3d.view_perspective='CAMERA'
bpy.ops.object.select_all(action='DESELECT')
bpy.context.view_layer.update()
credit=(OUT/'SOURCE_LICENSE.txt').read_text(encoding='utf-8')
credit_text=bpy.data.texts.get('SOURCE_LICENSE.txt') or bpy.data.texts.new('SOURCE_LICENSE.txt')
credit_text.clear()
credit_text.write(credit)
scene['asset_attribution']=credit
scene['figurehead_revision']='v05 / rebuilt from licensed anatomical skull base'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BlackOath.blend'))
log('editable Blender source saved')

# Freeze evaluated geometry into one portable mesh per logical collection.
# Source curves, bevels, individual components and UVs remain editable in the blend.
import sys
sys.path.insert(0, str(Path(__file__).parent))
from black_oath_export import export_ship
triangle_count = export_ship(scene, groups, OUT)
manifest={'name':'Black Oath','hull_length_m':52,'masts':3,'sails':9,'cannons':48,
          'evaluated_triangles':triangle_count,'collections':list(groups),
          'source':'BlackOath.blend','export':'BlackOath.glb','reference':'Concepts/01_dark_fantasy.png',
          'figurehead_revision':'v05','figurehead_reference':'Concepts/skull_reference_v03.png',
          'figurehead_source':'Source/Skull_v05/selected_source.json',
          'figurehead_center_m':[-29.2,0,9.465],
          'figurehead_license':'CC BY 4.0; see SOURCE_LICENSE.txt'}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
log('BUILD_OK; triangles='+str(triangle_count))
