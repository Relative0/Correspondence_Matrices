"""Prepare and execute the frozen 72-case exact q64 decision surface."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.recognition import query_ladder_learning_freeze as learning
from cmbench.recognition import query_ladder_q64_execution as q64


def _run_dir(value: Path) -> Path:
    resolved = value.resolve()
    if not resolved.is_relative_to(ROOT):
        raise argparse.ArgumentTypeError("run directory must be inside the project")
    return resolved


def prepare(run_dir: Path, replication_id: str, compiler: str) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=False)
    baseline = q64.build_baseline_closure(ROOT)
    baseline_path = run_dir / "BASELINE_CLOSURE.json"
    q64.write_json_exclusive(baseline_path, baseline)
    frozen = q64.load_verified_parent(ROOT)
    oracles = q64.build_oracles(frozen)
    oracle_path = run_dir / "ORACLES.json"
    q64.write_json_exclusive(oracle_path, oracles)
    host_dir = run_dir / replication_id
    host_dir.mkdir()
    native_path, native_identity = q64.build_native(ROOT, host_dir / "native", compiler)
    child = q64.build_child_freeze(
        ROOT, run_dir, baseline_path, oracle_path, native_identity,
    )
    child_path = run_dir / "CHILD_FREEZE.json"
    q64.write_json_exclusive(child_path, child)
    child_verification = q64.verify_child_freeze(ROOT, child_path)
    q64.write_json_exclusive(run_dir / "CHILD_FREEZE_INDEPENDENT_VERIFICATION.json",
                             child_verification)
    functional = q64.functional_preflight(frozen, oracles, native_path)
    q64.write_json_exclusive(run_dir / "FUNCTIONAL_PREFLIGHT.json", functional)
    facts, machine_sha = q64.physical_machine_identity()
    preflight_core = {
        "schema": q64.HOST_PREFLIGHT_SCHEMA,
        "status": "verified_ready_not_timed",
        "replication_id": replication_id,
        "physical_machine_attestation": "physical_machine_not_vm",
        "physical_machine_facts": facts,
        "physical_machine_sha256": machine_sha,
        "python": sys.version,
        "runtime_executable_sha256": q64.file_sha256(Path(sys.executable)),
        "native": native_identity,
        "child_freeze_file_sha256": q64.file_sha256(child_path),
        "functional_preflight_file_sha256": q64.file_sha256(run_dir / "FUNCTIONAL_PREFLIGHT.json"),
        "charged_costs_measured": False,
        "decision_cells_executed": 0,
        "prospective_cases_consumed": 0,
    }
    q64.write_json_exclusive(host_dir / "HOST_PREFLIGHT.json",
                             {**preflight_core, "preflight_sha256": q64.digest(preflight_core)})
    return {
        "status": "prepared", "run_dir": str(run_dir),
        "replication_id": replication_id, "planned_cells": q64.EXPECTED_CELLS,
        "child_freeze_file_sha256": q64.file_sha256(child_path),
        "native_library_sha256": native_identity["native_library_sha256"],
        "physical_machine_sha256": machine_sha,
    }


def prepare_host(run_dir: Path, replication_id: str, compiler: str) -> dict[str, Any]:
    q64.verify_child_freeze(ROOT, run_dir / "CHILD_FREEZE.json")
    host_dir = run_dir / replication_id
    host_dir.mkdir(parents=True, exist_ok=False)
    native_path, native_identity = q64.build_native(ROOT, host_dir / "native", compiler)
    frozen = q64.load_verified_parent(ROOT)
    oracles = q64.load_json(run_dir / "ORACLES.json")
    q64.validate_oracles(oracles, frozen)
    functional = q64.functional_preflight(frozen, oracles, native_path)
    functional_path = host_dir / "FUNCTIONAL_PREFLIGHT.json"
    q64.write_json_exclusive(functional_path, functional)
    facts, machine_sha = q64.physical_machine_identity()
    core = {
        "schema": q64.HOST_PREFLIGHT_SCHEMA, "status": "verified_ready_not_timed",
        "replication_id": replication_id,
        "physical_machine_attestation": "physical_machine_not_vm",
        "physical_machine_facts": facts, "physical_machine_sha256": machine_sha,
        "python": sys.version, "runtime_executable_sha256": q64.file_sha256(Path(sys.executable)),
        "native": native_identity,
        "child_freeze_file_sha256": q64.file_sha256(run_dir / "CHILD_FREEZE.json"),
        "functional_preflight_file_sha256": q64.file_sha256(functional_path),
        "charged_costs_measured": False, "decision_cells_executed": 0,
        "prospective_cases_consumed": 0,
    }
    q64.write_json_exclusive(host_dir / "HOST_PREFLIGHT.json",
                             {**core, "preflight_sha256": q64.digest(core)})
    return {"status": "host_prepared", "replication_id": replication_id,
            "physical_machine_sha256": machine_sha,
            "native_library_sha256": native_identity["native_library_sha256"]}


def worker(run_dir: Path, replication_id: str, case_id: str, arm: str) -> int:
    # The supervisor has already verified the parent and child closures.  Replaying
    # the full 72-case generator in every fresh child would add uncharged lifecycle
    # work without strengthening the per-cell semantic check.
    frozen = q64.load_json(ROOT / q64.PARENT_RELATIVE)
    oracles = q64.load_json(run_dir / "ORACLES.json")
    preflight = q64.load_json(run_dir / replication_id / "HOST_PREFLIGHT.json")
    native = ROOT / preflight["native"]["native_library"]
    try:
        row = q64.execute_cell(frozen, oracles, native, case_id, arm)
        envelope = {"worker_status": "ok", "row": row}
        code = 0
    except Exception as exc:
        envelope = {"worker_status": "error", "error_type": type(exc).__name__,
                    "error": str(exc)}
        code = 1
    print(json.dumps(envelope, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return code


def run_host(run_dir: Path, replication_id: str, max_seconds: float) -> dict[str, Any]:
    child_path = run_dir / "CHILD_FREEZE.json"
    q64.verify_child_freeze(ROOT, child_path)
    frozen = q64.load_verified_parent(ROOT)
    host_dir = run_dir / replication_id
    preflight_path = host_dir / "HOST_PREFLIGHT.json"
    preflight = q64.load_json(preflight_path)
    if preflight.get("status") != "verified_ready_not_timed":
        raise ValueError("host preflight is not sealed")
    raw_path = host_dir / "RAW.jsonl"
    charged_path = host_dir / "CHARGED_COSTS.json"
    result_path = host_dir / "RESULT.json"
    if any(path.exists() for path in (raw_path, charged_path, result_path)):
        raise ValueError("refusing to overwrite a host attempt")
    charged = learning.measure_charged_cost_components(
        frozen["cohort"]["cases"], batches=21, repetitions=1000,
    )
    q64.write_json_exclusive(charged_path, charged)
    started = time.perf_counter()
    counts = {"ok": 0, "failed": 0, "timeout": 0, "refused": 0}
    rows = 0
    command_prefix = [sys.executable, str(Path(__file__).resolve()), "worker",
                      "--run-dir", str(run_dir), "--replication-id", replication_id]
    with raw_path.open("x", encoding="utf-8", newline="\n") as stream:
        for planned in q64.expected_schedule(frozen):
            if time.perf_counter() - started > max_seconds:
                raise TimeoutError("host attempt exceeded frozen wall bound; attempt is incomplete")
            command = [*command_prefix, "--case-id", planned["case_id"],
                       "--arm", planned["arm"]]
            lifecycle_started = time.perf_counter_ns()
            try:
                completed = subprocess.run(
                    command, cwd=ROOT, capture_output=True, text=True,
                    timeout=q64.CELL_TIMEOUT_SECONDS,
                )
                lifecycle_ns = time.perf_counter_ns() - lifecycle_started
                envelope = json.loads(completed.stdout) if completed.stdout.strip() else {}
                if completed.returncode == 0 and envelope.get("worker_status") == "ok":
                    row = envelope["row"]
                    counts["ok"] += 1
                else:
                    row = {
                        "schema": q64.RAW_SCHEMA, "status": "failed",
                        "reason": envelope.get("error", "worker_failed_without_envelope"),
                        "case_id": planned["case_id"], "arm": planned["arm"],
                        "query_count": q64.QUERY_COUNT, "timings_ns": {},
                        "output_sha256": None, "output_bytes": 0,
                        "exact_check_passed": False, "resources": {},
                        "memory_learning_measurement_performed": False,
                    }
                    counts["failed"] += 1
                row["worker_exit_code"] = completed.returncode
                row["worker_stderr"] = completed.stderr
            except subprocess.TimeoutExpired as exc:
                lifecycle_ns = time.perf_counter_ns() - lifecycle_started
                row = {
                    "schema": q64.RAW_SCHEMA, "status": "timeout",
                    "reason": "cell_timeout", "case_id": planned["case_id"],
                    "arm": planned["arm"], "query_count": q64.QUERY_COUNT,
                    "timings_ns": {}, "output_sha256": None, "output_bytes": 0,
                    "exact_check_passed": False, "resources": {},
                    "memory_learning_measurement_performed": False,
                    "worker_exit_code": None, "worker_stderr": str(exc),
                }
                counts["timeout"] += 1
            row.update(planned)
            row["fresh_process_lifecycle_ns"] = lifecycle_ns
            row["fresh_process_lifecycle_in_accounted_total"] = False
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False) + "\n")
            stream.flush()
            rows += 1
    result = {
        "schema": q64.HOST_RESULT_SCHEMA,
        "status": "complete" if rows == q64.EXPECTED_CELLS and counts["ok"] == rows else "incomplete",
        "replication_id": replication_id,
        "child_freeze_file_sha256": q64.file_sha256(child_path),
        "host_preflight_file_sha256": q64.file_sha256(preflight_path),
        "raw_file_sha256": q64.file_sha256(raw_path),
        "charged_cost_file_sha256": q64.file_sha256(charged_path),
        "expected_cells": q64.EXPECTED_CELLS, "completed_rows": rows,
        "counts": counts, "elapsed_seconds": time.perf_counter() - started,
        "labels_produced": False, "models_trained": 0,
        "prospective_cases_consumed": 0, "memory_learning_measurements": 0,
    }
    q64.write_json_exclusive(result_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "prepare-host"):
        item = sub.add_parser(name)
        item.add_argument("--run-dir", required=True, type=Path)
        item.add_argument("--replication-id", required=True)
        item.add_argument("--compiler", default="cc")
    item = sub.add_parser("run-host")
    item.add_argument("--run-dir", required=True, type=Path)
    item.add_argument("--replication-id", required=True)
    item.add_argument("--max-seconds", type=float, default=14400.0)
    item = sub.add_parser("worker")
    item.add_argument("--run-dir", required=True, type=Path)
    item.add_argument("--replication-id", required=True)
    item.add_argument("--case-id", required=True)
    item.add_argument("--arm", required=True, choices=learning.EXACT_ARMS)
    args = parser.parse_args()
    run_dir = _run_dir(args.run_dir)
    if args.command == "prepare": result = prepare(run_dir, args.replication_id, args.compiler)
    elif args.command == "prepare-host": result = prepare_host(run_dir, args.replication_id, args.compiler)
    elif args.command == "run-host": result = run_host(run_dir, args.replication_id, args.max_seconds)
    else: return worker(run_dir, args.replication_id, args.case_id, args.arm)
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result.get("status") not in {"incomplete", "failed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
