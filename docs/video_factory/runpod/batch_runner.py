"""Bounded, resumable, failure-isolated runner for a CM render batch."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verified_finished(result_path: Path, expected_payload_sha256: str | None = None) -> bool:
    if not result_path.is_file():
        return False
    try:
        result = json.loads(result_path.read_text("utf-8"))
        if result.get("passed") is not True or result.get("status") != "passed":
            return False
        if expected_payload_sha256 is not None:
            return result.get("technical_observations", {}).get(
                "bundle_payload_sha256"
            ) == expected_payload_sha256
        return True
    except (OSError, json.JSONDecodeError):
        return False


def append_event(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def run_one(worker: Path, bundle: Path, job: Path, output: Path, timeout: int,
            payload_sha256: str) -> dict[str, Any]:
    job_data = json.loads(job.read_text("utf-8"))
    result_path = output / job_data["job_id"] / "render_result.json"
    if verified_finished(result_path, payload_sha256):
        return {"job_id": job_data["job_id"], "status": "resumed", "result": str(result_path)}
    try:
        proc = subprocess.run(
            [sys.executable, str(worker), str(job), "--bundle-root", str(bundle),
             "--output-root", str(output)], timeout=timeout,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return {"job_id": job_data["job_id"], "status": "failed", "error": "timeout"}
    if proc.returncode != 0 or not verified_finished(result_path, payload_sha256):
        return {"job_id": job_data["job_id"], "status": "failed",
                "error": (proc.stderr or proc.stdout or "worker failed")[-1000:]}
    return {"job_id": job_data["job_id"], "status": "passed", "result": str(result_path)}


def run_batch(bundle: Path, output: Path, *, max_parallel: int | None = None, timeout: int = 1800) -> list[dict[str, Any]]:
    batch = json.loads((bundle / "cm" / "batch_manifest.json").read_text("utf-8"))
    package = json.loads((bundle / "package_manifest.json").read_text("utf-8"))
    declared = int(batch["aggregate"]["max_parallel"])
    parallel = declared if max_parallel is None else min(max_parallel, declared)
    if parallel < 1:
        raise ValueError("max_parallel must be positive")
    jobs_by_id = {}
    for path in (bundle / "cm" / "proofs").glob("*/render_job.json"):
        data = json.loads(path.read_text("utf-8"))
        jobs_by_id[data["job_id"]] = path
    missing = set(batch["jobs"]) - set(jobs_by_id)
    if missing:
        raise ValueError(f"batch jobs missing from bundle: {sorted(missing)}")
    worker = bundle / "runpod" / "worker.py"
    event_path = output / "batch_progress.jsonl"
    results = []
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {
            pool.submit(
                run_one, worker, bundle, jobs_by_id[job_id], output, timeout,
                package["payload_sha256"],
            ): job_id
            for job_id in batch["jobs"]
        }
        try:
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                append_event(event_path, result)
        except KeyboardInterrupt:
            for future in futures:
                future.cancel()
            append_event(event_path, {"status": "interrupted"})
            raise
    results.sort(key=lambda item: batch["jobs"].index(item["job_id"]))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--max-parallel", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    results = run_batch(args.bundle_root.resolve(), args.output_root.resolve(),
                        max_parallel=args.max_parallel, timeout=args.timeout)
    print(json.dumps(results, indent=2))
    raise SystemExit(0 if all(item["status"] in {"passed", "resumed"} for item in results) else 1)


if __name__ == "__main__":
    main()
