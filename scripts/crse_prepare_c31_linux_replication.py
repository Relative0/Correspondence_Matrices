"""Freeze the unchanged C30 prepared-policy second-machine replication package."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.gf2_prepared_policy_adjudication import (
    AGGREGATE_PAIRED_LOWER_FLOOR,
    AGGREGATE_POINT_FLOOR,
    BLOCKS,
    CONFIDENCE_LEVEL,
    MINIMUM_WIDTH_PAIRED_LOWER_FLOOR,
    MINIMUM_WIDTH_POINT_FLOOR,
    median_lower_order_statistic_rank,
)


OUT = ROOT / "docs/recognition/c31_linux_confirmation"
MANIFEST = OUT / "c31_linux_upload_manifest.json"
PROTOCOL = OUT / "C31_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_09_01.md"
CONTRACT = ROOT / "docs/recognition/c31_prepared_policy_replication_contract.json"
C27_MANIFEST = ROOT / "docs/recognition/c27_linux_confirmation/c27_linux_upload_manifest.json"
C30_RUN = ROOT / "docs/recognition/runs/c30-prepared-policy-windows-20260901-001"
C30_SUMMARY = ROOT / "docs/recognition/learning_milestone_c30_prepared_policy_context_results.json"
IMAGE = "python:3.13.15-slim-bookworm@sha256:b6bd71b0dd3811ddbcbc523ec2965fd1e1bcfdf7a20ab24679273d3bee726129"
NUMPY = "numpy==2.3.2 --hash=sha256:938065908d1d869c7d75d8ec45f735a034771c6ea07088867f713d1cd3bbbe4f"
RUN_NAME = "c31-prepared-policy-linux-20260901-001"

EXCLUDE_C27_TARGETS = {
    "scripts/cm_comparative_c27_support_aware.py",
    "scripts/crse_gf2_support_aware_verify.py",
}
ADDITIONAL_PROJECT_FILES = (
    "cmbench/comparative/schedule.py",
    "cmbench/comparative/gf2_prepared_policy_experiment.py",
    "cmbench/comparative/gf2_prepared_policy_adjudication.py",
    "cmbench/recognition/gf2_prepared_support_context.py",
    "scripts/cm_comparative_c30_prepared_policy.py",
    "scripts/crse_gf2_prepared_policy_verify.py",
    "scripts/crse_c31_cross_machine_adjudicate.py",
    "docs/recognition/runs/c29-variance-localization-windows-20260901-002/results.json",
    "docs/recognition/runs/c29-variance-localization-windows-20260901-002/independent_verification.json",
    "docs/recognition/c31_prepared_policy_replication_contract.json",
)
COMMANDS = (
    [
        "python", "-B", "scripts/cm_comparative_c30_prepared_policy.py",
        "--output", f"run-output/{RUN_NAME}", "--blocks", "16",
        "--max-seconds", "600",
    ],
    [
        "python", "-B", "scripts/crse_gf2_prepared_policy_verify.py",
        f"run-output/{RUN_NAME}",
    ],
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_identity(path: Path) -> dict[str, int | str]:
    return {"bytes": path.stat().st_size, "sha256": sha256(path)}


def main() -> int:
    if any(path.exists() for path in (MANIFEST, PROTOCOL, CONTRACT)):
        raise SystemExit("refusing to overwrite frozen C31 package artifacts")
    OUT.mkdir(parents=True, exist_ok=True)
    local_files = {}
    for name in (
        "functional_controls.json",
        "independent_verification.json",
        "manifest.json",
        "measurements.jsonl",
        "prepared_context.json",
        "results.json",
        "run_spec.json",
    ):
        path = C30_RUN / name
        local_files[name] = file_identity(path)
    local_result = json.loads((C30_RUN / "results.json").read_text(encoding="utf-8"))
    local_verification = json.loads(
        (C30_RUN / "independent_verification.json").read_text(encoding="utf-8"))
    if (
        local_result.get("status") != "complete"
        or local_result.get("semantic_or_artifact_mismatches") != 0
        or local_verification.get("status") != "verified"
        or local_verification.get("results_sha256") != sha256(C30_RUN / "results.json")
        or local_result.get("summary", {}).get("measurement_batches") != 128
        or local_result.get("summary", {}).get("timed_queries") != 1024
    ):
        raise ValueError("C31 cannot freeze unverified local C30 evidence")
    rank, achieved_confidence = median_lower_order_statistic_rank()
    contract = {
        "schema": "crse-c31-prepared-policy-replication-contract/v1",
        "created_date": "2026-09-01",
        "source_milestone": "C30",
        "source_milestone_summary_sha256": sha256(C30_SUMMARY),
        "schedule": {
            "seed": 20260901,
            "blocks": BLOCKS,
            "widths": [3, 4, 5, 6],
            "methods": ["resident_direct_screened", "support_aware_c30_prepared"],
            "query_count": 8,
            "measurement_batches": 128,
            "paired_batches": 64,
            "timed_queries": 1024,
            "max_partitions": 64,
            "materialize_budget": 4,
            "unchanged_from_c30": True,
        },
        "paired_block_lower_bound": {
            "method": "exact_distribution_free_one_sided_binomial_order_statistic",
            "sampling_unit": "prespecified_counterbalanced_block",
            "sample_count": BLOCKS,
            "requested_confidence_level": CONFIDENCE_LEVEL,
            "achieved_confidence_level": achieved_confidence,
            "order_statistic_rank_one_based": rank,
            "undercoverage_numerator": (2**BLOCKS) - round(achieved_confidence * 2**BLOCKS),
            "undercoverage_denominator": 2**BLOCKS,
        },
        "thresholds": {
            "aggregate_point_minimum": AGGREGATE_POINT_FLOOR,
            "minimum_width_point_minimum": MINIMUM_WIDTH_POINT_FLOOR,
            "aggregate_paired_median_lower_minimum": AGGREGATE_PAIRED_LOWER_FLOOR,
            "minimum_width_paired_median_lower_minimum": MINIMUM_WIDTH_PAIRED_LOWER_FLOOR,
        },
        "cross_machine_requirement": {
            "execution_count_minimum": 2,
            "physical_machine_count_minimum": 2,
            "same_host_container_counts_as_second_machine": False,
            "all_execution_point_and_paired_lower_gates_required": True,
        },
        "local_execution": {
            "execution_id": "c30-windows-20260901-001",
            "physical_machine_id": "windows-desktop-qd8tm7n-c30",
            "run": "docs/recognition/runs/c30-prepared-policy-windows-20260901-001",
            "files": local_files,
        },
        "requirements": {
            "semantic_or_artifact_mismatches": 0,
            "functional_controls_replayed": 6,
            "verified_context_records_replayed": 512,
            "preparation_charge_conserved": True,
            "policy_refit": False,
            "training": False,
            "method_substitution": False,
            "production_write": False,
            "automatic_shadow_promotion": False,
            "production_promotion": False,
        },
        "decision_scope": (
            "Passing makes the frozen candidate eligible for a separate shadow review; "
            "it does not authorize shadow or production promotion."
        ),
    }
    CONTRACT.write_bytes(
        json.dumps(contract, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")

    source_manifest = json.loads(C27_MANIFEST.read_text(encoding="utf-8"))
    if source_manifest.get("schema") != "crse-c27-linux-replication-upload-manifest/v1":
        raise ValueError("C27 runtime package base changed")
    sources: dict[str, tuple[str, str]] = {}
    for row in source_manifest["files"]:
        if row["target"] not in EXCLUDE_C27_TARGETS:
            sources[row["target"]] = (row["source"], row["kind"])
    for target in ADDITIONAL_PROJECT_FILES:
        kind = (
            "scientific_contract" if target == str(CONTRACT.relative_to(ROOT)).replace("\\", "/")
            else "frozen_prior_evidence" if "/runs/c29-" in target
            else "project"
        )
        if target in sources:
            raise ValueError(f"duplicate C31 package target: {target}")
        sources[target] = (target, kind)

    rows = []
    for target in sorted(sources):
        source, kind = sources[target]
        path = ROOT / source
        rows.append({
            "source": source,
            "target": target,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "kind": kind,
        })
    if len({row["target"] for row in rows}) != len(rows):
        raise ValueError("duplicate C31 package target")
    total_bytes = sum(row["bytes"] for row in rows)
    protocol = f"""# C31 unchanged prepared-policy second-machine replication protocol

