"""Deterministic O(DAG) structural accounting for comparative CM studies."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from bitset_backend import FlatProgram, program_metrics
from cm_expr_serde import expr_to_json_dag

from .contracts import canonical_bytes


def expression_stats(expr: Any, *, unfolded_limit: int = 1_000_000_000) -> dict[str, Any]:
    """Count object/structural DAGs and bounded tree unfolding iteratively."""
    if type(unfolded_limit) is not int or unfolded_limit < 1:
        raise ValueError("unfolded limit must be a positive integer")
    document = expr_to_json_dag(expr)
    structural_nodes = len(document["nodes"])

    seen: set[int] = set()
    alive: list[Any] = []
    stack = [expr]
    while stack:
        node = stack.pop()
        marker = id(node)
        if marker in seen:
            continue
        seen.add(marker)
        alive.append(node)
        for name in ("a", "b"):
            child = getattr(node, name, None)
            if child is not None:
                stack.append(child)

    counts: dict[int, int] = {}
    stack2 = [(expr, False)]
    capped = False
    while stack2:
        node, processed = stack2.pop()
        marker = id(node)
        if marker in counts:
            continue
        children = tuple(getattr(node, name) for name in ("a", "b") if hasattr(node, name))
        if not processed:
            stack2.append((node, True))
            for child in children:
                if id(child) not in counts:
                    stack2.append((child, False))
            continue
        total = 1
        for child in children:
            total += counts[id(child)]
            if total > unfolded_limit:
                total = unfolded_limit + 1
                capped = True
                break
        counts[marker] = total
    unfolded = counts[id(expr)]
    if unfolded > unfolded_limit:
        unfolded = None
        capped = True
    return {
        "object_dag_nodes": len(seen),
        "structural_dag_nodes": structural_nodes,
        "unfolded_occurrences": unfolded,
        "unfolded_limit": unfolded_limit,
        "unfolded_capped": capped,
        "sharing_factor": (None if unfolded is None else unfolded / structural_nodes),
        "expression_v2_sha256": hashlib.sha256(canonical_bytes(document)).hexdigest(),
    }


def cm_dag_signature(node: Any) -> tuple[tuple[Any, ...], ...]:
    """Exact ordered CM-DAG signature without unfolding deep public keys."""
    index_by_id: dict[int, int] = {}
    records: list[tuple[Any, ...]] = []
    stack = [(node, False)]
    while stack:
        current, processed = stack.pop()
        marker = id(current)
        if marker in index_by_id:
            continue
        if not processed:
            stack.append((current, True))
            for child in reversed(current.args):
                if id(child) not in index_by_id:
                    stack.append((child, False))
            continue
        children = tuple(index_by_id[id(child)] for child in current.args)
        index_by_id[marker] = len(records)
        records.append((current.kind, current.vars, current.const_value, current.op, children, current.var_name))
    return tuple(records)


def cm_ir_stats(node: Any) -> dict[str, Any]:
    signature = cm_dag_signature(node)
    kinds: dict[str, int] = {}
    transpose_candidates = 0
    for kind, variables, _const, op, children, _var in signature:
        label = op if kind == "op" else kind
        kinds[label] = kinds.get(label, 0) + 1
        if len(children) > 1 and variables:
            transpose_candidates += 1
    return {
        "cm_ir_nodes": len(signature),
        "cm_ir_kinds": dict(sorted(kinds.items())),
        "cm_ir_root_variables": list(node.vars),
        "cm_ir_signature_sha256": hashlib.sha256(canonical_bytes(signature)).hexdigest(),
        "multi_child_alignment_candidates": transpose_candidates,
    }


def flat_program_record(program: FlatProgram) -> dict[str, Any]:
    loads = [[int(slot), str(kind), payload] for slot, kind, payload in program.loads]
    ops = [[int(slot), int(opcode), [int(value) for value in args]] for slot, opcode, args in program.ops]
    structure = {
        "n_slots": int(program.n_slots),
        "root_slot": int(program.root_slot),
        "loads": loads,
        "ops": ops,
    }
    return {
        **program_metrics(program),
        "flat_program_sha256": hashlib.sha256(canonical_bytes(structure)).hexdigest(),
    }


def exact_diagnostic_record(diagnostics: Mapping[str, Any]) -> dict[str, int | float | str | None]:
    """Keep bounded scalar diagnostics and reject nested/opaque values."""
    output: dict[str, int | float | str | None] = {}
    for key, value in diagnostics.items():
        if not isinstance(key, str) or len(key) > 128:
            raise ValueError("invalid diagnostic key")
        if type(value) is int:
            output[key] = value
        elif type(value) is float:
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError("nonfinite diagnostic")
            output[key] = value
        elif isinstance(value, str) and len(value) <= 256:
            output[key] = value
        elif value is None:
            output[key] = None
        else:
            raise ValueError("unsupported diagnostic value")
    return dict(sorted(output.items()))
