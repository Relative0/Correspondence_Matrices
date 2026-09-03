"""Validate the comparison package in an isolated tree without network or timing."""
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
HERE = ROOT / "docs/recognition/architecture_comparison_execution_retry_20260903"
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
ISOLATED = HERE / ".isolated-package-validation"
OUTPUT = HERE / "LOCAL_PACKAGE_VALIDATION.json"
SMOKE_NAME = "architecture-comparison-local-package-smoke-20260903-002"


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
        raise SystemExit("refusing to overwrite local package validation")
    manifest = _load(MANIFEST)
    if (
        manifest.get("schema") != "cm-architecture-comparison-runpod-upload-manifest/v1"
        or manifest.get("authorization_status") != "upload_not_authorized_exact_approval_pending"
        or len(manifest.get("files", [])) != manifest.get("file_count")
        or sum(row["bytes"] for row in manifest["files"]) != manifest.get("bytes")
        or manifest.get("network_during_workload") is not False
        or manifest.get("limits", {}).get("wall_seconds") != 420
    ):
        raise ValueError("upload manifest envelope")
    ISOLATED.mkdir(parents=True)
    for row in manifest["files"]:
        source = ROOT.joinpath(*Path(row["source"]).parts)
        target = ISOLATED.joinpath(*Path(row["target"]).parts)
        if source.stat().st_size != row["bytes"] or _sha256(source) != row["sha256"]:
            raise ValueError(f"package source changed: {row['source']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if target.stat().st_size != row["bytes"] or _sha256(target) != row["sha256"]:
            raise ValueError(f"isolated copy mismatch: {row['target']}")
    initial = sorted(
        path.relative_to(ISOLATED).as_posix()
        for path in ISOLATED.rglob("*") if path.is_file()
    )
    if initial != sorted(row["target"] for row in manifest["files"]):
        raise ValueError("unexpected isolated package file")
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    freeze_check = subprocess.run(
        [
            sys.executable, "-B", "-c",
            "import json,pathlib; from cmbench.comparative.architecture_comparison_freeze "
            "import verify_freeze; root=pathlib.Path.cwd(); artifact=root/'docs/recognition/"
            "architecture_comparison_freeze_20260903/FREEZE.json'; "
            "verify_freeze(json.loads(artifact.read_text()), root)",
        ],
        cwd=ISOLATED, env=environment, check=False, capture_output=True, text=True, timeout=120,
    )
    if freeze_check.returncode:
        raise RuntimeError(
            "isolated parent-freeze verification failed: "
            f"{freeze_check.returncode}; {freeze_check.stderr[-3000:]}"
        )
    output = ISOLATED / "run-output" / SMOKE_NAME
    command = [
        sys.executable, "-B", "scripts/cm_architecture_comparison_campaign.py",
        "--output", str(output), "--functional-smoke", "--local-platform-validation",
        "--oracles", str(ISOLATED / "docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json"),
    ]
    started = time.perf_counter()
    completed = subprocess.run(
        command, cwd=ISOLATED, env=environment, check=False,
        capture_output=True, text=True, timeout=300,
    )
    if completed.returncode:
        raise RuntimeError(
            f"isolated functional smoke failed: {completed.returncode}; {completed.stderr[-3000:]}"
        )
    smoke = _load(output / "functional_smoke.json")
    if (
        smoke.get("status") != "pass"
        or smoke.get("rows_checked") != 71
        or smoke.get("rows_by_lane") != {"A": 8, "B": 8, "C": 4, "D": 51}
        or smoke.get("all_exact") is not True
        or smoke.get("synthetic_clock_used") is not True
        or smoke.get("timing_evidence_produced") is not False
        or smoke.get("local_platform_validation_only") is not True
    ):
        raise RuntimeError("isolated functional smoke invariant")
    result_files = [
        path for path in (ISOLATED / "run-output").rglob("*") if path.is_file()
    ]
    result_bytes = sum(path.stat().st_size for path in result_files)
    if result_bytes > manifest["result_cap_bytes"]:
        raise RuntimeError("local smoke output exceeds retrieval cap")
    document = {
        "schema": "cm-architecture-comparison-local-package-validation/v1",
        "status": "pass",
        "manifest_sha256": _sha256(MANIFEST),
        "package_files": manifest["file_count"],
        "package_bytes": manifest["bytes"],
        "isolated_initial_files": len(initial),
        "functional_rows_checked": smoke["rows_checked"],
        "functional_rows_by_lane": smoke["rows_by_lane"],
        "native_library_sha256": smoke["native_library_sha256"],
        "network_used": False,
        "parent_freeze_verification_passed": True,
        "pythonpath_injected": False,
        "synthetic_clock_used": True,
        "timing_evidence_produced": False,
        "decision_bearing_result_produced": False,
        "runpod_resource_created": False,
        "result_files": len(result_files),
        "result_bytes": result_bytes,
        "result_cap_bytes": manifest["result_cap_bytes"],
        "stdout_bytes": len(completed.stdout.encode("utf-8")),
        "stdout_sha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
        "stderr_bytes": len(completed.stderr.encode("utf-8")),
        "stderr_sha256": hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
        "wall_seconds": time.perf_counter() - started,
    }
    _write_new(OUTPUT, document)
    print(json.dumps(document, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
