"""Run the ordered, hash-bound CM deep-series smoke jobs sequentially."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


def run(bundle_root: Path, output_root: Path, timeout: int) -> None:
    batch = json.loads((bundle_root / "cm" / "batch_manifest.json").read_text("utf-8"))
    worker = bundle_root / "runpod" / "deep_series_smoke_worker.py"
    results = []
    for job_id in batch["ordered_job_ids"]:
        job = bundle_root / "cm" / "jobs" / f"{job_id}.json"
        completed = subprocess.run(
            [sys.executable, str(worker), str(job), "--bundle-root", str(bundle_root),
             "--output-root", str(output_root)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
        log_root = output_root / job_id
        log_root.mkdir(parents=True, exist_ok=True)
        (log_root / "worker.stdout.log").write_text(completed.stdout, encoding="utf-8")
        (log_root / "worker.stderr.log").write_text(completed.stderr, encoding="utf-8")
        result_path = log_root / "render_result.json"
        result = json.loads(result_path.read_text("utf-8")) if result_path.is_file() else {}
        results.append({"job_id": job_id, "returncode": completed.returncode, "passed": result.get("passed") is True})
        if completed.returncode or result.get("passed") is not True:
            raise RuntimeError(f"smoke job failed: {job_id}")
    summary = {"schema_version": "1.0", "batch_id": batch["batch_id"], "jobs": results, "passed": True}
    (output_root / "batch_result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    run(args.bundle_root.resolve(), args.output_root.resolve(), args.timeout)


if __name__ == "__main__":
    main()
