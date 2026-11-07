"""AUREL: an original contemporary office tower, modeled and rendered in Blender."""
import hashlib
import json
import math
import random
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/ModernTower'
OUT.mkdir(exist_ok=True)
(OUT/'Textures').mkdir(exist_ok=True)
(OUT/'.temp').mkdir(exist_ok=True)
tempfile.tempdir=str(OUT/'.temp')
bpy.context.preferences.filepaths.temporary_directory=tempfile.tempdir
random.seed(4127)
rng=np.random.default_rng(4127)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'; scene.unit_settings.scale_length=1
scene.render.engine='CYCLES'
scene.cycles.samples=80; scene.cycles.use_denoising=True
scene.cycles.max_bounces=12; scene.cycles.transmission_bounces=8
scene.cycles.transparent_max_bounces=12
scene.cycles.adaptive_threshold=.025
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX'; prefs.get_devices()
for d in prefs.devices: d.use=d.type!='CPU'
scene.cycles.device='GPU'
scene.render.resolution_x=1600; scene.render.resolution_y=1900
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.view_settings.exposure=-1.35

groups={}
for name in ('01_Structure','02_Curtainwall','03_Interiors','04_Architectural_Details',
             '05_Landscape','06_Rooftop','90_Presentation'):
    c=bpy.data.collections.new(name); scene.collection.children.link(c); groups[name]=c
current='01_Structure'
cache={}
night_lights=[]


def mat(name,color,rough=.5,metal=0,transmission=0,emission=0,texture=None):
    m=bpy.data.materials.new(name); m.use_nodes=True; m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
    p.inputs['Transmission Weight'].default_value=transmission
    p.inputs['IOR'].default_value=1.46 if transmission else 1.5
    if emission:
        p.inputs['Emission Color'].default_value=(*color,1)
        p.inputs['Emission Strength'].default_value=emission
    if texture:
        size=1024
        v,u=np.mgrid[0:size,0:size].astype(np.float32)/size
        noise=rng.normal(0,.014,(size,size))
        for frequency,amplitude in ((3,.018),(11,.012),(41,.008)):
            noise+=amplitude*np.sin((u*.73+v*.29)*math.tau*frequency)*np.cos((v*.8-u*.3)*math.tau*frequency)
        if texture=='wood':
            noise+=.075*np.sin((u+.009*np.sin(v*math.tau*3))*math.tau*72)
        rgba=np.ones((size,size,4),np.float32)
        rgba[:,:,:3]=np.clip(np.array(color)*(1+noise[:,:,None]),.005,.98)
        image=bpy.data.images.new(name+'_BaseColor',size,size,alpha=False)
        image.pixels.foreach_set(rgba.ravel())
        image.filepath_raw=str(OUT/'Textures'/(name+'.png')); image.file_format='PNG'
        image.save(); image.pack()
        tex=m.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=image
        m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
        bump=m.node_tree.nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value=.12
        bump.inputs['Distance'].default_value=.0025
        m.node_tree.links.new(tex.outputs['Color'],bump.inputs['Height'])
        m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    return m


limestone=mat('Limestone',(.70,.665,.575),.67,texture='stone')
stone_dark=mat('Basalt',(.145,.16,.16),.6,texture='stone')
concrete=mat('Concrete',(.47,.49,.48),.78,texture='stone')
bronze=mat('Satin_bronze',(.36,.28,.17),.27,.82)
aluminum=mat('Anodized_dark',(.065,.085,.095),.28,.72)
glass=[mat('Vision_glass_'+str(i),(.56+i*.025,.72+i*.012,.79+i*.008),.035+i*.007,0,1) for i in range(3)]
clear=mat('Low_iron_glass',(.92,.97,.97),.035,0,1)
spandrel=mat('Insulated_spandrel',(.095,.145,.165),.23,.42)
white=mat('Warm_ceiling',(.58,.58,.54),.73)
carpet=mat('Office_carpet',(.18,.205,.21),.93,texture='stone')
wood=mat('Smoked_oak',(.29,.18,.095),.5,texture='wood')
black=mat('Rubber_gasket',(.018,.023,.025),.78)
soil=mat('Soil',(.08,.065,.04),.95)
bark=mat('Bark',(.18,.145,.09),.88,texture='wood')
leaves=[mat('Foliage_'+str(i),c,.65) for i,c in enumerate([
    (.075,.135,.035),(.13,.22,.055),(.21,.30,.07),(.095,.19,.055)])]
