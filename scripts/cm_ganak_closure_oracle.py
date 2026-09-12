"""Revisit exactly the eight unresolved contexts under a new 120-second cap."""
import argparse
import json
from pathlib import Path
from scripts.cm_application_oracle import install,count,write
from scripts.cm_d4_closure_oracle import cases,PRIOR

def run(output):
    output.mkdir(parents=True,exist_ok=False)
    old=json.loads((PRIOR/'attempt-006/evidence/oracle-extension/RESULTS.json').read_text())
    binary=install(output);results=[]
    for case in cases():
        indices=range(1,8) if case['id']=='additional-09' else [2]
        for i in indices:
            fixed=case['contexts'][i]
            prior=[r for r in old if r['case']==case['id'] and r['context']==fixed]
            assert len(prior)==1 and prior[0]['status']=='timeout'
            row=count(binary,case,fixed,output,case['id']+'-'+str(i),120)
            results.append(dict(context_index=i,**row))
            print(json.dumps(dict(case=case['id'],context_index=i,status=row['status'])),flush=True)
    write(output/'RESULTS.json',results)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
    run(parser.parse_args().output)
