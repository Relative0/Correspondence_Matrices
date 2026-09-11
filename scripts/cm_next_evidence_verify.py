"""Reaggregate the new campaign without executing research workloads."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT/'docs/audits/2026-09-11-cm-next-research'


def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data): path.write_text(json.dumps(data,indent=2)+'\n')


def counts(attempt):
    folder = attempt/'evidence/counts'
    expected_schedule = read(AUDIT/'COUNT-SCHEDULE.json')
    cases = {r['id']:r for r in read(AUDIT/'COUNT-FIXTURES.json')}
    rows = []; summaries = []; outcomes = read(folder/'OUTCOMES.json')
    for outcome in outcomes:
        target = folder/(outcome['case']+'-'+outcome['mode'])
        scheduled = [r for r in expected_schedule if r['case']==outcome['case'] and r['mode']==outcome['mode']]
        group = [json.loads(line) for line in (target/'RAW.jsonl').read_text().splitlines()] if (target/'RAW.jsonl').exists() else []
        assert [{k:r[k] for k in ('case','mode','repeat','method')} for r in group] == scheduled[:len(group)]
        if outcome['status'] == 'complete': assert len(group) == len(scheduled)
        if group:
            oracle = read(target/'ORACLE.json')
            assert len(oracle) == 32 and all(type(v) is int and v >= 0 for v in oracle)
            for r in group:
                assert r['status'] in ('complete','refused')
                if r['status'] == 'complete':
                    assert r['exact'] and r['values'] == oracle
                    assert r['total_ns'] == r['setup_ns']+r['query_ns']+r['cleanup_ns']
                    assert all(r[k] > 0 for k in ('total_ns','setup_ns','query_ns','warm_ns'))
                else: assert r['reason'] and r['admission_ns'] > 0
        rows += group
        for method in ('bucket_natural','bucket_min_fill','array_min_fill','cudd_natural','cudd_dynamic'):
            selected = [r for r in group if r['method'] == method]
            summary = dict(attempt=attempt.name,case=outcome['case'],mode=outcome['mode'],method=method,q=32,
                           cohort=cases[outcome['case']]['cohort'],observed_repetitions=len(selected),planned_repetitions=9)
            complete = [r for r in selected if r['status']=='complete']
            if len(complete)==9:
                summary.update(status='complete',cold_ms=statistics.median(r['total_ns'] for r in complete)/1e6,
                    setup_ms=statistics.median(r['setup_ns'] for r in complete)/1e6,
                    warm_ms=statistics.median(r['warm_ns'] for r in complete)/1e6,
                    observed_warm_range_ms=[min(r['warm_ns'] for r in complete)/1e6,max(r['warm_ns'] for r in complete)/1e6])
                for baseline in ('cudd_natural','cudd_dynamic'):
                    native = {r['repeat']:r for r in group if r['method']==baseline and r['status']=='complete'}
                    if len(native) != 9: continue
                    logs = [math.log(native[r['repeat']]['total_ns']/r['total_ns']) for r in complete]
                    rng = random.Random(2026091193)
                    draws = sorted(math.exp(sum(rng.choices(logs,k=9))/9) for _ in range(500))
                    summary[baseline] = dict(paired_geomean_speedup=math.exp(statistics.mean(logs)),ci95=[draws[12],draws[487]])
            elif len(selected)==9 and not complete:
                assert all(r['status']=='refused' for r in selected)
                summary.update(status='refused',reason=selected[0]['reason'])
            else:
                summary.update(status='incomplete',reason=outcome['status'],observed_complete=len(complete),
                               observed_refused=len(selected)-len(complete))
            summaries.append(summary)
    return dict(outcomes=outcomes,summaries=summaries,verified_rows=len(rows),
                expected_rows=len(outcomes)*45,missing_rows=len(outcomes)*45-len(rows),
                status_counts=dict(Counter(r['status'] for r in rows)),
                checked_query_outputs=2*32*sum(r['status']=='complete' for r in rows),
                exact_for_all_completed_rows=True)


def pipes(attempt):
    folder=attempt/'evidence/pipes'; schedule=read(folder/'SCHEDULE.json')
    rows=[json.loads(s) for s in (folder/'RAW.jsonl').read_text().splitlines()]
    assert len(rows)==len(schedule)==288
    summary=[]
    for expected,row in zip(schedule,rows):
        assert all(row[k]==expected[k] for k in ('n','width','cancel','repeat')) and row['delay_s']==expected['delay']
        receipt,consumer=row['receipt'],row['consumer']
        assert row['independent_exact'] and receipt['sha256']==consumer['sha256'] and receipt['written_bytes']==consumer['bytes']
        assert row['producer_consumer_peak_rss_sum_upper_bytes']==row['memory_after']['VmHWM']+consumer['memory']['VmHWM']
    keys=sorted({(r['n'],r['width'],r['delay_s'],r['cancel']) for r in rows})
    for n,width,delay,cancel in keys:
        group=[r for r in rows if (r['n'],r['width'],r['delay_s'],r['cancel'])==(n,width,delay,cancel)]
        assert len(group)==9
        summary.append(dict(n=n,width=width,delay_s=delay,cancel=cancel,repetitions=9,
            written_bytes=group[0]['receipt']['written_bytes'],completed=group[0]['receipt']['completed'],
            median_total_ms=statistics.median(r['total_ns'] for r in group)/1e6,
            median_first_accepted_ms=statistics.median(r['first_accepted_ns'] for r in group)/1e6,
            median_first_consumed_ms=statistics.median(r['first_consumed_ns'] for r in group)/1e6,
            median_process_lifecycle_ms=statistics.median(r['process_lifecycle_ns'] for r in group)/1e6,
            median_rss_upper_mib=statistics.median(r['producer_consumer_peak_rss_sum_upper_bytes'] for r in group)/(1 << 20)))
    return dict(rows=len(rows),exact=True,summary=summary)


def preparation(attempt):
    rows=read(attempt/'evidence/preparation/RAW.json'); assert len(rows)==324 and all(r['exact'] for r in rows)
    summaries=[]
    for family,n,q,method in sorted({(r['family'],r['n'],r['q'],r['method']) for r in rows}):
        selected=[r for r in rows if (r['family'],r['n'],r['q'],r['method'])==(family,n,q,method)]
        assert len(selected)==9
        summaries.append(dict(family=family,n=n,q=q,method=method,
            median_total_ms=statistics.median(r['total_ns'] for r in selected)/1e6,
            median_with_initial_setup_ms=statistics.median(r['total_with_initial_setup_ns'] for r in selected)/1e6,
            median_setup_ms=statistics.median(r['setup_ns'] for r in selected)/1e6,
            median_query_ms=statistics.median(r['query_ns'] for r in selected)/1e6,
            original_storage_ms=selected[0]['original_storage_ns']/1e6,serialized_bytes=selected[0]['serialized_bytes']))
    return dict(rows=len(rows),exact=True,summary=summaries)


def isolated(attempt):
    folder=attempt/'evidence/isolated-counts'
    protocol=read(folder/'PROTOCOL.json'); outcomes=read(folder/'OUTCOMES.json')
    summaries=[]; statuses=Counter(); checked=0
    for case in protocol['cases']:
        for mode in ('full','projected'):
            target=folder/(case+'-'+mode)
            oracle=read(target/'ORACLE.json') if (target/'ORACLE.json').exists() else None
            for method in ('bucket_natural','bucket_min_fill','array_min_fill','cudd_natural','cudd_dynamic'):
                path=target/method/'RAW.jsonl'
                rows=[json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
                assert [r['repeat'] for r in rows]==list(range(len(rows)))
                assert all((r['case'],r['mode'],r['method'],r['q'])==(case,mode,method,32) for r in rows)
                for r in rows:
                    statuses[r['status']]+=1
                    if r['status']=='complete':
                        assert r['exact'] and oracle is not None and r['values']==oracle
                        assert r['total_ns']==r['setup_ns']+r['query_ns']+r['cleanup_ns']
                        checked+=64
                summary=dict(attempt=attempt.name,case=case,mode=mode,method=method,q=32,
                             observed_repetitions=len(rows),planned_repetitions=9)
                if len(rows)==9 and all(r['status']=='complete' for r in rows):
                    summary.update(status='complete',cold_ms=statistics.median(r['total_ns'] for r in rows)/1e6,
                                   warm_ms=statistics.median(r['warm_ns'] for r in rows)/1e6)
                elif len(rows)==9 and all(r['status']=='refused' for r in rows):
                    summary.update(status='refused',reason=rows[0]['reason'])
                else:
                    measured=(target/method/'STATUS.json').exists()
                    status=read(target/method/'STATUS.json') if measured else read(target/'ORACLE-STATUS.json')
                    reason=next((r['reason'] for r in rows if r['status']=='failed'),
                                'method process '+status['status'] if measured else 'independent oracle '+status['status']+'; method not measured')
                    summary.update(status='incomplete',reason=reason)
                summaries.append(summary)
    return dict(protocol=protocol,outcomes=outcomes,summaries=summaries,status_counts=dict(statuses),checked_query_outputs=checked,
                exact_for_all_completed_rows=True)


def regression_final():
    path=AUDIT/'attempt-014/evidence/FINAL-TESTS.xml'
    if not path.exists(): return None
    published=read(AUDIT/'attempt-009/evidence/regression/TEST-OUTCOMES.json')['published']
    before={r['test']:r['status'] for r in published}
    failures=[]; fixed=[]; added=[]
    for case in ET.parse(path).iter('testcase'):
        name=case.get('classname','')+'::'+case.get('name','')
        status=next((s for s in ('failure','error','skipped') if case.find(s) is not None),'passed')
        if status in ('failure','error'):
            failures.append(dict(test=name,status=status,preexisting=before.get(name) in ('failure','error')))
        if status=='passed' and before.get(name) in ('failure','error'): fixed.append(name)
        if name not in before: added.append(dict(test=name,status=status))
    line=(AUDIT/'attempt-014/evidence/transport/full-regression-final.log').read_text().splitlines()[-1]
    numbers={name:int(value) for value,name in re.findall(r'(\d+) (failed|passed|skipped|errors|subtests passed)',line)}
    return dict(summary=line,counts=numbers,failures=failures,new_failures=[r for r in failures if not r['preexisting']],
                fixed_failures=fixed,added_tests=added)


def verify():
    result=dict(attempts={},counts={},isolated={},pipes={},preparation={},soaks={},tests={})
    for attempt in sorted(AUDIT.glob('attempt-*')):
        if not (attempt/'RUN.json').exists(): continue
        run=read(attempt/'RUN.json'); result['attempts'][attempt.name]=dict(status=run['status'],
            error=run.get('error'),creation_attempted=run['creation_attempted'],creation_uncertain=run['creation_uncertain'],
            cost_upper_bound_usd=(read(attempt/'RESERVATION.json')['reserved_usd'] if run['creation_uncertain'] else run.get('cost_upper_bound_usd',0)),
            recorded_elapsed_cost_estimate_usd=run.get('cost_upper_bound_usd',0),
            cleanup_verified=run.get('cleanup',{}).get('owned_pod_absent',not run['creation_attempted']))
        if (attempt/'evidence/transport/SOURCE_VERIFICATION.json').exists():
            profile=read(attempt/'RESERVATION.json')['profile']; freeze=read(AUDIT/'packages'/(profile+'-FREEZE.json'))
            assert read(attempt/'evidence/transport/SOURCE_VERIFICATION.json')==freeze['source']
            assert sha(AUDIT/'packages'/(profile+'.zip'))==freeze['bundle_sha256']
            placement=read(attempt/'evidence/transport/PLACEMENT.json')
            result['attempts'][attempt.name]['machine_id']=placement['runpod_machine_id']
            result['attempts'][attempt.name]['cpu_model']=next(s.partition(':')[2].strip() for s in placement['cpuinfo'].splitlines() if s.startswith('model name'))
        if (attempt/'evidence/counts/OUTCOMES.json').exists(): result['counts'][attempt.name]=counts(attempt)
        if (attempt/'evidence/isolated-counts/OUTCOMES.json').exists(): result['isolated'][attempt.name]=isolated(attempt)
        if (attempt/'evidence/pipes/RESULT.json').exists(): result['pipes'][attempt.name]=pipes(attempt)
        if (attempt/'evidence/preparation/RESULT.json').exists(): result['preparation'][attempt.name]=preparation(attempt)
        if (attempt/'evidence/SOAK.json').exists():
            soak=read(attempt/'evidence/SOAK.json'); assert soak['exact'] and soak['seconds']>=120
            assert soak['cache_after']['entry_bytes']==0
            assert all(r['cache']['entry_bytes']<=r['cache']['max_bytes'] for r in soak['snapshots'])
            result['soaks'][attempt.name]=soak
        for xml in (attempt/'evidence').rglob('*.xml'):
            if not xml.name.endswith('.xml'): continue
            try: document=ET.parse(xml)
            except ET.ParseError: continue
            suites=list(document.iter('testsuite'))
            if suites: result['tests'][(attempt.name+'/'+xml.relative_to(attempt).as_posix())]={k:sum(int(s.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    result['reserved_usd']=sum(read(p)['reserved_usd'] for p in AUDIT.glob('attempt-*/RESERVATION.json'))
    result['final_regression']=regression_final()
    result['estimated_cost_upper_usd']=sum(r['cost_upper_bound_usd'] for r in result['attempts'].values())
    assert result['reserved_usd'] <= 10
    write(AUDIT/'VERIFICATION.json',result)
    print(json.dumps(dict(count_runs=len(result['counts']),pipe_runs=len(result['pipes']),preparation_runs=len(result['preparation']),
                         estimated_cost_upper_usd=result['estimated_cost_upper_usd'],reserved_usd=result['reserved_usd'])))


if __name__ == '__main__': verify()
