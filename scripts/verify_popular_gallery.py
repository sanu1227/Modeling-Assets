"""Verify the saved native gallery, appended mesh counts and overview framing."""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets'/'PokemonPopular'
source=OUT/'Pokemon_Popular.blend'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
manifest=json.loads((OUT/'gallery_manifest.json').read_text(encoding='utf8'))
scene=bpy.context.scene;graph=bpy.context.evaluated_depsgraph_get()
errors=[];items=[]
for item in manifest['models']:
    name=item['name'];col=bpy.data.collections.get('Pokemon_'+name)
    if col is None:
        errors.append('Missing native collection '+name);continue
    triangles=0;finite=True;projected=[];meshes=0
    for ob in col.all_objects:
        if ob.type!='MESH':continue
        meshes+=1;evaluated=ob.evaluated_get(graph);mesh=evaluated.to_mesh()
        mesh.calc_loop_triangles();triangles+=len(mesh.loop_triangles)
        coords=np.empty(len(mesh.vertices)*3,np.float64);mesh.vertices.foreach_get('co',coords)
        finite=finite and bool(np.isfinite(coords).all());evaluated.to_mesh_clear()
        for corner in ob.bound_box:
            p=world_to_camera_view(scene,scene.camera,ob.matrix_world@Vector(corner))
            projected.append((float(p.x),float(p.y),float(p.z)))
    framed=all(.005<=x<=.995 and .005<=y<=.995 and z>0 for x,y,z in projected)
    if triangles!=item['triangles']:errors.append('Triangle count changed in gallery: '+name)
    if not finite:errors.append('Non-finite geometry: '+name)
    if not framed:errors.append('Overview clips model: '+name)
    if not bpy.data.objects.get('Move_'+name):errors.append('Missing independent root: '+name)
    items.append({'name':name,'meshes':meshes,'triangles':triangles,'finite':finite,'overview_in_frame':framed})
for image in bpy.data.images:
    if image.source=='FILE' and not image.packed_file and not image.packed_files:
        errors.append('Unpacked image dependency: '+image.name)
for font in bpy.data.fonts:
    if font.filepath and font.filepath!='<builtin>' and not font.packed_file:
        errors.append('Unpacked font dependency: '+font.name)
if bpy.data.libraries:errors.append('Linked external Blender library remains')
if len(items)!=21:errors.append('Expected 21 native model collections')
if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:errors.append('Gallery modified during read-only verification')
report={'passed':not errors,'checked_at':datetime.now(timezone.utc).isoformat(),
        'source_sha256':digest,'models':items,'model_count':len(items),
        'total_triangles':sum(item['triangles'] for item in items),'errors':errors,
        'packed_images':len(bpy.data.images),'note':'Saved scene reopened and inspected; no interactive performance claim.'}
(OUT/'gallery_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'passed':not errors,'model_count':len(items),'errors':errors},ensure_ascii=False),flush=True)
if errors:raise SystemExit(1)