light=mat('Warm_LED',(.98,.80,.53),.3,emission=.8)
screenmat=mat('Monitor_display',(.18,.28,.35),.35,emission=.2)
asphalt=mat('Asphalt',(.065,.075,.09),.92,texture='stone')
clay=mat('Blockout',(.5,.53,.52),.7)


def mesh(name,verts,faces,material,bevel=0,group=None):
    data=bpy.data.meshes.new(name); data.from_pydata(verts,[],faces); data.update()
    bm=bmesh.new(); bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(data); bm.free()
    data.materials.append(material)
    uv=data.uv_layers.new(name='UV_Surface')
    for poly in data.polygons:
        axis=max(range(3),key=lambda a:abs(poly.normal[a]))
        a,b=[i for i in range(3) if i!=axis]
        for loop in poly.loop_indices:
            co=data.vertices[data.loops[loop].vertex_index].co
            uv.data[loop].uv=(co[a]*.45,co[b]*.45)
    obj=bpy.data.objects.new(name,data); groups[group or current].objects.link(obj)
    if bevel:
        mod=obj.modifiers.new('Edge highlight','BEVEL'); mod.width=bevel; mod.segments=2 if bevel>=.02 else 1
    return obj


def box(name,size,loc,material=bronze,bevel=.012,rot=None):
    key=(tuple(round(s,5) for s in size),material.name,bevel)
    if key in cache:
        obj=cache[key].copy(); groups[current].objects.link(obj); obj.name=name
    else:
        x,y,z=(s/2 for s in size)
        obj=mesh(name,[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
                       (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)],
            [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],material,bevel)
        cache[key]=obj
    obj.location=loc; obj.rotation_euler=rot or (0,0,0); obj.scale=(1,1,1)
    return obj


def beam(name,a,b,width=.1,depth=None,material=bronze,bevel=.006):
    a,b=Vector(a),Vector(b)
    obj=box(name,(width,depth or width,(b-a).length),(a+b)/2,material,bevel)
    obj.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return obj


def tube(name,a,b,radius,material=aluminum,n=10):
    a,b=Vector(a),Vector(b); length=(b-a).length
    key=('tube',radius,round(length,5),material.name,n)
    if key in cache:
        obj=cache[key].copy(); groups[current].objects.link(obj); obj.name=name
    else:
        verts=[(radius*math.cos(i*math.tau/n),radius*math.sin(i*math.tau/n),z)
               for z in (-length/2,length/2) for i in range(n)]
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        obj=mesh(name,verts,faces,material); cache[key]=obj
    obj.location=(a+b)/2; obj.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return obj


def slab(name,outline,z,thickness,material=concrete):
    n=len(outline)
    verts=[(x,y,h) for h in (z-thickness,z) for x,y in outline]
    return mesh(name,verts,[tuple(reversed(range(n))),tuple(range(n,2*n))]+
                [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],material,min(.015,thickness*.2))


def facade(name,center,z,width,depth,height,direction,material,offset=0,bevel=.006):
    d=Vector(direction).normalized(); outward=Vector((d.y,-d.x))
    xy=Vector(center)+outward*offset
    return box(name,(width,depth,height),(xy.x,xy.y,z),material,bevel,
               (0,0,math.atan2(d.y,d.x)))


def point_camera(loc,target,lens=52,shift=0):
    camera.location=loc
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.lens=lens; camera.data.shift_y=shift


