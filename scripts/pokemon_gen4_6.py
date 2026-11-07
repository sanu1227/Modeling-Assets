"""Hand-authored first-partner models matched to official reference silhouettes.

All characters face -Y. Materials and closed-mesh primitives are supplied by
pokemon_common; the gallery builder owns collections, exports and presentation.
"""
import math

from pokemon_common import *
import pokemon_common as common


def _fuse(name, stems, color):
    """Smooth connected skin volumes without merging eyes or colored markings."""
    parts = [o for o in common.COLLECTION.objects if any(o.name.startswith(s) for s in stems)]
    if len(parts) > 1:
        union(name, parts, color, voxel=.024)


def _surface_polygon(name, center, scale, outline, color, depth=.025):
    """Closed colored inset with a deliberate angular outline on curved skin."""
    x=sum(p[0] for p in outline)/len(outline)
    z=sum(p[1] for p in outline)/len(outline)
    verts=[(x,front(center,scale,x,z)-depth,z)]
    count=len(outline)
    for ring in range(1,13):
        t=ring/12
        for px,pz in outline:
            px,pz=x+(px-x)*t,z+(pz-z)*t
            verts.append((px,front(center,scale,px,pz)-depth,pz))
    faces=[(0,1+j,1+(j+1)%count) for j in range(count)]
    for ring in range(11):
        for j in range(count):
            a,b=1+ring*count+j,1+ring*count+(j+1)%count
            faces.append((a,b,b+count,a+count))
    obj=mesh(name,verts,faces,color)
    mod=obj.modifiers.new('Closed inset','SOLIDIFY')
    mod.thickness=.014
    mod.offset=-1
    apply(obj,mod)
    return obj


def build_turtwig():
    green, light, shell, seam = 'A1BE72', 'E8CF64', '9D845D', '3E3E38'
    ell('Turtwig body', (0,.24,.67), (.65,.82,.51), green)
    ell('Turtwig shell rim', (0,.38,.83), (.74,.84,.35), seam)
    ell('Turtwig earth shell', (0,.40,1.02), (.67,.77,.43), shell)
    # Raised engraved-looking plate divisions follow the curved carapace.
    tube('Turtwig shell central seam', [(0,-.20,1.24),(0,.07,1.43),(0,.43,1.46),(0,.85,1.36),(0,1.12,1.13)], [.014]*5, seam)
    for s in (-1,1):
        tube('Turtwig shell side seam', [(0,.36,1.46),(s*.32,.38,1.41),(s*.58,.41,1.26),(s*.66,.40,1.09)], [.015]*4, seam)
        for y in (-.27,.76):
            ell('Turtwig sturdy leg', (s*.46,y,.35), (.23,.27,.37), green)
            ell('Turtwig yellow toe', (s*.46,y-.09,.14), (.24,.28,.14), light)
    head, hs = (0,-.60,1.10), (.69,.60,.55)
    ell('Turtwig broad head', head, hs, green)
    patch('Turtwig golden lower jaw',head,hs,(0,.88),(.56,.23),light)
    ell('Turtwig brown crown', (0,-.48,1.59), (.31,.29,.09),shell)
    for x in (-.21,0,.21):
        cone('Turtwig crown zigzag',(x,-.672,1.60),(x+.02,-.739,1.49),.105,shell)
    for s in (-1,1):
        patch('Turtwig yellow eye ring',head,hs,(s*.41,1.22),(.16,.245),light)
        eye('Turtwig eye', head, hs, s*.41,1.23, (.095,.175), '242A2D',False)
        ell('Turtwig nostril', (s*.12,-1.193,1.005), (.026,.012,.022), seam)
        for y in (-.27,.76):
            for k in (-1,1):
                cone('Turtwig jagged ankle cuff',(s*.46+k*.085,y-.16,.21),(s*.46+k*.085,y-.17,.31),.055,light)
    mouth=[]
    for i in range(7):
        x=(i/6-.5)*.70
        z=.87+.14*(x/.35)**2
        mouth.append((x,front(head,hs,x,z)-.027,z))
    tube('Turtwig broad mouth line',mouth,[.009]*7,seam)
    tube('Turtwig sprout stem', [(0,-.48,1.55),(0,-.40,1.82),(.05,-.34,2.06)], [.075,.06,.035], '825A38')
    leaf('Turtwig left leaf', (.015,-.36,1.91),(-.51,-.36,2.49),.185,'68AA6C',.035)
    leaf('Turtwig right leaf', (.015,-.36,1.91),(.58,-.35,2.41),.185,'68AA6C',.035)
    tube('Turtwig tail', [(0,.90,.69),(0,1.21,.72),(.06,1.40,.81)], [.15,.095,.012],green)
    _fuse('Turtwig continuous skin', ['Turtwig body','Turtwig sturdy leg','Turtwig tail'], green)


