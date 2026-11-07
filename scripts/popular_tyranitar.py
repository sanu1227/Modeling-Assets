"""Hand-authored Tyranitar sculpture with original painted armor patterns."""
import sys
import math
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import pokemon_common as c
from popular_lucario import loft, png_texture, uv_for_untextured

OUT=ROOT/'assets'/'PokemonPopular'/'Tyranitar'
(OUT/'renders').mkdir(parents=True,exist_ok=True)
GREEN='93A86D';DARK='282F34';BLUE='536B93';IVORY='F4F0DF';MOUTH='45383E';TONGUE='C88890'


def rgb(value):return tuple(int(value[i:i+2],16) for i in (0,2,4))


def polygon(x,z,outline):
    inside=np.zeros(x.shape,dtype=bool)
    for i,(ax,az) in enumerate(outline):
        bx,bz=outline[(i+1)%len(outline)]
        inside^=((az>z)!=(bz>z))&(x<(bx-ax)*(z-az)/(bz-az+1e-12)+ax)
    return inside


def cylindrical_paint(obj,samples,name,pattern,axis='Z',resolution=2048):
    lo,hi=samples[0,0],samples[-1,0]
    v,u=np.mgrid[0:resolution,0:resolution].astype(np.float32)/(resolution-1)
    pos=hi-v*(hi-lo);angle=u*2*math.pi
    cx,cy,rx,ry=[np.interp(pos,samples[:,0],samples[:,i]) for i in range(1,5)]
    x=cx+rx*np.sin(angle)
    if axis=='Z':y=cy-ry*np.cos(angle);z=pos
    else:y=pos;z=cy+ry*np.cos(angle)
    pixels=np.empty((resolution,resolution,3),np.uint8);pixels[:]=rgb(GREEN)
    pattern(pixels,x,y,z,angle)
    obj.data.materials.clear();obj.data.materials.append(png_texture(name,pixels,OUT))
    uv=obj.data.uv_layers.new(name='Painted armor UV')
    coords=[]
    for vert in obj.data.vertices:
        x,y,z=vert.co;pos=z if axis=='Z' else y
        cx,cy,rx,ry=[np.interp(pos,samples[:,0],samples[:,i]) for i in range(1,5)]
        a=math.atan2((x-cx)/max(.003,rx),-(y-cy)/max(.003,ry) if axis=='Z' else (z-cy)/max(.003,ry))%(2*math.pi)
        coords.append((a/(2*math.pi),(pos-lo)/(hi-lo)))
    for poly in obj.data.polygons:
        items=[coords[obj.data.loops[i].vertex_index] for i in poly.loop_indices]
        seam=max(u for u,v in items)-min(u for u,v in items)>.5
        for i,(u,v) in zip(poly.loop_indices,items):uv.data[i].uv=(u+1 if seam and u<.5 else u,v)


def body_pattern(pixels,x,y,z,a):
    front=np.cos(a)>.10;back=np.cos(a)<-.10
    belly=polygon(x,z,[(0,2.72),(.40,2.15),(.31,1.58),(0,1.12),(-.31,1.58),(-.40,2.15)])&front
    pixels[belly]=rgb(BLUE)
    for h in (2.29,1.94,1.56):pixels[belly&(abs(z-h)<.012)]=rgb('4F5C78')
    for s in (-1,1):
        for pts in [[(.16,3.01),(.32,3.12),(.43,2.92)],[(.23,2.80),(.47,2.83),(.40,2.64)]]:
            pixels[polygon(x,z,[(s*px,pz) for px,pz in pts])&front]=rgb(DARK)
    rear=polygon(x,z,[(0,2.20),(.24,1.89),(0,1.60),(-.24,1.89)])&back
    pixels[rear]=rgb(BLUE)
    pixels[rear&(abs(z-1.9)<.012)]=rgb('4F5C78')
    for pts in [[(-.12,2.77),(.12,2.77),(0,2.54)],[(-.10,2.49),(.10,2.49),(0,2.30)]]:
        pixels[polygon(x,z,pts)&back]=rgb(DARK)


def head_pattern(pixels,x,y,z,a):
    for s in (-1,1):
        side=x*s>.13
        outline=[(-.64,3.84),(-.13,3.93),(.00,3.85),(-.38,3.80)]
        pixels[polygon(y,z,outline)&side]=rgb(DARK)
        cy,cz=-.34,3.858
        inner=[(cy+(py-cy)*.88,cz+(pz-cz)*.72) for py,pz in outline]
        white=polygon(y,z,inner)&side;pixels[white]=rgb('F8F4DE')
        pixels[(((y+.38)/.028)**2+((z-3.854)/.039)**2<1)&white]=rgb('161D22')
        pixels[(((x-s*.14)/.025)**2+((z-3.785)/.012)**2<1)&(y<-.60)]=rgb('4C5B43')


