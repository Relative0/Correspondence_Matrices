"""C36 exact repeated restrictions on fresh width-11..16 natural functions."""
from __future__ import annotations

import copy
import hashlib
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np

from bitset_backend import (
    bitset_to_bool_array,
    build_bitset_env,
    eval_cm_node_words,
    eval_expr_bitset,
    eval_expr_words_cse,
    get_expr_cse_program,
    get_flat_program,
)
from cm_expr_serde import expr_from_json
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir

from cmbench.recognition.yosys_wide_restriction_data import (
    DATASET_SCHEMA, WIDTHS, truth_sha256_wide,
)

from .contracts import (
    CONTRACT_SCHEMA,
    RESULT_SCHEMA,
    canonical_bytes,
    contract_digest,
    validate_contract,
    validate_result,
)


SEMANTIC_SCHEMA = "crse-c36-wide-partial-context-output/v1"
METHODS = (
    "direct_ast_restrict",
    "flattened_cse_words",
    "cm_ir_words",
    "compiled_truth_projection",
)
CHECKPOINTS = (1, 4, 16, 64)
LIVE_WIDTHS = (6, 8, 10)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_wide_case(case: Mapping[str, Any]) -> dict[str, Any]:
    required = {"case_id", "cluster_id", "family", "n_vars", "truth_bits_hex",
                "truth_sha256", "expression_v2", "expression_v2_sha256",
                "selection_sha256"}
    _require(isinstance(case, Mapping) and required.issubset(case), "C36 case fields")
    n_vars = case["n_vars"]
    _require(type(n_vars) is int and n_vars in WIDTHS, "C36 width must be 11..16")
    bits = int(case["truth_bits_hex"], 16)
    _require(truth_sha256_wide(bits, n_vars) == case["truth_sha256"], "C36 truth identity")
    _require(hashlib.sha256(canonical_bytes(case["expression_v2"])).hexdigest()
             == case["expression_v2_sha256"], "C36 expression identity")
    return {"case_id": case["case_id"], "n_vars": n_vars, "bits": bits}


def build_query_trace(case_id: str, n_vars: int) -> list[dict[str, Any]]:
    _require(isinstance(case_id, str) and case_id and n_vars in WIDTHS,
             "invalid C36 trace identity")
    rows = []
    for query in range(64):
        seed = hashlib.sha256(f"c36:{case_id}:{query}".encode("ascii")).digest()
        live_count = min(n_vars - 1, LIVE_WIDTHS[seed[0] % len(LIVE_WIDTHS)])
        ordered = sorted(range(n_vars),
                         key=lambda index: hashlib.sha256(seed + bytes([index])).digest())
        fixed_indices = set(ordered[:n_vars - live_count])
        fixed = []
        for offset, index in enumerate(sorted(fixed_indices)):
            fixed.append({"variable": f"x{index}",
                          "value": (seed[1 + offset] >> (index % 8)) & 1})
        row = {
            "query": query,
            "fixed": fixed,
            "remaining_order": [f"x{i}" for i in range(n_vars) if i not in fixed_indices],
        }
        row["query_sha256"] = _digest(row)
        rows.append(row)
    return rows


def validate_query_trace(trace: Any, case_id: str, n_vars: int) -> list[dict[str, Any]]:
    expected = build_query_trace(case_id, n_vars)
    _require(isinstance(trace, list) and trace == expected, "C36 frozen query trace")
    return expected


def restrict_full_truth(bits: int, n_vars: int,
                        fixed: Mapping[str, int]) -> tuple[tuple[str, ...], int]:
    fixed_indices = {int(name[1:]): value for name, value in fixed.items()}
    _require(1 <= len(fixed_indices) < n_vars
             and all(0 <= index < n_vars and type(value) is int and value in (0, 1)
                     for index, value in fixed_indices.items()), "invalid C36 restriction")
    remaining = tuple(index for index in range(n_vars) if index not in fixed_indices)
    reduced = 0
    for residual in range(1 << len(remaining)):
        values = dict(fixed_indices)
        for position, index in enumerate(remaining):
            values[index] = (residual >> (len(remaining) - 1 - position)) & 1
        original = 0
        for index in range(n_vars):
            original = (original << 1) | values[index]
        reduced |= ((bits >> original) & 1) << residual
    return tuple(f"x{index}" for index in remaining), reduced