def area(name,loc,target,energy,size,color,night_energy=None):
    data=bpy.data.lights.new(name,'AREA'); data.energy=energy; data.shape='RECTANGLE'; data.size=size; data.size_y=size*.18; data.color=color
    obj=bpy.data.objects.new(name,data); groups['90_Presentation'].objects.link(obj); obj.location=loc
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    obj.visible_glossy=False
    obj.visible_transmission=False
    if night_energy is not None: night_lights.append((obj,energy,night_energy))
    return obj


current='90_Presentation'
world=bpy.data.worlds.new('Aurel_Daylight'); scene.world=world; world.use_nodes=True
wn=world.node_tree.nodes; wl=world.node_tree.links
sky=wn.new('ShaderNodeTexSky'); sky.sky_type='MULTIPLE_SCATTERING'
sky.sun_elevation=math.radians(28); sky.sun_rotation=math.radians(145)
sky.air_density=1.05
background=wn.get('Background'); background.inputs['Strength'].default_value=.38
wl.new(sky.outputs[0],background.inputs['Color'])
camera_data=bpy.data.cameras.new('Architectural_camera')
camera=bpy.data.objects.new('Camera_Hero',camera_data); groups[current].objects.link(camera); scene.camera=camera
camera.data.clip_end=50000
point_camera((90,-125,27),(0,0,27),64,.10)
area('Soft_front',(15,-48,48),(0,0,20),3000,35,(.82,.9,1),16000)
box('Ground',(10000,10000,.25),(0,0,-.4),concrete,.01)

# Save the volume study before architectural detail.
current='01_Structure'
blocks=[box('Podium_block',(32,26,7.4),(0,0,3.7),clay),
        box('Tower_block',(22.4,19.2,43.2),(0,0,29),clay),
        box('Crown_block',(16,14.4,10.8),(0,.8,56),clay)]
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Aurel_blockout.blend'))
for obj in blocks: bpy.data.objects.remove(obj,do_unlink=True)
cache.clear()
print('STAGE: massing saved',flush=True)

footprint=[(-10,-9.6),(10,-9.6),(11.2,-8.4),(11.2,8.4),(10,9.6),(-10,9.6),(-11.2,8.4),(-11.2,-8.4)]
crown=[(-7,-6.4),(7,-6.4),(8,-5.4),(8,7),(7,8),(-7,8),(-8,7),(-8,-5.4)]

# Podium stone cladding uses actual joints, reveals and a deep lobby.
slab('Podium_foundation',[(-16,-13),(16,-13),(16,13),(-16,13)],.35,.35,stone_dark)
slab('Podium_roof',[(-16,-13),(16,-13),(16,13),(-16,13)],7.4,.42,limestone)
for x in (-15.5,-9,-3,3,9,15.5):
    for y in (-12.3,12.3):
        box('Structural_pier',(1.05,1.0,6.8),(x,y,3.75),limestone,.025)
        for z in (1.8,3.4,5.0,6.6):
            box('Pier_joint',(1.065,1.012,.018),(x,y,z),stone_dark,0)
for y in (-7.5,-2,3.5,9):
    for x in (-15.5,15.5):
        box('Side_pier',(1,1.05,6.8),(x,y,3.75),limestone,.025)
for y in (-13,13):
    for x in np.arange(-14.4,16,3.2):
        box('Stone_fascia_panel',(3.17,.22,.65),(x,y,7.13),limestone,.008)
for x in (-16,16):
    for y in np.arange(-11.4,13,3.2):
        box('Stone_fascia_side',(.22,3.17,.65),(x,y,7.13),limestone,.008)
current='02_Curtainwall'
for y,angle in [(-12.7,0),(12.7,math.pi)]:
    for i in range(18):
        x=-14.45+i*1.7
        if y<0 and abs(x)<2.6: continue
        box('Lobby_glass',(1.65,.035,6.1),(x,y,3.55),clear,0)
        box('Lobby_mullion',(.055,.14,6.3),(x-.85,y,3.55),aluminum,.004)
        box('Lobby_transom',(1.7,.12,.055),(x,y,3.8),aluminum,.004)
