import numpy as np

from cm_exprlib import Var
from cmbench.availability import detect_backends
from cmbench.config import BenchmarkConfig
from cmbench.context import make_context


def test_context_cache_helpers_are_stable():
    config = BenchmarkConfig(sizes=(2,), trials=1, seed=1, max_depth=2)
    ctx = make_context(config, detect_backends())

    assert ctx.var_names(2) is ctx.var_names(2)
    assert ctx.var_name_map(2) is ctx.var_name_map(2)
    assert ctx.bitset_env(2) is ctx.bitset_env(2)
    assert ctx.eval_grid(2) is ctx.eval_grid(2)
    assert ctx.canonical_layout(2, "balanced") is ctx.canonical_layout(2, "balanced")

    tt = ctx.get_or_compute_tt(Var(0), 2)
    assert ctx.get_or_compute_tt(Var(0), 2) is tt
    assert np.array_equal(tt, np.array([0, 0, 1, 1], dtype=np.uint8))
