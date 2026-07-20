from types import SimpleNamespace

import numpy as np

import cm_bench
from cm_exprlib import And, Var, eval_expr_tt
from cmbench.availability import detect_backends
from cmbench.config import BenchmarkConfig
from cmbench.context import make_context


def _legacy_args_for_time_backends() -> SimpleNamespace:
    return SimpleNamespace(
        cm_debug_stats=False,
        cm_report_ir_breakdown=False,
        cm_compile_once_per_expression=False,
        cm_exec_target="local",
        cm_compare_no_reinflate=False,
        cm_layout="balanced",
        cm_pair=False,
        cm_lazy=False,
        cm_reuse_compiled_ir=False,
        cm_use_persistent_cache=False,
        cm_hybrid_threshold=7,
        cm_compare_hybrid=False,
        cm_parallel=False,
        no_robdd=True,
        no_dd=True,
        no_robdd_dd=True,
        no_bitset=True,
        no_numba=True,
        no_sympy=True,
        no_espresso=True,
        no_bdd_sop=True,
        sampled_correctness=0,
        cm_profile_cached_exec=False,
        cm_eval_repeat=1,
        full_tt_max_n=16,
        large_n_safe=False,
        robdd_dd_backend="auto",
        robdd_order_policy="fixed",
        robdd_order_sweeps=1,
        robdd_dynamic_reordering=False,
        robdd_reorder_method="sift",
        robdd_measure_tt_extract=False,
        robdd_tt_extract_method="all-assignments",
        robdd_tt_extract_max_n=16,
    )


def test_generate_benchmark_expr_can_return_tt_ref():
    config = BenchmarkConfig(sizes=(2,), trials=1, seed=1, max_depth=2)
    expr, diag, tt_ref = cm_bench.generate_benchmark_expr(
        2,
        np.random.default_rng(1),
        max_depth=2,
        style="ordinary",
        build_tt=True,
        config=config,
        return_tt_ref=True,
    )

    assert tt_ref is not None
    assert tt_ref.shape == (4,)
    assert "tt_density" in diag
    assert np.array_equal(tt_ref, eval_expr_tt(expr, 2).reshape(-1))


def test_time_backends_reuses_supplied_tt_ref(monkeypatch):
    expr = And(Var(0), Var(1))
    tt_ref = eval_expr_tt(expr, 2).astype(np.uint8).reshape(-1)
    config = BenchmarkConfig(
        sizes=(2,),
        trials=1,
        seed=1,
        max_depth=2,
        no_bitset=True,
        no_numba=True,
        no_sympy=True,
        no_espresso=True,
        no_bdd_sop=True,
        no_dd=True,
        no_robdd=True,
        no_robdd_dd=True,
    )
    monkeypatch.setattr(cm_bench, "args", _legacy_args_for_time_backends())
    monkeypatch.setattr(
        cm_bench,
        "eval_expr_tt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("tt_ref was recomputed")),
    )

    row = cm_bench.time_backends_on_expr(
        2,
        expr,
        use_dd=False,
        use_espresso=False,
        verbose=False,
        tt_ref=tt_ref,
        config=config,
        ctx=make_context(config, detect_backends()),
    )

    assert row["cm_ok"] is True
    assert row["tt_ref_available"] is True
    assert row["tt_ref_source"] == "generate_benchmark_expr"
    assert row["correctness_reference"] == "eval_expr_tt"

