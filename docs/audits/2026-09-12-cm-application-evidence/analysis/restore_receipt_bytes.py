"""Restore four historical receipts to their independently recorded exact bytes."""
import hashlib
import json
from pathlib import Path
import sys

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2];CHECKOUT=ROOT/'build/cm-applications'
sys.path.insert(0,str(CHECKOUT))
from scripts.cm_research_publication import scan_bytes

def read(name):return json.loads((CHECKOUT/name).read_text(encoding='utf-8'))
def sha(data):return hashlib.sha256(data).hexdigest()
base='docs/recognition/'
specs=[
 (base+'c38_linux_confirmation/runpod-c38-linux-execute-001/RUN.json',base+'c38_linux_confirmation/C38_INITIAL_NO_CREATE_RECONCILIATION_20260903.json',['initial_run_sha256']),
 (base+'architecture_comparison_execution_20260903/runpod-architecture-comparison-execute-001/RUN.json',base+'architecture_comparison_execution_20260903/ATTEMPT_001_STATUS.json',['run_record_sha256']),
 (base+'architecture_query_ladder_followup_execution_20260903/runpod-architecture-query-ladder-execute-001/RUN.json',base+'architecture_query_ladder_followup_execution_20260903/ATTEMPT_001_STATUS.json',['evidence','run_sha256']),
 (base+'architecture_query_ladder_followup_retry_002_execution_20260904/runpod-architecture-query-ladder-execute-002/RUN.json',base+'architecture_query_ladder_followup_retry_002_execution_20260904/ANALYSIS.json',['inputs','controller_sha256']),
]
pending=[];records=[]
for name,binding,keys in specs:
 expected=read(binding)
 for key in keys:expected=expected[key]
 original=(ROOT/name).read_bytes();before=(CHECKOUT/name).read_bytes()
 assert sha(original)==expected,name
 assert before==original.replace(b'\r\n',b'\n') and before!=original,name
 assert json.loads(before)==json.loads(original)
 scan_bytes(name,original)
 pending.append((name,original,before))
 records.append(dict(path=name,restored_sha256=expected,restored_bytes=len(original),
  before_sha256=sha(before),before_bytes=len(before),binding=binding,binding_selector=keys,
  binding_sha256=sha((CHECKOUT/binding).read_bytes()),json_values_changed=False))
destination=AUDIT/'receipt_byte_variants';destination.mkdir(exist_ok=False)
for name,original,before in pending:
 for data in (original,before):
  path=destination/(sha(data)+'.json')
  if not path.exists():path.write_bytes(data)
 (CHECKOUT/name).write_bytes(original)
attributes=CHECKOUT/'.gitattributes'
text=attributes.read_text(encoding='utf-8').rstrip()+'\n\n# Preserve exact recovered historical receipt hashes across platforms.\n'
text+=''.join('/'+name+' -text whitespace=cr-at-eol\n' for name,_,_ in pending)
text+='\n# Exact sealed application evidence, including retained source objects.\n/docs/audits/2026-09-12-cm-application-evidence/** -text whitespace=cr-at-eol\n'
attributes.write_text(text,encoding='utf-8',newline='\n')
with (AUDIT/'RECEIPT-BYTE-RESTORATION.json').open('x') as f:json.dump(dict(files=records,expected_hashes_rewritten=False,scope='Four exact receipt byte restorations; JSON values unchanged. Both original and normalized variants retained in this new audit.'),f,indent=2);f.write('\n')
print(json.dumps(dict(restored_files=len(records),semantic_changes=0)))
