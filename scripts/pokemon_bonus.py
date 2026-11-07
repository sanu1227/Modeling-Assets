"""Special partners and the three officially revealed Winds / Waves starters."""
from pokemon_common import *


def _face_shape(name, center, scale, outline, color, depth):
    """Closed, thin painted shape following the curved head surface."""
    n, rings = len(outline), 8
    x = sum(p[0] for p in outline)/n
    z = sum(p[1] for p in outline)/n
    verts = [(x, front(center, scale, x, z)-depth, z)]
    for ring in range(1, rings+1):
        r = ring/rings
        for px, pz in outline:
            xx, zz = x+(px-x)*r, z+(pz-z)*r
            verts.append((xx, front(center, scale, xx, zz)-depth, zz))
    faces = [(0, 1+j, 1+(j+1)%n) for j in range(n)]
    for ring in range(rings-1):
        for j in range(n):
            a, b = 1+ring*n+j, 1+ring*n+(j+1)%n
            faces.append((a, b, b+n, a+n))
    obj = mesh(name, verts, faces, color)
    mod = obj.modifiers.new('Closed painted surface', 'SOLIDIFY')
    mod.thickness=.012; mod.offset=-1
    apply(obj, mod)
    return obj


def build_pikachu():
    yellow = 'F6CE3D'
    head, hs = (0, -.16, 1.48), (.59, .43, .52)
    parts = [ell('Pikachu_body', (0, .02, .72), (.46, .37, .64), yellow),
             ell('Pikachu_head', head, hs, yellow)]
    for s in (-1, 1):
        parts.append(ell('Pikachu_arm', (s*.38, -.22, .78), (.17, .18, .32), yellow, (0, -s*24, 0)))
        ell('Pikachu_foot', (s*.28, -.20, .16), (.23, .33, .15), yellow)
        tube('Pikachu_ear', [(s*.34, -.08, 1.83), (s*.48, -.04, 2.15), (s*.61, -.03, 2.45)],
             [(.16, .11), (.13, .085), (.075, .055)], yellow)
        tube('Pikachu_black_ear_tip', [(s*.59, -.03, 2.39), (s*.65, -.035, 2.57), (s*.67, -.04, 2.65)],
             [(.084, .060), (.053, .035), .005], '28313A')
    union('Pikachu_skin', parts, yellow)
    for s in (-1, 1):
        eye('Pikachu_eye', head, hs, s*.235, 1.56, (.087, .118), white=False)
        patch('Pikachu_cheek', head, hs, (s*.405, 1.30), (.12, .12), 'DF483F')
    ell('Pikachu_nose', (0, -.588, 1.40), (.048, .03, .033), '26323B')
    smile('Pikachu_smile_left', (-.075, -.594, 1.30), .15)
    smile('Pikachu_smile_right', (.075, -.594, 1.30), .15)
    # The lightning silhouette is a closed, lightly bevelled solid.
    shape = [(.31, .56), (.67, .77), (.54, 1.02), (.91, 1.09),
             (.70, 1.41), (1.24, 1.87), (1.52, 1.58), (1.08, 1.24),
             (1.28, .98), (.82, .85), (.94, .64), (.43, .40)]
    verts = [(x, y, z) for y in (.32, .48) for x, z in shape]
    n = len(shape)
    faces = [tuple(range(n-1, -1, -1)), tuple(range(n, n*2))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    tail = mesh('Pikachu_lightning_tail', verts, faces, yellow)
    mod = tail.modifiers.new('Soft vinyl edges', 'BEVEL'); mod.width=.025; mod.segments=3
    apply(tail, mod)
    tube('Pikachu_tail_root', [(.18, .32, .46), (.44, .40, .49), (.63, .40, .61)], [.11, .09, .075], '9C683D')
    for z in (.68, .91):
        ell('Pikachu_back_stripe', (0, .352, z), (.31, .025, .072), '9C683D')


def build_eevee():
    brown, cream = 'B9834D', 'F6E5B5'
    head, hs = (0, -.37, 1.38), (.54, .40, .48)
    parts = [ell('Eevee_body', (0, .24, .65), (.43, .58, .46), brown),
             ell('Eevee_head', head, hs, brown)]
    for x, tip_z in ((-.18, 1.92), (0, 1.97), (.18, 1.90)):
        parts.append(cone('Eevee_crown_fur', (x, -.35, 1.75), (x+.035, -.31, tip_z), .10, brown))
    for s in (-1, 1):
        for y in (-.16, .57):
            parts.append(ell('Eevee_leg', (s*.28, y, .32), (.16, .18, .28), brown))
            ell('Eevee_paw', (s*.28, y-.09, .13), (.19, .25, .13), brown)
        tube('Eevee_ear', [(s*.32, -.29, 1.65), (s*.49, -.26, 2.0), (s*.66, -.23, 2.31)],
             [(.21, .12), (.18, .095), .007], brown)
        tube('Eevee_inner_ear', [(s*.35, -.395, 1.76), (s*.49, -.35, 2.02), (s*.61, -.29, 2.22)],
             [(.105, .020), (.11, .019), .005], '46392F')
    union('Eevee_skin', parts, brown)
    fluff = [ell('Eevee_neck_ruff', (0, -.24, .93), (.56, .40, .30), cream)]
    for i in range(9):
        a = math.pi*2*i/9
        x, y = .47*math.cos(a), -.24+.27*math.sin(a)
        fluff.append(cone('Eevee_ruff_tuft', (x*.75, y, 1.00), (x*1.22, y-.035, .68), .18, cream))
    fluff.append(cone('Eevee_center_chest_tuft', (0, -.47, .96), (0, -.60, .58), .22, cream))
    union('Eevee_fluffy_collar', fluff, cream, .035)
    for s in (-1, 1):
        eye('Eevee_eye', head, hs, s*.22, 1.46, (.105, .16), iris='422B1B', white=False)
    ell('Eevee_nose', (0, -.772, 1.30), (.065, .04, .043), '342F2E')
    smile('Eevee_smile', (0, -.766, 1.22), .23)
    tail = tube('Eevee_bushy_tail', [(0, .61, .64), (.37, .93, .81), (.62, .88, 1.10),
                                   (.78, .68, 1.45), (.77, .57, 1.76)],
                [.19, .26, .32, .23, .008], brown, 32, 8)
    tail.data.materials.append(material(cream))
    for face in tail.data.polygons:
        if face.center.z > 1.28:
            face.material_index = 1


def build_browt():
    yellow, green, black = 'FFF08B', '8CBD38', '373B38'
    head, hs = (0, -.04, 1.27), (.66, .46, .66)
    ell('Browt_dark_lower_body', (0, .035, .62), (.53, .38, .34), black)
    parts = [ell('Browt_round_plumage', head, hs, yellow)]
    for s in (-1, 1):
        parts.append(ell('Browt_wing', (s*.64, -.025, 1.07), (.35, .17, .18), yellow, (0, -s*25, 0)))
        parts.append(ell('Browt_wing_tip', (s*.78, -.035, 1.00), (.16, .15, .10), yellow))
        tube('Browt_leg', [(s*.23, .025, .50), (s*.23, -.005, .22), (s*.25, -.10, .12)], [.075, .060, .055], black)
        for k in (-1, 0, 1):
            tube('Browt_toe', [(s*.25, -.08, .13), (s*.25+k*.12, -.24, .09), (s*.25+k*.18, -.35, .07)],
                 [.055, .043, .008], black, 12, 4)
    for x in (-.45, -.23, 0, .23, .45):
        parts.append(ell('Browt_scalloped_down', (x, -.17, .78), (.22, .25, .20), yellow))
    union('Browt_yellow_plumage', parts, yellow, .04)
    for s in (-1, 1):
        eye('Browt_eye', head, hs, s*.235, 1.35, (.15, .205), iris='343936')
        leaf('Browt_leaf_brow', (0, -.46, 1.61), (s*.57, -.30, 1.94), .20, green, .07)
        tube('Browt_leaf_vein', [(s*.035, -.511, 1.65), (s*.28, -.478, 1.78), (s*.45, -.365, 1.89)],
             [.012, .011, .003], '5C872D', 10, 4)
    ell('Browt_green_beak_surround', (0, -.493, 1.39), (.17, .10, .24), green)
    ell('Browt_beak', (0, -.600, 1.32), (.13, .105, .07), 'BE816A')
    tube('Browt_beak_line', [(-.11, -.646, 1.32), (0, -.706, 1.30), (.11, -.646, 1.32)], [.009]*3, black, 10, 4)
    leaf('Browt_top_plume', (.08, .045, 1.80), (.18, .065, 2.20), .09, yellow, .03)
    leaf('Browt_short_plume', (.09, .06, 1.82), (.33, .08, 2.05), .07, yellow, .02)
    ell('Browt_back_tail', (0, .45, .96), (.23, .30, .16), yellow, (24, 0, 0))


def build_pombon():
    orange, cream = 'F5B246', 'FFE798'
    body = [ell('Pombon_body', (0, .27, .69), (.47, .60, .44), orange)]
    for s in (-1, 1):
        for y in (-.10, .62):
            body.append(ell('Pombon_leg', (s*.30, y, .29), (.14, .16, .27), orange))
            ell('Pombon_paw', (s*.30, y-.08, .12), (.18, .23, .12), orange)
            for k in (-1, 0, 1):
                ell('Pombon_toe', (s*.30+k*.066, y-.265, .12), (.043, .035, .05), 'D99132')
    union('Pombon_body_skin', body, orange)
    head, hs = (0, -.29, 1.28), (.61, .42, .62)
    mane = [ell('Pombon_face', head, hs, orange)]
    for i in range(13):
        a = 2*math.pi*i/13
        x, z = math.cos(a), math.sin(a)
        mane.append(tube('Pombon_fur_point', [(x*.43, -.11, 1.21+z*.46), (x*.65, -.10, 1.21+z*.60),
                                           (x*.77, -.10, 1.25+z*.64)], [.20, .15, .008], orange))
    union('Pombon_fluffy_mane', mane, orange, .035)
    for s in (-1, 1):
        tube('Pombon_ear', [(s*.34, -.27, 1.67), (s*.41, -.21, 1.96), (s*.43, -.15, 2.12)],
             [(.20, .12), (.15, .08), .008], orange)
        tube('Pombon_inner_ear', [(s*.36, -.38, 1.77), (s*.42, -.29, 1.96), (s*.43, -.23, 2.02)],
             [(.075, .02), (.075, .018), .005], 'CA8A36')
        eye('Pombon_eye', head, hs, s*.205, 1.42, (.073, .117), white=False)
        ell('Pombon_eye_warm_glint', (s*.205, front(head, hs, s*.205, 1.42)-.055, 1.375), (.018, .014, .02), 'F78A60')
    ell('Pombon_open_mouth', (0, -.696, 1.15), (.19, .045, .21), '643046')
    for s in (-1, 1):
        ell('Pombon_muzzle', (s*.075, -.716, 1.30), (.13, .085, .10), cream)
        cone('Pombon_tiny_fang', (s*.12, -.745, 1.24), (s*.11, -.751, 1.17), .028, 'FFF8D7')
    ell('Pombon_nose', (0, -.805, 1.34), (.055, .035, .04), 'DB3E51')
    ell('Pombon_tongue', (.04, -.757, 1.03), (.105, .055, .14), 'F38C91', (0, -16, 0))
    leaf('Pombon_forehead_lock', (0, -.45, 1.70), (.17, -.31, 1.94), .10, cream, .04)
    tube('Pombon_curled_tail', [(0, .69, .83), (.20, 1.0, 1.11), (.30, .85, 1.42), (.18, .65, 1.42)],
         [.18, .24, .23, .13], 'DDA044', 22, 6)
    tube('Pombon_flame_crest', [(0, .08, 1.72), (.08, .13, 2.01), (.22, .11, 2.21), (.16, .08, 2.40)],
         [.22, .22, .115, .005], 'EF6262', 24, 6)
    leaf('Pombon_flame_curl', (.18, .10, 2.02), (.32, .09, 2.23), .10, 'EF6262', .015)
    ell('Pombon_warm_chest', (0, -.40, .77), (.24, .05, .14), 'FFCF66')


def build_gecqua():
    blue, pale = '177DB8', 'A5DDE6'
    head, hs = (0, -.16, 1.58), (.71, .43, .51)
    core = [ell('Gecqua_body', (0, .13, .75), (.29, .29, .44), blue),
            tube('Gecqua_neck', [(0, .09, .96), (0, -.02, 1.24), (0, -.11, 1.44)], [.18, .14, .22], blue),
            ell('Gecqua_large_head', head, hs, blue)]
    union('Gecqua_skin', core, blue, .035)
    ell('Gecqua_belly', (0, -.137, .76), (.22, .047, .30), pale, (-12, 0, 0))
    for s in (-1, 1):
        tube('Gecqua_haunch', [(s*.18, .22, .72), (s*.36, .20, .43), (s*.27, -.04, .22)],
             [.17, .14, .075], blue, 18, 5)
        tube('Gecqua_foot', [(s*.27, -.04, .24), (s*.32, -.22, .12), (s*.34, -.36, .10)], [.085, .08, .065], blue)
        for k in (-1, 0, 1):
            start = (s*.33+k*.045, -.29, .12)
            end = (s*.34+k*.115, -.49, .075)
            tube('Gecqua_toe', [start, end], [.035, .022], pale, 12, 4)
            ell('Gecqua_toe_pad', end, (.038, .048, .022), pale)
        arm = [(s*.20, -.03, 1.02), (s*.42, -.15, .77), (s*.63, -.28, .85)]
        tube('Gecqua_bent_arm', arm, [.085, .073, .05], blue, 16, 5)
        for k in (-1, 0, 1):
            end = (s*(.83+.025*(k==0)), -.32-k*.07, .85+k*.08)
            tube('Gecqua_finger', [arm[-1], (s*.75, -.32-k*.04, .85+k*.075), end], [.030, .027, .018], pale, 12, 4)
            ell('Gecqua_finger_pad', end, (.027, .032, .027), pale)
        # Painted eyes remain flush to the head, including the half-closed lids.
        x, z = s*.33, 1.57
        for label, xx, zz, rx, rz, color, depth in [
            ('eye_dark', x, z, .237, .279, '263339', .020),
            ('magenta_iris', x, z-.105, .192, .135, 'C38CB4', .026),
            ('white_pupil', x-s*.025, z+.002, .050, .190, 'FFFDFC', .032),
            ('eye_glint', x-s*.10, z+.04, .048, .060, 'FFFFFF', .038)]:
            outline = [(xx+rx*math.cos(a*math.tau/48), zz+rz*math.sin(a*math.tau/48)) for a in range(48)]
            _face_shape('Gecqua_'+label, head, hs, outline, color, depth)
        outline = []
        for i in range(25):
            a = math.pi*(1-i/24)
            xx = x+.265*math.cos(a)
            zz = 1.69+.265*math.sin(a)-s*.10*(xx-x)
            outline.append((xx, zz))
        _face_shape('Gecqua_half_closed_lid', head, hs, outline, pale, .045)
        tube('Gecqua_lid_sweep', [(s*.51, front(head, hs, s*.51, 1.70)-.045, 1.70),
                                (s*.69, -.36, 1.68), (s*.83, -.26, 1.77)],
             [(.025, .060), (.020, .045), .005], pale, 18, 5)
    _face_shape('Gecqua_forehead_drop', head, hs,
                [(-.065, 1.72), (-.07, 1.81), (-.06, 1.98), (.045, 1.86),
                 (.10, 1.77), (.09, 1.70), (.025, 1.66)], '83CFF1', .025)
    ell('Gecqua_muzzle', (0, -.535, 1.37), (.20, .16, .14), blue)
    for s in (-1, 1):
        ell('Gecqua_nostril', (s*.065, -.687, 1.395), (.016, .012, .013), '234351')
    smile('Gecqua_smirk', (0, -.625, 1.305), .28, '234351')
    tube('Gecqua_tail', [(0, .32, .64), (-.22, .62, .64), (-.58, .70, .85), (-.80, .65, 1.06), (-.94, .57, 1.36)],
         [.14, .23, .29, .24, .012], blue, 24, 6)
    ell('Gecqua_tail_water_mark', (-.60, .478, 1.04), (.25, .030, .12), '83CFF1', (0, -28, 0))

