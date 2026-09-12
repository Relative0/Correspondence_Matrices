"""Release entry point for the immutable count-closure verifier.

The captured verifier completes its checks but reuses ``expected`` for its
schedule set, accidentally returning that set in ``science_sha256``. Preserve
the sealed source and repair only this report field from the manifest bytes.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.verify_cm_count_closures import verify as verify_sealed

def verify(root=ROOT):
    result=verify_sealed(root)
    manifest=root/'docs/audits/2026-09-12-cm-count-closures/FINAL-MANIFEST.json'
    result['science_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
    return result

if __name__=='__main__':print(json.dumps(verify(),indent=2))