for x in (-15.75,15.75):
    for y in np.arange(-11.5,12.0,1.9):
        box('Lobby_side_glass',(.035,1.85,6.1),(x,y,3.55),clear,0)
        box('Lobby_side_mullion',(.14,.06,6.3),(x,y-.95,3.55),aluminum,.004)

def floor_facade(outline,z,index,recessed=False):
    global current
    current='01_Structure'
    slab('Floor_slab',outline,z,.22,white)
    slab('Carpet_finish',[(x*.975,y*.975) for x,y in outline],z+.025,.025,carpet)
    box('Service_core',(7,7,3.35),(0,.8,z+1.67),white,.02)
    for edge in range(len(outline)):
        a,b=Vector(outline[edge]),Vector(outline[(edge+1)%len(outline)])
        d=(b-a).normalized(); count=max(1,round((b-a).length/1.65)); width=(b-a).length/count
        for bay in range(count):
            center=a+(b-a)*(bay+.5)/count
            offset=-2.5 if recessed and edge==0 else 0
            current='02_Curtainwall'
            facade('Vision_panel',center,z+2.13,width-.10,.028,2.72,d,glass[(index+bay)%3],offset,0)
            facade('Spandrel_panel',center,z+.51,width-.08,.12,.85,d,spandrel,offset,.008)
            facade('Horizontal_pressure_cap',center,z+3.55,width,.13,.065,d,bronze,offset+.06,.005)
            facade('Vertical_mullion',a+(b-a)*bay/count,z+1.8,.075,.18,3.6,d,bronze,offset+.055,.006)
            if not recessed or edge!=0:
                facade('Solar_fin',a+(b-a)*bay/count,z+1.8,.075,.42,3.6,d,bronze,.21,.008)
            current='03_Interiors'
            if count>2 and bay%3==1:
                facade('Room_divider',center,z+1.55,.075,2.4,2.8,d,white,offset-1.55,.008)
            if count>2 and bay%3!=1 and (index+bay)%4!=0:
                facade('Desk',center,z+.79,1.12,.64,.07,d,wood,offset-1.1,.015)
                facade('Desk_pedestal',center,z+.4,.32,.45,.72,d,white,offset-1.15,.01)
                facade('Office_monitor',center,z+1.1,.42,.035,.28,d,screenmat,offset-1.2,.008)
                facade('Chair_back',center,z+.9,.43,.08,.45,d,aluminum,offset-1.85,.025)
                facade('Chair_seat',center,z+.5,.43,.43,.08,d,aluminum,offset-1.75,.025)
            if bay%3==0 and count>2:
                facade('Ceiling_strip',center,z+3.31,1.1,.32,.035,d,light,offset-1.5,0)
    if index%3!=1:
        for x in (-5,5):
            area('Office_light',(x,-4.5,z+3.2),(x,-4.5,z),0,4,(1,.78,.52),350 if index%2 else 220)


for level in range(12):
    floor_facade(footprint,7.4+level*3.6,level,recessed=level==6)
for level in range(3):
    floor_facade(crown,50.6+level*3.6,level+12)
current='01_Structure'
slab('Terrace_roof',footprint,50.6,.27,limestone)
slab('Crown_roof',crown,61.4,.26,limestone)
print('STAGE: facade and interior depth complete',flush=True)

current='04_Architectural_Details'
# Clear entrance doors, vertical handles, canopy with a warm underside and drainage edge.
for x in (-1.9,-.63,.63,1.9):
    box('Entrance_door',(1.21,.035,3.4),(x,-12.78,2.05),clear,0)
    box('Door_jamb',(.055,.12,3.5),(x-.63,-12.81,2.05),bronze,.004)
    tube('Door_pull',(x+.40,-12.94,1.15),(x+.40,-12.94,2.05),.018,bronze,12)
