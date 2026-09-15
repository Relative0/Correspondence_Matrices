from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cmbench.recognition.profitability_rule_experiment import (
    DeterministicProfitabilityGate, ProfitabilityRuleConfig, make_versions,
    run_profitability_rule_experiment,
)
from cmbench.recognition.natural_rule_experiment import (
    NaturalRuleConfig, load_natural_cases, run_natural_rule_experiment,
)


class ProfitabilityGateTests(unittest.TestCase):
    def test_gate_uses_only_task_reuse_and_upstream_size(self):
        gate = DeterministicProfitabilityGate(min_reuses=32, min_estimated_nodes=8)
        self.assertEqual(gate.decide("complete_vector", 1, 40).reason,
                         "insufficient_expected_reuse")
        self.assertEqual(gate.decide("complete_vector", 32, 4).reason, "cone_too_small")
        self.assertTrue(gate.decide("complete_vector", 32, 40).apply_rules)
        self.assertFalse(gate.decide("single_assignment", 128, 40).apply_rules)

    def test_versions_cover_add_remove_and_revert(self):
        config = ProfitabilityRuleConfig(cone_count=16, rounds=1, max_seconds=30)
        versions, manifest = make_versions(config)
        self.assertEqual([len(versions[version]) for version in ("v1", "v2", "v3", "v4")],
                         [16, 16, 16, 16])
        self.assertEqual(manifest["versions"]["v3"]["removed_cone_ids"],
                         ["cone-004", "cone-005"])
        self.assertEqual(manifest["versions"]["v3"]["added_cone_ids"],
                         ["cone-016", "cone-017"])
        self.assertEqual(manifest["versions"]["v4"]["reverted_cone_ids"],
                         ["cone-000", "cone-001"])

    def test_small_run_is_exact_and_independently_verifiable(self):
        config = ProfitabilityRuleConfig(cone_count=16, rounds=1, max_seconds=30)
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            result = run_profitability_rule_experiment(config, run, progress=lambda _message: None)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["semantic_mismatches"], 0)
            self.assertTrue(result["criteria"]["hardening_met"])
            self.assertEqual(result["row_count"], 16)
            from scripts.crse_rule_profitability_verify import verify
            verification = verify(run)
            self.assertEqual(verification["status"], "pass")
            self.assertEqual(verification["proof_rows_reproduced"], 16)

    def test_register_still_preserves_all_tracks(self):
        root = Path(__file__).resolve().parents[1]
        register = json.loads((root / "docs/recognition/experiment_register.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual([track["id"] for track in register["tracks"]],
                         [f"R{index:02d}" for index in range(1, 19)])
        self.assertEqual(len(register["applications"]), 8)
        reports = {item.get("report") for track in register["tracks"] for item in track["results"]}
        self.assertIn("RULE_PROFITABILITY_MILESTONE_D4_2026_08_29.md", reports)
        self.assertIn("NATURAL_RULE_PROFITABILITY_MILESTONE_D5_2026_08_29.md", reports)
        d4 = json.loads((root / "docs/recognition/rule_profitability_milestone_d4_results.json")
                        .read_text(encoding="utf-8"))
        d5 = json.loads((root / "docs/recognition/natural_rule_profitability_milestone_d5_results.json")
                        .read_text(encoding="utf-8"))
        self.assertEqual(d4["verification"]["semantic_mismatches"], 0)
        self.assertEqual(d5["verification"]["natural_cases_verified"], 32)
        self.assertFalse(d5["criteria"]["production_promotion"])


class NaturalRuleProfitabilityTests(unittest.TestCase):
    def test_natural_selection_is_sealed_and_bounded(self):
        config = NaturalRuleConfig(case_count=8, rounds=1, max_seconds=30)
        cases, manifest = load_natural_cases(config)
        self.assertEqual(len(cases), 8)
        self.assertFalse(manifest["prior_epfl_slices_overlap"])
        self.assertTrue(all(9 <= case.n_vars <= 12 for case in cases))

    def test_small_natural_run_is_independently_verifiable(self):
        config = NaturalRuleConfig(case_count=8, rounds=1, max_seconds=30)
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            result = run_natural_rule_experiment(config, run, progress=lambda _message: None)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["semantic_mismatches"], 0)
            from scripts.crse_natural_rule_verify import verify
            verification = verify(run)
            self.assertEqual(verification["status"], "pass")
            self.assertEqual(verification["natural_cases_verified"], 8)


if __name__ == "__main__":
    unittest.main()
