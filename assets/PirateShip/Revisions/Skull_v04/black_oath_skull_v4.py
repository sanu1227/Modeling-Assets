"""Weathered black-and-gold skull insignia; real raised surface-following inlays."""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def build_skull(collection, center=(-29.2, 0, 9.37)):
    """Create SkullV4_* objects, facing -X. Returns only the new components."""
    made = []
    def link(o):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        collection.objects.link(o)
        return o

    def surface_material(name,base,metal,rough,seed):
        m=bpy.data.materials.new(name)
        m.diffuse_color=(*base,1)
        m.use_nodes=True
        nodes,links=m.node_tree.nodes,m.node_tree.links
        p=nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value=(*base,1)
        p.inputs['Metallic'].default_value=metal
        p.inputs['Roughness'].default_value=rough
        size=512
        v,u=np.mgrid[0:size,0:size].astype(np.float32)/size
        rng=np.random.default_rng(seed)
        wear=(.28*np.sin(u*math.tau*5+np.sin(v*math.tau*7))
              +.17*np.cos(v*math.tau*13-u*math.tau*3)
              +rng.normal(0,.075,(size,size)))
        rgba=np.ones((size,size,4),dtype=np.float32)
        rgba[:,:,:3]=np.array(base)[None,None,:]*np.clip(1+wear[:,:,None],.22,1.65)
        if 'Black' in name:
            # Tiny oxidized flecks interrupt the blackened surface.
            mask=(rng.random((size,size))>.994)
            rgba[mask,:3]=(.11,.070,.025)
        image=bpy.data.images.new(name+'_BaseColor',size,size,alpha=False)
        image.pixels.foreach_set(rgba.ravel())
        image.pack()
        node=nodes.new('ShaderNodeTexImage')
        node.image=image
        links.new(node.outputs['Color'],p.inputs['Base Color'])
        noise=nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value=43
        noise.inputs['Detail'].default_value=3
        bump=nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value=.24
        bump.inputs['Distance'].default_value=.012
        links.new(noise.outputs['Fac'],bump.inputs['Height'])
        links.new(bump.outputs['Normal'],p.inputs['Normal'])
        return m
    material=surface_material('SkullV4_Weathered_Black',(.024,.029,.033),.38,.72,84)
    gold=surface_material('SkullV4_Antique_Gold',(.36,.25,.087),.68,.58,91)
    ivory=surface_material('SkullV4_Old_Ivory',(.42,.35,.22),.12,.66,113)

    def mesh(name, verts, faces):
        data = bpy.data.meshes.new(name)
        data.from_pydata(verts, [], faces)
        data.update()
        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(data)
        bm.free()
        o = bpy.data.objects.new(name, data)
        collection.objects.link(o)
        return o

    def active(o):
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o

    def apply(o, modifier):
        active(o)
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    def ellipsoid(name, loc, scale):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=24, location=loc)
        o = link(bpy.context.object)
        o.name = name
        o.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return o

    def subtract(target, cutter, rounding=0):
        if rounding:
            b = cutter.modifiers.new('Rounded cavity corners','BEVEL')
            b.width = rounding
            b.segments = 3
            apply(cutter,b)
        mod = target.modifiers.new('Sculpted recess','BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.solver = 'EXACT'
        mod.object = cutter
        apply(target,mod)
        data = cutter.data
        bpy.data.objects.remove(cutter,do_unlink=True)
        if data.users == 0:
            bpy.data.meshes.remove(data)

    def remesh(o, size=.022, smooth=4):
        m=o.modifiers.new('Unified sculpt surface','REMESH')
        m.mode='VOXEL'
        m.voxel_size=size
        m.use_smooth_shade=True
        apply(o,m)
        m=o.modifiers.new('Sculpt polish','SMOOTH')
        m.factor=.48
        m.iterations=smooth
        apply(o,m)

    def finish(o,mat=None):
        o.name = o.name if o.name.startswith('SkullV4_') else 'SkullV4_'+o.name
        o.data.materials.clear()
        o.data.materials.append(mat or material)
        for poly in o.data.polygons:
            poly.use_smooth=True
        layer=o.data.uv_layers.get('SkullUV') or o.data.uv_layers.new(name='SkullUV')
        for poly in o.data.polygons:
            axis=max(range(3),key=lambda a:abs(poly.normal[a]))
            axes=[a for a in range(3) if a!=axis]
            for li in poly.loop_indices:
                co=o.data.vertices[o.data.loops[li].vertex_index].co
                layer.data[li].uv=(co[axes[0]],co[axes[1]])
        o.location += Vector(center)
        o['figurehead_revision']=4
        made.append(o)
        return o

    # Anatomical structural volumes: cranial vault, maxilla, and malar arches.
    def loft(name,rings,n=64,frontal_power=1.0,subdivision=1):
        verts=[]
        for z,w,front,back in rings:
            cx,r=(front+back)/2,(back-front)/2
            for i in range(n):
                a=math.tau*i/n
                c=math.cos(a)
                if c<0:
                    c=-abs(c)**frontal_power
                verts.append((cx+r*c,w*math.sin(a),z))
        faces=[tuple(reversed(range(n))),tuple(range((len(rings)-1)*n,len(rings)*n))]
        faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i)
                  for j in range(len(rings)-1) for i in range(n)]
        o=mesh(name,verts,faces)
        if subdivision:
            m=o.modifiers.new('Bone surface interpolation','SUBSURF')
            m.levels=subdivision
            apply(o,m)
        return o

    def unite(objects,size=.014,polish=2):
        bpy.ops.object.select_all(action='DESELECT')
        for o in objects:o.select_set(True)
        o=objects[0]
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.join()
        remesh(o,size,polish)
        return o

    def bone_ridge(name,points,widths):
        # Diamond-section bone creates planar ridges rather than round tubes.
        points=[Vector(p) for p in points]
        samples=[]
        for j in range(len(points)-1):
            p0=points[max(0,j-1)]
            p1,p2=points[j],points[j+1]
            p3=points[min(len(points)-1,j+2)]
            for k in range(8):
                t=k/8
                p=.5*(2*p1+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t
                      +(-p0+3*p1-3*p2+p3)*t*t*t)
                samples.append((p,widths[j]*(1-t)+widths[j+1]*t))
        samples.append((points[-1],widths[-1]))
        verts=[]
        for i,(p,w) in enumerate(samples):
            tangent=samples[min(i+1,len(samples)-1)][0]-samples[max(0,i-1)][0]
            lateral=Vector((-tangent.y,tangent.x,0)).normalized()
            verts += [p+lateral*w*.5,p+Vector((0,0,w*.32)),
                      p-lateral*w*.5,p-Vector((0,0,w*.55))]
        faces=[(0,3,2,1),tuple(range((len(samples)-1)*4,len(samples)*4))]
        faces += [(j*4+i,j*4+(i+1)%4,(j+1)*4+(i+1)%4,(j+1)*4+i)
                  for j in range(len(samples)-1) for i in range(4)]
        return mesh(name,verts,faces)

    skull=loft('SkullV4_Cranium',[
        (-.43,.40,-.05,.47),(-.20,.64,-.34,.67),(.04,.81,-.60,.79),
        (.26,.92,-.78,.84),(.48,.94,-.94,.84),(.64,.92,-.91,.83),
        (.82,.88,-.80,.80),(.98,.79,-.66,.73),(1.12,.64,-.48,.59),
        (1.23,.44,-.25,.39),(1.29,.21,-.04,.20),(1.32,.045,.055,.095)
    ],subdivision=2)
    parts=[skull]
    maxilla=loft('Maxilla',[
        (-.72,.50,-1.00,.10),(-.63,.54,-1.04,.13),(-.46,.53,-1.00,.13),
        (-.29,.50,-.90,.10),(-.10,.44,-.83,.11),(.08,.25,-.78,.16)
    ],frontal_power=.86,subdivision=2)
    parts.append(maxilla)
    for side in [-1,1]:
        # A filled malar wedge meets the orbital floor and the upper maxilla.
        # Its rear face penetrates the vault; no detached front-facing straps.
        outline=[(-.68,.37,.13),(-.40,.73,.23),(-.22,.88,.035),
                 (-.25,.78,-.15),(-.73,.44,-.32),(-.78,.31,-.10)]
        verts=[(x+depth,side*y,z) for depth in [0,.34] for x,y,z in outline]
        n=len(outline)
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        malar=mesh('Malar_bone',verts,faces)
        bevel=malar.modifiers.new('Malar plane transition','BEVEL')
        bevel.width=.105
        bevel.segments=3
        apply(malar,bevel)
        parts.append(malar)
        parts.append(bone_ridge('Zygomatic_arch',[
            (-.23,side*.83,-.015),(.02,side*.84,-.015),
            (.29,side*.76,.06),(.42,side*.63,.12)
        ],[.16,.13,.15,.21]))
    # Continuous alveolar bone follows the same elliptical dental arch as roots.
    def alveolar_shelf(name,zbottom,ztop):
        n=61
        verts=[]
        for inner,z in [(False,zbottom),(False,ztop),(True,zbottom),(True,ztop)]:
            for i in range(n):
                a=-1.42+2.84*i/(n-1)
                c,s=math.cos(a),math.sin(a)
                # Fine scalloping breaks the straight mouthguard edge.
                scallop=.010*(1+math.cos(a*math.pi/.20)) if z==zbottom else 0
                p=Vector((-.985+.60*(1-c),.50*s,z+scallop))
                p+=Vector((-c,s,0)).normalized()*(.040 if not inner else -.11)
                verts.append(p)
        faces=[]
        for i in range(n-1):
            for a,b in [(0,1),(1,3),(3,2),(2,0)]:
                faces.append((a*n+i,a*n+i+1,b*n+i+1,b*n+i))
        faces += [(0,n,3*n,2*n),(n-1,3*n-1,4*n-1,2*n-1)]
        return mesh(name,verts,faces)
    parts.append(alveolar_shelf('Upper_alveolar_process',-.705,-.53))
    skull=unite(parts,.014,2)

    # Acute medial corner, unequal upper/lower planes, and a deep orbital vault.
    orbit=[(-.28,-.035),(-.15,.085),(.14,.145),(.33,.075),
           (.30,-.115),(.025,-.205),(-.18,-.165)]
    for side in [-1,1]:
        verts=[]
        for depth,scale,dz in [(-1.60,1.05,0),(-.42,.94,.005),(.05,.40,.035)]:
            verts += [(depth,side*(.45+u*scale),.29+v*scale+dz) for u,v in orbit]
        n=len(orbit)
        faces=[tuple(reversed(range(n))),tuple(range(2*n,3*n))]
        faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i)
                  for j in range(2) for i in range(n)]
        subtract(skull,mesh('Orbit_recess',verts,faces),.012)
        subtract(skull,ellipsoid('Temporal_fossa',(.36,side*.88,.34),(.29,.19,.29)))
        subtract(skull,ellipsoid('Subzygomatic_undercut',(.02,side*.69,-.29),(.28,.20,.20)))
    nose=[(0,-.02),(.10,-.20),(.145,-.36),(.08,-.435),(0,-.405),
          (-.08,-.435),(-.145,-.36),(-.10,-.20)]
    n=len(nose)
    verts=[(x,y*scale,z) for x,scale in [(-1.50,1),(-.12,.66)] for y,z in nose]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    subtract(skull,mesh('Piriform_nasal_aperture',verts,faces),.012)
    remesh(skull,.0115,4)
    finish(skull)

    # An elliptical mandible narrows into a firm chin and rises at a true angle.
    n=61
    verts=[]
    for ring in range(4):
        inner=ring>=2
        bottom=ring%2
        for i in range(n):
            a=-1.35+2.7*i/(n-1)
            s,c=math.sin(a),math.cos(a)
            x=-.98+.63*(1-c)
            y=.51*s
            radial=Vector((-c,s,0)).normalized()
            p=Vector((x,y,0))+radial*(.07 if not inner else -.065)
            z=(-1.145+.145*abs(s)**1.25) if bottom else (-.94+.025*abs(s)-.010*(1+math.cos(a*math.pi/.20)))
            if not inner:
                p.x-=.035*(1-abs(s))**4
            verts.append((p.x,p.y,z))
    faces=[]
    for i in range(n-1):
        for a,b in [(0,1),(1,3),(3,2),(2,0)]:
            faces.append((a*n+i,a*n+i+1,b*n+i+1,b*n+i))
    faces += [(0,n,3*n,2*n),(n-1,3*n-1,4*n-1,2*n-1)]
    jaw=mesh('SkullV4_Mandible',verts,faces)
    parts=[jaw]
    for side in [-1,1]:
        outline=[(-.54,-1.035),(-.17,-1.00),(.06,-.84),(.15,-.18),
                 (.045,-.10),(-.09,-.20),(-.25,-.78)]
        verts=[]
        for offset in [-.065,.065]:
            for x,z in outline:
                y=.49+.14*max(0,min(1,(z+1.075)/1.0))
                verts.append((x,side*(y+offset),z))
        m=len(outline)
        faces=[tuple(reversed(range(m))),tuple(range(m,2*m))]
        faces += [(i,(i+1)%m,(i+1)%m+m,i+m) for i in range(m)]
        parts.append(mesh('Mandibular_ramus',verts,faces))
    jaw=unite(parts,.0115,2)
    finish(jaw)

    # Each tooth has a cervical root, curved crown and class-specific biting face.
    # Incisors are flattened, canines pointed, and posterior teeth broad with cusps.
    theta=[.10,.30,.49,.72,.91,1.10,1.29]
    dimensions=[(.091,.125,.153),(.085,.125,.143),(.092,.145,.163),
                (.106,.172,.133),(.112,.190,.127),(.132,.217,.120),(.139,.225,.116)]
    for row in [0,1]:
        for side in [-1,1]:
            for index,a in enumerate(theta):
                width,depth,height=dimensions[index]
                if row:
                    width*=.94
                    height*=.78
                direction=-1 if not row else 1
                neck=-.690 if not row else -.950
                y=side*.50*math.sin(a)
                x=-.985+.60*(1-math.cos(a))
                # Molars retreat deeply along the jaw instead of forming a flat keyboard.
                angle=-side*math.atan2(.60*math.sin(a),.50*math.cos(a))
                x+=.012*math.sin(index*2.4+side)
                z=neck+.008*math.sin(index*1.7+row)+(.025 if row else -.018)*math.sin(a)
                nr=20
                rings=[(-.035,.66,.64),(0,.73,.70),(.045,.98,1.0)]
                if index==2:
                    rings += [(height*.72,.84,.78),(height,.40,.39)]
                elif index<2:
                    rings += [(height*.72,1.02,.64),(height,.91,.30)]
                else:
                    rings += [(height*.70,1.0,1.0),(height,.92,.86)]
                verts=[]
                for h,wy,dx in rings:
                    for k in range(nr):
                        t=math.tau*k/nr
                        co,si=math.cos(t),math.sin(t)
                        exponent=.74 if index<3 else .58
                        xx=depth*.5*dx*math.copysign(abs(co)**exponent,co)
                        yy=width*.5*wy*math.copysign(abs(si)**exponent,si)
                        hh=h
                        if h==height and index>=3:
                            hh+=.013*math.cos(t*2)**2-.008
                        verts.append((xx,yy,direction*hh))
                faces=[tuple(reversed(range(nr)))]
                for j in range(len(rings)-1):
                    faces += [(j*nr+k,j*nr+(k+1)%nr,(j+1)*nr+(k+1)%nr,(j+1)*nr+k) for k in range(nr)]
                center_index=len(verts)
                verts.append((0,0,direction*(height-(.025 if index>=3 else .002))))
                last=(len(rings)-1)*nr
                faces += [(last+k,last+(k+1)%nr,center_index) for k in range(nr)]
                tooth=mesh(f'SkullV4_{"Lower" if row else "Upper"}_{side}_{index+1}',verts,faces)
                tooth.location=(x,y,z)
                tooth.rotation_euler.z=angle
                mod=tooth.modifiers.new('Natural crown transitions','SUBSURF')
                mod.levels=1
                apply(tooth,mod)
                finish(tooth,gold if (row,side,index) in {(0,-1,2),(1,1,3)} else ivory)

    graphs={o.name:BVHTree.FromObject(o,bpy.context.evaluated_depsgraph_get()) for o in [skull,jaw]}
    inlay_base_count=len(made)

    def skin_point(target,y,z):
        origin=Vector(center)+Vector((-3,y,z))
        local=target.matrix_world.inverted()@origin
        hit,normal,_,_=graphs[target.name].ray_cast(local,Vector((1,0,0)),5)
        if hit is None:
            raise ValueError(f'Inlay projection misses {target.name}: y={y}, z={z}')
        return target.matrix_world@hit-Vector(center)

    def ribbon(name,controls,widths,target=skull,closed=False):
        controls=[Vector(p) for p in controls]
        samples=[]
        count=len(controls)
        segments=count if closed else count-1
        for j in range(segments):
            p0=controls[(j-1)%count] if closed or j else controls[0]
            p1=controls[j]
            p2=controls[(j+1)%count]
            p3=controls[(j+2)%count] if closed or j+2<count else controls[-1]
            for k in range(10):
                t=k/10
                p=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
                w=widths[j]*(1-t)+widths[(j+1)%count]*t
                samples.append((p,w))
        if not closed:
            samples.append((controls[-1],widths[-1]))
        verts=[]
        n=len(samples)
        # Slight stepped relief prevents coplanar flicker where motifs cross.
        lift=.003+.0003*(len(made)-inlay_base_count)
        for i,(p,w) in enumerate(samples):
            before=samples[(i-1)%n][0] if closed or i else p
            after=samples[(i+1)%n][0] if closed or i<n-1 else p
            tangent=(after-before).normalized()
            lateral=Vector((-tangent.y,tangent.x))
            q1=p+lateral*w/2
            q2=p-lateral*w/2
            a=skin_point(target,*q1)
            b=skin_point(target,*q2)
            verts += [a+Vector((-lift,0,0)),b+Vector((-lift,0,0)),
                      a+Vector((.006,0,0)),b+Vector((.006,0,0))]
        faces=[]
        for i in range(n if closed else n-1):
            a,b=i*4,((i+1)%n)*4
            faces += [(a,a+1,b+1,b),(a+2,b+2,b+3,a+3),
                      (a,b,b+2,a+2),(a+1,a+3,b+3,b+1)]
        if not closed:
            faces += [(0,2,3,1),((n-1)*4,(n-1)*4+1,(n-1)*4+3,(n-1)*4+2)]
        o=mesh('SkullV4_'+name,verts,faces)
        return finish(o,gold)

    # Low engraved plates follow the actual bone surface.
    ribbon('Gold_Central_Flame',[(0,.43),(0,.65),(.008,.91),(0,1.17)],
           [.038,.055,.039,.007])
    for side in [-1,1]:
        def mirrored(points):
            return [(side*y,z) for y,z in points]
        ribbon('Gold_Inner_Flame',mirrored([(0,.50),(.16,.68),(.14,.88),(.21,1.07)]),
               [.032,.062,.052,.007])
        ribbon('Gold_Outer_Flame',mirrored([(.19,.51),(.33,.65),(.40,.80),(.32,.94)]),
               [.024,.058,.048,.006])
        ribbon('Gold_Swept_Flame',mirrored([(.42,.49),(.58,.61),(.56,.79),(.64,.92)]),
               [.022,.055,.033,.006])
        # Broken accents preserve thin bone rims rather than enclosing goggles.
        ribbon('Gold_Brow_Edge',mirrored([(.21,.41),(.39,.48),(.62,.49),(.78,.39)]),
               [.018,.029,.025,.006])
        ribbon('Gold_Orbital_Fragment',mirrored([(.28,.10),(.40,.065),(.57,.074)]),
               [.007,.020,.004])
        ribbon('Gold_Malar_Edge',mirrored([(.73,-.055),(.65,-.15),(.51,-.23)]),
               [.008,.025,.006])
        ribbon('Gold_Nasal_Fragment',mirrored([(.064,-.08),(.14,-.24),(.18,-.36)]),
               [.006,.020,.008])
    ribbon('Gold_Chin_Chevron',[(-.33,-1.045),(0,-1.105),(.33,-1.045)],
           [.009,.032,.009],target=jaw)
    return made


