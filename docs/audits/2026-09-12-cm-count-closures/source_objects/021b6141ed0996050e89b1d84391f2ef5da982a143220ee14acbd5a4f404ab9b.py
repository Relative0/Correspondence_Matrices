"""Frozen fresh-process component-count experiment with paired controls."""
import argparse
import gc
import json
from pathlib import Path
import subprocess
import sys
import time

from cmbench.backends.bucket_counts import CountPlanLimit
from cmbench.comparative.component_counts import count_components
from scripts.cm_application_studies import cases,write
from scripts.cm_next_count_campaign import runner

METHODS=('component_count','array_min_fill','cudd_dynamic')

def worker(args):
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    case=next(c for c in cases(args.kind) if c['id']==args.case)
    diagnostics=[];start=time.perf_counter_ns()
    try:
        if args.method=='component_count':
            def query(fixed):
                answer,stats=count_components(case,fixed);diagnostics.append(stats);return answer
            stats=dict(cache_scope='fresh per query, including warm replay')
        else:query,stats=runner(case,'projected',args.method)
        setup=time.perf_counter_ns()-start
        start=time.perf_counter_ns();values=[query(f) for f in case['contexts']];cold=time.perf_counter_ns()-start
        start=time.perf_counter_ns();warm=[query(f) for f in case['contexts']];warm_ns=time.perf_counter_ns()-start
        assert values==warm
        start=time.perf_counter_ns();del query;gc.collect();cleanup=time.perf_counter_ns()-start
        result=dict(status='complete',values=values,setup_ns=setup,query_ns=cold,cleanup_ns=cleanup,
                    total_ns=setup+cold+cleanup,warm_ns=warm_ns,stats=stats,diagnostics=diagnostics,
                    peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    except CountPlanLimit as exc:result=dict(status='refused',reason=str(exc),diagnostics=diagnostics)
    write(args.output,result)

def run(output):
    output.mkdir(parents=True,exist_ok=False);rows=[]
    for kind in ('feature','independent'):
        for case in cases(kind):
            for repeat in range(3):
                for method in (METHODS if repeat%2==0 else METHODS[::-1]):
                    key=f'{case["id"]}-{method}-{repeat}';path=output/(key+'.json')
                    with (output/(key+'.log')).open('xb') as stream:
                        try:
                            child=subprocess.run([sys.executable,'-B','-m','scripts.cm_component_count_study','worker',
                                '--kind',kind,'--case',case['id'],'--method',method,'--output',str(path)],
                                stdout=stream,stderr=subprocess.STDOUT,timeout=15)
                            row=json.loads(path.read_text()) if child.returncode==0 else dict(status='failed',exit_code=child.returncode)
                        except subprocess.TimeoutExpired:row=dict(status='timeout',limit_s=15)
                    rows.append(dict(kind=kind,case=case['id'],method=method,repeat=repeat,**row))
                    print(json.dumps(dict(case=case['id'],method=method,repeat=repeat,status=row['status'])),flush=True)
    write(output/'RESULTS.json',rows)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('worker','run'))
    parser.add_argument('--kind');parser.add_argument('--case');parser.add_argument('--method');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='worker':worker(args)
    else:run(args.output)
