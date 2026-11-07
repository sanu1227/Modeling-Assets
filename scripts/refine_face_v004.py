"""Preserve the approved face features while cleaning projected skin and eyes."""
import math
import bpy


def _smooth(t):
    t=max(0.0,min(1.0,t))
    return t*t*(3-2*t)


def _feature(x,z,cx,cz,rx,rz):
    distance=math.hypot((x-cx)/rx,(z-cz)/rz)
    return 1-_smooth((distance-.65)/.65)


def refine_face(head, eyes, body, collection):
    """Operate on loaded v003 objects; create no files and leave hair untouched."""
    if head.get('FaceCleanupV004'):
        return {'already_applied':True}
    skin=(.68,.37,.245,1)
    face=head.data.materials[0]
    face.name='Face_SoftFeatureProjection_v004'
    nodes=face.node_tree.nodes
    for node in nodes:
        if node.type=='MIX_RGB':node.inputs[1].default_value=skin
    shader=nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value=.56
    shader.inputs['Subsurface Weight'].default_value=.035
    shader.inputs['Subsurface Scale'].default_value=.010
    face.diffuse_color=skin
    mask=head.data.color_attributes['ReferenceBlend']
    changed=0
    for vertex,datum in zip(head.data.vertices,mask.data):
        x,y,z=vertex.co
        front=_smooth((.015-y)/.055)*_smooth((z-1.505)/.025)
        base=0.0
        eyes_mask=max(_feature(x,z,-.043,1.608,.025,.0125),_feature(x,z,.017,1.612,.025,.0125))
        brows=max(_feature(x,z,-.043,1.631,.031,.011),_feature(x,z,.017,1.635,.031,.011))
        nose=.92*_feature(x,z,-.012,1.576,.018,.025)
        mouth=_feature(x,z,-.012,1.548,.027,.013)
        weight=max(base,eyes_mask,brows,nose,mouth)*front
        datum.color=(weight,weight,weight,1)
        # Close the remaining 0.29mm central slit without moving the smile.
        line=1.548005+.065*(x+.012)
        lip_weight=(1-_smooth((abs(x+.012)-.017)/.015))*_smooth((-.049-y)/.014)
        lip_weight*=1-_smooth((abs(z-line)-.006)/.010)
        delta=-.00014*math.tanh((z-line)/.0002)*lip_weight
        if abs(delta)>1e-9:
            vertex.co.z+=delta;changed+=1
    head.data.update()

    # Scope the new colour to the face/neck; forearm and clothing materials stay intact.
    neck_skin=bpy.data.materials['Body_Skin_Refined'].copy()
    neck_skin.name='Face_Neck_Skin_v004';neck_skin.diffuse_color=skin
    ns=neck_skin.node_tree.nodes.get('Principled BSDF')
    ns.inputs['Base Color'].default_value=skin
    ns.inputs['Roughness'].default_value=.56
    ns.inputs['Subsurface Weight'].default_value=.035
    ns.inputs['Subsurface Scale'].default_value=.010
    for i,mat in enumerate(head.data.materials):
        if mat and mat.name.startswith('Body_Skin_Refined'):head.data.materials[i]=neck_skin

    # Keep the closed ear topology and its alignment to the fitted hair.
    # Warm cartilage shading softens cavities without changing the outer rim.
    ear_material=neck_skin.copy();ear_material.name='Ear_WarmCartilage_v004'
    es=ear_material.node_tree.nodes.get('Principled BSDF')
    es.inputs['Roughness'].default_value=.65
    es.inputs['Subsurface Weight'].default_value=.12
    es.inputs['Subsurface Scale'].default_value=.008
    es.inputs['Emission Color'].default_value=(.40,.16,.08,1)
    es.inputs['Emission Strength'].default_value=.045
    ear_tint=head.data.color_attributes.new(name='EarTintV004',type='FLOAT_COLOR',domain='POINT')
    ear_vertices=0
    for vertex,datum in zip(head.data.vertices,ear_tint.data):
        x,y,z=vertex.co
        ear_weight=_smooth((x-.045)/.014)*_smooth((y+.004)/.018)
        ear_weight*=_smooth((z-1.558)/.012)*(1-_smooth((z-1.626)/.012))
        inner=math.exp(-((y-.024)/.015)**2-((z-1.597)/.016)**2)
        amount=.18*inner*ear_weight
        datum.color=tuple(a*(1-amount)+b*amount for a,b in zip(skin[:3],(.66,.26,.20)))+(1,)
        if ear_weight>0:
            ear_vertices+=1
    ear_attr=ear_material.node_tree.nodes.new('ShaderNodeVertexColor');ear_attr.layer_name=ear_tint.name
    ear_material.node_tree.links.new(ear_attr.outputs['Color'],es.inputs['Base Color'])
    head.data.materials.append(ear_material);ear_slot=len(head.data.materials)-1
    for polygon in head.data.polygons:
        points=[head.data.vertices[i].co for i in polygon.vertices]
        if all(p.x>.050 and p.y>-.003 and 1.561<p.z<1.637 for p in points):
            polygon.material_index=ear_slot
    head.data.update()
    for mat in body.data.materials:
        if mat and mat.name.startswith('Neck_Chest_ContinuousSkin'):
            for node in mat.node_tree.nodes:
                if node.type=='MIX_RGB':node.inputs[2].default_value=skin
                elif node.type=='MATH' and node.operation=='MULTIPLY' and abs(node.inputs[1].default_value-.06)<1e-6:
                    node.inputs[1].default_value=.035
                elif node.type=='MATH' and node.operation=='MULTIPLY_ADD' and abs(node.inputs[2].default_value-.73)<1e-6:
                    node.inputs[1].default_value=-.17
    # Match the extension's shading to the retained torso at the overlap root.
    group=head.vertex_groups.new(name='Neck_ShadingBlend_v004')
    for vertex in head.data.vertices:
        weight=1-_smooth((vertex.co.z-1.426)/.025)
        if weight>0:group.add([vertex.index],weight,'REPLACE')
    modifier=head.modifiers.new('Continuous neck shading v004','DATA_TRANSFER')
    modifier.object=body;modifier.use_loop_data=True
    modifier.data_types_loops={'CUSTOM_NORMAL'}
    modifier.loop_mapping='POLYINTERP_NEAREST'
    modifier.vertex_group=group.name
    head['FaceCleanupV004']=True
    return {'lip_vertices_refined':changed,'ear_vertices_tinted':ear_vertices,'skin_color_linear':list(skin[:3]),'feature_mask':'eyes brows nose lips retained; clean cheek and forehead skin','eyes_sharpened':False,'neck_normal_blend':True}