def build_chimchar():
    orange, cream, dark = 'EA8548','F5D1A0','47302B'
    torso = ell('Chimchar torso',(0,.04,.91),(.32,.27,.58),orange)
    patch('Chimchar cream belly',(0,.04,.91),(.32,.27,.58),(0,.88),(.245,.42),cream)
    for s in (-1,1):
        tube('Chimchar leg',[(s*.23,.07,.60),(s*.39,-.02,.36),(s*.38,-.22,.18)],[.19,.15,.12],orange)
        ell('Chimchar foot',(s*.38,-.33,.13),(.23,.30,.13),cream)
        for k in (-1,0,1):
            tube('Chimchar toe line',[(s*.38+k*.08,-.52,.16),(s*.38+k*.08,-.59,.13)],[.008,.006],dark)
        # Slightly open arms give the little monkey its playful stance.
        tube('Chimchar arm',[(s*.25,.01,1.26),(s*.51,-.04,.94),(s*.62,-.26,.58)],[.115,.095,.070],orange)
        ell('Chimchar hand',(s*.63,-.28,.49),(.15,.12,.15),cream)
        for k in (-1,0,1):
            tube('Chimchar finger',[(s*.63+k*.075,-.31,.47),(s*.63+k*.10,-.39,.28)],[.039,.027],cream)
        ell('Chimchar ear',(s*.59,-.04,1.85),(.27,.18,.30),orange)
        ell('Chimchar ear rim',(s*.60,-.195,1.85),(.20,.045,.25),cream)
        ell('Chimchar ear inside',(s*.60,-.237,1.85),(.13,.025,.19),'C96462')
    head, hs = (0,-.09,1.88),(.60,.49,.56)
    ell('Chimchar head',head,hs,orange)
    # The cream mask has two brow lobes and a projecting rounded muzzle.
    for s in (-1,1):
        patch('Chimchar eye mask',head,hs,(s*.235,1.98),(.26,.30),cream)
        patch('Chimchar red eye outline',head,hs,(s*.25,2.025),(.15,.238),'D9736B')
    ell('Chimchar muzzle',(0,-.49,1.66),(.39,.23,.22),cream)
    for s in (-1,1):
        eye('Chimchar eye',head,hs,s*.25,1.995,(.112,.185),'313132')
        ell('Chimchar nostril',(s*.065,-.715,1.75),(.018,.012,.014),dark)
    smile('Chimchar smile',(0,-.724,1.62),.24,dark)
    tube('Chimchar crown curl',[(0,-.03,2.32),(.05,-.01,2.53),(.20,-.03,2.64),(.26,-.05,2.59)],[.20,.13,.055,.012],orange)
    for x,z in [(-.30,2.25),(-.07,2.31),(.19,2.29)]:
        _surface_polygon('Chimchar forehead hair point',head,hs,[(x-.12,z),(x+.09,z+.025),(x-.055,z-.15)],orange,.030)
    # Chimchar has a flame on its rump, rather than a long monkey tail.
    ell('Chimchar rump flame base',(0,.43,.78),(.28,.20,.31),'F4682A')
    for x, z in [(-.25,1.18),(0,1.42),(.27,1.20)]:
        leaf('Chimchar flame tongue',(0,.44,.69),(x,.55,z),.21,'F4682A',.08)
    leaf('Chimchar golden flame',(0,.28,.70),(.04,.34,1.22),.18,'FFD251',.05)
    _fuse('Chimchar smooth orange skin',['Chimchar torso','Chimchar leg','Chimchar arm'],orange)


