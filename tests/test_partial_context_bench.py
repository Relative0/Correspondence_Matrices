import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import cm_bench
from cm_exprlib import And, Or, Var


def _partial_args(**overrides):
    base = {
        "partial_output_mode": "remaining-vars",
        "partial_context_style": "random_fixed",
        "partial_contexts": 6,
        "partial_fixed_var_count": None,
        "partial_fixed_var_fraction": 0.5,
        "partial_reuse_compiled_ir": True,
        "partial_robdd_measure_extract": False,
        "cm_hybrid_threshold": 7,
        "cm_max_full_output_vars": 16,
        "cm_use_persistent_cache": True,
        "sampled_correctness": 0,
        "full_tt_max_n": 16,
        "no_bitset": False,
        "no_dd": True,
        "no_robdd_dd": True,
        "robdd_dd_backend": "autoref",
        "robdd_order_policy": "fixed",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class PartialContextBenchTests(unittest.TestCase):
    def setUp(self) -> None:
        cm_bench.args = _partial_args()

    def test_context_generation_count_and_fixed_count(self) -> None:
        contexts = cm_bench.generate_partial_contexts(
            8,
            np.random.default_rng(1),
            context_count=10,
            fixed_var_count=3,
            style="sliding_window",
        )
        self.assertEqual(len(contexts), 10)
        self.assertTrue(all(len(c) == 3 for c in contexts))

    def test_remaining_vars_reference_and_bitset_fixed_match(self) -> None:
        expr = Or(And(Var(0), Var(1)), Var(2))
        context = {"x1": 1}
        out_vars = cm_bench._partial_output_vars(3, context, "remaining-vars")
        ref = cm_bench._partial_reference_array(expr, 3, context, out_vars)
        bits = cm_bench._eval_expr_bitset_fixed(expr, cm_bench.build_bitset_env(out_vars), context)
        self.assertTrue(np.array_equal(cm_bench.bitset_to_bool_array(bits, len(out_vars)), ref))
        self.assertEqual(out_vars, ["x0", "x2"])

    def test_cm_cached_and_no_cache_match_reference(self) -> None:
        expr = Or(And(Var(0), Var(1)), Var(2))
        contexts = [{"x1": 1}, {"x0": 0}]
        row = cm_bench.time_partial_context_workload(
            3,
            expr,
            contexts,
            trial=0,
            expr_style="test",
            bit_env=cm_bench.build_bitset_env(["x0", "x1", "x2"]),
            sample_rng=np.random.default_rng(2),
            robdd_order_seed=3,
        )
        self.assertEqual(row["partial_bitset_restricted_ok_rate"], 1.0)
        self.assertEqual(row["partial_cm_no_cache_ok_rate"], 1.0)
        self.assertEqual(row["partial_cm_cache_ok_rate"], 1.0)
        self.assertIn("partial_cm_cache_live_vars_median", row)
        self.assertEqual(row["partial_bitset_baseline_kind"], "raw_ast_recursive")

        # A words request below the six-variable crossover truthfully records
        # the flat compatibility engine used on both sides.
        cm_bench.args = _partial_args(cm_words_eval=True, cm_hybrid_threshold=16)
        words_row = cm_bench.time_partial_context_workload(
            3,
            expr,
            contexts,
            trial=0,
            expr_style="test",
            bit_env=None,
            sample_rng=np.random.default_rng(2),
            robdd_order_seed=3,
        )
        self.assertEqual(words_row["partial_bitset_baseline_kind"], "raw_ast_flat")
        self.assertEqual(words_row["partial_bitset_restricted_baseline_kinds"], "raw_ast_flat")
        self.assertEqual(words_row["partial_bitset_restricted_ok_rate"], 1.0)
        self.assertEqual(words_row["partial_cm_no_cache_ok_rate"], 1.0)
        self.assertEqual(words_row["partial_cm_cache_ok_rate"], 1.0)

    def test_large_n_does_not_force_full_reference_tables(self) -> None:
        cm_bench.args = _partial_args(full_tt_max_n=4, sampled_correctness=3)
        expr = Or(Var(0), Var(5))
        contexts = [{"x1": 1, "x2": 0, "x3": 1, "x4": 0, "x5": 1}]
        row = cm_bench.time_partial_context_workload(
            12,
            expr,
            contexts,
            trial=0,
            expr_style="test",
            bit_env=None,
            sample_rng=np.random.default_rng(4),
            robdd_order_seed=5,
        )
        self.assertEqual(row["partial_context_count"], 1)
        self.assertEqual(row["partial_cm_cache_ok_rate"], 1.0)

    def test_robdd_restriction_matches_reference_when_available(self) -> None:
        cm_bench.args = _partial_args(no_dd=False, no_robdd_dd=False, robdd_dd_backend="autoref")
        expr = Or(And(Var(0), Var(1)), Var(2))
        contexts = [{"x1": 1}, {"x2": 0}]
        refs = [
            cm_bench._partial_reference_array(expr, 3, c, cm_bench._partial_output_vars(3, c, "remaining-vars"))
            for c in contexts
        ]
        row = cm_bench._robdd_partial_context_workload(
            expr,
            3,
            contexts,
            output_mode="remaining-vars",
            reference_arrays=refs,
            sample_rng=np.random.default_rng(6),
            order_seed=7,
        )
        if row["partial_robdd_status"] == "ok":
            self.assertEqual(row["partial_robdd_ok_rate"], 1.0)
        else:
            self.assertIn(row["partial_robdd_status"], {"unavailable", "error"})

    def test_cli_writes_partial_csv_fields(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = root / "cm_bench.py"
        with tempfile.TemporaryDirectory() as td:
            cmd = [
                sys.executable,
                str(script),
                "--bench-partial-contexts",
                "--sizes",
                "4",
                "--trials",
                "1",
                "--max-depth",
                "2",
                "--expr-style",
                "mixed_no_constants",
                "--partial-contexts",
                "4",
                "--partial-fixed-var-count",
                "2",
                "--partial-output-mode",
                "remaining-vars",
                "--cm-use-persistent-cache",
                "--no-dd",
                "--out-prefix",
                "partial_cli",
            ]
            subprocess.run(cmd, cwd=td, check=True, capture_output=True, text=True)
            with (Path(td) / "partial_cli_raw.csv").open("r", newline="", encoding="utf-8") as f:
                raw_row = next(csv.DictReader(f))
            with (Path(td) / "partial_cli_summary.csv").open("r", newline="", encoding="utf-8") as f:
                summary_row = next(csv.DictReader(f))
        self.assertIn("partial_context_count", raw_row)
        self.assertIn("partial_cm_cache_total_s", raw_row)
        self.assertIn("partial_cm_cache_total_s_median", summary_row)


if __name__ == "__main__":
    unittest.main()
