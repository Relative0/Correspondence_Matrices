"""Bounded CM/CSE/raw-flat arms for contract and local-smoke verification.

This module is deliberately not a benchmark campaign.  It executes one
already-declared relation contract and returns auditable stage accounting.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from typing import Any, Callable

import numpy as np

from bitset_backend import (
    PreparedFlatEvaluation,
    _bind_flat_program,
    _eval_prepared_flat,
    build_bitset_env,
    compile_expr_cse,
    compile_expr_flat,
    eval_cm_node_flat,
    eval_cm_node_words,
    eval_expr_bitset,
    get_flat_program,
)
from cm_ir import compile_expr_to_cm_ir, materialize_cm, materialize_hybrid_no_reinflate
from cm_normalize import canonical_layout

from .contracts import RESULT_SCHEMA, contract_digest, validate_contract, validate_result
from .ir import cm_ir_stats, exact_diagnostic_record, expression_stats, flat_program_record


ARMS = frozenset({
    "cm_dense",
    "cm_flat_bigint",
    "cm_flat_words",
    "cm_no_reinflate",
    "cse_flat",
    "raw_flat",
    "direct_expr_bitset",
})
MAX_SMOKE_K = 8


def _semantic_bytes(bits: int, k: int) -> bytes:
    if type(bits) is not int or bits < 0 or type(k) is not int or k < 0:
        raise ValueError("invalid packed relation")
    size = max(1, ((1 << k) + 7) // 8)
    if bits >= 1 << (1 << k):
        raise ValueError("packed relation outside declared width")
    return bits.to_bytes(size, "little")


def semantic_sha256(bits: int, k: int) -> str:
    return hashlib.sha256(_semantic_bytes(bits, k)).hexdigest()


def dense_to_bits(value: np.ndarray) -> int:
    flat = np.asarray(value, dtype=np.uint8).reshape(-1)
    return int.from_bytes(np.packbits(flat, bitorder="little").tobytes(), "little")


def scalar_relation(expr: Any, variable_order: tuple[str, ...], fixed: Mapping[str, int]) -> int:
    """Independent scalar assignment loop; imports no CM/flat evaluator."""
    from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor

    def evaluate(node: Any, assignment: Mapping[str, int]) -> int:
        if isinstance(node, Var):
            return int(assignment[f"x{node.i}"])
        if isinstance(node, Not):
            return 1 - evaluate(node.a, assignment)
        left = evaluate(node.a, assignment)
        right = evaluate(node.b, assignment)
        if isinstance(node, And):
            return left & right
        if isinstance(node, Or):
            return left | right
        if isinstance(node, Xor):
            return left ^ right
        if isinstance(node, Imp):
            return (1 - left) | right
        if isinstance(node, Eqv):
            return 1 - (left ^ right)
        raise TypeError(node)

    output = 0
    k = len(variable_order)
    for index in range(1 << k):
        assignment = dict(fixed)
        for position, variable in enumerate(variable_order):
            if variable not in fixed:
                assignment[variable] = (index >> (k - 1 - position)) & 1
        output |= evaluate(expr, assignment) << index
    return output


def _stage(clock: Callable[[], int], function: Callable[[], Any]) -> tuple[Any, int]:
    started = clock()
    value = function()
    elapsed = clock() - started
    if type(elapsed) is not int or elapsed < 0:
        raise ValueError("nonmonotonic benchmark clock")
    return value, elapsed


def _execute_program(program: Any, variables: tuple[str, ...], fixed: Mapping[str, int]) -> int:
    template, full_mask = _bind_flat_program(program, variables, fixed)
    return _eval_prepared_flat(PreparedFlatEvaluation(program, template, full_mask, False))


def execute_arm(
    *,
    expr: Any,
    contract: Mapping[str, Any],
    case_id: str,
    arm: str,
    clock: Callable[[], int] = time.perf_counter_ns,
    smoke_bound: int | None = None,
) -> dict[str, Any]:
    """Execute one exact relation arm; correctness validation remains outside."""
    normalized = validate_contract(contract)
    if normalized["task"] != "complete_relation" or arm not in ARMS:
        raise ValueError("unsupported local comparative arm/task")
    variables = normalized["variable_order"]
    output_variables = normalized["output_order"]
    fixed = normalized["fixed"]
    if smoke_bound is not None and (type(smoke_bound) is not int or len(variables) > smoke_bound):
        raise ValueError("local smoke variable bound")
    kind = normalized["kind"]
    allowed_kind = {
        "cm_dense": {"dense_cm"},
        "cm_flat_bigint": {"packed_bigint"},
        "cm_flat_words": {"packed_words"},
        "cm_no_reinflate": {"packed_bigint", "reduced_bigint"},
        "cse_flat": {"packed_bigint"},
        "raw_flat": {"packed_bigint"},
        "direct_expr_bitset": {"packed_bigint"},
    }[arm]
    if kind not in allowed_kind:
        raise ValueError("arm cannot deliver declared artifact")

    timings: dict[str, int] = {}
    diagnostics: dict[str, Any] = {"timing_enabled": 1}
    node = program = None
    expr_info = expression_stats(expr)
    started = clock()

    if arm.startswith("cm_"):
        node, timings["prepare_ir_ns"] = _stage(
            clock,
            lambda: compile_expr_to_cm_ir(
                expr,
                diagnostics=diagnostics,
                reuse_cache=False,
                persistent_cache=False,
                share_aware_flatten=True,
            ),
        )
        if arm in {"cm_flat_bigint", "cm_flat_words"}:
            program, timings["lower_flat_ns"] = _stage(clock, lambda: get_flat_program(node))
    elif arm == "cse_flat":
        program, timings["prepare_cse_flat_ns"] = _stage(clock, lambda: compile_expr_cse(expr, flatten=True))
    elif arm == "raw_flat":
        program, timings["prepare_raw_flat_ns"] = _stage(clock, lambda: compile_expr_flat(expr))
    else:
        if fixed:
            raise ValueError("direct expression BitSet complete relation requires no fixed axes")
        environment, timings["prepare_environment_ns"] = _stage(
            clock, lambda: build_bitset_env(variables))

    native_bytes: int
    if arm == "cm_dense":
        rows, columns = canonical_layout(list(variables))
        value, timings["execute_ns"] = _stage(
            clock,
            lambda: materialize_cm(
                node,
                rows,
                columns,
                fixed,
                diagnostics=diagnostics,
                materialize_mode="numpy",
                output_budget=None,
            ),
        )
        bits, timings["deliver_ns"] = _stage(clock, lambda: dense_to_bits(value))
        native_bytes = int(value.nbytes)
    elif arm == "cm_flat_bigint":
        bits, timings["execute_ns"] = _stage(clock, lambda: eval_cm_node_flat(node, variables, fixed=fixed))
        delivered, timings["deliver_ns"] = _stage(clock, lambda: _semantic_bytes(bits, len(output_variables)))
        native_bytes = len(delivered)
    elif arm == "cm_flat_words":
        bits, timings["execute_ns"] = _stage(clock, lambda: eval_cm_node_words(node, variables, fixed=fixed))
        delivered, timings["deliver_ns"] = _stage(clock, lambda: _semantic_bytes(bits, len(output_variables)))
        native_bytes = max(8, len(delivered))
    elif arm == "cm_no_reinflate":
        reduced = normalized["output_scope"] == "reduced"
        result, timings["execute_ns"] = _stage(
            clock,
            lambda: materialize_hybrid_no_reinflate(
                node,
                variables,
                fixed=fixed,
                diagnostics=diagnostics,
                hybrid_threshold=max(8, len(output_variables)),
                allow_reduced_output=reduced,
                max_full_output_vars=(len(output_variables) if reduced else None),
                output_budget=None,
                flat_eval=True,
                words_eval=False,
            ),
        )
        if result.bits is None or tuple(result.output_vars) != output_variables:
            raise ValueError("no-reinflation result did not match declared packed artifact")
        bits = int(result.bits)
        delivered, timings["deliver_ns"] = _stage(clock, lambda: _semantic_bytes(bits, len(output_variables)))
        native_bytes = len(delivered)
    elif arm == "cse_flat":
        bits, timings["execute_ns"] = _stage(clock, lambda: _execute_program(program, variables, fixed))
        delivered, timings["deliver_ns"] = _stage(clock, lambda: _semantic_bytes(bits, len(output_variables)))
        native_bytes = len(delivered)
    elif arm == "raw_flat":
        bits, timings["execute_ns"] = _stage(clock, lambda: _execute_program(program, variables, fixed))
        delivered, timings["deliver_ns"] = _stage(clock, lambda: _semantic_bytes(bits, len(output_variables)))
        native_bytes = len(delivered)
    else:
        bits, timings["execute_ns"] = _stage(
            clock, lambda: eval_expr_bitset(expr, environment))
        delivered, timings["deliver_ns"] = _stage(
            clock, lambda: _semantic_bytes(bits, len(output_variables)))
        native_bytes = len(delivered)

    task_total = clock() - started
    if type(task_total) is not int or task_total < 0:
        raise ValueError("nonmonotonic total clock")
    timings["task_total_ns"] = task_total
    digest = semantic_sha256(bits, len(output_variables))
    identity: dict[str, Any] = {
        "semantic_hash": "little_endian_assignment_bits/v1",
        "expression": expr_info,
    }
    if node is not None:
        identity["cm_ir"] = cm_ir_stats(node)
        identity["cm_diagnostics"] = exact_diagnostic_record(diagnostics)
    if program is not None:
        identity["flat_program"] = flat_program_record(program)
    result = {
        "schema": RESULT_SCHEMA,
        "contract_sha256": contract_digest(contract),
        "case_id": case_id,
        "arm": arm,
        "status": "ok",
        "reason": "completed",
        "timings_ns": timings,
        "artifact": {
            "kind": kind,
            "output_scope": normalized["output_scope"],
            "output_order": list(output_variables),
            "bytes": native_bytes,
            "sha256": digest,
        },
        "resources": {"measurement": "in_process_trivial_smoke", "rss_measured": False},
        "identity": identity,
    }
    validate_result(result, contract)
    return result
