import unittest

import numpy as np

from cm_build import compile_expr_to_cm
from cm_exprlib import eval_expr_tt, random_expr
from cm_normalize import canonical_layout
from cm_parallel import compile_expr_to_cm_parallel

try:
    from cm_build_lazy import compile_expr_to_cm_lazy

    HAS_LAZY = True
except Exception:
    HAS_LAZY = False


class CMParallelTests(unittest.TestCase):
    def _check_backend(self, *, use_lazy: bool) -> None:
        rng = np.random.default_rng(222)
        n = 8
        R, C = canonical_layout([f"x{i}" for i in range(n)])

        for _ in range(3):
            expr = random_expr(n, rng, max_depth=5, p_unary=0.25)
            if use_lazy:
                seq = compile_expr_to_cm_lazy(expr, R, C, fixed={})
            else:
                seq = compile_expr_to_cm(expr, R, C, fixed={})

            par = compile_expr_to_cm_parallel(
                expr,
                R,
                C,
                fixed={},
                use_lazy=use_lazy,
                workers=2,
                min_n=1,
                min_nodes=1,
                chunk_rows=32,
            )
            self.assertTrue(np.array_equal(seq.reshape(-1).view(np.uint8), par.reshape(-1).view(np.uint8)))

            tt_ref = eval_expr_tt(expr, n).astype(np.uint8).reshape(-1)
            self.assertTrue(np.array_equal(tt_ref, par.reshape(-1).view(np.uint8)))

    def test_parallel_matches_eager_and_truth_table(self) -> None:
        self._check_backend(use_lazy=False)

    @unittest.skipUnless(HAS_LAZY, "cm_build_lazy is not available")
    def test_parallel_matches_lazy_and_truth_table(self) -> None:
        self._check_backend(use_lazy=True)

    def test_parallel_is_deterministic(self) -> None:
        rng = np.random.default_rng(999)
        n = 8
        expr = random_expr(n, rng, max_depth=6, p_unary=0.25)
        R, C = canonical_layout([f"x{i}" for i in range(n)])

        results = []
        for _ in range(3):
            par = compile_expr_to_cm_parallel(
                expr,
                R,
                C,
                fixed={},
                use_lazy=False,
                workers=2,
                min_n=1,
                min_nodes=1,
                chunk_rows=32,
            )
            results.append(par.reshape(-1).view(np.uint8))

        self.assertTrue(np.array_equal(results[0], results[1]))
        self.assertTrue(np.array_equal(results[1], results[2]))


if __name__ == "__main__":
    unittest.main()
