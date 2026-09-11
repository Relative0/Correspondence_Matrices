"""Frozen feature semantics, concrete-selection counts and bounded candidates."""
import argparse
import gc
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

from cmbench.backends.bucket_counts import CountPlanLimit
from cmbench.comparative.projected_simplify import count_simplified
from scripts.cm_application_oracle import install, count, write
from scripts.cm_next_count_campaign import runner, LIMITS

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'docs/audits/2026-09-12-cm-application-evidence'
METHODS=('bucket_min_fill','array_min_fill','cudd_natural','cudd_dynamic','simplified_bucket')

def read(name):return json.loads((AUDIT/name).read_text())

def cases(kind):
    if kind=='feature':return read('FEATURE-CASES.json')
    return json.loads((ROOT/'docs/audits/2026-09-12-cm-evidence-frontiers/INDEPENDENT-CASES.json').read_text())

def semantic(output):
    output.mkdir(parents=True,exist_ok=False);rows=[]
    for kind in ('original','concrete'):
        for solver in ('g3','m22'):
            destination=output/(kind+'-'+solver+'.json')
            with destination.with_suffix('.log').open('xb') as stream:
                try:
                    child=subprocess.run([sys.executable,'-B','-m','scripts.cm_application_studies','miter',
                        '--kind',kind,'--method',solver,'--output',str(destination)],stdout=stream,stderr=subprocess.STDOUT,timeout=30)
                    result=json.loads(destination.read_text()) if child.returncode==0 else dict(status='failed',exit_code=child.returncode)
                except subprocess.TimeoutExpired:result=dict(status='timeout')
            rows.append(dict(kind=kind,solver=solver,**result))
    write(output/'RESULTS.json',rows)
    return all(r['status']=='complete' and r['satisfiable'] is False for r in rows if r['kind']=='concrete')

def worker(args):
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    if args.action=='miter':
        from pysat.solvers import Solver
        problem=read('ATTRIBUTED-MITERS.json')[args.kind]
        start=time.perf_counter_ns()
        with Solver(name=args.method,bootstrap_with=problem['clauses']) as solver:
            sat=solver.solve();model=solver.get_model() if sat else None
        write(args.output,dict(status='complete',satisfiable=sat,model=model,elapsed_ns=time.perf_counter_ns()-start));return
    case=next(c for c in cases(args.kind) if c['id']==args.case)
    start=time.perf_counter_ns();diagnostics=[]
    try:
        if args.method=='simplified_bucket':
            def query(fixed):
                value,stats=count_simplified(case,fixed,plan_limits=LIMITS)
                diagnostics.append(stats);return value
            stats=dict(scope='every request pays conditioning, simplification and compilation')
        else:query,stats=runner(case,'projected',args.method)
        setup=time.perf_counter_ns()-start
        start=time.perf_counter_ns();values=[query(c) for c in case['contexts']];query_ns=time.perf_counter_ns()-start
        start=time.perf_counter_ns();warm=[query(c) for c in case['contexts']];warm_ns=time.perf_counter_ns()-start
        assert values==warm
        start=time.perf_counter_ns();del query;gc.collect();cleanup=time.perf_counter_ns()-start
        row=dict(status='complete',values=values,setup_ns=setup,query_ns=query_ns,warm_ns=warm_ns,
                 cleanup_ns=cleanup,total_ns=setup+query_ns+cleanup,stats=stats,diagnostics=diagnostics,
                 peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    except CountPlanLimit as exc:
        row=dict(status='refused',reason=str(exc),diagnostics=diagnostics)
    write(args.output,row)

def benchmark(output,kind):
    output.mkdir(parents=True,exist_ok=False)
    admitted=semantic(output/'semantic') if kind=='feature' else True
    rows=[]
    for case in cases(kind):
        for repeat in range(3):
            for method in (METHODS if repeat%2==0 else METHODS[::-1]):
                key=case['id']+'-'+method+'-'+str(repeat);path=output/(key+'.json')
                if case['id']=='additional-08' and not admitted:
                    result=dict(status='refused',reason='concrete Boolean abstraction not verified')
                else:
                    with (output/(key+'.log')).open('xb') as stream:
                        try:
                            child=subprocess.run([sys.executable,'-B','-m','scripts.cm_application_studies','worker','--kind',kind,
                                '--case',case['id'],'--method',method,'--output',str(path)],stdout=stream,stderr=subprocess.STDOUT,timeout=15)
                            result=json.loads(path.read_text()) if child.returncode==0 else dict(status='failed',exit_code=child.returncode)
                        except subprocess.TimeoutExpired:result=dict(status='timeout',limit_s=15)
                rows.append(dict(case=case['id'],method=method,repeat=repeat,**result))
                print(json.dumps(dict(case=case['id'],method=method,repeat=repeat,status=result['status'])),flush=True)
    write(output/'RESULTS.json',rows)

def feature_oracle(output):
    output.mkdir(parents=True,exist_ok=False);admitted=semantic(output/'semantic')
    binary=install(output);rows=[]
    for case in cases('feature'):
        for i,fixed in enumerate(case['contexts']):
            if case['id']=='additional-08' and not admitted:row=dict(case=case['id'],status='refused',reason='Boolean abstraction not verified')
            else:row=count(binary,case,fixed,output,case['id']+'-'+str(i),20)
            rows.append(row)
            print(json.dumps(dict(case=case['id'],context_index=i,status=row['status'])),flush=True)
    write(output/'RESULTS.json',rows)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('miter','worker','bench','oracle'))
    parser.add_argument('--kind',default='feature');parser.add_argument('--case');parser.add_argument('--method')
    parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    if args.action=='bench':benchmark(args.output,args.kind)
    elif args.action=='oracle':feature_oracle(args.output)
    else:worker(args)
