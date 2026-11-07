"""Reference-led, editable Umbreon model. Official illustration: dex #197.

Build + quick review: blender --background --python this.py -- --draft
Build + full review: blender --background --python this.py -- --all
"""
import sys
import math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import eeveelutions_helpers as h

OUT=h.setup('Umbreon')
BLACK='303A3D';GOLD='EFD43B';RED='DB263E';INK='101821'

# The long neck, sloping chest, slim waist and hocks form one sculpted skin.
parts=[h.ell('Torso', (0,.20,.99),(.34,.72,.34),BLACK),
       h.ell('Chest', (0,-.35,1.03),(.29,.32,.40),BLACK),
       h.ell('Raised neck', (0,-.43,1.40),(.235,.27,.45),BLACK,(-12,0,0)),
       h.ell('Cranium',(0,-.57,1.85),(.38,.34,.36),BLACK),
       h.ell('Cheeks',(0,-.64,1.70),(.34,.29,.245),BLACK),
       h.ell('Tapered muzzle',(0,-.80,1.68),(.225,.19,.15),BLACK),
       h.ell('Jaw',(0,-.69,1.58),(.245,.24,.14),BLACK)]
for s in (-1,1):
    parts.append(h.tube('Foreleg',[(s*.09,-.32,1.19),(s*.225,-.38,.87),(s*.255,-.44,.47),(s*.265,-.46,.16)],
                        [(.13,.145),(.13,.14),(.089,.095),(.083,.09)],BLACK))
    parts.append(h.ell('Front paw',(s*.265,-.53,.095),(.116,.19,.095),BLACK))
    parts.append(h.ell('Rear haunch',(s*.21,.70,.89),(.18,.28,.31),BLACK,(0,s*6,0)))
    parts.append(h.tube('Hind leg',[(s*.25,.75,.93),(s*.29,.58,.59),(s*.27,.82,.33),(s*.27,.80,.13)],
                        [(.17,.18),(.13,.13),(.075,.085),(.075,.08)],BLACK))
    parts.append(h.ell('Rear paw',(s*.27,.71,.08),(.106,.17,.08),BLACK))
skin=h.union('Umbreon | continuous skin',parts,BLACK,.017)

# Ears are flattened cones; yellow bands wrap the complete surface, without decals.
for s in (-1,1):
    ear_points=([(-.27,-.57,2.055),(-.49,-.55,2.14),(-.73,-.52,2.20),(-1.04,-.48,2.24)] if s<0 else
                [(.27,-.57,2.055),(.37,-.55,2.30),(.48,-.52,2.54),(.64,-.48,2.81)])
    h.tube('Umbreon | '+('left' if s<0 else 'right')+' ear',
           ear_points,
           [(.105,.095),(.16,.087),(.125,.067),(.0025,.0025)],BLACK,
           sides=56,steps=20,width_axis=(1,0,0),bands=[(.55,.70,GOLD)])

# Large swept fox tail: broad in its middle, clean pointed tip and complete ring.
h.tube('Umbreon | swept tail',[(0,.76,1.06),(0,1.12,1.27),(-.05,1.42,1.59),(-.13,1.69,1.89),(-.23,1.89,2.18)],
       [(.12,.12),(.19,.19),(.19,.18),(.12,.12),(.003,.003)],BLACK,
       sides=64,steps=20,width_axis=(1,0,0),bands=[(.55,.72,GOLD)])

# The forehead ring is elliptical, sitting above the brow rather than between eyes.
h.paint('Umbreon | forehead gold ring',skin,h.circle(0,2.003,.122,.149),GOLD,
        hole=h.circle(0,2.003,.076,.100),depth=.007)
for s in (-1,1):
    # Side leg rings follow sculpted actual skin rather than floating disks.
    h.paint('Umbreon | front leg ring '+str(s),skin,h.circle(-.397,.727,.080,.174,-4),GOLD,
            plane='side',side=s,hole=h.circle(-.397,.727,.045,.119,-4),depth=.006)
    h.paint('Umbreon | hind leg ring '+str(s),skin,h.circle(.675,.81,.116,.183,-12),GOLD,
            plane='side',side=s,hole=h.circle(.675,.81,.068,.127,-12),depth=.006)
    x=s*.178;z=1.812
    h.paint('Umbreon | eye socket '+str(s),skin,h.circle(x,z,.121,.079,s*20),INK,depth=.004)
    h.paint('Umbreon | red iris '+str(s),skin,h.circle(x,z,.108,.068,s*20),RED,depth=.007)
    h.paint('Umbreon | black pupil '+str(s),skin,h.circle(x-s*.009,z+.002,.021,.060,s*8),INK,depth=.010)
    h.paint('Umbreon | eye catchlight '+str(s),skin,h.circle(x-s*.025,z+.030,.020,.017), 'FFFDF1',depth=.013)
    # Delicate toe creases; no visible claws in the reference.
    for dx in (-.032,.032):
        h.line('Umbreon | toe fold',[(s*.265+dx,-.691,.086),(s*.265+dx,-.686,.117),(s*.265+dx,-.66,.14)],BLACK,.003)

h.ell('Umbreon | small nose',(0,-.980,1.71),(.036,.020,.020),INK)
h.line('Umbreon | mouth', [(-.080,-.950,1.610),(-.04,-.968,1.601),(0,-.974,1.603),(.04,-.968,1.601),(.080,-.950,1.610)],INK,.005)

h.stage()
h.save_export()
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
if '--draft' in args:h.render(('hero','front','side'),True)
if '--all' in args:h.render(('hero','front','side','back','clay'))
h.validate()
