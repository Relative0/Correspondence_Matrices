"""Compiler admission and exact cache-key compatibility regressions."""
import hashlib
from unittest.mock import patch

import numpy as np
import pytest

import cm_ir
from cm_exprlib import And, Or, Xor, Not, Imp, Eqv, Var, random_expr, eval_expr_tt


def chain(depth):
    e = Var(0)
    for _ in range(depth):
        e = Not(e)
    return e


def doubled(depth):
    e = Var(0)
    for _ in range(depth):
        e = Or(e, e)
    return e


@pytest.mark.parametrize("entry", [
    cm_ir.compile_expr_to_cm_ir, cm_ir.compile_expr_to_cm_ir_cached,
    cm_ir.compile_expr_to_cm_ir_persistent, cm_ir.compile_expr_cached,
    cm_ir.CMIRBuilder().build])
def test_deep_input_refused_before_build(entry):
    with patch.object(cm_ir.CMIRBuilder, "_build_rec", side_effect=AssertionError("build called")):
        with pytest.raises(ValueError, match="compil.*depth"):
            entry(chain(1200))


@pytest.mark.parametrize("flags", [dict(), dict(reuse_cache=True), dict(persistent_cache=True),
    dict(share_aware_flatten=False, build_memo=False)])
def test_excess_expanded_compile_work_refused(flags):
    with patch.object(cm_ir.CMIRBuilder, "_build_rec", side_effect=AssertionError("build called")):
        with pytest.raises(ValueError, match="compil.*work"):
            cm_ir.compile_expr_to_cm_ir(doubled(40), **flags)


def test_cache_key_does_not_hash_recursive_expr():
    cm_ir.clear_cm_ir_compile_cache()
    e = doubled(12)
    with patch.object(Or, "__hash__", side_effect=AssertionError("AST hashing called")):
        node = cm_ir.compile_expr_to_cm_ir(e, reuse_cache=True)
        diag = {}
        assert cm_ir.compile_expr_to_cm_ir(doubled(12), reuse_cache=True, diagnostics=diag) is node
        assert diag["ir_compile_cache_hit"] == 1


def legacy_persistent_digest(e):
    h = hashlib.blake2b(digest_size=16)
    if isinstance(e, Var):
        h.update(b"VAR:" + f"x{e.i}".encode())
    elif isinstance(e, Not):
        h.update(b"NOT:" + legacy_persistent_digest(e.a))
    else:
        parts = [legacy_persistent_digest(e.a), legacy_persistent_digest(e.b)]
        if not isinstance(e, Imp):
            parts.sort()
        h.update({And: b"AND2:", Or: b"OR2:", Xor: b"XOR2:", Eqv: b"EQV2:", Imp: b"IMP:"}[type(e)])
        h.update(b"".join(parts))
    return h.digest()


def test_iterative_persistent_digest_legacy_bytes_and_deep_chain():
    rng = np.random.default_rng(584)
    for _ in range(100):
        e = random_expr(4, rng, max_depth=5)
        assert cm_ir._persistent_digest(e, {}) == legacy_persistent_digest(e)
    expected = legacy_persistent_digest(Var(0))
    for _ in range(1200):
        expected = hashlib.blake2b(b"NOT:" + expected, digest_size=16).digest()
    assert cm_ir._persistent_digest(chain(1200), {}) == expected


def test_ordered_cache_key_matches_dataclass_equality():
    rng = np.random.default_rng(794)
    exprs = [random_expr(3, rng, max_depth=3) for _ in range(50)]
    shared = And(Var(0), Var(1))
    exprs += [Or(shared, shared), Or(And(Var(0), Var(1)), And(Var(0), Var(1))),
        And(Var(0), Var(1)), And(Var(1), Var(0)),
        And(And(Var(0), Var(1)), Var(2)), And(Var(0), And(Var(1), Var(2)))]
    keys = [cm_ir._ordered_expr_cache_key(e, cm_ir._check_compile_graph(e)) for e in exprs]
    for i, a in enumerate(exprs):
        for j, b in enumerate(exprs):
            assert (keys[i] == keys[j]) == (a == b)


def test_compile_modes_match_source():
    rng = np.random.default_rng(933)
    for _ in range(40):
        e = random_expr(4, rng, max_depth=5)
        expected = eval_expr_tt(e, 4).astype(bool).reshape(4, 4)
        keys = []
        for flags in (dict(), dict(reuse_cache=True), dict(persistent_cache=True)):
            node = cm_ir.compile_expr_to_cm_ir(e, **flags)
            keys.append(node.key)
            np.testing.assert_array_equal(cm_ir.materialize_cm(node, ["x0", "x1"], ["x2", "x3"]), expected)
        assert keys[0] == keys[1] == keys[2]


@pytest.mark.parametrize("entry", [cm_ir.compile_expr_to_cm_ir_cached,
    cm_ir.compile_expr_to_cm_ir_persistent, cm_ir.CMIRBuilder().build])
def test_typed_cycle_refusal_and_node_limit(entry):
    e = Not(Var(0))
    object.__setattr__(e, "a", e)
    with pytest.raises(cm_ir.CompilationAdmissionError, match="acyclic") as failure:
        entry(e)
    assert failure.value.status == cm_ir.OutputStatus.REFUSED
    with patch.object(cm_ir, "_COMPILE_MAX_NODES", 2):
        with pytest.raises(cm_ir.CompilationAdmissionError, match="node limit"):
            entry(And(Var(0), Var(1)))


def test_admission_boundaries_and_diagnostics():
    diag = {}
    cm_ir.compile_expr_to_cm_ir(chain(255), diagnostics=diag)
    assert diag["ir_compile_admission_depth"] == 256
    assert diag["ir_compile_admission_nodes"] == 256
    with pytest.raises(cm_ir.CompilationAdmissionError, match="depth"):
        cm_ir.compile_expr_to_cm_ir(chain(256))
    cm_ir.compile_expr_to_cm_ir(doubled(18), reuse_cache=True, diagnostics=diag)
    assert diag["ir_compile_admission_structural_work"] == 1048555
    with pytest.raises(cm_ir.CompilationAdmissionError, match="work"):
        cm_ir.compile_expr_to_cm_ir(doubled(19), reuse_cache=True)


def test_reused_admission_diagnostics_do_not_report_stale_success():
    diag = {}
    cm_ir.compile_expr_to_cm_ir(Var(0), diagnostics=diag)
    assert diag["ir_compile_admission_status"] == "ok"
    with pytest.raises(cm_ir.CompilationAdmissionError):
        cm_ir.compile_expr_to_cm_ir(chain(1200), diagnostics=diag)
    assert diag["ir_compile_admission_status"] == "refused"
    assert "ir_compile_admission_nodes" not in diag
    assert "ir_compile_admission_depth" not in diag
    assert "ir_compile_admission_structural_work" not in diag
