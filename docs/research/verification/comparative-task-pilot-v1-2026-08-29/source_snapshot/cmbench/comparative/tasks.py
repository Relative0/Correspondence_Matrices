"""Bounded task-matched adapters built on the verified session engines.

This is a functional comparison layer, not a timing campaign.  It gives CM,
structural CSE, direct CNF and CaDiCaL the same task/trace and hashes a
canonical semantic result.  Scalar CNF enumeration remains outside execution
and supplies the independent expected digest.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Mapping
from typing import Any

from scripts import cm_measurement_verify as scalar
from scripts import cm_native_contracts as native
from scripts import cm_session_contracts as sessions

from .arms import semantic_sha256
from .contracts import (
    CONTRACT_SCHEMA,
    RESULT_SCHEMA,
    canonical_bytes,
    contract_digest,
    validate_contract,
    validate_result,
)


BACKENDS = ("cm", "cse", "cnf", "sat")
LIFECYCLES = ("fresh_engine", "resident_engine")
TASKS = (
    "exact_count",
    "sat_status",
    "witness",
    "partial_context",
    "version_history",
    "equivalence_delta",
)
ARTIFACTS = {
    "exact_count": "scalar_count",
    "sat_status": "boolean_status",
    "witness": "witness_assignment",
    "partial_context": "context_answers",
    "version_history": "history_answers",
    "equivalence_delta": "delta_count",
}
ORDERED_ARTIFACTS = {"witness_assignment", "context_answers", "history_answers"}
MAX_EVENTS = 32
COUNTER_NAMES = (
    "engine_instances",
    "solver_instances",
    "programs_built",
    "program_cache_hits",
    "ir_persistent_cache_hits",
    "ir_persistent_cache_misses",
    "flat_evaluations",
    "cnf_evaluations",
    "solve_calls",
)


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _variables(k: int) -> tuple[str, ...]:
    return tuple(f"x{i}" for i in range(k))


def validate_trace(scenario: Mapping[str, Any], task: str, trace: Any) -> list[dict[str, Any]]:
    k = sessions.validate_scenario(scenario)
    require(task in TASKS, "unsupported task")
    require(isinstance(trace, list) and 1 <= len(trace) <= MAX_EVENTS, "bounded nonempty trace required")
    versions = len(scenario["versions"])
    output: list[dict[str, Any]] = []
    for event in trace:
        require(isinstance(event, dict), "trace event must be an object")
        if task == "exact_count":
            require(set(event) == {"version"}, "count trace fields")
            keys = ("version",)
        elif task == "equivalence_delta":
            require(set(event) == {"before", "after"}, "delta trace fields")
            keys = ("before", "after")
        else:
            require(set(event) == {"version", "assumptions"}, "query trace fields")
            keys = ("version",)
            native.validate_sessions([event["assumptions"]], k)
        for key in keys:
            require(type(event[key]) is int and 0 <= event[key] < versions, "version outside scenario")
        output.append({key: (list(value) if isinstance(value, list) else value) for key, value in event.items()})
    return output


def semantic_document(task: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    require(task in TASKS and isinstance(rows, list), "semantic output")
    return {"schema": "cm-comparative-semantic-output/v1", "task": task, "rows": rows}


def semantic_digest(task: str, rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(canonical_bytes(semantic_document(task, rows))).hexdigest()


def task_contract(
    *,
    contract_id: str,
    task: str,
    backend: str,
    lifecycle: str,
    k: int,
    queries: int,
    expected_sha256: str,
) -> dict[str, Any]:
    require(task in TASKS and backend in BACKENDS and lifecycle in LIFECYCLES, "contract mode")
    require(type(k) is int and 1 <= k <= 8, "task pilot width must be 1..8")
    kind = ARTIFACTS[task]
    variables = _variables(k)
    ordered = kind in ORDERED_ARTIFACTS
    contract = {
        "schema": CONTRACT_SCHEMA,
        "contract_id": contract_id,
        "task": task,
        "artifact": {
            "kind": kind,
            "variable_order": list(variables),
            "output_order": list(variables) if ordered else [],
            "fixed": [],
            "output_scope": "not_applicable",
            "restoration": "none",
            "stream": None,
        },
        "lifecycle": lifecycle,
        "queries": queries,
        "validation": {
            "oracle": "independent_scalar_cnf/v1",
            "validation_in_timed_span": False,
            "required_output_sha256": expected_sha256,
        },
    }
    validate_contract(contract)
    return contract


def _vectors(scenario: Mapping[str, Any]) -> list[int]:
    sessions.validate_scenario(scenario)
    return [scalar.scalar_vector({"k": scenario["k"], "clauses": version["clauses"]})
            for version in scenario["versions"]]


def _witness(bits: int, k: int) -> list[dict[str, Any]] | None:
    if not bits:
        return None
    assignment = (bits & -bits).bit_length() - 1
    return [{"variable": f"x{i}", "value": (assignment >> i) & 1} for i in range(k)]


def _rows_from_vectors(
    scenario: Mapping[str, Any], task: str, trace: list[dict[str, Any]], vectors: list[int]
) -> list[dict[str, Any]]:
    k = scenario["k"]
    rows: list[dict[str, Any]] = []
    for index, event in enumerate(trace):
        if task == "exact_count":
            rows.append({**event, "count": vectors[event["version"]].bit_count()})
        elif task == "equivalence_delta":
            delta = vectors[event["before"]] ^ vectors[event["after"]]
            rows.append({**event, "equivalent": delta == 0, "changed_assignments": delta.bit_count(),
                         "delta_sha256": semantic_sha256(delta, k)})
        else:
            assumptions = event["assumptions"]
            compatible = sum(1 << assignment for assignment in range(1 << k)
                             if native.compatible(assignment, assumptions))
            bits = vectors[event["version"]] & compatible
            if task == "witness":
                rows.append({"query": index, **event, "witness": _witness(bits, k)})
            else:
                rows.append({"query": index, **event, "satisfiable": bool(bits)})
    return rows


def scalar_oracle(
    scenario: Mapping[str, Any], task: str, trace: Any
) -> list[dict[str, Any]]:
    normalized = validate_trace(scenario, task, trace)
    return _rows_from_vectors(scenario, task, normalized, _vectors(scenario))


def _counters() -> dict[str, int]:
    return {name: 0 for name in COUNTER_NAMES}


def execute_task(
    *,
    scenario: Mapping[str, Any],
    task: str,
    trace: Any,
    backend: str,
    lifecycle: str,
    contract: Mapping[str, Any],
    case_id: str,
    solver_factory: Callable[[], Any] | None = None,
    native_identity: Mapping[str, Any] | None = None,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    normalized_trace = validate_trace(scenario, task, trace)
    require(backend in BACKENDS and lifecycle in LIFECYCLES, "execution mode")
    normalized_contract = validate_contract(contract)
    require(normalized_contract["task"] == task and normalized_contract["lifecycle"] == lifecycle and
            normalized_contract["queries"] == len(normalized_trace) and
            normalized_contract["variable_order"] == _variables(scenario["k"]), "contract/request mismatch")

    if backend == "sat":
        if solver_factory is None:
            identity = native.sat_identity()
            require(identity.get("status") == "available", "native SAT unavailable")
            from pysat.solvers import Cadical195
            solver_factory = Cadical195
            native_identity = identity
        else:
            require(isinstance(native_identity, Mapping), "injected solver identity required")
    else:
        require(solver_factory is None and native_identity is None, "native settings on nonnative backend")

    counts = _counters()
    retained: sessions.Engine | None = None

    def evaluate(version: int, assumptions: list[int], vector: bool) -> int | bool:
        nonlocal retained
        fresh = lifecycle == "fresh_engine"
        engine: sessions.Engine | None = None
        try:
            engine = retained if retained is not None else sessions.Engine(
                scenario, backend, counts, solver_factory if backend == "sat" else None
            )
            if not fresh:
                retained = engine
            engine.prepare(version)
            return engine.evaluate(version, assumptions, vector)
        finally:
            if fresh and engine is not None:
                engine.close()

    started = clock()
    rows: list[dict[str, Any]] = []
    try:
        for index, event in enumerate(normalized_trace):
            if task == "exact_count":
                bits = int(evaluate(event["version"], [], True))
                rows.append({**event, "count": bits.bit_count()})
            elif task == "equivalence_delta":
                earlier = int(evaluate(event["before"], [], True))
                later = int(evaluate(event["after"], [], True))
                delta = earlier ^ later
                rows.append({**event, "equivalent": delta == 0, "changed_assignments": delta.bit_count(),
                             "delta_sha256": semantic_sha256(delta, scenario["k"])})
            elif task == "witness":
                # Canonical witnesses require the same ascending original-axis
                # order from every backend.  Extract the full bounded vector,
                # then apply assumptions; do not accept a solver's arbitrary
                # model or reinterpret a reduced relation as original axes.
                bits = int(evaluate(event["version"], [], True))
                compatible = sum(1 << assignment for assignment in range(1 << scenario["k"])
                                 if native.compatible(assignment, event["assumptions"]))
                bits &= compatible
                rows.append({"query": index, **event, "witness": _witness(bits, scenario["k"])})
            else:
                answer = evaluate(event["version"], event["assumptions"], False)
                require(type(answer) is bool, "nonboolean status")
                rows.append({"query": index, **event, "satisfiable": answer})
    finally:
        if retained is not None:
            retained.close()
    task_total = clock() - started
    require(type(task_total) is int and task_total >= 0, "nonmonotonic task clock")

    document = semantic_document(task, rows)
    payload = canonical_bytes(document)
    result = {
        "schema": RESULT_SCHEMA,
        "contract_sha256": contract_digest(contract),
        "case_id": case_id,
        "arm": backend,
        "status": "ok",
        "reason": "completed",
        "timings_ns": {"task_total_ns": task_total},
        "artifact": {
            "kind": normalized_contract["kind"],
            "output_scope": normalized_contract["output_scope"],
            "output_order": list(normalized_contract["output_order"]),
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
        "resources": {"measurement": "in_process_functional_smoke", "rss_measured": False},
        "identity": {
            "semantic_output": document,
            "semantic_encoding": "canonical_json_sha256/v1",
            "counters": counts,
            "native_identity": dict(native_identity) if native_identity is not None else None,
            "output_cache_used": False,
            "performance_claim_permitted": False,
        },
    }
    validate_task_result(result, contract)
    return result


def validate_task_result(
    result: Mapping[str, Any], contract: Mapping[str, Any], expected_rows: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    validated = validate_result(result, contract)
    identity = result.get("identity")
    require(isinstance(identity, Mapping) and set(identity) == {
        "semantic_output", "semantic_encoding", "counters", "native_identity",
        "output_cache_used", "performance_claim_permitted",
    }, "task identity fields")
    require(identity["semantic_encoding"] == "canonical_json_sha256/v1" and
            identity["output_cache_used"] is False and identity["performance_claim_permitted"] is False,
            "task claim boundary")
    document = identity["semantic_output"]
    require(isinstance(document, Mapping) and set(document) == {"schema", "task", "rows"} and
            document["schema"] == "cm-comparative-semantic-output/v1" and
            document["task"] == validate_contract(contract)["task"] and isinstance(document["rows"], list),
            "semantic document")
    payload = canonical_bytes(document)
    require(result["artifact"]["bytes"] == len(payload) and
            result["artifact"]["sha256"] == hashlib.sha256(payload).hexdigest(), "semantic artifact identity")
    counts = identity["counters"]
    require(isinstance(counts, Mapping) and set(counts) == set(COUNTER_NAMES) and
            all(type(value) is int and 0 <= value <= 1_000_000 for value in counts.values()), "counter record")
    if expected_rows is not None:
        require(document["rows"] == expected_rows, "independent scalar output mismatch")
    return validated
