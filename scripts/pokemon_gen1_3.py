"""Sculpted original-proportion interpretations of the nine early starters.

Each builder adds named, editable components to pokemon_common's active collection.
Front is negative Y. Models intentionally retain separate coloured sculpt pieces.
"""
from pokemon_common import *
import math
from mathutils.bvhtree import BVHTree


def _polygon_patch(name, center, scale, outline, color, skin=None, lift=None):
    """Thin closed coloured marking fitted to an ellipsoidal skin surface."""
    outline=list(outline)
    signed_area=sum(p[0]*outline[(i+1)%len(outline)][1]-outline[(i+1)%len(outline)][0]*p[1]
                    for i,p in enumerate(outline))
    if signed_area<0:
        outline.reverse()
    cx=sum(p[0] for p in outline)/len(outline)
    cz=sum(p[1] for p in outline)/len(outline)
    rim=[]
    for i,p in enumerate(outline):
        q=outline[(i+1)%len(outline)]
        for j in range(4):
            t=j/4
            rim.append((p[0]*(1-t)+q[0]*t,p[1]*(1-t)+q[1]*t))
    tree=BVHTree.FromObject(skin,bpy.context.evaluated_depsgraph_get()) if skin else None
    def surface(x,z):
        if tree:
            inv=skin.matrix_world.inverted()
            hit,_,_,_=tree.ray_cast(inv@Vector((x,-5,z)),inv.to_3x3()@Vector((0,1,0)))
            if hit is not None:
                return (skin.matrix_world@hit).y-(.012 if lift is None else lift)
        return front(center,scale,x,z)-(.019 if lift is None else lift)
    vertices=[(cx,surface(cx,cz),cz)]
    n=len(rim)
    for ring in range(1,5):
        for x,z in rim:
            x,z=cx+(x-cx)*ring/4,cz+(z-cz)*ring/4
            vertices.append((x,surface(x,z),z))
    faces=[(0,1+j,1+(j+1)%n) for j in range(n)]
    for ring in range(3):
        for j in range(n):
            a,b=1+ring*n+j,1+ring*n+(j+1)%n
            faces.append((a,b,b+n,a+n))
    obj=mesh(name,vertices,faces,color)
    mod=obj.modifiers.new("Closed marking thickness","SOLIDIFY")
    mod.thickness=.022; mod.offset=-1
    apply(obj,mod)
    return obj


def _almond_eye(name, center, scale, x, z, size, iris):
    """Colour layers follow the skin instead of stacking raised eyeball discs."""
    sx,sz=size
    side=-1 if x<0 else 1
    rim=[(-.94,-.78),(-.91,-.04),(-.58,.70),(.08,1.01),(.66,.68),(.96,-.73),(.46,-.96),(-.38,-.98)]
    outline=[(x+side*u*sx,z+v*sz) for u,v in rim]
    _polygon_patch(name+" almond sclera",center,scale,outline,"FFF8E9",lift=.010)
    for label,rx,rz,cx,cz,lift,col in (
        ("iris",sx*.70,sz*.87,x+side*sx*.13,z,.017,iris),
        ("pupil",sx*.34,sz*.70,x+side*sx*.14,z+.008,.024,"172C35"),
        ("highlight",sx*.22,sz*.22,x-side*sx*.08,z+sz*.45,.031,"FFFFFF")):
        ring=[(cx+rx*math.cos(i*math.tau/32),cz+rz*math.sin(i*math.tau/32)) for i in range(32)]
        _polygon_patch(name+" "+label,center,scale,ring,col,lift=lift)


def _claws(prefix, x, y, z, spread=.105, size=.065):
    for i in (-1, 0, 1):
        ell(f"{prefix} claw {i + 2}", (x + i * spread, y, z),
            (size, size * 1.6, size * .55), "FFF4DC")


def _feather_cutout(name, outline, front_y, depth, color):
    vertices=[(x,front_y,z) for x,z in outline]+[(x,front_y+depth,z) for x,z in outline]
    n=len(outline)
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    obj=mesh(name,vertices,faces,color)
    bevel=obj.modifiers.new("Soft feather edge","BEVEL")
    bevel.width=.012; bevel.segments=3
    apply(obj,bevel)
    return obj


