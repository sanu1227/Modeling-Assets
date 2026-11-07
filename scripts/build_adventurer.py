"""Editable female adventurer using CC0 MakeHuman topology and original accessories."""
from pathlib import Path
from collections import defaultdict
import json
import math
import sys

import bpy
import bmesh
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "Character"
SRC = OUT / "Source" / "MakeHuman"
sys.path.insert(0, str(ROOT / "scripts"))


def obj_data(path):
    vertices, uvs, faces, groups = [], [], [], []
    group = "body"
    for line in path.read_text(encoding="utf-8").splitlines():
        a = line.split()
        if not a:
            continue
        if a[0] == "v":
            vertices.append(Vector(tuple(map(float, a[1:4]))))
        elif a[0] == "vt":
            uvs.append(tuple(map(float, a[1:3])))
        elif a[0] == "g":
            group = a[1]
        elif a[0] == "f":
            faces.append([(int(w.split('/')[0])-1, int(w.split('/')[1])-1 if '/' in w and w.split('/')[1] else None) for w in a[1:]])
            groups.append(group)
    return vertices, uvs, faces, groups


def material(name, color, roughness=.5, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return mat


def make_mesh(name, vertices, uvs, faces, collection, mat):
    used = sorted({i for face in faces for i, _ in face})
    remap = {old: new for new, old in enumerate(used)}
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([vertices[i] for i in used], [], [[remap[i] for i, _ in f] for f in faces])
    mesh.update()
    if uvs:
        layer = mesh.uv_layers.new(name="UVMap")
        for polygon, face in zip(mesh.polygons, faces):
            for loop, (_, uv) in zip(polygon.loop_indices, face):
                if uv is not None:
                    layer.data[loop].uv = uvs[uv]
    ids = mesh.attributes.new("source_vertex_id", "INT", "POINT")
    for datum, old in zip(ids.data, used):
        datum.value = old
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    for p in mesh.polygons:
        p.use_smooth = True
    return obj


def subdiv(obj, level=1):
    modifier = obj.modifiers.new("Surface refinement", "SUBSURF")
    modifier.levels = level
    modifier.render_levels = level


def curve_object(name, points, radius, mat, collection):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    curve.resolution_u = 12
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points)-1)
    for point, co in zip(spline.bezier_points, points):
        point.co = co
        point.handle_left_type = point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def bind_character(body, collection, joints):
    """A simple editable FK skeleton; fine deformation cleanup remains an artist task."""
    armature=bpy.data.armatures.new("Adventurer_Skeleton")
    rig=bpy.data.objects.new("Adventurer_Rig",armature)
    bpy.data.collections["04_Rig"].objects.link(rig)
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode="EDIT")
    def bone(name,head,tail,parent=None,deform=True):
        b=armature.edit_bones.new(name)
        b.head,b.tail=head,tail
        b.use_deform=deform
        if parent:
            b.parent=armature.edit_bones[parent]
        return b
    bone("Root",(0,0,0),(0,0,.2),deform=False)
    bone("Hips",joints["joint-pelvis"],joints["joint-spine-4"],"Root")
    previous="Hips"
    for i,(a,b) in enumerate(((4,3),(3,2),(2,1)),1):
        name=f"Spine{i}"
        bone(name,joints[f"joint-spine-{a}"],joints[f"joint-spine-{b}"],previous)
        previous=name
    bone("Chest",joints["joint-spine-1"],joints["joint-neck"],previous)
    bone("Neck",joints["joint-neck"],joints["joint-head"],"Chest")
    bone("Head",joints["joint-head"],joints["joint-head-2"],"Neck")
    for side in ("l","r"):
        s=side.upper()
        j=lambda key:joints[f"joint-{side}-{key}"]
        bone(f"Clavicle.{s}",j("clavicle"),j("shoulder"),"Chest")
        bone(f"UpperArm.{s}",j("shoulder"),j("elbow"),f"Clavicle.{s}")
        bone(f"Forearm.{s}",j("elbow"),j("hand"),f"UpperArm.{s}")
        bone(f"Hand.{s}",j("hand"),j("finger-3-1"),f"Forearm.{s}")
        for finger in range(1,6):
            parent=f"Hand.{s}"
            for segment in range(1,4):
                name=f"Finger{finger}_{segment}.{s}"
                bone(name,j(f"finger-{finger}-{segment}"),j(f"finger-{finger}-{segment+1}"),parent)
                parent=name
        bone(f"Thigh.{s}",j("upper-leg"),j("knee"),"Hips")
        bone(f"Shin.{s}",j("knee"),j("ankle"),f"Thigh.{s}")
        bone(f"Foot.{s}",j("ankle"),j("foot-1"),f"Shin.{s}")
        bone(f"Toe.{s}",j("foot-1"),j("foot-2"),f"Foot.{s}")
    bpy.ops.object.mode_set(mode="OBJECT")
    body.select_set(True)
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    # Keep a small normalized influence set for the initial skin binding.
    missing=0
    for v in body.data.vertices:
        weights=sorted([(g.group,g.weight) for g in v.groups if g.weight>0.00001],key=lambda g:-g[1])[:4]
        total=sum(w for _,w in weights)
        if total == 0:
            missing+=1
            continue
        for group_index in [g.group for g in v.groups]:
            body.vertex_groups[group_index].remove([v.index])
        for group,w in weights:
            body.vertex_groups[group].add([v.index],w/total,"REPLACE")
    assert missing==0, f"Unweighted body vertices: {missing}"
    tree=KDTree(len(body.data.vertices))
    for v in body.data.vertices:
        tree.insert(body.matrix_world@v.co,v.index)
    tree.balance()
    for obj in list(collection.objects):
        if obj == body or obj.get("accessory")=="sword" or obj.type not in {"MESH","CURVE"}:
            continue
        if obj.type=="CURVE":
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active=obj
            bpy.ops.object.convert(target="MESH")
            obj=bpy.context.object
        groups={g.index:obj.vertex_groups.new(name=g.name) for g in body.vertex_groups}
        is_head=obj.get("part")=="Hair" or obj.name.startswith(("Eyes_","Iris_","Brow","Lash","Eyeliner","Catchlight","Eye_glint_","Upper_lid_"))
        head_group=obj.vertex_groups.get("Head")
        for v in obj.data.vertices:
            if is_head:
                head_group.add([v.index],1,"REPLACE")
            else:
                _,idx,_=tree.find(obj.matrix_world@v.co)
                for g in body.data.vertices[idx].groups:
                    groups[g.group].add([v.index],g.weight,"REPLACE")
        mod=obj.modifiers.new("Character skin binding","ARMATURE")
        mod.object=rig
    rig.show_in_front=True
    rig["binding_note"]="Basic FK rig and initial weights; extreme pose and garment collision cleanup pending"
    rig.hide_set(True)
    return rig


