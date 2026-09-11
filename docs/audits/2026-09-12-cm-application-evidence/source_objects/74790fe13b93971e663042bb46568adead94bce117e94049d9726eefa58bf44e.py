"""Prospectively bounded exact-count follow-up; not a timing comparison.

Five fixed unresolved cases get one 60-second unconditional attempt each.
Only a completed unconditional count opens that case's seven fixed conditional
queries, at 30 seconds each. Every unrun/failed query is retained explicitly.
"""
import argparse
from pathlib import Path
import json
from scripts.cm_application_oracle import install, count, write
from scripts.cm_application_studies import cases


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    selected = [c for c in cases('feature') if c['id']=='additional-09']
    selected += [c for c in cases('independent') if c['id'] not in ('independent-01','independent-02')]
    assert len(selected)==5
    binary=install(output);rows=[]
    for case in selected:
        assert case['contexts'][0]=={}
        gate=False
        for i,context in enumerate(case['contexts']):
            if i and not gate:
                row=dict(case=case['id'],context=context,status='not_scheduled',
                         reason='predeclared gate: unconditional exact count did not complete')
            else:
                row=count(binary,case,context,output,case['id']+'-'+str(i),60 if i==0 else 30)
                if i==0:gate=row['status']=='complete'
            rows.append(row)
            print(json.dumps(dict(case=case['id'],context_index=i,status=row['status'])),flush=True)
    write(output/'RESULTS.json',rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
