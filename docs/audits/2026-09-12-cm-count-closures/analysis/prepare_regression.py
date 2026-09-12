"""Freeze fixture restoration and broad regression without changing old tests."""
import ast
import json
from pathlib import Path
AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2];CHECKOUT=ROOT/'build/cm-closures'
sources=['cmbench/comparative/component_counts.py','scripts/cm_d4_closure_oracle.py','scripts/cm_ganak_closure_oracle.py',
         'scripts/cm_component_count_study.py','scripts/restore_cm_closure_fixtures.py',
         'tests/test_component_counts.py','tests/test_closure_fixture_restoration.py','.gitattributes']
restoration=json.loads((CHECKOUT/'docs/audits/2026-09-12-cm-count-closures/RECEIPT-RESTORATION.json').read_text())
sources += [row['path'] for row in restoration]
for name in sources:
    if name.endswith('.py'):ast.parse((CHECKOUT/name).read_text())
commands=[
    dict(name='restore-prior',args=['scripts/restore_cm_historical_fixtures.py','--restore'],timeout=60),
    dict(name='restore-application',args=['scripts/restore_cm_application_fixtures.py','--restore','--download-d4','--output','/workspace/cm-packed-evidence/APPLICATION-FIXTURES.json'],timeout=120),
    dict(name='restore-closure',args=['scripts/restore_cm_closure_fixtures.py','--restore','--download','--output','/workspace/cm-packed-evidence/CLOSURE-FIXTURES.json'],timeout=300),
    dict(name='native-build',args=['scripts/build_cm_fused_slots.py'],timeout=30),
    dict(name='focused',args=['-m','pytest','tests/test_component_counts.py','tests/test_closure_fixture_restoration.py',
         '-q','-p','no:cacheprovider','--junitxml','/workspace/cm-packed-evidence/FOCUSED-TESTS.xml'],timeout=120),
    dict(name='full-regression',args=['-m','pytest','tests','-q','--tb=short','--continue-on-collection-errors','-p','no:cacheprovider',
         '--basetemp','/workspace/cm-pytest','--junitxml','/workspace/cm-packed-evidence/FULL-TESTS.xml'],timeout=2000,allow_failure=True)]
protocol=dict(purpose='Exact dependency and receipt restoration; unchanged historical expected hashes and tests; retain all failures',
    sources=sources,commands=commands,controller='scripts/runpod_closure_research_controller_v2.py',remote='scripts/cm_closure_research_remote_v2.py')
with (AUDIT/'closure-regression-PROTOCOL.json').open('x') as stream:json.dump(protocol,stream,indent=2);stream.write('\n')