box('Entrance_upper_glass',(5.15,.035,2.45),(0,-12.75,5.05),clear,0)
box('Entry_header',(5.3,.2,.12),(0,-12.8,3.85),bronze,.01)
box('Canopy_roof',(10,4.5,.20),(0,-14.25,4.55),bronze,.025)
box('Canopy_soffit',(9.8,4.3,.08),(0,-14.25,4.40),wood,.01)
for x in np.arange(-4.7,4.8,.23):
    box('Soffit_slat',(.035,4.2,.055),(x,-14.25,4.33),aluminum,.004)
for x in (-3.5,0,3.5):
    box('Canopy_recessed_light',(.055,3.8,.025),(x,-14.25,4.29),light,0)
for x in (-4.5,4.5):
    beam('Canopy_tie',(x,-12.6,6.0),(x,-15.9,4.65),.035,material=aluminum)

fontpath=Path('C:/Windows/Fonts/segoeuil.ttf')
font=bpy.data.fonts.load(str(fontpath)) if fontpath.exists() else None
def lettering(name,text,loc,size,material=bronze):
    curve=bpy.data.curves.new(name,'FONT'); curve.body=text; curve.size=size
    curve.align_x='CENTER'; curve.align_y='CENTER'; curve.space_character=1.3
    curve.extrude=.008; curve.bevel_depth=.0015; curve.bevel_resolution=0; curve.resolution_u=3
    if font: curve.font=font
    obj=bpy.data.objects.new(name,curve); groups[current].objects.link(obj)
    obj.location=loc; obj.rotation_euler=(math.pi/2,0,0); curve.materials.append(material)
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active=obj
    bpy.ops.object.convert(target='MESH')
    bm=bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(obj.data); bm.free()
    obj.data.uv_layers.new(name='UV_Surface'); obj.select_set(False)
    return obj
lettering('Aurel_entry','A U R E L',(0,-13.14,6.25),.78,bronze)
lettering('Aurel_address','21  /  BUSINESS AVENUE',(0,-13.14,5.55),.19,aluminum)
box('Address_totem',(1.1,.32,2.5),(-7,-15.8,1.6),stone_dark,.03)
lettering('Totem_number','21',(-7,-15.98,2.15),.55,light)
lettering('Totem_name','AUREL',(-7,-15.98,1.55),.15,light)
for z,y,width in ((.08,-17.2,12),(.20,-16.85,11.7),(.32,-16.5,11.4)):
    box('Entry_step',(width,.38,.16),(0,y,z),limestone,.018)
    box('Step_nosing',(width-.3,.025,.016),(0,y-.185,z+.065),light,0)

def railing(outline,z,material=clear):
    for i in range(len(outline)):
        a,b=Vector(outline[i]),Vector(outline[(i+1)%len(outline)])
        d=(b-a).normalized(); count=max(1,round((b-a).length/1.5))
        for n in range(count):
            center=a+(b-a)*(n+.5)/count
            facade('Glass_balustrade',center,z+.58,(b-a).length/count-.035,.018,1.06,d,material,0,0)
            facade('Railing_post',a+(b-a)*n/count,z+.56,.035,.05,1.12,d,aluminum,0,.003)
        beam('Railing_top',(a.x,a.y,z+1.13),(b.x,b.y,z+1.13),.04,material=bronze,bevel=.004)

railing([(-15.7,-12.7),(15.7,-12.7),(15.7,12.7),(-15.7,12.7)],7.44)
railing([(x*.985,y*.985) for x,y in footprint],50.65)
railing([(-9.8,-9.48),(9.8,-9.48),(9.8,-9.2),(-9.8,-9.2)],29.05)
for y in np.arange(-8.5,-6.6,.16):
    box('Skygarden_deck',(19.5,.145,.055),(0,y,29.08),wood,.004)

