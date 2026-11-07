"""Reopen delivered .blend files and independently reimport their GLB exports."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import eeveelutions_helpers as h

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Umbreon','Sylveon']
for name in args:
    if name not in ('Umbreon','Sylveon','Dragonite','Luxray','Eevee'):raise ValueError(name)
    h.NAME=name
    h.OUT=h.ROOT/'assets'/'PokemonPopular'/name
    if not h.validate()['passed']:raise RuntimeError(name+' validation failed')