def _flame(prefix, base, height=.75, width=.24):
    x, y, z = base
    tube(prefix + " orange silhouette", [(x,y,z), (x-.07,y,z+height*.35),
         (x+.08,y,z+height*.7), (x-.015,y,z+height)],
         [width*.65,width,width*.55,.009], "FF681F", sides=20)
    for side in (-1, 1):
        tube(prefix + f" side lick {side}", [(x+side*width*.25,y,z+height*.12),
             (x+side*width*.9,y,z+height*.42), (x+side*width*.85,y,z+height*.68)],
             [width*.55,width*.4,.009], "FF681F")
    tube(prefix + " golden heart", [(x,y-width*.55,z+.035),
         (x,y-width*.63,z+height*.32), (x+.025,y-width*.43,z+height*.67)],
         [width*.40,width*.55,.007], "FFD64A")


def build_bulbasaur():
    skin = "74BEAD"
    dark = "368F82"
    body = ell("Bulbasaur broad body", (0,.23,.66), (.67,.81,.5), skin)
    head = (0,-.48,1.03)
    hs = (.79,.57,.62)
    parts = [body, ell("Bulbasaur broad face", head, hs, skin)]
    for side in (-1,1):
        parts.append(ell(f"Bulbasaur cheek {side}", (side*.51,-.61,.85), (.31,.37,.27), skin))
        for j,y in enumerate((-.42,.63)):
            parts.append(ell(f"Bulbasaur leg {side} {j}", (side*.49,y,.31), (.25,.28,.34), skin))
            _claws(f"Bulbasaur foot {side} {j}", side*.49,y-.25,.12,.085,.055)
        parts.append(cone(f"Bulbasaur ear {side}", (side*.49,-.42,1.39),
                          (side*.64,-.34,1.82),.25,skin))
    skin_mesh=union("Bulbasaur continuous skin",parts,skin,voxel=.035)
    for side in (-1,1):
        _almond_eye(f"Bulbasaur ruby eye {side}",head,hs,side*.4,1.21,(.20,.24),"C84B63")
        _polygon_patch(f"Bulbasaur temple spot {side}",head,hs,
                       [(side*.55,1.17),(side*.66,1.11),(side*.63,.98),(side*.51,1.02)],dark)
        _polygon_patch(f"Bulbasaur brow spot {side}",head,hs,
                       [(side*.20,1.49),(side*.40,1.49),(side*.28,1.36)],dark)
        ell(f"Bulbasaur nostril {side}",(side*.16,-1.032,.99),(.025,.016,.018),"347567")
        cone(f"Bulbasaur tiny fang {side}",(side*.29,-.991,.81),(side*.29,-1.003,.72),.044,"FFF4DC")
        ell(f"Bulbasaur flank spot {side}",(side*.654,.31,.75),(.028,.16,.11),dark)
        _polygon_patch(f"Bulbasaur angular foreleg spot {side}",head,hs,
                       [(side*.42,.41),(side*.54,.48),(side*.63,.41),(side*.59,.29),(side*.46,.30)],dark,skin_mesh)
    _polygon_patch("Bulbasaur forehead diamond",head,hs,
                   [(-.07,1.48),(.045,1.46),(.075,1.34),(-.03,1.30)],dark)
    patch("Bulbasaur open smiling mouth",head,hs,(0,.80),(.39,.105),"593947")
    patch("Bulbasaur pink tongue",head,hs,(0,.755),(.28,.035),"C98597")
    ell("Bulbasaur bulb heart",(0,.47,1.39),(.58,.58,.60),"5C9D59")
    for j in range(4):
        a=j*math.tau/4
        x,y=math.sin(a),math.cos(a)
        tube(f"Bulbasaur bulb petal {j+1}",[(x*.35,.47+y*.35,1.07),
             (x*.5,.47+y*.5,1.45),(x*.29,.47+y*.29,1.79),(0,.46,2.02)],
             [.32,.33,.23,.016],"78AF62" if j%2 else "6AA456",sides=24)


