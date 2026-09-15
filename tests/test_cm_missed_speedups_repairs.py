"""Regression coverage for the 2026-09-15 missed-speedups repairs."""

from dataclasses import replace

import numpy as np
import pytest

import cm_bench as bench
import cm_ir as ir
from bitset_backend import bitset_to_bool_array
from cm_exprlib import And, Imp, Or, Var, eval_expr_tt
from cmbench.config import BenchmarkConfig
from cmbench.output_budget import OutputBudget, OutputBudgetExceeded
from cmbench.phase_timing import PhaseRecorder


def _common():
    return Imp(And(Var(0), Var(1)), Or(Var(2), Var(3)))


def _config(*, flat: bool, compile_once: bool, words: bool = False) -> BenchmarkConfig:
    return BenchmarkConfig(
        sizes=(4,), trials=1, seed=2, max_depth=3,
        no_numba=True, no_sympy=True, no_espresso=True, no_bdd_sop=True,
        no_dd=True, no_robdd=True, no_robdd_dd=True,
        cm_compare_no_reinflate=True, cm_flat_eval=flat, cm_words_eval=words,
        cm_compile_once_per_expression=compile_once, cm_eval_repeat=2,
    )


@pytest.mark.parametrize("flat", [False, True])
@pytest.mark.parametrize("compile_once", [False, True])
def test_single_expr_forwards_flat_choice_despite_opposite_default(
    flat, compile_once, monkeypatch
):
    expr = _common()
    reference = eval_expr_tt(expr, 4).astype(np.uint8).reshape(-1)
    calls = []
    original = ir.materialize_hybrid_no_reinflate

    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        actual = bitset_to_bool_array(int(result.bits), len(result.output_vars))
        assert np.array_equal(actual, reference)
        calls.append((dict(kwargs), result))
        return result

    monkeypatch.setattr(bench, "materialize_hybrid_no_reinflate", capture)
    with ir.evaluation_defaults_scope(flat_eval=not flat, words_eval=False):
        row = bench.time_backends_on_expr(
            4, expr, use_dd=False, use_espresso=False, verbose=False,
            sample_rng=np.random.default_rng(2), tt_ref=reference,
            config=_config(flat=flat, compile_once=compile_once),
        )
        assert ir.get_evaluation_defaults() == (not flat, False)

    assert len(calls) == 3
    assert all(kwargs["flat_eval"] is flat for kwargs, _ in calls)
    assert all(kwargs["words_eval"] is False for kwargs, _ in calls)
    assert calls[0][0]["diagnostics"]["cached_exec_engine_kind"] == (
        "cm_node_flat" if flat else "cm_node_recursive"
    )
    assert row["cm_hybrid_no_reinflate_ok"] is True


def test_words_precedence_is_preserved_when_benchmark_forwards_both_flags(monkeypatch):
    expr = _common()
    reference = eval_expr_tt(expr, 16).astype(np.uint8).reshape(-1)
    calls = []
    original = ir.materialize_hybrid_no_reinflate

    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append((dict(kwargs), result))
        return result

    monkeypatch.setattr(bench, "materialize_hybrid_no_reinflate", capture)
    config = _config(flat=False, compile_once=True, words=True)
    config = replace(config, sizes=(16,), cm_hybrid_threshold=16)
    row = bench.time_backends_on_expr(
        16, expr, use_dd=False, use_espresso=False, verbose=False,
        sample_rng=np.random.default_rng(2), tt_ref=reference, config=config,
    )

    assert calls
    assert all(call[0]["flat_eval"] is False for call in calls)
    assert all(call[0]["words_eval"] is True for call in calls)
    assert calls[0][0]["diagnostics"]["cached_exec_engine_kind"] == "cm_node_words"
    assert calls[0][1].final_output_representation_code == 2
    assert calls[0][1].output_vars == tuple(f"x{i}" for i in range(16))
    assert calls[0][1].bits is not None
    assert row["cm_hybrid_no_reinflate_ok"] is True