bpy.ops.wm.open_mainfile(filepath=str(OUT / "Character_References_v003.blend"))
scene = bpy.context.scene
work = bpy.data.collections["03_Character_Work"]
source_collection = bpy.data.collections["02_Source_High"]
source_collection.hide_render = True
materials = {
    "skin": material("Skin warm", (.51, .275, .173), .47),
    "lips": material("Rose lips", (.39, .085, .078), .38),
    "cloth": material("Teal woven shirt", (.047, .145, .16), .72),
    "pants": material("Slate trousers", (.055, .066, .085), .76),
    "leather": material("Chestnut leather", (.20, .075, .029), .5),
    "leather_dark": material("Leather edges", (.095, .029, .012), .6),
    "thread": material("Leather stitching", (.38, .23, .1), .66),
    "metal": material("Antique brass", (.56, .31, .095), .28, .75),
    "blade": material("Steel", (.48, .57, .64), .24, .9),
    "hair": material("Chestnut hair", (.075, .024, .012), .43),
    "dark": material("Hair shadows", (.024, .007, .004), .5),
    "hair_highlight": material("Hair warm strands", (.13, .047, .018), .42),
    "eyes": material("Eye sclera", (.88, .88, .83), .19),
    "iris": material("Hazel iris", (.145, .082, .023), .27),
    "limbal": material("Dark limbal ring", (.029, .016, .008), .27),
    "pupil": material("Pupils", (.002, .003, .004), .13),
}
skin_shader = materials["skin"].node_tree.nodes.get("Principled BSDF")
skin_shader.inputs["Subsurface Weight"].default_value = .08
skin_shader.inputs["Subsurface Radius"].default_value = (1, .45, .25)
skin_shader.inputs["Subsurface Scale"].default_value = .035

