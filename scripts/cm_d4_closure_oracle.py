"""Independent projected-count check using the pinned d4 competition binary.

A forced fresh selected variable preserves counts and avoids d4 interpreting an
empty projection as full model counting. No weights or approximate modes are used.
"""
import argparse
import hashlib
from itertools import product
import json
from pathlib import Path
import re
import subprocess
import time
import urllib.request

from scripts.restore_cm_application_fixtures import D4_URL, D4_SHA, D4_BYTES

ROOT=Path(__file__).resolve().parents[1]
PRIOR=ROOT/'docs/audits/2026-09-12-cm-application-evidence'

def write(path,value):
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')

def encode(case,fixed):
    n=case['n']
    assert type(n) is int and n>=0
    selected=case['projected']
    assert len(set(selected))==len(selected) and all(type(v) is int and 0<=v<n for v in selected)
    clauses=[list(c) for c in case['clauses']]
    assert all(type(v) is int and 1<=abs(v)<=n for c in clauses for v in c)
    for name,value in fixed.items():
        assert re.fullmatch(r'x[0-9]+',name) and type(value) in (int,bool) and value in (0,1)
        var=int(name[1:])+1
        assert 1<=var<=n
        clauses.append([var if value else -var])
    clauses.append([n+1])
    lines=[f'p cnf {n+1} {len(clauses)}','c p show '+' '.join(str(v+1) for v in [*selected,n])+' 0']
    lines+=[' '.join(map(str,c))+' 0' for c in clauses]
    return ('\n'.join(lines)+'\n').encode()

def limits():
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(6<<30,6<<30))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))

def exact_control(case,fixed):
    answers=set()
    for row in product((0,1),repeat=case['n']):
        if any(row[int(k[1:])]!=v for k,v in fixed.items()):continue
        if all(any(row[abs(v)-1]==(v>0) for v in c) for c in case['clauses']):
            answers.add(tuple(row[v] for v in case['projected']))
    return len(answers)

def count(binary,case,fixed,out,key,timeout):
    data=encode(case,fixed);path=out/(key+'.cnf');path.write_bytes(data)
    row=dict(case=case['id'],context=fixed,input_sha256=hashlib.sha256(data).hexdigest(),
             binary_sha256=D4_SHA,limit_s=timeout,address_space_limit_bytes=6<<30,
             fresh_forced_selected_axis=True,command=[str(binary),str(path)])
    start=time.perf_counter_ns()
    try:
        child=subprocess.run(row['command'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,preexec_fn=limits)
        log=child.stdout;matches=re.findall(rb'^c s exact (?:arb|quadruple) int ([0-9]+)\s*$',log,re.M)
        row.update(status='complete' if child.returncode==0 and len(matches)==1 and b'Run the projected model counter' in log else 'failed',exit_code=child.returncode)
        if row['status']=='complete':row['value']=int(matches[0])
    except subprocess.TimeoutExpired as exc:
        log=exc.stdout or b'';row['status']='timeout'
    row['elapsed_ns']=time.perf_counter_ns()-start
    (out/(key+'.log')).write_bytes(log)
    write(out/(key+'.json'),row)
    return row

def cases():
    feature=json.loads((PRIOR/'FEATURE-CASES.json').read_text())
    independent=json.loads((ROOT/'docs/audits/2026-09-12-cm-evidence-frontiers/INDEPENDENT-CASES.json').read_text())
    return [next(c for c in feature if c['id']=='additional-09'),next(c for c in independent if c['id']=='independent-03')]

def run(output):
    output.mkdir(parents=True,exist_ok=False)
    binary=ROOT/'build/closure-d4';binary.parent.mkdir(exist_ok=True)
    with urllib.request.urlopen(D4_URL,timeout=60) as response:data=response.read(D4_BYTES+1)
    assert len(data)==D4_BYTES and hashlib.sha256(data).hexdigest()==D4_SHA
    with binary.open('xb') as stream:stream.write(data)
    binary.chmod(0o755)
    write(output/'INSTALL.json',dict(url=D4_URL,bytes=D4_BYTES,sha256=D4_SHA))
    controls=json.loads((PRIOR/'ORACLE-PROTOCOL.json').read_text())['controls']
    rows=[]
    for i,case in enumerate(controls):
        for j,fixed in enumerate(case['contexts']):
            row=count(binary,case,fixed,output,f'control-{i}-{j}',15)
            row['expected']=exact_control(case,fixed);rows.append(row)
    # Large integers and empty projection with multiple hidden witnesses.
    for i,(case,expected) in enumerate([
        (dict(id='wide-free',n=128,projected=list(range(128)),clauses=[]),1<<128),
        (dict(id='empty-multiple-witnesses',n=3,projected=[],clauses=[[1,2]]),1),
        (dict(id='empty-unsat',n=2,projected=[],clauses=[[1],[-1]]),0)]):
        row=count(binary,case,{},output,f'edge-{i}',15);row['expected']=expected;rows.append(row)
    write(output/'CONTROLS.json',rows)
    assert all(r['status']=='complete' and r['value']==r['expected'] for r in rows),'d4 semantic controls failed'
    results=[]
    for case in cases():
        for i,fixed in enumerate(case['contexts']):
            row=count(binary,case,fixed,output,case['id']+'-'+str(i),90)
            results.append(dict(context_index=i,**row))
            print(json.dumps(dict(case=case['id'],context_index=i,status=row['status'])),flush=True)
    write(output/'RESULTS.json',results)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
    run(parser.parse_args().output)