def build_piplup():
    blue, navy, pale, gold = '65B7D6','285A91','EFF8ED','F3CF51'
    body, bs = (0,.06,.87),(.54,.39,.65)
    ell('Piplup round body',body,bs,blue)
    patch('Piplup light blue belly',body,bs,(0,.73),(.37,.45),'ACDCE4')
    for s in (-1,1):
        ell('Piplup webbed foot',(s*.29,-.16,.14),(.27,.35,.14),gold)
        for k in (-1,1):
            tube('Piplup toe crease',[(s*.29+k*.07,-.43,.17),(s*.29+k*.10,-.48,.12)],[.008,.005],'BE982F')
        ell('Piplup flipper',(s*.53,.01,.95),(.18,.17,.43),blue,(0,s*-24,0))
        ell('Piplup collar point',(s*.26,-.27,1.25),(.31,.11,.22),navy,(0,s*20,0))
        ell('Piplup breast spot',(s*.19,-.342,.96),(.090,.045,.125),pale)
    head,hs=(0,-.07,1.82),(.64,.53,.59)
    ell('Piplup navy head',head,hs,navy)
    patch('Piplup forehead blue blaze',head,hs,(0,1.92),(.18,.27),blue)
    for s in (-1,1):
        patch('Piplup white face',head,hs,(s*.26,1.78),(.29,.39),pale)
        eye('Piplup eye',head,hs,s*.27,1.91,(.095,.17),'19364B',False)
    # A narrow blue stripe separates the two pale face panels.
    ell('Piplup beak upper',(0,-.624,1.65),(.17,.23,.11),gold)
    ell('Piplup beak lower',(0,-.64,1.58),(.145,.18,.065),'EABC3B')
    tube('Piplup beak seam',[(-.13,-.76,1.625),(0,-.849,1.62),(.13,-.76,1.625)],[.009]*3,'AD842A')
    for s in (-1,1):
        leaf('Piplup tail feather',(0,.34,.75),(s*.23,.79,.91),.16,blue,.06)
    _fuse('Piplup continuous body',['Piplup round body','Piplup flipper'],blue)