def thigh_pattern(side):
    def paint(pixels,x,y,z,a):
        front=np.cos(a)>.10
        patterns=[[(.40,1.40),(.64,1.59),(.92,1.46),(.98,1.29),(.69,1.34)],[(.45,1.20),(.95,1.25),(.84,.94),(.60,1.06)]]
        for pts in patterns:pixels[polygon(x,z,[(side*px,pz) for px,pz in pts])&front]=rgb(DARK)
    return paint


def armor_spike(name,base,tip,radius,flat=.7):
    a,b=Vector(base),Vector(tip);d=b-a
    obj=c.tube(name,[a,a.lerp(b,.45),a.lerp(b,.8),b],[(radius,radius*flat),(radius*.65,radius*.50*flat),(radius*.25,radius*.20*flat),.004],GREEN,12,5)
    return obj


def armor_plate(name,a,b,tip,thickness=.12):
    """Broad triangular armor with a solid, softly rounded edge."""
    a,b,tip=Vector(a),Vector(b),Vector(tip)
    normal=(b-a).cross(tip-a).normalized()
    vertices=[p+normal*side*thickness/2 for side in (-1,1) for p in (a,b,tip)]
    obj=c.mesh(name,vertices,[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],GREEN)
    mod=obj.modifiers.new('Rounded armor edges','BEVEL');mod.width=min(.024,thickness*.24);mod.segments=3;c.apply(obj,mod)
    return obj


def breast_plate(side,samples):
    outline=[(.37,2.64),(.63,2.69),(.73,2.36),(.64,2.28),(.53,2.04),(.39,2.30)]
    vertices=[]
    for x,z in outline:
        cx,cy,rx,ry=[np.interp(z,samples[:,0],samples[:,i]) for i in range(1,5)]
        y=cy-ry*math.sqrt(max(.0,1-(x/rx)**2))-.026
        vertices.append((side*x,y,z))
    center=Vector(tuple(np.mean(vertices,axis=0)));center.y-=.035
    vertices.append(center)
    obj=c.mesh('Pointed front chest armor',vertices,[(len(outline),i,(i+1)%len(outline)) for i in range(len(outline))],GREEN)
    mod=obj.modifiers.new('Closed armor backing','SOLIDIFY');mod.thickness=.045;mod.offset=0;c.apply(obj,mod)
    mod=obj.modifiers.new('Soft armor edge','BEVEL');mod.width=.012;mod.segments=3;c.apply(obj,mod)


def mouth_bowl():
    n=96;rings=24;verts=[(0,-.31,3.47)];faces=[]
    for k in range(1,rings+1):
        r=k/rings
        for j in range(n):
            a=2*math.pi*j/n
            # The side corners retreat inside the cheeks, while upper and lower
            # edges follow the lips. A planar circular rim protruded from the jaw.
            edge_y=-.25-.50*abs(math.sin(a))**1.6
            verts.append((.29*r*math.cos(a),-.31*(1-r)+edge_y*r,3.47+.235*r*math.sin(a)))
    for j in range(n):faces.append((0,1+j,1+(j+1)%n))
    for k in range(rings-1):
        for j in range(n):
            a=1+k*n+j;b=1+k*n+(j+1)%n;faces.append((a,b,b+n,a+n))
    obj=c.mesh('04_Recessed mouth cavity',verts,faces,MOUTH)
    mod=obj.modifiers.new('Closed mouth backing','SOLIDIFY');mod.thickness=.018;mod.offset=0;c.apply(obj,mod)
    c.ell('Pink tongue',(0,-.575,3.278),(.19,.19,.035),TONGUE)
    for s in (-1,1):
        c.cone('Upper fang',(s*.20,-.736,3.675),(s*.19,-.741,3.535),.052,IVORY)
        c.cone('Lower fang',(s*.18,-.725,3.265),(s*.18,-.733,3.365),.043,IVORY)


