"""C35 exact repeated partial-context queries on frozen natural expressions.

Every method receives one immutable expression and the same outcome-independent
trace of partial assignments.  A query delivers the complete reduced relation,
from which exact count, SAT status, and a canonical witness are derived.  This
keeps BDD, SAT, CSE, direct evaluation, and CM IR under one output contract.
"""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from bitset_backend import (
    PreparedFlatEvaluation,
    _bind_flat_program,
    build_bitset_env,
    compile_expr_cse,
    eval_expr_bitset,
    get_flat_program,
)
from cm_expr_serde import expr_from_json
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir

from cmbench.recognition.bdd_ordering import ExactBddArtifact
from cmbench.recognition.sat_guidance import encode_expression_cnf

from .contracts import (
    CONTRACT_SCHEMA,
    RESULT_SCHEMA,
    canonical_bytes,
    contract_digest,
    validate_contract,
    validate_result,
)
from .gf2_natural_headroom import validate_dataset_manifest as validate_c34_manifest
from .gf2_natural_headroom import validate_natural_case


DATASET_SCHEMA = "crse-c35-natural-repeated-query-dataset/v1"
SEMANTIC_SCHEMA = "crse-c35-partial-context-output/v1"
METHODS = (
    "direct_ast_restrict",
    "flattened_cse_restrict",
    "cm_ir_restrict",
    "direct_truth_cache",
    "bdd_autoref_restrict",
    "cadical_enumeration",
)
CHECKPOINTS = (1, 4, 16, 64)
MAX_FIXED = 4


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def select_session_cases(cases: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Select one source-identity case per width without consulting outcomes."""
    selected = []
    widths = sorted({validate_natural_case(case)["n_vars"] for case in cases})
    for n_vars in widths:
        group = [case for case in cases if case["n_vars"] == n_vars]
        chosen = min(group, key=lambda row: (row["selection_sha256"], row["case_id"]))
        selected.append(chosen["case_id"])
    _require(widths == list(range(3, 11)) and len(selected) == 8,
             "C35 requires one natural case at every width 3..10")
    return tuple(selected)


def build_query_trace(case_id: str, n_vars: int, *, queries: int = 64) -> list[dict[str, Any]]:
    """Build a deterministic output-blind partial-assignment trace."""
    _require(isinstance(case_id, str) and case_id and 3 <= n_vars <= 10,
             "invalid C35 trace identity")
    _require(queries == 64, "C35 freezes exactly 64 queries")
    rows = []
    for query in range(queries):
        seed = hashlib.sha256(f"c35:{case_id}:{query}".encode("ascii")).digest()
        fixed_count = 1 + seed[0] % min(MAX_FIXED, n_vars - 1)
        variables = sorted(
            range(n_vars),
            key=lambda index: hashlib.sha256(seed + bytes([index])).digest(),
        )[:fixed_count]
        assignments = [
            {"variable": f"x{index}", "value": (seed[1 + offset] >> (index % 8)) & 1}
            for offset, index in enumerate(sorted(variables))
        ]
        remaining = [f"x{index}" for index in range(n_vars) if index not in variables]
        row = {
            "query": query,
            "fixed": assignments,
            "remaining_order": remaining,
        }
        row["query_sha256"] = _digest(row)
        rows.append(row)
    return rows


def validate_query_trace(trace: Any, case_id: str, n_vars: int) -> list[dict[str, Any]]:
    _require(isinstance(trace, list) and len(trace) == 64, "C35 trace cardinality")
    expected = build_query_trace(case_id, n_vars)
    _require(trace == expected, "C35 trace is not the frozen output-blind trace")
    return expected


def restrict_full_truth(bits: int, n_vars: int, fixed: Mapping[str, int]) -> tuple[tuple[str, ...], int]:
    """Project an MSB-first packed truth vector after fixing original axes."""
    _require(type(bits) is int and 0 <= bits < 1 << (1 << n_vars), "invalid full truth")
    _require(isinstance(fixed, Mapping) and 1 <= len(fixed) < n_vars, "invalid restriction")
    fixed_indices: dict[int, int] = {}
    for name, value in fixed.items():
        _require(isinstance(name, str) and name.startswith("x") and name[1:].isdigit(),
                 "invalid fixed variable")
        index = int(name[1:])
        _require(0 <= index < n_vars and index not in fixed_indices
                 and type(value) is int and value in (0, 1), "invalid fixed value")
        fixed_indices[index] = value
    remaining_indices = tuple(index for index in range(n_vars) if index not in fixed_indices)
    reduced = 0
    for residual_assignment in range(1 << len(remaining_indices)):
        original_assignment = 0
        residual_position = 0
        for index in range(n_vars):
            if index in fixed_indices:
                value = fixed_indices[index]
            else:
                value = (residual_assignment >>
                         (len(remaining_indices) - 1 - residual_position)) & 1
                residual_position += 1
            original_assignment = (original_assignment << 1) | value
        reduced |= ((bits >> original_assignment) & 1) << residual_assignment
    return tuple(f"x{index}" for index in remaining_indices), reduced


def _canonical_witness(reduced: int, remaining: Sequence[str], fixed: Mapping[str, int],
                       n_vars: int) -> list[dict[str, Any]] | None:
    if reduced == 0:
        return None
    assignment = (reduced & -reduced).bit_length() - 1
    values = dict(fixed)
    for position, name in enumerate(remaining):
        values[name] = (assignment >> (len(remaining) - 1 - position)) & 1
    return [{"variable": f"x{index}", "value": values[f"x{index}"]}
            for index in range(n_vars)]


def semantic_row(query: Mapping[str, Any], reduced: int, n_vars: int) -> dict[str, Any]:
    fixed = {row["variable"]: row["value"] for row in query["fixed"]}
    remaining = tuple(query["remaining_order"])
    width = len(remaining)
    _require(type(reduced) is int and 0 <= reduced < 1 << (1 << width),
             "invalid C35 reduced relation")
    byte_count = max(1, ((1 << width) + 7) // 8)
    truth_payload = reduced.to_bytes(byte_count, "little")
    return {
        "query": query["query"],
        "query_sha256": query["query_sha256"],
        "fixed": list(query["fixed"]),
        "remaining_order": list(remaining),
        "truth_bits_hex": format(reduced, "x"),
        "truth_sha256": hashlib.sha256(truth_payload).hexdigest(),
        "exact_count": reduced.bit_count(),
        "satisfiable": bool(reduced),
        "canonical_witness": _canonical_witness(reduced, remaining, fixed, n_vars),
    }


def semantic_document(case_id: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {"schema": SEMANTIC_SCHEMA, "case_id": case_id, "rows": list(rows)}


def oracle_document(case: Mapping[str, Any], trace: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = validate_natural_case(case)
    validate_query_trace(list(trace), normalized["case_id"], normalized["n_vars"])
    rows = []
    for query in trace:
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        remaining, reduced = restrict_full_truth(normalized["bits"], normalized["n_vars"], fixed)
        _require(tuple(query["remaining_order"]) == remaining, "C35 trace remaining order")
        rows.append(semantic_row(query, reduced, normalized["n_vars"]))
    return semantic_document(normalized["case_id"], rows)


def build_dataset_manifest(
    c34_manifest_path: Path,
    c34_verification_path: Path,
    source_path: Path,
    *,
    c34_manifest_relative: str,
    c34_verification_relative: str,
    source_relative: str,
) -> dict[str, Any]:
    c34 = json.loads(c34_manifest_path.read_text(encoding="utf-8"))
    verification = json.loads(c34_verification_path.read_text(encoding="utf-8"))
    source = json.loads(source_path.read_text(encoding="utf-8"))
    validate_c34_manifest(c34, source)
    _require(verification.get("status") == "verified"
             and verification.get("manifest_sha256") == _sha256(c34_manifest_path),
             "C35 requires verified frozen C34 input")
    source_map = {case["case_id"]: case for case in source["cases"]}
    selected = select_session_cases(source["cases"])
    rows = []
    for case_id in selected:
        case = source_map[case_id]
        trace = build_query_trace(case_id, case["n_vars"])
        oracle = oracle_document(case, trace)
        rows.append({
            "case_id": case_id,
            "cluster_id": case["cluster_id"],
            "family": case["family"],
            "n_vars": case["n_vars"],
            "truth_sha256": case["truth_sha256"],
            "expression_v2_sha256": case["expression_v2_sha256"],
            "selection_sha256": case["selection_sha256"],
            "trace": trace,
            "trace_sha256": _digest(trace),
            "required_output_sha256": _digest(oracle),
        })
    manifest = {
        "schema": DATASET_SCHEMA,
        "status": "frozen",
        "source": {
            "c34_manifest_path": c34_manifest_relative,
            "c34_manifest_sha256": _sha256(c34_manifest_path),
            "c34_verification_path": c34_verification_relative,
            "c34_verification_sha256": _sha256(c34_verification_path),
            "dataset_path": source_relative,
            "dataset_sha256": _sha256(source_path),
        },
        "selection": {
            "cases": "one lowest source selection identity per width 3..10",
            "queries": "64 SHA-256-derived partial assignments per case",
            "outcome_or_timing_used": False,
            "training_use": False,
            "fresh_confirmation": False,
        },
        "counts": {"cases": 8, "queries_per_case": 64, "total_queries": 512},
        "checkpoints": list(CHECKPOINTS),
        "cases": rows,
        "provenance": {
            "natural_source_reused": True,
            "network_used": False,
            "training": False,
            "policy_refit": False,
        },
    }
    validate_dataset_manifest(manifest, source)
    return manifest


def validate_dataset_manifest(manifest: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    _require(isinstance(manifest, Mapping) and manifest.get("schema") == DATASET_SCHEMA
             and manifest.get("status") == "frozen", "C35 dataset schema/status")
    rows = manifest.get("cases")
    _require(isinstance(rows, list) and len(rows) == 8
             and len({row.get("case_id") for row in rows}) == 8, "C35 case cardinality")
    _require(manifest.get("checkpoints") == list(CHECKPOINTS)
             and manifest.get("counts") == {"cases": 8, "queries_per_case": 64,
                                              "total_queries": 512},
             "C35 frozen bounds")
    source_map = {case["case_id"]: case for case in source.get("cases", [])}
    _require(tuple(row["case_id"] for row in rows) == select_session_cases(source["cases"]),
             "C35 case selection")
    _require([row["n_vars"] for row in rows] == list(range(3, 11)), "C35 width coverage")
    for row in rows:
        case = source_map.get(row["case_id"])
        _require(case is not None and all(row[key] == case[key] for key in
                 ("cluster_id", "family", "n_vars", "truth_sha256",
                  "expression_v2_sha256", "selection_sha256")), "C35 source binding")
        trace = validate_query_trace(row.get("trace"), row["case_id"], row["n_vars"])
        _require(row.get("trace_sha256") == _digest(trace)
                 and row.get("required_output_sha256") == _digest(oracle_document(case, trace)),
                 "C35 trace/oracle binding")
    selection = manifest.get("selection", {})
    _require(selection.get("outcome_or_timing_used") is False
             and selection.get("training_use") is False
             and selection.get("fresh_confirmation") is False,
             "C35 selection boundary")
    return {"cases": 8, "queries": 512}


def bind_manifest_cases(manifest: Mapping[str, Any], source: Mapping[str, Any]) -> list[dict[str, Any]]:
    validate_dataset_manifest(manifest, source)
    source_map = {case["case_id"]: case for case in source["cases"]}
    return [{**source_map[row["case_id"]], "c35_trace": row["trace"],
             "c35_required_output_sha256": row["required_output_sha256"]}
            for row in manifest["cases"]]


def task_contract(case: Mapping[str, Any], method: str) -> dict[str, Any]:
    normalized = validate_natural_case(case)
    _require(method in METHODS, "unknown C35 method")
    contract = {
        "schema": CONTRACT_SCHEMA,
        "contract_id": f"c35:{normalized['case_id']}:{method}",
        "task": "partial_context",
        "artifact": {
            "kind": "context_answers",
            "variable_order": [f"x{i}" for i in range(normalized["n_vars"])],
            "output_order": [f"x{i}" for i in range(normalized["n_vars"])],
            "fixed": [],
            "output_scope": "not_applicable",
            "restoration": "none",
            "stream": None,
        },
        "lifecycle": "resident_engine",
        "queries": 64,
        "validation": {
            "oracle": "frozen_full_truth_projection/v1",
            "validation_in_timed_span": False,
            "required_output_sha256": case["c35_required_output_sha256"],
        },
    }
    validate_contract(contract)
    return contract


def _eval_ast_restricted(expr: Expr, n_vars: int, fixed: Mapping[str, int],
                         remaining: Sequence[str]) -> int:
    env = build_bitset_env(tuple(remaining))
    full_mask = (1 << (1 << len(remaining))) - 1

    def rec(node: Expr) -> int:
        if isinstance(node, Var):
            name = f"x{node.i}"
            return full_mask if fixed.get(name) == 1 else (0 if name in fixed else int(env[name]))
        if isinstance(node, Not):
            return (~rec(node.a)) & full_mask
        left = rec(node.a)
        right = rec(node.b)
        if isinstance(node, And):
            return left & right
        if isinstance(node, Or):
            return left | right
        if isinstance(node, Xor):
            return left ^ right
        if isinstance(node, Imp):
            return ((~left) | right) & full_mask
        if isinstance(node, Eqv):
            return (~(left ^ right)) & full_mask
        raise TypeError(node)

    return rec(expr)


def execute_session(
    *,
    case: Mapping[str, Any],
    contract: Mapping[str, Any],
    method: str,
    clock: Callable[[], int] = time.perf_counter_ns,
    solver_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    normalized = validate_natural_case(case)
    normalized_contract = validate_contract(contract)
    _require(method in METHODS and normalized_contract["task"] == "partial_context"
             and normalized_contract["queries"] == 64
             and contract["contract_id"] == f"c35:{normalized['case_id']}:{method}",
             "C35 task/method contract")
    trace = validate_query_trace(case.get("c35_trace"), normalized["case_id"],
                                 normalized["n_vars"])
    expected = _digest(oracle_document(case, trace))
    _require(expected == case.get("c35_required_output_sha256")
             == contract["validation"]["required_output_sha256"], "C35 oracle mismatch")

    timings = {"input_decode_ns": 0, "representation_ns": 0, "compile_ns": 0,
               "query_total_ns": 0, "cleanup_ns": 0, "task_total_ns": 0}
    resources: dict[str, Any] = {}

    started = clock()
    expr = expr_from_json(case["expression_v2"])
    timings["input_decode_ns"] = max(1, clock() - started)
    program = node = bdd = solver = None
    full_bits = None

    started = clock()
    if method == "flattened_cse_restrict":
        program = compile_expr_cse(expr, flatten=True)
        resources.update({"program_slots": program.n_slots, "program_ops": len(program.ops)})
    elif method == "cm_ir_restrict":
        node = compile_expr_to_cm_ir(
            expr, reuse_cache=False, persistent_cache=False, share_aware_flatten=True)
        program = get_flat_program(node)
        resources.update({"program_slots": program.n_slots, "program_ops": len(program.ops)})
    elif method == "direct_truth_cache":
        environment = build_bitset_env(tuple(f"x{i}" for i in range(normalized["n_vars"])))
        full_bits = eval_expr_bitset(expr, environment)
        resources["materialized_truth_bits"] = 1 << normalized["n_vars"]
    elif method == "bdd_autoref_restrict":
        bdd = ExactBddArtifact.build(
            expr, normalized["n_vars"], [f"x{i}" for i in range(normalized["n_vars"])],
            backend="autoref")
        resources["bdd_nodes"] = bdd.node_count
    elif method == "cadical_enumeration":
        formula = encode_expression_cnf(expr, normalized["n_vars"])
        if solver_factory is None:
            from pysat.solvers import Cadical195
            solver_factory = Cadical195
        solver = solver_factory(bootstrap_with=formula.clauses)
        resources.update({"clauses": len(formula.clauses), "maximum_variable": formula.max_var})
    timings["representation_ns"] = max(1, clock() - started)
    # Representation construction above is the complete resident setup.  The
    # separate compile field is retained for aligned lifecycle accounting.
    timings["compile_ns"] = 0

    rows = []
    cumulative_query_ns = 0
    checkpoint_query_ns: dict[str, int] = {}
    solve_calls = 0
    for query in trace:
        query_started = clock()
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        remaining = tuple(query["remaining_order"])
        if method == "direct_ast_restrict":
            reduced = _eval_ast_restricted(expr, normalized["n_vars"], fixed, remaining)
        elif method in {"flattened_cse_restrict", "cm_ir_restrict"}:
            template, full_mask = _bind_flat_program(program, remaining, fixed)
            reduced = PreparedFlatEvaluation(program, template, full_mask, False).evaluate()
        elif method == "direct_truth_cache":
            actual_remaining, reduced = restrict_full_truth(
                int(full_bits), normalized["n_vars"], fixed)
            _require(actual_remaining == remaining, "C35 truth-cache order mismatch")
        elif method == "bdd_autoref_restrict":
            actual_remaining, vector = bdd.restrict_truth_bits(fixed)
            _require(actual_remaining == remaining, "C35 BDD order mismatch")
            reduced = sum(int(value) << index for index, value in enumerate(vector))
        else:
            reduced = 0
            for residual_assignment in range(1 << len(remaining)):
                assumptions = []
                values = dict(fixed)
                for position, name in enumerate(remaining):
                    values[name] = (residual_assignment >>
                                    (len(remaining) - 1 - position)) & 1
                for index in range(normalized["n_vars"]):
                    value = values[f"x{index}"]
                    assumptions.append(index + 1 if value else -(index + 1))
                reduced |= int(bool(solver.solve(assumptions=assumptions))) << residual_assignment
                solve_calls += 1
        row = semantic_row(query, int(reduced), normalized["n_vars"])
        canonical_bytes(row)
        elapsed = max(1, clock() - query_started)
        cumulative_query_ns += elapsed
        rows.append(row)
        if len(rows) in CHECKPOINTS:
            checkpoint_query_ns[str(len(rows))] = cumulative_query_ns
    timings["query_total_ns"] = cumulative_query_ns

    cleanup_started = clock()
    if bdd is not None:
        bdd.close()
    if solver is not None:
        solver.delete()
    timings["cleanup_ns"] = max(1, clock() - cleanup_started)
    timings["task_total_ns"] = sum(value for key, value in timings.items()
                                    if key != "task_total_ns")
    setup_ns = timings["input_decode_ns"] + timings["representation_ns"] + timings["compile_ns"]
    checkpoint_total_ns = {
        key: setup_ns + value + timings["cleanup_ns"] for key, value in checkpoint_query_ns.items()
    }

    document = semantic_document(normalized["case_id"], rows)
    payload = canonical_bytes(document)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise RuntimeError("C35 method failed the exact partial-context oracle")
    resources["solve_calls"] = solve_calls
    resources["input_binding_cache_entries"] = len(program.bound_cache) if program is not None else 0
    result = {
        "schema": RESULT_SCHEMA,
        "contract_sha256": contract_digest(contract),
        "case_id": normalized["case_id"],
        "arm": method,
        "status": "ok",
        "reason": "completed",
        "timings_ns": timings,
        "artifact": {
            "kind": "context_answers",
            "output_scope": "not_applicable",
            "output_order": [f"x{i}" for i in range(normalized["n_vars"])],
            "bytes": len(payload),
            "sha256": actual,
        },
        "resources": resources,
        "identity": {
            "semantic_output": document,
            "trace_sha256": _digest(trace),
            "expression_v2_sha256": case["expression_v2_sha256"],
            "checkpoint_query_ns": checkpoint_query_ns,
            "checkpoint_total_ns": checkpoint_total_ns,
            "setup_total_ns": setup_ns,
            "exact_check_passed": True,
        },
    }
    validate_result(result, contract)
    return result
