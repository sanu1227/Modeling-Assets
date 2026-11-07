import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector,Matrix

args=sys.argv[sys.argv.index('--')+1:]
source=Path(args[0]);label=args[1];out=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
if source.is_dir():
    for path in sorted(source.glob('*.obj')):
        bpy.ops.wm.obj_import(filepath=str(path),forward_axis='Y',up_axis='Z')
elif source.suffix.lower()=='.stl':
    bpy.ops.wm.stl_import(filepath=str(source))
else:
    bpy.ops.wm.obj_import(filepath=str(source),forward_axis='Y',up_axis='Z')
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
if label=='martinjario':
    turn=Matrix.Rotation(math.pi/2,4,'X')
    for o in objects:o.matrix_world=turn@o.matrix_world
bpy.context.view_layer.update()
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
low=Vector(tuple(min(p[i] for p in points) for i in range(3)))
high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
center=(low+high)/2;scale=2.8/max(high-low)
mat=bpy.data.materials.new('Inspection clay');mat.diffuse_color=(.55,.50,.40,1)
mat.use_nodes=True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.25,.22,.18,1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.8
for o in objects:
    o.location-=center;o.location*=scale;o.scale*=scale
    o.data.materials.clear();o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
report={'source':str(source),'bounds_original':[list(low),list(high)],'vertices':sum(len(o.data.vertices) for o in objects),'faces':sum(len(o.data.polygons) for o in objects)}
(out/(label+'_inspection.json')).write_text(json.dumps(report,indent=2))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
world=bpy.data.worlds.new('gray');scene.world=world;world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.08,.08,.08,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.5
for name,loc,power in [('Key',(-3,-4,5),800),('Fill',(4,-1,2),500),('Back',(1,4,4),600)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=4
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc
    o.rotation_euler=(-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',d);scene.collection.objects.link(cam);scene.camera=cam
d.type='ORTHO';d.ortho_scale=3.7
for suffix,loc in [('front',(0,-6,.3)),('quarter',(4,-6,1.2)),('back',(0,6,.3))]:
    cam.location=loc;cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(out/(label+'_'+suffix+'.png'));bpy.ops.render.render(write_still=True)
