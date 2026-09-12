"""Reconcile exact counts, all frozen benchmark cells and regression evidence."""
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import re
from statistics import median
import xml.etree.ElementTree as ET

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2];CHECKOUT=ROOT/'build/cm-closures'
PRIOR=CHECKOUT/'docs/audits/2026-09-12-cm-application-evidence'
FRONTIER=CHECKOUT/'docs/audits/2026-09-12-cm-evidence-frontiers'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value):(AUDIT/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def run():
    kinds={'feature':read(PRIOR/'FEATURE-CASES.json'),'independent':read(FRONTIER/'INDEPENDENT-CASES.json')}
    cases={c['id']:c for cohort in kinds.values() for c in cohort}
    attempts=[]
    for n in range(1,8):
        folder=AUDIT/f'attempt-{n:03d}';record=read(folder/'RUN.json')
        assert record['cleanup']['owned_pod_absent'] and not record['creation_uncertain']
        assert sha(folder/'evidence.zip')==record['evidence']['sha256']
        assert record['status']==('failed' if n==3 else 'complete'),folder.name
        attempts.append(dict(id=folder.name,status=record['status'],created=record['creation_attempted'],
            cleanup_verified=True,rate_usd_per_hour=record['actual_resources']['rate_usd_per_hour'],
            cost_upper_bound_usd=record['cost_upper_bound_usd'],reserved_usd=read(folder/'RESERVATION.json')['reserved_usd'],
            run_sha256=sha(folder/'RUN.json'),evidence_sha256=record['evidence']['sha256']))
    controls=read(AUDIT/'attempt-001/evidence/d4-oracle/CONTROLS.json')
    assert len(controls)==36 and all(r['status']=='complete' and r['value']==r['expected'] for r in controls)
    database=defaultdict(list)
    def add(case,context,value,counter,path):
        assert type(value) is int and value>=0
        index=cases[case]['contexts'].index(context)
        key=(case,index)
        assert all(r['value']==value for r in database[key]),(key,value,database[key])
        database[key].append(dict(value=value,counter=counter,path=path))
    prior_oracles=[('attempt-001/evidence/oracle/QIF-RESULTS.json','ganak'),
        ('attempt-003/evidence/feature-oracle/RESULTS.json','ganak'),
        ('attempt-006/evidence/oracle-extension/RESULTS.json','ganak')]
    for relative,counter in prior_oracles:
        for row in read(PRIOR/relative):
            if row['status']=='complete':add(row['case'],row['context'],row['value'],counter,(PRIOR/relative).relative_to(CHECKOUT).as_posix())
    for row in read(PRIOR/'attempt-008/evidence/synthesis-enumeration/RESULTS.json'):
        assert row['status']=='complete'
        add(row['case'],row['context'],row['value'],row['solver'],'prior verified synthesis enumeration')
    for relative in ('attempt-002/evidence/feature-benchmark/RESULTS.json','attempt-004/evidence/independent-benchmark/RESULTS.json'):
        for row in read(PRIOR/relative):
            if row['status']=='complete' and row['method'].startswith('cudd'):
                for context,value in zip(cases[row['case']]['contexts'],row['values'],strict=True):
                    add(row['case'],context,value,'cudd','prior independently verified CUDD benchmark')
    oracle_attempts=[]
    for relative,counter in [('attempt-001/evidence/d4-oracle/RESULTS.json','d4'),
                             ('attempt-002/evidence/ganak-oracle/RESULTS.json','ganak'),
                             ('attempt-006/evidence/oracle-retry/RESULTS.json',None),
                             ('attempt-007/evidence/remaining-counts/RESULTS.json',None)]:
        for row in read(AUDIT/relative):
            identity=row.get('counter',counter)
            if row['status']=='complete':add(row['case'],row['context'],row['value'],identity,relative)
            public_row={k:v for k,v in row.items() if k not in ('command','value')}
            if 'value' in row:public_row['value']=str(row['value'])
            oracle_attempts.append(dict(counter=identity,source=relative,**{k:v for k,v in public_row.items() if k!='counter'}))
    raw=read(AUDIT/'attempt-004/evidence/component-study/RESULTS.json')
    for row in raw:
        if row['status']=='complete' and row['method'] in ('component_count','cudd_dynamic'):
            for context,value in zip(cases[row['case']]['contexts'],row['values'],strict=True):
                add(row['case'],context,value,'component_count' if row['method']=='component_count' else 'cudd',
                    'attempt-004/evidence/component-study/RESULTS.json')
    entries=[]
    for kind,cohort in kinds.items():
        for case in cohort:
            for index,context in enumerate(case['contexts']):
                values=database[(case['id'],index)];assert values
                counters=sorted({r['counter'] for r in values})
                entries.append(dict(kind=kind,case=case['id'],context_index=index,context=context,
                    exact_value=str(values[0]['value']),counters=counters,independently_cross_checked=len(counters)>=2))
    assert len(entries)==120
    closure_oracle=dict(controls_passed=36,feature_completed=72,independent_completed=48,
        feature_cross_checked=sum(r['independently_cross_checked'] for r in entries if r['kind']=='feature'),
        independent_cross_checked=sum(r['independently_cross_checked'] for r in entries if r['kind']=='independent'),
        entries=entries,attempts=oracle_attempts,
        note='Exact values retain arbitrary-precision decimal strings. Every fixed context has a completed counter result; agreement between separately implemented counters is distinguished from a single-counter result and is not a certified proof. Counter identities distinguish Ganak, d4, CUDD, SAT enumeration and the independently implemented component candidate. The latter passed exhaustive enumeration controls. Retries change deadlines or memory caps and are not performance comparisons.')

    raw=read(AUDIT/'attempt-004/evidence/component-study/RESULTS.json')
    expected={(c['id'],method,repeat) for c in cases.values() for method in ('component_count','array_min_fill','cudd_dynamic') for repeat in range(3)}
    assert len(raw)==len(expected)==135
    assert {(r['case'],r['method'],r['repeat']) for r in raw}==expected
    checked_outputs=0
    for row in raw:
        if row['status']=='complete':
            assert len(row['values'])==8
            for index,value in enumerate(row['values']):
                references=[r for r in database[(row['case'],index)] if r['counter'] in ('ganak','d4')]
                assert references and all(r['value']==value for r in references),row
                checked_outputs+=1
    studies={}
    for kind,cohort in kinds.items():
        rows=[]
        for case in cohort:
            for method in ('component_count','array_min_fill','cudd_dynamic'):
                group=[r for r in raw if r['case']==case['id'] and r['method']==method]
                statuses=dict(Counter(r['status'] for r in group))
                row=dict(case=case['id'],method=method,repeats=3,statuses=statuses,independently_cross_checked=False)
                if statuses=={'complete':3}:
                    row.update(status='complete',independently_cross_checked=True,
                        median_total_ms=median(r['total_ns'] for r in group)/1e6,
                        min_total_ms=min(r['total_ns'] for r in group)/1e6,max_total_ms=max(r['total_ns'] for r in group)/1e6,
                        exact_integer_outputs=[str(v) for v in group[0]['values']])
                else:
                    reasons=sorted({r['reason'] for r in group if r.get('reason')})
                    row.update(status='refused' if statuses=={'refused':3} else 'incomplete',
                               reason='; '.join([*(f'{v} {k}' for k,v in statuses.items()),*reasons]))
                rows.append(row)
        candidate=[r['case'] for r in rows if r['method']=='component_count' and r['status']=='complete']
        earlier=read(PRIOR/'PUBLIC-RESULTS.json')[kind+'_methods']
        earlier_complete={r['case'] for r in earlier if r['status']=='complete'}
        studies[kind]=dict(methods=rows,status_counts=dict(Counter(r['status'] for r in raw if r['kind']==kind)),
                           candidate_completed_cases=candidate,newly_completed_cases=sorted(set(candidate)-earlier_complete))
    studies.update(measured_utc='2026-09-12',timed_outputs_checked=checked_outputs,
        exhaustive_cases=1280,cache_modes=2,
        note='Nine feature and six independent cases, three methods, eight contexts and three fresh-process repetitions. Fifteen-second workers and 2 GiB address-space limit. Every completed timed output matches Ganak or d4. Setup, cold requests and cleanup are charged; the component candidate starts a fresh memo table per query. Results apply to this controlled workload and host, with no default promotion.')
    def tests(path):
        failures=[];passed=[]
        for test in ET.parse(path).iter('testcase'):
            name=test.attrib.get('classname','')+'::'+test.attrib['name']
            bad=[node for node in test if node.tag in ('failure','error')]
            failures.extend(dict(test=name,kind=node.tag,message=node.attrib.get('message'),detail=node.text) for node in bad)
            if not bad and not test.findall('skipped'):passed.append(name)
        return dict(failures=failures,passed_ids=passed)
    regression=tests(AUDIT/'attempt-005/evidence/FULL-TESTS.xml');focused=tests(AUDIT/'attempt-005/evidence/FOCUSED-TESTS.xml')
    assert not focused['failures']
    log=(AUDIT/'attempt-005/evidence/transport/full-regression.log').read_text()
    line=next(s for s in reversed(log.splitlines()) if 'passed' in s and 'subtests passed in' in s)
    counts={key:int(re.search(r'(\d+) '+key+r'\b',line)[1]) if re.search(r'(\d+) '+key+r'\b',line) else 0 for key in ('failed','passed','skipped','errors')}
    counts['subtests_passed']=int(re.search(r'(\d+) subtests passed',line)[1])
    assert len(regression['failures'])==counts['failed']+counts['errors']
    previous=read(PRIOR/'PUBLIC-RESULTS.json');old={r['test'] for r in previous['regression']['failures']};current={r['test'] for r in regression['failures']}
    recovered=sorted(old-current);new=sorted(current-old)
    assert not new,new
    assert set(recovered)<=set(regression['passed_ids'])
    fixture=read(AUDIT/'attempt-005/evidence/CLOSURE-FIXTURES.json')
    assert fixture['complete'] and fixture['expected_files']==fixture['restored']==46
    origin=read(AUDIT/'upstream/EPFL-BYTE-COMPARISON.json')
    assert origin['rows'][0]['retained_exact'] and not origin['retained_bytes_changed']
    cost=dict(new_conservative_bound_usd=sum(r['cost_upper_bound_usd'] for r in attempts),
              prior_conservative_bound_usd=0.592875834852457,combined_nonrefunded_reservations_usd=9.50,
              all_created_pods_deleted=True,posted_billing_verified=False)
    cost['combined_conservative_bound_usd']=cost['new_conservative_bound_usd']+cost['prior_conservative_bound_usd']
    public=previous
    public.update(schema='cm-count-closures-public-results/v1',latest_research_utc='2026-09-12',
        prior_summary_sha256=sha(PRIOR/'PUBLIC-RESULTS.json'),closure_oracle=closure_oracle,component_study=studies,
        epfl_origin=origin,cost=cost)
    public['legacy_study_fields']=dict(measured_utc=previous['measured_utc'],
        fields=['feature_methods','independent_methods','feature_note','independent_note',
                'feature_status_counts','independent_status_counts','oracle','oracle_extension'],
        note='These retained fields describe the earlier five-method application study and its initial oracle attempts. Current count coverage is closure_oracle; current paired timings are component_study. Do not compare timings across the two host placements as paired results.')
    public['regression_triage']=read(AUDIT/'REGRESSION-TRIAGE.json')
    public['fixtures'].update(restored_files=318,newly_restored_files=46,
        recovered_failure_ids=35+len(recovered),newly_recovered_failure_ids=len(recovered),remaining_failure_ids=len(current),
        note='Another 46 pinned public CNF files restored, for 318 dependencies total; three more original receipt files recovered without changing hashes. The EPFL origin discrepancy was a false positive caused by asymmetric line-ending normalization; the retained file exactly matches declared upstream.')
    public['regression']=dict(counts=counts,new_failure_ids=new,recovered=recovered,failures=regression['failures'],focused_passed=len(focused['passed_ids']),
        note=f"Current Linux replay: {counts['passed']} passed, {counts['subtests_passed']} passing subtests, {counts['failed']} failures, {counts['errors']} errors and {counts['skipped']} skipped. {len(recovered)} more historical failing IDs recovered, zero new failing IDs. The historical suite is not green.")
    completed=sum(len(studies[k]['candidate_completed_cases']) for k in kinds)
    expanded=sum(len(studies[k]['newly_completed_cases']) for k in kinds)
    public['disposition']=f"All 120 fixed application contexts have completed exact counts; {sum(r['independently_cross_checked'] for r in entries)} have agreement between independent counters. Residual-component counting completes {completed} of 15 cases and adds {expanded} cases beyond the prior methods' coverage. More historical dependencies and receipts are recovered, and the EPFL origin discrepancy is resolved. Natural backend-demand traces and remaining historical/platform failures still require evidence."
    write('PUBLIC-RESULTS.json',public)
    write('VERIFICATION.json',dict(status='pass',attempts=attempts,oracle_entries=entries,
        checked_timed_outputs=checked_outputs,regression=regression,cost=cost))
    print(json.dumps(dict(status='pass',counts=counts,recovered=len(recovered),counter_agreement=sum(r['independently_cross_checked'] for r in entries),candidate_cases=completed,new_cases=expanded,cost=cost)))

if __name__=='__main__':run()
