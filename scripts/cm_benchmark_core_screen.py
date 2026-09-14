"""Frozen bounded screen for counting, biology, and affine benchmark lanes."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "cm-benchmark-core-screen/v1"
PLAN_SCHEMA = "cm-benchmark-core-screen-plan/v1"
CAMPAIGN = "cm-mega-prelaunch-20260914-008"
REPETITIONS = 3
CELL_SECONDS = 60
CAMPAIGN_SECONDS = 3600


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def append(path, value):
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(canonical(value).decode() + "\n")


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _quantiles(rows, count, key):
    ordered = sorted(rows, key=key)
    if len(ordered) <= count:
        return ordered
    indices = [round(index * (len(ordered) - 1) / (count - 1)) for index in range(count)]
    return [ordered[index] for index in indices]


def _case(row):
    return {
        "case_id": row["case_id"],
        "input_sha256": row["expected_sha256"],
        "path": "inputs/" + row["group"] + "/" + Path(row["path"]).name,
        "metadata": row["metadata"],
    }


def build_plan(admission_path):
    admission_path = Path(admission_path)
    admission = json.loads(admission_path.read_text(encoding="utf-8"))
    admitted = [row for row in admission["rows"] if row.get("state") == "admitted"]

    exact = [row for row in admitted if row.get("kind") == "mc"
             and row["metadata"].get("declared_support_variables") == 0]
    exact = _quantiles(exact, 8, lambda row: (row["metadata"]["variables"], row["case_id"]))
    projected = [row for row in admitted if row.get("kind") == "pmc"]
    projected = _quantiles(projected, 8, lambda row: (
        row["metadata"]["projection_variables"], row["metadata"]["variables"], row["case_id"]))

    unique_biology = {}
    for row in admitted:
        if row.get("kind") == "bnet" and row["metadata"].get("functions", 10**9) <= 16:
            unique_biology.setdefault(row["path"], row)
    biology = _quantiles(list(unique_biology.values()), 12,
                         lambda row: (row["metadata"]["functions"], row["case_id"]))

    affine = [row for row in admitted if row.get("kind") == "alist"]
    affine = _quantiles(affine, 8, lambda row: (
        row["metadata"].get("columns", 0), row["metadata"].get("rows", 0), row["case_id"]))

    lanes = [
        ("exact_count", exact, ("ganak", "d4"), "paired_native_incumbents"),
        ("projected_count", projected, ("ganak_projected",), "unpaired_exact_native"),
        ("biology_fixed_points", biology, ("bnet_cm_scalar", "biodivine_aeon"), "paired"),
        ("affine_solution_count", affine, ("cm_packed_elimination", "sparse_set_elimination"), "paired"),
    ]
    cells = []
    case_rows = []
    for lane, rows, arms, assurance in lanes:
        for row in rows:
            case = _case(row)
            case["lane"] = lane
            case["assurance"] = assurance
            case_rows.append(case)
            for repetition in range(REPETITIONS):
                order = list(arms)
                if int(digest_bytes(f"{lane}:{case['case_id']}:{repetition}".encode())[:2], 16) & 1:
                    order.reverse()
                for position, arm in enumerate(order):
                    identity = {
                        "campaign_id": CAMPAIGN, "lane": lane, "case_id": case["case_id"],
                        "arm": arm, "repetition": repetition, "position": position,
                        "input_sha256": case["input_sha256"],
                    }
                    cells.append({**identity, "cell_id": digest_bytes(canonical(identity))})
    body = {
        "schema": PLAN_SCHEMA,
        "campaign_id": CAMPAIGN,
        "created_utc": utc_now(),
        "selection": "pre-outcome deterministic quantiles by declared size; no timing input",
        "repetitions": REPETITIONS,
        "cell_seconds": CELL_SECONDS,
        "campaign_seconds": CAMPAIGN_SECONDS,
        "cases": sorted(case_rows, key=lambda row: (row["lane"], row["case_id"])),
        "cells": cells,
        "not_run_policy": {
            "campaign_boundary": "remaining cells recorded not_run when stop-admission time binds",
            "cell_boundary": "timeout, exception, wrong answer, and unavailable are distinct",
            "projected_count": "Ganak measurements are unpaired and cannot support a CM speedup claim",
        },
    }
    body["plan_sha256"] = digest_bytes(canonical(body))
    return body


def _rhs(case_id, count):
    raw = hashlib.shake_256(("cm-affine-rhs:" + case_id).encode()).digest((count + 7) // 8)
    return tuple((raw[index // 8] >> (index % 8)) & 1 for index in range(count))


def sparse_affine_count(rows, rhs, width):
    pivots = {}
    for mask, value in zip(rows, rhs):
        support = {index for index in range(width) if mask & (1 << index)}
        value = int(value)
        while support:
            pivot = max(support)
            if pivot not in pivots:
                pivots[pivot] = (support, value)
                break
            other, other_value = pivots[pivot]
            support = support.symmetric_difference(other)
            value ^= other_value
        if not support and value:
            return 0
    return 1 << (width - len(pivots))


def execute(request):
    path = Path(request["root"]) / request["case"]["path"]
    if not path.is_file() or path.is_symlink() or digest(path) != request["case"]["input_sha256"]:
        raise ValueError("input identity mismatch")
    lane, arm = request["cell"]["lane"], request["cell"]["arm"]
    started_wall, started_cpu = time.perf_counter_ns(), time.process_time_ns()
    native = None
    if lane == "exact_count":
        from cmbench.backends.native_count import run_d4, run_ganak
        native = (run_ganak(path, mode="exact", executable=os.environ.get("CM_GANAK", "ganak"),
                            timeout_seconds=CELL_SECONDS)
                  if arm == "ganak" else
                  run_d4(path, executable=os.environ.get("CM_D4", "d4-counter"), timeout_seconds=CELL_SECONDS))
        value = native.count
    elif lane == "projected_count":
        from cmbench.backends.native_count import run_ganak
        native = run_ganak(path, mode="projected", executable=os.environ.get("CM_GANAK", "ganak"),
                           timeout_seconds=CELL_SECONDS)
        value = native.count
    elif lane == "biology_fixed_points":
        from cmbench.biology_bnet import aeon_fixed_point_count, parse_bnet, scalar_fixed_point_count
        value = (scalar_fixed_point_count(parse_bnet(path.read_text(encoding="utf-8")), max_variables=16)
                 if arm == "bnet_cm_scalar" else aeon_fixed_point_count(path))
    elif lane == "affine_solution_count":
        from cmbench.backends.affine_constraints import AffineConstraintPlan, parse_alist
        width, rows = parse_alist(path.read_text(encoding="utf-8"))
        rhs = _rhs(request["case"]["case_id"], len(rows))
        names = tuple(f"x{index:05d}" for index in range(width))
        value = (AffineConstraintPlan(rows, rhs, names).count()
                 if arm == "cm_packed_elimination" else sparse_affine_count(rows, rhs, width))
    else:
        raise ValueError("unknown lane")
    wall_ns = time.perf_counter_ns() - started_wall
    cpu_ns = time.process_time_ns() - started_cpu
    record = {
        "schema": SCHEMA, "status": "ok", "cell": request["cell"],
        "value": str(value), "value_sha256": digest_bytes(str(value).encode()),
        "wall_ns": wall_ns, "cpu_ns": cpu_ns,
        "native_stdout_sha256": digest_bytes(native.stdout.encode()) if native else None,
        "native_stderr_sha256": digest_bytes(native.stderr.encode()) if native else None,
    }
    try:
        import resource
        record["rss_highwater_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except ImportError:
        record["rss_highwater_kib"] = None
    return record


def worker(request_path):
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))
        resource.setrlimit(resource.RLIMIT_CPU, (CELL_SECONDS, CELL_SECONDS + 2))
        resource.setrlimit(resource.RLIMIT_FSIZE, (16 << 20, 16 << 20))
    except ImportError:
        pass
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    write_new(request["result_path"], execute(request))


def _load_terminal(ledger):
    terminal = {}
    if not ledger.exists():
        return terminal
    for line in ledger.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        terminal[row["cell_id"]] = row
    return terminal


def _summarize(plan, rows):
    by_lane = defaultdict(list)
    by_pair = defaultdict(dict)
    for row in rows:
        by_lane[row["lane"]].append(row)
        if row["status"] == "ok":
            key = (row["lane"], row["case_id"], row["repetition"])
            by_pair[key][row["arm"]] = row
    mismatches = []
    ratios = defaultdict(list)
    pair_contracts = {
        "exact_count": ("ganak", "d4"),
        "biology_fixed_points": ("bnet_cm_scalar", "biodivine_aeon"),
        "affine_solution_count": ("cm_packed_elimination", "sparse_set_elimination"),
    }
    for key, arms in by_pair.items():
        lane = key[0]
        if lane not in pair_contracts:
            continue
        left, right = pair_contracts[lane]
        if left in arms and right in arms:
            if arms[left]["value_sha256"] != arms[right]["value_sha256"]:
                mismatches.append({"lane": lane, "case_id": key[1], "repetition": key[2]})
            elif arms[left]["wall_ns"] > 0:
                ratios[lane].append(arms[right]["wall_ns"] / arms[left]["wall_ns"])
    comparisons = {}
    for lane, values in ratios.items():
        comparisons[lane] = {
            "ratio_definition": "second declared arm wall time divided by first declared arm wall time",
            "paired_cells": len(values),
            "median_ratio": statistics.median(values),
            "geometric_mean_ratio": math.exp(sum(math.log(value) for value in values) / len(values)),
        }
    return {
        "schema": "cm-benchmark-core-screen-summary/v1",
        "status": "failed_correctness" if mismatches else "complete",
        "plan_sha256": plan["plan_sha256"],
        "cells": len(rows),
        "status_counts": {status: sum(row["status"] == status for row in rows)
                          for status in sorted({row["status"] for row in rows})},
        "lane_counts": {lane: len(items) for lane, items in sorted(by_lane.items())},
        "correctness_mismatches": mismatches,
        "comparisons": comparisons,
        "projected_count_claim_boundary": "unpaired Ganak exact measurements; no CM speedup claim",
    }


def run_campaign(plan_path, root, output):
    plan_path, root, output = Path(plan_path), Path(root).resolve(), Path(output)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    validate_plan(plan)
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / "PLAN.json", plan)
    (output / "cells").mkdir()
    ledger = output / "ledger.jsonl"
    cases = {row["case_id"]: row for row in plan["cases"]}
    started = time.monotonic()
    for index, cell in enumerate(plan["cells"]):
        if time.monotonic() - started >= plan["campaign_seconds"]:
            append(ledger, {**cell, "status": "not_run", "reason": "campaign_stop_admission"})
            continue
        folder = output / "cells" / f"{index:04d}"
        folder.mkdir()
        result_path = folder / "result.json"
        request = {"root": str(root), "case": cases[cell["case_id"]], "cell": cell,
                   "result_path": str(result_path)}
        request_path = folder / "request.json"
        write_new(request_path, request)
        before = time.perf_counter_ns()
        with (folder / "worker.log").open("xb") as log:
            process = subprocess.Popen(
                [sys.executable, "-B", str(Path(__file__)), "worker", "--request", str(request_path)],
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
            try:
                code = process.wait(timeout=plan["cell_seconds"] + 5)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                code = process.wait(timeout=5)
        parent_wall_ns = time.perf_counter_ns() - before
        if timed_out:
            row = {**cell, "status": "timeout", "parent_wall_ns": parent_wall_ns}
        elif code or not result_path.exists():
            row = {**cell, "status": "worker_error", "exit_code": code, "parent_wall_ns": parent_wall_ns,
                   "log_sha256": digest(folder / "worker.log")}
        else:
            row = {**cell, **json.loads(result_path.read_text(encoding="utf-8")),
                   "parent_wall_ns": parent_wall_ns}
        append(ledger, row)
        if (index + 1) % 10 == 0:
            print(json.dumps({"completed": index + 1, "total": len(plan["cells"])}), flush=True)
    rows = list(_load_terminal(ledger).values())
    summary = _summarize(plan, rows)
    summary["elapsed_seconds"] = time.monotonic() - started
    write_new(output / "SUMMARY.json", summary)
    return summary


def validate_plan(plan):
    if plan.get("schema") != PLAN_SCHEMA or plan.get("campaign_id") != CAMPAIGN:
        raise ValueError("plan schema or campaign")
    body = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if digest_bytes(canonical(body)) != plan.get("plan_sha256"):
        raise ValueError("plan digest")
    cases = {row["case_id"]: row for row in plan.get("cases", [])}
    if len(cases) != len(plan.get("cases", [])) or len(plan.get("cells", [])) != 192:
        raise ValueError("plan cardinality")
    for cell in plan["cells"]:
        identity = {key: cell[key] for key in (
            "campaign_id", "lane", "case_id", "arm", "repetition", "position", "input_sha256")}
        if cell["case_id"] not in cases or digest_bytes(canonical(identity)) != cell["cell_id"]:
            raise ValueError("cell identity")


def verify(plan_path, output):
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    validate_plan(plan)
    rows = list(_load_terminal(Path(output) / "ledger.jsonl").values())
    if len(rows) != len(plan["cells"]):
        raise ValueError("terminal ledger cardinality")
    summary = _summarize(plan, rows)
    stored = json.loads((Path(output) / "SUMMARY.json").read_text(encoding="utf-8"))
    for key in ("status", "plan_sha256", "cells", "status_counts", "lane_counts",
                "correctness_mismatches", "comparisons", "projected_count_claim_boundary"):
        if summary[key] != stored.get(key):
            raise ValueError("summary mismatch: " + key)
    return {"status": "passed", "cells": len(rows), "correctness_mismatches": len(summary["correctness_mismatches"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--admission", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    worker_parser = sub.add_parser("worker")
    worker_parser.add_argument("--request", type=Path, required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--plan", type=Path, required=True)
    run_parser.add_argument("--root", type=Path, required=True)
    run_parser.add_argument("--output", type=Path, required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--plan", type=Path, required=True)
    verify_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "freeze":
        write_new(args.output, build_plan(args.admission))
        result = {"status": "frozen", "output": str(args.output),
                  "sha256": digest(args.output)}
    elif args.action == "worker":
        worker(args.request)
        return 0
    elif args.action == "run":
        result = run_campaign(args.plan, args.root, args.output)
    else:
        result = verify(args.plan, args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
