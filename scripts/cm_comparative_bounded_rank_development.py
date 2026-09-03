"""Run bounded GF(2)-rank complete-task development study."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from cmbench.comparative.gf2_bounded_rank_experiment import BoundedRankConfig, run
def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--run-id", required=True); p.add_argument("--output", type=Path, required=True); a=p.parse_args()
    result=run(BoundedRankConfig(run_id=a.run_id), a.output,
               ROOT/"docs/recognition/c16_linux_confirmation/c16_dataset.json", ROOT,
               progress=lambda n,t,c: print(f"bounded-rank {n}/{t} {c}", flush=True) if n==t or n%20==0 else None)
    print(json.dumps(result["summary"]["decision"], sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
