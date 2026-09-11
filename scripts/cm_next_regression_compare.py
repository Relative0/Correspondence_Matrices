"""Same-host clean-publication versus integrated-source broad regression replay."""
import json
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('/workspace/cm-packed-evidence/regression')
BASE = Path('/workspace/cm-regression-baseline')


def run():
    OUT.mkdir(parents=True,exist_ok=False)
    subprocess.run(['git','worktree','add','--detach',str(BASE),'d15cb618f4eb99b6621e4ab24773a00f03ae484e'],cwd=ROOT,check=True)
    records = []
    for label, directory in (('published',BASE),('integrated',ROOT)):
        command = [sys.executable,'-B','-m','pytest','tests','-q','--tb=short','--continue-on-collection-errors',
                   '-p','no:cacheprovider','--basetemp','/workspace/pytest-'+label,'--junitxml',str(OUT/(label+'.xml'))]
        started = time.monotonic()
        with (OUT/(label+'.log')).open('xb') as stream:
            result = subprocess.run(command,cwd=directory,stdout=stream,stderr=subprocess.STDOUT,timeout=1100)
        records.append(dict(label=label,exit_code=result.returncode,elapsed_s=time.monotonic()-started))
    (OUT/'RUNS.json').write_text(json.dumps(records,indent=2)+'\n')
    outcomes = {}
    for label in ('published','integrated'):
        rows = []
        for case in ET.parse(OUT/(label+'.xml')).iter('testcase'):
            status = next((kind for kind in ('failure','error','skipped') if case.find(kind) is not None),'passed')
            node = case.find(status) if status != 'passed' else None
            rows.append(dict(test=case.get('classname','')+'::'+case.get('name',''),status=status,
                             message=node.get('message') if node is not None else None))
        outcomes[label] = rows
    (OUT/'TEST-OUTCOMES.json').write_text(json.dumps(outcomes,indent=2)+'\n')
    before = {r['test']:r for r in outcomes['published']}; after = {r['test']:r for r in outcomes['integrated']}
    bad = ('failure','error')
    diff = dict(new_failures=[r for k,r in after.items() if r['status'] in bad and (k not in before or before[k]['status'] not in bad)],
                fixed_failures=[r for k,r in after.items() if r['status']=='passed' and k in before and before[k]['status'] in bad],
                added_tests=[r for k,r in after.items() if k not in before],
                retained_failures=[r for k,r in after.items() if r['status'] in bad and k in before and before[k]['status'] in bad])
    (OUT/'DIFFERENTIAL.json').write_text(json.dumps(diff,indent=2)+'\n')
    print(json.dumps({k:len(v) for k,v in diff.items()}),flush=True)


if __name__ == '__main__': run()