def build_snivy():
    green, pale, gold = '64A94A','F0E7AD','EACB58'
    body, bs=(0,.06,.86),(.32,.31,.67)
    ell('Snivy slender body',body,bs,green)
    patch('Snivy pale belly',body,bs,(0,.82),(.24,.48),pale)
    tube('Snivy curved neck',[(0,.04,1.12),(0,-.015,1.45),(0,-.16,1.73)],[.25,.24,.27],green)
    head,hs=(0,-.23,1.88),(.43,.47,.39)
    ell('Snivy head',head,hs,green)
    tube('Snivy pointed muzzle',[(0,-.45,1.84),(0,-.79,1.86),(0,-1.13,1.99)],[(.31,.19),(.22,.115),(.012,.008)],green,sides=24)
    tube('Snivy pale chin',[(0,-.51,1.75),(0,-.80,1.79),(0,-1.12,1.975)],[(.29,.085),(.20,.07),(.01,.006)],pale,sides=24)
    patch('Snivy pale neck',(0,.04,1.30),(.25,.28,.43),(0,1.33),(.17,.32),pale)
    for s in (-1,1):
        patch('Snivy yellow eye surround',head,hs,(s*.25,1.97),(.135,.183),gold)
        eye('Snivy amber eye',head,hs,s*.25,1.96,(.105,.135),'9C5F49')
        # A sloping lid reduces the generic wide-eyed expression.
        eyelid=[]
        for x,z in ((.14,2.055),(.25,2.04),(.35,2.01)):
            eyelid.append((s*x,front(head,hs,s*x,z)-.067,z))
        tube('Snivy confident upper eyelid',eyelid,[.025,.028,.018],green)
        # Long golden collar points are part of Snivy's characteristic outline.
        leaf('Snivy golden collar',(s*.14,-.02,1.42),(s*.48,-.06,1.74),.16,gold,.05)
        tube('Snivy tiny arm',[(s*.25,0,1.15),(s*.43,-.07,1.13),(s*.50,-.15,1.27)],[.065,.05,.015],green)
        tube('Snivy short leg',[(s*.17,.01,.36),(s*.20,-.04,.18),(s*.27,-.26,.12)],[.075,.055,.012],pale)
    smile('Snivy knowing smile',(0,-.918,1.81),.19,'4E6238')
    tube('Snivy curled tail',[(0,.19,.48),(.16,.56,.49),(.34,.84,.69),(.34,1.02,.93)],[.16,.14,.11,.065],green)
    leaf('Snivy tail middle leaf',(.31,.90,.82),(.32,1.30,1.72),.29,'407B39',.12)
    leaf('Snivy tail left leaf',(.30,.94,.91),(-.20,1.20,1.45),.24,'407B39',.08)
    leaf('Snivy tail right leaf',(.36,.95,.90),(.87,1.19,1.47),.24,'407B39',.08)
    tube('Snivy tail leaf vein',[(.32,1.018,.95),(.32,1.10,1.22),(.32,1.26,1.61)],[.018,.014,.006],gold)
    _fuse('Snivy smooth green skin',['Snivy slender body','Snivy curved neck','Snivy head','Snivy pointed muzzle','Snivy tiny arm','Snivy curled tail'],green)


def build_tepig():
    orange, dark, red = 'E8954B','514137','DD6554'
    ell('Tepig round body',(0,.26,.77),(.61,.77,.58),orange)
    ell('Tepig dark rump',(0,.69,.76),(.57,.40,.52),dark)
    for s in (-1,1):
        for y in (-.10,.70):
            ell('Tepig short leg',(s*.39,y,.32),(.19,.22,.29),orange)
            ell('Tepig cloven hoof',(s*.39,y-.035,.12),(.205,.24,.13),dark)
            tube('Tepig hoof notch',[(s*.39,y-.265,.09),(s*.39,y-.26,.17)],[.008,.006],'241E1E')
    head,hs=(0,-.46,1.30),(.60,.50,.53)
    ell('Tepig head',head,hs,orange)
    patch('Tepig dark forehead',head,hs,(0,1.51),(.47,.29),dark)
    patch('Tepig golden forehead blaze',head,hs,(0,1.43),(.18,.31),'F0D45E')
    for s in (-1,1):
        # The dark forehead stretches around the ears; orange cheeks stay exposed.
        ell('Tepig tall ear',(s*.38,-.31,1.99),(.18,.115,.43),dark,(0,s*-16,0))
        eye('Tepig eye',head,hs,s*.30,1.39,(.12,.17),'3E2F29')
    ell('Tepig red snout',(0,-.96,1.12),(.30,.17,.205),red)
    for s in (-1,1):
        ell('Tepig nostril',(s*.105,-1.118,1.13),(.046,.018,.063),dark)
    smile('Tepig happy mouth',(0,-.993,.97),.20,dark)
    points=[]
    for i in range(24):
        a=i*math.pi*2/19
        points.append((.11*math.sin(a),1.02+i*.018,.81+.14*(1-math.cos(a))))
    tube('Tepig corkscrew tail',points,[.035]*len(points),dark,sides=12,steps=2)
    p=points[-1]
    ell('Tepig red tail bead',(p[0],p[1],p[2]),(.115,.115,.115),red)
    _fuse('Tepig orange skin',['Tepig round body','Tepig short leg'],orange)


