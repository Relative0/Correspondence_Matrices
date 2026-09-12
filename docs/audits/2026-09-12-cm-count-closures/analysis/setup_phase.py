"""Create a new research audit without changing earlier controllers or seals."""
import hashlib
import json
from pathlib import Path
import urllib.request

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
CHECKOUT=ROOT/'build/cm-closures'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
source=(ROOT/'scripts/runpod_application_research_controller.py').read_text()
source=source.replace('2026-09-12-cm-application-evidence','2026-09-12-cm-count-closures')
source=source.replace('build/cm-applications','build/cm-closures')
source=source.replace('cm_application_research_remote.py','cm_closure_research_remote.py')
source=source.replace('BUDGET = 4.0','BUDGET = 2.25')
source=source.replace("'2026-09-12-cm-evidence-frontiers')", "'2026-09-12-cm-evidence-frontiers', '2026-09-12-cm-application-evidence')")
assert '2026-09-12-cm-application-evidence' in source
path=ROOT/'scripts/runpod_closure_research_controller.py'
with path.open('x',encoding='utf-8',newline='\n') as stream:stream.write(source)
remote=(ROOT/'scripts/cm_application_research_remote.py').read_text().replace(
    '6f38fa521619aa0cbf91ee3c294ffca304e313ba','643b5b6c9614ee1d1daed4eb374a431a67514587')
with (ROOT/'scripts/cm_closure_research_remote.py').open('x',encoding='utf-8',newline='\n') as stream:stream.write(remote)
(AUDIT/'packages').mkdir(exist_ok=False)
prior=[]
for name in ('2026-09-11-cm-next-research','2026-09-12-cm-evidence-frontiers','2026-09-12-cm-application-evidence'):
    for path in (ROOT/'docs/audits'/name).glob('attempt-*/RESERVATION.json'):
        prior.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),reserved_usd=json.loads(path.read_text())['reserved_usd']))
assert sum(r['reserved_usd'] for r in prior)==7.75
(AUDIT/'PRIOR-RESERVATIONS.json').write_text(json.dumps(prior,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(prior_reservations_usd=7.75,remaining_reservations_usd=2.25)))