def test_remote_failure_local_fallback_forwards_configured_evaluator(monkeypatch):
    expr = _common()
    reference = eval_expr_tt(expr, 4).astype(np.uint8).reshape(-1)
    calls = []
    original = ir.materialize_hybrid_no_reinflate

    def offline(*_args, **_kwargs):
        raise RuntimeError("offline sentinel")

    def capture(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(dict(kwargs))
        return result

    monkeypatch.setattr(bench, "execute_remote_cm", offline)
    monkeypatch.setattr(bench, "materialize_hybrid_no_reinflate", capture)
    config = replace(
        _config(flat=True, compile_once=False),
        cm_exec_target="runpod",
        cm_runpod_fallback_local=True,
    )
    row = bench.time_backends_on_expr(
        4, expr, use_dd=False, use_espresso=False, verbose=False,
        sample_rng=np.random.default_rng(2), tt_ref=reference, config=config,
    )

    assert len(calls) == 1
    assert calls[0]["flat_eval"] is True
    assert calls[0]["words_eval"] is False
    assert row["cm_runpod_fallback_local"] is True
    assert row["cm_hybrid_no_reinflate_ok"] is True


def test_ir_cache_profile_is_a_current_call_snapshot_and_counters_accumulate():
    ir.clear_cm_ir_persistent_cache()
    try:
        diag = {"sentinel": "preserve"}
        first = PhaseRecorder()
        with first.activate():
            ir.compile_expr_to_cm_ir_persistent(_common(), diag)
        cold_profile = dict(diag["ir_cache_profile_v1"])
        cold_hits = diag["ir_persistent_cache_hits"]

        ir.compile_expr_to_cm_ir_persistent(_common(), diag)
        assert "ir_cache_profile_v1" not in diag
        assert diag["ir_persistent_cache_hits"] > cold_hits
        assert diag["sentinel"] == "preserve"

        second = PhaseRecorder()
        with second.activate():
            ir.compile_expr_to_cm_ir_persistent(_common(), diag)
        warm_profile = diag["ir_cache_profile_v1"]
        assert cold_profile["root_hits"] == 0
        assert warm_profile["root_hits"] == 1
        assert warm_profile != cold_profile

        ir.compile_expr_to_cm_ir(_common(), diag, persistent_cache=False)
        assert "ir_cache_profile_v1" not in diag
        assert diag["sentinel"] == "preserve"
    finally:
        ir.clear_cm_ir_persistent_cache()


def test_ir_cache_profile_is_cleared_before_a_failed_compile(monkeypatch):
    ir.clear_cm_ir_persistent_cache()
    try:
        diag = {"sentinel": 7}
        with PhaseRecorder().activate():
            ir.compile_expr_to_cm_ir_persistent(_common(), diag)
        assert "ir_cache_profile_v1" in diag

        def fail(_expr):
            raise RuntimeError("compile failure sentinel")

        monkeypatch.setattr(ir.CMIRBuilder, "_shared_assoc_uids", staticmethod(fail))
        with pytest.raises(RuntimeError, match="compile failure sentinel"):
            with PhaseRecorder().activate():
                ir.compile_expr_to_cm_ir_persistent(Or(Var(4), Var(5)), diag)
        assert "ir_cache_profile_v1" not in diag
        assert diag["sentinel"] == 7
    finally:
        ir.clear_cm_ir_persistent_cache()


def test_cached_engine_snapshot_tracks_packed_fallback_reverse_and_refusal():
    node = ir.compile_expr_to_cm_ir(_common())
    names = tuple(f"x{i}" for i in range(4))
    diag = {"sentinel": "preserve"}

    packed = ir.materialize_hybrid_no_reinflate(
        node, names, flat_eval=True, words_eval=False,
        hybrid_threshold=4, diagnostics=diag,
    )
    assert diag["cached_exec_engine_kind"] == "cm_node_flat"
    fallback = ir.materialize_hybrid_no_reinflate(
        node, names, flat_eval=True, words_eval=False,
        hybrid_threshold=0, diagnostics=diag,
    )
    assert fallback.bits is None and fallback.tt is not None
    assert np.array_equal(fallback.tt, bitset_to_bool_array(packed.bits, 4))
    assert "cached_exec_engine_kind" not in diag
    assert "cached_exec_engine_live_k" not in diag

    ir.materialize_hybrid_no_reinflate(
        node, names, flat_eval=False, words_eval=False,
        hybrid_threshold=4, diagnostics=diag,
    )
    assert diag["cached_exec_engine_kind"] == "cm_node_recursive"
    assert diag["cached_exec_engine_live_k"] == 4

    with pytest.raises(OutputBudgetExceeded):
        ir.materialize_hybrid_no_reinflate(
            node, names, flat_eval=True, words_eval=False,
            hybrid_threshold=4, diagnostics=diag,
            output_budget=OutputBudget(max_output_bytes=0),
        )
    assert "cached_exec_engine_kind" not in diag
    assert "cached_exec_engine_live_k" not in diag
    assert diag["sentinel"] == "preserve"


def test_k20_refusal_and_reduced_output_preserve_budget_and_engine_semantics():
    node = ir.compile_expr_to_cm_ir(Or(Var(0), Var(19)))
    names = tuple(f"x{i}" for i in range(20))
    diag = {}
    bounded = OutputBudget(max_output_vars=16, allow_reduced_output=False)

    with pytest.raises(OutputBudgetExceeded):
        ir.materialize_hybrid_no_reinflate(
            node, names, flat_eval=True, words_eval=False,
            hybrid_threshold=7, diagnostics=diag, output_budget=bounded,
        )
    assert "cached_exec_engine_kind" not in diag

    reduced = ir.materialize_hybrid_no_reinflate(
        node, names, flat_eval=True, words_eval=False,
        hybrid_threshold=7, diagnostics=diag, allow_reduced_output=True,
        max_full_output_vars=16, output_budget=bounded,
    )
    assert reduced.output_vars == ("x0", "x19")
    assert reduced.status.value == "reduced"
    assert diag["cached_exec_engine_kind"] == "cm_node_flat"
    assert diag["cached_exec_engine_live_k"] == 2


def test_cached_engine_snapshot_is_cleared_before_engine_selection_error(monkeypatch):
    import cmbench.backends.bitset_engine as engines

    node = ir.compile_expr_to_cm_ir(_common())
    names = tuple(f"x{i}" for i in range(4))
    diag = {}
    ir.materialize_hybrid_no_reinflate(
        node, names, flat_eval=True, hybrid_threshold=4, diagnostics=diag,
    )

    def fail(**_kwargs):
        raise RuntimeError("engine selection failure sentinel")

    monkeypatch.setattr(engines, "select_cm_node_engine", fail)
    with pytest.raises(RuntimeError, match="engine selection failure sentinel"):
        ir.materialize_hybrid_no_reinflate(
            node, names, flat_eval=True, hybrid_threshold=4, diagnostics=diag,
        )
    assert "cached_exec_engine_kind" not in diag
    assert "cached_exec_engine_live_k" not in diag


def test_packed_snapshot_uses_current_permuted_and_all_fixed_output_basis():
    node = ir.compile_expr_to_cm_ir(_common())
    diag = {}
    permuted = ("x3", "x2", "x1", "x0")
    result = ir.materialize_hybrid_no_reinflate(
        node, permuted, flat_eval=True, hybrid_threshold=4, diagnostics=diag,
    )
    assert result.output_vars == permuted
    assert diag["cached_exec_engine_live_k"] == 4

    reduced = ir.materialize_hybrid_no_reinflate(
        node,
        tuple(f"x{i}" for i in range(4)),
        fixed={"x0": 1, "x1": 1, "x2": 0, "x3": 0},
        flat_eval=False,
        hybrid_threshold=4,
        diagnostics=diag,
        allow_reduced_output=True,
        output_budget=OutputBudget(max_output_vars=0, allow_reduced_output=True),
    )
    assert reduced.output_vars == ()
    assert reduced.bits == 0
    assert reduced.final_output_representation_code == 3
    assert diag["cached_exec_engine_kind"] == "cm_node_recursive"
    assert diag["cached_exec_engine_live_k"] == 0
