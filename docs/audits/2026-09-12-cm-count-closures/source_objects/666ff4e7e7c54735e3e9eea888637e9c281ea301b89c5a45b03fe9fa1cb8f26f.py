"""Final bounded independent checks, selected after the component study."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
from scripts import cm_d4_closure_oracle as d4
from scripts import cm_application_oracle as ganak

def run(output):
    output.mkdir(parents=True,exist_ok=False)
    binary=d4.ROOT/'build/closure-d4';binary.parent.mkdir(exist_ok=True)
    with urllib.request.urlopen(d4.D4_URL,timeout=60) as response:data=response.read(d4.D4_BYTES+1)
    assert len(data)==d4.D4_BYTES and hashlib.sha256(data).hexdigest()==d4.D4_SHA
    with binary.open('xb') as stream:stream.write(data)
    binary.chmod(0o755)
    cases=json.loads((d4.PRIOR/'FEATURE-CASES.json').read_text())
    feature=next(c for c in cases if c['id']=='additional-07');rows=[]
    for index,fixed in enumerate(feature['contexts']):
        row=d4.count(binary,feature,fixed,output,f'd4-feature-07-{index}',90)
        rows.append(dict(counter='d4',context_index=index,**row))
        print(json.dumps(dict(case=feature['id'],context_index=index,status=row['status'])),flush=True)
    decision=next(c for c in cases if c['id']=='additional-09')
    ganak_binary=ganak.install(output);ganak.limits=d4.limits
    row=ganak.count(ganak_binary,decision,decision['contexts'][7],output,'ganak-decision-7',240)
    rows.append(dict(counter='ganak',context_index=7,address_space_limit_bytes=6<<30,**row))
    d4.write(output/'RESULTS.json',rows)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
