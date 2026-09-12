"""Restore only surviving bytes that match independent historical hashes."""
import hashlib
import json
from pathlib import Path

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2];CHECKOUT=ROOT/'build/cm-closures'
DEST=CHECKOUT/'docs/audits/2026-09-12-cm-count-closures'
def sha(data):return hashlib.sha256(data).hexdigest()
manifest='docs/recognition/runs/post-benchmark-neural-eligibility-development-20260903-001/manifest.json'
source=json.loads((CHECKOUT/manifest).read_text())
base='docs/recognition/architecture_comparison_execution_retry_20260903/'
cases=[(base+'ANALYSIS.json',source['evidence']['analysis'],manifest,'evidence.analysis'),
       (base+'runpod-architecture-comparison-retry-002/RUN.json',source['evidence']['controller_state'],manifest,'evidence.controller_state')]
pilot='deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/runs/hardware-epfl-context-pilot-2026-08-27-run2/'
checks=dict((line.split(maxsplit=1)[1].strip().lstrip('*'),line.split()[0]) for line in (CHECKOUT/(pilot+'CHECKSUMS.sha256')).read_text().splitlines())
cases.append((pilot+'raw.csv',checks['raw.csv'],pilot+'CHECKSUMS.sha256','raw.csv'))
prepared=[]
for name,expected,binding,field in cases:
    before=(CHECKOUT/name).read_bytes();original=(ROOT/name).read_bytes()
    assert sha(original)==expected and sha(before)!=expected
    assert before.replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n')
    prepared.append((name,before,original,dict(path=name,before_sha256=sha(before),restored_sha256=expected,
                     bytes=len(original),binding=binding,binding_sha256=sha((CHECKOUT/binding).read_bytes()),field=field,
                     recovery='surviving original CRLF bytes',content_changed=False)))
records=[]
for name,before,original,row in prepared:
    for label,data in [('before',before),('restored',original)]:
        path=DEST/'receipt-bytes'/label/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(data)
    (CHECKOUT/name).write_bytes(original);records.append(row)
attributes=CHECKOUT/'.gitattributes'
with attributes.open('a',encoding='utf-8',newline='\n') as stream:
    stream.write('\n# Preserve additional independently bound historical receipt bytes.\n')
    for name,_,_,_ in prepared:stream.write('/'+name+' -text whitespace=cr-at-eol\n')
    stream.write('/docs/audits/2026-09-12-cm-count-closures/** -text whitespace=cr-at-eol\n')
with (DEST/'RECEIPT-RESTORATION.json').open('x') as stream:json.dump(records,stream,indent=2);stream.write('\n')
print(json.dumps(dict(restored_files=len(records),expected_hashes_changed=False)))
