"""Bounded native-adapter controls, never a speed ranking or native installer.

Only the explicit --sat-worker executes an installed solver. CUDD ordering
and d4 parsing are preparation contracts; no silent pure-Python fallback.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.machinery
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.cm_measurement_verify import (MAX_RECORD, digest, encoded, independent_auditor,
                                           require, scalar_vector, strict_json, validate_case)


def file_identity(path):
    path = Path(path)
    require(path.is_file() and not any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)),
            "native identity path missing or linked")
    with path.open("rb") as handle:
        data = handle.read((64 << 20) + 1)
    require(len(data) <= 64 << 20, "native identity file limit")
    return {"file": path.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def binding_identity(distribution, module, version):
    """Record actual extension identity; package metadata alone is insufficient."""
    result = {"distribution": distribution, "module": module, "required_version": version,
              "status": "refused", "fallback_used": False, "complete_build_identity": False}
    try:
        result["installed_version"] = importlib.metadata.version(distribution)
        spec = importlib.util.find_spec(module)
        if spec is None or not spec.origin:
            result["reason"] = "compiled_binding_missing"
        elif not any(spec.origin.endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES):
            result["reason"] = "module_is_not_compiled_extension"
        elif result["installed_version"] != version:
            result["reason"] = "unreviewed_wrapper_version"
        else:
            result.update(status="available", binding=file_identity(spec.origin),
                          reason="extension_identified_not_yet_executed")
    except importlib.metadata.PackageNotFoundError:
        result["reason"] = "distribution_missing"
    except (ImportError, OSError, ValueError):
        result["reason"] = "identity_unavailable"
    return result


def inventory():
    return {"cudd": binding_identity("dd", "dd.cudd", "0.6.0"),
            "zdd": binding_identity("dd", "dd.cudd_zdd", "0.6.0"),
            "sat": sat_identity(),
            "d4": {"status": "refused", "reason": "no_explicit_hash_pinned_binary_configured",
                   "fallback_used": False}}


def sat_identity():
    result = binding_identity("python-sat", "pysolvers", "1.8.dev20")
    if result["status"] == "available":
        spec = importlib.util.find_spec("pysat.solvers")
        require(spec is not None and spec.origin, "SAT wrapper unavailable")
        result["wrapper"] = file_identity(spec.origin)
    return result


def validate_sessions(sessions, k):
    require(isinstance(sessions, list) and 1 <= len(sessions) <= 16, "bounded session list required")
    for assumptions in sessions:
        require(isinstance(assumptions, list) and len(assumptions) <= k, "bounded assumptions required")
        require(all(type(lit) is int and 1 <= abs(lit) <= k for lit in assumptions), "assumption outside universe")
        require(len({abs(lit) for lit in assumptions}) == len(assumptions), "duplicate/conflicting assumptions")


def compatible(assignment, assumptions):
    return all(bool(assignment & (1 << (abs(lit) - 1))) == (lit > 0) for lit in assumptions)


def sat_contract(case, sessions, solver_factory):
    """Separate vector and session instances, preserving all declared variables.

    Factory injection in unit tests is simulated, not native evidence. Native
    entry requires a pinned installed extension in sat_worker(). No timing is
    accepted from these correctness controls, including scalar-oracle work.
    """
    k, clauses = validate_case(case)
    validate_sessions(sessions, k)
    expected = scalar_vector(case)

    def load(solver):
        # Do not infer k from max literal; unused variables belong to the task.
        # Explicit add_clause handles empty clauses (the installed wrapper's
        # bootstrap path indexes clause[0] and cannot accept an empty clause).
        for variable in range(1, k + 1):
            solver.add_clause([variable, -variable])
        for clause in clauses:
            solver.add_clause(list(clause))

    vector = 0
    with solver_factory() as solver:
        load(solver)
        for assignment in range(1 << k):
            assumptions = [i + 1 if assignment & (1 << i) else -(i + 1) for i in range(k)]
            answer = solver.solve(assumptions=assumptions)
            require(type(answer) is bool, "SAT returned unknown/nonboolean answer")
            vector |= int(answer) << assignment
    require(vector == expected, "SAT complete vector disagrees with scalar oracle")
    rows = []
    with solver_factory() as solver:
        load(solver)
        for assumptions in sessions:
            possible = [a for a in range(1 << k) if (expected >> a) & 1 and compatible(a, assumptions)]
            answer = solver.solve(assumptions=assumptions)
            require(type(answer) is bool and answer == bool(possible), "SAT session mismatch or unknown")
            row = {"assumptions": assumptions, "satisfiable": answer}
            if answer:
                model = solver.get_model()
                require(isinstance(model, list) and len(model) == k and
                        all(type(lit) is int and 1 <= abs(lit) <= k for lit in model) and
                        len({abs(lit) for lit in model}) == k, "SAT witness must cover declared universe")
                assignment = sum(1 << (lit - 1) for lit in model if lit > 0)
                require(assignment in possible, "SAT witness invalid")
                row["witness"] = model
            else:
                core = solver.get_core()
                if core is None and expected == 0:
                    core = []  # Empty base-unsatisfiable core, checked below.
                require(isinstance(core, list) and all(type(lit) is int and lit in assumptions for lit in core)
                        and len(set(core)) == len(core), "SAT core outside assumptions")
                require(not any((expected >> a) & 1 and compatible(a, core) for a in range(1 << k)),
                        "SAT core does not imply contradiction")
                row["core"] = core
                row["core_minimality_claimed"] = False
            rows.append(row)
    return {"case_sha256": digest(case), "k": k, "packed_hex": hex(vector), "sessions": rows,
            "vector_solve_calls": 1 << k, "session_solve_calls": len(sessions), "solver_instances": 2,
            "count_task_measured": False, "session_semantics": "one reused solver; assumptions replaced per call",
            "incr_constructor_flag": False, "warm_start_constructor_flag": False}


def sat_worker():
    raw = sys.stdin.buffer.read(MAX_RECORD + 1)
    require(len(raw) <= MAX_RECORD, "native request byte limit")
    request = strict_json(raw)
    require(isinstance(request, dict) and set(request) == {"identity", "cases"}, "native request fields")
    require(isinstance(request["cases"], list) and 1 <= len(request["cases"]) <= 8, "native case count")
    # Check every case before import/solver construction.
    for item in request["cases"]:
        require(isinstance(item, dict) and set(item) == {"case", "sessions"}, "native case fields")
        k, _ = validate_case(item["case"])
        validate_sessions(item["sessions"], k)
    before = sat_identity()
    require(before["status"] == "available" and before == request["identity"], "native identity mismatch")
    from pysat.solvers import Cadical195
    rows = [sat_contract(item["case"], item["sessions"], Cadical195) for item in request["cases"]]
    require(sat_identity() == before, "native binding changed during probe")
    return {"schema": "cm-native-sat-contract/v1", "status": "passed", "pid": os.getpid(),
            "request_sha256": digest(request), "identity": before, "adapter": "pysat.Cadical195",
            "rows": rows, "performance_ranking_permitted": False, "native_execution": True,
            "source_root": str(ROOT)}


def validate_sat_result(result, request, frozen, observed_pids):
    fields = {"schema", "status", "pid", "request_sha256", "identity", "adapter", "rows",
              "performance_ranking_permitted", "native_execution", "source_root"}
    require(isinstance(result, dict) and set(result) == fields, "SAT result fields")
    require(result["schema"] == "cm-native-sat-contract/v1" and result["status"] == "passed" and
            result["adapter"] == "pysat.Cadical195" and result["request_sha256"] == digest(request) and
            digest(result["identity"]) == digest(request["identity"]) and type(result["pid"]) is int and result["pid"] > 0 and
            result["pid"] in observed_pids and result["source_root"] == str(frozen) and
            result["performance_ranking_permitted"] is False and result["native_execution"] is True,
            "SAT worker identity/scope mismatch")
    require(isinstance(result["rows"], list) and len(result["rows"]) == len(request["cases"]), "SAT case cardinality mismatch")
    row_fields = {"case_sha256", "k", "packed_hex", "sessions", "vector_solve_calls", "session_solve_calls",
                  "solver_instances", "count_task_measured", "session_semantics", "incr_constructor_flag",
                  "warm_start_constructor_flag"}
    for actual, item in zip(result["rows"], request["cases"]):
        k = item["case"]["k"]
        expected = scalar_vector(item["case"])
        require(isinstance(actual, dict) and set(actual) == row_fields, "SAT row fields")
        require(actual["case_sha256"] == digest(item["case"]) and type(actual["k"]) is int and actual["k"] == k and
                actual["packed_hex"] == hex(expected) and actual["count_task_measured"] is False and
                actual["incr_constructor_flag"] is False and actual["warm_start_constructor_flag"] is False and
                actual["session_semantics"] == "one reused solver; assumptions replaced per call", "SAT row scope mismatch")
        for field, wanted in (("vector_solve_calls", 1 << k), ("session_solve_calls", len(item["sessions"])), ("solver_instances", 2)):
            require(type(actual[field]) is int and actual[field] == wanted, "SAT call accounting")
        require(isinstance(actual["sessions"], list) and len(actual["sessions"]) == len(item["sessions"]), "SAT sessions missing")
        for session, assumptions in zip(actual["sessions"], item["sessions"]):
            require(isinstance(session, dict) and session.get("assumptions") == assumptions, "SAT session identity")
            validate_sessions([session["assumptions"]], k)  # JSON true must not alias literal 1.
            possible = [a for a in range(1 << k) if (expected >> a) & 1 and compatible(a, assumptions)]
            require(type(session.get("satisfiable")) is bool and session["satisfiable"] == bool(possible), "SAT session answer")
            if possible:
                require(set(session) == {"assumptions", "satisfiable", "witness"}, "SAT witness fields")
                model = session["witness"]
                require(isinstance(model, list) and len(model) == k and
                        all(type(lit) is int and 1 <= abs(lit) <= k for lit in model) and
                        len({abs(lit) for lit in model}) == k, "SAT witness universe")
                require(sum(1 << (lit - 1) for lit in model if lit > 0) in possible, "SAT witness does not satisfy case")
            else:
                require(set(session) == {"assumptions", "satisfiable", "core", "core_minimality_claimed"} and
                        session["core_minimality_claimed"] is False, "SAT core fields")
                core = session["core"]
                require(isinstance(core, list) and all(type(lit) is int and lit in assumptions for lit in core) and
                        len(set(core)) == len(core), "SAT core subset")
                require(not any((expected >> a) & 1 and compatible(a, core) for a in range(1 << k)), "SAT core invalid")


def cudd_order_contract(case, mode, manager_factory, export_graph, clock=time.perf_counter_ns):
    """Prepared dd 0.6.0 contract, with injectable manager/export for controls.

    export_graph must serialize the given measured manager/root. Plain
    `BDD.reorder()` is GROUP sifting in this wrapper, not ordinary sifting.
    Manager creation, construction, reordering and graph export are charged.
    This is not a native execution entry point or a complete timing protocol.
    """
    k, clauses = validate_case(case)
    require(mode in {"fixed", "group_sift"}, "unreviewed CUDD reorder mode")
    order = {f"x{i}": i for i in range(k)}
    begin = clock()
    manager = manager_factory()
    manager.configure(reordering=False)
    require(manager.configure()["reordering"] is False, "automatic reordering still enabled")
    manager.declare(*order)
    root = manager.true
    for clause in clauses:
        value = manager.false
        for literal in clause:
            term = manager.var(f"x{abs(literal) - 1}")
            value |= term if literal > 0 else ~term
        root &= value
    built = clock()
    before = dict(manager.var_levels)
    stats_before = manager.statistics()
    require(before == order and stats_before["n_reorderings"] == 0, "unexpected construction order/search")
    if mode == "group_sift":
        manager.reorder()
    ordered = clock()
    after = dict(manager.var_levels)
    stats_after = manager.statistics()
    require(set(after) == set(order) and set(after.values()) == set(range(k)), "invalid reordered variable map")
    require(manager.configure()["reordering"] is False, "automatic reordering enabled after search")
    require(type(stats_after["n_reorderings"]) is int and stats_after["n_reorderings"] >= 0, "invalid reorder counter")
    if mode == "fixed":
        require(after == before and stats_after["n_reorderings"] == 0, "fixed order changed")
    else:
        require(stats_after["n_reorderings"] >= 1, "group sift did not run")
    graph = export_graph(manager, root)
    exported = clock()
    require(isinstance(graph, dict) and graph.get("level_of_var") == after, "export is not reordered manager graph")
    require(len(encoded(graph)) <= MAX_RECORD, "BDD artifact byte limit")
    require(independent_auditor().replay_bdd(graph, k) == scalar_vector(case), "BDD graph replay mismatch")
    phases = {"manager_and_build_ns": built - begin, "order_search_ns": ordered - built,
              "export_ns": exported - ordered, "cold_total_ns": exported - begin}
    require(all(type(value) is int and 0 <= value <= 60_000_000_000 for value in phases.values()), "CUDD clock invalid")
    return {"mode": mode, "reorder_method": "none" if mode == "fixed" else "CUDD_REORDER_GROUP_SIFT",
            "order_before": before, "order_after": after, "reorderings_before": stats_before["n_reorderings"],
            "reorderings_after": stats_after["n_reorderings"], "graph": graph, **phases,
            "task": "construct_and_export_graph", "performance_ranking_permitted": False}


def parse_d4_count(raw, k):
    """Strict unweighted, nonprojected legacy d4 `s <integer>` output only."""
    require(type(k) is int and 0 <= k <= 8, "d4 bounded universe required")
    require(isinstance(raw, bytes) and len(raw) <= MAX_RECORD, "d4 output limit")
    lines = raw.decode("ascii").splitlines()
    answers = []
    for line in lines:
        if not line.strip() or line.startswith("c "):
            continue
        match = re.fullmatch(r"s (0|[1-9][0-9]{0,2})", line)
        require(match is not None, "unsupported d4 output dialect or noninteger count")
        answers.append(int(match[1]))
    require(len(answers) == 1 and answers[0] <= 1 << k, "ambiguous/out-of-universe d4 count")
    return {"task": "exact_count", "count": answers[0], "k": k, "output_contract": "scalar_count_only",
            "lifecycle": "cold_cli_including_process_start", "complete_vector_measured": False,
            "ddnnf_serialization_measured": False}


def d4_count_command(executable, expected_sha256, input_path, input_sha256, case):
    """Prepare only. No execution, PATH search, downloads or option passthrough."""
    k, clauses = validate_case(case)
    executable, input_path = Path(executable), Path(input_path)
    require(executable.is_absolute() and input_path.is_absolute(), "explicit absolute d4 paths required")
    require(all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                for value in (expected_sha256, input_sha256)), "pinned d4/input SHA-256 required")
    binary = file_identity(executable)
    require(binary["sha256"] == expected_sha256, "d4 binary changed")
    data = (f"p cnf {k} {len(clauses)}\n" + "".join(" ".join(map(str, clause)) + (" " if clause else "") + "0\n"
                                                        for clause in clauses)).encode("ascii")
    require(hashlib.sha256(data).hexdigest() == input_sha256 and
            file_identity(input_path)["sha256"] == input_sha256, "d4 input identity/universe mismatch")
    return {"command": [str(executable), "-mc", str(input_path)], "binary": binary,
            "task": "exact_count", "input_sha256": input_sha256, "k": k,
            "execution_authorized_by_this_function": False}


def parse_d4_competition_count(raw, k):
    """Strict parser for the pinned d4v2 competition exact-count dialect."""
    require(type(k) is int and 1 <= k <= 8, "d4 competition universe required")
    require(isinstance(raw, bytes) and len(raw) <= MAX_RECORD, "d4 output limit")
    statuses, answers = [], []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        if line == "c":
            continue
        if line in {"s SATISFIABLE", "s UNSATISFIABLE"}:
            statuses.append(line.removeprefix("s "))
            continue
        exact = re.fullmatch(r"c s exact (?:arb|quadruple) int (0|[1-9][0-9]{0,2})", line)
        if exact:
            answers.append(int(exact[1]))
            continue
        if re.fullmatch(
            r"time: [0-9.eE+-]+/[0-9.eE+-]+  number: [0-9]+/[0-9]+", line
        ):
            continue
        require(line.startswith("c "), "unsupported d4 competition output dialect")
    require(len(statuses) == 1 and len(answers) == 1 and answers[0] <= 1 << k,
            "ambiguous/out-of-universe d4 competition count")
    require((statuses[0] == "UNSATISFIABLE") == (answers[0] == 0),
            "d4 competition status/count mismatch")
    return {"task": "exact_count", "count": answers[0], "k": k,
            "output_contract": "d4v2_competition_exact_integer",
            "lifecycle": "cold_cli_including_process_start", "complete_vector_measured": False,
            "ddnnf_serialization_measured": False}


def d4_competition_count_command(executable, expected_sha256, input_path, input_sha256, case):
    """Prepare the exact pinned d4v2 competition count command without executing it."""
    row = d4_count_command(executable, expected_sha256, input_path, input_sha256, case)
    require(row["k"] >= 1, "d4 competition requires a positive-width universe")
    return {**row, "command": [str(Path(executable)), str(Path(input_path))],
            "cli_contract": "d4v2_competition_positional_input"}


def probe_cases():
    from scripts.cm_measurement_verify import fixtures
    cases = [{"id": "true-k0", "k": 0, "clauses": []},
             {"id": "false-k0", "k": 0, "clauses": [[]]},
             {"id": "unused-variable-k3", "k": 3, "clauses": [[1]]},
             {"id": "conflict-k2", "k": 2, "clauses": [[1], [-1]]},
             {"id": "satisfiable-k8", "k": 8, "clauses": [[1, -2], [2, 3], [-3, 4], [5, -6], [7, 8]]}]
    cases += [case for case in fixtures() if case["id"] in {"boundary-k6", "random-k8-0"}]
    return [{"case": case, "sessions": [[], [], []] if case["k"] == 0 else
             [[], [1], [-1], [], [case["k"]], [-case["k"]], []]} for case in cases]


def probe(output):
    from scripts.cm_benchmark_provenance import capture_source_snapshot
    from scripts.cm_measurement_verify import SOURCES
    from scripts.cm_process_supervisor import run
    output = output.absolute()
    require(output.resolve().is_relative_to(ROOT) and not output.exists() and
            not any(p.is_symlink() or p.is_junction() for p in (output, *output.parents)),
            "new nonlinked project-local probe output required")
    sources = (*SOURCES, "scripts/cm_native_contracts.py", "tests/test_cm_native_contracts.py")
    before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources}
    snapshot = capture_source_snapshot(ROOT, output / "source_snapshot", sources)
    frozen = output / "source_snapshot"
    require(all(row["sha256"] == before[row["path"]] for row in snapshot["files"]), "source changed before freeze")
    available = inventory()
    request = {"identity": available["sat"], "cases": probe_cases()}
    plan = {"schema": "cm-native-contract-probe/v1", "request": request, "inventory": available,
            "performance_ranking_permitted": False, "source_manifest_sha256": snapshot["manifest_sha256"],
            "not_executed": ["native_CUDD", "native_ZDD", "native_d4", "real_corpus_benchmark"]}
    (output / "plan.json").write_bytes(encoded(plan) + b"\n")
    row = {"status": "refused", "reason": available["sat"]["reason"]}
    # Keep a running receipt visible even if this controller is interrupted.
    (output / "started.json").write_bytes(encoded({"status": "running", "request_sha256": digest(request)}) + b"\n")
    if available["sat"]["status"] == "available":
        proc = run([sys.executable, "-B", str(frozen / "scripts/cm_native_contracts.py"), "--sat-worker"],
                   input=encoded(request), cwd=frozen)
        row = {"status": proc.status, "reason": proc.reason, "supervision": proc.resources,
               "controller_wall_ns": proc.wall_ns, "launched_pid": proc.pid}
        if proc.status == "ok":
            try:
                result = strict_json(proc.stdout)
                require(proc.resources["cleanup_verified"] and proc.resources["streams_closed"] and
                        proc.resources["attached_before_resume"], "SAT supervision incomplete")
                validate_sat_result(result, request, frozen, proc.resources["observed_job_pids"])
                row.update(status="passed", result=result, worker_pid_observed_in_owned_job=True)
            except (ValueError, KeyError, TypeError):
                row.update(status="error", reason="invalid_native_worker_result")
        elif proc.stderr:
            row["stderr_excerpt"] = proc.stderr[:4096].decode("utf-8", errors="replace")
    unchanged = (hashlib.sha256((frozen / "source_manifest.json").read_bytes()).hexdigest() == snapshot["manifest_sha256"] and
                 all(hashlib.sha256((frozen / name).read_bytes()).hexdigest() == value for name, value in before.items()))
    live_changes = [name for name, value in before.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value]
    summary = {"schema": "cm-native-contract-probe-result/v1", "sat": row, "inventory": available,
               "status": "completed" if unchanged and not live_changes and row["status"] in {"passed", "refused"} else "failed",
               "frozen_sources_unchanged": unchanged, "concurrent_source_changes": live_changes,
               "performance_ranking_permitted": False, "cloud_run": False,
               "native_CUDD_executed": False, "native_ZDD_executed": False, "native_d4_executed": False}
    (output / "summary.json").write_bytes(encoded(summary) + b"\n")
    files = sorted(path for path in output.rglob("*") if path.is_file())
    (output / "CHECKSUMS.sha256").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output).as_posix()}\n" for path in files), encoding="ascii")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--sat-worker", action="store_true")
    group.add_argument("--probe-output", type=Path)
    args = parser.parse_args()
    result = sat_worker() if args.sat_worker else probe(args.probe_output) if args.probe_output else inventory()
    sys.stdout.buffer.write(encoded(result) + b"\n")
    return 1 if result.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