def build():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene
    asset=bpy.data.collections.new('Pokemon_Tyranitar');scene.collection.children.link(asset)
    studio=bpy.data.collections.new('90_Presentation');scene.collection.children.link(studio)
    c.COLLECTION=asset
    for value in (GREEN,DARK,BLUE,IVORY,MOUTH,TONGUE):c.material(value,.63).node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.17
    body,samples=loft('01_Heavy armored torso',[(.68,0,.12,.35,.30),(1.05,0,.10,.73,.56),(1.45,0,.05,.91,.64),(1.95,0,0,.88,.65),(2.35,0,0,.77,.56),(2.65,0,.01,.63,.45),(2.95,0,.04,.51,.37),(3.30,0,.09,.42,.32),(3.55,0,.1,.34,.28)],GREEN,sides=96,steps=9)
    cylindrical_paint(body,samples,'Tyranitar_body',body_pattern)
    head,hs=loft('02_Upper head and muzzle',[(-.90,0,3.72,.19,.065),(-.76,0,3.75,.29,.12),(-.54,0,3.77,.36,.18),(-.20,0,3.75,.43,.275),(.18,0,3.65,.40,.32),(.42,0,3.61,.07,.10)],GREEN,axis='Y',sides=96,steps=9)
    cylindrical_paint(head,hs,'Tyranitar_face',head_pattern,axis='Y')
    # Flatten the central brow and snout into a broad armored plane; preserve
    # the authored UV placement while moving the small upper portion of each ring.
    for vertex in head.data.vertices:
        x,y,z=vertex.co
        cy=np.interp(y,hs[:,0],hs[:,2]);ry=max(.003,np.interp(y,hs[:,0],hs[:,4]))
        cosine=(z-cy)/ry
        if cosine>.65:
            t=min(1.0,(cosine-.65)/.35)
            vertex.co.z=cy+ry*(.65+.20*(2*t-t*t))
    head.data.update()
    loft('03_Lower open jaw',[(-.79,0,3.225,.21,.055),(-.60,0,3.23,.29,.085),(-.37,0,3.27,.32,.105),(-.10,0,3.39,.32,.15),(.16,0,3.50,.25,.17),(.26,0,3.49,.10,.09)],GREEN,axis='Y',sides=64,steps=8)
    mouth_bowl()
    # Crown and five paired rows of broad triangular dorsal armor.
    armor_spike('Central crown horn',(0,-.005,3.91),(0,.24,4.25),.20,.8)
    for s in (-1,1):
        armor_spike('Side crown horn',(s*.31,.03,3.88),(s*.60,.39,4.03),.14,.65)
        for i,(bx,by,z,tx,ty,tz,r) in enumerate([(.22,.25,3.57,.68,.66,3.80,.22),(.30,.35,3.13,.96,.82,3.40,.28),(.37,.44,2.69,1.12,.91,2.98,.30),(.43,.54,2.26,1.12,.99,2.48,.26),(.43,.57,1.96,.95,.94,2.08,.18)]):
            armor_plate(f'{s}_Dorsal armor {i+1}',(s*bx,by-.17,z+r),(s*bx,by-.17,z-r),(s*tx,ty,tz+.06),.11 if i<3 else .09)
        # Thin overlapping plates form the pointed lower breast carapace.
        breast_plate(s,samples)
    # Short strong arms terminate in three forward-facing claws.
    for s in (-1,1):
        label='L' if s<0 else 'R'
        parts=[c.tube(label+'_Short thick arm',[(s*.56,.0,2.70),(s*.69,-.075,2.54),(s*.83,-.23,2.415),(s*.90,-.405,2.385)],[.22,.205,.21,.19],GREEN,32,8),c.ell(label+'_Broad hand',(s*.90,-.43,2.385),(.225,.205,.16),GREEN)]
        c.union(label+'_05_Arm and hand',parts,GREEN,.015)
        for offset in (-.12,0,.12):
            c.cone(label+'_White hand claw',(s*.90+offset,-.56,2.375),(s*.90+offset*1.1,-.79,2.25),.060,IVORY)
        # The large thigh shell and its two black cavities remain separate editable armor.
        thigh,ts=loft(label+'_06_Armored thigh',[(.62,s*.66,0,.25,.27),(.83,s*.69,0,.40,.38),(1.10,s*.68,.01,.47,.43),(1.42,s*.60,.05,.43,.40),(1.68,s*.50,.07,.27,.27),(1.78,s*.45,.10,.09,.12)],GREEN,sides=80,steps=8)
        cylindrical_paint(thigh,ts,'Tyranitar_thigh_'+label,thigh_pattern(s),resolution=1024)
        shin=c.tube(label+'_Lower leg',[(s*.70,.04,.85),(s*.74,-.08,.48),(s*.76,-.16,.24)],[.255,.25,.28],GREEN,32,7)
        foot=c.ell(label+'_Heavy foot',(s*.76,-.28,.20),(.34,.46,.20),GREEN)
        c.union(label+'_07_Lower leg and foot',[shin,foot],GREEN,.015)
        for offset in (-.21,0,.21):
            c.cone(label+'_White toe claw',(s*.76+offset,-.56,.15),(s*.76+offset*1.16,-.85,.06),.092,IVORY)
    # Broad armored tail with four terminal blades around its tapered tip.
    tail=c.tube('08_Heavy tapering tail',[(0,.48,1.07),(.19,.97,.83),(.54,1.55,.64),(.90,2.08,.69),(1.17,2.48,.81),(1.40,2.69,.84)],[(.58,.51),(.48,.40),(.35,.29),(.24,.20),(.12,.105),.004],GREEN,48,9)
    for base,tip,r in [((.98,2.16,.75),(1.12,2.24,1.23),.16),((1.02,2.20,.66),(1.16,2.30,.27),.14),((.93,2.17,.72),(.63,2.47,.74),.13),((1.08,2.20,.73),(1.52,2.36,.75),.15)]:
        along=Vector((.10,.17,.02));point=Vector(base)
        armor_plate('Tail terminal blade',point-along,point+along,tip,.07)
    root=bpy.data.objects.new('root_Tyranitar',None);asset.objects.link(root)
    root['pokemon']='Tyranitar';root['korean']='마기라스';root['canonical_height_m']=2.0;root['reference']='https://www.pokemon.com/us/pokedex/tyranitar';root['design']='Hand-authored fan model; no extracted meshes'
    factor=2.0/4.25
    for obj in list(asset.objects):
        if obj.type!='MESH':continue
        uv_for_untextured(obj);obj.location*=factor;obj.scale*=factor;c.active(obj);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);obj.parent=root;obj['pokemon']='Tyranitar'
    return asset,studio,root


