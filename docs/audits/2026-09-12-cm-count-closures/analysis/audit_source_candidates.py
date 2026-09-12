"""Bounded search for the exact backend blocking three historical packages."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2];CHECKOUT=ROOT/'build/cm-closures'
GIT=['git','-c','safe.directory='+CHECKOUT.as_posix(),'-C',str(CHECKOUT)]
manifests=['docs/recognition/'+name+'/UPLOAD_MANIFEST.json' for name in (
    'architecture_comparison_execution_retry_20260903',
    'architecture_query_ladder_followup_retry_002_execution_20260904',
    'architecture_query_ladder_cross_machine_execution_20260904')]
def sha(data):return hashlib.sha256(data).hexdigest()
expected=[]
for name in manifests:
    raw=(CHECKOUT/name).read_bytes();row=next(r for r in json.loads(raw)['files'] if r['source']=='bitset_backend.py')
    expected.append(dict(manifest=name,manifest_sha256=sha(raw),source=row))
targets={r['source']['sha256'] for r in expected};candidates=[]
def record(location,data):
    for transform,payload in [('raw',data),('lf',data.replace(b'\r\n',b'\n')),('crlf',data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))]:
        candidates.append(dict(location=location,transform=transform,bytes=len(payload),sha256=sha(payload),matches_expected=sha(payload) in targets))
paths=subprocess.check_output(['rg','--files','-g','bitset_backend.py','-g','!build/**','-g','!external/**','-g','!.venv/**'],cwd=ROOT).decode().splitlines()
assert len(paths)<256
for name in paths:
    path=ROOT/name;assert path.stat().st_size<1<<20
    record(name.replace('\\','/'),path.read_bytes())
revisions=subprocess.check_output([*GIT,'log','--all','--format=%H','--','bitset_backend.py']).decode().split()
assert len(revisions)<32
for rev in revisions:record('git:'+rev+':bitset_backend.py',subprocess.check_output([*GIT,'show',rev+':bitset_backend.py']))
archive=CHECKOUT/'docs/research/downloads/CM-Research-2026-08-28.zip'
assert sha(archive.read_bytes())=='7e542350d13c25a81266fad8d581eb007b24367fc7f3c4b985195e02ed07369e'
with zipfile.ZipFile(archive) as packed:
    members=[n for n in packed.namelist() if n.endswith('/bitset_backend.py')]
    assert len(members)<128
    for name in members:
        assert packed.getinfo(name).file_size<1<<20
        record('immutable-research-archive:'+name,packed.read(name))
result=dict(expected=expected,repository_copies=len(paths),git_versions=len(revisions),archive_copies=len(members),
    matches=sum(r['matches_expected'] for r in candidates),candidates=candidates,
    scope='Same-named surviving repository files, locally available Git history and the pinned research archive only; not a claim that every backup or historical source package was searched',
    current_sources_replaced=False,historical_expectations_changed=False)
(AUDIT/'HISTORICAL-SOURCE-SEARCH.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('candidates','expected')}))