def build_charmander():
    orange="EF9854"
    body=(0,.03,.90); bs=(.48,.39,.74)
    head=(0,-.12,1.88); hs=(.53,.44,.60)
    parts=[ell("Charmander pear body",body,bs,orange),ell("Charmander head",head,hs,orange)]
    for s in (-1,1):
        parts.append(tube(f"Charmander arm {s}",[(s*.33,0,1.17),(s*.56,-.02,1.01),(s*.62,-.18,.96)],
                          [.18,.15,.15],orange))
        parts.append(ell(f"Charmander haunch {s}",(s*.36,.02,.38),(.26,.30,.34),orange))
        parts.append(ell(f"Charmander foot {s}",(s*.37,-.23,.16),(.25,.36,.17),orange))
        _claws(f"Charmander toe {s}",s*.37,-.54,.14,.085,.058)
    parts.append(tube("Charmander sweeping tail",[(0,.30,.43),(.3,.65,.34),(.76,.70,.45),(1.01,.59,.9),(1.03,.45,1.3)],
                       [.27,.23,.18,.12,.09],orange,sides=20))
    union("Charmander smooth orange skin",parts,orange,voxel=.034)
    patch("Charmander cream belly",body,bs,(0,.79),(.335,.49),"FFE5AB")
    for s in (-1,1):
        _almond_eye(f"Charmander turquoise eye {s}",head,hs,s*.275,2.01,(.14,.24),"276E89")
        ell(f"Charmander nostril {s}",(s*.12,-.549,1.77),(.023,.012,.019),"A05539")
        for j in range(3):
            ell(f"Charmander finger {s} {j}",(s*(.54+j*.06),-.24,.92),(.052,.08,.065),orange)
    patch("Charmander open smile",head,hs,(0,1.61),(.32,.12),"6C414A")
    patch("Charmander tongue",head,hs,(0,1.565),(.22,.045),"CE899A")
    for s in (-1,1):
        y=front(head,hs,s*.23,1.66)-.045
        cone(f"Charmander fang {s}",(s*.23,y,1.69),(s*.23,y,1.61),.035,"FFF9E6")
    _flame("Charmander tail flame",(1.03,.44,1.20),.89,.25)


def build_squirtle():
    blue="78C7D3"
    body=(0,.03,.8); bs=(.52,.38,.63)
    head=(0,-.11,1.65); hs=(.64,.52,.56)
    skin=[ell("Squirtle body",body,bs,blue),ell("Squirtle head",head,hs,blue)]
    for s in (-1,1):
        skin.append(tube(f"Squirtle waving arm {s}",[(s*.38,-.02,1.03),(s*.65,-.11,.96),(s*.81,-.14,1.06)],
                         [.20,.17,.14],blue))
        skin.append(ell(f"Squirtle leg {s}",(s*.36,.01,.35),(.25,.26,.31),blue))
        skin.append(ell(f"Squirtle foot {s}",(s*.4,-.19,.15),(.23,.32,.15),blue))
    union("Squirtle blue skin",skin,blue,voxel=.035)
    ell("Squirtle shell ivory rim",(0,.25,.85),(.65,.28,.76),"F7E5C0")
    ell("Squirtle brown carapace",(0,.42,.86),(.59,.30,.68),"9C6B42")
    # Raised rear seams remain visible when orbiting the editable model.
    for s in (-1,1):
        tube(f"Squirtle rear shell seam {s}",[(s*.3,.57,1.39),(s*.27,.704,1.14),
             (s*.39,.709,.82),(s*.28,.646,.46)], [.014]*4,"644831",sides=10)
    tube("Squirtle shell central panel top",[(-.29,.673,1.17),(0,.722,1.3),(.29,.673,1.17)],
         [.016]*3,"644831",sides=10)
    tube("Squirtle shell central panel bottom",[(-.36,.704,.83),(0,.737,.65),(.36,.704,.83)],
         [.016]*3,"644831",sides=10)
    patch("Squirtle golden plastron",body,bs,(0,.78),(.46,.56),"F2D59A")
    for z,w in ((.53,.36),(.82,.43),(1.07,.34)):
        points=[]
        for i in range(7):
            x=-w+i*w/3
            pz=z-.025*(1-(x/w)**2)
            points.append((x,front(body,bs,x,pz)-.027,pz))
        tube(f"Squirtle belly plate {z}",points,[.008]*len(points),"BD9C6A",sides=10)
    for s in (-1,1):
        points=[]
        for z in (.32,.50,.72,.95,1.18):
            x=s*.19
            points.append((x,front(body,bs,x,z)-.025,z))
        tube(f"Squirtle vertical belly plate {s}",points,[.007]*len(points),"BD9C6A",sides=10)
    tube("Squirtle curled tail",[(.30,.40,.35),(.70,.53,.37),(.94,.42,.61),(.84,.27,.82),(.62,.23,.77),(.65,.23,.60)],
         [.22,.23,.22,.20,.15,.075],blue,sides=20)
    for s in (-1,1):
        eye(f"Squirtle warm brown eye {s}",head,hs,s*.30,1.78,(.17,.23),"693C4E")
        _claws(f"Squirtle foot {s}",s*.4,-.46,.13,.08,.052)
    smile("Squirtle smile",(0,-.615,1.41),.67)


