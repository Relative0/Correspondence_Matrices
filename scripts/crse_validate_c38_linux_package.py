"""Validate the frozen C38 package in isolation without network or paid resources."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c38_linux_confirmation"
MANIFEST = HERE / "c38_linux_upload_manifest.json"
PROTOCOL = HERE / "C38_C37_NATIVE_SECOND_MACHINE_PROTOCOL_2026_09_03.md"
CONTRACT = HERE / "c38_c37_native_replication_contract.json"
ISOLATED = HERE / ".isolated-package-validation"
OUTPUT = HERE / "C38_PACKAGE_LOCAL_VALIDATION_20260903.json"
LOCAL_RUN_NAME = "c38-c37-native-local-package-validation-20260903-001"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8")
            + b"\n"
        )


def main() -> int:
    if ISOLATED.exists() or OUTPUT.exists():
        raise SystemExit("refusing to overwrite C38 local validation evidence")
    manifest = load(MANIFEST)
    if (
        manifest.get("schema")
        != "crse-c38-c37-native-linux-replication-upload-manifest/v1"
        or manifest.get("authorization_status")
        != "upload_not_authorized_exact_approval_pending"
        or manifest.get("protocol_sha256") != sha256(PROTOCOL)
        or manifest.get("replication_contract_sha256") != sha256(CONTRACT)
        or len(manifest.get("files", [])) != manifest.get("file_count")
        or sum(row["bytes"] for row in manifest["files"]) != manifest.get("bytes")
        or manifest.get("network_during_workload") is not False
    ):
        raise ValueError("C38 frozen manifest envelope mismatch")

    ISOLATED.mkdir(parents=True)
    for row in manifest["files"]:
        source = ROOT.joinpath(*Path(row["source"]).parts)
        target = ISOLATED.joinpath(*Path(row["target"]).parts)
        if source.stat().st_size != row["bytes"] or sha256(source) != row["sha256"]:
            raise ValueError(f"C38 package source changed: {row['source']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if target.stat().st_size != row["bytes"] or sha256(target) != row["sha256"]:
            raise ValueError(f"C38 isolated copy mismatch: {row['target']}")

    initial_files = sorted(
        path.relative_to(ISOLATED).as_posix()
        for path in ISOLATED.rglob("*") if path.is_file()
    )
    if initial_files != sorted(row["target"] for row in manifest["files"]):
        raise ValueError("C38 isolated package contains an unexpected file")

    run_dir = ISOLATED / "run-output" / LOCAL_RUN_NAME
    commands = (
        [
            sys.executable, "-B", "scripts/cm_c38_linux_replication.py",
            "--run-id", LOCAL_RUN_NAME, "--output", str(run_dir),
            "--compiler", "local", "--max-seconds", "1200",
            "--local-platform-validation",
        ],
        [
            sys.executable, "-B", "scripts/crse_native_exact_confirmation_verify.py",
            "--run-dir", str(run_dir),
        ],
        [
            sys.executable, "-B", "scripts/crse_c38_linux_replication_verify.py",
            "--run-dir", str(run_dir),
        ],
    )
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    records = []
    started = time.perf_counter()
    for command in commands:
        completed = subprocess.run(
            command, cwd=ISOLATED, env=environment, check=False,
            capture_output=True, text=True, timeout=1250,
        )
        record = {
            "command": [str(item) for item in command],
            "returncode": completed.returncode,
            "stdout_bytes": len(completed.stdout.encode("utf-8")),
            "stdout_sha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
            "stderr_bytes": len(completed.stderr.encode("utf-8")),
            "stderr_sha256": hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
        }
        records.append(record)
        if completed.returncode:
            raise RuntimeError(
                f"C38 isolated validation command failed: {record}; "
                f"stderr={completed.stderr[-2000:]}"
            )

    result = load(run_dir / "results.json")
    c37_verification = load(run_dir / "independent_verification.json")
    c38_verification = load(run_dir / "c38_independent_verification.json")
    raw_rows = sum(
        1 for line in (run_dir / "raw_measurements.jsonl").read_text(
            encoding="utf-8"
        ).splitlines() if line.strip()
    )
    invariants = {
        "result_complete": result.get("status") == "complete",
        "c37_verification": c37_verification.get("status") == "verified",
        "c38_verification": c38_verification.get("status") == "verified",
        "local_only_label": c38_verification.get("local_platform_validation_only") is True,
        "raw_sessions": raw_rows == 954,
        "single_root_query_checks": (
            c38_verification.get("single_root_queries_checked") == 44928
        ),
        "multi_root_output_query_checks": (
            c38_verification.get("multi_root_output_queries_checked") == 48384
        ),
        "semantic_and_artifact_checks": all(
            c38_verification.get(key) == 0
            for key in (
                "parent_identity_mismatches", "derived_identity_mismatches",
                "source_map_mismatches", "dataset_rebinding_mismatches",
                "verification_rebinding_mismatches", "freeze_binding_mismatches",
                "c37_verification_mismatches", "result_boundary_mismatches",
            )
        ),
        "no_training": result.get("decision", {}).get("training") is False,
        "no_production_promotion": (
            result.get("decision", {}).get("production_promotion") is False
        ),
    }
    if not all(invariants.values()):
        raise RuntimeError(f"C38 isolated validation invariant failed: {invariants}")

    output_files = [path for path in (ISOLATED / "run-output").rglob("*") if path.is_file()]
    output_bytes = sum(path.stat().st_size for path in output_files)
    if output_bytes > manifest["result_cap_bytes"]:
        raise RuntimeError("C38 isolated result exceeds retrieval cap")
    document = {
        "schema": "crse-c38-linux-package-local-validation/v1",
        "status": "pass",
        "authorization_status": manifest["authorization_status"],
        "manifest_sha256": sha256(MANIFEST),
        "protocol_sha256": sha256(PROTOCOL),
        "replication_contract_sha256": sha256(CONTRACT),
        "initial_file_count": len(initial_files),
        "initial_source_bytes": manifest["bytes"],
        "commands": records,
        "pythonpath_injected": False,
        "network_used": False,
        "local_platform_validation_only": True,
        "timing_result_used_for_c38_decision": False,
        "invariants": invariants,
        "raw_sessions": raw_rows,
        "single_root_queries_checked": 44928,
        "multi_root_output_queries_checked": 48384,
        "result_files": len(output_files),
        "result_bytes": output_bytes,
        "result_cap_bytes": manifest["result_cap_bytes"],
        "wall_seconds": time.perf_counter() - started,
    }
    write_new(OUTPUT, document)
    print(json.dumps(document, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
