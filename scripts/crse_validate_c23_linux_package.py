"""Run the frozen C23 package from an isolated directory without PYTHONPATH."""
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
HERE = ROOT / "docs/recognition/c23_linux_confirmation"
MANIFEST = HERE / "c23_linux_upload_manifest.json"
OUTPUT = HERE / "C23_PACKAGE_LOCAL_VALIDATION_20260831.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C23 package validation")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="crse-c23-package-") as temporary:
        isolated = Path(temporary)
        for row in manifest["files"]:
            source, target = ROOT / row["source"], isolated / row["target"]
            if source.stat().st_size != row["bytes"] or sha256(source) != row["sha256"]:
                raise ValueError(f"C23 frozen source changed: {row['source']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if target.stat().st_size != row["bytes"] or sha256(target) != row["sha256"]:
                raise ValueError("C23 isolated copy mismatch")
        before = sorted(
            str(path.relative_to(isolated)).replace("\\", "/")
            for path in isolated.rglob("*") if path.is_file()
        )
        if before != sorted(row["target"] for row in manifest["files"]):
            raise ValueError("C23 isolated package contains unlisted files")
        environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        environment.update({
            "PYTHONDONTWRITEBYTECODE": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        })
        dependency = subprocess.run(
            [sys.executable, "-B", "-c",
             "import dd,astutils,ply,pathlib; print(dd.__version__); "
             "print(pathlib.Path(dd.__file__).resolve())"],
            cwd=isolated, env=environment, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        )
        if (dependency.returncode != 0 or dependency.stdout.splitlines()[0] != "0.6.0"
                or str(isolated.resolve()) not in dependency.stdout.splitlines()[1]):
            raise ValueError("C23 vendored dependency isolation failed")
        command_records = []
        started = time.perf_counter()
        for command in manifest["commands"]:
            actual = [sys.executable, *command[1:]]
            completed = subprocess.run(
                actual, cwd=isolated, env=environment, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300,
            )
            command_records.append({
                "command": command,
                "returncode": completed.returncode,
                "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
                "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
                "stderr_bytes": len(completed.stderr.encode()),
            })
            if completed.returncode != 0:
                raise ValueError("isolated C23 package command failed: " + completed.stderr[-1200:])
        wall = time.perf_counter() - started
        run = isolated / "run-output" / manifest["run_name"]
        result = json.loads((run / "results.json").read_text(encoding="utf-8"))
        verification = json.loads((run / "independent_verification.json").read_text(encoding="utf-8"))
        if (
            result.get("status") != "complete"
            or result.get("measurement_rows") != 1680
            or result.get("memory_measurement_rows") != 56
            or result.get("semantic_or_artifact_mismatches") != 0
            or result.get("claims", {}).get("unchanged_c21_methods") is not True
            or verification.get("status") != "verified"
            or verification.get("measurement_rows_checked") != 1680
            or verification.get("semantic_or_artifact_mismatches") != 0
        ):
            raise ValueError("isolated C23 scientific gates failed")
        output_files = [path for path in (isolated / "run-output").rglob("*") if path.is_file()]
        output_bytes = sum(path.stat().st_size for path in output_files)
        if output_bytes > manifest["result_cap_bytes"]:
            raise ValueError("isolated C23 result cap exceeded")
        validation = {
            "schema": "crse-c23-linux-package-local-validation/v1",
            "status": "pass",
            "manifest_sha256": sha256(MANIFEST),
            "pythonpath_injected": False,
            "initial_file_count": len(before),
            "initial_files": before,
            "vendored_dd_version": "0.6.0",
            "vendored_dd_loaded_from_package": True,
            "commands": command_records,
            "wall_seconds": wall,
            "measurement_rows": 1680,
            "memory_rows": 56,
            "semantic_or_artifact_mismatches": 0,
            "independent_verification": "verified",
            "result_files": len(output_files),
            "result_bytes": output_bytes,
            "result_cap_bytes": manifest["result_cap_bytes"],
            "results_sha256": sha256(run / "results.json"),
            "independent_verification_sha256": sha256(run / "independent_verification.json"),
        }
    OUTPUT.write_bytes(json.dumps(validation, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps(validation, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
