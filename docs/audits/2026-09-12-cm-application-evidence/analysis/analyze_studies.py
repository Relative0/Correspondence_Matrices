"""Check every scheduled result and independent count before publishing metrics."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2];CHECKOUT=ROOT/'build/cm-applications'
def read(name):return json.loads((AUDIT/name).read_text(encoding='utf-8'))
def write(name,value):
 with (AUDIT/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2);f.write('\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

protocol=read('STUDY-PROTOCOL.json')
feature_cases=read('FEATURE-CASES.json')
independent_cases=json.loads((CHECKOUT/'docs/audits/2026-09-12-cm-evidence-frontiers/INDEPENDENT-CASES.json').read_text())
feature_oracle=read('attempt-003/evidence/feature-oracle/RESULTS.json')
qif=read('attempt-001/evidence/oracle/QIF-RESULTS.json')
controls=read('attempt-001/evidence/oracle/CONTROL-RESULTS.json')
assert len(controls)==33 and all(r['status']=='complete' and r['value']==r['expected'] for r in controls)

def oracle_map(rows,cases):
 expected={(c['id'],json.dumps(context,sort_keys=True)) for c in cases for context in c['contexts']}
 seen=set();result={}
 for row in rows:
  key=row['case'],json.dumps(row['context'],sort_keys=True)
  assert key in expected and key not in seen,key
  seen.add(key)
  if row['status']=='complete':
   assert type(row['value']) is int and row['value']>=0
   result[key]=row['value']
 assert seen==expected
 return result

def summarize(rows,cases,oracles):
 expected={(c['id'],m,r) for c in cases for m in protocol['methods'] for r in range(3)}
 assert len(rows)==len(expected) and {(r['case'],r['method'],r['repeat']) for r in rows}==expected
 summaries=[];matched=0
 for case in cases:
  keys=[(case['id'],json.dumps(context,sort_keys=True)) for context in case['contexts']]
  complete=[r for r in rows if r['case']==case['id'] and r['status']=='complete']
  for row in complete:
   assert len(row['values'])==8 and all(type(v) is int and v>=0 for v in row['values'])
   assert row['values']==complete[0]['values'],case['id']
   for key,value in zip(keys,row['values']):
    if key in oracles:
     assert value==oracles[key],key
     matched+=1
  verified=bool(complete) and all(k in oracles for k in keys)
  for method in protocol['methods']:
   selected=[r for r in rows if r['case']==case['id'] and r['method']==method]
   result=dict(case=case['id'],method=method,statuses=dict(Counter(r['status'] for r in selected)),
    repeats=3,independently_cross_checked=verified and all(r['status']=='complete' for r in selected))
   if result['independently_cross_checked']:
    result.update(status='complete',median_total_ms=statistics.median(r['total_ns'] for r in selected)/1e6,
     median_warm_ms=statistics.median(r['warm_ns'] for r in selected)/1e6,
     min_total_ms=min(r['total_ns'] for r in selected)/1e6,max_total_ms=max(r['total_ns'] for r in selected)/1e6,
     exact_integer_outputs=[str(v) for v in selected[0]['values']])
   else:
    result.update(status='refused' if all(r['status']=='refused' for r in selected) else 'incomplete',
     reason='; '.join(f'{v} {k}' for k,v in result['statuses'].items())+
      '; '+next((r.get('reason','') for r in selected if r.get('reason')),'no complete independently checked three-repetition measurement'))
   summaries.append(result)
 return dict(methods=summaries,status_counts=dict(Counter(r['status'] for r in rows)),
  scheduled_cells=len(rows),matched_timed_query_outputs=matched)

# The oracle retains exhaustive controls separately from the two QIF cases.
qif_rows=[r for r in qif if r.get('case') in ('independent-01','independent-02')]
independent_oracles=oracle_map(qif_rows,independent_cases[:2])
feature_oracles=oracle_map(feature_oracle,feature_cases)
features=summarize(read('attempt-002/evidence/feature-benchmark/RESULTS.json'),feature_cases,feature_oracles)
independent=summarize(read('attempt-004/evidence/independent-benchmark/RESULTS.json'),independent_cases,independent_oracles)
for attempt,study in [('002','feature-benchmark'),('003','feature-oracle')]:
 rows=read(f'attempt-{attempt}/evidence/{study}/semantic/RESULTS.json')
 assert {(r['kind'],r['solver']) for r in rows}=={(k,s) for k in ('original','concrete') for s in ('g3','m22')}
 assert all(r['status']=='complete' and r['satisfiable'] is False for r in rows)
write('STUDY-ANALYSIS.json',dict(schema='cm-application-study-analysis/v1',verified=True,feature=features,
 independent=independent,feature_oracle_statuses=dict(Counter(r['status'] for r in feature_oracle)),
 concrete_pc_richmond_admitted=True,pc_richmond_all_boolean_features_equivalent=True,
 scope='Independent Ganak integer counts verify outputs. Solver agreement is not a certified proof. Generated queries are not consumer traces; different hosts and changed worker deadlines are not paired speedup comparisons.'))
print(json.dumps(dict(feature=features['status_counts'],independent=independent['status_counts'],
 matched_timed_outputs=features['matched_timed_query_outputs']+independent['matched_timed_query_outputs'])))
