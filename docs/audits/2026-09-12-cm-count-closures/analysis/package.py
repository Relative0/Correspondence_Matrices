"""Freeze declared source overlays and commands for this bounded phase."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2];CHECKOUT=ROOT/'build/cm-closures'
profile=sys.argv[1]
definition=json.loads((AUDIT/(profile+'-PROTOCOL.json')).read_text())
sources=definition['sources'];commands=definition['commands']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
manifest=dict(base_commit='643b5b6c9614ee1d1daed4eb374a431a67514587',files={name:sha(CHECKOUT/name) for name in sources})
bundle=AUDIT/'packages'/(profile+'.zip')
with zipfile.ZipFile(bundle,'x',zipfile.ZIP_DEFLATED) as archive:
    for name in sources:archive.write(CHECKOUT/name,name)
    for name,value in [('SOURCE_MANIFEST.json',manifest),('COMMANDS.json',commands),('PUBLIC_FIXTURES.json',[])]:archive.writestr(name,json.dumps(value,indent=2))
    prior=ROOT/'docs/audits/2026-09-11-cm-next-research'
    archive.write(prior/'REGRESSION-DEPENDENCIES.json','DEPENDENCIES.json');archive.write(prior/'TOOLS.json','TOOLS.json')
freeze=dict(profile=profile,protocol_sha256=sha(AUDIT/(profile+'-PROTOCOL.json')),source=manifest,bundle_sha256=sha(bundle),bundle_bytes=bundle.stat().st_size,
    controller_sha256=sha(ROOT/definition.get('controller','scripts/runpod_closure_research_controller.py')),
    remote_sha256=sha(ROOT/definition.get('remote','scripts/cm_closure_research_remote.py')),
    transport_sha256=sha(ROOT/'scripts/runpod_query_ladder_q64_second_host_v3_controller.py'),bootstrap_sha256=sha(ROOT/'scripts/runpod_frontier_bootstrap.py'))
with (AUDIT/'packages'/(profile+'-FREEZE.json')).open('x') as stream:json.dump(freeze,stream,indent=2);stream.write('\n')
print(json.dumps(dict(profile=profile,files=len(sources),bundle_bytes=bundle.stat().st_size)))