native, uv, faces, groups = obj_data(SRC / "base.obj")
target_weights = {
    "asian-female-young": .55, "caucasian-female-young": .45,
    "female-young-averagemuscle-averageweight-idealproportions": .28,
    "universal-female-young-averagemuscle-minweight": .10,
    "l-eye-scale-incr": .32, "r-eye-scale-incr": .32,
    "chin-width-decr": .12,
}
for name, weight in target_weights.items():
    for line in (SRC / (name + ".target")).read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        row = line.split()
        native[int(row[0])] += Vector(tuple(map(float, row[1:4]))) * weight

group_ids = defaultdict(set)
for face, group in zip(faces, groups):
    group_ids[group].update(i for i, _ in face)
native_joints = {g: sum((native[i] for i in indices), Vector()) / len(indices) for g, indices in group_ids.items() if g.startswith("joint-")}
body_indices = group_ids["body"]
floor = min(native[i].y for i in body_indices)
top = max(native[i].y for i in body_indices)
scale = (1.71 - .025) / (top - floor)


def initial_transform(point):
    p = Vector((point.x * scale, -point.z * scale, (point.y-floor)*scale + .025))
    # Rotate arms slightly down to a relaxed A-pose; preserve torso and neck.
    shoulder = native_joints["joint-l-shoulder" if point.x >= 0 else "joint-r-shoulder"]
    shoulder = Vector((shoulder.x*scale, -shoulder.z*scale, (shoulder.y-floor)*scale+.025))
    weight = max(0, min(1, (abs(p.x) - abs(shoulder.x) + .015) / .06))
    weight = weight*weight*(3-2*weight)
    if weight and (p.z > 1.16 or abs(p.x) > .24):
        a = math.radians(10) * (1 if p.x > 0 else -1) * weight
        q = p-shoulder
        p.x = shoulder.x + q.x*math.cos(a)+q.z*math.sin(a)
        p.z = shoulder.z - q.x*math.sin(a)+q.z*math.cos(a)
    return p


arm_alignments = []
for side, sign in (("l",1),("r",-1)):
    elbow = initial_transform(native_joints[f"joint-{side}-elbow"])
    wrist = initial_transform(native_joints[f"joint-{side}-hand"])
    shoulder = initial_transform(native_joints[f"joint-{side}-shoulder"])
    desired = elbow-shoulder
    desired.y = 0
    rotation = (wrist-elbow).rotation_difference(desired)
    arm_alignments.append((sign, elbow, rotation))


def transform(point):
    p=initial_transform(point)
    for sign, elbow, rotation in arm_alignments:
        if p.x*sign > 0 and p.z > .82:
            w=max(0,min(1,(abs(p.x)-abs(elbow.x)+.025)/.07))
            w=w*w*(3-2*w)
            if w:
                p=p.lerp(elbow+rotation@(p-elbow),w)
    return p


