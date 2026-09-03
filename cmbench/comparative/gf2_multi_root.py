"""Genuine sibling-output arithmetic workloads and deterministic union DAGs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

from cmbench.recognition.yosys_unused_gf2_data import (
    _add_vectors,
    _product_vector,
    _variable_map,
)

from .gf2_wide_repeated_queries import build_query_trace


_BINARY = {
    And: "and",
    Or: "or",
    Xor: "xor",
    Imp: "imp",
    Eqv: "eqv",
}


def expressions_to_multi_root_dag(roots: tuple[Expr, ...]) -> dict[str, Any]:
    """Serialize several roots to one structurally deduplicated topological DAG."""
    if len(roots) < 2:
        raise ValueError("multi-root serialization requires at least two roots")
    nodes: list[dict[str, Any]] = []
    by_structure: dict[tuple[object, ...], int] = {}
    by_identity: dict[int, int] = {}
    alive: list[Expr] = []
    for root in roots:
        stack: list[tuple[Expr, bool]] = [(root, False)]
        scheduled: set[int] = set()
        while stack:
            expression, processed = stack.pop()
            identity = id(expression)
            if identity in by_identity:
                continue
            if processed:
                if isinstance(expression, Var):
                    entry: dict[str, Any] = {"op": "var", "i": int(expression.i)}
                    key: tuple[object, ...] = ("var", int(expression.i))
                elif isinstance(expression, Not):
                    a = by_identity[id(expression.a)]
                    entry = {"op": "not", "a": a}
                    key = ("not", a)
                else:
                    for node_type, opcode in _BINARY.items():
                        if isinstance(expression, node_type):
                            break
                    else:
                        raise TypeError(expression)
                    a = by_identity[id(expression.a)]
                    b = by_identity[id(expression.b)]
                    entry = {"op": opcode, "a": a, "b": b}
                    key = (opcode, a, b)
                index = by_structure.get(key)
                if index is None:
                    index = len(nodes)
                    nodes.append(entry)
                    by_structure[key] = index
                by_identity[identity] = index
                continue
            if identity in scheduled:
                continue
            scheduled.add(identity)
            alive.append(expression)
            stack.append((expression, True))
            if isinstance(expression, Var):
                continue
            if isinstance(expression, Not):
                stack.append((expression.a, False))
                continue
            if isinstance(expression, tuple(_BINARY)):
                stack.append((expression.b, False))
                stack.append((expression.a, False))
                continue
            raise TypeError(expression)
    return {
        "version": 2,
        "nodes": nodes,
        "roots": [by_identity[id(root)] for root in roots],
    }


@dataclass(frozen=True)
class MultiRootWorkload:
    workload_id: str
    family: str
    n_vars: int
    roots: tuple[Expr, ...]

    @property
    def trace(self) -> list[dict[str, Any]]:
        return build_query_trace(self.workload_id, self.n_vars)

    @property
    def union_document(self) -> dict[str, Any]:
        return expressions_to_multi_root_dag(self.roots)

    @property
    def separate_documents(self) -> tuple[dict[str, Any], ...]:
        return tuple(expr_to_json_dag(root) for root in self.roots)


def _multiply_workload(workload_id: str, output_bits: tuple[int, ...]) -> MultiRootWorkload:
    specifications = tuple(
        [("A", bit) for bit in range(8)] + [("B", bit) for bit in range(8)])
    variables = _variable_map(specifications)
    product = _product_vector(variables, 8, 8)
    return MultiRootWorkload(
        workload_id=workload_id,
        family="multiply_sibling_outputs",
        n_vars=16,
        roots=tuple(product[bit] for bit in output_bits if product[bit] is not None),
    )


def _add_workload() -> MultiRootWorkload:
    specifications = tuple(
        [("A", bit) for bit in range(8)] + [("B", bit) for bit in range(8)])
    variables = _variable_map(specifications)
    result = _add_vectors(
        [variables[("A", bit)] for bit in range(8)],
        [variables[("B", bit)] for bit in range(8)],
    )
    return MultiRootWorkload(
        "multi-add8-bits456", "add_sibling_outputs", 16,
        tuple(result[bit] for bit in (4, 5, 6) if result[bit] is not None),
    )


def _popcount_workload() -> MultiRootWorkload:
    specifications = tuple(("din", bit) for bit in range(16))
    variables = _variable_map(specifications)
    accumulated: list[Expr | None] = []
    for bit in range(16):
        accumulated = _add_vectors(accumulated, [variables[("din", bit)]])
    return MultiRootWorkload(
        "multi-popcount16-bits123", "popcount_sibling_outputs", 16,
        tuple(accumulated[bit] for bit in (1, 2, 3) if accumulated[bit] is not None),
    )


def _addertree_workload() -> MultiRootWorkload:
    specifications = tuple((f"din{word}", bit) for word in range(4) for bit in range(4))
    variables = _variable_map(specifications)
    accumulated: list[Expr | None] = []
    for word in range(4):
        accumulated = _add_vectors(
            accumulated, [variables[(f"din{word}", bit)] for bit in range(4)])
    return MultiRootWorkload(
        "multi-addertree4x4-bits234", "addertree_sibling_outputs", 16,
        tuple(accumulated[bit] for bit in (2, 3, 4) if accumulated[bit] is not None),
    )


def _multiply_add_workload() -> MultiRootWorkload:
    specifications = tuple(
        [("A", bit) for bit in range(5)]
        + [("B", bit) for bit in range(5)]
        + [("C", bit) for bit in range(6)])
    variables = _variable_map(specifications)
    product = _product_vector(variables, 5, 5)
    result = _add_vectors(product, [variables[("C", bit)] for bit in range(6)])
    return MultiRootWorkload(
        "multi-muladd5x5c6-bits345", "multiply_add_sibling_outputs", 16,
        tuple(result[bit] for bit in (3, 4, 5) if result[bit] is not None),
    )


def sibling_output_workloads() -> tuple[MultiRootWorkload, ...]:
    workloads = (
        _multiply_workload("multi-multiply8-bits345", (3, 4, 5)),
        _multiply_workload("multi-multiply8-bits567", (5, 6, 7)),
        _add_workload(),
        _popcount_workload(),
        _addertree_workload(),
        _multiply_add_workload(),
    )
    if any(len(workload.roots) != 3 for workload in workloads):
        raise AssertionError("multi-root workload cardinality")
    return workloads


def _prospective_multiply(
    workload_id: str,
    a_width: int,
    b_width: int,
    output_bits: tuple[int, int, int],
) -> MultiRootWorkload:
    specifications = tuple(
        [("A", bit) for bit in range(a_width)]
        + [("B", bit) for bit in range(b_width)]
    )
    variables = _variable_map(specifications)
    product = _product_vector(variables, a_width, b_width)
    return MultiRootWorkload(
        workload_id,
        "multiply_sibling_outputs",
        len(specifications),
        tuple(product[bit] for bit in output_bits if product[bit] is not None),
    )


def _prospective_add(width: int, output_bits: tuple[int, int, int]) -> MultiRootWorkload:
    specifications = tuple(
        [("A", bit) for bit in range(width)]
        + [("B", bit) for bit in range(width)]
    )
    variables = _variable_map(specifications)
    result = _add_vectors(
        [variables[("A", bit)] for bit in range(width)],
        [variables[("B", bit)] for bit in range(width)],
    )
    return MultiRootWorkload(
        f"c37-multi-add{width}-bits{''.join(map(str, output_bits))}",
        "add_sibling_outputs",
        len(specifications),
        tuple(result[bit] for bit in output_bits if result[bit] is not None),
    )


def _prospective_popcount(inputs: int) -> MultiRootWorkload:
    specifications = tuple(("din", bit) for bit in range(inputs))
    variables = _variable_map(specifications)
    accumulated: list[Expr | None] = []
    for bit in range(inputs):
        accumulated = _add_vectors(accumulated, [variables[("din", bit)]])
    output_bits = (1, 2, 3)
    return MultiRootWorkload(
        f"c37-multi-popcount{inputs}-bits123",
        "popcount_sibling_outputs",
        inputs,
        tuple(accumulated[bit] for bit in output_bits if accumulated[bit] is not None),
    )


def _prospective_addertree(words: int, width: int) -> MultiRootWorkload:
    specifications = tuple(
        (f"din{word}", bit) for word in range(words) for bit in range(width)
    )
    variables = _variable_map(specifications)
    accumulated: list[Expr | None] = []
    for word in range(words):
        accumulated = _add_vectors(
            accumulated,
            [variables[(f"din{word}", bit)] for bit in range(width)],
        )
    output_bits = (2, 3, 4)
    return MultiRootWorkload(
        f"c37-multi-addertree{words}x{width}-bits234",
        "addertree_sibling_outputs",
        len(specifications),
        tuple(accumulated[bit] for bit in output_bits if accumulated[bit] is not None),
    )


def _prospective_multiply_add(
    a_width: int,
    b_width: int,
    c_width: int,
) -> MultiRootWorkload:
    specifications = tuple(
        [("A", bit) for bit in range(a_width)]
        + [("B", bit) for bit in range(b_width)]
        + [("C", bit) for bit in range(c_width)]
    )
    variables = _variable_map(specifications)
    product = _product_vector(variables, a_width, b_width)
    result = _add_vectors(
        product, [variables[("C", bit)] for bit in range(c_width)]
    )
    output_bits = (2, 3, 4)
    return MultiRootWorkload(
        f"c37-multi-muladd{a_width}x{b_width}c{c_width}-bits234",
        "multiply_add_sibling_outputs",
        len(specifications),
        tuple(result[bit] for bit in output_bits if result[bit] is not None),
    )


def prospective_sibling_output_workloads() -> tuple[MultiRootWorkload, ...]:
    """Return the timing-blind, parameter-disjoint C37 confirmation workloads."""
    workloads = (
        _prospective_multiply("c37-multi-multiply7x7-bits234", 7, 7, (2, 3, 4)),
        _prospective_multiply("c37-multi-multiply8x7-bits456", 8, 7, (4, 5, 6)),
        _prospective_add(7, (3, 4, 5)),
        _prospective_popcount(15),
        _prospective_addertree(3, 5),
        _prospective_multiply_add(4, 4, 7),
    )
    development_ids = {row.workload_id for row in sibling_output_workloads()}
    if (
        len(workloads) != 6
        or len({row.workload_id for row in workloads}) != len(workloads)
        or development_ids.intersection(row.workload_id for row in workloads)
        or any(len(row.roots) != 3 or not 11 <= row.n_vars <= 16 for row in workloads)
    ):
        raise AssertionError("invalid prospective multi-root workload freeze")
    return workloads
