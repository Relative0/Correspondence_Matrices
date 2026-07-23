import numpy as np

import cm_bench
from cm_exprlib import And, Var, eval_expr_tt
from cmbench.config import BenchmarkConfig


def _small_row(**overrides):
    expr = And(Var(0), Var(1))
    cfg_kwargs = dict(
        sizes=(2,),
        trials=1,
        seed=0,
        max_depth=2,
        no_numba=True,
        no_sympy=True,
        no_espresso=True,
        no_bdd_sop=True,
        no_dd=True,
        no_robdd_dd=True,
    )
    cfg_kwargs.update(overrides)
    cfg = BenchmarkConfig(**cfg_kwargs)
    row = cm_bench.time_backends_on_expr(
        2,
        expr,
        use_dd=False,
        use_espresso=False,
        verbose=False,
        sample_rng=np.random.default_rng(0),
        tt_ref=eval_expr_tt(expr, 2).astype(np.uint8).reshape(-1),
        config=cfg,
    )
    return row


def test_single_expr_row_preserves_representative_schema_keys() -> None:
    row = _small_row()
    expected = {
        "n_vars",
        "trial",
        "expr_style",
        "cm_time_s",
        "cm_ok",
        "cm_tt_extract_time_s",
        "bitset_time_s",
        "bitset_ok",
        "bitset_baseline_kind",
        "cm_words_eval",
        "numba_time_s",
        "numba_ok",
        "sympy_time_s",
        "sympy_ok",
        "bdd_sop_time_s",
        "bdd_sop_ok",
        "robdd_build_time_s",
        "robdd_status",
        "correctness_reference",
        "tt_ref_available",
        "tt_ref_source",
    }
    row["n_vars"] = 2
    row["trial"] = 0
    row["expr_style"] = "ordinary"
    assert expected <= set(row)


def test_no_reinflate_row_preserves_representative_schema_keys() -> None:
    row = _small_row(
        cm_compare_no_reinflate=True,
        cm_eval_repeat=2,
        cm_compile_once_per_expression=True,
    )
    expected = {
        "cm_hybrid_no_reinflate_time_s",
        "cm_hybrid_no_reinflate_exec_only_time_s",
        "cm_hybrid_no_reinflate_tt_extract_time_s",
        "cm_hybrid_no_reinflate_ok",
        "cm_hybrid_no_reinflate_declined",
        "cm_hybrid_no_reinflate_cached_exec_only_time_s",
        "cm_hybrid_no_reinflate_final_output_representation_code",
        "cm_hybrid_no_reinflate_final_cm_materialization_performed",
        "sampled_correctness_samples",
        "sampled_correctness_mismatches",
        "sampled_correctness_mismatch_rate",
    }
    assert expected <= set(row)

    words_row = _small_row(
        cm_compare_no_reinflate=True,
        cm_words_eval=True,
        cm_hybrid_threshold=16,
    )
    assert words_row["cm_words_eval"] is True
    assert words_row["bitset_baseline_kind"] == "raw_ast_words"
    assert words_row["cm_hybrid_no_reinflate_ok"] is True
    assert words_row["bitset_ok"] is True


def test_single_expr_selected_values_stable_for_small_expression() -> None:
    row = _small_row(cm_compare_no_reinflate=True)
    assert row["cm_ok"] is True
    assert row["bitset_ok"] is True
    assert row["cm_hybrid_no_reinflate_ok"] is True
    assert row["correctness_reference"] == "eval_expr_tt"
    assert row["tt_ref_available"] is True
    assert row["tt_ref_source"] == "generate_benchmark_expr"
