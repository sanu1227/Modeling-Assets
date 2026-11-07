"""Original-proportion modeled first partners from Alola, Galar and Paldea."""
from pokemon_common import *
from mathutils.bvhtree import BVHTree


def _mask(name,head,size,outline,color,skin=None):
    """Closed curved graphic fitted to the face, with a deliberate crisp silhouette."""
    if skin:
        signed=sum(p[0]*outline[(i+1)%len(outline)][1]-outline[(i+1)%len(outline)][0]*p[1] for i,p in enumerate(outline))
        if signed<0:outline=list(reversed(outline))
        rim=[]
        for i,p in enumerate(outline):
            q=outline[(i+1)%len(outline)]
            rim.extend([(p[0]+(q[0]-p[0])*j/8,p[1]+(q[1]-p[1])*j/8) for j in range(8)])
        outline=rim
        tree=BVHTree.FromObject(skin,bpy.context.evaluated_depsgraph_get())
        inv=skin.matrix_world.inverted()
    def surface(x,z):
        if skin:
            hit,_,_,_=tree.ray_cast(inv@Vector((x,-5,z)),inv.to_3x3()@Vector((0,1,0)))
            if hit is not None:return (skin.matrix_world@hit).y-.010
        return front(head,size,x,z)-.018
    x=sum(p[0] for p in outline)/len(outline);z=sum(p[1] for p in outline)/len(outline)
    n=len(outline);vertices=[(x,surface(x,z),z)]
    for row in range(1,9):
        for px,pz in outline:
            xx=x+(px-x)*row/8;zz=z+(pz-z)*row/8
            vertices.append((xx,surface(xx,zz),zz))
    faces=[(0,1+j,1+(j+1)%n) for j in range(n)]
    for row in range(7):
        for j in range(n):
            a=1+row*n+j;b=1+row*n+(j+1)%n;faces.append((a,b,b+n,a+n))
    obj=mesh(name,vertices,faces,color)
    mod=obj.modifiers.new('Closed face marking','SOLIDIFY');mod.thickness=.014;mod.offset=-1;apply(obj,mod)
    return obj


def build_rowlet():
    tan='B98C63'; cream='F8F0DE'; green='288E74'
    c=(0,0,1.27);s=(.87,.64,1.00)
    ell('Round owl body',c,s,tan)
    patch('Ivory breast',c,s,(0,.72),(.64,.48),cream)
    for side in (-1,1):
        patch('Heart face lobe',c,s,(side*.33,1.59),(.40,.49),cream)
        eye('Oval owl eye',c,s,side*.34,1.62,(.105,.165),'2B2924',False)
        ell('Folded wing',(side*.70,-.04,1.02),(.23,.43,.56),tan,rot=(0,side*-17,0))
        foot=ell('Orange owl foot',(side*.35,-.13,.24),(.19,.29,.14),'C58049')
        for j in (-1,1):cone('Owl toe',(side*.35+j*.07,-.29,.24),(side*.35+j*.14,-.46,.12),.075,'C58049')
        leaf('Bow tie leaf',(side*.03,-.66,1.03),(side*.57,-.64,1.05),.23,green,.04)
        tube('Leaf bow vein',[(side*.08,-.714,1.03),(side*.27,-.72,1.07),(side*.50,-.67,1.05)],[.014,.012,.005],'247560',10)
    ell('Bow knot',(0,-.66,1.03),(.09,.07,.11),green)
    ell('Ivory beak',(0,-.679,1.61),(.15,.15,.26),'EEE9D7')
    cone('Orange lower beak',(0,-.75,1.43),(0,-.78,1.28),.115,'C27846')
    for side in (-1,1):leaf('Small tail',(0,.45,.57),(side*.20,.86,.48),.18,tan,.01)