def projection_indices(n_vars: int, fixed: Mapping[str, int],
                       remaining: Sequence[str]) -> np.ndarray:
    """Compile one restriction to original truth-vector row indices."""
    remaining_indices = tuple(int(name[1:]) for name in remaining)
    rows = np.arange(1 << len(remaining_indices), dtype=np.uint32)
    indices = np.zeros(rows.shape, dtype=np.uint32)
    fixed_indices = {int(name[1:]): value for name, value in fixed.items()}
    _require(set(remaining_indices).isdisjoint(fixed_indices)
             and set(remaining_indices) | set(fixed_indices) == set(range(n_vars)),
             "C36 projection axis partition")
    for index, value in fixed_indices.items():
        if value:
            indices |= np.uint32(1 << (n_vars - 1 - index))
    for position, index in enumerate(remaining_indices):
        values = (rows >> np.uint32(len(remaining_indices) - 1 - position)) & np.uint32(1)
        indices |= values << np.uint32(n_vars - 1 - index)
    indices.flags.writeable = False
    return indices


def project_truth_vector(vector: np.ndarray, indices: np.ndarray) -> int:
    selected = np.asarray(vector[indices], dtype=np.uint8)
    return int.from_bytes(np.packbits(selected, bitorder="little").tobytes(), "little")


def _canonical_witness(reduced: int, remaining: Sequence[str], fixed: Mapping[str, int],
                       n_vars: int) -> list[dict[str, Any]] | None:
    if reduced == 0:
        return None
    residual = (reduced & -reduced).bit_length() - 1
    values = dict(fixed)
    for position, name in enumerate(remaining):
        values[name] = (residual >> (len(remaining) - 1 - position)) & 1
    return [{"variable": f"x{i}", "value": values[f"x{i}"]} for i in range(n_vars)]