def build_chikorita():
    green="D4E99D"
    head=(0,-.22,1.37); hs=(.57,.48,.51)
    parts=[ell("Chikorita pear body",(0,.16,.79),(.54,.58,.61),green),
           ell("Chikorita head",head,hs,green)]
    for s in (-1,1):
        for j,y in enumerate((-.25,.50)):
            parts.append(ell(f"Chikorita foot {s} {j}",(s*.34,y,.21),(.2,.24,.24),green))
    parts.append(tube("Chikorita little tail",[(0,.53,.61),(0,.79,.68),(0,.89,.85)],[.2,.14,.01],green))
    union("Chikorita pale green skin",parts,green,voxel=.035)
    for s in (-1,1):
        eye(f"Chikorita eye {s}",head,hs,s*.25,1.45,(.12,.18),"BD4C58")
    smile("Chikorita soft smile",(0,-.691,1.20),.21)
    for j in range(9):
        a=j*math.tau/9
        ell(f"Chikorita necklace bud {j+1}",(.48*math.sin(a),-.12+.50*math.cos(a),1.01),
            (.08,.08,.09),"609C63")
    tube("Chikorita head leaf stalk",[(0,-.17,1.79),(0,-.12,2.03),(-.07,.01,2.2)],
         [.09,.075,.055],"639A54")
    leaf("Chikorita signature long leaf",(-.07,.01,2.12),(-1.1,.13,2.76),.31,"7BAC5B",bend=.24)
    tube("Chikorita leaf central vein",[(-.07,-.025,2.13),(-.58,-.245,2.45),(-1.06,.07,2.73)],
         [.014,.012,.004],"ADC981",sides=10)


def build_cyndaquil():
    cream="F7DEA5"; dark="38777B"
    parts=[ell("Cyndaquil cream torso",(0,.10,.72),(.48,.48,.62),cream),
           ell("Cyndaquil rounded head",(0,-.23,1.25),(.48,.51,.43),cream)]
    parts.append(tube("Cyndaquil long pointed snout",[(0,-.51,1.2),(0,-.79,1.09),(0,-1.05,1.02)],
                       [(.31,.24),(.22,.17),(.08,.08)],cream,sides=24))
    for s in (-1,1):
        parts.append(ell(f"Cyndaquil foot {s}",(s*.30,-.1,.16),(.19,.27,.17),cream))
        parts.append(tube(f"Cyndaquil arm {s}",[(s*.35,-.08,.9),(s*.47,-.27,.71),(s*.40,-.39,.62)],
                          [.12,.10,.085],cream))
    union("Cyndaquil cream skin",parts,cream,voxel=.032)
    ell("Cyndaquil blue back",(0,.29,.91),(.455,.39,.65),dark)
    ell("Cyndaquil blue crown",(0,-.10,1.45),(.43,.42,.24),dark)
    for s in (-1,1):
        tube(f"Cyndaquil closed smiling eye {s}",[(s*.26,-.659,1.30),(s*.32,-.642,1.32),(s*.38,-.601,1.30)],
             [.019,.019,.016],"263D42",sides=10)
    ell("Cyndaquil tiny nose",(0,-1.113,1.026),(.075,.021,.048),"3E5552")
    # The orange-and-yellow fan is attached to the dark dorsal saddle.
    for i,(x,z,h) in enumerate(((-.46,.92,.74),(-.27,1.18,.83),(0,1.24,.99),(.28,1.17,.87),(.48,.9,.71))):
        _flame(f"Cyndaquil dorsal fire {i+1}",(x,.47,z),h,.19)