# Lobby composition is visible through the actual glass, especially at blue hour.
current='03_Interiors'
box('Lobby_floor',(30.5,24.5,.06),(0,0,.42),limestone,.02)
box('Lobby_feature_wall',(13,.4,5.9),(0,3,3.4),wood,.03)
for x in np.arange(-6.4,6.5,.24):
    box('Feature_wall_batten',(.035,.10,5.8),(x,2.74,3.4),bronze,.004)
box('Reception_counter',(5.0,1.5,1.15),(0,-1.3,1.04),limestone,.06)
box('Reception_top',(5.1,1.6,.06),(0,-1.3,1.65),stone_dark,.012)
lettering('Lobby_brand','AUREL',(0,2.48,4.25),1.1,light)
for x in (-9,9):
    for y in (-3.5,-7):
        box('Lobby_sofa',(2.5,.95,.44),(x,y,.68),carpet,.12)
        box('Sofa_back',(2.5,.18,.65),(x,y+.4,1.05),carpet,.08)
    box('Lobby_table',(1.6,.8,.08),(x,-5.25,.91),wood,.035)
    box('Table_base',(1.1,.5,.45),(x,-5.25,.65),aluminum,.01)
for x in (-8,0,8):
    area('Lobby_light',(x,-6,6.35),(x,-6,0),100,5,(1,.8,.55),700)

current='06_Rooftop'
box('Mechanical_room',(9,6,3.15),(0,1.2,63.05),aluminum,.035)
for y in (-1.9,4.3):
    for z in np.arange(61.7,64.6,.19):
        box('Mechanical_louver',(9.2,.12,.065),(0,y,z),bronze,.008,(math.radians(18),0,0))
for x in (-4.6,4.6):
    for z in np.arange(61.7,64.6,.19):
        box('Mechanical_side_louver',(.12,6.3,.065),(x,1.2,z),bronze,.008)
box('Mechanical_coping',(9.5,6.6,.17),(0,1.2,64.72),limestone,.02)
for x in (-4.7,4.7):
    for y in (-3.9,-1.4,1.1):
        box('Condenser',(1.5,1.8,.85),(x,y,61.87),white,.04)
        tube('Fan_housing',(x,y,62.32),(x,y,62.38),.58,aluminum,24)
        for a in np.linspace(0,math.pi,8):
            beam('Fan_guard',(x-.5*math.cos(a),y-.5*math.sin(a),62.40),
                 (x+.5*math.cos(a),y+.5*math.sin(a),62.40),.013,material=bronze,bevel=0)
for y in (-6.3,7.8):
    box('Crown_light',(13.5,.035,.045),(0,y,61.25),light,0)
print('STAGE: lobby, terraces and rooftop complete',flush=True)

current='05_Landscape'
def tree(loc,height=5,seed=1):
    randomizer=random.Random(seed)
    x,y,z=loc
    tube('Tree_trunk',(x,y,z),(x+.10,y+.04,z+height*.71),height*.025,bark,10)
    centers=[]
    for i in range(15):
        angle=i*2.39996; t=.38+i*.023
        radius=height*(.23 if i<11 else .16)
        end=Vector((x+math.cos(angle)*radius,y+math.sin(angle)*radius,z+height*(t+.24)))
        start=Vector((x,y,z+height*t))
        tube('Tree_branch',start,end,height*.008,bark,7)
        centers.append(end)
    verts=[]; faces=[]; colors=[]
    # Small closed leaves give real silhouettes and light transmission gaps.
    for center in centers:
        for j in range(85):
            offset=Vector((randomizer.gauss(0,height*.10),randomizer.gauss(0,height*.10),randomizer.gauss(0,height*.10)))
            p=center+offset
            length=height*randomizer.uniform(.030,.050); width=length*.46
            axis=Vector((randomizer.uniform(-1,1),randomizer.uniform(-1,1),randomizer.uniform(-.3,.8))).normalized()
            across=axis.cross(Vector((0,0,1))).normalized()
            n=axis.cross(across).normalized()*.005
            base=len(verts)
            verts += [tuple(p-axis*length),tuple(p+across*width),tuple(p+axis*length),tuple(p-across*width),tuple(p+n),tuple(p-n)]
            faces += [(base+a,base+b,base+4) for a,b in ((0,1),(1,2),(2,3),(3,0))]
            faces += [(base+b,base+a,base+5) for a,b in ((0,1),(1,2),(2,3),(3,0))]
            colors += [randomizer.randrange(4)]*8
    obj=mesh('Tree_foliage',verts,faces,leaves[0])
    for m in leaves[1:]: obj.data.materials.append(m)
    for p,index in zip(obj.data.polygons,colors): p.material_index=index
    return obj


