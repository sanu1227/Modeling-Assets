"""Reopen the saved character, check real mesh/skin data and render a pose test."""
from pathlib import Path
import json
import math
import bpy
from mathutils import Vector

OUT=Path(__file__).resolve().parents[1]/"assets"/"Character"
bpy.ops.wm.open_mainfile(filepath=str(OUT/"Adventurer_Model_v001.blend"))
scene=bpy.context.scene
work=bpy.data.collections["03_Character_Work"]
body=bpy.data.objects["Body_Female_Edit"]
rig=bpy.data.objects["Adventurer_Rig"]
assert len(body.data.vertices)==13380
assert body.data.uv_layers and body.data.color_attributes.get("FaceTint")
assert len(rig.data.bones)>=50
weights=[sum(g.weight for g in v.groups) for v in body.data.vertices]
assert min(weights)>.999 and max(weights)<1.001
assert max(len(v.groups) for v in body.data.vertices)<=4
meshes=[o for o in work.objects if o.type=="MESH" and not o.hide_render and o.get("accessory")!="sword"]
assert len(meshes)>30
points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
assert all(math.isfinite(c) for p in points for c in p)
minimum=[min(p[i] for p in points) for i in range(3)]
maximum=[max(p[i] for p in points) for i in range(3)]
assert 1.65<maximum[2]-minimum[2]<1.9
assert minimum[2]>-.015
triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes)

graph=bpy.context.evaluated_depsgraph_get()
evaluated=body.evaluated_get(graph)
rest_mesh=evaluated.to_mesh()
rest=[v.co.copy() for v in rest_mesh.vertices]
evaluated.to_mesh_clear()
bone=rig.pose.bones["Forearm.L"]
bone.rotation_mode="XYZ"
bone.rotation_euler.x=math.radians(45)
bpy.context.view_layer.update()
evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
posed_mesh=evaluated.to_mesh()
posed=[v.co.copy() for v in posed_mesh.vertices]
evaluated.to_mesh_clear()
assert len(rest)==len(posed)
movement=max((a-b).length for a,b in zip(rest,posed))
assert movement>.01
assert all(math.isfinite(c) for p in posed for c in p)
scene.render.resolution_x=900
scene.render.resolution_y=1100
scene.render.filepath=str(OUT/"Adventurer_PoseCheck.png")
bpy.ops.render.render(write_still=True)
bone.rotation_euler=(0,0,0)
bpy.context.view_layer.update()
camera=scene.camera
camera.location=(4,0,.92)
camera.rotation_euler=(Vector((0,0,.92))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.ortho_scale=2.05
scene.render.filepath=str(OUT/"Adventurer_Side.png")
bpy.ops.render.render(write_still=True)
report={
    "passed":True,
    "blender_version":bpy.app.version_string,
    "file_reopened":True,
    "character_mesh_created":True,
    "visible_character_mesh_objects":len(meshes),
    "control_mesh_triangles":triangles,
    "bounds_min_m":minimum,
    "bounds_max_m":maximum,
    "body_vertices":len(body.data.vertices),
    "body_uv_layers":len(body.data.uv_layers),
    "bones":len(rig.data.bones),
    "body_weight_sums":[min(weights),max(weights)],
    "max_body_influences":max(len(v.groups) for v in body.data.vertices),
    "forearm_pose_changed_geometry":True,
    "pose_max_vertex_displacement_m":movement,
    "pose_all_vertices_finite":True,
    "engine_tested":False,
    "production_deformation_review_complete":False,
    "preview":"Adventurer_Preview.png",
    "face_preview":"Adventurer_Face.png",
    "pose_preview":"Adventurer_PoseCheck.png",
    "side_preview":"Adventurer_Side.png",
    "source":"MakeHuman CC0 core mesh and targets; original Blender modeling scripts",
}
(OUT/"Adventurer_Validation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("ADVENTURER_VALIDATION_OK",json.dumps(report))
