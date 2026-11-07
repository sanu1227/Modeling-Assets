import sys,json,math
from pathlib import Path
import bpy,bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
from black_oath_skull_adornments_v4 import build_adornments
from black_oath_skull_v4 import build_skull
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/PirateShip/BlackOath.blend'))
for o in list(bpy.context.scene.objects):
    bpy.data.objects.remove(o,do_unlink=True)
collection=bpy.data.collections.new('Adornment_preview')
bpy.context.scene.collection.children.link(collection)
skull_objects=build_skull(collection) if '--combined' in sys.argv else []
objects=build_adornments(collection)
bpy.context.view_layer.update()
graph=bpy.context.evaluated_depsgraph_get()
errors=[]
triangles=0
components={}
low=Vector((math.inf,)*3)
high=Vector((-math.inf,)*3)
for o in objects:
    eo=o.evaluated_get(graph);d=eo.to_mesh();d.calc_loop_triangles()
    triangles+=len(d.loop_triangles)
    bm=bmesh.new();bm.from_mesh(d)
    if 'Crossbone_' in o.name:
        pending=set(bm.verts)
        sizes=[]
        while pending:
            stack=[pending.pop()]
            size=0
            while stack:
                vert=stack.pop();size+=1
                for edge in vert.link_edges:
                    other=edge.other_vert(vert)
                    if other in pending:
                        pending.remove(other);stack.append(other)
            sizes.append(size)
        components[o.name]=sizes
        if len(sizes)!=1:errors.append({'name':o.name,'components':sizes})
    nonmanifold=sum(not e.is_manifold for e in bm.edges)
    winding=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
    degenerate=sum(t.area<1e-11 for t in d.loop_triangles)
    if nonmanifold or winding or degenerate or not d.uv_layers:
        errors.append({'name':o.name,'nonmanifold':nonmanifold,'winding':winding,'degenerate':degenerate,'uv':bool(d.uv_layers)})
    for v in d.vertices:
        p=eo.matrix_world@v.co
        for i in range(3):
            low[i]=min(low[i],p[i]);high[i]=max(high[i],p[i])
    bm.free();eo.to_mesh_clear()
report={'passed':not errors,'objects':len(objects),'triangles':triangles,'bounds':[list(low),list(high)],'bone_connected_components':components,'errors':errors}
(OUT/'adornment_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
try:
    p=bpy.context.preferences.addons['cycles'].preferences
    p.compute_device_type='OPTIX';p.get_devices()
    for d in p.devices:d.use=d.type!='CPU'
    scene.cycles.device='GPU'
except Exception:pass
world=bpy.data.worlds.new('Adornment_preview_world');world.use_nodes=True
scene.world=world;world.node_tree.nodes['Background'].inputs[0].default_value=(.11,.135,.16,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.35
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.1
scene.render.resolution_x=1400;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
center=Vector((-29.2,0,9.35))
for name,loc,power,size,color in [('Key',(-33,-4,13),1800,4,(1,.86,.65)),
                               ('Fill',(-32,4,9),850,4,(.64,.79,1)),
                               ('Rim',(-27,2,12),1700,3,(1,.68,.32))]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=loc
    o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',data);scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=4.75
for label,loc in [('front',(-36,0,9.6)),('three_quarter',(-36,-4,10.8))]:
    cam.location=loc;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/('adornment_'+label+'.png'))
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'adornment_preview.blend'))
assert not errors,report

