"""Run the bounded local C32 baseline-serving shadow experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_prepared_shadow_experiment import (
    C32Config,
    run_experiment,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blocks", type=int, default=16)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    args = parser.parse_args()
    result = run_experiment(
        C32Config(
            run_id=args.output.name,
            blocks=args.blocks,
            max_seconds=args.max_seconds,
        ),
        output=args.output.resolve(),
        dataset_path=ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset.json",
        dataset_verification_path=(
            ROOT / "docs/recognition/c27_yosys_fresh_gf2_dataset_verification.json"),
        c27_policy_path=ROOT / "docs/recognition/c27_support_aware_policy.json",
        c22_policy_path=ROOT / "docs/recognition/c22_source_portfolio_policy.json",
        c31_final_path=(
            ROOT / "docs/recognition/c31_linux_confirmation/"
            "RUNPOD_C31_FINAL_VERIFICATION_20260901.json"),
        c31_adjudication_path=(
            ROOT / "docs/recognition/c31_linux_confirmation/"
            "C31_CROSS_MACHINE_ADJUDICATION_20260901.json"),
        root=ROOT,
    )
    print(json.dumps({
        "status": result["status"],
        "run": str(args.output),
        "served_exact_queries": result["summary"]["served_exact_queries"],
        "shadow_candidate_observations": result["summary"][
            "shadow_candidate_observations"],
        "semantic_or_artifact_mismatches": result[
            "semantic_or_artifact_mismatches"],
        "shadow_review_gate": result["summary"]["shadow_review_gate"],
        "shadow_promotion": False,
        "production_promotion": False,
    }, sort_keys=True))
    return int(result["status"] != "complete")


if __name__ == "__main__":
    raise SystemExit(main())