def build_totodile():
    blue="6FBBCB"
    body=(0,.05,.77); bs=(.48,.39,.61)
    head=(0,-.04,1.66); hs=(.58,.46,.54)
    parts=[ell("Totodile body",body,bs,blue),ell("Totodile cranium",head,hs,blue)]
    for s in (-1,1):
        parts.append(ell(f"Totodile eye brow {s}",(s*.30,-.20,1.91),(.26,.28,.33),blue))
        parts.append(tube(f"Totodile arm {s}",[(s*.37,0,1.04),(s*.62,-.12,.92),(s*.73,-.28,1.02)],
                          [.17,.15,.14],blue))
        parts.append(ell(f"Totodile foot {s}",(s*.36,-.14,.17),(.25,.35,.18),blue))
        _claws(f"Totodile toes {s}",s*.36,-.44,.13,.09,.06)
    parts.append(tube("Totodile thick tail",[(0,.34,.43),(.16,.69,.37),(.35,1.03,.46),(.42,1.18,.73)],
                       [.28,.24,.15,.012],blue,sides=20))
    skin_mesh=union("Totodile blue skin",parts,blue,voxel=.034)
    ell("Totodile mouth interior",(0,-.52,1.33),(.47,.36,.24),"61353D")
    ell("Totodile long upper snout",(0,-.57,1.55),(.55,.48,.21),blue)
    ell("Totodile lower jaw",(0,-.55,1.11),(.48,.43,.14),"95D3D6")
    for s in (-1,1):
        eye(f"Totodile ruby eye {s}",(s*.30,-.20,1.91),(.26,.28,.33),s*.30,1.96,(.14,.22),"C7585B")
        ell(f"Totodile nostril {s}",(s*.27,-1.001,1.59),(.028,.017,.023),"39787E")
        for i in range(2):
            x=s*(.25+i*.13)
            cone(f"Totodile upper tooth {s} {i}",(x,-.86+i*.06,1.43),(x,-.86+i*.06,1.27),.058,"FFF7DF")
        cone(f"Totodile lower fang {s}",(s*.31,-.88,1.16),(s*.31,-.88,1.29),.053,"FFF7DF")
    ell("Totodile pink tongue",(0,-.80,1.235),(.28,.16,.075),"CE7B88")
    _polygon_patch("Totodile yellow V bib",body,bs,[(-.31,1.09),(0,.76),(.31,1.09),(0,1.15)],"F4DD9A",skin_mesh)
    for i,(y,z) in enumerate(((.38,1.47),(.48,1.18),(.57,.88),(.85,.55),(1.04,.55))):
        cone(f"Totodile red dorsal scute {i}",(0,y,z),(0,y+.15,z+.30),.16,"CE5961")


