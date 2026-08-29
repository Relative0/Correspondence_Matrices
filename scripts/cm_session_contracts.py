"""Matched bounded session/version correctness pilot; no performance ranking.

Fresh and reused CM, CSE, direct-CNF and installed CaDiCaL get identical
requests. Historical conditioned slices remain distinct from synthetic edits.
No installs, network, cloud operations or production-default changes.
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
from contextlib import contextmanager
import csv
import hashlib
import io
import os
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import cm_measurement_verify as base
from scripts import cm_native_contracts as native

require, encoded, digest = base.require, base.encoded, base.digest
SEED = 2026082802
BACKENDS = ("cm", "cse", "cnf", "sat")
LIFECYCLES = ("fresh", "reused")
TASKS = ("partial_configuration", "version_delta")
HISTORY = ("deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/runs/"
           "configuration-fm-version-delta-full21-2026-08-27/cases.jsonl")
HISTORY_SHA256 = "3a4a394f458e0064994b4339858401e523f8dea836a3a697120f9db83299ef0e"
ADMISSIONS = HISTORY.rsplit("/", 1)[0] + "/admissions.csv"
ADMISSIONS_SHA256 = "9afbf841866b26e6bc0615160d1e64c6f627904a8729fdd9837c809fccbb113a"
SOURCE_COMMIT = "afa60ee2c836e7bdc4068e0f4f128ea31158d2ad"
KNOWN_CHANGE_CASE = "soletta@2015-06-26_18-38-56->2015-06-26_23-03-00|incidence|k8"
SOURCES = (*base.SOURCES, "scripts/cm_native_contracts.py", "tests/test_cm_native_contracts.py",
           "scripts/cm_session_contracts.py", "tests/test_cm_session_contracts.py", HISTORY, ADMISSIONS)


def validate_scenario(scenario):
    require(isinstance(scenario, dict) and set(scenario) == {"id", "k", "feature_names", "versions", "source"}, "scenario fields")
    require(isinstance(scenario["id"], str) and 1 <= len(scenario["id"]) <= 256, "scenario identity")
    k = scenario["k"]
    require(type(k) is int and 0 <= k <= 8, "scenario width")
    names = scenario["feature_names"]
    require(isinstance(names, list) and len(names) == k and
            all(isinstance(name, str) and 1 <= len(name) <= 512 for name in names) and len(set(names)) == k,
            "unique aligned feature names required")
    versions = scenario["versions"]
    require(isinstance(versions, list) and 2 <= len(versions) <= 4, "bounded version list required")
    for version in versions:
        require(isinstance(version, dict) and set(version) == {"id", "clauses"}, "version fields")
        require(isinstance(version["id"], str) and 1 <= len(version["id"]) <= 128, "version identity")
        base.validate_case({"k": k, "clauses": version["clauses"]})
    require(len({version["id"] for version in versions}) == len(versions), "duplicate version identity")
    require(isinstance(scenario["source"], dict) and scenario["source"].get("kind") in
            {"synthetic", "cached_conditioned_real"}, "source kind")
    return k


def traces(scenario):
    k = validate_scenario(scenario)
    rng = random.Random(SEED + int(digest(scenario)[:8], 16))
    partial = []
    for version in range(len(scenario["versions"])):
        for fixed in (0, (k + 3) // 4, (k + 1) // 2, (3 * k + 3) // 4, k, 0):
            variables = sorted(rng.sample(range(1, k + 1), fixed))
            partial.append({"version": version, "assumptions": [v * rng.choice((-1, 1)) for v in variables]})
    partial.extend(({"version": 0, "assumptions": [1] if k else []}, {"version": 0, "assumptions": []}))
    n = len(scenario["versions"])
    delta = [{"before": 0, "after": 0}] + [{"before": i, "after": i + 1} for i in range(n - 1)]
    delta += [{"before": n - 1, "after": 0}, {"before": 0, "after": 1}]
    return partial, delta


def synthetic_scenarios():
    rng = random.Random(SEED)
    clauses = []
    for _ in range(12):
        clause = [v * rng.choice((-1, 1)) for v in rng.sample(range(1, 9), 3)]
        clause[0] = abs(clause[0])  # All-true planted witness, disclosed synthetic control.
        clauses.append(clause)
    specs = [
        ("zero-width", 0, [[], [[]], []]),
        ("unit-flip", 1, [[[1]], [[-1]]]),
        ("word-boundary", 6, [[[1, -6], [-1, 6]], [[1, -6], [-1, 6], [-1]]]),
        ("duplicate-no-change", 7, [[[1], [1], [-2, 3]], [[1], [-2, 3]]]),
        ("unused-variables", 8, [[[1]], [[1], [2]]]),
        ("seeded-local-edit", 8, [clauses + clauses[:4], clauses + clauses[:4] + [[-1]]]),
    ]
    return [{"id": name, "k": k, "feature_names": [f"x{i}" for i in range(k)],
             "versions": [{"id": f"v{i}", "clauses": value} for i, value in enumerate(versions)],
             "source": {"kind": "synthetic", "seed": SEED}} for name, k, versions in specs]


def historical_scenarios(root=ROOT, known_change_control=False):
    """One first eligible ID per history, independent of outputs/timings.

    Keep every cached candidate in the selection ledger. Do not deduplicate
    clauses, trim formulas, or silently enlarge the k/clause limits.
    """
    path = root / HISTORY
    require(not any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)), "linked historical input")
    with path.open("rb") as handle:
        raw = handle.read((8 << 20) + 1)
    require(len(raw) <= 8 << 20 and hashlib.sha256(raw).hexdigest() == HISTORY_SHA256, "historical input identity changed")
    candidates = [base.strict_json(line) for line in raw.splitlines()]
    require(len(candidates) == 120 and len({row["case_id"] for row in candidates}) == 120, "historical candidate cardinality")
    selected, ledger, seen = [], [], set()
    for row in sorted(candidates, key=lambda row: row["case_id"]):
        history = row["case_id"].split("@", 1)[0]
        receipt = {"case_id": row["case_id"], "history": history, "k": row["k"], "selected": False}
        if row["k"] != 8:
            receipt["reason"] = "outside_declared_k8_cohort"
        else:
            scenario = {"id": row["case_id"], "k": row["k"], "feature_names": row["feature_names"],
                        "versions": [{"id": "earlier", "clauses": row["earlier_residual"]},
                                     {"id": "later", "clauses": row["later_residual"]}],
                        "source": {"kind": "cached_conditioned_real", "history": history,
                                   "source_commit": SOURCE_COMMIT, "input_path": HISTORY,
                                   "input_sha256": HISTORY_SHA256, "source_record_sha256": digest(row),
                                   "conditioning": "saved joint context; not existential projection or full-model equivalence",
                                   "earlier_packed_sha256": row["earlier_packed_sha256"],
                                   "later_packed_sha256": row["later_packed_sha256"]}}
            try:
                validate_scenario(scenario)
            except ValueError:
                receipt["reason"] = "outside_bounded_case_contract"
            else:
                if known_change_control and row["case_id"] != KNOWN_CHANGE_CASE:
                    receipt["reason"] = "outside_named_known_change_diagnostic"
                elif history in seen:
                    receipt["reason"] = "one_per_history_candidate_budget"
                else:
                    receipt.update(selected=True, reason="first_eligible_case_id_in_history")
                    if known_change_control:
                        receipt["reason"] = "named_known_nonzero_positive_control_not_natural_sample"
                        scenario["source"]["selection_role"] = "known_nonzero_positive_control"
                    selected.append(scenario)
                    seen.add(history)
        ledger.append(receipt)
    require(len(selected) == (1 if known_change_control else 7), "historical selection unexpectedly changed")
    return selected, ledger


def original_admissions(root=ROOT):
    path = root / ADMISSIONS
    require(not any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)), "linked historical admissions")
    with path.open("rb") as handle:
        raw = handle.read(65537)
    require(len(raw) <= 65536 and hashlib.sha256(raw).hexdigest() == ADMISSIONS_SHA256, "historical admission identity changed")
    records = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    require(len(records) == 21 and len({row["transition_id"] for row in records}) == 21, "historical admission cardinality")
    require(all(row["admitted"] in {"True", "False"} for row in records), "historical admission state")
    return [{"transition_id": row["transition_id"], "history": row["history"], "admitted": row["admitted"] == "True",
             "reason": row["reason"], "scope": "historical admission; not a new execution"} for row in records]


def validate_request(request):
    require(isinstance(request, dict) and set(request) ==
            {"scenario", "task", "backend", "lifecycle", "trace", "native_identity"}, "request fields")
    k = validate_scenario(request["scenario"])
    require(request["task"] in TASKS and request["backend"] in BACKENDS and request["lifecycle"] in LIFECYCLES,
            "unknown task/backend/lifecycle")
    require((request["backend"] == "sat" and isinstance(request["native_identity"], dict)) or
            (request["backend"] != "sat" and request["native_identity"] is None), "native identity scope")
    trace = request["trace"]
    require(isinstance(trace, list) and 1 <= len(trace) <= 32, "bounded trace required")
    n = len(request["scenario"]["versions"])
    for event in trace:
        fields = {"version", "assumptions"} if request["task"] == "partial_configuration" else {"before", "after"}
        require(isinstance(event, dict) and set(event) == fields, "trace event fields")
        for key in ("version",) if request["task"] == "partial_configuration" else ("before", "after"):
            require(type(event[key]) is int and 0 <= event[key] < n, "version index")
        if request["task"] == "partial_configuration":
            native.validate_sessions([event["assumptions"]], k)
    return k


@contextmanager
def isolated_cm_pool(pool):
    """Only in this trusted sequential worker; restore any caller pool on exit."""
    import cm_ir
    previous = cm_ir._PERSISTENT_IR_CACHE
    cm_ir._PERSISTENT_IR_CACHE = pool
    try:
        yield
    finally:
        cm_ir._PERSISTENT_IR_CACHE = previous


def flat_context(program, k, assumptions):
    from bitset_backend import PreparedFlatEvaluation, _bind_flat_program, _eval_prepared_flat, _eval_words
    fixed = {f"x{abs(lit) - 1}": int(lit > 0) for lit in assumptions}
    live = tuple(f"x{i}" for i in range(k - 1, -1, -1) if f"x{i}" not in fixed)
    if len(live) >= 6:
        return _eval_words(program, live, fixed)
    template, mask = _bind_flat_program(program, live, fixed)
    return _eval_prepared_flat(PreparedFlatEvaluation(program, template, mask, False))


class Engine:
    def __init__(self, scenario, backend, counters, solver_factory=None):
        self.scenario, self.backend, self.counts = scenario, backend, counters
        self.k = scenario["k"]
        self.pool, self.programs, self.columns = OrderedDict(), {}, {}
        self.solver = None
        counters["engine_instances"] += 1
        if backend == "sat":
            require(solver_factory is not None, "SAT factory required")
            self.solver = solver_factory()
            counters["solver_instances"] += 1
            try:
                for variable in range(1, self.k + len(scenario["versions"]) + 1):
                    self.solver.add_clause([variable, -variable])
                for i, version in enumerate(scenario["versions"]):
                    for clause in version["clauses"]:
                        self.solver.add_clause([-(self.k + i + 1), *clause])
            except BaseException:
                self.close()
                raise

    def close(self):
        if self.solver is not None:
            solver, self.solver = self.solver, None
            solver.delete()

    def selectors(self, version):
        return [self.k + i + 1 if i == version else -(self.k + i + 1)
                for i in range(len(self.scenario["versions"]))]

    def prepare(self, version):
        if self.backend not in {"cm", "cse"}:
            return
        if version in self.programs:
            self.counts["program_cache_hits"] += 1
            return
        from bitset_backend import FlatProgram, compile_expr_cse, get_flat_program
        from cm_ir import compile_expr_to_cm_ir
        clauses = self.scenario["versions"][version]["clauses"]
        if self.k == 0:
            program = FlatProgram(1, 0, ((0, "const", int(not any(not c for c in clauses))),), ())
        else:
            expression = base._expression(clauses)
            if self.backend == "cm":
                diagnostics = {}
                with isolated_cm_pool(self.pool):
                    node = compile_expr_to_cm_ir(expression, diagnostics, persistent_cache=True, reuse_cache=False)
                program = get_flat_program(node)
                for name in ("ir_persistent_cache_hits", "ir_persistent_cache_misses"):
                    self.counts[name] += diagnostics.get(name, 0)
            else:
                program = compile_expr_cse(expression, flatten=True)
        self.programs[version] = program
        self.counts["programs_built"] += 1

    def direct_cnf(self, version, assumptions):
        self.counts["cnf_evaluations"] += 1
        fixed = {abs(lit) - 1: lit > 0 for lit in assumptions}
        live = tuple(i for i in range(self.k) if i not in fixed)
        if live not in self.columns:
            self.columns[live] = {variable: sum(1 << a for a in range(1 << len(live)) if (a >> j) & 1)
                                  for j, variable in enumerate(live)}
        full = (1 << (1 << len(live))) - 1
        values = self.columns[live]
        output = full
        for clause in self.scenario["versions"][version]["clauses"]:
            term = 0
            for lit in clause:
                variable = abs(lit) - 1
                value = full if fixed.get(variable) is True else 0 if variable in fixed else values[variable]
                term |= value if lit > 0 else full ^ value
            output &= term
        return output

    def evaluate(self, version, assumptions, vector):
        if self.backend in {"cm", "cse"}:
            self.counts["flat_evaluations"] += 1
            output = flat_context(self.programs[version], self.k, assumptions)
        elif self.backend == "cnf":
            output = self.direct_cnf(version, assumptions)
        else:
            selectors = self.selectors(version)

            def solve(context):
                self.counts["solve_calls"] += 1
                answer = self.solver.solve(assumptions=[*selectors, *context])
                require(type(answer) is bool, "SAT unknown/nonboolean response")
                return answer

            if not vector:
                return solve(assumptions)
            output = 0
            for assignment in range(1 << self.k):
                context = [i + 1 if (assignment >> i) & 1 else -i - 1 for i in range(self.k)]
                output |= int(solve(context)) << assignment
        return output if vector else bool(output)


def execute(request, solver_factory=None, clock=time.perf_counter_ns):
    """Run exact task obligations; oracle and artifact replay belong to controller."""
    k = validate_request(request)
    counters = {name: 0 for name in ("engine_instances", "solver_instances", "programs_built", "program_cache_hits",
                                    "ir_persistent_cache_hits", "ir_persistent_cache_misses", "flat_evaluations",
                                    "cnf_evaluations", "solve_calls")}
    rows, calls, artifacts = [], [], {}
    retained = None

    def evaluate(version, assumptions, vector):
        nonlocal retained
        start = clock()
        fresh = request["lifecycle"] == "fresh"
        engine = None
        try:
            engine = retained if retained is not None else Engine(request["scenario"], request["backend"], counters, solver_factory)
            if not fresh:
                retained = engine
            engine.prepare(version)
            prepared = clock()
            before_calls = counters["solve_calls"]
            output = engine.evaluate(version, assumptions, vector)
            finished = clock()
            calls.append({"version": version, "assumptions": assumptions,
                          "selectors": engine.selectors(version) if request["backend"] == "sat" else [],
                          "mode": "ascending_complete_assignments" if vector else "single_partial_query",
                          "solve_calls": counters["solve_calls"] - before_calls,
                          "prepare_ns": prepared - start, "execute_ns": finished - prepared,
                          "total_ns": finished - start})
            if version in engine.programs:
                artifact = base.export_flat(engine.programs[version], k)
                require(version not in artifacts or digest(artifacts[version]) == digest(artifact), "unstable flat program")
                artifacts[version] = artifact
            return output
        finally:
            if fresh and engine is not None:
                engine.close()

    started = clock()
    try:
        for event in request["trace"]:
            if request["task"] == "partial_configuration":
                rows.append({**event, "satisfiable": evaluate(event["version"], event["assumptions"], False)})
            else:
                earlier = evaluate(event["before"], [], True)
                later = evaluate(event["after"], [], True)
                delta = earlier ^ later
                rows.append({**event, "earlier_hex": hex(earlier), "later_hex": hex(later),
                             "delta_hex": hex(delta), "changed_assignments": delta.bit_count()})
    finally:
        if retained is not None:
            retained.close()
    finished = clock()
    return {"schema": "cm-session-contract/v1", "task": request["task"], "backend": request["backend"],
            "lifecycle": request["lifecycle"], "scenario_sha256": digest(request["scenario"]),
            "trace_sha256": digest(request["trace"]), "rows": rows, "calls": calls, "counters": counters,
            "artifacts": [{"version": version, "program": program} for version, program in sorted(artifacts.items())],
            "session_total_ns": finished - started, "output_cache_used": False,
            "performance_ranking_permitted": False, "timings_for_contract_diagnostics_only": True,
            "memory_metric": "whole owned job counter; not representation-only memory or RSS"}


def oracle(scenario):
    return [base.scalar_vector({"k": scenario["k"], "clauses": version["clauses"]}) for version in scenario["versions"]]


def expected_rows(request, vectors):
    k = request["scenario"]["k"]
    rows = []
    for event in request["trace"]:
        if request["task"] == "partial_configuration":
            answer = any((vectors[event["version"]] >> a) & 1 and native.compatible(a, event["assumptions"])
                         for a in range(1 << k))
            rows.append({**event, "satisfiable": answer})
        else:
            earlier, later = vectors[event["before"]], vectors[event["after"]]
            delta = earlier ^ later
            rows.append({**event, "earlier_hex": hex(earlier), "later_hex": hex(later),
                         "delta_hex": hex(delta), "changed_assignments": delta.bit_count()})
    return rows


def validate_result(result, request, frozen, observed_pids, vectors):
    k = validate_request(request)
    fields = {"schema", "task", "backend", "lifecycle", "scenario_sha256", "trace_sha256", "rows", "calls", "counters",
              "artifacts", "session_total_ns", "output_cache_used", "performance_ranking_permitted",
              "timings_for_contract_diagnostics_only", "memory_metric", "pid", "interpreter", "source_root",
              "request_sha256", "native_identity"}
    require(isinstance(result, dict) and set(result) == fields and result.get("schema") == "cm-session-contract/v1", "result schema/fields")
    for field in ("task", "backend", "lifecycle"):
        require(result.get(field) == request[field], "result task identity")
    require(result.get("scenario_sha256") == digest(request["scenario"]) and result.get("trace_sha256") == digest(request["trace"])
            and result.get("request_sha256") == digest(request), "result input identity")
    require(type(result.get("pid")) is int and result["pid"] > 0 and result["pid"] in observed_pids and
            result.get("source_root") == str(frozen) and result.get("interpreter") == sys.executable, "worker process/source binding")
    require(result.get("output_cache_used") is False and result.get("performance_ranking_permitted") is False and
            result.get("timings_for_contract_diagnostics_only") is True and
            result.get("memory_metric") == "whole owned job counter; not representation-only memory or RSS", "result claim boundary")
    require(digest(result.get("native_identity")) == digest(request["native_identity"]), "native identity mismatch")
    require(digest(result.get("rows")) == digest(expected_rows(request, vectors)), "exact task mismatch")
    expected_calls = []
    for event in request["trace"]:
        expected_calls.extend([(event["version"], event["assumptions"])] if request["task"] == "partial_configuration"
                              else [(event["before"], []), (event["after"], [])])
    calls = result.get("calls")
    require(isinstance(calls, list) and len(calls) == len(expected_calls), "call cardinality")
    vector = request["task"] == "version_delta"
    for call, (version, assumptions) in zip(calls, expected_calls):
        selectors = [k + i + 1 if i == version else -(k + i + 1) for i in range(len(request["scenario"]["versions"]))]
        require(set(call) == {"version", "assumptions", "selectors", "mode", "solve_calls", "prepare_ns", "execute_ns", "total_ns"}, "call fields")
        wanted = {"version": version, "assumptions": assumptions, "selectors": selectors if request["backend"] == "sat" else [],
                  "mode": "ascending_complete_assignments" if vector else "single_partial_query",
                  "solve_calls": ((1 << k) if vector else 1) if request["backend"] == "sat" else 0}
        require(digest({key: call[key] for key in wanted}) == digest(wanted), "selector/context/call mismatch")
        require(all(type(call[key]) is int and 0 <= call[key] <= base.MAX_TIMING_NS for key in ("prepare_ns", "execute_ns", "total_ns")) and
                call["total_ns"] == call["prepare_ns"] + call["execute_ns"], "call timing accounting")
    require(type(result.get("session_total_ns")) is int and
            sum(call["total_ns"] for call in calls) <= result["session_total_ns"] <= base.MAX_TIMING_NS, "session timing accounting")
    counts = result.get("counters")
    require(isinstance(counts, dict) and set(counts) == {"engine_instances", "solver_instances", "programs_built", "program_cache_hits",
            "ir_persistent_cache_hits", "ir_persistent_cache_misses", "flat_evaluations", "cnf_evaluations", "solve_calls"} and
            all(type(value) is int and 0 <= value <= 100000 for value in counts.values()), "invalid counters")
    require(counts["engine_instances"] == (len(calls) if request["lifecycle"] == "fresh" else 1), "fresh/reused engine accounting")
    require(counts["solve_calls"] == sum(call["solve_calls"] for call in calls), "solve total")
    require(counts["solver_instances"] == (counts["engine_instances"] if request["backend"] == "sat" else 0), "solver instance total")
    require(counts["flat_evaluations"] == (len(calls) if request["backend"] in {"cm", "cse"} else 0) and
            counts["cnf_evaluations"] == (len(calls) if request["backend"] == "cnf" else 0), "evaluation counters")
    wanted_builds = (len(calls) if request["lifecycle"] == "fresh" else len({version for version, _ in expected_calls})) if request["backend"] in {"cm", "cse"} else 0
    require(counts["programs_built"] == wanted_builds and
            counts["program_cache_hits"] == (len(calls) - wanted_builds if request["backend"] in {"cm", "cse"} else 0), "program reuse accounting")
    artifacts = result.get("artifacts")
    require(isinstance(artifacts, list), "artifact list")
    versions = sorted({version for version, _ in expected_calls}) if request["backend"] in {"cm", "cse"} else []
    require([item["version"] for item in artifacts] == versions, "artifact version coverage")
    auditor = base.independent_auditor(frozen)
    for artifact in artifacts:
        require(set(artifact) == {"version", "program"} and type(artifact["version"]) is int, "artifact fields")
        _program, width = base.import_flat(artifact["program"])
        require(width == k and auditor.replay_flat(artifact["program"]) == vectors[artifact["version"]], "independent artifact mismatch")


def worker(request):
    validate_request(request)
    solver_factory = None
    if request["backend"] == "sat":
        identity = native.sat_identity()
        require(identity["status"] == "available" and digest(identity) == digest(request["native_identity"]), "native binding unavailable/changed")
        from pysat.solvers import Cadical195
        solver_factory = Cadical195
    elif request["backend"] in {"cm", "cse"}:
        import bitset_backend  # Included in whole-process latency, outside inner diagnostics.
        import cm_ir
    result = execute(request, solver_factory)
    if request["backend"] == "sat":
        require(digest(native.sat_identity()) == digest(request["native_identity"]), "native binding changed during execution")
    result.update(pid=os.getpid(), interpreter=sys.executable, source_root=str(ROOT),
                  request_sha256=digest(request), native_identity=request["native_identity"])
    return result


def verify_sources(frozen, manifest):
    require(hashlib.sha256((frozen / "source_manifest.json").read_bytes()).hexdigest() == manifest["manifest_sha256"], "source manifest changed")
    for row in manifest["files"]:
        require(hashlib.sha256((frozen / row["path"]).read_bytes()).hexdigest() == row["sha256"], "frozen source changed")


def evidence_totals(requests, scheduled, state):
    """Counts of accepted outputs/work, never ratios of diagnostic timings."""
    totals = {"accepted_partial_answers": 0, "accepted_delta_vectors": 0, "native_solve_calls": 0,
              "independent_flat_artifact_replays": 0, "verified_worker_cleanups": 0, "by_backend_lifecycle": {}}
    for request, cell in zip(requests, scheduled):
        row = state["cells"].get(cell["cell_id"], {})
        key = request["backend"] + "/" + request["lifecycle"]
        group = totals["by_backend_lifecycle"].setdefault(key, {"scheduled_cells": 0, "accepted_cells": 0,
                                                              "engine_instances": 0, "programs_built": 0})
        group["scheduled_cells"] += 1
        if row.get("status") != "ok":
            continue
        result = row["result"]
        group["accepted_cells"] += 1
        for name in ("engine_instances", "programs_built"):
            group[name] += result["counters"][name]
        totals["accepted_partial_answers" if request["task"] == "partial_configuration" else "accepted_delta_vectors"] += len(result["rows"])
        totals["native_solve_calls"] += result["counters"]["solve_calls"]
        totals["independent_flat_artifact_replays"] += len(result["artifacts"])
        totals["verified_worker_cleanups"] += int(row["supervision"].get("cleanup_verified") is True)
    return totals


def pilot(output, synthetic_only=False, known_change_control=False):
    from scripts.cm_benchmark_provenance import capture_source_snapshot
    from scripts.cm_process_supervisor import run
    output = output.absolute()
    require(not (synthetic_only and known_change_control), "conflicting cohort scopes")
    require(not output.exists() and output.resolve().is_relative_to(ROOT) and
            not any(p.is_symlink() or p.is_junction() for p in (output, *output.parents)), "new nonlinked project output required")
    observed = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}
    manifest = capture_source_snapshot(ROOT, output / "source_snapshot", SOURCES)
    frozen = output / "source_snapshot"
    require(all(row["sha256"] == observed[row["path"]] for row in manifest["files"]), "source changed before freeze")
    scenarios, selection, admissions = ([] if known_change_control else synthetic_scenarios()), [], []
    if not synthetic_only:
        real, selection = historical_scenarios(frozen, known_change_control)
        scenarios += real
        admissions = original_admissions(frozen)
        admitted = {row["transition_id"] for row in admissions if row["admitted"]}
        require(all(row["case_id"].split("|")[0] in admitted for row in selection), "candidate absent from original admissions")
    identity = native.sat_identity()
    requests, oracle_rows, vectors_by_case = [], [], {}
    for scenario in scenarios:
        vectors = oracle(scenario)
        vectors_by_case[digest(scenario)] = vectors
        if scenario["source"]["kind"] == "cached_conditioned_real":
            for name, value in zip(("earlier", "later"), vectors):
                raw = value.to_bytes((1 << scenario["k"]) // 8, "little")
                require(hashlib.sha256(raw).hexdigest() == scenario["source"][name + "_packed_sha256"], "historical relation changed")
        oracle_rows.append({"scenario_sha256": digest(scenario), "vectors": [hex(value) for value in vectors]})
        partial, delta = traces(scenario)
        for task, trace in zip(TASKS, (partial, delta)):
            for backend in BACKENDS:
                for lifecycle in LIFECYCLES:
                    requests.append({"scenario": scenario, "task": task, "trace": trace, "backend": backend,
                                     "lifecycle": lifecycle, "native_identity": identity if backend == "sat" else None})
    scheduled = [{"cell_id": f"cell-{i:03}", "request_sha256": digest(request)} for i, request in enumerate(requests)]
    plan = {"schema": "cm-session-pilot/v1", "seed": SEED, "requests": requests, "scheduled_cells": scheduled,
            "selection_role": "named_known_nonzero_positive_control" if known_change_control else
                              "synthetic_only" if synthetic_only else "synthetic_plus_outcome_independent_history_sample",
            "historical_selection": selection, "source_manifest_sha256": manifest["manifest_sha256"],
            "original_transition_admissions": admissions,
            "input_preparation": "bounded scalar oracle before workers; no measured objects warmed",
            "fresh_scope": "new representation/solver per query or per version-vector extraction; interpreter remains resident",
            "sat_encoding": "both lifecycles load identical guarded versions; exactly one positive selector, all others negative",
            "output_cache_used": False, "performance_ranking_permitted": False,
            "scheduling": "fixed sequential correctness pilot; no crossover/timing rankings",
            "native_CUDD_ZDD_d4": "not executed; separate native-build gates remain",
            "command_template": [sys.executable, "-B", str(frozen / "scripts/cm_session_contracts.py"), "--worker"]}
    (output / "plan.json").write_bytes(encoded(plan) + b"\n")
    (output / "oracles.json").write_bytes(encoded(oracle_rows) + b"\n")
    ledger = output / "cells.jsonl"
    for cell, request in zip(scheduled, requests):
        verify_sources(frozen, manifest)
        base.append_record(ledger, {**cell, "status": "running"})
        row = {**cell, "status": "error"}
        if request["backend"] == "sat" and identity["status"] != "available":
            row.update(status="refused", reason="native_sat_unavailable")
        else:
            proc = run(plan["command_template"], input=encoded(request), cwd=frozen)
            row.update(status=proc.status if proc.status in {"refused", "timeout"} else "error",
                       reason=proc.reason, supervisor_status=proc.status, supervision=proc.resources,
                       controller_wall_ns=proc.wall_ns, launched_pid=proc.pid)
            if proc.status == "ok":
                try:
                    result = base.strict_json(proc.stdout)
                    require(proc.resources["cleanup_verified"] and proc.resources["streams_closed"] and
                            proc.resources["attached_before_resume"], "incomplete supervision")
                    validate_result(result, request, frozen, proc.resources["observed_job_pids"], vectors_by_case[digest(request["scenario"])])
                    row.update(status="ok", result=result, worker_pid_observed_in_owned_job=True)
                except (ValueError, TypeError, KeyError, RecursionError):
                    row.update(reason="invalid_or_inexact_worker_result")
            elif proc.stderr:
                row["stderr_excerpt"] = proc.stderr[:4096].decode("utf-8", errors="replace")
        base.append_record(ledger, row)
        print(encoded({"cell_id": cell["cell_id"], "status": row["status"]}).decode(), flush=True)
    verify_sources(frozen, manifest)
    state = base.read_ledger(ledger)
    reconciliation = base.reconcile_schedule(state, scheduled)
    changes = [name for name, expected in observed.items() if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    summary = {"schema": "cm-session-pilot-result/v1", "scenario_count": len(scenarios), "scheduled_cell_count": len(scheduled),
               "selection_role": plan["selection_role"],
               "outcomes": dict(Counter(row["status"] for row in state["cells"].values())), **reconciliation,
               "accepted_output_totals": evidence_totals(requests, scheduled, state),
               "scenario_relations": [{"id": scenario["id"], "kind": scenario["source"]["kind"],
                                       "counts": [value.bit_count() for value in vectors_by_case[digest(scenario)]],
                                       "first_transition_changed_assignments": (vectors_by_case[digest(scenario)][0] ^
                                                                                vectors_by_case[digest(scenario)][1]).bit_count()}
                                      for scenario in scenarios],
               "frozen_sources_unchanged": True, "concurrent_source_changes": changes,
               "performance_ranking_permitted": False, "full_measurement_protocol_complete": False, "cloud_run": False}
    summary["status"] = "passed" if (not changes and reconciliation["all_scheduled_cells_retained"] and not state["unfinished"] and
                                                    not state["partial_tail"] and all(row["status"] == "ok" for row in state["cells"].values())) else "incomplete"
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
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--synthetic-only", action="store_true")
    scope.add_argument("--known-change-control", action="store_true")
    args = parser.parse_args()
    if args.worker:
        raw = sys.stdin.buffer.read(base.MAX_RECORD + 1)
        require(len(raw) <= base.MAX_RECORD, "worker input bound")
        result = worker(base.strict_json(raw))
    else:
        result = pilot(args.pilot_output, args.synthetic_only, args.known_change_control)
    print(encoded(result).decode(), flush=True)
    return 0 if result.get("status", "passed") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
