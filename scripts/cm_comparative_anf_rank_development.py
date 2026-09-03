"""Run the development-only ANF-basis GF(2)-rank study."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_anf_rank_experiment import ANFRankConfig, run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=float, default=900.0)
    args = parser.parse_args()

    def progress(stage: str, current: int, total: int, case_id: str) -> None:
        interval = 40 if stage != "exhaustive" else 8192
        if current == total or current % interval == 0:
            print(f"anf-rank {stage} {current}/{total} {case_id}", flush=True)

    result = run(
        ANFRankConfig(run_id=args.run_id, max_seconds=args.max_seconds), args.output,
        ROOT / "docs/recognition/c16_linux_confirmation/c16_dataset.json", ROOT,
        progress=progress)
    print(json.dumps(result["summary"]["decision"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
