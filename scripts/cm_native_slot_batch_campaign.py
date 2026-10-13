"""Execute the frozen native scalar-versus-batch campaign after authorization."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from cmbench.comparative import gf2_native_slot_batch_workload as workload


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _worker(args: argparse.Namespace) -> int:
    freeze_path = args.freeze.resolve()
    oracles_path = args.oracles.resolve()
    authorization = _load(args.authorization.resolve())
    workload.validate_authorization(authorization, freeze_path, oracles_path)
    freeze = _load(freeze_path)
    oracles = _load(oracles_path)
    workload.validate_freeze(freeze)
    workload.validate_oracles(oracles, freeze, replay=False)
    row = workload.execute_cell(
        freeze,
        oracles,
        args.library.resolve(),
        args.case_id,
        args.arm,
        args.query_count,
    )
    print(json.dumps(row, sort_keys=True, separators=(",", ":")))
    return 0


def _host_facts() -> dict:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "python": sys.version,
    }


def _run(args: argparse.Namespace) -> int:
    freeze_path = args.freeze.resolve()
    oracles_path = args.oracles.resolve()
    authorization_path = args.authorization.resolve()
    library_path = args.library.resolve()
    output = args.output.resolve()
    for path in (freeze_path, oracles_path, authorization_path, library_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    if not output.is_relative_to(ROOT.resolve()):
        raise ValueError("run output must remain inside the project")
    authorization = _load(authorization_path)
    workload.validate_authorization(authorization, freeze_path, oracles_path)
    freeze = _load(freeze_path)
    oracles = _load(oracles_path)
    workload.validate_freeze(freeze, ROOT)
    workload.validate_oracles(oracles, freeze, replay=False)
    output.mkdir(parents=True, exist_ok=False)
    raw_path = output / "RAW.jsonl"
    started = time.monotonic()
    counts = Counter()
    with raw_path.open("x", encoding="utf-8", newline="\n") as stream:
        for cell in freeze["measurement_contract"]["schedule"]:
            if time.monotonic() - started > workload.MAX_WALL_SECONDS:
                raise TimeoutError("native batch campaign exceeded frozen wall bound")
            command = [
                sys.executable,
                "-B",
                str(Path(__file__).resolve()),
                "--worker",
                "--freeze",
                str(freeze_path),
                "--oracles",
                str(oracles_path),
                "--authorization",
                str(authorization_path),
                "--library",
                str(library_path),
                "--case-id",
                cell["case_id"],
                "--arm",
                cell["arm"],
                "--query-count",
                str(cell["query_count"]),
            ]
            lifecycle_started = time.perf_counter_ns()
            try:
                completed = subprocess.run(
                    command,
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=workload.CELL_TIMEOUT_SECONDS,
                )
                lifecycle_ns = time.perf_counter_ns() - lifecycle_started
                if completed.returncode == 0:
                    row = json.loads(completed.stdout)
                    counts["ok"] += 1
                else:
                    row = {
                        "schema": workload.RAW_SCHEMA,
                        "status": "failed",
                        "reason": "worker_nonzero_exit",
                        "worker_exit_code": completed.returncode,
                        "worker_stderr": completed.stderr[-4000:],
                    }
                    counts["failed"] += 1
            except subprocess.TimeoutExpired:
                lifecycle_ns = time.perf_counter_ns() - lifecycle_started
                row = {
                    "schema": workload.RAW_SCHEMA,
                    "status": "timeout",
                    "reason": "cell_timeout",
                }
                counts["timeout"] += 1
            row.update(cell)
            row["fresh_process_lifecycle_ns"] = lifecycle_ns
            row["fresh_process_lifecycle_in_accounted_total"] = False
            stream.write(json.dumps(
                row, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ))
            stream.write("\n")
            stream.flush()
    facts = _host_facts()
    result = {
        "schema": "crse-native-slot-batch-local-run/v1",
        "status": "complete_unverified",
        "freeze_file_sha256": workload.file_sha256(freeze_path),
        "oracles_file_sha256": workload.file_sha256(oracles_path),
        "authorization_file_sha256": workload.file_sha256(authorization_path),
        "native_library_sha256": workload.file_sha256(library_path),
        "raw_file_sha256": workload.file_sha256(raw_path),
        "host_facts": facts,
        "physical_machine_sha256": workload.digest(facts),
        "elapsed_seconds": time.monotonic() - started,
        "counts": dict(counts),
    }
    _write_json_new(output / "RESULT.json", result)
    print(output)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--oracles", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--case-id")
    parser.add_argument("--arm", choices=workload.ARMS)
    parser.add_argument("--query-count", type=int, choices=workload.QUERY_COUNTS)
    args = parser.parse_args()
    if args.worker:
        if args.case_id is None or args.arm is None or args.query_count is None:
            parser.error("worker cell identity is required")
        return _worker(args)
    if args.output is None:
        parser.error("--output is required")
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
