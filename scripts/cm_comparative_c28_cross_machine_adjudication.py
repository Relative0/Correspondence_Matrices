"""Adjudicate frozen C27 profitability across recorded machines without refitting."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_cross_machine_adjudication import adjudicate_cross_machine
from cmbench.comparative.gf2_support_aware_experiment import summarize


EXECUTIONS = (
    {
        "execution_id": "windows-primary",
        "physical_machine_id": "brian-local-machine",
        "environment": "Windows primary",
        "role": "primary fresh confirmation",
        "path": "docs/recognition/runs/c27-support-aware-fresh-windows-20260831-001",
    },
    {
        "execution_id": "docker-linux-001",
        "physical_machine_id": "brian-local-machine",
        "environment": "Docker Linux/amd64 repetition 1",
        "role": "same-host portability repetition",
        "path": (
            "docs/recognition/c27_linux_confirmation/c27-docker-linux-portability-001/"
            "results/c27-support-aware-fresh-linux-20260831-001"
        ),
    },
    {
        "execution_id": "docker-linux-002",
        "physical_machine_id": "brian-local-machine",
        "environment": "Docker Linux/amd64 repetition 2",
        "role": "same-host portability repetition",
        "path": (
            "docs/recognition/c27_linux_confirmation/c27-docker-linux-portability-002/"
            "results/c27-support-aware-fresh-linux-20260831-001"
        ),
    },
    {
        "execution_id": "docker-linux-003",
        "physical_machine_id": "brian-local-machine",
        "environment": "Docker Linux/amd64 repetition 3",
        "role": "same-host portability repetition",
        "path": (
            "docs/recognition/c27_linux_confirmation/c27-docker-linux-portability-003/"
            "results/c27-support-aware-fresh-linux-20260831-001"
        ),
    },
    {
        "execution_id": "runpod-cpu5c-001f",
        "physical_machine_id": "runpod-gukzs8ixi5gpdi",
        "environment": "RunPod Secure cpu5c Linux/amd64",
        "role": "physical second-machine confirmation",
        "path": (
            "docs/recognition/c27_linux_confirmation/runpod-c27-linux-execute-001f/"
            "evidence/run-output/c27-support-aware-fresh-linux-20260831-001"
        ),
    },
)
RUNPOD_FINAL = ROOT / (
    "docs/recognition/c27_linux_confirmation/"
    "RUNPOD_C27_RETRY_003_FINAL_VERIFICATION_20260901.json"
)
POLICY = ROOT / "docs/recognition/c27_support_aware_policy.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_rows(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: Any) -> None:
    path.write_bytes(json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False,
    ).encode("utf-8") + b"\n")


def load_execution(spec: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    run = ROOT / spec["path"]
    paths = {
        name: run / name for name in (
            "manifest.json", "run_spec.json", "results.json", "measurements.jsonl",
            "memory_measurements.jsonl", "functional_controls.json",
            "independent_verification.json",
        )
    }
    if any(not path.is_file() for path in paths.values()):
        raise ValueError(f"C28 missing frozen execution files: {spec['execution_id']}")
    manifest = load(paths["manifest.json"])
    run_spec = load(paths["run_spec.json"])
    result = load(paths["results.json"])
    verification = load(paths["independent_verification.json"])
    controls = load(paths["functional_controls.json"])
    rows = load_rows(paths["measurements.jsonl"])
    memory_rows = load_rows(paths["memory_measurements.jsonl"])
    recomputed = summarize(rows, memory_rows, controls)
    if (
        manifest.get("schema") != "crse-c27-run-manifest/v1"
        or run_spec.get("fresh_confirmation") is not True
        or run_spec.get("policy_refit") is not False
        or run_spec.get("production_promotion") is not False
        or run_spec.get("c27_policy_file_sha256") != sha256(POLICY)
        or result.get("status") != "complete"
        or result.get("measurement_batches") != 720
        or result.get("timed_queries") != 7560
        or result.get("memory_measurement_batches") != 24
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("claims", {}).get("support_policy_frozen_before_corpus") is not True
        or result.get("claims", {}).get("policy_refit") is not False
        or result.get("claims", {}).get("production_promotion") is not False
        or result.get("summary") != recomputed
        or len(rows) != 720
        or sum(len(row.get("query_records", [])) for row in rows) != 7560
        or any(row.get("exact_check_passed") is not True for row in rows)
        or len(memory_rows) != 24
        or any(row.get("exact_check_passed") is not True for row in memory_rows)
        or controls.get("all_passed") is not True
        or verification.get("status") != "verified"
        or verification.get("measurement_batches_checked") != 720
        or verification.get("timed_query_records_checked") != 7560
        or verification.get("memory_batches_checked") != 24
        or verification.get("summary_recomputed") is not True
        or verification.get("semantic_or_artifact_mismatches") != 0
        or verification.get("production_promotion") is not False
    ):
        raise ValueError(f"C28 rejected frozen execution: {spec['execution_id']}")
    record = {
        **{key: spec[key] for key in (
            "execution_id", "physical_machine_id", "environment", "role")},
        "rows": rows,
        "measurements_sha256": sha256(paths["measurements.jsonl"]),
        "independent_verification_sha256": sha256(paths["independent_verification.json"]),
    }
    evidence = {
        **{key: spec[key] for key in spec},
        "files": {name: {"sha256": sha256(path), "bytes": path.stat().st_size}
                  for name, path in paths.items()},
        "c27_policy_sha256": run_spec["c27_policy_sha256"],
        "c27_policy_file_sha256": run_spec["c27_policy_file_sha256"],
        "c22_policy_sha256": run_spec["c22_policy_sha256"],
        "c22_policy_file_sha256": run_spec["c22_policy_file_sha256"],
        "dataset_sha256": run_spec["dataset_sha256"],
        "measurement_batches": 720,
        "timed_queries": 7560,
        "memory_batches": 24,
        "semantic_or_artifact_mismatches": 0,
    }
    return record, evidence


def report(result: dict[str, Any]) -> str:
    lines = [
        "# Learning milestone C28: no-refit cross-machine profitability adjudication",
        "",
        "Status: implemented and independently verifiable; shadow and production promotion refused",
        "",
        "## Contract",
        "",
        "C28 reads five frozen C27 timing executions and does not rerun timings, train a model,",
        "or refit the transparent support rule. Windows plus three Docker repetitions share one",
        "physical machine; the RunPod cpu5c execution is the second physical machine.",
        "",
        "For each execution and query count, C28 exhaustively evaluates all 3,125 paired",
        "five-of-five round resamples. Admission requires the point estimate and the 95%",
        "paired-round lower bound to reach 1.00x aggregate speedup and 0.90x minimum-width",
        "speedup over resident direct screened execution on every recorded execution.",
        "",
        "## Cross-execution envelope",
        "",
        "| Queries | point aggregate floor | point width floor | bootstrap aggregate floor | bootstrap width floor | admissible |",
        "|---:|---:|---:|---:|---:|:---:|",
    ]
    for query_count, row in result["by_query_count"].items():
        point = row["cross_execution_point_floor"]
        lower = row["cross_execution_paired_bootstrap_95_lower_floor"]
        lines.append(
            f"| {query_count} | {point['aggregate_speedup_over_direct_screened']:.4f}x | "
            f"{point['minimum_width_speedup_over_direct_screened']:.4f}x | "
            f"{lower['aggregate_speedup_over_direct_screened']:.4f}x | "
            f"{lower['minimum_width_speedup_over_direct_screened']:.4f}x | "
            f"{'yes' if row['admissible'] else 'no'} |"
        )
    lines += [
        "",
        "## Decision",
        "",
        f"Point-admissible query counts: `{result['point_admissible_query_counts']}`.",
        f"Uncertainty-admissible query counts: `{result['uncertainty_admissible_query_counts']}`.",
        f"Uncertainty-safe monotonic suffix: `{result['uncertainty_monotonic_suffix_start']}`.",
        "",
        "The adjudicator refuses shadow promotion because no measured query-count suffix is",
        "safe under the frozen uncertainty rule. Any isolated positive remains research evidence",
        "rather than a general q>=k routing rule. Exact fallback remains the required behavior.",
        "Production promotion is false.",
        "",
        "The lower bounds are conditional diagnostics over five rounds per execution. They are",
        "not independent hardware confidence intervals, and the three Docker repetitions do not",
        "increase the physical-machine count beyond two.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    runpod_final = load(RUNPOD_FINAL)
    if (
        runpod_final.get("status") != "pass"
        or runpod_final.get("scientific_confirmation_complete") is not True
        or runpod_final.get("semantic_or_artifact_mismatches") != 0
        or runpod_final.get("owned_pod_absent_verified") is not True
    ):
        raise ValueError("C28 RunPod second-machine evidence is incomplete")

    records, evidence = [], []
    for spec in EXECUTIONS:
        record, frozen = load_execution(spec)
        records.append(record)
        evidence.append(frozen)
    policy_tuples = {
        (row["c27_policy_sha256"], row["c27_policy_file_sha256"],
         row["c22_policy_sha256"], row["c22_policy_file_sha256"], row["dataset_sha256"])
        for row in evidence
    }
    if len(policy_tuples) != 1:
        raise ValueError("C28 executions do not share one frozen policy and dataset")

    result = adjudicate_cross_machine(records)
    result.update({
        "status": "complete",
        "run_name": output.name,
        "fresh_c27_policy_unchanged": True,
        "input_policy_and_dataset_identity_count": len(policy_tuples),
        "measurement_batches_checked": 720 * len(records),
        "timed_queries_checked": 7560 * len(records),
        "memory_batches_checked": 24 * len(records),
        "semantic_or_artifact_mismatches": 0,
        "runpod_final_verification_sha256": sha256(RUNPOD_FINAL),
    })
    input_manifest = {
        "schema": "crse-c28-cross-machine-input-manifest/v1",
        "policy_refit": False,
        "training": False,
        "timings_rerun": False,
        "source_execution_count": len(evidence),
        "physical_machine_count": 2,
        "c27_policy_file_sha256": sha256(POLICY),
        "runpod_final_verification": str(RUNPOD_FINAL.relative_to(ROOT)).replace("\\", "/"),
        "runpod_final_verification_sha256": sha256(RUNPOD_FINAL),
        "executions": evidence,
    }
    write(output / "input_manifest.json", input_manifest)
    write(output / "results.json", result)
    (output / "report.md").write_text(report(result), encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "point_admissible_query_counts": result["point_admissible_query_counts"],
        "uncertainty_admissible_query_counts": result[
            "uncertainty_admissible_query_counts"],
        "uncertainty_monotonic_suffix_start": result[
            "uncertainty_monotonic_suffix_start"],
        "physical_machine_count": result["physical_machine_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