def build_treecko():
    green="A0CB69"; tail="72A676"
    body=(0,.04,.91); bs=(.28,.25,.57)
    head=(0,-.05,1.78); hs=(.43,.34,.45)
    parts=[ell("Treecko slim body",body,bs,green),ell("Treecko tapered lower head",head,hs,green),
           tube("Treecko long neck",[(0,.02,1.18),(0,-.02,1.48),(0,-.06,1.65)],[.17,.16,.23],green),
           tube("Treecko left split crown",[(-.16,.05,1.92),(-.21,.06,2.22),(-.22,.07,2.43)],
                [.24,.19,.04],green,sides=24),
           tube("Treecko right split crown",[(.16,-.025,1.94),(.20,.02,2.27),(.17,.04,2.53)],
                [.25,.19,.035],green,sides=24)]
    for s in (-1,1):
        parts.append(tube(f"Treecko long leg {s}",[(s*.17,.03,.51),(s*.26,-.01,.30),(s*.29,-.16,.12)],
                          [.13,.105,.10],green))
        parts.append(tube(f"Treecko outstretched arm {s}",[(s*.20,0,1.20),(s*.51,-.04,1.18),(s*.77,-.1,1.26)],
                          [.10,.075,.08],green))
        for i in range(3):
            x=s*(.19+i*.11)
            parts.append(tube(f"Treecko toe {s} {i}",[(s*.29,-.17,.12),(x,-.35,.11),(x,-.46,.12)],
                              [.06,.065,.052],green,sides=12))
            hx=s*(.68+i*.15)
            hz=1.42+(.11 if i==1 else 0)
            parts.append(tube(f"Treecko finger {s} {i}",[(s*.77,-.10,1.26),(hx,-.16,hz),(hx,-.20,hz+.04)],
                              [.038,.035,.032],green,sides=12))
    skin_mesh=union("Treecko soft gecko skin",parts,green,voxel=.023)
    for s in (-1,1):
        for i in range(3):
            x=s*(.19+i*.11)
            ell(f"Treecko separate round toe pad {s} {i}",(x,-.465,.12),(.072,.073,.065),green)
            hx=s*(.68+i*.15)
            hz=1.42+(.11 if i==1 else 0)
            ell(f"Treecko separate round finger pad {s} {i}",(hx,-.20,hz+.04),(.055,.05,.055),green)
    patch("Treecko red belly",body,bs,(0,.95),(.19,.43),"D67A89")
    _polygon_patch("Treecko fitted red throat",body,bs,
                   [(-.10,1.23),(-.085,1.53),(0,1.57),(.085,1.53),(.10,1.23)],"D67A89",skin_mesh)
    # The large flattened curled tail is broad and heavy in the official design.
    tube("Treecko fleshy hooked tail",[(0,.22,.59),(.29,.47,.52),(.62,.54,.49),(.89,.48,.62),(.87,.43,.85)],
         [(.19,.15),(.31,.19),(.36,.19),(.23,.15),(.075,.07)],tail,sides=24)
    for s in (-1,1):
        x,z=s*.27,1.91
        eye(f"Treecko golden eye {s}",head,hs,x,z,(.135,.205),"F3D362",white=False)
        y=front(head,hs,x,z)-.018
        normal=Vector(((x-head[0])/hs[0]**2,(y-head[1])/hs[1]**2,(z-head[2])/hs[2]**2)).normalized()
        pupil=ell(f"Treecko vertical slit pupil {s}",Vector((x,y,z))+normal*.043,(.031,.018,.135),"263B31")
        eye_rotation=Vector((0,-1,0)).rotation_difference(normal)
        pupil.rotation_euler=eye_rotation.to_euler()
        highlight=ell(f"Treecko pupil glint {s}",Vector((x,y,z))+normal*.065+eye_rotation@Vector((-.015,0,.075)),
                      (.022,.01,.037),"FFFBE8")
        highlight.rotation_euler=eye_rotation.to_euler()
    smile("Treecko knowing smile",(0,-.363,1.57),.43)
    ell("Treecko nostril left",(-.09,-.385,1.69),(.016,.010,.018),"50764B")
    ell("Treecko nostril right",(.09,-.385,1.69),(.016,.010,.018),"50764B")


