"""Small, frozen-source measurement-contract verification; not a speed ranking.

No network or cloud operations. Each pilot arm and reload gets a fresh Python
process. Heavy/native/full-corpus measurements belong to a later accepted run.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
AUDITOR = (
    "deliverables_n22_24/master_explainer_2026_08_03/"
    "use_case_benchmarks_2026-08-27/independence_audit_2026_08_27/artifact_audit.py"
)
SOURCES = (
    "scripts/cm_measurement_verify.py", "tests/test_cm_measurement_verify.py",
    "cm_ir.py", "bitset_backend.py", "cm_exprlib.py", "cmbench/__init__.py",
    "cmbench/output_budget.py", "scripts/cm_benchmark_provenance.py",
    "cmbench/reporting/__init__.py", "cmbench/reporting/provenance.py",
    "cmbench/reporting/summary_tables.py", AUDITOR,
)
ARMS = ("cm", "cse", "cnf")
MAX_K = 8
MAX_RECORD = 256 * 1024
SEED = 2026082801


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def validate_case(case):
    require(isinstance(case, dict), "case must be an object")
    k = case.get("k")
    require(type(k) is int and 0 <= k <= MAX_K, "verification width must be 0..8")
    clauses = case.get("clauses")
    require(isinstance(clauses, (list, tuple)) and len(clauses) <= 128, "clause limit")
    for clause in clauses:
        require(isinstance(clause, (list, tuple)) and len(clause) <= 32, "literal limit")
        require(all(type(lit) is int and 1 <= abs(lit) <= k for lit in clause), "invalid literal")
    return k, tuple(tuple(clause) for clause in clauses)


def scalar_vector(case):
    """Exhaustive scalar oracle, with no CM/BitSet imports or pattern cache."""
    k, clauses = validate_case(case)
    result = 0
    for assignment in range(1 << k):
        if all(any(bool(assignment & (1 << (abs(lit) - 1))) == (lit > 0)
                   for lit in clause) for clause in clauses):
            result |= 1 << assignment
    return result


def fixtures():
    rows = []
    rng = random.Random(SEED)
    for k in (0, 1, 5, 6, 7, 8):
        rows.extend((
            {"id": f"tautology-k{k}", "k": k, "clauses": []},
            {"id": f"contradiction-k{k}", "k": k, "clauses": [[]]},
        ))
        if k:
            rows.append({"id": f"boundary-k{k}", "k": k, "clauses": [[1, -k], [-1, k]]})
            for sample in range(4):
                clauses = [[rng.choice((-1, 1)) * rng.randint(1, k)
                            for _ in range(rng.randint(1, 4))] for _ in range(12)]
                clauses.extend(clauses[:4])
                rows.append({"id": f"random-k{k}-{sample}", "k": k, "clauses": clauses})
    return rows


def balanced_schedule(arms):
    require(len(set(arms)) == len(arms) and bool(arms), "unique nonempty arms required")
    arms = tuple(arms)
    forward = [arms[offset:] + arms[:offset] for offset in range(len(arms))]
    return forward + [tuple(reversed(row)) for row in forward]


def _expression(clauses):
    from cm_exprlib import And, Not, Or, Var

    def fold(nodes, operator):
        while len(nodes) > 1:
            nodes = [operator(nodes[i], nodes[i + 1]) if i + 1 < len(nodes) else nodes[i]
                     for i in range(0, len(nodes), 2)]
        return nodes[0]

    if not clauses:
        return Or(Var(0), Not(Var(0)))
    if any(not clause for clause in clauses):
        return And(Var(0), Not(Var(0)))
    return fold([fold([Var(abs(lit) - 1) if lit > 0 else Not(Var(abs(lit) - 1))
                       for lit in clause], Or) for clause in clauses], And)


def prepare(case, arm):
    """Return a computation, never a stored output; preparation is inside cold."""
    k, clauses = validate_case(case)
    require(arm in ARMS, "unsupported arm")
    if arm == "cnf":
        full = (1 << (1 << k)) - 1
        # Fresh input columns, not a module-global warm cache.
        columns = tuple(sum(1 << a for a in range(1 << k) if (a >> v) & 1) for v in range(k))

        def evaluate():
            result = full
            for clause in clauses:
                value = 0
                for lit in clause:
                    value |= columns[abs(lit) - 1] if lit > 0 else full ^ columns[abs(lit) - 1]
                result &= value
            return result

        return evaluate, None
    from bitset_backend import FlatProgram, compile_expr_cse, get_flat_program
    from cm_ir import compile_expr_to_cm_ir

    if k == 0:
        # The AST has no constant node. Explicit zero-width adapter, not a
        # claim that an absent free variable was compiled by the normal AST.
        program = FlatProgram(1, 0, ((0, "const", int(not any(not c for c in clauses))),), ())
    else:
        expr = _expression(clauses)
        program = (get_flat_program(compile_expr_to_cm_ir(expr, reuse_cache=False, persistent_cache=False))
                   if arm == "cm" else compile_expr_cse(expr, flatten=True))
    require(program.word_plan is None and not program.bound_cache, "prepared object already bound")
    return lambda: execute_flat(program, k), program


def execute_flat(program, k):
    from bitset_backend import PreparedFlatEvaluation, _bind_flat_program, _eval_prepared_flat, _eval_words
    order = tuple(f"x{i}" for i in range(k - 1, -1, -1))
    if k >= 6:
        return _eval_words(program, order, {})
    template, mask = _bind_flat_program(program, order, {})
    return _eval_prepared_flat(PreparedFlatEvaluation(program, template, mask, False))


def export_flat(program, k):
    return {"schema": "cm-flat-packed/v1", "k": k, "n_slots": program.n_slots,
            "root_slot": program.root_slot, "loads": program.loads, "ops": program.ops}


def import_flat(data):
    """Strict bounded structural load. Any optional cached answer is ignored."""
    from bitset_backend import FlatProgram
    require(isinstance(data, dict) and data.get("schema") == "cm-flat-packed/v1", "flat schema")
    k, slots, root = data.get("k"), data.get("n_slots"), data.get("root_slot")
    require(type(k) is int and 0 <= k <= MAX_K, "flat width")
    require(type(slots) is int and 1 <= slots <= 4096, "flat slot limit")
    require(type(root) is int and 0 <= root < slots, "flat root")
    loads, ops = data.get("loads"), data.get("ops")
    require(isinstance(loads, (tuple, list)) and isinstance(ops, (tuple, list)), "flat lists")
    require(len(loads) + len(ops) == slots, "flat completeness")
    assigned = set()

    def assign(slot):
        require(type(slot) is int and 0 <= slot < slots and slot not in assigned, "flat duplicate/invalid slot")
        assigned.add(slot)

    for load in loads:
        require(isinstance(load, (list, tuple)) and len(load) == 3, "flat load arity")
        slot, kind, value = load
        if kind == "const":
            require(type(value) is int and value in (0, 1), "flat constant")
        else:
            require(kind == "var" and isinstance(value, str) and value in {f"x{i}" for i in range(k)}, "flat variable")
        assign(slot)
    for operation in ops:
        require(isinstance(operation, (list, tuple)) and len(operation) == 3, "flat operation")
        slot, opcode, args = operation
        require(type(opcode) is int and opcode in range(6), "flat opcode")
        require(isinstance(args, (tuple, list)) and 1 <= len(args) <= 4096, "flat operands")
        require(all(type(arg) is int and arg in assigned for arg in args), "flat dependency")
        require((opcode != 0 or len(args) == 1) and (opcode not in (4, 5) or len(args) == 2), "flat operation arity")
        assign(slot)
    require(len(assigned) == slots and root in assigned, "flat incomplete program")
    return FlatProgram(slots, root, tuple(tuple(row) for row in loads),
                       tuple((slot, op, tuple(args)) for slot, op, args in ops)), k


def measure(case, arm, rounds=6, clock=time.perf_counter_ns):
    require(type(rounds) is int and 1 <= rounds <= 12, "bounded warm rounds required")
    start = clock()
    evaluate, program = prepare(case, arm)
    prepared_at = clock()
    first = evaluate()
    finished = clock()
    warm = []
    for _ in range(rounds):
        before = clock()
        value = evaluate()
        elapsed = clock() - before
        require(value == first, "warm output changed")
        warm.append(elapsed)
    return {
        "schema": "cm-measurement-contract-cell/v1", "arm": arm, "task": "complete_vector",
        "case_sha256": digest(case), "k": case["k"], "packed_hex": hex(first),
        "cold_prepare_ns": prepared_at - start, "cold_first_execution_ns": finished - prepared_at,
        "cold_total_ns": finished - start, "warm_recompute_ns": warm,
        "output_cache_used": False, "zero_width_adapter": case["k"] == 0 and arm != "cnf",
        "kernel": "direct_cnf_bigint" if arm == "cnf" else ("numpy_words" if case["k"] >= 6 else "bigint_flat"),
        "artifact": export_flat(program, case["k"]) if program is not None else None,
        "timings_for_contract_diagnostics_only": True,
    }


def independent_auditor(root=ROOT):
    spec = importlib.util.spec_from_file_location("measurement_independent_auditor", root / AUDITOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker(request):
    require(isinstance(request, dict), "worker request object required")
    mode = request.get("mode")
    if mode == "measure":
        validate_case(request["case"])
        # Imports are outside inner timings, but included in controller wall
        # latency. No oracle/CM evaluation precedes this process's cold call.
        import bitset_backend  # noqa: F401
        import cm_ir  # noqa: F401
        result = measure(request["case"], request["arm"])
    elif mode == "reload":
        name = request.get("artifact_file", "")
        require(isinstance(name, str) and re.fullmatch(r"cell-\d+-artifact\.json", name), "artifact filename")
        path = ROOT.parent / "artifacts" / name
        require(path.is_file() and not path.is_symlink(), "artifact missing/linked")
        import bitset_backend  # noqa: F401
        start = time.perf_counter_ns()
        with path.open("rb") as handle:
            raw = handle.read(MAX_RECORD + 1)
        require(len(raw) <= MAX_RECORD, "artifact byte limit")
        data = json.loads(raw)
        loaded = time.perf_counter_ns()
        program, k = import_flat(data)
        reconstructed = time.perf_counter_ns()
        value = execute_flat(program, k)
        finished = time.perf_counter_ns()
        result = {"schema": "cm-measurement-reload/v1", "packed_hex": hex(value),
                  "artifact_sha256": hashlib.sha256(raw).hexdigest(),
                  "file_read_decode_ns": loaded - start, "reconstruct_ns": reconstructed - loaded,
                  "first_query_ns": finished - reconstructed, "reload_total_ns": finished - start,
                  "cached_answer_used": False, "os_file_cache": "uncontrolled",
                  "timings_for_contract_diagnostics_only": True}
    else:
        raise ValueError("worker mode")
    result.update({"pid": os.getpid(), "interpreter": sys.executable, "source_root": str(ROOT)})
    return result


def append_record(path, record):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded(record).decode("utf-8") + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def run_cell(frozen, ledger, cell_id, request, expected, invoke=subprocess.run, timeout=15):
    append_record(ledger, {"cell_id": cell_id, "status": "running", "request_sha256": digest(request)})
    started = time.perf_counter_ns()
    row = {"cell_id": cell_id, "status": "error", "request_sha256": digest(request)}
    try:
        proc = invoke([sys.executable, "-B", str(frozen / "scripts/cm_measurement_verify.py"), "--worker"],
                      input=encoded(request) + b"\n", cwd=frozen, capture_output=True,
                      timeout=timeout, check=False)
        if proc.returncode:
            row.update(reason="worker_nonzero_exit", returncode=proc.returncode,
                       stderr_excerpt=proc.stderr[:4096].decode("utf-8", errors="replace"))
        elif len(proc.stdout) > MAX_RECORD:
            row.update(reason="oversized_worker_output")
        else:
            result = json.loads(proc.stdout)
            require(isinstance(result, dict), "worker result object")
            value = result.get("packed_hex")
            require(isinstance(value, str) and len(value) < MAX_RECORD, "worker output missing")
            if request.get("mode") == "measure":
                require(result.get("schema") == "cm-measurement-contract-cell/v1", "worker schema mismatch")
                require(result.get("arm") == request["arm"] and result.get("case_sha256") == digest(request["case"]), "worker identity mismatch")
                require(result.get("source_root") == str(frozen), "worker source mismatch")
                require(result.get("output_cache_used") is False, "unexpected answer cache")
                for field in ("cold_prepare_ns", "cold_first_execution_ns", "cold_total_ns"):
                    require(type(result.get(field)) is int and result[field] >= 0, "invalid cold timing")
                require(result["cold_total_ns"] == result["cold_prepare_ns"] + result["cold_first_execution_ns"], "cold phase accounting")
            elif request.get("mode") == "reload":
                require(result.get("schema") == "cm-measurement-reload/v1" and result.get("cached_answer_used") is False, "reload contract")
                require(result.get("source_root") == str(frozen), "reload source mismatch")
            row.update(status="ok" if int(value, 16) == expected else "mismatch", result=result)
    except subprocess.TimeoutExpired:
        row.update(status="timeout", reason="worker_deadline")
    except MemoryError:
        row.update(status="memory_limit", reason="controller_allocation_failure")
    except (OSError, ValueError, TypeError, KeyError):
        row.update(status="error", reason="invalid_or_missing_worker_result")
    row["controller_wall_ns"] = time.perf_counter_ns() - started
    append_record(ledger, row)
    return row


def read_ledger(path):
    """Retain interrupted cells rather than dropping their running records."""
    states = {}
    partial_tail = False
    lines = path.read_bytes().splitlines()
    for index, line in enumerate(lines):
        try:
            row = json.loads(line)
        except ValueError:
            require(index == len(lines) - 1, "corrupt ledger before tail")
            partial_tail = True
            break
        require(isinstance(row, dict) and isinstance(row.get("cell_id"), str), "invalid ledger row")
        prior = states.get(row["cell_id"])
        require((prior is None and row["status"] == "running") or
                (prior is not None and prior["status"] == "running" and row["status"] != "running"),
                "duplicate or invalid cell transition")
        states[row["cell_id"]] = row
    return {"cells": states, "partial_tail": partial_tail,
            "unfinished": [key for key, row in states.items() if row["status"] == "running"]}


def verify_snapshot(frozen, expected_manifest_sha256=None):
    raw = (frozen / "source_manifest.json").read_bytes()
    if expected_manifest_sha256 is not None:
        require(hashlib.sha256(raw).hexdigest() == expected_manifest_sha256, "snapshot manifest changed")
    manifest = json.loads(raw)
    require({row["path"] for row in manifest["files"]} == set(SOURCES), "snapshot allowlist mismatch")
    require(len(manifest["files"]) == len(SOURCES), "duplicate snapshot source")
    for row in manifest["files"]:
        path = frozen / row["path"]
        require(not path.is_symlink() and path.resolve().is_relative_to(frozen.resolve()), "linked snapshot source")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"], "snapshot source changed")
    return manifest


def pilot(output):
    from scripts.cm_benchmark_provenance import capture_source_snapshot
    output = output.resolve()
    require(output.is_relative_to(ROOT) and not output.exists(), "new project-local output required")
    observed = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}
    snapshot = capture_source_snapshot(ROOT, output / "source_snapshot", SOURCES)
    frozen = output / "source_snapshot"
    require(all(row["sha256"] == observed[row["path"]] for row in snapshot["files"]), "source changed during preparation")
    verify_snapshot(frozen, snapshot["manifest_sha256"])
    (output / "artifacts").mkdir()
    wanted = ("tautology-k0", "boundary-k6", "contradiction-k7", "random-k8-0")
    cases = [case for case in fixtures() if case["id"] in wanted]
    scheduled = []
    for number, (_case, arm) in enumerate(((case, arm) for case in cases for arm in ARMS), start=1):
        scheduled.append({"cell_id": f"cell-{number}", "mode": "measure", "case": _case["id"], "arm": arm})
        if arm != "cnf":
            scheduled.extend((
                {"cell_id": f"cell-{number}-independent", "mode": "independent_replay", "case": _case["id"], "arm": arm},
                {"cell_id": f"cell-{number}-reload", "mode": "reload", "case": _case["id"], "arm": arm},
            ))
    plan = {"schema": "cm-verification-pilot/v1", "seed": SEED, "cases": cases, "scheduled_cells": scheduled,
            "arms": ARMS, "warm_rounds": 6, "maximum_worker_seconds": 15,
            "arm_order": "fixed plumbing pilot; not counterbalanced performance evidence",
            "execution": "local_functional_verification", "performance_ranking_permitted": False,
            "source_manifest_sha256": snapshot["manifest_sha256"],
            "not_measured": ["native_CUDD", "ZDD", "d4", "peak_memory", "version_reuse", "real_corpus_performance"]}
    (output / "plan.json").write_bytes(encoded(plan) + b"\n")
    ledger = output / "cells.jsonl"
    auditor = independent_auditor(frozen)
    rows = []
    serial = 0
    for case in cases:
        expected = scalar_vector(case)
        for arm in ARMS:
            verify_snapshot(frozen, snapshot["manifest_sha256"])
            serial += 1
            row = run_cell(frozen, ledger, f"cell-{serial}", {"mode": "measure", "case": case, "arm": arm}, expected)
            rows.append(row)
            if arm == "cnf":
                continue
            if row["status"] != "ok":
                for suffix in ("independent", "reload"):
                    identity = f"cell-{serial}-{suffix}"
                    append_record(ledger, {"cell_id": identity, "status": "running"})
                    refusal = {"cell_id": identity, "status": "refused", "reason": "prerequisite_measurement_failed"}
                    append_record(ledger, refusal)
                    rows.append(refusal)
                continue
            artifact = row["result"]["artifact"]
            audit_id = f"cell-{serial}-independent"
            append_record(ledger, {"cell_id": audit_id, "status": "running"})
            try:
                passed = auditor.replay_flat(artifact) == expected
                audit_row = {"cell_id": audit_id, "status": "ok" if passed else "mismatch"}
            except (ValueError, AssertionError, KeyError, TypeError):
                audit_row = {"cell_id": audit_id, "status": "error", "reason": "independent_replay_rejected"}
            append_record(ledger, audit_row)
            rows.append(audit_row)
            if audit_row["status"] != "ok":
                reload_id = f"cell-{serial}-reload"
                append_record(ledger, {"cell_id": reload_id, "status": "running"})
                refusal = {"cell_id": reload_id, "status": "refused", "reason": "independent_replay_failed"}
                append_record(ledger, refusal)
                rows.append(refusal)
                continue
            name = f"cell-{serial}-artifact.json"
            (output / "artifacts" / name).write_bytes(encoded(artifact) + b"\n")
            rows.append(run_cell(frozen, ledger, f"cell-{serial}-reload", {"mode": "reload", "artifact_file": name}, expected))
    verify_snapshot(frozen, snapshot["manifest_sha256"])
    state = read_ledger(ledger)
    changes = [name for name in SOURCES if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != observed[name]]
    summary = {"schema": "cm-verification-pilot-result/v1", "status": "passed" if all(row["status"] == "ok" for row in rows) else "failed",
               "case_count": len(cases), "cell_count": len(rows), "outcomes": dict(Counter(row["status"] for row in rows)),
               "scheduled_cell_count": len(scheduled), "all_scheduled_cells_retained": {row["cell_id"] for row in scheduled} == set(state["cells"]),
               "unfinished_cells": state["unfinished"], "frozen_sources_unchanged": True,
               "concurrent_live_source_changes": changes, "cloud_run": False,
               "performance_ranking_permitted": False, "full_measurement_protocol_complete": False}
    (output / "summary.json").write_bytes(encoded(summary) + b"\n")
    files = sorted(path for path in output.rglob("*") if path.is_file())
    (output / "CHECKSUMS.sha256").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output).as_posix()}\n" for path in files), encoding="ascii")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--worker", action="store_true")
    group.add_argument("--pilot-output", type=Path)
    args = parser.parse_args()
    if args.worker:
        raw = sys.stdin.buffer.read(MAX_RECORD + 1)
        require(len(raw) <= MAX_RECORD, "request byte limit")
        result = worker(json.loads(raw))
    else:
        result = pilot(args.pilot_output)
    sys.stdout.buffer.write(encoded(result) + b"\n")
    return 0 if result.get("status", "passed") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
