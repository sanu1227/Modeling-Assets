"""Weathered anatomical crossbones, hemp jewelry and physical mount hardware."""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def build_adornments(collection, center=(-29.2, 0, 9.37)):
    """Return only SkullV4_* meshes. Front of the figurehead points toward -X."""
    center=Vector(center)
    made=[]

    def material(name,color,rough=.65,metal=0):
        mat=bpy.data.materials.new('SkullV4_Adornment_'+name)
        mat.use_nodes=True
        mat.diffuse_color=(*color,1)
        p=mat.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value=(*color,1)
        p.inputs['Roughness'].default_value=rough
        p.inputs['Metallic'].default_value=metal
        return mat

    bone=material('Weathered_bone',(.26,.215,.15),.82,.03)
    gold=material('Salt_worn_bronze',(.115,.072,.029),.68,.65)
    rope=material('Worn_hemp',(.052,.041,.027),.96)
    teal=material('Faded_turquoise',(.026,.075,.068),.73)
    red=material('Worn_red_stone',(.080,.025,.016),.75)
    amber=material('Clouded_amber',(.14,.077,.025),.70)
    ivory=material('Aged_ivory_beads',(.24,.20,.14),.78,.02)
    dark=material('Weathered_slate_beads',(.018,.022,.025),.76)
    iron=material('Forged_mount_iron',(.018,.021,.022),.73,.72)
    # Portable, packed stained-bone color. Fine bump remains a Blender accent.
    size=512
    v,u=np.mgrid[0:size,0:size].astype(np.float32)/size
    random=np.random.default_rng(771)
    def value_noise(resolution):
        grid=random.uniform(-1,1,(resolution+1,resolution+1))
        grid[-1,:]=grid[0,:]
        grid[:,-1]=grid[:,0]
        x=u*resolution
        y=v*resolution
        ix=np.floor(x).astype(int)
        iy=np.floor(y).astype(int)
        fx=x-ix
        fy=y-iy
        fx=fx*fx*(3-2*fx)
        fy=fy*fy*(3-2*fy)
        return ((grid[iy,ix]*(1-fx)+grid[iy,ix+1]*fx)*(1-fy)
                +(grid[iy+1,ix]*(1-fx)+grid[iy+1,ix+1]*fx)*fy)
    # Random fields, not periodic waves: marine stains have no repeated bands.
    stain=.23*value_noise(5)+.12*value_noise(13)+.055*value_noise(39)+.025*value_noise(117)
    for _ in range(19):
        cu,cv=random.random(2)
        ru,rv=random.uniform(.025,.12,2)
        stain -= random.uniform(.04,.16)*np.exp(-((u-cu)/ru)**2-((v-cv)/rv)**2)
    value=np.clip(1+stain+random.normal(0,.018,(size,size)),.55,1.23)
    rgba=np.ones((size,size,4),dtype=np.float32)
    rgba[:,:,:3]=np.array((.26,.215,.15))*value[:,:,None]
    image=bpy.data.images.new('SkullV4_Adornment_Bone_BaseColor',size,size,alpha=False)
    image.pixels.foreach_set(rgba.ravel())
    image.pack()
    nodes,links=bone.node_tree.nodes,bone.node_tree.links
    tex=nodes.new('ShaderNodeTexImage')
    tex.image=image
    links.new(tex.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
    bump=nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value=.08
    bump.inputs['Distance'].default_value=.005
    links.new(tex.outputs['Color'],bump.inputs['Height'])
    links.new(bump.outputs['Normal'],nodes.get('Principled BSDF').inputs['Normal'])

    def mesh(name,verts,faces,mat,uv=None,smooth=True):
        name='SkullV4_Adornment_'+name
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
        o['figurehead_revision']=4
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

    def long_bone(name,a,b,twist=0,kind='femur'):
        a,b=Vector(a),Vector(b)
        axis=(b-a).normalized()
        U=Vector((1,0,0))
        V=axis.cross(U).normalized()
        profile=[(0,.15),(.04,.16),(.12,.145),(.24,.115),(.43,.097),(.63,.102),
                 (.80,.116),(.90,.135),(.97,.13),(1,.105)]
        ts=np.linspace(0,1,101)
        pr=np.array(profile)
        verts,uv=[],[]
        n=48
        for k,t in enumerate(ts):
            r=float(np.interp(t,pr[:,0],pr[:,1]))
            angle=twist+.30*math.sin(math.pi*t)
            A=U*math.cos(angle)+V*math.sin(angle)
            B=V*math.cos(angle)-U*math.sin(angle)
            loc=(a+axis*.12).lerp(b-axis*.24,float(t))+U*(.07*math.sin(math.pi*t))+V*(.045*math.sin(math.pi*t)*math.cos(math.pi*t*.7))
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
        def lobe(origin,depth,transverse,length,direction=None):
            nonlocal faces
            long_axis=axis if direction is None else Vector(direction).normalized()
            depth_axis=(U-long_axis*U.dot(long_axis)).normalized()
            wide_axis=long_axis.cross(depth_axis).normalized()
            offset=len(verts)
            verts.append(origin+long_axis*length);uv.append((0,0))
            slices,rings=32,19
            for k in range(1,rings+1):
                phi=math.pi*k/(rings+1)
                for j in range(slices):
                    theta=math.tau*j/slices
                    shape=1+.022*math.sin(theta*3+phi*2)+.012*math.cos(theta*5-phi)
                    verts.append(origin+long_axis*(length*math.cos(phi))
                                 +depth_axis*(depth*math.sin(phi)*math.cos(theta)*shape)
                                 +wide_axis*(transverse*math.sin(phi)*math.sin(theta)*shape))
                    uv.append((j/slices,k/(rings+1)))
            bottom=len(verts)
            verts.append(origin-long_axis*length);uv.append((0,1))
            faces += [(offset,offset+1+(j+1)%slices,offset+1+j) for j in range(slices)]
            faces += [(offset+1+k*slices+j,offset+1+k*slices+(j+1)%slices,
                       offset+1+(k+1)*slices+(j+1)%slices,offset+1+(k+1)*slices+j)
                      for k in range(rings-1) for j in range(slices)]
            faces += [(bottom,offset+1+(rings-1)*slices+j,
                       offset+1+(rings-1)*slices+(j+1)%slices) for j in range(slices)]

        # Each end has its own anatomy, rather than four repeated biscuit tips.
        if kind=='femur':
            # Offset rounded head, oblique neck and a lower rough trochanter.
            lobe(b-axis*.16+V*.12,.105,.11,.26,axis*.75+V*.66)
            lobe(b-axis*.035+V*.25,.205,.215,.22)
            lobe(b-axis*.20-V*.115,.155,.14,.225,axis-V*.22)
            # Unequal distal condyles with the intercondylar recess preserved.
            lobe(a+axis*.13-V*.12+U*.012,.185,.175,.22)
            lobe(a+axis*.16+V*.125-U*.014,.16,.145,.205)
            lobe(a+axis*.31,.135,.18,.23)
        else:
            # Humeral head and small tubercle, with a slanted surgical neck.
            lobe(b-axis*.09+V*.13,.205,.21,.225,axis+V*.3)
            lobe(b-axis*.22-V*.105,.115,.115,.18)
            lobe(b-axis*.28,.13,.145,.19,axis+V*.18)
            # Flatter trochlea/capitulum complex; visibly unlike the proximal end.
            lobe(a+axis*.13-V*.08,.145,.20,.17,axis+V*.15)
            lobe(a+axis*.18+V*.16,.125,.105,.145)
            lobe(a+axis*.31,.12,.15,.18)
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
            coords=[]
            for li in poly.loop_indices:
                p=o.data.vertices[o.data.loops[li].vertex_index].co-a
                along=p.dot(axis)
                radial=p-axis*along
                coords.append((math.atan2(-radial.dot(V),-radial.dot(U))/math.tau+.5,
                               along/(b-a).length*3))
            wraps=max(q[0] for q in coords)-min(q[0] for q in coords)>.5
            for li,q in zip(poly.loop_indices,coords):
                layer.data[li].uv=(q[0]+(1 if wraps and q[0]<.5 else 0),q[1])
        return o

    # Midpoints are hidden behind the cranial vault; tips frame the silhouette.
    long_bone('Crossbone_A',center+Vector((.67,-1.65,-1.72)),
              center+Vector((.67,1.61,1.72)),.18,'femur')
    long_bone('Crossbone_B',center+Vector((.83,1.67,-1.72)),
              center+Vector((.83,-1.64,1.72)),-.16,'humerus')

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
                points.append(p+.0095*(math.cos(angle)*U+math.sin(angle)*V))
            tube(name+'_braid_'+str(strand),points,.0035,rope,6)
        return controls

    def bead(name,loc,axis,radius,height,mat,style=0):
        axis=Vector(axis).normalized()
        ref=Vector((1,0,0))
        U=axis.cross(ref).normalized()
        V=axis.cross(U).normalized()
        hole=.0145
        if style==0:
            profile=[(0,hole),(0,radius*.65),(.18*height,radius),
                     (.82*height,radius),(height,radius*.65),(height,hole)]
        elif style==1:
            profile=[(0,hole),(0,radius*.62),(.5*height,radius),
                     (height,radius*.62),(height,hole)]
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

    bpy.context.view_layer.update()
    candidates=[o for o in collection.objects if o.type=='MESH' and o.name.startswith('SkullV4_')
                and 'Adornment' not in o.name]
    core=max(candidates,key=lambda o:len(o.data.vertices)) if candidates else None
    tree=BVHTree.FromObject(core,bpy.context.evaluated_depsgraph_get()) if core else None

    def surface_attachment(local):
        point=center+Vector(local)
        normal=Vector((-1,0,0))
        if tree is not None:
            hit,n,_,_=tree.find_nearest(core.matrix_world.inverted()@point)
            if hit is not None:
                point=core.matrix_world@hit
                normal=(core.matrix_world.to_3x3()@n).normalized()
        return point,normal

    attachments={}
    for label,sign in [('Long',-1),('Short',1)]:
        surface,normal=surface_attachment((-.38,sign*.82,.64))
        down=Vector((0,0,-1))
        down=(down-normal*down.dot(normal)).normalized()
        eyelet=surface+normal*.055+down*.047
        attachments[label]=(surface,normal,eyelet,down)
        tube(label+'_embedded_eyelet_pin',[surface-normal*.045,surface+normal*.06],.021,iron,12)
        ring(label+'_seated_eyelet',eyelet,.056,.0085,gold,normal)
        ring(label+'_pin_washer',surface+normal*.012,.028,.007,iron,normal)
    long_controls=[attachments['Long'][2]+attachments['Long'][3]*.052]
    long_controls += [center+Vector(p) for p in [(-.48,-.96,.28),(-.57,-1.03,-.16),
                                                (-.55,-1.08,-.62),(-.52,-1.08,-.98)]]
    short_controls=[attachments['Short'][2]+attachments['Short'][3]*.052]
    short_controls += [center+Vector(p) for p in [(-.58,.97,.46),(-.65,1.00,.19),(-.64,1.01,.01)]]
    braid('Long_temple_tassel',long_controls,18)
    braid('Short_temple_braid',short_controls,10)
    palette=[gold,teal,ivory,red,gold,amber,dark,gold,red,ivory,teal,gold]
    for label,controls,ts in [('Long',long_controls,np.linspace(.20,.97,12)),
                              ('Short',short_controls,np.linspace(.08,.93,7))]:
        for i,t in enumerate(ts):
            pos=path_at(controls,float(t))
            tangent=(path_at(controls,min(1,float(t)+.01))-path_at(controls,max(0,float(t)-.01))).normalized()
            radius=.68*(.055,.065,.048,.052,.042,.071)[i%6]
            height=.68*(.085,.105,.070,.090,.050,.12)[i%6]
            mat=palette[i%len(palette)]
            bead(label+'_bead_'+str(i),pos,tangent,radius,height,mat,i%3)
            if i in [1,5,9]:
                ring(label+'_bead_bronze_rim',pos+tangent*height*.38,radius*.83,.005,gold,tangent)
    # Two small drop rings and one tapered ivory charm finish the longer cord.
    tip=long_controls[-1]
    for offset in [0,.065]:
        ring('Tassel_drop_ring',tip+Vector((0,0,-offset)),.041,.007,gold)
    start=tip+Vector((0,0,-.105))
    n=16
    profile=[(0,.021),(-.04,.036),(-.10,.031),(-.23,.012),(-.28,.004)]
    verts=[start+Vector((r*math.cos(j*math.tau/n),r*math.sin(j*math.tau/n),z))
           for z,r in profile for j in range(n)]
    faces=[tuple(reversed(range(n))),tuple(range((len(profile)-1)*n,len(profile)*n))]
    faces += [(k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j)
              for k in range(len(profile)-1) for j in range(n)]
    mesh('Tapered_ivory_charm',verts,faces,ivory)

    def iron_strap(name,a,b,width=.065,depth=.12):
        a,b=Vector(a),Vector(b)
        tangent=(b-a).normalized()
        ref=Vector((0,1,0)) if abs(tangent.y)<.8 else Vector((1,0,0))
        U=tangent.cross(ref).normalized()*width/2
        V=tangent.cross(U).normalized()*depth/2
        verts=[p+s*U+t*V for p in [a,b] for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        o=mesh(name,verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),
                          (1,2,6,5),(2,3,7,6),(3,0,4,7)],iron,smooth=False)
        bevel=o.modifiers.new('Worn iron edges','BEVEL')
        bevel.width=.006
        bevel.segments=2
        return o

    # Actual two-piece stem clamps. The existing stem follows this saved curve;
    # its original mesh/curve stays untouched.
    stem_axis=Vector((-1.8,0,2.9)).normalized()
    stem_centers=[]
    for z in [8.90,9.55]:
        stem=Vector((-27.5+(z-7.5)*(-1.8/2.9),0,z))
        stem_centers.append(stem)
        ring('Stem_clamp',stem,.267,.036,iron,stem_axis)
        for side in [-1,1]:
            rivet=stem+Vector((.03,side*.27,0))
            tube('Clamp_rivet',[rivet-Vector((.02,0,0)),rivet+Vector((.025,0,0))],.032,iron,10)
    for side in [-1,1]:
        y=side*.25
        iron_strap('Vertical_mount_strap',stem_centers[0]+Vector((0,y,0)),
                   stem_centers[1]+Vector((0,y,0)),.065,.11)
        bone_anchor=center+Vector((.78 if side<0 else .94,side*.32,-.33))
        iron_strap('Crossbone_rear_brace',bone_anchor,
                   stem_centers[0]+Vector((0,side*.23,.07)),.055,.10)
        rear,normal=surface_attachment((.68,side*.30,.15))
        iron_strap('Skull_rear_brace',rear+normal*.01,
                   stem_centers[1]+Vector((0,side*.23,0)),.065,.12)
        tube('Rear_mount_rivet',[rear-normal*.03,rear+normal*.045],.034,iron,12)
    return made
