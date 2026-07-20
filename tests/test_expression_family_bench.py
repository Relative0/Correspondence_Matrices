import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import cm_bench


def _family_args(**overrides):
    base = {
        "cm_hybrid_threshold": 7,
        "cm_max_full_output_vars": 16,
        "sampled_correctness": 0,
        "full_tt_max_n": 16,
        "no_bitset": False,
        "cm_use_persistent_cache": True,
        "no_dd": True,
        "no_robdd_dd": True,
        "robdd_dd_backend": "autoref",
        "robdd_order_policy": "fixed",
        "robdd_dynamic_reordering": False,
        "robdd_reorder_method": "sift",
        "robdd_order_sweeps": 1,
        "family_robdd_shared_manager": False,
        "family_no_robdd": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class ExpressionFamilyBenchTests(unittest.TestCase):
    def setUp(self) -> None:
        cm_bench.args = _family_args()

    def test_family_generation_produces_requested_number_of_variants(self) -> None:
        family = cm_bench.generate_expression_family(
            4,
            np.random.default_rng(1),
            3,
            "mixed_no_constants",
            family_size=7,
            variant_style="composition_mix",
        )
        self.assertEqual(len(family["variants"]), 7)

    def test_forced_shared_substructure_has_measurable_reuse(self) -> None:
        family = cm_bench.generate_expression_family(
            4,
            np.random.default_rng(2),
            3,
            "mixed_no_constants",
            family_size=8,
            variant_style="shared_block_mix",
            shared_blocks=3,
            force_shared_substructure=True,
        )
        diag = cm_bench.expression_family_diagnostics(
            family,
            4,
            family_id="test",
            variant_style="shared_block_mix",
            mutation_rate=0.15,
        )
        self.assertGreater(diag["family_reuse_ratio"], 0.0)
        self.assertGreater(diag["family_repeated_subtree_hash_count"], 0)

    def test_family_workload_correctness_and_cache_fields(self) -> None:
        family = cm_bench.generate_expression_family(
            4,
            np.random.default_rng(3),
            3,
            "mixed_no_constants",
            family_size=5,
            variant_style="composition_mix",
            force_shared_substructure=True,
        )
        row = cm_bench.time_expression_family_workload(
            4,
            family,
            family_id="test",
            trial=0,
            expr_style="mixed_no_constants",
            variant_style="composition_mix",
            mutation_rate=0.15,
            bit_env=cm_bench.build_bitset_env(["x0", "x1", "x2", "x3"]),
            sample_rng=np.random.default_rng(4),
            robdd_order_seed=5,
        )
        self.assertEqual(row["family_bitset_ok_rate"], 1.0)
        self.assertEqual(row["family_cm_no_cache_ok_rate"], 1.0)
        self.assertEqual(row["family_cm_cache_ok_rate"], 1.0)
        self.assertIn("family_cm_cache_persistent_hits_total", row)
        self.assertIn("family_cm_cache_persistent_misses_total", row)

    def test_robdd_unavailable_or_disabled_does_not_crash(self) -> None:
        cm_bench.args = _family_args(no_dd=False, no_robdd_dd=False, robdd_dd_backend="cudd")
        family = cm_bench.generate_expression_family(
            3,
            np.random.default_rng(5),
            2,
            "mixed_no_constants",
            family_size=3,
            variant_style="subtree_wrap",
        )
        row = cm_bench.time_expression_family_workload(
            3,
            family,
            family_id="test",
            trial=0,
            expr_style="mixed_no_constants",
            variant_style="subtree_wrap",
            mutation_rate=0.15,
            bit_env=cm_bench.build_bitset_env(["x0", "x1", "x2"]),
            sample_rng=np.random.default_rng(6),
            robdd_order_seed=7,
        )
        self.assertIn("family_robdd_build_total_time_s", row)

    def test_cli_writes_family_csv_fields(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = root / "cm_bench.py"
        with tempfile.TemporaryDirectory() as td:
            cmd = [
                sys.executable,
                str(script),
                "--bench-expression-family",
                "--sizes",
                "4",
                "--trials",
                "1",
                "--max-depth",
                "2",
                "--expr-style",
                "mixed_no_constants",
                "--family-size",
                "4",
                "--family-force-shared-substructure",
                "--cm-use-persistent-cache",
                "--family-no-robdd",
                "--out-prefix",
                "family_cli",
            ]
            subprocess.run(cmd, cwd=td, check=True, capture_output=True, text=True)
            with (Path(td) / "family_cli_raw.csv").open("r", newline="", encoding="utf-8") as f:
                raw_row = next(csv.DictReader(f))
            with (Path(td) / "family_cli_summary.csv").open("r", newline="", encoding="utf-8") as f:
                summary_row = next(csv.DictReader(f))
        self.assertIn("family_reuse_ratio", raw_row)
        self.assertIn("family_cm_cache_total_time_s", raw_row)
        self.assertEqual(raw_row["family_robdd_status"], "skipped")
        self.assertIn("family_cm_cache_total_time_s_median", summary_row)


if __name__ == "__main__":
    unittest.main()
