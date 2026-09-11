"""Independent projected-model enumeration for the three low-count synthesis cases.

Exploratory selection follows their observed Ganak counts, not timing evidence.
Two SAT solvers block selected assignments, never full witness assignments.
"""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
from scripts.cm_application_oracle import write, exhaustive
from scripts.cm_application_studies import cases, read


def enumerate_count(case, fixed, solver_name, cap=512):
    from pysat.solvers import Solver
    selected=case['projected'];clauses=case['clauses']
    with Solver(name=solver_name,bootstrap_with=clauses) as solver:
        # Declare every variable, including selected axes absent from clauses.
        for variable in range(1,case['n']+1):solver.add_clause([variable,-variable])
        for name,value in fixed.items():solver.add_clause([(int(name[1:])+1)*(1 if value else -1)])
        count=0
        while solver.solve():
            if count==cap:return dict(status='refused',reason='projected model enumeration cap reached',cap=cap)
            count+=1
            if not selected:return dict(status='complete',value=1)
            model={abs(v):v>0 for v in solver.get_model()}
            if any(v+1 not in model for v in selected):raise ValueError('solver omitted selected variable')
            solver.add_clause([-(v+1) if model[v+1] else v+1 for v in selected])
        return dict(status='complete',value=count)


def worker(args):
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    if args.kind=='control':case=read('ORACLE-PROTOCOL.json')['controls'][int(args.case)]
    else:case=next(c for c in cases('independent') if c['id']==args.case)
    fixed=case['contexts'][args.context]
    row=enumerate_count(case,fixed,args.solver)
    if args.kind=='control':row['expected']=exhaustive(case,fixed)
    write(args.output,dict(case=case['id'],context=fixed,solver=args.solver,**row))


def run(output):
    output.mkdir(parents=True,exist_ok=False);controls=[];rows=[]
    selected=[c for c in cases('independent') if c['id'] in ('independent-07','independent-08','independent-09')]
    assert len(selected)==3
    for kind,cohort in [('control',read('ORACLE-PROTOCOL.json')['controls']),('synthesis',selected)]:
        for index,case in enumerate(cohort):
            for context in range(len(case['contexts'])):
                for solver in ('g3','m22'):
                    key=f'{kind}-{index}-{context}-{solver}';path=output/(key+'.json')
                    with (output/(key+'.log')).open('xb') as log:
                        try:
                            child=subprocess.run([sys.executable,'-B','-m','scripts.cm_synthesis_projected_enumeration','worker',
                              '--kind',kind,'--case',str(index) if kind=='control' else case['id'],'--context',str(context),
                              '--solver',solver,'--output',str(path)],stdout=log,stderr=subprocess.STDOUT,timeout=15)
                            row=json.loads(path.read_text()) if child.returncode==0 else dict(status='failed',exit_code=child.returncode)
                        except subprocess.TimeoutExpired:row=dict(status='timeout',limit_s=15)
                    row.update(case=case['id'],context=case['contexts'][context],solver=solver)
                    (controls if kind=='control' else rows).append(row)
                    print(json.dumps(dict(case=case['id'],context=context,solver=solver,status=row['status'])),flush=True)
        write(output/('CONTROLS.json' if kind=='control' else 'RESULTS.json'),controls if kind=='control' else rows)
        if kind=='control':assert len(controls)==66 and all(r['status']=='complete' and r['value']==r['expected'] for r in controls)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('run','worker'));parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--kind');parser.add_argument('--case');parser.add_argument('--context',type=int);parser.add_argument('--solver')
    args=parser.parse_args()
    run(args.output) if args.action=='run' else worker(args)
