"""Independent SAT checks of frozen SXFM/projected-CNF equivalence miters."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'docs/audits/2026-09-12-cm-evidence-frontiers/SXFM-MITERS.json'

def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case');parser.add_argument('--solver')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    cases=json.loads(INPUT.read_text())
    if args.case:
        resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
        from pysat.solvers import Solver
        case=next(c for c in cases if c['id']==args.case)
        start=time.perf_counter_ns()
        with Solver(name=args.solver,bootstrap_with=case['clauses']) as solver:
            sat=solver.solve();model=solver.get_model() if sat else None
        write(args.output,dict(status='complete',case=args.case,solver=args.solver,
            satisfiable=sat,model=model,elapsed_ns=time.perf_counter_ns()-start))
        return
    args.output.mkdir(parents=True,exist_ok=False);rows=[]
    for case in cases:
        for solver in ('g3','m22'):
            destination=args.output/(case['id']+'-'+solver+'.json')
            with destination.with_suffix('.log').open('xb') as stream:
                try:
                    result=subprocess.run([sys.executable,'-B','-m','scripts.cm_frontier_mapping_verify',
                        '--case',case['id'],'--solver',solver,'--output',str(destination)],
                        stdout=stream,stderr=subprocess.STDOUT,timeout=30)
                    row=json.loads(destination.read_text()) if result.returncode==0 else dict(status='failed',exit_code=result.returncode)
                except subprocess.TimeoutExpired:row=dict(status='timeout',limit_s=30)
            rows.append(dict(case=case['id'],solver=solver,**{k:v for k,v in row.items() if k not in ('case','solver')}))
    write(args.output/'RESULTS.json',rows)

if __name__=='__main__':main()
