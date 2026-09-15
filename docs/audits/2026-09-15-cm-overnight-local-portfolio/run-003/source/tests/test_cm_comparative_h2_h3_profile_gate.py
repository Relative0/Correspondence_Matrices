from __future__ import annotations

import hashlib

import numpy as np

from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Eqv, Not, Or, Var, Xor, all_assignments_tt
from cm_ir import compile_expr_to_cm_ir, materialize_cm
from cm_normalize import canonical_layout
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.h2_h3_profile_gate import (
    COMPONENTS,
    PARENT_FREEZE_CANONICAL_SHA256,
    _profile_category,
    build_freeze,
)
from cmbench.comparative.ir import cm_dag_signature


def _dnf(mask: int, k: int):
    variables = [Var(index) for index in range(k)]
    terms = []
    for assignment in range(1 << k):
        if not ((mask >> assignment) & 1):
            continue
        literals = []
        for index, variable in enumerate(variables):
            value = (assignment >> (k - 1 - index)) & 1
            literals.append(variable if value else Not(variable))
        term = literals[0]
        for literal in literals[1:]:
            term = And(term, literal)
        terms.append(term)
    if not terms:
        return Xor(variables[0], variables[0])
    expression = terms[0]
    for term in terms[1:]:
        expression = Or(expression, term)
    return expression


def _vector(expression, k: int) -> np.ndarray:
    node = compile_expr_to_cm_ir(expression, reuse_cache=False, persistent_cache=False)
    rows, columns = canonical_layout([f"x{index}" for index in range(k)])
    return materialize_cm(node, rows, columns).reshape(-1).astype(np.uint8)


def test_freeze_is_deterministic_source_bound_and_uses_only_admitted_cases():
    first = build_freeze(".")
    second = build_freeze(".")
    assert canonical_bytes(first) == canonical_bytes(second)
    assert first["source_checkpoint"] == "c9af2a3c80388e467944bd706036996db9eed9b8"
    assert first["parent_freeze"]["canonical_sha256"] == PARENT_FREEZE_CANONICAL_SHA256
    assert len(first["workload"]["complete_relation"]["case_ids"]) == 15
    assert len(first["workload"]["repeated_restriction"]["case_ids"]) == 30
    assert len(first["workload"]["related_multi_root"]["case_ids"]) == 12
    assert len(first["workload"]["smaller_query"]["case_ids"]) == 3
    assert first["continuation"]["h9_work_authorized"] is False
    assert first["continuation"]["cloud_execution_authorized"] is False


def test_profile_function_rules_are_mutually_exclusive_and_cover_frozen_components():
    samples = [
        ("cm_ir.py", "make_and"),
        ("cm_ir.py", "__hash__"),
        ("cm_ir.py", "_intern"),
        ("contracts.py", "canonical_bytes"),
        ("cm_ir.py", "align_to_vars"),
        ("numpy.py", "array"),
        ("bitset_backend.py", "bitset_to_bool_array"),
        ("~", "<method 'copy' of 'numpy.ndarray' objects>"),
    ]
    observed = [_profile_category(filename, name) for filename, name in samples]
    assert tuple(observed) == COMPONENTS


def test_exhaustive_boolean_functions_through_three_variables_match_independent_vectors():
    for k in (1, 2, 3):
        assignments = all_assignments_tt(k)
        for mask in range(1 << (1 << k)):
            expression = _dnf(mask, k)
            actual = _vector(expression, k)
            expected = np.array([(mask >> row) & 1 for row in range(len(assignments))], dtype=np.uint8)
            assert np.array_equal(actual, expected), (k, mask)


def test_sharing_and_commutative_metamorphics_preserve_canonical_structure_and_output():
    a, b, c = Var(0), Var(1), Var(2)
    shared = Xor(a, And(b, c))
    shared_expression = Eqv(And(shared, Not(a)), Or(shared, b))
    left_clone = Xor(Var(0), And(Var(1), Var(2)))
    right_clone = Xor(Var(0), And(Var(1), Var(2)))
    expanded_expression = Eqv(And(left_clone, Not(Var(0))), Or(right_clone, Var(1)))
    assert expr_to_json_dag(shared_expression) == expr_to_json_dag(expanded_expression)
    assert np.array_equal(_vector(shared_expression, 3), _vector(expanded_expression, 3))
    first = compile_expr_to_cm_ir(And(shared, Or(a, b)), reuse_cache=False)
    second = compile_expr_to_cm_ir(And(Or(b, a), shared), reuse_cache=False)
    first_sha = hashlib.sha256(canonical_bytes(cm_dag_signature(first))).hexdigest()
    second_sha = hashlib.sha256(canonical_bytes(cm_dag_signature(second))).hexdigest()
    assert first_sha == second_sha