def build_oshawott():
    white, teal, navy, cream = 'F4F4E7','81C8C6','376D89','F1D99D'
    body,bs=(0,.04,.82),(.44,.33,.59)
    ell('Oshawott body',body,bs,teal)
    for s in (-1,1):
        ell('Oshawott scalloped collar',(s*.205,-.22,1.27),(.21,.12,.16),teal)
        ell('Oshawott collar lobe',(s*.34,-.15,1.32),(.13,.12,.13),teal)
    for s in (-1,1):
        ell('Oshawott paddle foot',(s*.25,-.13,.13),(.24,.33,.13),navy)
        ell('Oshawott white arm',(s*.43,-.03,1.03),(.16,.17,.31),white,(0,s*-24,0))
    head,hs=(0,-.05,1.76),(.65,.50,.57)
    ell('Oshawott white head',head,hs,white)
    for s in (-1,1):
        leaf('Oshawott dark ear',(s*.43,.02,1.91),(s*.65,-.01,2.24),.22,navy,.04)
        eye('Oshawott eye',head,hs,s*.265,1.88,(.095,.16),'2B3137',False)
        for x,z in ((.36,1.65),(.46,1.63),(.40,1.56)):
            patch('Oshawott whisker freckle',head,hs,(s*x,z),(.018,.018),'535C60')
    ell('Oshawott orange nose',(0,-.557,1.74),(.105,.065,.075),'B67B45')
    tube('Oshawott thoughtful mouth',[(-.15,-.531,1.50),(0,-.555,1.58),(.15,-.531,1.50)],[.009,.010,.009],'525057')
    # Sculpted scallop shell, with five raised ribs and a small rounded hinge.
    shell_center,shell_scale=(0,-.335,.80),(.30,.070,.245)
    ell('Oshawott scalchop shell',shell_center,shell_scale,cream)
    for i in (-1,0,1):
        points=[]
        for j in range(7):
            t=j/6
            x=i*(.04+.115*t)
            z=.59+.39*t
            points.append((x,front(shell_center,shell_scale,x,z)-.004,z))
        tube('Oshawott shell shallow rib',points,[.009]*7,'CFB783',sides=10,steps=2)
    ell('Oshawott shell hinge',(0,-.385,.555),(.115,.055,.055),cream)
    ell('Oshawott paddle tail',(0,.52,.45),(.31,.38,.10),navy,(-18,0,0))
    _fuse('Oshawott teal torso',['Oshawott body','Oshawott scalloped collar','Oshawott collar lobe'],teal)


def build_chespin():
    green, brown, cream, dark = '79A846','A36F45','EFD1A0','443326'
    body,bs=(0,.045,.80),(.43,.34,.58)
    ell('Chespin brown body',body,bs,brown)
    patch('Chespin cream belly',body,bs,(0,.82),(.30,.39),cream)
    for s in (-1,1):
        ell('Chespin leg',(s*.25,.015,.32),(.18,.19,.28),brown)
        ell('Chespin shoe-like foot',(s*.27,-.15,.14),(.19,.26,.14),'6F5037')
        tube('Chespin long white toe',[(s*.27,-.27,.15),(s*.32,-.47,.13),(s*.35,-.62,.10)],[.15,.11,.005],'F3F1E7')
        tube('Chespin arm',[(s*.31,.00,1.13),(s*.61,-.035,1.03),(s*.85,-.06,.96)],[.14,.14,.07],brown)
        for k in (-1,1):
            cone('Chespin hand claw',(s*.83,-.10,1.00+k*.04),(s*.96,-.11,1.00+k*.045),.028,cream)
    head,hs=(0,-.025,1.77),(.65,.51,.62)
    ell('Chespin green hood',head,hs,green)
    patch('Chespin broad face',head,hs,(0,1.74),(.54,.48),cream)
    # The forehead notch is a low, central green point between the eyes.
    _surface_polygon('Chespin forehead brown point',head,hs,[(-.25,2.20),(.25,2.20),(0,1.99)],brown)
    leaf('Chespin central crown spike',(0,.02,2.28),(0,.02,2.91),.095,green,.02)
    for s in (-1,1):
        leaf('Chespin upper hood spike',(s*.24,-.01,2.22),(s*.50,-.015,2.79),.10,green,.02)
        leaf('Chespin side hood spike',(s*.52,.015,2.02),(s*.89,.03,2.51),.10,green,.02)
        leaf('Chespin cheek hood point',(s*.53,-.03,1.48),(s*.84,-.03,1.44),.08,green,.02)
        _surface_polygon('Chespin brown cheek panel',head,hs,[(s*.36,1.78),(s*.56,1.86),(s*.57,1.59),(s*.37,1.39)],brown)
        eye('Chespin eye',head,hs,s*.235,1.88,(.10,.15),'3C302C',False)
    ell('Chespin nose',(0,-.56,1.70),(.083,.045,.060),'D6845B')
    ell('Chespin open smile',(0,-.522,1.49),(.23,.065,.145),dark)
    ell('Chespin tongue',(0,-.575,1.43),(.12,.023,.055),'C8787E')
    ell('Chespin front tooth',(0,-.584,1.575),(.069,.025,.042),'FFF8E4')
    tube('Chespin tail',[(0,.27,.47),(0,.60,.57),(0,.82,.70)],[.14,.12,.065],green)
    cone('Chespin orange tail tip',(0,.78,.68),(0,1.05,.88),.09,'DB8052')
    _fuse('Chespin smooth body',['Chespin brown body','Chespin arm','Chespin leg'],brown)