def semantic_row(query: Mapping[str, Any], reduced: int, n_vars: int) -> dict[str, Any]:
    remaining = tuple(query["remaining_order"])
    fixed = {row["variable"]: row["value"] for row in query["fixed"]}
    byte_count = max(1, ((1 << len(remaining)) + 7) // 8)
    return {
        "query": query["query"], "query_sha256": query["query_sha256"],
        "fixed": list(query["fixed"]), "remaining_order": list(remaining),
        "truth_bits_hex": format(reduced, "x"),
        "truth_sha256": hashlib.sha256(reduced.to_bytes(byte_count, "little")).hexdigest(),
        "exact_count": reduced.bit_count(), "satisfiable": bool(reduced),
        "canonical_witness": _canonical_witness(reduced, remaining, fixed, n_vars),
    }


def semantic_document(case_id: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {"schema": SEMANTIC_SCHEMA, "case_id": case_id, "rows": list(rows)}


def oracle_document(case: Mapping[str, Any], trace: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = validate_wide_case(case)
    validate_query_trace(list(trace), normalized["case_id"], normalized["n_vars"])
    rows = []
    for query in trace:
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        remaining, reduced = restrict_full_truth(normalized["bits"], normalized["n_vars"], fixed)
        _require(remaining == tuple(query["remaining_order"]), "C36 oracle axis order")
        rows.append(semantic_row(query, reduced, normalized["n_vars"]))
    return semantic_document(normalized["case_id"], rows)


def attach_query_contracts(dataset: Mapping[str, Any]) -> dict[str, Any]:
    output = copy.deepcopy(dataset)
    for case in output["cases"]:
        trace = build_query_trace(case["case_id"], case["n_vars"])
        case["c36_trace"] = trace
        case["c36_trace_sha256"] = _digest(trace)
        case["c36_required_output_sha256"] = _digest(oracle_document(case, trace))
    output["query_contract"] = {
        "queries_per_case": 64, "checkpoints": list(CHECKPOINTS),
        "live_widths": list(LIVE_WIDTHS),
        "selection_uses_outputs_or_timings": False,
    }
    validate_dataset(output)
    return output


def validate_dataset(dataset: Mapping[str, Any]) -> dict[str, Any]:
    from cmbench.recognition.yosys_wide_restriction_data import validate_dataset as validate_source
    validate_source(dict(dataset))
    _require(dataset.get("query_contract") == {
        "queries_per_case": 64, "checkpoints": list(CHECKPOINTS),
        "live_widths": list(LIVE_WIDTHS), "selection_uses_outputs_or_timings": False,
    }, "C36 query contract")
    for case in dataset["cases"]:
        trace = validate_query_trace(case.get("c36_trace"), case["case_id"], case["n_vars"])
        _require(case.get("c36_trace_sha256") == _digest(trace)
                 and case.get("c36_required_output_sha256") == _digest(oracle_document(case, trace)),
                 "C36 trace/oracle binding")
    return {"cases": 18, "queries": 1152}


def task_contract(case: Mapping[str, Any], method: str) -> dict[str, Any]:
    normalized = validate_wide_case(case)
    _require(method in METHODS, "unknown C36 method")
    variables = [f"x{i}" for i in range(normalized["n_vars"])]
    contract = {
        "schema": CONTRACT_SCHEMA, "contract_id": f"c36:{normalized['case_id']}:{method}",
        "task": "partial_context",
        "artifact": {"kind": "context_answers", "variable_order": variables,
                     "output_order": variables, "fixed": [], "output_scope": "not_applicable",
                     "restoration": "none", "stream": None},
        "lifecycle": "resident_engine", "queries": 64,
        "validation": {"oracle": "independent_scalar_and_full_projection/v1",
                       "validation_in_timed_span": False,
                       "required_output_sha256": case["c36_required_output_sha256"]},
    }
    validate_contract(contract)
    return contract


def _eval_ast_restricted(expr: Expr, fixed: Mapping[str, int],
                         remaining: Sequence[str]) -> int:
    env = build_bitset_env(tuple(remaining))
    full_mask = (1 << (1 << len(remaining))) - 1

    def rec(node: Expr) -> int:
        if isinstance(node, Var):
            name = f"x{node.i}"
            return full_mask if fixed.get(name) == 1 else (0 if name in fixed else int(env[name]))
        if isinstance(node, Not):
            return (~rec(node.a)) & full_mask
        left, right = rec(node.a), rec(node.b)
        if isinstance(node, And): return left & right
        if isinstance(node, Or): return left | right
        if isinstance(node, Xor): return left ^ right
        if isinstance(node, Imp): return ((~left) | right) & full_mask
        if isinstance(node, Eqv): return (~(left ^ right)) & full_mask
        raise TypeError(node)
    return rec(expr)


def execute_session(*, case: Mapping[str, Any], contract: Mapping[str, Any], method: str,
                    clock: Callable[[], int] = time.perf_counter_ns) -> dict[str, Any]:
    normalized = validate_wide_case(case)
    normalized_contract = validate_contract(contract)
    _require(method in METHODS and normalized_contract["task"] == "partial_context"
             and contract["contract_id"] == f"c36:{normalized['case_id']}:{method}",
             "C36 task/method contract")
    trace = validate_query_trace(case.get("c36_trace"), normalized["case_id"],
                                 normalized["n_vars"])
    expected = _digest(oracle_document(case, trace))
    _require(expected == case.get("c36_required_output_sha256")
             == contract["validation"]["required_output_sha256"], "C36 oracle mismatch")
    timings = {"input_decode_ns": 0, "representation_ns": 0, "query_total_ns": 0,
               "cleanup_ns": 0, "task_total_ns": 0}
    resources: dict[str, Any] = {}
    started = clock()
    expression = expr_from_json(case["expression_v2"])
    timings["input_decode_ns"] = max(1, clock() - started)
    node = program = truth_vector = plans = None
    started = clock()
    if method == "flattened_cse_words":
        program = get_expr_cse_program(expression, flatten=True)
        resources.update({"program_slots": program.n_slots, "program_ops": len(program.ops),
                          "kernel": "numpy_words_at_live_width_ge_6"})
    elif method == "cm_ir_words":
        node = compile_expr_to_cm_ir(expression, reuse_cache=False, persistent_cache=False,
                                     share_aware_flatten=True)
        program = get_flat_program(node)
        resources.update({"program_slots": program.n_slots, "program_ops": len(program.ops),
                          "kernel": "numpy_words_at_live_width_ge_6"})
    elif method == "compiled_truth_projection":
        names = tuple(f"x{i}" for i in range(normalized["n_vars"]))
        full_bits = eval_expr_bitset(expression, build_bitset_env(names))
        truth_vector = bitset_to_bool_array(full_bits, normalized["n_vars"])
        plans = []
        for query in trace:
            fixed = {row["variable"]: row["value"] for row in query["fixed"]}
            plans.append(projection_indices(normalized["n_vars"], fixed,
                                            query["remaining_order"]))
        resources.update({"materialized_truth_bits": 1 << normalized["n_vars"],
                          "compiled_projection_index_bytes": sum(plan.nbytes for plan in plans)})
    timings["representation_ns"] = max(1, clock() - started)
    rows = []
    cumulative = 0
    checkpoint_query: dict[str, int] = {}
    for index, query in enumerate(trace):
        started = clock()
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        remaining = tuple(query["remaining_order"])
        if method == "direct_ast_restrict":
            reduced = _eval_ast_restricted(expression, fixed, remaining)
        elif method == "flattened_cse_words":
            reduced = eval_expr_words_cse(expression, remaining, fixed=fixed, flatten=True)
        elif method == "cm_ir_words":
            reduced = eval_cm_node_words(node, remaining, fixed=fixed)
        else:
            reduced = project_truth_vector(truth_vector, plans[index])
        row = semantic_row(query, int(reduced), normalized["n_vars"])
        canonical_bytes(row)
        cumulative += max(1, clock() - started)
        rows.append(row)
        if len(rows) in CHECKPOINTS:
            checkpoint_query[str(len(rows))] = cumulative
    timings["query_total_ns"] = cumulative
    started = clock()
    node = program = truth_vector = plans = None
    timings["cleanup_ns"] = max(1, clock() - started)
    timings["task_total_ns"] = sum(value for key, value in timings.items()
                                    if key != "task_total_ns")
    setup = timings["input_decode_ns"] + timings["representation_ns"]
    checkpoint_total = {key: setup + value + timings["cleanup_ns"]
                        for key, value in checkpoint_query.items()}
    document = semantic_document(normalized["case_id"], rows)
    payload = canonical_bytes(document)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise RuntimeError("C36 method failed the exact frozen oracle")
    result = {
        "schema": RESULT_SCHEMA, "contract_sha256": contract_digest(contract),
        "case_id": normalized["case_id"], "arm": method, "status": "ok",
        "reason": "completed", "timings_ns": timings,
        "artifact": {"kind": "context_answers", "output_scope": "not_applicable",
                     "output_order": [f"x{i}" for i in range(normalized["n_vars"])],
                     "bytes": len(payload), "sha256": actual},
        "resources": resources,
        "identity": {"semantic_output": document,
                     "trace_sha256": _digest(trace),
                     "expression_v2_sha256": case["expression_v2_sha256"],
                     "checkpoint_query_ns": checkpoint_query,
                     "checkpoint_total_ns": checkpoint_total,
                     "setup_total_ns": setup, "exact_check_passed": True},
    }
    validate_result(result, contract)
    return result
