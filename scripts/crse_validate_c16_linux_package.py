"""Run the complete C16 workload from only its frozen upload package."""
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
MANIFEST = ROOT / "docs/recognition/c16_linux_confirmation/c16_linux_upload_manifest.json"
ISOLATED = ROOT / "tmp/c16-linux-package-isolated-001"
OUTPUT = ROOT / "docs/recognition/c16_linux_confirmation/C16_PACKAGE_LOCAL_VALIDATION_20260830.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if ISOLATED.exists() or OUTPUT.exists():
        raise SystemExit("refusing to reuse C16 isolated validation output")
    ISOLATED.mkdir(parents=True)
    for row in manifest["files"]:
        source, target = ROOT / row["source"], ISOLATED / row["target"]
        if source.stat().st_size != row["bytes"] or sha(source) != row["sha256"]:
            raise SystemExit("C16 source changed after package freeze")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if target.stat().st_size != row["bytes"] or sha(target) != row["sha256"]:
            raise SystemExit("C16 isolated copy mismatch")
    before = sorted(str(path.relative_to(ISOLATED)).replace("\\", "/")
                    for path in ISOLATED.rglob("*") if path.is_file())
    if before != sorted(row["target"] for row in manifest["files"]):
        raise SystemExit("C16 isolated directory contains files outside manifest")
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update({"PYTHONPATH": str(ISOLATED), "PYTHONDONTWRITEBYTECODE": "1",
                        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
                        "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"})
    command = [sys.executable, "-B", "scripts/crse_gf2_screening_linux_confirmation.py",
               "--dataset", "study/c16-dataset.json", "--output",
               "run-output/c16-linux-confirmation", "--repetitions", "3"]
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=ISOLATED, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=360)
    wall = time.perf_counter() - started
    summary_path = ISOLATED / "run-output/c16-linux-confirmation/summary.json"
    if completed.returncode != 0 or not summary_path.is_file():
        raise SystemExit("isolated C16 workload failed: " + completed.stderr[-1200:])
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (summary.get("status") != "complete" or summary.get("semantic_mismatches") != 0
            or summary.get("criteria", {}).get("exact") is not True
            or summary.get("config", {}).get("cases") != 40
            or summary.get("measurement_rows") != 360):
        raise SystemExit("isolated C16 workload did not satisfy exactness gates")
    result = {
        "schema": "crse-c16-linux-package-local-validation/v1",
        "status": "pass",
        "manifest_sha256": sha(MANIFEST),
        "initial_file_count": len(before),
        "initial_files": before,
        "returncode": completed.returncode,
        "wall_seconds": wall,
        "summary_sha256": sha(summary_path),
        "measurement_rows": summary["measurement_rows"],
        "semantic_mismatches": 0,
        "criteria": summary["criteria"],
        "speedup": summary["speedup"],
        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderr_bytes": len(completed.stderr.encode()),
    }
    OUTPUT.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
