"""Invariant checks on independently reaggregated, already measured records."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("recompute", HERE / "recompute_frozen_evidence.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FrozenEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads((HERE / "frozen_evidence.json").read_text(encoding="utf-8"))

    def test_same_row_sums_used_for_phase_percent(self):
        rows = [{"arm": "a", "total": 10, "phase": 1},
                {"arm": "a", "total": 100, "phase": 90}]
        out = MODULE.phase_summary(rows, ["arm"], "total", ["phase"])[0]
        self.assertAlmostEqual(out["aggregate_phase_percent"]["phase"], 100 * 91 / 110)

    def test_all_architecture_stages_reconcile_including_serialization(self):
        for study in self.evidence["architecture"].values():
            for row in study["arm_phase_statistics"]:
                metrics = row["metrics"]
                self.assertIn("serialization_ns_when_applicable", metrics)
                total = metrics["accounted_total_ns"]["sum"]
                stages = sum(value["sum"] for key, value in metrics.items() if key != "accounted_total_ns")
                self.assertEqual(total, stages)
                self.assertAlmostEqual(sum(row["aggregate_phase_percent"].values()), 100)

    def test_sympy_nested_partitions_reconcile_without_double_counting(self):
        for row in self.evidence["sympy_gate"]["arm_statistics"]:
            metrics = row["metrics"]
            caller = metrics["caller_total_ns"]["sum"]
            task = metrics["task_total_ns"]["sum"]
            self.assertEqual(caller, task + metrics["outside_task_ns"]["sum"])
            named = sum(value["sum"] for key, value in metrics.items()
                        if value and key not in {"caller_total_ns", "task_total_ns", "outside_task_ns", "task_unattributed_ns"})
            self.assertEqual(task, named + metrics["task_unattributed_ns"]["sum"])

    def test_warm_pass_is_not_a_cold_phase(self):
        for row in self.evidence["continuation_development"]["session_statistics"]:
            self.assertIn("warm_ns", row["metrics"])
            self.assertNotIn("warm_ns", row["aggregate_phase_percent"])
            self.assertAlmostEqual(sum(row["aggregate_phase_percent"].values()), 100)

    def test_gate_recomputations_and_binding_checks_all_match(self):
        gate = self.evidence["sympy_gate"]
        self.assertEqual(gate["rows"], 186)
        self.assertEqual(gate["status_counts"], {"ok": 186})
        self.assertEqual(len(gate["recomputed_gate_ratios"]), 9)
        self.assertTrue(all(row["matches_review"] for row in gate["recomputed_gate_ratios"]))
        self.assertEqual(len(self.evidence["predecessor_binding_checks"]), 26)
        self.assertTrue(all(row["matches"] for row in self.evidence["predecessor_binding_checks"]))

    def test_no_fixture_or_oracle_input_files_consumed(self):
        for source in self.evidence["sources"]:
            name = Path(source["path"]).name.lower()
            self.assertNotIn(name, {"fixtures.json", "frozen_inputs.json", "oracles.json"})
            self.assertNotIn("-oracles.json", name)

    def test_existing_output_is_never_overwritten_and_verify_is_read_only(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            output = Path(directory) / "result.json"
            self.assertEqual(MODULE.publish_result({"value": 1}, output), "created")
            original = output.read_bytes()
            with self.assertRaises(FileExistsError):
                MODULE.publish_result({"value": 2}, output)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(MODULE.publish_result({"value": 1}, output, verify=True), "verified_without_writing")
            with self.assertRaises(AssertionError):
                MODULE.publish_result({"value": 2}, output, verify=True)
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