Upload only the frozen **{len(rows)}-file, {total_bytes:,}-byte package** in
`c31_linux_upload_manifest.json`. It contains the exact C30 implementation, the sealed
C27/C22/C19 policies, the verified 48-case C27 dataset, the two hash-bound C29 inputs,
the prospective C31 adjudication contract, the independent verifier, and bounded
pure-Python runtime dependencies. It excludes credentials, local C30 timing files,
generated media, source checkouts, compiled BDD backends, and unrelated worktree files.

Run the unchanged C30 seed, 16 counterbalanced blocks, n=3/4/5/6 width schedule, q8
case sequence, 64-partition bound, four-artifact materialization budget, prepared-policy
lifecycle charging, and six fail-closed controls. The required output is 128 measurement
batches, 64 paired batches, 1,024 timed exact GF(2) queries, 512 independently replayed
verified contexts, zero semantic or artifact mismatches, and a conserved one-time
preparation charge. Then run the packaged independent verifier on the same pod.

After bounded retrieval, apply the already frozen C31 adjudicator to the original C30
Windows evidence and this second physical-machine execution. Every execution must clear
the 1.00x aggregate and 0.90x minimum-width point floors. It must also clear the same
floors using the exact one-sided {achieved_confidence:.4%} distribution-free median lower
bound: the fifth ordered value from the 16 prespecified paired blocks. A failed timing
gate is a valid result and must be retained without refitting, method substitution, or a
changed rerun. Passing only makes the candidate eligible for a separate shadow review;
it does not authorize shadow or production promotion.