def build_torchic():
    orange="F3A14C"; gold="F9D26F"
    head=(0,-.06,1.52); hs=(.54,.46,.54)
    ell("Torchic round body",(0,.08,.80),(.47,.42,.53),orange)
    ell("Torchic round head",head,hs,orange)
    for s in (-1,1):
        ell(f"Torchic pale shoulder feathers {s}",(s*.38,.01,1.01),(.21,.22,.20),gold,rot=(0,s*23,0))
        for j in range(3):
            cone(f"Torchic collar feather {s} {j}",(s*(.27+j*.085),-.14+j*.10,1.06),
                 (s*(.35+j*.10),-.20+j*.10,.79+j*.045),.105,gold)
        tube(f"Torchic leg {s}",[(s*.21,.03,.43),(s*.21,-.02,.21)],[.075,.067],gold)
        for j in (-1,0,1):
            tube(f"Torchic toe {s} {j}",[(s*.21,-.02,.12),(s*.21+j*.10,-.24,.10),
                 (s*.21+j*.14,-.34+.05*abs(j),.1)],[.055,.05,.025],gold,sides=12)
        eye(f"Torchic shiny dark eye {s}",head,hs,s*.235,1.59,(.105,.16),"28292C",white=False)
        outline=[(s*x,z) for x,z in ((.13,1.13),(.40,1.12),(.60,.98),(.44,1.00),
                 (.53,.84),(.37,.91),(.36,.73),(.25,.84),(.17,.78))]
        _feather_cutout(f"Torchic layered feather ruff {s}",outline,-.31,.10,gold)
    ell("Torchic upper beak",(0,-.52,1.35),(.17,.18,.09),gold)
    ell("Torchic lower beak",(0,-.535,1.29),(.13,.13,.045),"E9B653")
    for j,(x,tipx,h) in enumerate(((-.13,-.27,.39),(0,.12,.63),(.16,.47,.38))):
        tube(f"Torchic golden crown plume {j}",[(x,-.005,1.91),(x*.85,.025,2.08),(tipx,.03,1.96+h)],
             [(.115,.07),(.13,.075),(.008,.008)],gold,sides=20)
    cone("Torchic rear tail plume",(0,.40,.75),(0,.69,1.03),.18,orange)


def build_mudkip():
    blue="77BFD8"; fin="467FBA"; orange="F3A25E"
    head=(0,-.33,1.09); hs=(.73,.55,.57)
    parts=[ell("Mudkip body",(0,.31,.63),(.53,.65,.42),blue),
           ell("Mudkip broad face",head,hs,blue)]
    for s in (-1,1):
        for j,y in enumerate((-.22,.65)):
            parts.append(ell(f"Mudkip foot {s} {j}",(s*.42,y,.22),(.24,.28,.23),blue))
    skin_mesh=union("Mudkip smooth blue skin",parts,blue,voxel=.035)
    _polygon_patch("Mudkip fitted pale lower jaw",head,hs,
                   [(-.58,.94),(-.47,.80),(0,.74),(.47,.80),(.58,.94),(.37,.965),(-.37,.965)],"D6E6E8",skin_mesh)
    # A vertically flattened fish fin forms the tall central head crest.
    tube("Mudkip tall head fin",[(0,-.16,1.51),(0,-.06,1.84),(0,.05,2.12),(0,.13,2.27)],
         [(.085,.34),(.09,.32),(.085,.23),(.06,.12)],fin,sides=20)
    ell("Mudkip rounded fin tip",(0,.13,2.27),(.06,.12,.11),fin)
    tube("Mudkip lighter fin leading edge",[(0,-.42,1.58),(0,-.34,1.84),(0,-.17,2.12),(0,.13,2.30)],
         [.032,.029,.023,.005],"98D6E3",sides=12)
    # Tail is a broad, upright flattened paddle behind the little body.
    ell("Mudkip pale tail paddle",(0,1.02,.85),(.40,.095,.57),"C0DCE1",rot=(-26,0,0))
    for s in (-1,1):
        eye(f"Mudkip glossy eye {s}",head,hs,s*.34,1.21,(.12,.16),"292E36",white=False)
        ell(f"Mudkip orange cheek {s}",(s*.68,-.30,1.04),(.18,.14,.30),orange)
        for j in range(3):
            start=(s*.68,-.29,1.17-j*.13)
            end=(s*(1.01-.07*abs(j-1)),-.26,1.24-j*.18)
            tube(f"Mudkip cheek gill {s} {j}",[start,end],[.087,.012],orange,sides=16)
    points=[]
    for x,z in ((-.54,.96),(-.28,.935),(0,.925),(.28,.935),(.54,.96)):
        points.append((x,front(head,hs,x,z)-.013,z))
    tube("Mudkip broad mouth line",points,[.013]*len(points),"39535D",sides=10)


BUILDERS = {
    "Bulbasaur": build_bulbasaur,
    "Charmander": build_charmander,
    "Squirtle": build_squirtle,
    "Chikorita": build_chikorita,
    "Cyndaquil": build_cyndaquil,
    "Totodile": build_totodile,
    "Treecko": build_treecko,
    "Torchic": build_torchic,
    "Mudkip": build_mudkip,
}
