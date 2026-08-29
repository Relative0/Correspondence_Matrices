"""Matched-state regression and negative controls; native execution is separate."""
from collections import OrderedDict
import copy
import io
import sys
import unittest
from unittest.mock import patch

from scripts import cm_session_contracts as sessions
from scripts import cm_measurement_verify as base


class TinySAT:
    """Deliberately simulated brute-force solver, used only at tiny widths."""
    def __init__(self):
        self.clauses, self.calls, self.n, self.closed = [], [], 0, False

    def add_clause(self, clause):
        self.clauses.append(list(clause))
        self.n = max(self.n, max(map(abs, clause), default=0))

    def solve(self, assumptions):
        self.calls.append(list(assumptions))
        fixed = {abs(lit) - 1: lit > 0 for lit in assumptions}
        free = [i for i in range(self.n) if i not in fixed]
        for bits in range(1 << len(free)):
            values = {**fixed, **{i: bool((bits >> j) & 1) for j, i in enumerate(free)}}
            if all(any(values[abs(lit) - 1] == (lit > 0) for lit in clause) for clause in self.clauses):
                return True
        return False

    def delete(self):
        self.closed = True


class SessionContractTests(unittest.TestCase):
    def request(self, scenario=None, backend="cm", lifecycle="reused", task="partial_configuration"):
        scenario = copy.deepcopy(scenario or sessions.synthetic_scenarios()[1])
        partial, delta = sessions.traces(scenario)
        return {"scenario": scenario, "backend": backend, "lifecycle": lifecycle, "task": task,
                "trace": partial if task == "partial_configuration" else delta,
                "native_identity": {"simulated": True} if backend == "sat" else None}

    def result(self, request, factory=TinySAT):
        result = sessions.execute(request, factory)
        result.update(pid=123, interpreter=sys.executable, source_root=str(sessions.ROOT),
                      request_sha256=sessions.digest(request), native_identity=request["native_identity"])
        sessions.validate_result(result, request, sessions.ROOT, [123], sessions.oracle(request["scenario"]))
        return result

    def test_synthetic_scenarios_and_traces_are_deterministic_and_include_undo(self):
        self.assertEqual(sessions.synthetic_scenarios(), sessions.synthetic_scenarios())
        for scenario in sessions.synthetic_scenarios():
            partial, delta = sessions.traces(scenario)
            self.assertEqual((partial, delta), sessions.traces(scenario))
            self.assertEqual(partial[0], partial[-1])
            self.assertEqual(delta[0], {"before": 0, "after": 0})
            self.assertIn({"before": len(scenario["versions"]) - 1, "after": 0}, delta)

    def test_schema_width_alignment_and_version_identity_refuse(self):
        good = sessions.synthetic_scenarios()[1]
        variants = [{**good, "k": True}, {**good, "k": 9}, {**good, "extra": 1},
                    {**good, "feature_names": []}, {**good, "versions": good["versions"] * 2},
                    {**good, "versions": [{"id": "v", "clauses": [[2]]}, {"id": "v2", "clauses": []}]},
                    {**good, "source": {"kind": "projected_full_model"}}]
        for variant in variants:
            with self.assertRaises(ValueError):
                sessions.validate_scenario(variant)

    def test_selector_injection_bad_traces_and_modes_refuse_before_construction(self):
        request = self.request(backend="sat")
        variants = [{**request, "trace": [{"version": 0, "assumptions": [2]}]},
                    {**request, "trace": [{"version": True, "assumptions": []}]},
                    {**request, "trace": [{"version": 0, "assumptions": [True]}]},
                    {**request, "trace": [{"version": 0, "assumptions": [1, -1]}]},
                    {**request, "trace": []}, {**request, "trace": request["trace"] * 3},
                    {**request, "backend": "cudd"}, {**request, "lifecycle": "answer_cache"},
                    {**request, "task": "weighted_count"}]
        with patch.object(sessions, "Engine") as factory:
            for variant in variants:
                with self.assertRaises(ValueError):
                    sessions.execute(variant, TinySAT)
        factory.assert_not_called()

    def test_all_synthetic_non_native_arms_match_both_task_oracles(self):
        for scenario in sessions.synthetic_scenarios():
            for task in sessions.TASKS:
                for backend in ("cm", "cse", "cnf"):
                    rows = []
                    for lifecycle in sessions.LIFECYCLES:
                        with self.subTest(scenario=scenario["id"], task=task, backend=backend, lifecycle=lifecycle):
                            rows.append(self.result(self.request(scenario, backend, lifecycle, task))["rows"])
                    self.assertEqual(rows[0], rows[1])

    def test_sat_gates_select_one_version_and_allow_rollback(self):
        for scenario in sessions.synthetic_scenarios()[:2]:
            for task in sessions.TASKS:
                for lifecycle in sessions.LIFECYCLES:
                    created = []

                    def factory():
                        solver = TinySAT()
                        created.append(solver)
                        return solver

                    request = self.request(scenario, "sat", lifecycle, task)
                    result = self.result(request, factory)
                    self.assertTrue(all(solver.closed for solver in created))
                    for solver in created:
                        for assumptions in solver.calls:
                            selectors = [lit for lit in assumptions if abs(lit) > scenario["k"]]
                            self.assertEqual(len(selectors), len(scenario["versions"]))
                            self.assertEqual(sum(lit > 0 for lit in selectors), 1)
                    self.assertEqual(sum(len(solver.calls) for solver in created), result["counters"]["solve_calls"])

    def test_fresh_and_reused_sat_load_identical_guarded_formulas(self):
        encodings = []
        for lifecycle in sessions.LIFECYCLES:
            def factory():
                solver = TinySAT()
                encodings.append(solver)
                return solver

            self.result(self.request(backend="sat", lifecycle=lifecycle), factory)
        self.assertTrue(all(solver.clauses == encodings[0].clauses for solver in encodings))

    def test_empty_clause_disables_only_its_own_version(self):
        scenario = sessions.synthetic_scenarios()[0]
        result = self.result(self.request(scenario, "sat"))
        for row in result["rows"]:
            self.assertEqual(row["satisfiable"], row["version"] != 1)

    def test_sat_vector_enumeration_charges_every_original_assignment_not_selectors(self):
        request = self.request(backend="sat", task="version_delta")
        result = self.result(request)
        self.assertEqual(result["counters"]["solve_calls"], len(request["trace"]) * 2 * (1 << request["scenario"]["k"]))
        self.assertEqual(result["rows"][1]["delta_hex"], "0x3")

    def test_same_version_and_duplicate_clause_changes_remain_zero_delta(self):
        scenario = sessions.synthetic_scenarios()[3]
        for backend in ("cm", "cse", "cnf"):
            result = self.result(self.request(scenario, backend, task="version_delta"))
            self.assertTrue(all(row["delta_hex"] == "0x0" and row["changed_assignments"] == 0 for row in result["rows"]))

    def test_free_variable_contexts_cross_words_bigint_and_zero_width(self):
        scenario = sessions.synthetic_scenarios()[4]
        request = self.request(scenario)
        request["trace"] = [{"version": 0, "assumptions": literals} for literals in
                            ([], [2, -3], [2, -3, 4], list(range(1, 9)), [-1], [])]
        result = self.result(request)
        self.assertEqual([row["satisfiable"] for row in result["rows"]], [True, True, True, True, False, True])

    def test_reused_programs_recompute_outputs_and_preserve_only_structure(self):
        request = self.request()
        with patch.object(sessions, "flat_context", wraps=sessions.flat_context) as evaluate:
            result = self.result(request)
        self.assertEqual(evaluate.call_count, len(request["trace"]))
        self.assertEqual(result["counters"]["programs_built"], 2)
        self.assertGreater(result["counters"]["program_cache_hits"], 0)
        self.assertFalse(result["output_cache_used"])

    def test_fresh_representations_are_reconstructed_for_each_query(self):
        request = self.request(lifecycle="fresh")
        result = self.result(request)
        self.assertEqual(result["counters"]["programs_built"], len(request["trace"]))
        self.assertEqual(result["counters"]["program_cache_hits"], 0)

    def test_cm_persistent_pool_restored_on_success_and_error(self):
        import cm_ir
        prior = cm_ir._PERSISTENT_IR_CACHE
        original = list(prior.items())
        local = OrderedDict()
        with self.assertRaises(RuntimeError):
            with sessions.isolated_cm_pool(local):
                self.assertIs(cm_ir._PERSISTENT_IR_CACHE, local)
                raise RuntimeError("injected")
        self.result(self.request())
        self.assertIs(cm_ir._PERSISTENT_IR_CACHE, prior)
        self.assertEqual(list(prior.items()), original)

    def test_solver_is_closed_after_add_clause_failure(self):
        class Broken(TinySAT):
            def add_clause(self, clause):
                raise RuntimeError("injected load error")

        solver = Broken()
        with self.assertRaises(RuntimeError):
            sessions.execute(self.request(backend="sat"), lambda: solver)
        self.assertTrue(solver.closed)

    def test_solver_is_closed_after_unknown_result(self):
        class Unknown(TinySAT):
            def solve(self, assumptions):
                return None

        solver = Unknown()
        with self.assertRaisesRegex(ValueError, "unknown"):
            sessions.execute(self.request(backend="sat"), lambda: solver)
        self.assertTrue(solver.closed)

    def test_controller_rejects_every_missing_and_unknown_result_field(self):
        request = self.request()
        result = self.result(request)
        for field in result:
            changed = dict(result)
            del changed[field]
            with self.assertRaises(ValueError):
                sessions.validate_result(changed, request, sessions.ROOT, [123], sessions.oracle(request["scenario"]))
        with self.assertRaises(ValueError):
            sessions.validate_result({**result, "speedup": 100}, request, sessions.ROOT, [123], sessions.oracle(request["scenario"]))

    def test_controller_rejects_wrong_answers_identity_cache_claims_and_forged_work(self):
        request = self.request()
        result = self.result(request)
        changes = [lambda r: r.update(pid=True), lambda r: r.update(pid=124), lambda r: r.update(output_cache_used=True),
                   lambda r: r.update(performance_ranking_permitted=True), lambda r: r.update(lifecycle="fresh"),
                   lambda r: r["rows"][0].update(satisfiable=1), lambda r: r["calls"][0].update(solve_calls=True),
                   lambda r: r["calls"][0].update(total_ns=-1), lambda r: r.update(session_total_ns=0),
                   lambda r: r["counters"].update(engine_instances=2), lambda r: r["counters"].update(programs_built=0),
                   lambda r: r.update(artifacts=[]), lambda r: r["artifacts"][0]["program"].update(k=0)]
        for change in changes:
            changed = copy.deepcopy(result)
            change(changed)
            with self.assertRaises(ValueError):
                sessions.validate_result(changed, request, sessions.ROOT, [123], sessions.oracle(request["scenario"]))

    def test_controller_refuses_omitted_or_wrong_selector_sign(self):
        request = self.request(backend="sat")
        result = self.result(request)
        for selectors in ([], [2, 3], [-2, -3], [2]):
            changed = copy.deepcopy(result)
            changed["calls"][0]["selectors"] = selectors
            with self.assertRaises(ValueError):
                sessions.validate_result(changed, request, sessions.ROOT, [123], sessions.oracle(request["scenario"]))

    def test_controller_refuses_a_count_substituted_for_complete_delta(self):
        request = self.request(task="version_delta")
        result = self.result(request)
        result["rows"][1]["delta_hex"] = "0x2"
        with self.assertRaisesRegex(ValueError, "exact task"):
            sessions.validate_result(result, request, sessions.ROOT, [123], sessions.oracle(request["scenario"]))

    def test_cached_history_selection_retains_candidates_and_original_refusal(self):
        scenarios, ledger = sessions.historical_scenarios()
        admissions = sessions.original_admissions()
        self.assertEqual(len(scenarios), 7)
        self.assertEqual(len(ledger), 120)
        self.assertEqual(sum(row["selected"] for row in ledger), 7)
        self.assertEqual(len({row["source"]["history"] for row in scenarios}), 7)
        self.assertEqual(len(admissions), 21)
        refused = [row for row in admissions if not row["admitted"]]
        self.assertEqual(len(refused), 1)
        self.assertEqual(refused[0]["history"], "Linux")
        self.assertIn("no joint satisfying", refused[0]["reason"])

    def test_changed_historical_input_is_refused_before_selection(self):
        with patch.object(sessions.Path, "open", return_value=io.BytesIO(b"changed")), self.assertRaisesRegex(ValueError, "identity changed"):
            sessions.historical_scenarios()

    def test_known_change_control_is_explicitly_separate_and_keeps_selection_denominator(self):
        scenarios, ledger = sessions.historical_scenarios(known_change_control=True)
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(len(ledger), 120)
        self.assertEqual(scenarios[0]["id"], sessions.KNOWN_CHANGE_CASE)
        self.assertEqual(scenarios[0]["source"]["selection_role"], "known_nonzero_positive_control")
        earlier, later = sessions.oracle(scenarios[0])
        self.assertNotEqual(earlier, later)
        self.assertEqual(sum(row["selected"] for row in ledger), 1)

    def test_historical_canonical_relations_match_their_saved_packed_hashes(self):
        scenarios, _ = sessions.historical_scenarios()
        for scenario in scenarios:
            for name, value in zip(("earlier", "later"), sessions.oracle(scenario)):
                actual = sessions.hashlib.sha256(value.to_bytes(32, "little")).hexdigest()
                self.assertEqual(actual, scenario["source"][name + "_packed_sha256"])

    def test_aggregate_preserves_refused_cells_without_counting_their_outputs(self):
        requests = [self.request(), self.request(backend="sat")]
        scheduled = [{"cell_id": "a"}, {"cell_id": "b"}]
        result = self.result(requests[0])
        state = {"cells": {"a": {"status": "ok", "result": result, "supervision": {"cleanup_verified": True}},
                           "b": {"status": "refused"}}}
        totals = sessions.evidence_totals(requests, scheduled, state)
        self.assertEqual(totals["accepted_partial_answers"], len(requests[0]["trace"]))
        self.assertEqual(totals["native_solve_calls"], 0)
        self.assertEqual(totals["verified_worker_cleanups"], 1)
        self.assertEqual(totals["by_backend_lifecycle"]["sat/reused"]["scheduled_cells"], 1)
        self.assertEqual(totals["by_backend_lifecycle"]["sat/reused"]["accepted_cells"], 0)


if __name__ == "__main__":
    unittest.main()