No upload or paid RunPod action is authorized by this freeze. A later exact authorization
should be limited to one Secure CPU pod with no replacement, the pinned Python 3.13.15
image, 2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, zero persistent or network
volumes, one HTTPS port, a $0.25/hour rate ceiling, and a $0.05 controller cost ceiling.
Retrieve at most 16 MiB, delete the owned pod within ten minutes, and reconcile both
inventories for twelve minutes. No training or production write is permitted.
"""
    PROTOCOL.write_text(protocol, encoding="utf-8", newline="\n")
    manifest = {
        "schema": "crse-c31-linux-replication-upload-manifest/v1",
        "authorization_status": "upload_not_authorized_exact_approval_pending",
        "created_date": "2026-09-01",
        "file_count": len(rows),
        "bytes": total_bytes,
        "files": rows,
        "commands": list(COMMANDS),
        "run_name": RUN_NAME,
        "protocol_sha256": sha256(PROTOCOL),
        "replication_contract_sha256": sha256(CONTRACT),
        "runtime": {
            "architecture": "amd64",
            "image": IMAGE,
            "python": "3.13.15",
            "numpy": "2.3.2",
            "numpy_requirement": NUMPY,
            "dd": "0.6.0 pure-Python autoref subset vendored from the approved local environment",
            "astutils": "0.0.6 vendored dependency subset",
            "ply": "3.10 vendored dependency subset",
        },
        "network_during_setup": "pinned hash-checked NumPy wheel from PyPI only",
        "network_during_workload": False,
        "result_cap_bytes": 16 << 20,
        "scientific_contract": {
            "cases": 48,
            "blocks": BLOCKS,
            "query_count": 8,
            "measurement_batches": 128,
            "paired_batches": 64,
            "timed_queries": 1024,
            "verified_context_records": 512,
            "functional_controls": 6,
            "unchanged_c30_schedule": True,
            "lifecycle_preparation_fully_charged": True,
            "policy_refit": False,
            "training": False,
            "production_write": False,
            "shadow_promotion": False,
            "production_promotion": False,
        },
        "excluded": [
            ".env*", ".git/", "tokens", "credentials", "local C30 timings",
            "generated video/media", "unrelated dirty work", "compiled dd backends",
        ],
    }
    MANIFEST.write_bytes(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps({
        "file_count": len(rows),
        "bytes": total_bytes,
        "manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "contract_sha256": sha256(CONTRACT),
        "authorization_status": manifest["authorization_status"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
