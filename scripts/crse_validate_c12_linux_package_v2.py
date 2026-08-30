"""Run the complete C12 workload from only the frozen package-v2 files."""
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
MANIFEST = ROOT / "docs/recognition/c12_linux_confirmation/c12_linux_upload_manifest_v2.json"
ISOLATED = ROOT / "tmp/c12-linux-package-v2-isolated-001"
OUTPUT = ROOT / "docs/recognition/c12_linux_confirmation/C12_PACKAGE_V2_LOCAL_VALIDATION_20260830.json"
PYTHON = ROOT / ".venv-crse-neural/Scripts/python.exe"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if ISOLATED.exists():
        raise SystemExit("refusing to reuse isolated package directory")
    ISOLATED.mkdir(parents=True)
    copied = []
    for row in manifest["files"]:
        source, target = ROOT / row["source"], ISOLATED / row["target"]
        if source.stat().st_size != row["bytes"] or sha(source) != row["sha256"]:
            raise SystemExit("source changed after package freeze")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if target.stat().st_size != row["bytes"] or sha(target) != row["sha256"]:
            raise SystemExit("isolated copy mismatch")
        copied.append(str(target.relative_to(ISOLATED)).replace("\\", "/"))
    before = sorted(str(path.relative_to(ISOLATED)).replace("\\", "/")
                    for path in ISOLATED.rglob("*") if path.is_file())
    if before != sorted(row["target"] for row in manifest["files"]):
        raise SystemExit("isolated directory contains files outside manifest")
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update({"PYTHONPATH": str(ISOLATED), "PYTHONDONTWRITEBYTECODE": "1",
                        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                        "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
    command = [str(PYTHON), "-B", "scripts/crse_adaptive_dispatcher_linux_confirmation.py",
        "--dataset", "study/c12-dataset.json", "--output",
        "run-output/yosys-c7-linux-confirmation", "--repetitions", "16"]
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=ISOLATED, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
    wall = time.perf_counter() - started
    summary_path = ISOLATED / "run-output/yosys-c7-linux-confirmation/summary.json"
    if completed.returncode != 0 or not summary_path.is_file():
        raise SystemExit("isolated package workload failed: " + completed.stderr[-1200:])
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (summary.get("status") != "complete" or summary.get("semantic_mismatches") != 0
            or summary.get("criteria", {}).get("exact") is not True
            or summary.get("config", {}).get("cases") != 40
            or summary.get("config", {}).get("repetitions") != 16):
        raise SystemExit("isolated package workload did not satisfy exactness gates")
    result = {"schema": "crse-c12-package-v2-local-validation/v1", "status": "pass",
        "manifest_sha256": sha(MANIFEST), "initial_file_count": len(before),
        "initial_files": before, "isolated_directory": str(ISOLATED.relative_to(ROOT)).replace("\\", "/"),
        "returncode": completed.returncode, "wall_seconds": wall,
        "summary_sha256": sha(summary_path), "measurement_rows": 2560,
        "per_case_rows": 160, "semantic_mismatches": 0,
        "criteria": summary["criteria"], "split_summary": summary["split_summary"],
        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderr_bytes": len(completed.stderr.encode())}
    OUTPUT.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