def validate_skull(objects):
    report={'objects':len(objects),'triangles':0,'degenerate_triangles':0,
            'nonmanifold_edges':0,'inconsistent_winding':0,'bounds_min':[1e9]*3,'bounds_max':[-1e9]*3}
    report['connected_components']={}
    graph=bpy.context.evaluated_depsgraph_get()
    for o in objects:
        eo=o.evaluated_get(graph)
        d=eo.to_mesh()
        d.calc_loop_triangles()
        report['triangles']+=len(d.loop_triangles)
        report['degenerate_triangles']+=sum(t.area<1e-11 for t in d.loop_triangles)
        bm=bmesh.new()
        bm.from_mesh(d)
        report['nonmanifold_edges']+=sum(not e.is_manifold for e in bm.edges)
        report['inconsistent_winding']+=sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
        remaining=set(bm.verts)
        components=0
        while remaining:
            components+=1
            todo=[remaining.pop()]
            while todo:
                v=todo.pop()
                for edge in v.link_edges:
                    other=edge.other_vert(v)
                    if other in remaining:
                        remaining.remove(other)
                        todo.append(other)
        report['connected_components'][o.name]=components
        bm.free()
        for v in d.vertices:
            p=eo.matrix_world@v.co
            for i in range(3):
                report['bounds_min'][i]=min(report['bounds_min'][i],p[i])
                report['bounds_max'][i]=max(report['bounds_max'][i],p[i])
        eo.to_mesh_clear()
    report['passed']=(not any(report[k] for k in ['degenerate_triangles','nonmanifold_edges','inconsistent_winding'])
                      and all(n==1 for n in report['connected_components'].values()))
    return report