def build_fennekin():
    yellow, cream, orange, dark = 'F2DB7D','FFF6E4','DE7953','3C3A38'
    ell('Fennekin body',(0,.22,.75),(.43,.64,.43),yellow)
    for s in (-1,1):
        for y in (-.20,.66):
            tube('Fennekin slim leg',[(s*.29,y,.65),(s*.30,y-.035,.35),(s*.30,y-.08,.14)],[.13,.105,.095],yellow)
            ell('Fennekin paw',(s*.30,y-.14,.12),(.16,.22,.12),yellow)
    head,hs=(0,-.43,1.43),(.62,.47,.52)
    ell('Fennekin large head',head,hs,yellow)
    for s in (-1,1):
        # Huge fennec ears are solid tapered forms with separate orange interiors.
        leaf('Fennekin outer ear',(s*.35,-.29,1.73),(s*.86,-.18,2.72),.32,yellow,.015)
        leaf('Fennekin inner ear',(s*.40,-.405,1.86),(s*.83,-.295,2.60),.245,orange,.015)
        leaf('Fennekin ear outer flame tuft',(s*.49,-.40,1.94),(s*.99,-.30,2.52),.19,orange,.01)
        leaf('Fennekin ear inner flame tuft',(s*.44,-.40,1.90),(s*.62,-.33,2.49),.15,orange,.01)
        patch('Fennekin white cheek',head,hs,(s*.31,1.24),(.28,.20),cream)
        eye('Fennekin eye',head,hs,s*.29,1.53,(.115,.18),'D16F50')
        leaf('Fennekin cheek fur',(s*.34,-.61,1.19),(s*.79,-.42,1.25),.16,cream,.03)
        leaf('Fennekin upper cheek fur',(s*.34,-.57,1.31),(s*.76,-.38,1.44),.12,cream,.03)
    ell('Fennekin pointed muzzle',(0,-.84,1.24),(.29,.24,.15),cream)
    ell('Fennekin small nose',(0,-1.063,1.31),(.075,.052,.053),dark)
    smile('Fennekin mouth',(0,-1.046,1.18),.15,dark)
    ell('Fennekin white chest',(0,-.32,.88),(.26,.14,.28),cream)
    for x in (-.09,.09):
        tube('Fennekin brow fur line',[(x,-.796,1.59),(x*.75,-.856,1.43)],[.007,.004],'D0B35C')
    # Large raised brush tail with a distinct burnt-orange end.
    tube('Fennekin brush tail',[(0,.67,.77),(.15,1.00,1.00),(.22,1.30,1.31),(.15,1.43,1.49)],[.22,.33,.26,.12],yellow,sides=24)
    tube('Fennekin orange tail tip',[(.22,1.29,1.30),(.15,1.44,1.52),(.04,1.46,1.73)],[.25,.16,.012],orange,sides=24)
    _fuse('Fennekin smooth golden skin',['Fennekin body','Fennekin slim leg','Fennekin paw'],yellow)


