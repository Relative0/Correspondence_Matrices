"""Run complete-task ANF-rank pre-screen development adjudication."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_anf_full_screen_experiment import ANFFullScreenConfig, run

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(ANFFullScreenConfig(run_id=args.run_id), args.output,
                 ROOT / "docs/recognition/c16_linux_confirmation/c16_dataset.json", ROOT,
                 progress=lambda stage, current, total, case: print(
                     f"anf-full {stage} {current}/{total} {case}", flush=True)
                 if current == total or current % 20 == 0 else None)
    print(json.dumps(result["summary"]["decision"], sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
