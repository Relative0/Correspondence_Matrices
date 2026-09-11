"""Isolated, prospectively bounded semantic and projected-count measurements."""
import argparse
import gc
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

from cmbench.backends.bucket_counts import CountPlanLimit
from scripts.cm_next_count_campaign import runner

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'docs/audits/2026-09-12-cm-evidence-frontiers'
METHODS=('bucket_natural','bucket_min_fill','array_min_fill','cudd_natural','cudd_dynamic')

def read(name):return json.loads((AUDIT/name).read_text())
def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')

def worker(args):
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
    if args.action=='miter':
        from pysat.solvers import Solver
        case=next(x for x in read('FEATURE-MITERS.json') if x['id']==args.case)
        start=time.perf_counter_ns()
        with Solver(name=args.method,bootstrap_with=case['clauses']) as solver:
            sat=solver.solve()
            model=solver.get_model() if sat else None
        write(args.output,dict(status='complete',satisfiable=sat,model=model,
                              elapsed_ns=time.perf_counter_ns()-start))
        return
    case=next(x for x in read('INDEPENDENT-CASES.json') if x['id']==args.case)
    start=time.perf_counter_ns()
    try:
        count,stats=runner(case,'projected',args.method)
        setup=time.perf_counter_ns()-start
        start=time.perf_counter_ns();values=[count(c) for c in case['contexts']]
        query=time.perf_counter_ns()-start
        start=time.perf_counter_ns();warm=[count(c) for c in case['contexts']]
        warm_ns=time.perf_counter_ns()-start
        assert values==warm
        start=time.perf_counter_ns();del count;gc.collect()
        cleanup=time.perf_counter_ns()-start
        result=dict(status='complete',values=values,setup_ns=setup,query_ns=query,
            warm_ns=warm_ns,cleanup_ns=cleanup,total_ns=setup+query+cleanup,stats=stats,
            peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    except CountPlanLimit as exc:
        result=dict(status='refused',reason=str(exc),admission_ns=time.perf_counter_ns()-start)
    write(args.output,result)

def isolated(output,action,case,method,repeat):
    key=f'{case}-{method}-{repeat}'
    result_path=output/(key+'.json')
    start=time.monotonic()
    with (output/(key+'.log')).open('xb') as stream:
        try:
            child=subprocess.run([sys.executable,'-B','-m','scripts.cm_frontier_campaign',action,
                '--case',case,'--method',method,'--output',str(result_path)],
                stdout=stream,stderr=subprocess.STDOUT,timeout=30)
            result=json.loads(result_path.read_text()) if child.returncode==0 else dict(status='failed',exit_code=child.returncode)
        except subprocess.TimeoutExpired:result=dict(status='timeout',limit_s=30)
    row=dict(case=case,method=method,repeat=repeat,wall_s=time.monotonic()-start,**result)
    print(json.dumps({k:v for k,v in row.items() if k not in ('values','model','stats')}),flush=True)
    return row

def run(output):
    output.mkdir(parents=True,exist_ok=False)
    miters=[]
    for case in read('FEATURE-MITERS.json'):
        for solver in ('g3','m22'):miters.append(isolated(output,'miter',case['id'],solver,0))
    write(output/'MITER-RESULTS.json',miters)
    rows=[]
    for case in read('INDEPENDENT-CASES.json'):
        for repeat in range(3):
            for method in (METHODS if repeat%2==0 else METHODS[::-1]):
                rows.append(isolated(output,'count',case['id'],method,repeat))
    comparisons=[]
    for case in read('INDEPENDENT-CASES.json'):
        complete=[r for r in rows if r['case']==case['id'] and r['status']=='complete']
        agreement=bool(complete) and all(r['values']==complete[0]['values'] for r in complete)
        independent=agreement and any(r['method'].startswith('cudd') for r in complete) and any(not r['method'].startswith('cudd') for r in complete)
        comparisons.append(dict(case=case['id'],completed_cells=len(complete),
            complete_methods=sorted({r['method'] for r in complete}),all_completed_agree=agreement,
            independently_cross_checked=independent,values=complete[0]['values'] if agreement else None))
    write(output/'COUNT-RESULTS.json',rows);write(output/'COUNT-COMPARISONS.json',comparisons)
    assert all(r['all_completed_agree'] for r in comparisons if r['completed_cells'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('run','miter','count'))
    parser.add_argument('--case');parser.add_argument('--method');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='run':run(args.output)
    else:worker(args)
