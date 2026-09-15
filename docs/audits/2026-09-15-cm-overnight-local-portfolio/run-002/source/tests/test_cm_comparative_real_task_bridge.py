"""Cached-real cohort and coverage-plan controls."""

import unittest

from scripts import cm_comparative_real_task_bridge as bridge


class ComparativeRealTaskBridgeTests(unittest.TestCase):
    def test_selection_retains_complete_candidate_and_admission_ledgers(self):
        scenarios, selection = bridge.cohort()
        self.assertEqual(len(scenarios), 8)
        self.assertEqual(len(selection["default_candidate_ledger"]), 120)
        self.assertEqual(len(selection["known_change_candidate_ledger"]), 120)
        self.assertEqual(len(selection["original_transition_admissions"]), 21)
        self.assertEqual(sum(row["selected"] for row in selection["default_candidate_ledger"]), 7)
        self.assertEqual(sum(row["selected"] for row in selection["known_change_candidate_ledger"]), 1)
        self.assertTrue(selection["known_change_control_output_selected"])

    def test_bundle_has_one_functional_cell_per_declared_combination(self):
        plan, oracles, _selection = bridge.build_bundle()
        self.assertEqual(len(plan["cases"]), 8)
        self.assertEqual(len(plan["cells"]), 384)
        self.assertEqual(len({row["cell_id"] for row in plan["cells"]}), 384)
        self.assertEqual(set(oracles["cases"]), {row["case_id"] for row in plan["cases"]})
        self.assertFalse(plan["performance_claim_permitted"])

    def test_default_zero_changes_and_named_control_nonzero_stay_separate(self):
        plan, oracles, _selection = bridge.build_bundle()
        defaults = [oracles["cases"][row["case_id"]]["equivalence_delta"]["rows"][1]
                    for row in plan["cases"][:7]]
        control = oracles["cases"][plan["cases"][7]["case_id"]]["equivalence_delta"]["rows"][1]
        self.assertEqual([row["changed_assignments"] for row in defaults], [0] * 7)
        self.assertEqual(control["changed_assignments"], 2)
        self.assertEqual(plan["cases"][7]["selection_role"], "known_nonzero_positive_control")


if __name__ == "__main__":
    unittest.main()