def build_litten():
    black='30363F';red='BF413D';grey='A5ABB0'
    head=(0,-.55,1.44);hs=(.65,.49,.59)
    parts=[ell('Cat body',(0,.28,1.05),(.47,.75,.45),black),ell('Head',head,hs,black)]
    for side in (-1,1):
        for y,z in [(-.25,.55),(.72,.51)]:
            parts.append(ell('Cat leg',(side*.32,y,z),(.145,.18,.43),black))
            parts.append(ell('Cat paw',(side*.32,y-.10,.19),(.18,.25,.13),black))
    union('Litten continuous skin',parts,black,.035)
    for side in (-1,1):
        leaf('Large pointed ear',(side*.38,-.42,1.72),(side*.51,-.28,2.42),.26,black,.02)
        leaf('Gray inner ear',(side*.39,-.525,1.86),(side*.50,-.375,2.29),.16,grey,.025)
        eye('Yellow cat eye',head,hs,side*.28,1.42,(.21,.185),'EACB41',False)
        y=front(head,hs,side*.28,1.42)
        ell('Thin slit pupil',(side*.28,y-.061,1.42),(.023,.011,.145),'222631')
        _mask('Flat upper cat eyelid',head,hs,[(side*.07,1.56),(side*.47,1.60),(side*.47,1.67),(side*.08,1.68)],black)
        tube('Red brow',[(side*.03,-1.005,1.63),(side*.29,-1.008,1.66),(side*.49,-.90,1.67)],[.025,.042,.012],red)
        leaf('Whisker upper',(side*.39,-.83,1.22),(side*.92,-.86,1.23),.12,red,.01)
        leaf('Whisker lower',(side*.43,-.80,1.19),(side*.80,-.83,1.04),.11,red,.01)
        for z in (.44,.70):
            ell('Red front leg stripe',(side*.32,-.265,z),(.154,.186,.074),red)
        ell('Hind red stocking',(side*.32,.70,.38),(.153,.19,.115),red)
    _mask('Angular forehead cross',head,hs,[(-.05,1.99),(.05,1.99),(.075,1.81),(.34,1.77),(.08,1.73),(.055,1.60),(-.055,1.60),(-.08,1.73),(-.34,1.77),(-.075,1.81)],red)
    ell('Muzzle',(0,-.985,1.18),(.245,.10,.12),red)
    ell('Little dark nose',(0,-1.09,1.22),(.05,.024,.035),'20272E')
    smile('Cat mouth',(0,-1.09,1.12),.22)
    tube('Raised curved tail',[(0,.84,1.13),(.12,1.18,1.36),(.36,1.27,1.74),(.39,1.22,2.10),(.24,1.17,2.29)],[.12,.105,.085,.075,.06],black,20,7)
    for x,z in [(.10,2.47),(.29,2.54),(.42,2.42)]:cone('Three tail tips',(.24,1.17,2.20),(x,1.18,z),.065,black)


def build_popplio():
    blue='3D64A7';light='72C3D9';pink='B96991'
    head=(0,-.26,1.72);hs=(.59,.52,.61)
    parts=[ell('Sea lion chest',(0,.06,.88),(.39,.40,.65),blue),ell('Sea lion head',head,hs,blue)]
    union('Popplio smooth skin',parts,blue,.035)
    for side in (-1,1):
        ell('Tiny ear',(side*.55,-.08,1.72),(.24,.22,.14),blue,rot=(0,side*-18,0))
        ell('Long front flipper',(side*.55,-.31,.29),(.57,.28,.13),blue,rot=(0,0,side*-22))
        for j in (0,1):
            tube('Flipper nail arc',[(side*(.72+j*.16),-.48,.30),(side*(.78+j*.16),-.51,.35),(side*(.83+j*.16),-.46,.38)],[.025]*3,'E5E7D9',12)
        ell('Tail flipper',(side*.24,.56,.19),(.32,.48,.13),blue,rot=(0,0,side*28))
        eye('Sea lion eye',head,hs,side*.26,1.85,(.13,.205),'222A37',True)
    # Closed scalloped collar with distinct ruffle lobes.
    for j in range(10):
        a=2*math.pi*j/10
        ell('Scalloped blue neck frill',(.39*math.cos(a),.02+.30*math.sin(a),1.21),(.22,.19,.085),light,rot=(10*math.sin(a),-14*math.cos(a),0))
    ell('Ivory muzzle',(0,-.737,1.60),(.34,.18,.25),'F4EDDE')
    ell('Happy open mouth',(0,-.88,1.46),(.19,.045,.16),'513549')
    ell('Pink tongue',(0,-.922,1.40),(.13,.018,.065),'D782A2')
    ell('Pink round nose',(0,-.97,1.82),(.20,.18,.18),pink)
    for side in (-1,1):
        for j in range(2):tube('Muzzle whisker',[(side*.20,-.886,1.68+j*.065),(side*.29,-.842,1.70+j*.065)],[.009,.009],'425370',8,2)


