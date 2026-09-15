from __future__ import annotations

import numpy as np

import cm_bench
from cm_exprlib import And, Var
from cmbench.config import BenchmarkConfig


def _large_n_row(*, sampled_correctness: int):
    config = BenchmarkConfig(
        sizes=(20,),
        trials=1,
        seed=7,
        max_depth=2,
        full_tt_max_n=16,
        cm_compare_no_reinflate=True,
        cm_hybrid_threshold=16,
        cm_max_full_output_vars=16,
        large_n_safe=True,
        sampled_correctness=sampled_correctness,
        no_bitset=True,
        no_numba=True,
        no_sympy=True,
        no_espresso=True,
        no_bdd_sop=True,
        no_dd=True,
        no_robdd=True,
        no_robdd_dd=True,
    )
    return cm_bench.time_backends_on_expr(
        20,
        And(Var(0), Var(1)),
        use_dd=False,
        use_espresso=False,
        verbose=False,
        sample_rng=np.random.default_rng(11),
        config=config,
    )


def test_large_n_unvalidated_result_is_not_reported_as_correct() -> None:
    row = _large_n_row(sampled_correctness=0)

    assert row["tt_ref_available"] is False
    assert row["sampled_correctness_samples"] == 0
    assert row["cm_hybrid_no_reinflate_ok"] is None


def test_large_n_sampled_validation_controls_correctness_status() -> None:
    row = _large_n_row(sampled_correctness=25)

    assert row["sampled_correctness_samples"] == 25
    assert row["sampled_correctness_mismatches"] == 0
    assert row["cm_hybrid_no_reinflate_ok"] is True


def test_large_n_sampled_mismatch_cannot_report_correct(monkeypatch) -> None:
    monkeypatch.setattr(
        cm_bench,
        "sampled_correctness_check",
        lambda *_args, **_kwargs: {
            "sampled_correctness_samples": 25,
            "sampled_correctness_mismatches": 1,
            "sampled_correctness_mismatch_rate": 0.04,
        },
    )

    row = _large_n_row(sampled_correctness=25)

    assert row["sampled_correctness_mismatches"] == 1
    assert row["cm_hybrid_no_reinflate_ok"] is False