def planter(loc,size=(2.4,2.4,.55),height=4,seed=1):
    x,y,z=loc; w,d,h=size
    box('Planter_body',size,(x,y,z+h/2),limestone,.035)
    box('Planter_soil',(w-.18,d-.18,.04),(x,y,z+h+.01),soil,.005)
    tree((x,y,z+h+.02),height,seed)


for i,(x,y) in enumerate([(-12,-16.2),(12,-16.2),(-19,-7),(19,-7),(-19,7),(19,7)]):
    planter((x,y,.04),(2.7,2.7,.5),5.2,200+i)
for i,(x,y) in enumerate([(-13,-9),(13,-9),(-13,9),(13,9)]):
    planter((x,y,7.43),(2,2,.45),3.7,300+i)
for i,x in enumerate((-7.2,0,7.2)):
    planter((x,-8.1,29.1),(1.7,1.1,.45),2.4,400+i)
for i,(x,y) in enumerate([(-9,-7.8),(9,-7.8),(-9,7.8),(9,7.8)]):
    planter((x,y,50.63),(1.6,1.6,.4),2.6,500+i)
for x in (-17.2,17.2):
    for y in (-3,4):
        box('Bench_base',(1.2,3.2,.36),(x,y,.24),stone_dark,.035)
        for j in range(6):
            box('Bench_slat',(.155,3.25,.075),(x-.46+j*.18,y,.46),wood,.015)

# Removable urban setting and reflection context.
current='90_Presentation'
box('Plaza_base',(43,38,.20),(0,0,-.02),concrete,.02)
for row in range(23):
    for col in range(26):
        x=-20+col*1.6; y=-17.6+row*1.6
        if abs(x)<16 and abs(y)<13: continue
        box('Plaza_paver',(1.577,1.577,.06),(x,y,.105),limestone if (row+col)%6 else concrete,.007)
box('Front_road',(230,14,.10),(0,-26,-.12),asphalt,.008)
box('Side_road',(14,230,.1),(29,10,-.12),asphalt,.008)
for x in range(-100,101,8):
    box('Lane_dash',(3.3,.12,.008),(x,-26,-.063),white,0)
for y in range(-80,101,8):
    box('Side_lane_dash',(.12,3.3,.008),(29,y,-.063),white,0)
for i in range(9):
    box('Crosswalk',(2.8,.42,.008),(15,-31+i*1.05,-.058),white,0)
for x in np.arange(-20,21,1.25):
    box('Front_curb',(1.23,.3,.28),(x,-19.1,-.02),concrete,.015)
for x in (-18,-9,9,18):
    tube('Bollard',(x,-18,.0),(x,-18,.85),.07,aluminum,12)
    box('Bollard_reflector',(.1,.1,.06),(x,-18,.70),light,.006)
for x in (-20,20):
    tube('Street_lamp',(x,-20,0),(x,-20,6.8),.065,aluminum,12)
    beam('Street_lamp_arm',(x,-20,6.8),(x,-22.3,6.8),.07,material=aluminum)
    box('Street_lamp_head',(.35,.9,.08),(x,-22.2,6.75),aluminum,.02)
    area('Street_lamp_light',(x,-22.2,6.69),(x,-22.2,0),0,.7,(1,.83,.60),100)