def build_grookey():
    green='8FB85E';dark='5E813D';orange='C27C3D';cream='E5DA83';brown='79562D'
    h=(0,-.17,1.64);hs=(.64,.50,.62)
    parts=[ell('Monkey torso',(0,.14,.79),(.43,.39,.55),green),ell('Monkey head',h,hs,green)]
    for side in (-1,1):
        parts.append(ell('Bent monkey thigh',(side*.31,.16,.37),(.25,.26,.27),green))
        parts.append(tube('Long monkey arm',[(side*.37,.01,.99),(side*.53,-.12,.68),(side*.48,-.32,.35)],[.14,.12,.10],green))
    union('Grookey green skin',parts,green,.035)
    for side in (-1,1):
        ell('Monkey ear',(side*.65,-.08,1.58),(.25,.16,.30),brown,rot=(0,side*20,0))
        ell('Orange ear interior',(side*.67,-.208,1.58),(.16,.045,.21),orange,rot=(0,side*20,0))
        patch('Yellow face mask',h,hs,(side*.265,1.68),(.245,.345),cream)
        eye('Monkey eye',h,hs,side*.27,1.69,(.13,.20),'292B25',True)
        ell('Orange hand',(side*.48,-.35,.30),(.14,.14,.17),orange)
        for j in range(3):ell('Monkey fingers',(side*.48+(j-1)*.075,-.45,.26),(.035,.10,.048),orange)
        ell('Small monkey foot',(side*.30,-.04,.15),(.17,.26,.10),orange)
    ell('Monkey muzzle',(0,-.68,1.43),(.25,.19,.23),orange)
    for side in (-1,1):ell('Nostril',(side*.063,-.859,1.49),(.014,.010,.02),brown)
    smile('Monkey smile',(0,-.851,1.34),.24,brown)
    tube('Curled brown tail',[(0,.44,.57),(-.48,.66,.60),(-.80,.66,.91),(-.76,.64,1.20),(-.59,.62,1.30)],[.10,.10,.10,.09,.065],brown,20,7)
    leaf('Head leaf left',(0,0,2.11),(-.46,.02,2.66),.19,green,.02)
    leaf('Head leaf right',(.02,.03,2.10),(.31,.07,2.82),.19,green,.02)
    tube('Wooden hair stick',[(-.43,.12,2.20),(.05,.14,2.24),(.49,.16,2.27)],[.075,.073,.067],brown,20)
    ell('Stick cut end',(-.44,.12,2.20),(.018,.07,.07),'C49A5C',rot=(0,0,90))


