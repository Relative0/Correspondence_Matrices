"""Task-matched functional adapters and adversarial contract controls."""

from __future__ import annotations

import copy
import sys
import unittest

from cmbench.comparative import tasks
from scripts.cm_session_contracts import Engine


class TinySAT:
    """Simulated brute-force solver used only for bounded adapter unit tests."""

    def __init__(self):
        self.clauses, self.n, self.closed = [], 0, False

    def add_clause(self, clause):
        self.clauses.append(list(clause))
        self.n = max(self.n, max(map(abs, clause), default=0))

    def solve(self, assumptions):
        fixed = {abs(literal) - 1: literal > 0 for literal in assumptions}
        free = [index for index in range(self.n) if index not in fixed]
        for bits in range(1 << len(free)):
            values = {**fixed, **{variable: bool((bits >> offset) & 1)
                                  for offset, variable in enumerate(free)}}
            if all(any(values[abs(literal) - 1] == (literal > 0) for literal in clause)
                   for clause in self.clauses):
                return True
        return False

    def delete(self):
        self.closed = True


def scenario():
    return {
        "id": "matched-k6",
        "k": 6,
        "feature_names": [f"x{i}" for i in range(6)],
        "versions": [
            {"id": "base", "clauses": [[1, -6], [-1, 6]]},
            {"id": "duplicate", "clauses": [[1, -6], [-1, 6], [1, -6]]},
            {"id": "restricted", "clauses": [[1, -6], [-1, 6], [-1]]},
        ],
        "source": {"kind": "synthetic", "purpose": "task_adapter_control"},
    }


TRACES = {
    "exact_count": [{"version": 0}, {"version": 1}, {"version": 2}],
    "sat_status": [{"version": 0, "assumptions": []}, {"version": 2, "assumptions": [1]}],
    "witness": [{"version": 0, "assumptions": []}, {"version": 2, "assumptions": [1]}],
    "partial_context": [
        {"version": 0, "assumptions": []},
        {"version": 0, "assumptions": [1]},
        {"version": 2, "assumptions": [1]},
        {"version": 2, "assumptions": []},
    ],
    "version_history": [
        {"version": 0, "assumptions": [-1]},
        {"version": 1, "assumptions": [-1, -6]},
        {"version": 2, "assumptions": [-1]},
        {"version": 0, "assumptions": []},
    ],
    "equivalence_delta": [
        {"before": 0, "after": 1},
        {"before": 1, "after": 2},
        {"before": 2, "after": 0},
    ],
}


