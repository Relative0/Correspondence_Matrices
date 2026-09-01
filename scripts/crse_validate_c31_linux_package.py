"""Run the frozen C31 package from an isolated directory without PYTHONPATH."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c31_linux_confirmation"
MANIFEST = HERE / "c31_linux_upload_manifest.json"
OUTPUT = HERE / "C31_PACKAGE_LOCAL_VALIDATION_20260901.json"
ISOLATED = ROOT / "docs/recognition/runs/c31-package-local-validation-20260901-001"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists() or ISOLATED.exists():
        raise SystemExit("refusing to overwrite C31 package validation evidence")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("authorization_status") != "upload_not_authorized_exact_approval_pending":
        raise ValueError("C31 package authorization state changed")
    ISOLATED.mkdir(parents=True)
    for row in manifest["files"]:
        source, target = ROOT / row["source"], ISOLATED / row["target"]
        if source.stat().st_size != row["bytes"] or sha256(source) != row["sha256"]:
            raise ValueError(f"C31 frozen source changed: {row['source']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if target.stat().st_size != row["bytes"] or sha256(target) != row["sha256"]:
            raise ValueError("C31 isolated copy mismatch")
    before = sorted(
        str(path.relative_to(ISOLATED)).replace("\\", "/")
        for path in ISOLATED.rglob("*") if path.is_file())
    if before != sorted(row["target"] for row in manifest["files"]):
        raise ValueError("C31 isolated package contains unlisted files")
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    })
    dependency = subprocess.run(
        [
            sys.executable, "-B", "-c",
            "import dd,json,pathlib; from cmbench.comparative."
            "gf2_prepared_policy_adjudication import median_lower_order_statistic_rank; "
            "print(dd.__version__); print(pathlib.Path(dd.__file__).resolve()); "
            "print(json.dumps(median_lower_order_statistic_rank()))",
        ],
        cwd=ISOLATED,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    dependency_lines = dependency.stdout.splitlines()
    if (
        dependency.returncode != 0
        or len(dependency_lines) != 3
        or dependency_lines[0] != "0.6.0"
        or str(ISOLATED.resolve()) not in dependency_lines[1]
        or json.loads(dependency_lines[2]) != [5, 63019 / 65536]
    ):
        raise ValueError("C31 vendored dependency or adjudicator isolation failed")

    command_records = []
    started = time.perf_counter()
    for command in manifest["commands"]:
        actual = [sys.executable, *command[1:]]
        completed = subprocess.run(
            actual,
            cwd=ISOLATED,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=660,
        )
        command_records.append({
            "command": command,
            "returncode": completed.returncode,
            "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
            "stdout_bytes": len(completed.stdout.encode()),
            "stderr_bytes": len(completed.stderr.encode()),
        })
        if completed.returncode != 0:
            raise ValueError(
                "isolated C31 package command failed: " + completed.stderr[-2000:])
    wall_seconds = time.perf_counter() - started
    run = ISOLATED / "run-output" / manifest["run_name"]
    result = json.loads((run / "results.json").read_text(encoding="utf-8"))
    verification = json.loads(
        (run / "independent_verification.json").read_text(encoding="utf-8"))
    summary = result.get("summary", {})
    invariants = {
        "result_complete": result.get("status") == "complete",
        "measurement_batches": summary.get("measurement_batches") == 128,
        "paired_batches": summary.get("paired_batches") == 64,
        "timed_queries": summary.get("timed_queries") == 1024,
        "preparation_charge_conserved": summary.get(
            "lifecycle_preparation_charge_conserved") is True,
        "functional_controls": result.get("functional_controls_passed") is True,
        "result_exactness": result.get("semantic_or_artifact_mismatches") == 0,
        "verification_status": verification.get("status") == "verified",
        "verified_batches": verification.get("measurement_batches_checked") == 128,
        "verified_pairs": verification.get("paired_batches_checked") == 64,
        "verified_queries": verification.get("timed_query_records_checked") == 1024,
        "verified_contexts": verification.get("verified_context_records_replayed") == 512,
        "verified_controls": verification.get("functional_controls_replayed") == 6,
        "verified_exactness": verification.get("semantic_or_artifact_mismatches") == 0,
        "policy_refit": result.get("policy_refit") is False,
        "training": result.get("training") is False,
        "promotion_refused": (
            result.get("shadow_promotion") is False
            and result.get("production_promotion") is False
        ),
    }
    if not all(invariants.values()):
        raise ValueError(
            "isolated C31 scientific invariants failed: "
            + json.dumps(invariants, sort_keys=True))
    output_files = [path for path in (ISOLATED / "run-output").rglob("*") if path.is_file()]
    output_bytes = sum(path.stat().st_size for path in output_files)
    if output_bytes > manifest["result_cap_bytes"]:
        raise ValueError("isolated C31 result cap exceeded")
    validation = {
        "schema": "crse-c31-linux-package-local-validation/v1",
        "status": "pass",
        "manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": manifest["protocol_sha256"],
        "replication_contract_sha256": manifest["replication_contract_sha256"],
        "authorization_status": manifest["authorization_status"],
        "pythonpath_injected": False,
        "initial_file_count": len(before),
        "initial_source_bytes": manifest["bytes"],
        "vendored_dd_version": "0.6.0",
        "vendored_dd_loaded_from_package": True,
        "c31_adjudicator_loaded_from_package": True,
        "paired_lower_bound_rank": 5,
        "paired_lower_bound_achieved_confidence": 63019 / 65536,
        "commands": command_records,
        "wall_seconds": wall_seconds,
        "invariants": invariants,
        "measurement_batches": 128,
        "paired_batches": 64,
        "timed_queries": 1024,
        "verified_context_records": 512,
        "semantic_or_artifact_mismatches": 0,
        "prepared_no_regret_gate": summary.get("prepared_no_regret_gate"),
        "timing_gate_is_observational_not_package_validity": True,
        "independent_verification": "verified",
        "result_files": len(output_files),
        "result_bytes": output_bytes,
        "result_cap_bytes": manifest["result_cap_bytes"],
        "results_sha256": sha256(run / "results.json"),
        "measurements_sha256": sha256(run / "measurements.jsonl"),
        "independent_verification_sha256": sha256(
            run / "independent_verification.json"),
    }
    OUTPUT.write_bytes(
        json.dumps(validation, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps(validation, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
