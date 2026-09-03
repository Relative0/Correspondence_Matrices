"""Run the bounded local C33 asynchronous prepared-policy shadow experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_async_shadow_experiment import (
    C33Config,
    run_experiment,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blocks", type=int, default=16)
    parser.add_argument("--max-seconds", type=float, default=600.0)
    args = parser.parse_args()
    result = run_experiment(
        C33Config(
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
        c32_summary_path=(
            ROOT / "docs/recognition/"
            "learning_milestone_c32_prepared_policy_shadow_results.json"),
        root=ROOT,
    )
    summary = result["summary"]
    print(json.dumps({
        "status": result["status"],
        "run": str(args.output),
        "served_exact_queries": summary["served_exact_queries"],
        "candidate_observations": summary["candidate_observations"],
        "semantic_or_artifact_mismatches": summary[
            "semantic_or_artifact_mismatches"],
        "c33_local_gate": summary["c33_local_gate"],
        "async_full_serving_ratio": summary["aggregate_ratios"][
            "async_full_serving_ratio_over_disabled"],
        "shadow_promotion": False,
        "production_promotion": False,
    }, sort_keys=True))
    return int(result["status"] != "complete")


if __name__ == "__main__":
    raise SystemExit(main())
