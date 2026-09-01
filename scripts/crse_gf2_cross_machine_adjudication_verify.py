"""Independently verify a C28 no-refit cross-machine adjudication artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_cross_machine_adjudication import adjudicate_cross_machine
from cmbench.comparative.gf2_support_aware_experiment import summarize


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    manifest = load(run / "input_manifest.json")
    result = load(run / "results.json")
    if (
        manifest.get("schema") != "crse-c28-cross-machine-input-manifest/v1"
        or manifest.get("policy_refit") is not False
        or manifest.get("training") is not False
        or manifest.get("timings_rerun") is not False
        or manifest.get("source_execution_count") != 5
        or manifest.get("physical_machine_count") != 2
        or result.get("schema") != "crse-c28-cross-machine-profitability-adjudication/v1"
        or result.get("status") != "complete"
        or result.get("policy_refit") is not False
        or result.get("training") is not False
        or result.get("timings_rerun") is not False
        or result.get("fresh_c27_policy_unchanged") is not True
        or result.get("production_promotion") is not False
        or result.get("semantic_or_artifact_mismatches") != 0
    ):
        raise ValueError("C28 top-level contract mismatch")

    policy = ROOT / "docs/recognition/c27_support_aware_policy.json"
    runpod_final = ROOT / manifest["runpod_final_verification"]
    if (
        manifest.get("c27_policy_file_sha256") != sha256(policy)
        or manifest.get("runpod_final_verification_sha256") != sha256(runpod_final)
        or result.get("runpod_final_verification_sha256") != sha256(runpod_final)
        or load(runpod_final).get("status") != "pass"
    ):
        raise ValueError("C28 policy or second-machine fingerprint mismatch")

    records = []
    policy_identities = set()
    input_files_checked = 0
    for execution in manifest["executions"]:
        source = ROOT / execution["path"]
        for name, evidence in execution["files"].items():
            path = source / name
            if (
                not path.is_file()
                or path.stat().st_size != evidence["bytes"]
                or sha256(path) != evidence["sha256"]
            ):
                raise ValueError(
                    f"C28 frozen input mismatch: {execution['execution_id']}:{name}")
            input_files_checked += 1
        rows = load_rows(source / "measurements.jsonl")
        memory_rows = load_rows(source / "memory_measurements.jsonl")
        controls = load(source / "functional_controls.json")
        source_result = load(source / "results.json")
        verification = load(source / "independent_verification.json")
        if (
            len(rows) != 720
            or sum(len(row.get("query_records", [])) for row in rows) != 7560
            or any(row.get("exact_check_passed") is not True for row in rows)
            or len(memory_rows) != 24
            or any(row.get("exact_check_passed") is not True for row in memory_rows)
            or controls.get("all_passed") is not True
            or source_result.get("summary") != summarize(rows, memory_rows, controls)
            or source_result.get("semantic_or_artifact_mismatches") != 0
            or source_result.get("claims", {}).get("policy_refit") is not False
            or source_result.get("claims", {}).get("production_promotion") is not False
            or verification.get("status") != "verified"
            or verification.get("semantic_or_artifact_mismatches") != 0
        ):
            raise ValueError(f"C28 execution replay mismatch: {execution['execution_id']}")
        policy_identities.add((
            execution["c27_policy_sha256"], execution["c27_policy_file_sha256"],
            execution["c22_policy_sha256"], execution["c22_policy_file_sha256"],
            execution["dataset_sha256"],
        ))
        records.append({
            "execution_id": execution["execution_id"],
            "physical_machine_id": execution["physical_machine_id"],
            "environment": execution["environment"],
            "independent_verification_sha256": execution["files"][
                "independent_verification.json"]["sha256"],
            "measurements_sha256": execution["files"]["measurements.jsonl"]["sha256"],
            "rows": rows,
        })
    if len(policy_identities) != 1:
        raise ValueError("C28 source executions do not share one policy and dataset")

    recomputed = adjudicate_cross_machine(records)
    if any(result.get(key) != value for key, value in recomputed.items()):
        raise ValueError("C28 adjudication recomputation mismatch")
    if (
        result.get("execution_count") != 5
        or result.get("physical_machine_count") != 2
        or result.get("measurement_batches_checked") != 3600
        or result.get("timed_queries_checked") != 37800
        or result.get("memory_batches_checked") != 120
        or result.get("point_admissible_query_counts") != [8]
        or result.get("uncertainty_admissible_query_counts") != []
        or result.get("point_monotonic_suffix_start") is not None
        or result.get("uncertainty_monotonic_suffix_start") is not None
        or result.get("shadow_promotion") is not False
        or result.get("decision")
        != "refuse_shadow_promotion_no_uncertainty_safe_monotonic_suffix"
    ):
        raise ValueError("C28 frozen decision mismatch")

    verification = {
        "schema": "crse-c28-cross-machine-profitability-verification/v1",
        "status": "verified",
        "input_files_checked": input_files_checked,
        "execution_count": 5,
        "physical_machine_count": 2,
        "measurement_batches_checked": 3600,
        "timed_queries_checked": 37800,
        "memory_batches_checked": 120,
        "paired_round_resamples_per_execution_query": 3125,
        "execution_query_adjudications": 30,
        "paired_resample_statistics_recomputed": 93750,
        "point_admissible_query_counts": [8],
        "uncertainty_admissible_query_counts": [],
        "uncertainty_monotonic_suffix_start": None,
        "decision": result["decision"],
        "semantic_or_artifact_mismatches": 0,
        "policy_refit": False,
        "training": False,
        "timings_rerun": False,
        "shadow_promotion": False,
        "production_promotion": False,
        "input_manifest_sha256": sha256(run / "input_manifest.json"),
        "results_sha256": sha256(run / "results.json"),
        "report_sha256": sha256(run / "report.md"),
    }
    output = run / "independent_verification.json"
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(verification, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    print(json.dumps(verification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
