"""Classify observed remaining failures without changing historical expectations."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter
A=Path(__file__).resolve().parent
rows=[]
for test in ET.parse(A/'attempt-005/evidence/FULL-TESTS.xml').iter('testcase'):
    for node in test:
        if node.tag not in ('failure','error'):continue
        message=node.attrib.get('message','')
        category='historical replay or source identity'
        action='Recover the exact historical source/interpreter closure and rerun its unchanged verifier; retain current code separately.'
        if 'invalid ELF header' in message:
            category='Windows native binary on Linux'
            action='Replay with the recorded Windows runtime, or define a separate Linux native-build study with new identities. Do not substitute a Linux library under the old DLL hash.'
        elif '38615 == 38464' in message:
            category='specific missing historical backend'
            action='Locate the 38,464-byte backend with SHA-256 4b80a27fa4de67bf35fb13d76ea9d6cd679bfb6dafc8b554741f4987c49bcbdc; the recorded bounded search found no copy.'
        rows.append(dict(test=test.attrib.get('classname','')+'::'+test.attrib['name'],kind=node.tag,
                         category=category,observed_message=message,next_evidence=action))
assert len(rows)==21
result=dict(status='classified_observed_failures',categories=dict(Counter(r['category'] for r in rows)),
            inference_scope='Categories describe observed failure messages, not proof that every downstream issue has the same cause.',
            tests_changed=False,rows=rows)
(A/'REGRESSION-TRIAGE.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result['categories']))
