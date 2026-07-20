import cm_bench
from cmbench.availability import detect_backends
from cmbench.config import BenchmarkConfig
from cmbench.context import make_context


def test_equivalence_raw_has_phase3_provenance(monkeypatch):
    config = BenchmarkConfig(
        sizes=(2,),
        trials=1,
        seed=7,
        max_depth=2,
        equiv_backends="bitset",
        no_dd=True,
        no_sympy=True,
    )
    ctx = make_context(config, detect_backends())
    monkeypatch.setattr(cm_bench, "args", None)

    raw, _ = cm_bench.run_equivalence_bench([2], 1, 7, 2, False, config=config, ctx=ctx)

    row = raw.iloc[0]
    assert row["equiv_correctness_reference"] == "eval_expr_tt"
    assert bool(row["equiv_tt_f_available"]) is True
    assert bool(row["equiv_tt_g_available"]) is True
    assert row["equiv_tt_source"] == "eval_expr_tt"


def test_partial_and_family_raw_have_phase3_provenance(monkeypatch):
    base = dict(sizes=(3,), trials=1, seed=7, max_depth=2, no_dd=True, no_robdd_dd=True, no_bitset=True)
    monkeypatch.setattr(cm_bench, "args", None)

    partial_config = BenchmarkConfig(**base, partial_contexts=2)
    partial_ctx = make_context(partial_config, detect_backends())
    partial_raw, _ = cm_bench.run_partial_context_bench([3], 1, 7, 2, False, config=partial_config, ctx=partial_ctx)
    partial_row = partial_raw.iloc[0]
    assert partial_row["partial_reference_arrays_available_count"] == 2
    assert partial_row["partial_reference_source"] == "eval_expr_tt"
    assert partial_row["partial_correctness_reference"] == "eval_expr_tt"

    family_config = BenchmarkConfig(**base, family_size=3)
    family_ctx = make_context(family_config, detect_backends())
    family_raw, _ = cm_bench.run_expression_family_bench([3], 1, 7, 2, False, config=family_config, ctx=family_ctx)
    family_row = family_raw.iloc[0]
    assert family_row["family_tt_refs_available_count"] == 3
    assert family_row["family_tt_ref_source"] == "eval_expr_tt"
    assert family_row["family_correctness_reference"] == "eval_expr_tt"