coords = [transform(p) for p in native]
joints = {g: sum((coords[i] for i in indices), Vector()) / len(indices) for g, indices in group_ids.items() if g.startswith("joint-")}
body_faces = [f for f,g in zip(faces,groups) if g == "body"]
body = make_mesh("Body_Female_Edit", coords, uv, body_faces, work, materials["skin"])
subdiv(body, 1)
helper = make_mesh("MH_Tights_Source", coords, uv, [f for f,g in zip(faces,groups) if g == "helper-tights"], source_collection, materials["cloth"])
helper.hide_set(True)
helper.hide_render = True
body["source"] = "MakeHuman hm08 CC0 core mesh; Source/MakeHuman/sourceurls.txt"
scene["joints_json"] = json.dumps({k:list(v) for k,v in joints.items()})

# Deform the CC0 eye mesh using its documented barycentric attachment map.
eye_native, eye_uv, eye_faces, _ = obj_data(SRC / "high-poly.obj")
eye_map = []
mapping = False
eye_scale = Vector((abs(native[5399].x-native[11998].x)/1.6482, abs(native[791].y-native[881].y)/2.7213, abs(native[962].z-native[5320].z)/2.2795))
for line in (SRC / "high-poly.mhclo").read_text().splitlines():
    if line.startswith("verts "):
        mapping = True
        continue
    if mapping:
        row = line.split()
        if len(row) != 9 or not row[0].isdigit():
            if eye_map:
                break
            continue
        ids = list(map(int,row[:3]))
        weights = list(map(float,row[3:6]))
        offset = Vector(tuple(map(float,row[6:9])))
        p = sum((native[i]*w for i,w in zip(ids,weights)),Vector())
        p += Vector(tuple(offset[i]*eye_scale[i] for i in range(3)))
        eye_map.append(transform(p))
assert len(eye_map) == len(eye_native), (len(eye_map),len(eye_native))
eyes = make_mesh("Eyes_Sclera", eye_map, eye_uv, eye_faces, work, materials["eyes"])
subdiv(eyes, 1)

for side in ("l", "r"):
    center = joints[f"joint-{side}-eye"]
    near = [v for v in eye_map if v.x*center.x > 0]
    radius = max(v.z for v in near)-center.z
    front = min(v.y for v in near)
    r = radius * .55
    iris_v, iris_f = [], []
    for j in range(8):
        rho = r * j / 7
        for k in range(48):
            angle=2*math.pi*k/48
            iris_v.append(Vector((center.x+rho*math.cos(angle), front + radius-math.sqrt(max(0,radius*radius-rho*rho))-.0006, center.z+rho*math.sin(angle))))
    for j in range(7):
        for k in range(48):
            iris_f.append([(j*48+k,None),((j+1)*48+k,None),((j+1)*48+(k+1)%48,None),(j*48+(k+1)%48,None)])
    iris = make_mesh(f"Iris_{side}",iris_v,[],iris_f,work,materials["iris"])
    iris.data.materials.append(materials["pupil"])
    iris.data.materials.append(materials["limbal"])
    for p in iris.data.polygons:
        ring=p.index//48
        p.material_index = 1 if ring<3 else (2 if ring==6 else 0)
    bm=bmesh.new()
    bm.from_mesh(iris.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bm.to_mesh(iris.data)
    bm.free()

# Baseline is saved separately for independent clothing development.
base_report = {
    "head_top":1.71,
    "chin_z":joints["joint-jaw"].z,
    "head_width":max(coords[i].x for i in body_indices if coords[i].z>joints["joint-jaw"].z)*2,
    "head_depth":max(coords[i].y for i in body_indices if coords[i].z>joints["joint-jaw"].z)-min(coords[i].y for i in body_indices if coords[i].z>joints["joint-jaw"].z),
    "center_y":(max(coords[i].y for i in body_indices if coords[i].z>joints["joint-jaw"].z)+min(coords[i].y for i in body_indices if coords[i].z>joints["joint-jaw"].z))/2,
    "joints": {k:list(v) for k,v in joints.items()},
}
(OUT / "Source" / "Body_Landmarks.json").write_text(json.dumps(base_report,indent=2),encoding="utf-8")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Source" / "Base_Work.blend"))
print("BASE_BODY_OK",json.dumps({k:v for k,v in base_report.items() if k!='joints'}))

if "--base-only" in sys.argv:
    raise SystemExit(0)

from character_hair import build_hair
build_hair(base_report["head_top"],base_report["chin_z"],base_report["head_width"],base_report["head_depth"],base_report["center_y"],materials,work)
from character_face import build_face
build_face(body,joints,materials,work)
from character_clothing import build_clothes
build_clothes(helper,body,joints,materials,work)
from character_accessories import build_accessories
waist=[v.co for v in body.data.vertices if abs(v.co.z-1.06)<.008 and abs(v.co.x)<.18]
rx=max(abs(v.x) for v in waist)+.012
ry=(max(v.y for v in waist)-min(v.y for v in waist))/2+.012
cy=(max(v.y for v in waist)+min(v.y for v in waist))/2
build_accessories(1.06,rx,ry,cy,materials,work)
for obj in work.objects:
    if obj.get("accessory")=="sword":
        obj.hide_render=True

rig=bind_character(body,work,joints)

# Lighting and cameras are saved with the editable model.
studio=bpy.data.collections["05_Studio"]
for obj in studio.objects:
    if obj.type == "LIGHT":
        obj.data.energy *= .5
floor_mat=material("Studio floor",(.055,.071,.09),.8)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0))
floor_obj=bpy.context.object
floor_obj.name="Studio_Ground"
for col in list(floor_obj.users_collection):
    col.objects.unlink(floor_obj)
