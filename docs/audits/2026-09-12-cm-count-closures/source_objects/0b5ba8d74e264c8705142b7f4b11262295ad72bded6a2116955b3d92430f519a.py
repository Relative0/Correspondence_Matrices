"""A separately frozen retry for seven counts still lacking a second counter."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
from scripts import cm_application_oracle as ganak
from scripts import cm_d4_closure_oracle as d4

def run(output):
    output.mkdir(parents=True,exist_ok=False)
    binary=d4.ROOT/'build/closure-d4';binary.parent.mkdir(exist_ok=True)
    with urllib.request.urlopen(d4.D4_URL,timeout=60) as response:data=response.read(d4.D4_BYTES+1)
    assert len(data)==d4.D4_BYTES and hashlib.sha256(data).hexdigest()==d4.D4_SHA
    with binary.open('xb') as stream:stream.write(data)
    binary.chmod(0o755)
    rows=[];feature,qif=d4.cases()
    for index in (0,1,2,4,5,7):
        row=d4.count(binary,qif,qif['contexts'][index],output,f'd4-qif-{index}',240)
        rows.append(dict(counter='d4',context_index=index,**row))
        print(json.dumps(dict(counter='d4',context_index=index,status=row['status'])),flush=True)
    ganak_binary=ganak.install(output)
    # This process changes only the declared address-space cap, not old source
    # bytes, the exact integer invocation, the case or the conditioning request.
    ganak.limits=d4.limits
    row=ganak.count(ganak_binary,feature,feature['contexts'][7],output,'ganak-decision-7',120)
    rows.append(dict(counter='ganak',context_index=7,address_space_limit_bytes=6<<30,**row))
    d4.write(output/'RESULTS.json',rows)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
