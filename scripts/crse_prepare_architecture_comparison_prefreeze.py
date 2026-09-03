"""Write the dormant, fail-closed architecture-comparison prefreeze artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.comparison_prefreeze import build_prefreeze


NATIVE = ROOT / "docs/recognition/native_portfolio_baseline_closure_results.json"
C38 = ROOT / "docs/recognition/c38_linux_confirmation/C38_CROSS_MACHINE_ADJUDICATION_20260903.json"
FUNCTIONAL = ROOT / "docs/recognition/runs/architecture-refresh-harness-development-20260903-001"


def _load(path: Path) -> tuple[dict, str]:
    payload = path.read_bytes()
    return json.loads(payload), hashlib.sha256(payload).hexdigest()


def _write(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True,
                  allow_nan=False)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("prefreeze output escaped project")
    output.mkdir(parents=True, exist_ok=False)
    native, native_sha = _load(NATIVE)
    c38, c38_sha = _load(C38)
    plan, plan_sha = _load(FUNCTIONAL / "PLAN.json")
    result, result_sha = _load(FUNCTIONAL / "RESULT.json")
    checkpoint = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    prefreeze = build_prefreeze(
        source_checkpoint=checkpoint,
        native_closure=native,
        native_closure_sha256=native_sha,
        c38_adjudication=c38,
        c38_adjudication_sha256=c38_sha,
        functional_plan=plan,
        functional_plan_sha256=plan_sha,
        functional_result=result,
        functional_result_sha256=result_sha,
    )
    _write(output / "PREFREEZE.json", prefreeze)
    print(json.dumps({
        "status": prefreeze["status"],
        "source_checkpoint": checkpoint,
        "headroom": prefreeze["eligibility"]["current_q64_selector_oracle_headroom"],
        "fresh_corpus_selection": prefreeze["permissions"]["fresh_corpus_selection"],
        "runpod_authorization_request": prefreeze["permissions"]["runpod_authorization_request"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
