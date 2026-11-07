"""Reference-led Greninja sculpture. Front -Y, Z up; isolated from earlier assets.

Blender --background --factory-startup --python popular_greninja.py -- --draft
Use --render-only to render the saved source, --full for all review views.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import pokemon_common as c
from popular_painting import paint_front, ellipse

OUT = ROOT / 'assets' / 'PokemonPopular' / 'Greninja'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'renders').mkdir(exist_ok=True)
BLUE = '24478F'
NAVY = '1E3978'
CYAN = '3BB2D2'
CREAM = 'F5EDAC'
PINK = 'EA839E'
PAD = '6577AD'
WHITE = 'F7FAF5'
INK = '152449'


def args():
    p = argparse.ArgumentParser()
    p.add_argument('--draft', action='store_true')
    p.add_argument('--full', action='store_true')
    p.add_argument('--render-only', action='store_true')
    p.add_argument('--gpu', action='store_true')
    p.add_argument('--view', default='preview')
    return p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


def smooth_mesh(name, verts, faces, color, bevel=0):
    obj = c.mesh(name, verts, faces, color)
    if bevel:
        m = obj.modifiers.new('Soft sculpted edges', 'BEVEL')
        m.width = bevel
        m.segments = 3
        c.apply(obj, m)
    return obj


def plate(name, outline, thickness, color, bevel=.018, front_color=None):
    """Closed extrusion with an arbitrary three-dimensional outline."""
    n = len(outline)
    verts = [(x, y-thickness/2, z) for x, y, z in outline]
    verts += [(x, y+thickness/2, z) for x, y, z in outline]
    faces = [tuple(range(n-1, -1, -1)), tuple(range(n, n*2))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    obj = smooth_mesh(name, verts, faces, color, 0)
    if front_color:
        obj.data.materials.append(c.material(front_color))
        obj.data.polygons[0].material_index=1
    if bevel:
        m=obj.modifiers.new('Soft sculpted edges','BEVEL');m.width=bevel;m.segments=3;c.apply(obj,m)
    return obj


def ribbon(name, points, widths, thickness, color, sides=24, steps=8):
    """Smooth flattened tongue, with width predominantly along Z."""
    path = c.catmull(points, steps)
    sizes = c.catmull([(w, thickness, 0) for w in widths], steps)
    verts, faces = [], []
    for i, p in enumerate(path):
        tangent = (path[min(i+1,len(path)-1)] - path[max(i-1,0)]).normalized()
        up = Vector((0,0,1))
        up = (up-tangent*up.dot(tangent)).normalized()
        depth = tangent.cross(up).normalized()
        for j in range(sides):
            theta = 2*math.pi*j/sides
            verts.append(p+up*max(.009,sizes[i].x)*math.cos(theta)+depth*sizes[i].y*math.sin(theta))
    for i in range(len(path)-1):
        for j in range(sides):
            a, b = i*sides+j, i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    begin, end = len(verts), len(verts)+1
    verts.extend([path[0],path[-1]])
    for j in range(sides):
        faces.append((begin,(j+1)%sides,j))
        k=(len(path)-1)*sides
        faces.append((end,k+j,k+(j+1)%sides))
    return c.mesh(name, verts, faces, color)


def ell_between(name, a, b, radius, color):
    a,b=Vector(a),Vector(b)
    obj=c.ell(name,(a+b)/2,(radius[0],radius[1],(b-a).length/2),color)
    obj.rotation_euler=Vector((0,0,1)).rotation_difference(b-a).to_euler()
    return obj


def bubble(name, center, size, normal):
    obj=c.ell(name,center,size,WHITE)
    obj.rotation_euler=Vector((0,-1,0)).rotation_difference(Vector(normal).normalized()).to_euler()
    mat=c.material(WHITE)
    mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.30
    return obj


def solid_patch(name, outline, color, depth=.025):
    """Rounded closed web/marking, preserving hand-authored boundary."""
    border = [Vector(v) for v in outline]
    center = sum(border,Vector())/len(border)
    n=len(border)
    verts=[center+Vector((0,-depth,0)),center+Vector((0,depth,0))]
    verts += border
    faces=[]
    for i in range(n):
        faces.append((0,i+2,(i+1)%n+2))
        faces.append((1,(i+1)%n+2,i+2))
    return c.mesh(name, verts, faces, color)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene
    asset=bpy.data.collections.new('Pokemon_Greninja')
    scene.collection.children.link(asset)
    c.COLLECTION=asset
    c.MATERIALS.clear()
    for color in (BLUE,NAVY,CYAN,CREAM,PINK,PAD,WHITE,INK,'C62E50'):
        mat=c.material(color)
        sh=mat.node_tree.nodes.get('Principled BSDF')
        sh.inputs['Roughness'].default_value=.55
        sh.inputs['Specular IOR Level'].default_value=.24

    # Lean, tapering torso and the compact pelvis of the official crouch.
    torso=c.tube('01_Torso • tapered athletic core',
        [(0,.12,1.12),(0,.10,1.48),(0,.025,1.87),(0,-.045,2.25)],
        [(.26,.27),(.30,.29),(.32,.285),(.30,.25)],BLUE,48,10)
    pelvis=c.ell('01_Pelvis',(0,.14,1.12),(.38,.31,.27),BLUE)
    chest=solid_patch('02_Cream chest • pointed central bib',
        [(-.24,-.241,2.16),(-.32,-.285,1.99),(-.25,-.286,1.75),
         (-.11,-.292,1.47),(0,-.309,1.22),(.11,-.292,1.47),
         (.25,-.286,1.75),(.32,-.285,1.99),(.24,-.241,2.16)],CREAM,.026)
    # Hip tails are small fins rather than an added animal tail.
    for s in (-1,1):
        plate('03_Hip pointed fin '+str(s),
              [(s*.19,.25,1.28),(s*.50,.43,1.59),(s*.43,.45,1.11)],.12,BLUE,.025)
        plate('03_Cyan hip marking '+str(s),
              [(s*.30,.35,1.31),(s*.47,.445,1.51),(s*.41,.454,1.16)],.025,CYAN,.008)

    # Powerful folded thighs; asymmetric leg folding matches the reference pose.
    left_thigh=ell_between('04_Left rounded frog thigh',(.03,.10,1.08),(-1.13,-.01,1.64),(.41,.39),BLUE)
    right_thigh=ell_between('04_Right rounded frog thigh',(.02,.14,.94),(1.24,.10,1.87),(.44,.42),BLUE)
    c.tube('05_Left lower leg',[(-.85,.00,1.30),(-1.15,-.06,.95),(-1.53,-.16,.51),(-1.83,-.23,.24)],
           [.19,.13,.095,.085],BLUE,28,10)
    c.tube('05_Right folded lower leg',[(.92,.16,1.40),(.98,.54,1.08),(.59,.99,.60),(.60,.93,.20)],
           [.20,.13,.085,.080],BLUE,28,10)
    plate('05_Left heel spur',[(-1.48,-.07,.56),(-1.25,.02,.84),(-1.60,-.17,.42)],.09,BLUE,.015)
    plate('05_Right heel spur',[(.62,1.03,.43),(.83,1.19,.69),(.62,.95,.25)],.09,BLUE,.015)
    bubble('06_Left knee oval',(-.86,-.335,1.48),(.235,.065,.270),(-.25,-1,.25))
    bubble('06_Right knee oval',(.92,-.225,1.64),(.225,.066,.263),(.30,-1,.24))

    # Three toes, broad oval discs and pale web membranes on each foot.
    feet=[('L',(-1.81,-.22,.21),[(-2.42,-.27,.12),(-1.99,-.70,.12),(-1.43,-.54,.12)]),
          ('R',(.60,.92,.20),[(.28,.50,.12),(.72,.37,.12),(1.12,.60,.12)])]
    for label,base,tips in feet:
        base=Vector(base)
        c.ell('07_Foot palm '+label,base,(.17,.18,.085),BLUE)
        for k,tip in enumerate(tips):
            tip=Vector(tip)
            c.tube('07_Toe '+label+str(k),[base,base.lerp(tip,.5),tip],[.065,.055,.040],BLUE,20,8)
            disc=c.ell('07_Toe disc '+label+str(k),tip,(.205,.115,.055),PAD)
            disc.rotation_euler.z=math.atan2(tip.y-base.y,tip.x-base.x)
        for k in range(2):
            a,b=Vector(tips[k]),Vector(tips[k+1])
            solid_patch('07_Pale foot web '+label+str(k),
                        [base+Vector((0,0,.035)),base.lerp(a,.68)+Vector((0,0,.025)),
                         base.lerp(b,.68)+Vector((0,0,.025))],CREAM,.018)

    # Near arm reaches the floor; far arm extends high to the side.
    c.tube('08_Downward upper arm',[(-.24,-.02,2.16),(-.36,-.13,1.86),(-.29,-.37,1.49)],
           [.155,.125,.115],BLUE,32,10)
    c.tube('08_Downward forearm',[(-.29,-.37,1.50),(-.26,-.46,1.12),(-.23,-.68,.62),(-.25,-.85,.32)],
           [.17,.14,.085,.085],BLUE,32,10)
    bubble('09_Downward elbow bubble',(-.29,-.565,1.48),(.20,.065,.25),(-.12,-1,.04))
    c.tube('08_Raised upper arm',[(.24,.015,2.18),(.65,-.015,2.45),(1.12,-.01,2.71)],
           [.15,.125,.13],BLUE,32,10)
    c.tube('08_Raised forearm',[(1.10,-.01,2.70),(1.42,-.04,2.88),(1.76,-.05,3.02),(2.06,-.06,3.14)],
           [.17,.16,.10,.065],BLUE,32,10)
    bubble('09_Raised elbow bubble',(1.35,-.205,2.89),(.25,.060,.14),(.10,-1,.40))

    # Low hand spreads in a ground-contact tripod; raised hand fans in the air.
    handsets=[('Low',(-.25,-.86,.30),[(-.83,-1.22,.105),(-.24,-1.49,.105),(.37,-1.23,.105)]),
              ('High',(2.06,-.06,3.14),[(2.57,-.04,3.64),(2.81,-.065,3.48),(2.91,-.09,3.16)])]
    for label,base,tips in handsets:
        base=Vector(base)
        c.ell('10_Hand palm '+label,base,(.12,.10,.115),BLUE)
        for k,tip in enumerate(tips):
            tip=Vector(tip)
            c.tube('10_Finger '+label+str(k),[base,base.lerp(tip,.55),tip],[.050,.040,.029],BLUE,20,8)
            if label=='Low':
                disc=c.ell('10_Finger disc '+label+str(k),tip,(.235,.135,.052),PAD)
                disc.rotation_euler.z=math.atan2(tip.y-base.y,tip.x-base.x)
            else:
                disc=c.ell('10_Finger disc '+label+str(k),tip,(.18,.048,.075),PAD)
                disc.rotation_euler.y=-math.atan2(tip.z-base.z,tip.x-base.x)
        for k in range(2):
            a,b=Vector(tips[k]),Vector(tips[k+1])
            normal=Vector((0,-.023,0)) if label=='High' else Vector((0,0,.028))
            solid_patch('10_Pale hand web '+label+str(k),[base+normal,base.lerp(a,.70)+normal,base.lerp(b,.70)+normal],CREAM,.014)

    # Main skull tapers to a pointed chin; clean hand-authored cross sections.
    rings=[(2.22,.050,.065,-.50),(2.31,.24,.15,-.38),
           (2.49,.40,.24,-.22),(2.72,.50,.29,-.075),
           (2.96,.48,.30,.015),(3.13,.35,.23,.06),
           (3.22,.15,.13,.08),(3.24,.012,.015,.08)]
    samples=np.array([list(p) for p in c.catmull(rings,7)])
    n=80;verts=[];faces=[]
    for z,rx,ry,cy in samples:
        for j in range(n):
            a=2*math.pi*j/n
            verts.append((max(.012,rx)*math.sin(a),cy-max(.012,ry)*math.cos(a),z))
    for k in range(len(samples)-1):
        for j in range(n):
            a,b=k*n+j,k*n+(j+1)%n
            faces.append((a,b,b+n,a+n))
    first,last=len(verts),len(verts)+1
    verts.extend([(0,samples[0,3],samples[0,0]),(0,samples[-1,3],samples[-1,0])])
    for j in range(n):
        faces.append((first,(j+1)%n,j))
        a=(len(samples)-1)*n
        faces.append((last,a+j,a+(j+1)%n))
    head=c.mesh('11_Head • tapered frog skull',verts,faces,BLUE)
    bpy.context.view_layer.update()
    tree=BVHTree.FromObject(head,bpy.context.evaluated_depsgraph_get())

    def on_head(x,z,offset):
        hit,normal,_,_=tree.ray_cast(Vector((x,-5,z)),Vector((0,1,0)))
        if hit is None:
            z2=max(2.24,min(3.22,z))
            rx=np.interp(z2,samples[:,0],samples[:,1]);ry=np.interp(z2,samples[:,0],samples[:,2]);cy=np.interp(z2,samples[:,0],samples[:,3])
            y=cy-ry*math.sqrt(max(.02,1-(x/max(.01,rx))**2))
        else:y=hit.y
        return (x,y-offset,z)

    face_regions=[]
    def face_patch(name,outline,color,offset=.012):
        # Painted regions sit on the real head surface without layered shells.
        face_regions.append((color,outline))

    # Two long lateral fins have pale front faces and cyan inner membranes.
    for s in (-1,1):
        # The pale faces point OUTWARD, on sagittal fins swept behind the head.
        # This keeps one cream face and the opposite blue inner face visible in a
        # three-quarter view, as in the official sculpt; these are not flat ears.
        outline=[(s*.43,-.10,2.99),(s*.52,-.025,3.52),(s*.78,1.15,3.91),
                 (s*.50,.67,3.42),(s*.38,.32,3.00)]
        n=len(outline)
        halfwidth=[.045,.055,.004,.043,.04]
        vertices=[(x+s*w,y,z) for (x,y,z),w in zip(outline,halfwidth)]+[(x-s*w,y,z) for (x,y,z),w in zip(outline,halfwidth)]
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        fin=c.mesh('12_Swept lateral head fin '+str(s),vertices,faces,BLUE)
        fin.data.materials.append(c.material(CREAM));fin.data.polygons[0].material_index=1
        m=fin.modifiers.new('Soft fin bevel','BEVEL');m.width=.010;m.segments=3;c.apply(fin,m)
        plate('12_Cyan inner head sail '+str(s),
              [(s*.12,.10,3.10),(s*.44,.59,3.38),(s*.38,.32,3.00)],.060,CYAN,.010)
        face_patch('12_Pale lower cheek '+str(s),
            [(s*.055,2.265),(s*.30,2.36),(s*.43,2.60),(s*.48,2.90),
             (s*.42,2.83),(s*.34,2.56),(s*.20,2.39)],CREAM,.014)
        # Sharp eye contour with a small red iris, not round cartoon pupils.
        eye=[(s*.13,2.80),(s*.25,2.91),(s*.43,2.95),(s*.468,2.84),(s*.40,2.67),(s*.28,2.62)]
        face_patch('13_Eye dark boundary '+str(s),eye,INK,.022)
        mid=np.mean(eye,axis=0)
        inner=[tuple(mid+(np.array(p)-mid)*.91) for p in eye]
        face_patch('13_Triangular white eye '+str(s),inner,WHITE,.034)
        iris=[(s*.29,2.70),(s*.31,2.80),(s*.36,2.83),(s*.39,2.78),(s*.36,2.68),(s*.32,2.65)]
        face_patch('13_Ruby iris '+str(s),iris,'C62E50',.046)
        pupil=[(s*.325,2.68),(s*.338,2.79),(s*.358,2.79),(s*.35,2.68)]
        face_patch('13_Narrow eye pupil '+str(s),pupil,INK,.055)
        face_regions.append((WHITE,ellipse(s*.345,2.785,.009,.020)))

    paint_front(head,'Greninja painted face',OUT/'Textures'/'Greninja_face.png',
                BLUE,face_regions,(-.54,.54,2.20,3.27),2048)

    # Tall central arrow crest meets the pointed nose. Kept genuinely three-dimensional.
    crest_rings=[(2.245,.009,-.635,-.47),(2.73,.105,-.47,-.13),
                 (3.14,.125,-.32,.04),(3.77,.004,.035,.045)]
    vertices=[];faces=[]
    for z,width,front_y,back_y in crest_rings:
        middle=(front_y+back_y)/2
        vertices += [(0,front_y,z),(-width,middle,z),(0,back_y,z),(width,middle,z)]
    for k in range(len(crest_rings)-1):
        for j in range(4):
            a,b=k*4+j,k*4+(j+1)%4
            faces.append((a,b,b+4,a+4))
    faces += [(3,2,1,0),(12,13,14,15)]
    crest=c.mesh('14_Central diamond blade crest',vertices,faces,BLUE)
    for polygon in crest.data.polygons:polygon.use_smooth=False
    c.tube('14_Subtle mouth seam',[(-.30,-.369,2.44),(-.15,-.509,2.34),(0,-.578,2.28),(.15,-.509,2.34),(.30,-.369,2.44)],
           [.009,.009,.010,.009,.009],INK,12,7)

    # Tongue collar is an oblique flattened loop, plus a broad rounded trailing tip.
    n,minor=128,24;verts=[];faces=[]
    for i in range(n):
        a=2*math.pi*i/n
        center=Vector((.43*math.cos(a),.01+.33*math.sin(a),2.28+.055*math.sin(a)))
        radial=Vector((math.cos(a),math.sin(a),0))
        for j in range(minor):
            b=2*math.pi*j/minor
            verts.append(center+radial*.115*math.cos(b)+Vector((0,0,.17*math.sin(b))))
    for i in range(n):
        for j in range(minor):
            faces.append((i*minor+j,((i+1)%n)*minor+j,((i+1)%n)*minor+(j+1)%minor,i*minor+(j+1)%minor))
    c.mesh('15_Pink tongue scarf • neck wrap',verts,faces,PINK)
    ribbon('15_Pink tongue scarf • flowing free end',
           [(-.32,.17,2.36),(-.71,.20,2.52),(-1.18,.23,2.59),(-1.68,.23,2.86),(-2.18,.17,3.13),(-2.52,.10,3.15),(-2.68,.075,3.08)],
           [.13,.14,.135,.15,.20,.18,.01],.065,PINK)

    # Lower the torso/head into the compact crouch, then join organic skin parts.
    # Blade fins, pads, markings and tongue remain independently editable.
    for obj in list(asset.objects):
        if obj.type!='MESH':continue
        if obj.name.startswith(('11_','12_','13_','14_')):
            for vertex in obj.data.vertices:
                world=obj.matrix_world@vertex.co
                world.x*=1.35
                world.z-=.27
                vertex.co=obj.matrix_world.inverted()@world
        elif obj.name.startswith('15_'):
            for vertex in obj.data.vertices:
                world=obj.matrix_world@vertex.co
                world.z-=.27
                vertex.co=obj.matrix_world.inverted()@world
        elif obj.name.startswith(('01_','02_','03_','08_','09_','10_')):
            for vertex in obj.data.vertices:
                world=obj.matrix_world@vertex.co
                # Ground hand stays planted; upper body compresses smoothly.
                world.z-=.27*min(1,max(0,(world.z-1.40)/.75))
                vertex.co=obj.matrix_world.inverted()@world
    skin_parts=[obj for obj in list(asset.objects) if obj.type=='MESH' and obj.name.startswith(
        ('01_','04_','05_','08_','07_Foot palm','07_Toe L','07_Toe R','10_Hand palm','10_Finger Low','10_Finger High'))]
    torso=c.union('01_Continuous blue skin • torso and limbs',skin_parts,BLUE,.015)
    decimate=torso.modifiers.new('Balanced sculpt density','DECIMATE');decimate.ratio=.50;c.apply(torso,decimate)
    smooth=torso.modifiers.new('Final gentle sculpt polish','SMOOTH');smooth.factor=.50;smooth.iterations=12;c.apply(torso,smooth)
    bpy.context.view_layer.update()
    body_tree=BVHTree.FromObject(torso,bpy.context.evaluated_depsgraph_get())
    back_regions=[]
    for s in (-1,1):
        x=s*.60;z=1.38
        contour=[(x,z+.24),(x+s*.08,z+.07),(x+s*.25,z+.12),
                 (x+s*.12,z-.04),(x+s*.13,z-.23),(x-s*.025,z-.09),
                 (x-s*.19,z-.11),(x-s*.09,z+.06)]
        back_regions.append((CYAN,contour))
        plate('16_Rear hip spur '+str(s),
            [(s*.24,.34,1.20),(s*.35,.43,1.45),(s*.64,.69,1.75),(s*.45,.57,1.24)],.09,BLUE,.012)
    paint_front(torso,'Greninja painted hip markings',OUT/'Textures'/'Greninja_hips.png',
                BLUE,back_regions,(-1.35,1.35,0,2.2),2048,normal_sign=1)

    # All deliverable components have authored UVs (solid colors do not depend on them).
    # A simple projection is sufficient for these editable solid-color meshes.
    for obj in list(asset.objects):
        if obj.type!='MESH':continue
        obj['pokemon']='Greninja'
        obj['design']='Original sculpture based on official Greninja artwork; no game mesh extraction'
        if not obj.data.uv_layers:
            uv=obj.data.uv_layers.new(name='Editable planar UV')
            coords=np.array([list(v.co) for v in obj.data.vertices])
            low=coords.min(axis=0)
            span=np.maximum(coords.max(axis=0)-low,.001)
            for poly in obj.data.polygons:
                for loop in poly.loop_indices:
                    v=coords[obj.data.loops[loop].vertex_index]
                    uv.data[loop].uv=((v[0]-low[0])/span[0],(v[2]-low[2])/span[2])

    # Scale to a compact 1.5 m high display. Preserve floor contact exactly.
    bpy.context.view_layer.update()
    co=[o.matrix_world@v.co for o in asset.objects if o.type=='MESH' for v in o.data.vertices]
    lowest=min(p.z for p in co);highest=max(p.z for p in co)
    scale=1.5/(highest-lowest)
    for obj in asset.objects:
        obj.location.z-=lowest
        obj.location*=scale;obj.scale*=scale
        c.active(obj);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    root=bpy.data.objects.new('root_Greninja',None);asset.objects.link(root)
    root['korean']='개굴닌자';root['dex']=658
    root['pose']='Official artwork-inspired crouching ninja pose'
    root['scale_note']='Crouched sculpt including crests normalized to 1.5 m; not anatomical height calibration'
    for obj in asset.objects:
        if obj!=root:obj.parent=root
    make_studio()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in asset.objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=torso
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Greninja.blend'))
    bpy.ops.export_scene.gltf(filepath=str(OUT/'Greninja.glb'),export_format='GLB',use_selection=True,
                             export_apply=True,export_animations=False,export_cameras=False,export_lights=False,
                             export_extras=True)
    (OUT/'references'/'sources.json').write_text(json.dumps({
        'official_pokedex':'https://www.pokemon.com/us/pokedex/greninja',
        'official_artwork':'https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/658.png',
        'supplementary_concept_sheet':'https://www.pokewiki.de/images/e/e3/Quajutsu_Konzeptzeichnung.png',
        'supplementary_home_screenshot':'https://cdn-ak.f.st-hatena.com/images/fotolife/a/archerychocolate/20250422/20250422230248.png',
        'notes':'Artwork used for visual reference only. No downloaded game geometry.'},indent=2),encoding='utf-8')


def make_studio():
    scene=bpy.context.scene
    studio=bpy.data.collections.new('90_Presentation');scene.collection.children.link(studio)
    def move(obj):
        for col in list(obj.users_collection):col.objects.unlink(obj)
        studio.objects.link(obj)
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=1.20,depth=.045,location=(0,0,-.030))
    obj=bpy.context.object;obj.name='Display • slate plinth';move(obj)
    obj.data.materials.append(c.material('273748'))
    mod=obj.modifiers.new('Rounded edge','BEVEL');mod.width=.015;mod.segments=3;c.apply(obj,mod)
    for p in obj.data.polygons:p.use_smooth=True
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.057))
    obj=bpy.context.object;obj.name='Studio floor';move(obj);obj.data.materials.append(c.material('182431'))
    def area(name,position,power,color,size):
        data=bpy.data.lights.new(name,'AREA');obj=bpy.data.objects.new(name,data);studio.objects.link(obj)
        obj.location=position;obj.rotation_euler=(Vector((0,0,.75))-obj.location).to_track_quat('-Z','Y').to_euler()
        data.energy=power;data.color=color;data.shape='DISK';data.size=size
    area('Key softbox',(-3,-4,5),550,(1,.90,.79),4)
    area('Cool fill',(4,-2,3),400,(.70,.84,1),3)
    area('Back rim',(0,3.5,4),650,(.63,.85,1),3)
    world=bpy.data.worlds.new('Studio world');world.use_nodes=True;scene.world=world
    world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.16,.21,.28,1)
    world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.45
    camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);studio.objects.link(cam)
    camdata.type='ORTHO';scene.camera=cam
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=6
    scene.render.resolution_x=1600;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.view_settings.view_transform='AgX'
    scene.unit_settings.system='METRIC'
    set_view('preview')
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_distance=3.2
                area.spaces.active.region_3d.view_location=(0,0,.72)
                area.spaces.active.region_3d.view_rotation=cam.rotation_euler.to_quaternion()


VIEWS={
    'preview':((-2.5,-7,2.65),(0,-.02,.74),2.75),
    'front':((0,-8,.82),(0,0,.77),2.75),
    'back':((-2.8,7,2.7),(0,0,.75),2.75),
    'side':((7,-.8,2.1),(0,0,.75),2.20),
    'face':((1.15,-7,1.8),(0,-.08,1.11),1.25),
    'clay':((-2.5,-7,2.65),(0,-.02,.74),2.75),
}


def set_view(name):
    scene=bpy.context.scene;cam=scene.camera
    pos,target,scale=VIEWS[name]
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale


def render(options):
    scene=bpy.context.scene
    if options.gpu:
        pref=bpy.context.preferences.addons['cycles'].preferences
        pref.compute_device_type='OPTIX';pref.get_devices()
        for device in pref.devices:device.use=device.type=='OPTIX'
        if not any(d.type=='OPTIX' for d in pref.devices):raise RuntimeError('No OPTIX device available')
        scene.cycles.device='GPU'
    if options.draft:
        scene.cycles.samples=12;scene.render.resolution_percentage=50
    else:
        scene.cycles.samples=48;scene.render.resolution_percentage=100
    views=list(VIEWS) if options.full else [options.view]
    for name in views:
        set_view(name)
        scene.view_layers[0].material_override=None
        if name=='clay':scene.view_layers[0].material_override=c.material('9BAABB',.68)
        filename=name+('_draft' if options.draft else '')+'.png'
        scene.render.filepath=str(OUT/'renders'/filename)
        bpy.ops.render.render(write_still=True)
    scene.view_layers[0].material_override=None


if __name__=='__main__':
    options=args()
    if options.render_only:bpy.ops.wm.open_mainfile(filepath=str(OUT/'Greninja.blend'))
    else:build()
    render(options)
    print('GRENINJA_BUILD_OK',flush=True)
