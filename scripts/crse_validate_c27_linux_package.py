"""Run the frozen C27 package from an isolated directory without PYTHONPATH."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c27_linux_confirmation"
MANIFEST = HERE / "c27_linux_upload_manifest.json"
OUTPUT = HERE / "C27_PACKAGE_LOCAL_VALIDATION_20260831.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C27 package validation")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("authorization_status") != "upload_not_authorized_exact_approval_pending":
        raise ValueError("C27 package authorization state changed")
    with tempfile.TemporaryDirectory(prefix="crse-c27-package-") as temporary:
        isolated = Path(temporary)
        for row in manifest["files"]:
            source, target = ROOT / row["source"], isolated / row["target"]
            if source.stat().st_size != row["bytes"] or sha256(source) != row["sha256"]:
                raise ValueError(f"C27 frozen source changed: {row['source']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if target.stat().st_size != row["bytes"] or sha256(target) != row["sha256"]:
                raise ValueError("C27 isolated copy mismatch")
        before = sorted(
            str(path.relative_to(isolated)).replace("\\", "/")
            for path in isolated.rglob("*") if path.is_file())
        if before != sorted(row["target"] for row in manifest["files"]):
            raise ValueError("C27 isolated package contains unlisted files")
        environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        environment.update({
            "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
        })
        dependency = subprocess.run(
            [sys.executable, "-B", "-c",
             "import dd,astutils,ply,pathlib; print(dd.__version__); "
             "print(pathlib.Path(dd.__file__).resolve())"],
            cwd=isolated, env=environment, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=30)
        if (
            dependency.returncode != 0 or dependency.stdout.splitlines()[0] != "0.6.0"
            or str(isolated.resolve()) not in dependency.stdout.splitlines()[1]
        ):
            raise ValueError("C27 vendored dependency isolation failed")
        command_records = []
        started = time.perf_counter()
        for command in manifest["commands"]:
            actual = [sys.executable, *command[1:]]
            completed = subprocess.run(
                actual, cwd=isolated, env=environment, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=360)
            command_records.append({
                "command": command, "returncode": completed.returncode,
                "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
                "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
                "stdout_bytes": len(completed.stdout.encode()),
                "stderr_bytes": len(completed.stderr.encode()),
            })
            if completed.returncode != 0:
                raise ValueError("isolated C27 package command failed: " + completed.stderr[-1600:])
        wall = time.perf_counter() - started
        run = isolated / "run-output" / manifest["run_name"]
        result = json.loads((run / "results.json").read_text(encoding="utf-8"))
        verification = json.loads(
            (run / "independent_verification.json").read_text(encoding="utf-8"))
        invariants = {
            "result_complete": result.get("status") == "complete",
            "measurement_batches": result.get("measurement_batches") == 720,
            "timed_queries": result.get("timed_queries") == 7560,
            "memory_batches": result.get("memory_measurement_batches") == 24,
            "fallback_controls": result.get("fallback_controls") == 48,
            "selected_path_controls": result.get("selected_path_controls") == 48,
            "refusal_controls": result.get("refusal_controls") == 10,
            "result_exactness": result.get("semantic_or_artifact_mismatches") == 0,
            "verification_status": verification.get("status") == "verified",
            "verified_batches": verification.get("measurement_batches_checked") == 720,
            "verified_queries": verification.get("timed_query_records_checked") == 7560,
            "verified_exactness": verification.get("semantic_or_artifact_mismatches") == 0,
        }
        if not all(invariants.values()):
            raise ValueError("isolated C27 scientific invariants failed: " + json.dumps(
                invariants, sort_keys=True))
        timing_gate = result.get("summary", {}).get("support_aware_confirmation_gate")
        if type(timing_gate) is not bool:
            raise ValueError("isolated C27 timing gate is missing")
        output_files = [
            path for path in (isolated / "run-output").rglob("*") if path.is_file()]
        output_bytes = sum(path.stat().st_size for path in output_files)
        if output_bytes > manifest["result_cap_bytes"]:
            raise ValueError("isolated C27 result cap exceeded")
        validation = {
            "schema": "crse-c27-linux-package-local-validation/v1",
            "status": "pass",
            "manifest_sha256": sha256(MANIFEST),
            "authorization_status": manifest["authorization_status"],
            "pythonpath_injected": False,
            "initial_file_count": len(before),
            "initial_files": before,
            "vendored_dd_version": "0.6.0",
            "vendored_dd_loaded_from_package": True,
            "commands": command_records,
            "wall_seconds": wall,
            "measurement_batches": 720,
            "timed_queries": 7560,
            "memory_batches": 24,
            "semantic_or_artifact_mismatches": 0,
            "support_aware_confirmation_gate": timing_gate,
            "timing_gate_is_observational_not_package_validity": True,
            "independent_verification": "verified",
            "result_files": len(output_files),
            "result_bytes": output_bytes,
            "result_cap_bytes": manifest["result_cap_bytes"],
            "results_sha256": sha256(run / "results.json"),
            "independent_verification_sha256": sha256(
                run / "independent_verification.json"),
        }
    OUTPUT.write_bytes(json.dumps(
        validation, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n")
    print(json.dumps(validation, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
