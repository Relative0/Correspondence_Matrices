import cm_bench
from cmbench.availability import detect_backends
from cmbench.config import BenchmarkConfig
from cmbench.context import make_context


def test_run_equivalence_bench_accepts_explicit_config_without_global_args(monkeypatch):
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

    raw, summary = cm_bench.run_equivalence_bench(
        [2],
        1,
        7,
        2,
        False,
        config=config,
        ctx=ctx,
    )

    assert len(raw) == 1
    assert len(summary) == 1
    assert raw.iloc[0]["bitset_equiv_status"] == "ok"
    assert raw.iloc[0]["cm_equiv_status"] == "skipped"
    assert raw.iloc[0]["sympy_equiv_status"] == "skipped"