def build_scorbunny():
    white='F7F5ED';orange='D56E39';yellow='E8B95D'
    h=(0,-.08,1.74);hs=(.56,.39,.46)
    parts=[ell('Slender rabbit body',(0,.08,.96),(.30,.25,.43),white),ell('Rabbit head',h,hs,white)]
    for side in (-1,1):
        parts.append(tube('Rabbit leg',[(side*.16,.08,.73),(side*.23,.02,.45),(side*.24,-.05,.20)],[.115,.10,.10],white))
        parts.append(tube('Outstretched arm',[(side*.23,.04,1.20),(side*.45,-.02,1.13),(side*.63,-.06,1.24)],[.10,.085,.075],white))
        parts.append(ell('Hand',(side*.64,-.07,1.24),(.14,.11,.09),white,rot=(0,side*-18,0)))
    union('Scorbunny white skin',parts,white,.028)
    for side in (-1,1):
        leaf('Long rabbit ear',(side*.22,.02,2.05),(side*.44,.09,3.15),.18,white,.01)
        leaf('Orange ear tip',(side*.31,.02,2.63),(side*.44,.09,3.15),.158,orange,.015)
        leaf('Yellow inner ear',(side*.23,-.075,2.16),(side*.36,-.025,2.75),.075,yellow,.01)
        eye('Rabbit eye',h,hs,side*.245,1.76,(.105,.15),'713B2A',False)
        ell('Orange running foot',(side*.24,-.18,.14),(.16,.30,.115),orange)
        for x in (-.055,.055):tube('Foot toe groove',[(side*.24+x,-.437,.16),(side*.24+x,-.36,.235)],[.009,.008],'A24B2C',8)
        for j in range(2):leaf('Cheek fur',(side*.43,-.08,1.53+j*.10),(side*(.70-j*.08),-.10,1.58+j*.17),.08,white,.02)
    patch('Yellow nose band',h,hs,(0,1.79),(.19,.092),yellow)
    ell('Little rabbit nose',(0,-.495,1.64),(.032,.023,.026),'CF7853')
    patch('Happy open mouth',h,hs,(0,1.49),(.145,.11),'623C42')
    patch('Smile tongue',h,hs,(0,1.44),(.09,.032),'CE858D')
    ell('Neck orange patch',(0,-.173,1.25),(.075,.02,.09),orange)
    ell('Rabbit tail',(0,.36,.76),(.17,.14,.17),white)


def build_sobble():
    blue='75BCD5';dark='246C9B';cream='CAE7E5';yellow='EBD35B'
    h=(0,-.17,1.49);hs=(.66,.52,.60)
    ell('Large chameleon head',h,hs,blue)
    ell('Small chameleon torso',(0,.11,.63),(.29,.29,.41),blue)
    patch('Pale throat',(0,.11,.63),(.29,.29,.41),(0,.67),(.20,.30),cream)
    for side in (-1,1):
        patch('Pale face',h,hs,(side*.27,1.46),(.245,.30),cream)
        eye('Watery chameleon eye',h,hs,side*.29,1.52,(.14,.24),'2A72A5',True)
        patch('Blue cheek dot',h,hs,(side*.46,1.23),(.095,.10),dark)
        tube('Thin chameleon arm',[(side*.23,.02,.82),(side*.35,-.09,.58),(side*.29,-.31,.30)],[.067,.055,.05],blue)
        ell('Bent haunch',(side*.23,.16,.31),(.15,.20,.16),blue)
        for j in range(3):
            tube('Splayed finger',[(side*.29,-.30,.27),(side*(.25+j*.095),-.43,.23),(side*(.25+j*.12),-.49,.25)],[.039,.03,.018],blue,12,3)
            tube('Splayed toe',[(side*.26,.04,.22),(side*(.27+j*.10),-.10,.17),(side*(.30+j*.12),-.16,.17)],[.045,.03,.02],blue,12,3)
    patch('Open uncertain mouth',h,hs,(0,1.13),(.20,.095),'5D4757')
    patch('Small tongue',h,hs,(0,1.09),(.13,.028),'C98C9E')
    leaf('Tall head fin blue edge',(0,0,1.98),(.15,.03,2.94),.25,dark,.015)
    leaf('Tall yellow head fin',(0,-.045,2.03),(.15,-.02,2.90),.22,yellow,.015)
    leaf('Fin lower lobe',(.02,.015,2.13),(.40,.035,2.41),.125,yellow,.015)
    tube('Spiral chameleon tail',[(0,.34,.49),(.46,.64,.43),(.79,.62,.70),(.86,.57,1.05),(.66,.56,1.27),(.40,.55,1.24),(.28,.53,1.03),(.39,.51,.90),(.55,.49,.96)],[.13,.16,.18,.18,.16,.14,.12,.09,.055],blue,24,8)
    ell('Tail dark center',(.48,.365,1.04),(.15,.03,.16),dark)


