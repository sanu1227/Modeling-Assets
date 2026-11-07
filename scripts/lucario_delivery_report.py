"""Record artifact freshness after the three models' final visual review."""
import hashlib
import json
import struct
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for name in ('Lucario','Gardevoir','Tyranitar'):
    folder=ROOT/'assets'/'PokemonPopular'/name
    validation=json.loads((folder/'validation.json').read_text(encoding='utf-8'))
    files={ext:folder/(name+'.'+ext) for ext in ('blend','glb')}
    latest_source=max(path.stat().st_mtime for path in files.values())
    errors=[]
    if not validation['passed']:errors.append('Geometry validation failed')
    if (folder/'validation.json').stat().st_mtime<latest_source:errors.append('Stale validation')
    render_records={}
    for view in ('preview','front','back','side','face','clay','glb_check'):
        path=folder/'renders'/(name+'_'+view+'.png')
        if not path.is_file():
            errors.append('Missing render '+view)
            continue
        header=path.read_bytes()[:24]
        if header[:8]!=b'\x89PNG\r\n\x1a\n':errors.append('Invalid PNG '+view)
        width,height=struct.unpack('>II',header[16:24])
        fresh=path.stat().st_mtime>=latest_source
        if not fresh:errors.append('Stale render '+view)
        render_records[view]={'file':str(path.relative_to(folder)),
            'width':width,'height':height,'current_source':fresh}
    report={'passed':not errors,'checked_at':datetime.now(timezone.utc).isoformat(),
        'assets':{ext:{'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for ext,path in files.items()},
        'geometry_validation':'validation.json','source_triangles':validation['source']['triangles'],
        'source_meshes':validation['source']['meshes'],'renders':render_records,
        'visual_review':'All six final views and the actual reimported GLB preview were viewed directly.',
        'limitations':validation['limitations'],'errors':errors}
    (folder/'delivery_check.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(name,report['passed'],report['source_triangles'],errors)
    if errors:raise SystemExit(1)
