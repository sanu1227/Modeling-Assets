"""Organic crossbones and braided pirate jewelry; no scene/file side effects."""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector


def build_adornments(collection, center=(-29.2, 0, 9.37)):
    """Return only SkullV3_* meshes. Front of the figurehead points toward -X."""
    center=Vector(center)
    made=[]

    def material(name,color,rough=.65,metal=0):
        mat=bpy.data.materials.new('SkullV3_Adornment_'+name)
        mat.use_nodes=True
        mat.diffuse_color=(*color,1)
        p=mat.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value=(*color,1)
        p.inputs['Roughness'].default_value=rough
        p.inputs['Metallic'].default_value=metal
        return mat

    bone=material('Weathered_bone',(.34,.245,.12),.76,.12)
    gold=material('Aged_gold',(.27,.15,.045),.43,.78)
    rope=material('Braided_dark_cord',(.025,.018,.012),.92)
    teal=material('Turquoise',(.015,.16,.145),.40,.12)
    red=material('Garnet',(.21,.018,.009),.34,.18)
    amber=material('Amber',(.38,.13,.017),.38,.12)
    ivory=material('Ivory_beads',(.38,.30,.18),.62,.08)
    dark=material('Obsidian_beads',(.015,.022,.029),.32,.25)
    # Portable, packed stained-bone color. Fine bump remains a Blender accent.
    size=512
    v,u=np.mgrid[0:size,0:size].astype(np.float32)/size
    random=np.random.default_rng(771)
    stain=(.22*np.sin(u*math.tau*3+np.sin(v*math.tau*5))
           +.12*np.cos(v*math.tau*11-u*math.tau*4))
    stain += .09*np.sin(u*math.tau*17+v*math.tau*13)*np.sin(v*math.tau*8)
    for _ in range(15):
        cu,cv=random.random(2)
        ru,rv=random.uniform(.025,.12,2)
        stain -= random.uniform(.06,.22)*np.exp(-((u-cu)/ru)**2-((v-cv)/rv)**2)
    value=np.clip(1+stain+random.normal(0,.035,(size,size)),.36,1.30)
    rgba=np.ones((size,size,4),dtype=np.float32)
    rgba[:,:,:3]=np.array((.34,.245,.12))*value[:,:,None]
    image=bpy.data.images.new('SkullV3_Adornment_Bone_BaseColor',size,size,alpha=False)
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    nodes,links=bone.node_tree.nodes,bone.node_tree.links
    tex=nodes.new('ShaderNodeTexImage')
    tex.image=image
    links.new(tex.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
    bump=nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value=.17
    bump.inputs['Distance'].default_value=.009
    links.new(tex.outputs['Color'],bump.inputs['Height'])
    links.new(bump.outputs['Normal'],nodes.get('Principled BSDF').inputs['Normal'])

    def mesh(name,verts,faces,mat,uv=None,smooth=True):
        name='SkullV3_Adornment_'+name
        data=bpy.data.meshes.new(name)
        data.from_pydata(verts,[],faces)
        data.update()
        bm=bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(data)
        bm.free()
        data.materials.append(mat)
        layer=data.uv_layers.new(name='AdornmentUV')
        for poly in data.polygons:
            poly.use_smooth=smooth
            if uv is not None:
                coords=[uv[data.loops[i].vertex_index] for i in poly.loop_indices]
                wraps=max(q[0] for q in coords)-min(q[0] for q in coords)>.5
                for li,q in zip(poly.loop_indices,coords):
                    layer.data[li].uv=(q[0]+(1 if wraps and q[0]<.5 else 0),q[1])
            else:
                axes=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(poly.normal[k]))]
                for li in poly.loop_indices:
                    co=data.vertices[data.loops[li].vertex_index].co
                    layer.data[li].uv=(co[axes[0]],co[axes[1]])
        o=bpy.data.objects.new(name,data)
        collection.objects.link(o)
        o['figurehead_revision']=3
        o['component']='skull adornment'
        made.append(o)
        return o

    def tube(name,points,radius,mat,n=8,closed=False):
        points=[Vector(p) for p in points]
        count=len(points)
        tangents=[]
        for i in range(count):
            before=points[(i-1)%count] if closed or i>0 else points[0]
            after=points[(i+1)%count] if closed or i<count-1 else points[-1]
            tangents.append((after-before).normalized())
        ref=Vector((1,0,0)) if abs(tangents[0].x)<.8 else Vector((0,1,0))
        normal=tangents[0].cross(ref).normalized()
        verts,uv=[],[]
        for i,(point,tangent) in enumerate(zip(points,tangents)):
            normal=(normal-tangent*normal.dot(tangent)).normalized()
            binormal=tangent.cross(normal).normalized()
            for j in range(n):
                a=math.tau*j/n
                verts.append(point+radius*(normal*math.cos(a)+binormal*math.sin(a)))
                uv.append((j/n,i/max(1,count-1)))
        faces=[]
        for i in range(count if closed else count-1):
            nxt=(i+1)%count
            faces.extend((i*n+j,i*n+(j+1)%n,nxt*n+(j+1)%n,nxt*n+j) for j in range(n))
        if not closed:
            faces += [tuple(reversed(range(n))),tuple(range((count-1)*n,count*n))]
        return mesh(name,verts,faces,mat,uv)

    def ring(name,loc,radius,wire,mat,normal=(1,0,0)):
        normal=Vector(normal).normalized()
        ref=Vector((0,0,1)) if abs(normal.z)<.9 else Vector((1,0,0))
        U=normal.cross(ref).normalized()
        V=normal.cross(U).normalized()
        points=[Vector(loc)+radius*(math.cos(a)*U+math.sin(a)*V)
                for a in np.linspace(0,math.tau,32,endpoint=False)]
        return tube(name,points,wire,mat,8,True)

    def long_bone(name,a,b,twist=0):
        a,b=Vector(a),Vector(b)
        axis=(b-a).normalized()
        U=Vector((1,0,0))
        V=axis.cross(U).normalized()
        profile=[(0,.14),(.03,.17),(.10,.17),(.20,.135),(.42,.113),(.62,.12),
                 (.80,.14),(.90,.17),(.97,.17),(1,.14)]
        ts=np.linspace(0,1,101)
        pr=np.array(profile)
        verts,uv=[],[]
        n=48
        for k,t in enumerate(ts):
            r=float(np.interp(t,pr[:,0],pr[:,1]))
            angle=twist+.30*math.sin(math.pi*t)
            A=U*math.cos(angle)+V*math.sin(angle)
            B=V*math.cos(angle)-U*math.sin(angle)
            loc=(a+axis*.12).lerp(b-axis*.12,float(t))+U*(.045*math.sin(math.pi*t))+V*(.035*math.sin(math.tau*t))
            for j in range(n):
                theta=math.tau*j/n
                c,s=math.cos(theta),math.sin(theta)
                x=r*.80*c
                y=r*s
                rough=1+.010*math.sin(theta*7+t*38)+.006*math.sin(theta*13-t*57)
                verts.append(loc+(A*x+B*y)*rough)
                uv.append((j/n,float(t)))
        faces=[tuple(reversed(range(n))),tuple(range((len(ts)-1)*n,len(ts)*n))]
        faces += [(k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j)
                  for k in range(len(ts)-1) for j in range(n)]
        # Anatomical paired condyles are fused into the shaft, with a visible
        # saddle between their rounded ends. No separate spheres or flat paddles.
        for end,endpoint,inward in [(0,a,axis),(1,b,-axis)]:
            for side in [-1,1]:
                origin=endpoint+inward*.12+V*(side*.12)+U*(side*.014)
                depth=.18 if side<0 else .17
                transverse=.17 if side<0 else .18
                length=.245 if (side+end)%2 else .215
                offset=len(verts)
                verts.append(origin+axis*length);uv.append((0,0))
                slices=32
                rings=19
                for k in range(1,rings+1):
                    phi=math.pi*k/(rings+1)
                    for j in range(slices):
                        theta=math.tau*j/slices
                        shape=1+.018*math.sin(theta*3+phi*2)
                        verts.append(origin+axis*(length*math.cos(phi))
                                     +U*(depth*math.sin(phi)*math.cos(theta)*shape)
                                     +V*(transverse*math.sin(phi)*math.sin(theta)*shape))
                        uv.append((j/slices,k/(rings+1)))
                bottom=len(verts)
                verts.append(origin-axis*length);uv.append((0,1))
                faces += [(offset,offset+1+(j+1)%slices,offset+1+j) for j in range(slices)]
                faces += [(offset+1+k*slices+j,offset+1+k*slices+(j+1)%slices,
                           offset+1+(k+1)*slices+(j+1)%slices,offset+1+(k+1)*slices+j)
                          for k in range(rings-1) for j in range(slices)]
                faces += [(bottom,offset+1+(rings-1)*slices+j,
                           offset+1+(rings-1)*slices+(j+1)%slices) for j in range(slices)]
        o=mesh(name,verts,faces,bone,uv)
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active=o
        modifier=o.modifiers.new('Unified organic bone','REMESH')
        modifier.mode='VOXEL'
        modifier.voxel_size=.014
        modifier.use_smooth_shade=True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        modifier=o.modifiers.new('Bone surface polish','SMOOTH')
        modifier.factor=.35
        modifier.iterations=3
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        layer=o.data.uv_layers.get('AdornmentUV') or o.data.uv_layers.new(name='AdornmentUV')
        for poly in o.data.polygons:
            poly.use_smooth=True
            axes=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(poly.normal[k]))]
            for li in poly.loop_indices:
                co=o.data.vertices[o.data.loops[li].vertex_index].co
                layer.data[li].uv=(co[axes[0]],co[axes[1]])
        return o

    # Midpoints are hidden behind the cranial vault; tips frame the silhouette.
    long_bone('Crossbone_A',center+Vector((.67,-1.65,-1.72)),
              center+Vector((.67,1.61,1.72)),.18)
    long_bone('Crossbone_B',center+Vector((.83,1.67,-1.72)),
              center+Vector((.83,-1.64,1.72)),-.16)

    def path_at(points,t):
        scaled=t*(len(points)-1)
        i=min(len(points)-2,int(scaled))
        return Vector(points[i]).lerp(Vector(points[i+1]),scaled-i)

    def braid(name,controls,turns):
        count=180 if turns>10 else 110
        centers=[path_at(controls,float(t)) for t in np.linspace(0,1,count)]
        for strand in range(3):
            points=[]
            for i,p in enumerate(centers):
                tangent=(centers[min(i+1,count-1)]-centers[max(i-1,0)]).normalized()
                U=tangent.cross(Vector((1,0,0))).normalized()
                V=tangent.cross(U).normalized()
                angle=math.tau*(turns*i/(count-1)+strand/3)
                points.append(p+.018*(math.cos(angle)*U+math.sin(angle)*V))
            tube(name+'_braid_'+str(strand),points,.0065,gold if strand==2 else rope,6)
        return controls

    def bead(name,loc,axis,radius,height,mat,style=0):
        axis=Vector(axis).normalized()
        ref=Vector((1,0,0))
        U=axis.cross(ref).normalized()
        V=axis.cross(U).normalized()
        hole=.025
        if style==0:
            profile=[(0,hole),(0,radius*.65),(.18*height,radius),
                     (.82*height,radius),(height,radius*.65),(height,hole)]
        elif style==1:
            profile=[(0,hole),(0,radius*.5),(.5*height,radius),
                     (height,radius*.5),(height,hole)]
        else:
            profile=[(0,hole),(0,radius*.85),(.12*height,radius),
                     (.88*height,radius),(height,radius*.85),(height,hole)]
        n=16
        verts,uv=[],[]
        for z,r in profile:
            for j in range(n):
                angle=math.tau*j/n
                verts.append(Vector(loc)+axis*(z-height/2)+r*(math.cos(angle)*U+math.sin(angle)*V))
                uv.append((j/n,z/height))
        faces=[(k*n+j,k*n+(j+1)%n,((k+1)%len(profile))*n+(j+1)%n,((k+1)%len(profile))*n+j)
               for k in range(len(profile)) for j in range(n)]
        return mesh(name,verts,faces,mat,uv)

    long_controls=[center+Vector(p) for p in [(-.61,-1.00,.55),(-.72,-1.08,.12),
                    (-.76,-1.12,-.34),(-.73,-1.16,-.88),(-.70,-1.15,-1.42)]]
    short_controls=[center+Vector(p) for p in [(-.62,.77,1.03),(-.73,.94,.73),
                    (-.79,1.03,.39),(-.78,1.07,.06)]]
    braid('Long_temple_tassel',long_controls,17)
    braid('Short_temple_braid',short_controls,11)
    palette=[gold,teal,ivory,red,gold,amber,dark,gold,red,ivory,teal,gold]
    for label,controls,ts in [('Long',long_controls,np.linspace(.20,.97,12)),
                              ('Short',short_controls,np.linspace(.08,.93,7))]:
        for i,t in enumerate(ts):
            pos=path_at(controls,float(t))
            tangent=(path_at(controls,min(1,float(t)+.01))-path_at(controls,max(0,float(t)-.01))).normalized()
            radius=(.055,.065,.048,.052,.042,.071)[i%6]
            height=(.085,.105,.070,.090,.050,.12)[i%6]
            mat=palette[i%len(palette)]
            bead(label+'_bead_'+str(i),pos,tangent,radius,height,mat,i%3)
            if i in [1,5,9]:
                ring(label+'_bead_gold_rim',pos+tangent*height*.38,radius*.83,.008,gold,tangent)
        ring(label+'_temple_eyelet',controls[0],.085,.012,gold)
    # Two small drop rings and one tapered ivory charm finish the longer cord.
    tip=long_controls[-1]
    for offset in [0,.095]:
        ring('Tassel_drop_ring',tip+Vector((0,0,-offset)),.058,.010,gold)
    start=tip+Vector((0,0,-.15))
    n=16
    profile=[(0,.030),(-.05,.052),(-.12,.045),(-.28,.017),(-.34,.004)]
    verts=[start+Vector((r*math.cos(j*math.tau/n),r*math.sin(j*math.tau/n),z))
           for z,r in profile for j in range(n)]
    faces=[tuple(reversed(range(n))),tuple(range((len(profile)-1)*n,len(profile)*n))]
    faces += [(k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j)
              for k in range(len(profile)-1) for j in range(n)]
    mesh('Tapered_ivory_charm',verts,faces,ivory)
    return made