class ComparativeTaskTests(unittest.TestCase):
    def run_task(self, task, backend, lifecycle):
        expected = tasks.scalar_oracle(scenario(), task, TRACES[task])
        contract = tasks.task_contract(
            contract_id=f"{task}-{backend}-{lifecycle}", task=task, backend=backend,
            lifecycle=lifecycle, k=6, queries=len(TRACES[task]),
            expected_sha256=tasks.semantic_digest(task, expected),
        )
        created = []

        def factory():
            solver = TinySAT()
            created.append(solver)
            return solver

        result = tasks.execute_task(
            scenario=scenario(), task=task, trace=TRACES[task], backend=backend,
            lifecycle=lifecycle, contract=contract, case_id="matched-k6",
            solver_factory=factory if backend == "sat" else None,
            native_identity={"simulated": True} if backend == "sat" else None,
        )
        tasks.validate_task_result(result, contract, expected)
        self.assertTrue(all(solver.closed for solver in created))
        return result

    def test_all_tasks_backends_and_lifecycles_match_independent_oracle(self):
        for task in tasks.TASKS:
            for backend in tasks.BACKENDS:
                outputs = []
                for lifecycle in tasks.LIFECYCLES:
                    with self.subTest(task=task, backend=backend, lifecycle=lifecycle):
                        result = self.run_task(task, backend, lifecycle)
                        outputs.append(result["identity"]["semantic_output"])
                self.assertEqual(outputs[0], outputs[1])

    def test_duplicate_version_is_equivalent_and_real_edit_is_not(self):
        rows = tasks.scalar_oracle(scenario(), "equivalence_delta", TRACES["equivalence_delta"])
        self.assertEqual([(row["equivalent"], row["changed_assignments"]) for row in rows],
                         [(True, 0), (False, 16), (False, 16)])

    def test_witness_is_canonical_and_unsat_is_explicit(self):
        rows = tasks.scalar_oracle(scenario(), "witness", TRACES["witness"])
        self.assertEqual([item["value"] for item in rows[0]["witness"]], [0, 0, 0, 0, 0, 0])
        self.assertIsNone(rows[1]["witness"])

    def test_resident_reuses_one_engine_and_fresh_rebuilds_each_evaluation(self):
        resident = self.run_task("equivalence_delta", "cm", "resident_engine")
        fresh = self.run_task("equivalence_delta", "cm", "fresh_engine")
        self.assertEqual(resident["identity"]["counters"]["engine_instances"], 1)
        self.assertEqual(fresh["identity"]["counters"]["engine_instances"], 6)
        self.assertLess(resident["identity"]["counters"]["programs_built"],
                        fresh["identity"]["counters"]["programs_built"])

    def test_invalid_trace_contract_and_selector_injection_refuse(self):
        expected = tasks.scalar_oracle(scenario(), "partial_context", TRACES["partial_context"])
        contract = tasks.task_contract(
            contract_id="partial-cm", task="partial_context", backend="cm",
            lifecycle="resident_engine", k=6, queries=len(expected),
            expected_sha256=tasks.semantic_digest("partial_context", expected),
        )
        for trace in (
            [],
            [{"version": True, "assumptions": []}],
            [{"version": 0, "assumptions": [7]}],
            [{"version": 0, "assumptions": [1, -1]}],
            [{"version": 0, "assumptions": [], "answer": True}],
        ):
            with self.subTest(trace=trace), self.assertRaises(ValueError):
                tasks.execute_task(scenario=scenario(), task="partial_context", trace=trace, backend="cm",
                                   lifecycle="resident_engine", contract=contract, case_id="matched-k6")

    def test_mutated_semantic_output_counts_or_claims_are_refused(self):
        result = self.run_task("exact_count", "cnf", "resident_engine")
        expected = tasks.scalar_oracle(scenario(), "exact_count", TRACES["exact_count"])
        contract = tasks.task_contract(
            contract_id="exact_count-cnf-resident_engine", task="exact_count", backend="cnf",
            lifecycle="resident_engine", k=6, queries=len(expected),
            expected_sha256=tasks.semantic_digest("exact_count", expected),
        )
        mutations = []
        changed = copy.deepcopy(result)
        changed["identity"]["semantic_output"]["rows"][0]["count"] += 1
        mutations.append(changed)
        changed = copy.deepcopy(result)
        changed["identity"]["counters"]["engine_instances"] = True
        mutations.append(changed)
        changed = copy.deepcopy(result)
        changed["identity"]["performance_claim_permitted"] = True
        mutations.append(changed)
        for changed in mutations:
            with self.assertRaises(ValueError):
                tasks.validate_task_result(changed, contract, expected)

    def test_engine_cleanup_survives_evaluation_error(self):
        expected = tasks.scalar_oracle(scenario(), "sat_status", TRACES["sat_status"])
        contract = tasks.task_contract(
            contract_id="cleanup-sat", task="sat_status", backend="sat",
            lifecycle="resident_engine", k=6, queries=len(expected),
            expected_sha256=tasks.semantic_digest("sat_status", expected),
        )

        class Broken(TinySAT):
            def solve(self, assumptions):
                raise RuntimeError("injected")

        solver = Broken()
        with self.assertRaises(RuntimeError):
            tasks.execute_task(
                scenario=scenario(), task="sat_status", trace=TRACES["sat_status"], backend="sat",
                lifecycle="resident_engine", contract=contract, case_id="matched-k6",
                solver_factory=lambda: solver, native_identity={"simulated": True},
            )
        self.assertTrue(solver.closed)


if __name__ == "__main__":
    unittest.main()