def build_froakie():
    blue, pale, navy, yellow = '76C5DF','F5F8EC','376C92','F2DC6C'
    body,bs=(0,.06,.83),(.36,.30,.43)
    ell('Froakie torso',body,bs,blue)
    patch('Froakie pale chest',body,bs,(0,.80),(.23,.30),'DCEFE9')
    for s in (-1,1):
        # Wide bent knees and fine fingers keep the silhouette frog-like.
        ell('Froakie crouched thigh',(s*.42,.15,.46),(.30,.31,.28),blue)
        tube('Froakie folded shin',[(s*.57,.15,.46),(s*.63,-.06,.25),(s*.38,-.23,.12)],[.15,.11,.07],blue)
        ell('Froakie flat foot',(s*.39,-.32,.10),(.23,.26,.09),blue)
        for k in (-1,0,1):
            tube('Froakie long toe',[(s*.39+k*.09,-.39,.10),(s*.39+k*.13,-.63,.095)],[.040,.028],blue,sides=12)
            ell('Froakie toe pad',(s*.39+k*.13,-.63,.095),(.046,.052,.035),pale)
        tube('Froakie arm',[(s*.28,-.02,1.05),(s*.56,-.10,.80),(s*.72,-.27,.47)],[.09,.075,.055],blue)
        ell('Froakie white hand',(s*.73,-.29,.42),(.12,.10,.10),pale)
        for k in (-1,0,1):
            tube('Froakie finger',[(s*.73+k*.055,-.31,.40),(s*.73+k*.085,-.41,.28)],[.030,.023],pale,sides=12)
    head,hs=(0,-.08,1.48),(.64,.43,.37)
    ell('Froakie wide head',head,hs,blue)
    for s in (-1,1):
        eye_head=(s*.34,-.035,1.86)
        eye_scale=(.24,.29,.37)
        ell('Froakie raised eye socket',eye_head,eye_scale,blue)
        # Froakie's light yellow eye field surrounds a tall dark pupil.
        patch('Froakie yellow eye field',eye_head,eye_scale,(s*.34,1.88),(.177,.29),yellow)
        eye('Froakie vertical pupil',eye_head,eye_scale,s*.34,1.91,(.070,.20),'26383F',False)
        ell('Froakie nostril',(s*.11,-.503,1.52),(.015,.011,.018),navy)
    smile('Froakie quiet smile',(0,-.492,1.34),.28,navy)
    # A ring of clustered closed bubbles forms the signature foam scarf.
    for i in range(11):
        a=2*math.pi*i/11
        x=.36*math.sin(a)
        y=.04+.29*math.cos(a)
        z=1.13+.035*math.sin(3*a)
        ell('Froakie foam scarf',(x,y,z),(.18,.17,.16),pale)
    for x in (-.115,.115):
        ell('Froakie nose foam',(x,-.505,1.65),(.12,.09,.12),pale)
    ell('Froakie lower foam bib',(0,-.255,1.00),(.20,.16,.23),pale)
    _fuse('Froakie continuous blue skin',['Froakie torso','Froakie crouched thigh','Froakie folded shin','Froakie flat foot','Froakie long toe','Froakie arm'],blue)


BUILDERS = {
    'Turtwig': build_turtwig, 'Chimchar': build_chimchar, 'Piplup': build_piplup,
    'Snivy': build_snivy, 'Tepig': build_tepig, 'Oshawott': build_oshawott,
    'Chespin': build_chespin, 'Fennekin': build_fennekin, 'Froakie': build_froakie,
}

