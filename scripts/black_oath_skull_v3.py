"""Weathered black-and-gold skull insignia; real raised surface-following inlays."""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def build_skull(collection, center=(-29.2, 0, 9.37)):
    """Create SkullV3_* objects, facing -X. Returns only the new components."""
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
    material=surface_material('SkullV3_Weathered_Black',(.024,.029,.033),.38,.72,84)
    gold=surface_material('SkullV3_Antique_Gold',(.42,.30,.105),.72,.50,91)
    ivory=surface_material('SkullV3_Old_Ivory',(.42,.35,.22),.12,.66,113)

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
        o.name = o.name if o.name.startswith('SkullV3_') else 'SkullV3_'+o.name
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
        o['figurehead_revision']=3
        made.append(o)
        return o

    # Varying cross sections create cheek planes, a narrow maxilla, and a broad
    # cranial vault. The facial half is flatter than the back of the head.
    rings = [
        (-.73,.62,-.86,.35),(-.61,.64,-.88,.35),(-.40,.64,-.78,.40),
        (-.20,.79,-.70,.57),(.02,.99,-.78,.69),(.22,1.02,-.76,.77),
        (.49,.96,-.82,.80),(.66,.93,-.84,.80),(.88,.85,-.73,.76),
        (1.04,.79,-.65,.70),(1.17,.62,-.48,.55),(1.26,.42,-.28,.36),(1.31,.21,-.08,.20),
        (1.33,.045,.02,.08)]
    n=64
    verts=[]
    for z,w,front,back in rings:
        cx=(front+back)/2
        radius=(back-front)/2
        for i in range(n):
            t=math.tau*i/n
            c,s=math.cos(t),math.sin(t)
            c=math.copysign(abs(c)**(.62 if c<0 else 1),c)
            verts.append((cx+radius*c,w*s,z))
    faces=[tuple(reversed(range(n))),tuple(range((len(rings)-1)*n,len(rings)*n))]
    faces += [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i)
              for j in range(len(rings)-1) for i in range(n)]
    skull=mesh('SkullV3_Cranium',verts,faces)
    sub=skull.modifiers.new('Cranial sculpt interpolation','SUBSURF')
    sub.levels=2
    apply(skull,sub)

    # Polygonal eye openings have a broad upper rim and tapered inner corner.
    orbit=[(-.32,.015),(-.15,.065),(.22,.115),(.37,.065),
           (.32,-.13),(.13,-.205),(-.11,-.19),(-.29,-.11)]
    for side in [-1,1]:
        verts=[]
        for depth,scale,zshift in [(-1.50,1.04,0),(-.48,1,0),(.12,.58,.02)]:
            for u,v in orbit:
                verts.append((depth,side*(.47+u*scale),.24+v*scale+zshift))
        count=len(orbit)
        faces=[tuple(reversed(range(count))),tuple(range(2*count,3*count))]
        faces += [(j*count+i,j*count+(i+1)%count,(j+1)*count+(i+1)%count,(j+1)*count+i)
                  for j in range(2) for i in range(count)]
        subtract(skull,mesh('Orbital_cutter',verts,faces),.022)
        cutter=ellipsoid('Temporal_hollow',(.02,side*.81,-.15),(.39,.225,.30))
        subtract(skull,cutter)
    # Pear/triangular nasal opening below a narrow integrated bridge.
    outline=[(0,.015),(.13,-.16),(.20,-.34),(.12,-.44),(0,-.48),
             (-.12,-.44),(-.20,-.34),(-.13,-.16)]
    verts=[(x,y,z) for x,scale in [(-1.4,1),(-.2,.72)] for y,z in [(u*scale,v) for u,v in outline]]
    n=len(outline)
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    subtract(skull,mesh('Nasal_cutter',verts,faces),.025)
    # A continuous alveolar ridge seats every upper tooth, including the
    # posterior teeth where a rounded skull underside otherwise recedes.
    verts=[]
    sections,around=41,12
    for j in range(sections):
        u=-1+2*j/(sections-1)
        y=.54*u
        x=-.78+.40*abs(u)**1.65
        slope=.40*1.65*abs(u)**.65*(1 if u>=0 else -1)/.54
        radial=Vector((1,-slope,0)).normalized()
        for i in range(around):
            a=math.tau*i/around
            point=Vector((x,y,-.64))+radial*(.085*math.cos(a))+Vector((0,0,.10*math.sin(a)))
            verts.append(tuple(point))
    faces=[tuple(reversed(range(around))),tuple(range((sections-1)*around,sections*around))]
    faces += [(j*around+i,j*around+(i+1)%around,(j+1)*around+(i+1)%around,(j+1)*around+i)
              for j in range(sections-1) for i in range(around)]
    ridge=mesh('Alveolar_ridge',verts,faces)
    active(skull)
    ridge.select_set(True)
    bpy.ops.object.join()
    remesh(skull,.018,4)
    finish(skull)

    # Mandible: a thin U-shaped bony band with broad chin planes and rising rami.
    n=49
    verts=[]
    for ring in range(4):
        inner=ring>=2
        lower=ring%2
        for i in range(n):
            a=-math.pi/2+math.pi*i/(n-1)
            s,c=math.sin(a),math.cos(a)
            y=(.60 if not inner else .43)*s
            x=(-.87 if not inner else -.70)+(.70 if not inner else .62)*abs(s)**1.8
            z=(-1.24+.18*abs(s)**1.5) if lower else (-.98+.05*abs(s)**2)
            verts.append((x,y,z))
    faces=[]
    for i in range(n-1):
        for a,b in [(0,1),(1,3),(3,2),(2,0)]:
            faces.append((a*n+i,a*n+i+1,b*n+i+1,b*n+i))
    faces += [(0,n,3*n,2*n),(n-1,3*n-1,4*n-1,2*n-1)]
    jaw=mesh('SkullV3_Mandible',verts,faces)
    parts=[jaw]
    for side in [-1,1]:
        # Tapered ascending ramus, with an angled lower jaw corner.
        outline=[(-.25,-1.10),(.08,-.99),(.22,-.25),(.13,-.13),
                 (-.02,-.18),(-.04,-.77)]
        verts=[(x,side*y,z) for y in [.50,.67] for x,z in outline]
        n=len(outline)
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        parts.append(mesh('Ramus',verts,faces))
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active=jaw
    bpy.ops.object.join()
    remesh(jaw,.017,6)
    jaw.location.z += .05
    finish(jaw)

    # Compact, graded teeth follow an arch instead of a straight cartoon grin.
    for row in [0,1]:
        for i in range(12):
            u=(i-5.5)/5.5
            y=.54*u
            x=-.91+.53*abs(u)**1.65
            x += .07*(1-abs(u))**1.6
            height=(.155 if row==0 else .115)*(1-.24*abs(u))
            height*=[.94,1.04,.96,1.05,.98,1][i if i<6 else 11-i]
            if i in [2,9] and row==0: height*=1.13
            z=(-.70-height/2) if row==0 else (-.97+height/2)
            width=.093 if abs(u)<.5 else .103
            depth=.16 if abs(u)<.6 else .20
            half=width/2
            d=depth/2
            h=height/2
            verts=[(-d,-half,-h),(-d,half,-h),(d,half,-h),(d,-half,-h),
                   (-d*.82,-half*.88,h),(-d*.82,half*.88,h),(d*.82,half*.88,h),(d*.82,-half*.88,h)]
            faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
            tooth=mesh(f'SkullV3_{"Upper" if row==0 else "Lower"}Tooth_{i+1:02}',verts,faces)
            tooth.location=(x,y,z)
            tooth.rotation_euler.z=-.75*u
            bevel=tooth.modifiers.new('Rounded tooth enamel','BEVEL')
            bevel.width=.018
            bevel.segments=3
            apply(tooth,bevel)
            finish(tooth,gold if (row,i) in {(0,2),(0,7),(1,4)} else ivory)

    # Ornament coordinates are in the frontal Y/Z plane. Every strip vertex
    # is projected to the actual sculpt, then extruded into a closed solid.
    # This keeps broad inlays flush with the forehead, orbital and cheek planes.
    bpy.context.view_layer.update()
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
        lift=.018+.0012*(len(made)-inlay_base_count)
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
                      a+Vector((.012,0,0)),b+Vector((.012,0,0))]
        faces=[]
        for i in range(n if closed else n-1):
            a,b=i*4,((i+1)%n)*4
            faces += [(a,a+1,b+1,b),(a+2,b+2,b+3,a+3),
                      (a,b,b+2,a+2),(a+1,a+3,b+3,b+1)]
        if not closed:
            faces += [(0,2,3,1),((n-1)*4,(n-1)*4+1,(n-1)*4+3,(n-1)*4+2)]
        o=mesh('SkullV3_'+name,verts,faces)
        return finish(o,gold)

    # Broad branching/flame motifs, modeled in relief on the black forehead.
    ribbon('Gold_Central_Flame',[(0,.29),(0,.58),(.015,.84),(0,1.17)],
           [.075,.080,.065,.018])
    for sign in [-1,1]:
        def reflected(points):
            return [(sign*y,z) for y,z in points]
        ribbon('Gold_Inner_Flame',reflected([(0,.40),(.19,.63),(.17,.82),(.10,.98),(.18,1.12)]),
               [.055,.095,.090,.055,.012])
        ribbon('Gold_Outer_Flame',reflected([(.12,.48),(.32,.61),(.43,.82),(.33,.94),(.29,1.10)]),
               [.055,.105,.115,.075,.014])
        ribbon('Gold_Swept_Flame',reflected([(.23,.44),(.48,.50),(.58,.66),(.53,.79),(.62,.96)]),
               [.050,.100,.095,.055,.012])
        ribbon('Gold_Temple_Curl',reflected([(.70,.39),(.83,.56),(.85,.72),(.76,.86)]),
               [.045,.075,.060,.012])
        # Expand the eye outline onto solid bone outside the cut opening.
        eye=[(sign*(.47+u*1.19),.24+v*1.30+(.07 if v>=0 else 0)) for u,v in orbit]
        ribbon('Gold_Orbital_Rim',eye,[.075]*len(eye),closed=True)
        ribbon('Gold_Cheek_Flame',reflected([(.78,-.045),(.69,-.20),(.52,-.35),(.58,-.49)]),
               [.060,.075,.060,.018])
        ribbon('Gold_Maxillary_Accent',reflected([(.27,-.42),(.32,-.57),(.45,-.64)]),
               [.035,.050,.018])
    nose=[(0,.035),(.15,-.14),(.23,-.34),(.14,-.48),(0,-.51),
          (-.14,-.48),(-.23,-.34),(-.15,-.14)]
    ribbon('Gold_Nasal_Rim',nose,[.048]*len(nose),closed=True)
    ribbon('Gold_Forehead_Crown',[(-.72,.92),(-.55,1.08),(-.29,1.19),(0,1.22),
                                (.29,1.19),(.55,1.08),(.72,.92)],
           [.030,.032,.032,.032,.032,.032,.030])
    ribbon('Gold_Chin_Border',[(-.50,-1.00),(-.33,-1.075),(0,-1.13),(.33,-1.075),(.50,-1.00)],
           [.045,.055,.055,.055,.045],target=jaw)
    ribbon('Gold_Chin_Chevron',[(-.30,-1.04),(0,-1.12),(.30,-1.04)],
           [.030,.045,.030],target=jaw)
    return made


def validate_skull(objects):
    report={'objects':len(objects),'triangles':0,'degenerate_triangles':0,
            'nonmanifold_edges':0,'inconsistent_winding':0,'bounds_min':[1e9]*3,'bounds_max':[-1e9]*3}
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
        bm.free()
        for v in d.vertices:
            p=eo.matrix_world@v.co
            for i in range(3):
                report['bounds_min'][i]=min(report['bounds_min'][i],p[i])
                report['bounds_max'][i]=max(report['bounds_max'][i],p[i])
        eo.to_mesh_clear()
    report['passed']=not any(report[k] for k in ['degenerate_triangles','nonmanifold_edges','inconsistent_winding'])
    return report

