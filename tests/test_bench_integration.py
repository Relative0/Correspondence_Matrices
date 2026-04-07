import csv
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class BenchIntegrationTests(unittest.TestCase):
    def _run_and_read_summary(self, tmpdir: Path, out_prefix: str, extra_args):
        root = Path(__file__).resolve().parents[1]
        script = root / "cm_bench.py"
        cmd = [
            sys.executable,
            str(script),
            "--sizes",
            "4",
            "--trials",
            "1",
            "--max-depth",
            "2",
            "--seed",
            "123",
            "--out-prefix",
            out_prefix,
            "--no-sympy",
            "--no-robdd",
            "--no-dd",
            "--no-espresso",
            "--no-bdd-sop",
            "--no-numba",
        ] + list(extra_args)

        subprocess.run(cmd, cwd=tmpdir, check=True, capture_output=True, text=True)
        summary_path = tmpdir / f"{out_prefix}_summary.csv"
        self.assertTrue(summary_path.exists(), msg=f"missing summary CSV: {summary_path}")
        with summary_path.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)
        return rows[0]

    @staticmethod
    def _parse_optional_float(raw: str):
        if raw is None:
            return None
        txt = str(raw).strip()
        if txt == "":
            return None
        val = float(txt)
        if math.isnan(val):
            return None
        return val

    def test_cm_parallel_experiment_outputs_columns_and_ratios(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            row_on = self._run_and_read_summary(
                tmpdir,
                "bench_on",
                [
                    "--cm-layout",
                    "balanced",
                    "--cm-hybrid-threshold",
                    "7",
                    "--cm-compare-hybrid",
                    "--cm-parallel",
                    "--cm-parallel-workers",
                    "2",
                    "--cm-parallel-min-n",
                    "1",
                    "--cm-parallel-min-nodes",
                    "1",
                    "--cm-parallel-chunk-rows",
                    "8",
                    "--experiment",
                    "cm_vs_bitset",
                ],
            )
            row_off = self._run_and_read_summary(tmpdir, "bench_off", [])

            for col in [
                "cm_layout",
                "cm_hybrid_time_s_median",
                "cm_hybrid_tt_extract_time_s_median",
                "cm_partial_hybrid_time_s_median",
                "cm_partial_hybrid_tt_extract_time_s_median",
                "cm_parallel_time_s_median",
                "cm_tt_extract_time_s_median",
                "cm_parallel_tt_extract_time_s_median",
                "bitset_extract_time_s_median",
                "cm_hybrid_ok_all",
                "cm_partial_hybrid_ok_all",
                "cm_parallel_ok_all",
                "ratio_cm_hybrid_over_cm",
                "ratio_cm_hybrid_over_bitset",
                "ratio_cm_partial_hybrid_over_cm",
                "ratio_cm_partial_hybrid_over_bitset",
                "ratio_cm_parallel_over_cm",
                "ratio_cm_parallel_over_bitset",
                "ratio_cm_plus_extract_over_bitset_plus_extract",
                "cm_subtree_cache_hits_median",
                "cm_canonical_rewrites_median",
                "cm_pruned_branches_median",
                "cm_materializations_median",
                "cm_live_vars_max_median",
                "cm_bitset_materializations_median",
                "cm_numpy_materializations_median",
                "cm_materialization_live_vars_total_median",
                "cm_materialization_avg_k_median",
                "cm_hybrid_bitset_materializations_median",
                "cm_hybrid_numpy_materializations_median",
                "cm_hybrid_materialization_live_vars_total_median",
                "cm_hybrid_materialization_avg_k_median",
                "cm_hybrid_hybrid_depth_max_median",
                "cm_hybrid_full_collapse_occurred_median",
                "cm_partial_hybrid_bitset_materializations_median",
                "cm_partial_hybrid_numpy_materializations_median",
                "cm_partial_hybrid_materialization_live_vars_total_median",
                "cm_partial_hybrid_materialization_avg_k_median",
                "cm_partial_hybrid_hybrid_depth_max_median",
                "cm_partial_hybrid_full_collapse_occurred_median",
            ]:
                self.assertIn(col, row_on)
                self.assertIn(col, row_off)

            self.assertEqual(row_on["cm_layout"], "balanced")
            on_hybrid_time = self._parse_optional_float(row_on["cm_hybrid_time_s_median"])
            on_partial_time = self._parse_optional_float(row_on["cm_partial_hybrid_time_s_median"])
            on_parallel_time = self._parse_optional_float(row_on["cm_parallel_time_s_median"])
            on_ratio_hybrid_cm = self._parse_optional_float(row_on["ratio_cm_hybrid_over_cm"])
            on_ratio_hybrid_bitset = self._parse_optional_float(row_on["ratio_cm_hybrid_over_bitset"])
            on_ratio_partial_cm = self._parse_optional_float(row_on["ratio_cm_partial_hybrid_over_cm"])
            on_ratio_partial_bitset = self._parse_optional_float(row_on["ratio_cm_partial_hybrid_over_bitset"])
            on_ratio_cm = self._parse_optional_float(row_on["ratio_cm_parallel_over_cm"])
            on_ratio_bitset = self._parse_optional_float(row_on["ratio_cm_parallel_over_bitset"])
            self.assertIsNotNone(on_hybrid_time)
            self.assertIsNotNone(on_partial_time)
            self.assertIsNotNone(on_parallel_time)
            self.assertIsNotNone(on_ratio_hybrid_cm)
            self.assertIsNotNone(on_ratio_hybrid_bitset)
            self.assertIsNotNone(on_ratio_partial_cm)
            self.assertIsNotNone(on_ratio_partial_bitset)
            self.assertIsNotNone(on_ratio_cm)
            self.assertIsNotNone(on_ratio_bitset)
            self.assertEqual(row_on["cm_hybrid_full_collapse_occurred_median"], "1.0")
            self.assertEqual(row_on["cm_partial_hybrid_full_collapse_occurred_median"], "0.0")

            off_hybrid_time = self._parse_optional_float(row_off["cm_hybrid_time_s_median"])
            off_partial_time = self._parse_optional_float(row_off["cm_partial_hybrid_time_s_median"])
            off_parallel_time = self._parse_optional_float(row_off["cm_parallel_time_s_median"])
            self.assertIsNone(off_hybrid_time)
            self.assertIsNone(off_partial_time)
            self.assertIsNone(off_parallel_time)


if __name__ == "__main__":
    unittest.main()