def build_sprigatito():
    pale='B6D897';green='529747';dark='3A7F3E';pink='CF6C8B'
    h=(0,-.48,1.51);hs=(.66,.47,.57)
    parts=[ell('Cat body',(0,.22,.83),(.38,.57,.37),pale),ell('Cat head',h,hs,pale)]
    for side in (-1,1):
        for y in (-.13,.51):
            parts.append(ell('Slender cat leg',(side*.24,y,.43),(.12,.15,.36),pale))
            parts.append(ell('Rounded cat paw',(side*.24,y-.06,.14),(.14,.20,.12),pale))
    skin=union('Sprigatito pale skin',parts,pale,.03)
    for side in (-1,1):
        leaf('Leaf-shaped cat ear',(side*.36,-.30,1.87),(side*.55,-.20,2.53),.27,dark,.02)
        leaf('Pale ear interior',(side*.37,-.405,1.94),(side*.55,-.29,2.40),.17,pale,.025)
        _mask('Pointed green face leaf',h,hs,[(side*.015,1.42),(side*.08,1.70),(side*.27,1.96),(side*.42,1.91),(side*.38,1.67),(side*.51,1.51),(side*.35,1.27),(side*.09,1.32)],green,skin)
        eye('Pink cat eye',h,hs,side*.285,1.52,(.20,.25),pink,True)
        for j in range(3):
            leaf('Cheek fur',(side*.48,-.42,1.36-j*.09),(side*(.79-j*.045),-.35,1.44-j*.18),.11,pale,.015)
        leaf('Green neck ruff upper',(0,-.32,1.01),(side*.38,-.35,.94),.15,dark,.02)
        leaf('Green neck ruff lower',(0,-.34,1.02),(side*.20,-.39,.67),.13,green,.02)
    patch('Green nose bridge',h,hs,(0,1.38),(.19,.15),green)
    ell('Pink kitten nose',(0,-.965,1.37),(.065,.025,.039),pink)
    smile('Kitten smile',(0,-.928,1.27),.22,'46723B')
    tube('Plush upright cat tail',[(0,.65,.83),(.30,.90,1.03),(.51,.93,1.34),(.43,.90,1.58)],[.15,.20,.24,.09],pale,24,7)
    leaf('Green tail point',(.45,.91,1.31),(.39,.89,1.79),.23,green,.01)
    for side in (-1,1):
        for j in (-1,1):tube('Front toe seam',[(side*.24+j*.044,-.375,.12),(side*.24+j*.044,-.34,.21)],[.006,.005],'8BB776',8)


def build_fuecoco():
    red='C8533D';cream='F5E9C9';yellow='DBBD51';claw='4C515A'
    h=(0,-.08,1.55);hs=(.69,.56,.68)
    parts=[ell('Stocky crocodile body',(0,.16,.78),(.60,.49,.70),red),ell('Round crocodile cranium',h,hs,red)]
    for side in (-1,1):
        parts.append(ell('Crocodile haunch',(side*.46,.11,.37),(.28,.30,.35),red))
        parts.append(ell('Short crocodile arm',(side*.54,-.23,.87),(.17,.18,.25),red,rot=(0,side*22,0)))
    parts.append(tube('Broad crocodile tail',[(0,.48,.59),(.43,.77,.49),(.77,.85,.45),(.98,.88,.60)],[.32,.25,.13,.012],red,24,7))
    union('Fuecoco red skin',parts,red,.035)
    patch('Cream lower belly',(0,.16,.78),(.60,.49,.70),(0,.50),(.41,.33),cream)
    # Face mask and broad horizontal snout retain the crocodile silhouette.
    patch('Cream face mask',h,hs,(0,1.71),(.57,.46),cream)
    for side in (-1,1):eye('Vertical crocodile eye',h,hs,side*.30,1.89,(.065,.145),'393B41',True)
    ell('Open broad mouth',(0,-.59,1.23),(.50,.22,.33),'593E43')
    ell('Rounded lower jaw',(0,-.48,1.01),(.53,.28,.17),red)
    ell('Mouth tongue',(0,-.763,1.09),(.30,.055,.11),'BC7978')
    ell('Broad cream upper muzzle',(0,-.70,1.56),(.60,.34,.22),cream)
    for side in (-1,1):
        ell('Nostril',(side*.20,-1.018,1.65),(.043,.014,.034),'383739')
        cone('Upper tooth',(side*.34,-.83,1.43),(side*.32,-.86,1.28),.07,cream)
        cone('Lower tooth',(side*.28,-.69,1.09),(side*.27,-.71,1.23),.07,cream)
        for j in (-1,1):cone('Dark foot claw',(side*.47+j*.085,-.08,.21),(side*.47+j*.085,-.34,.08),.105,claw)
        for j in (-1,1):tube('Arm finger seam',[(side*.60+j*.04,-.36,.84),(side*.60+j*.04,-.39,.92)],[.008,.006],'A24435',8)
    # Rectangular belly scale with rounded corners, actual solid geometry.
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,-.366,.73))
    plate=finish(bpy.context.object,'Yellow rectangular belly scale',yellow);plate.scale=(.44,.06,.28)
    active(plate);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=plate.modifiers.new('Soft scale edges','BEVEL');mod.width=.045;mod.segments=4;apply(plate,mod)
    leaf('Large yellow head tuft',(-.07,.02,2.10),(-.25,.01,2.70),.15,yellow,.015)
    leaf('Small yellow head tuft',(.04,.03,2.12),(.25,.04,2.52),.095,'E9CC61',.015)


