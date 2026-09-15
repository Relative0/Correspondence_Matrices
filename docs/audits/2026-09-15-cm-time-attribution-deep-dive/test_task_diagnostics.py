"""Correctness and accounting tests for audit-only task adapters."""
import importlib.util
from pathlib import Path
import sys
import unittest

PATH = Path(__file__).with_name("task_diagnostics.py")
spec = importlib.util.spec_from_file_location("task_diagnostics", PATH)
td = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = td
spec.loader.exec_module(td)


class TaskDiagnosticsTests(unittest.TestCase):
    def test_historical_adapter_uses_pinned_baseline_and_exact_all_batch_answers(self):
        helper, _, cm, _, _, _, _ = td.runtime()
        case = td.fixture_case("balanced-k8")
        expr = helper.parse_expression(case["expression"])
        raw_rows = helper.assignment_rows(td.inputs()["assignment_generator"], 8)
        expected = helper.assignment_output(expr, 8, raw_rows)
        nodes = [td.batch_adapter(expr, structural=False), td.batch_adapter(expr, structural=True),
                 cm.compile_expr_to_cm_ir(expr, reuse_cache=False, persistent_cache=False)]
        self.assertEqual(len(expected), 4096)
        for node in nodes:
            self.assertEqual(helper._cm_batch_values(node, raw_rows, 8), expected)

    def test_cse_adapter_preserves_equal_subexpression_sharing_without_rewrite(self):
        _, _, _, ex, *_ = td.runtime()
        expr = ex.Or(ex.And(ex.Var(0), ex.Var(1)), ex.And(ex.Var(0), ex.Var(1)))
        raw = td.batch_adapter(expr, structural=False)
        cse = td.batch_adapter(expr, structural=True)
        self.assertIsNot(raw.args[0], raw.args[1])
        self.assertIs(cse.args[0], cse.args[1])
        self.assertEqual(cse.op, "OR")

    def test_q64_restriction_delivers_each_exact_cofactor(self):
        for arm in ("cse_packed", "cm_packed"):
            cell = {"case": "balanced-k8", "task": "restriction", "arm": arm, "q": 64}
            result = td.task_operation(cell, td.oracle_for(cell), td.Phases(False))
            self.assertTrue(result["correct"])
            self.assertEqual(result["query_count"], 64)
            self.assertEqual(result["contexts_unique"], 4)
            self.assertEqual(result["output_bytes"], 512)

    def test_exact_count_sat_and_equivalence_on_false_and_nontrivial_cases(self):
        for case in ("contradiction-k4", "balanced-k8"):
            for task in ("exact_count", "sat_status", "equivalence_status"):
                for arm in ("cse_packed", "cm_packed", "sympy_task"):
                    cell = {"case": case, "task": task, "arm": arm, "q": 1}
                    self.assertTrue(td.task_operation(cell, td.oracle_for(cell), td.Phases(False))["correct"])

    def test_expression_delivery_is_complete_and_semantically_verified(self):
        for arm in ("cse_shared_minimizer", "cm_shared_minimizer", "sympy_default", "sympy_forced"):
            cell = {"case": "absorption-k4", "task": "simplified_expression", "arm": arm, "q": 1}
            result = td.task_operation(cell, td.oracle_for(cell), td.Phases(False))
            self.assertTrue(result["correct"])
            self.assertGreater(result["output_bytes"], 0)
            self.assertEqual(result["quality"]["literal_occurrences"], 1)

    def test_family_both_cache_modes_preserve_all_outputs(self):
        for arm in ("cse_family", "cm_cache_off", "cm_cache_on", "public_cache_off", "public_cache_on"):
            td.reset_caches()
            cell = {"case": "identical_seed2", "task": "family", "arm": arm, "q": 1}
            result = td.family_operation(cell, td.oracle_for(cell), td.Phases(False))
            self.assertTrue(result["correct"])
            self.assertEqual(result["output_bytes"], 16)

    def test_phase_accounting_is_exclusive_and_cpu_wall_totals_close(self):
        cell = {"case": "balanced-k8", "task": "restriction", "arm": "cm_packed", "q": 1}
        record = td.execute(cell, td.oracle_for(cell), phase=True)
        self.assertEqual(sum(row["wall_ns"] for row in record["phases"].values()), record["wall_ns"])
        self.assertEqual(sum(row["cpu_ns"] for row in record["phases"].values()), record["cpu_ns"])
        self.assertAlmostEqual(sum(row["wall_percent_caller"] for row in record["phases"].values()), 100)


if __name__ == "__main__":
    unittest.main()
