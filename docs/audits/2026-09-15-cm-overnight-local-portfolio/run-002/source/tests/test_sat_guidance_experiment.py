from __future__ import annotations

from pathlib import Path
import importlib.util
import tempfile
import unittest

from cmbench.recognition.sat_guidance_experiment import (
    FAMILIES, SatGuidanceConfig, make_sat_guidance_dataset,
    run_sat_guidance_experiment, verify_sat_guidance_run,
)


ROOT = Path(__file__).resolve().parents[1]


class SatGuidanceDatasetTests(unittest.TestCase):
    def test_registered_e2_evidence_preserves_full_research_agenda(self):
        import json

        docs = ROOT / "docs/recognition"
        register = json.loads((docs / "experiment_register.json").read_text())
        machine = json.loads((
            docs / "learning_milestone_e2_sat_guidance_results.json").read_text())
        self.assertEqual([track["id"] for track in register["tracks"]],
                         [f"R{index:02d}" for index in range(1, 19)])
        self.assertEqual(len(register["applications"]), 8)
        self.assertIn("E2", register["milestones"]["E"])
        self.assertTrue(machine["exact"])
        self.assertFalse(machine["production_promotion"])
        self.assertEqual(machine["runpod"], {
            "used": False, "cost_usd": 0.0,
            "reason": "predeclared Windows timing gate failed",
        })

    def test_frozen_split_has_balanced_assumption_outcomes_and_unique_cases(self):
        config = SatGuidanceConfig(
            train_per_family=1, validation_per_family=1,
            test_per_family=1, repetitions=3)
        first = make_sat_guidance_dataset(config)
        second = make_sat_guidance_dataset(config)
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(FAMILIES) * 3)
        self.assertEqual(len({row["base_alpha_structural_sha256"] for row in first}),
                         len(first))
        for row in first:
            self.assertEqual(len(row["assumptions"]), 8)
            for assumptions in row["assumptions"]:
                self.assertEqual(len({abs(literal) for literal in assumptions}),
                                 len(assumptions))

    @unittest.skipUnless(importlib.util.find_spec("pysat") is not None,
                         "python-sat unavailable")
    def test_bounded_end_to_end_run_replays_all_exact_contracts(self):
        config = SatGuidanceConfig(
            train_per_family=1, validation_per_family=1,
            test_per_family=1, repetitions=3, max_seconds=120)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            summary = run_sat_guidance_experiment(
                config, output, progress=lambda _message: None)
            verified = verify_sat_guidance_run(output)
        self.assertTrue(summary["exact"])
        self.assertTrue(summary["advice_off_exact"])
        self.assertFalse(summary["count_task_measured"])
        self.assertEqual(verified["status"], "passed")
        self.assertGreater(verified["trusted_solver_replays"], 0)


if __name__ == "__main__":
    unittest.main()