def build_quaxly():
    white='F4F4EA';blue='63B8C6';dark='247B99';yellow='E5C753'
    h=(0,-.08,1.61);hs=(.54,.43,.59)
    parts=[ell('Duck body',(0,.12,.78),(.43,.39,.45),white),ell('Duck head',h,hs,white)]
    union('Quaxly white skin',parts,white,.03)
    for side in (-1,1):
        ell('Duck wing',(side*.40,.04,.88),(.29,.20,.14),white,rot=(0,side*25,side*15))
        tube('Blue duck ankle',[(side*.19,.08,.48),(side*.20,-.01,.18)],[.075,.072],blue)
        # Fan-shaped three-toed feet, fused into a solid webbed paddle.
        toes=[ell('Duck web',(side*.20,-.14,.13),(.22,.28,.065),blue)]
        for j in (-1,0,1):toes.append(ell('Webbed toe',(side*.20+j*.13,-.29,.12),(.095,.20,.058),blue,rot=(0,0,-j*15)))
        union('Webbed foot',toes,blue,.018)
        eye('Blue duck eye',h,hs,side*.215,1.62,(.11,.205),dark,True)
    ell('Yellow upper duck bill',(0,-.538,1.35),(.31,.25,.13),yellow)
    ell('Yellow lower duck bill',(0,-.55,1.27),(.28,.22,.075),yellow)
    tube('Duck bill seam',[(-.26,-.68,1.30),(0,-.792,1.29),(.26,-.68,1.30)],[.008,.008,.008],'927B34',10)
    for side in (-1,1):ell('Bill nostril',(side*.11,-.717,1.43),(.018,.013,.012),'A08C43')
    # Side-swept, full-bodied turquoise pompadour with a real rolled tip.
    hair=[ell('Water hair cap',(0,-.02,2.06),(.66,.51,.41),blue),ell('Left hair wave',(-.43,-.12,1.95),(.27,.39,.16),blue),
          tube('Swept hair curl',[(.31,.08,2.14),(.56,.06,2.17),(.69,.03,2.35),(.65,.01,2.43)],[.24,.19,.11,.015],blue,24,7)]
    union('Sculpted water pompadour',hair,blue,.025)
    tube('White water shine',[(-.27,-.477,2.18),(-.14,-.516,2.12),(0,-.529,2.13),(.14,-.501,2.20)],[.025,.032,.030,.018],'DFF5E9',16)
    ell('Duck breast tuft',(0,-.254,1.02),(.12,.10,.16),white)
    leaf('Small duck tail',(0,.37,.77),(.04,.77,.87),.20,white,.01)


BUILDERS = {name: globals()['build_'+name.lower()] for name in ('Rowlet','Litten','Popplio','Grookey','Scorbunny','Sobble','Sprigatito','Fuecoco','Quaxly')}
