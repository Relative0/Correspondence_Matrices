"""Validate the corrected query-ladder package in an isolated local tree."""
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
HERE = ROOT / "docs/recognition/architecture_query_ladder_followup_execution_20260903"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
ISOLATED = HERE / ".isolated-package-validation"
OUTPUT = HERE / "LOCAL_PACKAGE_VALIDATION.json"
SMOKE_NAME = "architecture-query-ladder-local-package-smoke-20260903-001"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main() -> int:
    if ISOLATED.exists() or OUTPUT.exists():
        raise SystemExit("refusing to overwrite query-ladder local package validation")
    manifest = _load(MANIFEST)
    if (
        manifest.get("schema") != "cm-architecture-query-ladder-runpod-upload-manifest/v1"
        or manifest.get("authorization_status") != "upload_not_authorized_exact_approval_pending"
        or manifest.get("file_count") != len(manifest.get("files", []))
        or manifest.get("bytes") != sum(row["bytes"] for row in manifest["files"])
        or manifest.get("network_during_workload") is not False
        or manifest.get("limits", {}).get("workload_wall_seconds") != 420
    ):
        raise ValueError("query-ladder upload manifest")
    ISOLATED.mkdir(parents=True)
    for row in manifest["files"]:
        source = ROOT.joinpath(*Path(row["source"]).parts)
        target = ISOLATED.joinpath(*Path(row["target"]).parts)
        if source.stat().st_size != row["bytes"] or _sha256(source) != row["sha256"]:
            raise ValueError(f"query-ladder package source changed: {row['source']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if target.stat().st_size != row["bytes"] or _sha256(target) != row["sha256"]:
            raise ValueError(f"query-ladder isolated copy mismatch: {row['target']}")
    initial = sorted(path.relative_to(ISOLATED).as_posix() for path in ISOLATED.rglob("*") if path.is_file())
    if initial != sorted(row["target"] for row in manifest["files"]):
        raise ValueError("unexpected query-ladder isolated package file")
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    freeze_check = subprocess.run(
        [
            sys.executable, "-B", "scripts/crse_verify_architecture_query_ladder_freeze.py",
            "--output", "run-output/freeze-verification.json",
        ],
        cwd=ISOLATED, env=environment, capture_output=True, text=True, timeout=120,
    )
    if freeze_check.returncode:
        raise RuntimeError(f"isolated follow-up freeze verification failed: {freeze_check.stderr[-3000:]}")
    smoke_output = ISOLATED / "run-output" / SMOKE_NAME
    command = [
        sys.executable, "-B", "scripts/cm_architecture_query_ladder_campaign.py",
        "--output", str(smoke_output), "--functional-smoke", "--local-platform-validation",
    ]
    started = time.perf_counter()
    completed = subprocess.run(
        command, cwd=ISOLATED, env=environment, capture_output=True, text=True, timeout=300,
    )
    if completed.returncode:
        raise RuntimeError(f"isolated query-ladder functional smoke failed: {completed.stderr[-3000:]}")
    smoke = _load(smoke_output / "functional_smoke.json")
    if (
        smoke.get("status") != "pass" or smoke.get("rows") != 32
        or smoke.get("query_counts") != [1, 4, 16, 64]
        or len(smoke.get("arms", [])) != 8
        or smoke.get("synthetic_clock_used") is not True
        or smoke.get("timing_evidence_produced") is not False
        or smoke.get("memory_evidence_produced") is not False
        or smoke.get("local_platform_validation_only") is not True
    ):
        raise RuntimeError("isolated query-ladder functional smoke invariant")
    result_files = [path for path in (ISOLATED / "run-output").rglob("*") if path.is_file()]
    result_bytes = sum(path.stat().st_size for path in result_files)
    document = {
        "schema": "cm-architecture-query-ladder-local-package-validation/v1",
        "status": "pass",
        "manifest_sha256": _sha256(MANIFEST),
        "package_files": manifest["file_count"],
        "package_bytes": manifest["bytes"],
        "isolated_initial_files": len(initial),
        "parent_and_followup_freeze_verification_passed": True,
        "functional_rows_checked": smoke["rows"],
        "functional_query_counts": smoke["query_counts"],
        "functional_arms": smoke["arms"],
        "native_library_sha256": smoke["runtime_binding"]["native_library_sha256"],
        "network_used": False,
        "pythonpath_injected": False,
        "synthetic_clock_used": True,
        "timing_evidence_produced": False,
        "memory_evidence_produced": False,
        "decision_bearing_result_produced": False,
        "runpod_resource_created": False,
        "result_files": len(result_files),
        "result_bytes": result_bytes,
        "result_cap_bytes": manifest["result_cap_bytes"],
        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
        "wall_seconds": time.perf_counter() - started,
    }
    _write_new(OUTPUT, document)
    print(json.dumps(document, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
