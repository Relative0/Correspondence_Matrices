"""Pure planning controls for the balanced comparative task pilot."""

import unittest

from cmbench.comparative import tasks
from cmbench.comparative.schedule import validate_plan
from scripts import cm_comparative_task_pilot as pilot


class ComparativeTaskPilotTests(unittest.TestCase):
    def test_plans_are_deterministic_complete_and_counterbalanced(self):
        case, traces = pilot.scenario(), pilot.traces()
        first, expected = pilot._plans(case, traces)
        second, expected_again = pilot._plans(case, traces)
        self.assertEqual((first, expected), (second, expected_again))
        self.assertEqual(len(first), len(tasks.TASKS) * len(tasks.LIFECYCLES))
        self.assertEqual(sum(len(plan["cells"]) for plan in first), 384)
        for plan in first:
            validate_plan(plan)
            self.assertEqual(len(plan["cells"]), 32)

    def test_oracles_retain_no_change_real_change_rollback_and_unsat(self):
        case, traces = pilot.scenario(), pilot.traces()
        delta = tasks.scalar_oracle(case, "equivalence_delta", traces["equivalence_delta"])
        self.assertEqual([(row["equivalent"], row["changed_assignments"]) for row in delta],
                         [(True, 0), (False, 16), (False, 16)])
        partial = tasks.scalar_oracle(case, "partial_context", traces["partial_context"])
        self.assertTrue(partial[0]["satisfiable"])
        self.assertFalse(partial[3]["satisfiable"])
        self.assertEqual(partial[0]["satisfiable"], partial[5]["satisfiable"])

    def test_task_contracts_pin_independent_expected_outputs(self):
        case, traces = pilot.scenario(), pilot.traces()
        plans, expected = pilot._plans(case, traces)
        for plan in plans:
            for backend in tasks.BACKENDS:
                contract = plan["contracts"][backend]
                self.assertEqual(contract["validation"]["required_output_sha256"],
                                 expected[plan["task"]]["sha256"])
                self.assertFalse(contract["validation"]["validation_in_timed_span"])


if __name__ == "__main__":
    unittest.main()