def stage(studio):
    scene=bpy.context.scene
    def move(obj,name,color):
        for col in list(obj.users_collection):col.objects.unlink(obj)
        studio.objects.link(obj);obj.name=name;obj.data.materials.append(c.material(color,.7))
    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=1.10,depth=.035,location=(0,.34,-.022))
    obj=bpy.context.object;move(obj,'Display plinth','D5DCC9');mod=obj.modifiers.new('Soft rim','BEVEL');mod.width=.015;mod.segments=3;c.apply(obj,mod)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.042));move(bpy.context.object,'Studio floor','E6E9E0')
    for name,pos,power,size,color in [('Soft key',(-4,-5,6),520,4,(1,.95,.87)),('Fill',(4,-2,3),250,3,(.86,.94,1)),('Rim',(1,4,5),450,3,(.95,1,.93))]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
        obj=bpy.data.objects.new(name,data);studio.objects.link(obj);obj.location=pos;obj.rotation_euler=(Vector((0,.2,1))-obj.location).to_track_quat('-Z','Y').to_euler()
    world=scene.world or bpy.data.worlds.new('World');scene.world=world;world.use_nodes=True;world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.53,.59,.49,1);world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.30
    data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);studio.objects.link(cam);data.type='ORTHO';scene.camera=cam
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.render.resolution_x=1600;scene.render.resolution_y=1600;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.10;scene.unit_settings.system='METRIC'
    return cam


def view(cam,pos,target,zoom):
    cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=zoom


def render(cam,draft=False):
    scene=bpy.context.scene
    views=[('preview',(3.5,-5.5,2.75),(0,.30,1.0),2.65),('front',(0,-5.5,1.1),(0,.15,1.0),2.55),('back',(3,5,2.75),(0,.35,1.0),2.80),('side',(5,0,1.2),(0,.4,1.0),2.80),('face',(2.6,-4.5,2.45),(0,-.08,1.73),.95)]
    if draft:scene.cycles.samples=12;scene.render.resolution_percentage=50;views=views[:2]
    for name,pos,target,zoom in views:
        view(cam,pos,target,zoom);scene.render.filepath=str(OUT/'renders'/('Tyranitar_'+name+('_draft' if draft else '')+'.png'));bpy.ops.render.render(write_still=True)
    if not draft:
        scene.view_layers[0].material_override=c.material('B6BFA8',.75);view(cam,(3.5,-5.5,2.75),(0,.30,1.0),2.65);scene.render.filepath=str(OUT/'renders'/'Tyranitar_clay.png');bpy.ops.render.render(write_still=True);scene.view_layers[0].material_override=None


if __name__=='__main__':
    asset,studio,root=build();cam=stage(studio);view(cam,(3.5,-5.5,2.75),(0,.30,1.0),2.65)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                space=area.spaces.active;space.region_3d.view_distance=3.4;space.region_3d.view_location=(0,.25,1.0);space.region_3d.view_rotation=cam.rotation_euler.to_quaternion();space.shading.type='MATERIAL';space.overlay.show_extras=False
    c.active(root);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Tyranitar.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in asset.objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.gltf(filepath=str(OUT/'Tyranitar.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=True)
    if '--no-render' not in sys.argv:render(cam,'--draft' in sys.argv)
    print('TYRANITAR_BUILD_OK',flush=True)
