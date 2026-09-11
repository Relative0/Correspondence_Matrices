"""Consumed-corpus diagnosis: a failed native arm cannot suppress other methods."""
import argparse
import gc
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

from scripts.cm_next_count_campaign import AUDIT, METHODS, runner, write
from cmbench.backends.bucket_counts import CountPlanLimit


def worker(case,mode,method,output):
    resource.setrlimit(resource.RLIMIT_AS,(2 << 30,2 << 30))
    if method == 'oracle':
        count,_ = runner(case,mode,'cudd_dynamic')
        write(output/'ORACLE.json',[count(c) for c in case['contexts']])
        return
    expected = json.loads((output.parent/'ORACLE.json').read_text())
    with (output/'RAW.jsonl').open('x') as stream:
        for repeat in range(9):
            gc.collect(); began=time.perf_counter_ns()
            row=dict(case=case['id'],mode=mode,method=method,repeat=repeat,q=32)
            try:
                count,stats=runner(case,mode,method)
                prepared=time.perf_counter_ns()
                values=[count(c) for c in case['contexts']]
                queried=time.perf_counter_ns()
                warm=[count(c) for c in case['contexts']]
                warmed=time.perf_counter_ns()
                assert values==warm==expected
                cleanup=time.perf_counter_ns(); del count
                cleanup_ns=time.perf_counter_ns()-cleanup
                row.update(status='complete',exact=True,values=values,setup_ns=prepared-began,
                    query_ns=queried-prepared,warm_ns=warmed-queried,cleanup_ns=cleanup_ns,
                    total_ns=queried-began+cleanup_ns,stats=stats)
            except CountPlanLimit as exc:
                row.update(status='refused',reason=str(exc),admission_ns=time.perf_counter_ns()-began)
            except Exception as exc:
                row.update(status='failed',error_type=type(exc).__name__,reason=str(exc))
            stream.write(json.dumps(row)+'\n'); stream.flush()
            if row['status']=='failed': break


def invoke(case,mode,method,path,deadline):
    began=time.monotonic()
    remaining=deadline-began
    if remaining <= 1: return dict(status='campaign_deadline',elapsed_s=0)
    limit=min(120,remaining)
    with (path/(method+'.log')).open('xb') as stream:
        try:
            completed=subprocess.run([sys.executable,'-B','-m','scripts.cm_next_count_isolated','worker',
                '--case',case['id'],'--mode',mode,'--method',method,'--output',str(path)],
                stdout=stream,stderr=subprocess.STDOUT,timeout=limit)
            result=dict(status='finished' if completed.returncode==0 else 'failed',exit_code=completed.returncode)
        except subprocess.TimeoutExpired: result=dict(status='timeout',limit_s=limit)
    result['elapsed_s']=time.monotonic()-began
    return result


def run(part,output):
    output.mkdir(parents=True,exist_ok=False)
    cases=[c for c in json.loads((AUDIT/'COUNT-FIXTURES.json').read_text()) if c['cohort']=='additional_public']
    selected=cases[:4] if part=='first' else cases[4:]
    write(output/'PROTOCOL.json',dict(scope='consumed diagnostic; original attempts remain controlling for their original harness',
         cases=[c['id'] for c in selected],contexts='unchanged frozen 32-query traces',repeats=9,
         arm_order='per-method processes; reverse method order for alternating case-mode positions',
         timing='internal setup, query, cleanup; process startup reported separately; no paired comparative CI',
         oracle='exact CUDD dynamic order; independent from the Python/array algorithms',child_limit_s=120,global_limit_s=1800))
    outcomes=[]; deadline=time.monotonic()+1800
    for index,case in enumerate(selected):
        for mode_index,mode in enumerate(('full','projected')):
            folder=output/(case['id']+'-'+mode); folder.mkdir()
            oracle=invoke(case,mode,'oracle',folder,deadline)
            write(folder/'ORACLE-STATUS.json',oracle)
            if oracle['status']!='finished' or not (folder/'ORACLE.json').exists():
                outcomes.append(dict(case=case['id'],mode=mode,method='oracle',**oracle)); continue
            for method in (METHODS if (index+mode_index)%2==0 else METHODS[::-1]):
                target=folder/method; target.mkdir()
                status=invoke(case,mode,method,target,deadline)
                write(target/'STATUS.json',status)
                outcomes.append(dict(case=case['id'],mode=mode,method=method,**status))
            print(json.dumps(dict(case=case['id'],mode=mode,completed=True)),flush=True)
    write(output/'OUTCOMES.json',outcomes)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=('run','worker'))
    parser.add_argument('--part',choices=('first','last')); parser.add_argument('--case')
    parser.add_argument('--mode',choices=('full','projected')); parser.add_argument('--method')
    parser.add_argument('--output',type=Path); args=parser.parse_args()
    if args.action=='run': run(args.part,args.output)
    else:
        case=next(c for c in json.loads((AUDIT/'COUNT-FIXTURES.json').read_text()) if c['id']==args.case)
        worker(case,args.mode,args.method,args.output)