# Low-detail context is outside the asset and creates spatially varied reflections.
for x,y,w,d,h in [(-75,18,26,38,36),(-60,70,35,30,52),(63,70,30,34,45),(22,105,55,22,29)]:
    context=box('Context_building',(w,d,h),(x,y,h/2),concrete,.08)
    context.visible_camera=False
    context.visible_shadow=False
    for z in np.arange(3,h,3.5):
        context=box('Context_band',(w+.1,d+.1,.65),(x,y,z),spandrel,.01)
        context.visible_camera=False
        context.visible_shadow=False
print('STAGE: landscape and context complete',flush=True)

asset=[o for name,c in groups.items() if name!='90_Presentation' for o in c.objects if o.type=='MESH']
root=bpy.data.objects.new('AUREL_ROOT',None); groups['01_Structure'].objects.link(root)
root['scale']='meters; ground-center pivot'
root['scope']='Exterior, visible interior depth, landscaping. No walkable interior simulation.'
for o in asset: o.parent=root
scene['design']='AUREL: original contemporary office building, limestone podium and bronze unitized curtain wall'
scene['render_note']='True glass transmission with modeled interior depth; surrounding context excluded from export.'
bpy.ops.object.select_all(action='DESELECT'); root.select_set(True); bpy.context.view_layer.objects.active=root
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.region_3d.view_location=(0,0,30)
            a.spaces.active.region_3d.view_distance=120
            a.spaces.active.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
            a.spaces.active.shading.type='MATERIAL'
            a.spaces.active.clip_end=2000
scene.render.filepath=str(OUT/'hero_day.png')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Aurel_Day.blend'))

# Export evaluated copies in six groups, without changing the editable original.
temporary=bpy.data.collections.new('EXPORT_TEMP'); scene.collection.children.link(temporary)
graph=bpy.context.evaluated_depsgraph_get(); exports=[]
for name,c in groups.items():
    if name=='90_Presentation': continue
    bpy.ops.object.select_all(action='DESELECT'); copies=[]
    for original in list(c.objects):
        if original.type!='MESH': continue
        data=bpy.data.meshes.new_from_object(original.evaluated_get(graph),preserve_all_data_layers=True,depsgraph=graph)
        obj=bpy.data.objects.new('Export_copy',data); temporary.objects.link(obj)
        obj.matrix_world=original.matrix_world; obj.select_set(True); copies.append(obj)
    if copies:
        bpy.context.view_layer.objects.active=copies[0]; bpy.ops.object.join()
        obj=copies[0]; obj.name='Aurel_'+name[3:]
        scene.cursor.location=(0,0,0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        exports.append(obj)
bpy.ops.object.select_all(action='DESELECT')
for obj in exports: obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Aurel.glb'),export_format='GLB',use_selection=True,
                         export_apply=True,export_cameras=False,export_lights=False)
for obj in exports: bpy.data.objects.remove(obj,do_unlink=True)
bpy.data.collections.remove(temporary)
print('STAGE: native asset and GLB saved',flush=True)

# Hero, close-up, and blue-hour views are rendered from the same geometry.
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.render.render(write_still=True)
point_camera((27,-43,10),(0,-7.5,4.0),48)
scene.render.resolution_x=1700; scene.render.resolution_y=1100
scene.render.filepath=str(OUT/'entrance_detail.png')
bpy.ops.render.render(write_still=True)
point_camera((90,-125,27),(0,0,27),64,.10)
scene.render.resolution_x=1600; scene.render.resolution_y=1900
for link in list(background.inputs['Color'].links): wl.remove(link)
background.inputs['Color'].default_value=(.065,.11,.23,1)
background.inputs['Strength'].default_value=.6
for obj,day,night in night_lights: obj.data.energy=night
light.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=18
scene.view_settings.exposure=1.1
scene.render.filepath=str(OUT/'hero_night.png')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Aurel_Night.blend'))
bpy.ops.render.render(write_still=True)
print('AUREL_BUILD_OK',flush=True)
