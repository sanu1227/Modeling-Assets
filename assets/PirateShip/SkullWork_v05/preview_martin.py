import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix

out=Path(__file__).resolve().parent
root=out.parents[2]
source=root/'assets/PirateShip/Source/Skull_v05/martinjario_skull.stl'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.stl_import(filepath=str(source))
skull=bpy.context.object;skull.name='SkullV5_Anatomical_Relic'
rotation=Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Rotation(math.pi/2,4,'X')
for v in skull.data.vertices:v.co=rotation@v.co
points=[v.co for v in skull.data.vertices]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
scale=2.45/(hi.z-lo.z);center=Vector((-29.2,0,9.37))
for v in skull.data.vertices:v.co=(v.co-(lo+hi)/2)*scale
skull.location=center;skull.data.update()
for p in skull.data.polygons:p.use_smooth=True
bm=bmesh.new();bm.from_mesh(skull.data)
topology={'vertices':len(bm.verts),'faces':len(bm.faces),'boundary_edges':sum(e.is_boundary for e in bm.edges),'wire_edges':sum(e.is_wire for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'noncontiguous_edges':sum(e.is_manifold and not e.is_contiguous for e in bm.edges),'components':[]}
remaining=set(bm.verts)
while remaining:
    todo=[remaining.pop()];verts=set(todo)
    while todo:
        v=todo.pop()
        for e in v.link_edges:
            other=e.other_vert(v)
            if other in remaining:remaining.remove(other);verts.add(other);todo.append(other)
    edges={e for v in verts for e in v.link_edges}
    topology['components'].append({'vertices':len(verts),'bounds_min':[min(v.co[i] for v in verts) for i in range(3)],'bounds_max':[max(v.co[i] for v in verts) for i in range(3)],'boundaries':sum(e.is_boundary for e in edges)})
topology['components'].sort(key=lambda item:-item['vertices'])
bm.free();(out/'martin_topology.json').write_text(json.dumps(topology,indent=2))
clay=bpy.data.materials.new('SkullV5_Neutral_Clay');clay.use_nodes=True
p=clay.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.40,.40,.40,1);p.inputs['Roughness'].default_value=.73
skull.data.materials.clear();skull.data.materials.append(clay)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    scene.cycles.device='GPU'
except Exception:pass
scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.20,.23,.26,1);scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.35
scene.view_settings.view_transform='AgX'
def aim(o,point):o.rotation_euler=(Vector(point)-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,power,size,color in [('Key',(-33,-4,13),1500,4,(1,.9,.78)),('Fill',(-32,4,10),700,4,(.7,.83,1)),('Rim',(-27,2,12),1300,3,(1,.91,.8))]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=loc;aim(o,center)
camera_data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',camera_data);bpy.context.collection.objects.link(camera);scene.camera=camera
camera_data.type='ORTHO';camera_data.ortho_scale=3.25
for label,loc in [('front',(-36,0,9.45)),('three_quarter',(-35,-5,10.3)),('profile',(-29.2,-7,9.45))]:
    camera.location=loc;aim(camera,center);scene.render.filepath=str(out/f'martin_clay_{label}.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'martin_anatomy_preview.blend'))
print('MARTIN_TOPOLOGY',json.dumps(topology))
