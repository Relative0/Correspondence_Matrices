"""Tests for the v2 defs/ref DAG serialization schema (2026-08-02 repair)."""
from __future__ import annotations

import json

import numpy as np
import pytest

from cm_expr_serde import (
    EXPR_SCHEMA_VERSION_DAG,
    expr_from_json,
    expr_to_json,
    expr_to_json_dag,
)
from cm_exprlib import And, Not, Or, Var, Xor, eval_expr_tt


def _identity_nodes(expr):
    seen = set()
    stack = [expr]
    while stack:
        e = stack.pop()
        if id(e) in seen:
            continue
        seen.add(id(e))
        if isinstance(e, Not):
            stack.append(e.a)
        elif not isinstance(e, Var):
            stack.extend((e.a, e.b))
    return len(seen)


def _shared_dag():
    h = Xor(Xor(Var(0), Var(1)), Var(2))
    return And(Or(h, Var(3)), Xor(h, Var(4)))


def test_dag_roundtrip_preserves_semantics_and_sharing():
    expr = _shared_dag()
    doc = json.loads(json.dumps(expr_to_json_dag(expr)))
    assert doc["version"] == EXPR_SCHEMA_VERSION_DAG
    rt = expr_from_json(doc)
    assert np.array_equal(eval_expr_tt(rt, 5), eval_expr_tt(expr, 5))
    # every definition is materialized exactly once
    assert _identity_nodes(rt) == len(doc["nodes"])


def test_structural_dedup_recovers_sharing_lost_by_construction():
    def make_h():
        return Xor(Xor(Var(0), Var(1)), Var(2))

    expr = And(Or(make_h(), Var(3)), Xor(make_h(), Var(4)))  # no identity sharing
    doc = expr_to_json_dag(expr)
    rt = expr_from_json(doc)
    assert _identity_nodes(rt) < _identity_nodes(expr)
    assert np.array_equal(eval_expr_tt(rt, 5), eval_expr_tt(expr, 5))


def test_serialization_is_deterministic():
    a = expr_to_json_dag(_shared_dag())
    b = expr_to_json_dag(_shared_dag())
    assert a == b


def test_v1_tree_documents_still_parse_identically():
    expr = _shared_dag()
    doc = json.loads(json.dumps(expr_to_json(expr)))
    assert "version" not in doc
    rt = expr_from_json(doc)
    assert np.array_equal(eval_expr_tt(rt, 5), eval_expr_tt(expr, 5))
    # the tree form cannot preserve sharing — documented behavior
    assert _identity_nodes(rt) > _identity_nodes(expr)


def test_deep_dag_serde_is_iterative():
    cur = Xor(Var(0), Var(1))
    for i in range(5000):
        cur = And(Or(cur, Var(2 + i % 4)), cur)
    doc = expr_to_json_dag(cur)
    rt = expr_from_json(doc)
    assert expr_to_json_dag(rt) == doc


@pytest.mark.parametrize(
    ("label", "doc"),
    [
        ("forward_ref", {"version": 2, "root": 0,
                         "nodes": [{"op": "not", "a": 1}, {"op": "var", "i": 0}]}),
        ("self_ref", {"version": 2, "root": 0, "nodes": [{"op": "not", "a": 0}]}),
        ("dangling_ref", {"version": 2, "root": 0,
                          "nodes": [{"op": "var", "i": 0}, {"op": "and", "a": 0, "b": 7}]}),
        ("bool_ref", {"version": 2, "root": 1,
                      "nodes": [{"op": "var", "i": 0}, {"op": "not", "a": False}]}),
        ("negative_ref", {"version": 2, "root": 1,
                          "nodes": [{"op": "var", "i": 0}, {"op": "not", "a": -1}]}),
        ("bad_root", {"version": 2, "root": 5, "nodes": [{"op": "var", "i": 0}]}),
        ("bool_root", {"version": 2, "root": True, "nodes": [{"op": "var", "i": 0}]}),
        ("bad_version", {"version": 3, "root": 0, "nodes": [{"op": "var", "i": 0}]}),
        ("empty_nodes", {"version": 2, "root": 0, "nodes": []}),
        ("nodes_not_list", {"version": 2, "root": 0, "nodes": {"op": "var", "i": 0}}),
        ("node_not_object", {"version": 2, "root": 0, "nodes": ["var"]}),
        ("bad_op", {"version": 2, "root": 0, "nodes": [{"op": "nand", "a": 0, "b": 0}]}),
        ("bad_var_index", {"version": 2, "root": 0, "nodes": [{"op": "var", "i": "x"}]}),
        ("duplicate_definition", {"version": 2, "root": 2,
                                  "nodes": [{"op": "var", "i": 0},
                                            {"op": "var", "i": 0},
                                            {"op": "and", "a": 0, "b": 1}]}),
    ],
)
def test_malformed_documents_are_rejected(label, doc):
    with pytest.raises(ValueError):
        expr_from_json(doc)


def test_non_mapping_input_rejected():
    with pytest.raises(ValueError):
        expr_from_json([1, 2, 3])  # type: ignore[arg-type]


def _deep_v1_doc(depth):
    doc = {"op": "var", "i": 0}
    for _ in range(depth):
        doc = {"op": "not", "a": doc}
    return doc


def test_deep_v1_documents_parse_iteratively():
    """2026-08-02 Phase A2: v1 deserialization must never RecursionError."""
    import sys

    limit = sys.getrecursionlimit()
    for depth in (limit // 2, limit, limit * 10):
        expr = expr_from_json(_deep_v1_doc(depth))
        count = 0
        while isinstance(expr, Not):
            expr = expr.a
            count += 1
        assert count == depth and isinstance(expr, Var)


def test_deep_v1_serialization_is_iterative():
    import sys

    expr = Var(0)
    for i in range(sys.getrecursionlimit() * 5):
        expr = Not(expr)
    doc = expr_to_json(expr)
    depth = 0
    while doc.get("op") == "not":
        doc = doc["a"]
        depth += 1
    assert depth == sys.getrecursionlimit() * 5


def test_malformed_deep_v1_fails_with_valueerror():
    import sys

    doc = _deep_v1_doc(sys.getrecursionlimit() * 5)
    cur = doc
    for _ in range(sys.getrecursionlimit() * 5 - 1):
        cur = cur["a"]
    cur["a"] = {"op": "bogus"}  # corrupt the deepest leaf
    with pytest.raises(ValueError):
        expr_from_json(doc)


def test_v1_roundtrip_output_unchanged_by_iterative_rewrite():
    expr = _shared_dag()
    doc = expr_to_json(expr)
    # exact structural form of the emitted document is preserved
    assert doc == {
        "op": "and",
        "a": {"op": "or",
              "a": {"op": "xor", "a": {"op": "xor", "a": {"op": "var", "i": 0},
                                        "b": {"op": "var", "i": 1}},
                    "b": {"op": "var", "i": 2}},
              "b": {"op": "var", "i": 3}},
        "b": {"op": "xor",
              "a": {"op": "xor", "a": {"op": "xor", "a": {"op": "var", "i": 0},
                                        "b": {"op": "var", "i": 1}},
                    "b": {"op": "var", "i": 2}},
              "b": {"op": "var", "i": 4}},
    }
