"""Combine verified scientific results with the completed regression and custody."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2];CHECKOUT=ROOT/'build/cm-applications'
def read(name):return json.loads((AUDIT/name).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value):
 with (AUDIT/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')

attempts=[]
for i in range(1,9):
 name=f'attempt-{i:03d}';run=read(name+'/RUN.json')
 assert run['status']=='complete' and run['cleanup']['owned_pod_absent'] and not run['creation_uncertain'],name
 assert sha(AUDIT/name/'evidence.zip')==run['evidence']['sha256']
 attempts.append(dict(id=name,status=run['status'],created=run['creation_attempted'],cleanup_verified=True,
  rate_usd_per_hour=run['actual_resources']['rate_usd_per_hour'],cost_upper_bound_usd=run['cost_upper_bound_usd'],
  reserved_usd=read(name+'/RESERVATION.json')['reserved_usd'],run_sha256=sha(AUDIT/name/'RUN.json'),
  evidence_sha256=run['evidence']['sha256']))

def tests(filename,attempt='attempt-007'):
 tree=ET.parse(AUDIT/attempt/'evidence'/filename)
 failures=[];passed=[]
 for test in tree.iter('testcase'):
  name=test.attrib.get('classname','')+'::'+test.attrib['name']
  bad=[node for node in test if node.tag in ('failure','error')]
  failures.extend(dict(test=name,kind=node.tag,message=node.attrib.get('message'),detail=node.text) for node in bad)
  if not bad and not test.findall('skipped'):passed.append(name)
 return dict(failures=failures,passed_ids=passed)

regression=tests('FULL-TESTS.xml');focused=tests('FOCUSED-TESTS.xml')
assert not focused['failures']
log=(AUDIT/'attempt-007/evidence/transport/full-regression.log').read_text(encoding='utf-8')
line=next(line for line in reversed(log.splitlines()) if 'passed' in line and 'subtests passed in' in line)
counts={key:int(re.search(r'(\d+) '+key+r'\b',line)[1]) for key in ('failed','passed','skipped','errors')}
counts['subtests_passed']=int(re.search(r'(\d+) subtests passed',line)[1])
assert len(regression['failures'])==counts['failed']+counts['errors']
prior=json.loads((CHECKOUT/'docs/audits/2026-09-12-cm-evidence-frontiers/PUBLIC-RESULTS.json').read_text())
old={r['test'] for r in prior['regression']['failures']};current={r['test'] for r in regression['failures']}
new=sorted(current-old);recovered=sorted(old-current)
assert not new,new
assert set(recovered)<=set(regression['passed_ids'])
restored=read('attempt-007/evidence/APPLICATION-FIXTURES.json')
assert restored['expected_files']==restored['restored']==157 and restored['complete']
study=read('STUDY-ANALYSIS.json')
extension=read('attempt-006/evidence/oracle-extension/RESULTS.json')
assert len(extension)==40
assert set(r['case'] for r in extension)=={'additional-09','independent-03','independent-07','independent-08','independent-09'}
for case in sorted(set(r['case'] for r in extension)):
 rows=[r for r in extension if r['case']==case]
 assert len(rows)==8 and rows[0]['context']=={}
 assert rows[0]['limit_s']==60
 if rows[0]['status']!='complete':assert all(r['status']=='not_scheduled' for r in rows[1:])
 else:assert all(r['limit_s']==30 for r in rows[1:])
enumeration=read('attempt-008/evidence/synthesis-enumeration/RESULTS.json')
enumeration_controls=read('attempt-008/evidence/synthesis-enumeration/CONTROLS.json')
assert len(enumeration_controls)==66 and all(r['status']=='complete' and r['value']==r['expected'] for r in enumeration_controls)
assert len(enumeration)==48
matches=set()
for row in enumeration:
 assert row['status']=='complete'
 key=(row['case'],json.dumps(row['context'],sort_keys=True),row['solver'])
 assert key not in matches
 matches.add(key)
 other=next(r for r in extension if r['case']==row['case'] and r['context']==row['context'])
 assert other['status']=='complete' and other['value']==row['value']
assert {r['case'] for r in enumeration}=={'independent-07','independent-08','independent-09'}
assert {r['solver'] for r in enumeration}=={'g3','m22'}
for row in extension:
 if row['status']=='complete':row['value']=str(row['value'])

models=prior['models']
pc=next(r for r in models if r['id']=='additional-08')
pc.update(identity_mapped=True,original_features=377,concrete_features=376,unmatched_variables=[],
 original_feature_equivalence=True,concrete_feature_equivalence=True,refusal=None,
 attribute_scope='Boolean selection abstraction only; 377 static double price attributes are metadata. No attribute-value configuration or price claim.')
cost=sum(r['cost_upper_bound_usd'] for r in attempts);reserved=sum(r['reserved_usd'] for r in attempts)
assert reserved+5.25<=10 and cost+.5025470124602317<10
video=read('VIDEO-CONSUMER-AUDIT.json')
public=dict(schema='cm-application-public-results/v1',status='verified_with_explicit_limitations',
 reviewed='2026-09-12',measured_utc='2026-09-11',models=models,
 mapping_note='All nine original model pairs now have checked concrete-feature contracts. The pc-richmond extended model is admitted only through a strict Boolean-selection abstraction, checked by Glucose3 and Minisat22. Static prices are metadata; configurable or unsupported attributes remain refused. Fiasco/uClibc retain their original abstract-root counterexamples and separate concrete-selection equivalence.',
 feature_methods=study['feature']['methods'],feature_status_counts=study['feature']['status_counts'],
 feature_note='All nine previously paired models, eight generated concrete-feature contexts, five methods, three fresh-process repetitions: 135 cells. Worker limit 15 seconds and 2 GiB. Ganak independently verified all 288 completed timed query outputs. The simplifier completed only Android and did not expand coverage; all conditioning and recompilation costs are charged.',
 feature_oracle_statuses=study['feature_oracle_statuses'],
 independent_admissions=prior['independent_admissions'],independent_methods=study['independent']['methods'],
 independent_status_counts=study['independent']['status_counts'],
 independent_note='The same six admitted information-flow/synthesis cases and unchanged contexts were rerun with five methods, three repetitions and a 15-second worker limit. The two completed QIF cases now match independent exact Ganak counts on all 16 contexts, including every prior and current completed CUDD repetition. The other cases remain explicit incomplete results. Changed deadlines and different hosts do not support before/after speedup claims.',
 oracle_extension=dict(protocol='Five unresolved cases; unconditional 60-second gate, then seven 30-second queries only after success. Not a timing comparison.',
  statuses=dict(Counter(r['status'] for r in extension)),queries=extension,
  synthesis_queries_verified_by_two_sat_solvers=24,
  synthesis_verification_note='After observing small Ganak counts, all three synthesis cases were selected for bounded projected-model enumeration. Glucose3 and Minisat22 matched all 24 counts; 66 exhaustive controls passed. This exploratory validation is not a prospectively selected performance comparison.'),
 oracle=dict(name='Ganak 2.6.3',probability=0,mode=0,exhaustive_controls=33,qif_contexts_verified=16,
  feature_contexts_completed=64,timed_outputs_matched=336,synthesis_contexts_verified=24,
  unique_feature_contexts_completed_including_followup=65,
  unique_independent_contexts_completed_including_followup=47,certified_proof=False),
 consumer=dict(natural_sessions_admitted=0,capture_ready=True,completed_video_artifacts_verified=3,
  note=video['interpretation']+' The adapter now targets the actual foundational formatter, including its set-valued highlighting arguments. A future actual production run is still needed for a runtime trace.'),
 video_audit=video,
 fixtures=dict(restored_files=272,newly_restored_files=157,recovered_failure_ids=25+len(recovered),
  newly_recovered_failure_ids=len(recovered),remaining_failure_ids=len(current),
  restored_receipt_files=4,
  note='115 prior fixtures plus 156 LogikBench files and the pinned public d4 executable. Four historical receipts also recover their originally recorded CRLF bytes; JSON values and expected hashes were not edited. Both byte variants are retained. The d4 binary is downloaded directly from immutable upstream and not republished in a new archive.'),
 regression=dict(counts=counts,new_failure_ids=new,recovered=recovered,failures=regression['failures'],
  focused_passed=len(focused['passed_ids']),
  note=f"Final Linux replay: {counts['passed']} passed, {counts['subtests_passed']} passing subtests, {counts['failed']} failures, {counts['errors']} errors and {counts['skipped']} skipped. {len(recovered)} further prior failing IDs recovered; no new failing IDs. The remaining historical suite is not green."),
 cost=dict(new_conservative_bound_usd=cost,prior_conservative_bound_usd=.5025470124602317,
  combined_conservative_bound_usd=cost+.5025470124602317,new_nonrefunded_reservations_usd=reserved,
  combined_nonrefunded_reservations_usd=reserved+5.25,all_created_pods_deleted=True,posted_billing_verified=False),
 disposition='All nine concrete-feature mappings are checked, including a restricted Boolean interpretation of pc-richmond. Independent exact counts now validate the completed QIF and concrete-feature measurements. Bounded simplification passed correctness controls but expanded neither benchmark cohort. More historical fixtures and the actual video production source were recovered and audited; genuine backend-demand traces and the remaining historical source closures still need evidence.')
write('PUBLIC-RESULTS.json',public)
write('VERIFICATION.json',dict(status='pass',attempts=attempts,study=study,
 regression=regression,regression_counts=counts,focused=focused,fixture_restoration=restored,
 extension_statuses=public['oracle_extension']['statuses'],synthesis_enumeration=enumeration,
 synthesis_control_count=len(enumeration_controls),cost=public['cost']))
print(json.dumps(dict(regression=counts,recovered=recovered,focused=len(focused['passed_ids']),extension=public['oracle_extension']['statuses'],cost=public['cost'])))