studio.objects.link(floor_obj)
floor_obj.data.materials.append(floor_mat)
scene.render.engine="CYCLES"
try:
    preferences=bpy.context.preferences.addons['cycles'].preferences
    preferences.compute_device_type='OPTIX'
    preferences.get_devices()
    for device in preferences.devices:
        device.use=device.type!='CPU'
    if any(d.use for d in preferences.devices):
        scene.cycles.device='GPU'
except Exception as exc:
    print('GPU fallback:',exc)
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=900
scene.render.resolution_y=1100
scene.render.resolution_percentage=100
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(.13,.16,.21,1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.35
camera=scene.camera
camera.location=(2.1,-5.2,2.0)
camera.rotation_euler=(Vector((0,0,.91))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.ortho_scale=2.1
scene.render.filepath=str(OUT/"Adventurer_Preview.png")
scene["stage"]="Editable 3D character model; deformation and engine delivery pending"
for name in ("Character_Design.txt","Character_Prep.txt","Model_Readme.txt"):
    previous=bpy.data.texts.get(name)
    if previous:
        bpy.data.texts.remove(previous)
    bpy.data.texts.load(str(OUT/name))
bpy.ops.object.select_all(action="DESELECT")
body.hide_set(False)
body.select_set(True)
bpy.context.view_layer.objects.active=body
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=="VIEW_3D":
            area.spaces.active.region_3d.view_rotation=camera.rotation_euler.to_quaternion()
            area.spaces.active.region_3d.view_location=(0,0,.9)
            area.spaces.active.region_3d.view_distance=2.6
            area.spaces.active.shading.type="MATERIAL"
            area.spaces.active.overlay.show_extras=False
            area.spaces.active.overlay.show_relationship_lines=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Adventurer_Model_v001.blend"))
bpy.ops.render.render(write_still=True)
camera.location=(0,-4,1.61)
camera.rotation_euler=(Vector((0,-.04,1.61))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.ortho_scale=.43
scene.render.resolution_x=800
scene.render.resolution_y=800
scene.render.filepath=str(OUT/"Adventurer_Face.png")
bpy.ops.render.render(write_still=True)
print("ADVENTURER_MODEL_RENDERED")
