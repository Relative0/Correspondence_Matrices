from __future__ import annotations

import importlib.util
import unittest

from cm_exprlib import (
    And, Eqv, Imp, Not, Or, Var, Xor, eval_expr_tt, miter_equiv, tseitin_cnf,
)
from cmbench.recognition.sat_guidance import (
    ExactSatSession, VersionedSatSessionCache, component_phases,
    encode_equivalence_miter, encode_expression_cnf, occurrence_phases,
    sat_guidance_features, validate_assumptions, verify_model,
)
from cmbench.recognition.sat_guidance_policy import (
    ACTIONS, SatGuidanceCostTree, fit_sat_guidance_cost_tree,
)


HAS_PYSAT = (importlib.util.find_spec("pysat") is not None
             and importlib.util.find_spec("pysat.solvers") is not None)


class ExpressionCnfTests(unittest.TestCase):
    def test_one_allocator_keeps_miter_auxiliaries_disjoint(self):
        formula = encode_equivalence_miter(
            And(Var(0), Var(1)), Or(Var(0), Var(1)), 3)
        # x1..x3, left output x4, right output x5, miter x6.
        self.assertEqual(formula.max_var, 6)
        self.assertEqual(formula.output_literal, 6)
        self.assertEqual(formula.clauses[-1], (6,))

    def test_explicit_universe_and_order_are_part_of_identity(self):
        source = encode_expression_cnf(Var(0), 4)
        ordered = encode_expression_cnf(Var(0), 4, clause_order="short_first")
        self.assertEqual(source.max_var, 4)
        self.assertTrue(all((index, -index) in source.clauses
                            for index in range(1, 5)))
        self.assertNotEqual(source.sha256, ordered.sha256)

    def test_bounds_and_assumption_contract_refuse_invalid_inputs(self):
        with self.assertRaisesRegex(ValueError, "1..16"):
            encode_expression_cnf(Var(0), 17)
        with self.assertRaisesRegex(ValueError, "outside"):
            encode_expression_cnf(Var(2), 2)
        for assumptions in ([0], [3], [1, -1], [True]):
            with self.assertRaises(ValueError):
                validate_assumptions(assumptions, 2)

    def test_deterministic_phase_controls_cover_original_universe(self):
        formula = encode_expression_cnf(
            And(Or(Var(0), Not(Var(1))), Xor(Var(0), Var(2))), 4)
        for phases in (occurrence_phases(formula), component_phases(formula)):
            self.assertEqual({abs(literal) for literal in phases}, {1, 2, 3, 4})


@unittest.skipUnless(HAS_PYSAT, "python-sat unavailable")
class ExactSatSessionTests(unittest.TestCase):
    def test_legacy_public_tseitin_and_miter_helpers_are_exact(self):
        from pysat.solvers import Cadical195

        expression = Eqv(Var(0), Var(1))
        expected = eval_expr_tt(expression, 3)
        output, clauses = tseitin_cnf(expression, 3)
        with Cadical195(bootstrap_with=[*clauses, [output]]) as solver:
            for assignment in range(8):
                assumptions = [index + 1 if assignment & (1 << (2 - index))
                               else -(index + 1) for index in range(3)]
                self.assertEqual(solver.solve(assumptions=assumptions),
                                 bool(expected[assignment]))
        max_var, clauses = miter_equiv(
            And(Var(0), Var(1)), Or(Var(0), Var(1)), 3)
        self.assertEqual(max_var, 6)
        with Cadical195(bootstrap_with=clauses) as solver:
            self.assertTrue(solver.solve())
        _, clauses = miter_equiv(expression, Not(Not(expression)), 3)
        with Cadical195(bootstrap_with=clauses) as solver:
            self.assertFalse(solver.solve())

    def test_all_operators_match_independent_truth_evaluation(self):
        expressions = (
            Not(Var(0)), And(Var(0), Var(1)), Or(Var(0), Var(1)),
            Xor(Var(0), Var(1)), Imp(Var(0), Var(1)), Eqv(Var(0), Var(1)),
            Eqv(Imp(Var(0), Var(1)), Or(Not(Var(0)), Var(1))),
        )
        for expression in expressions:
            expected = eval_expr_tt(expression, 3)
            with self.subTest(expression=type(expression).__name__), \
                    ExactSatSession(encode_expression_cnf(expression, 3)) as session:
                for assignment in range(8):
                    assumptions = [index + 1 if assignment & (1 << (2 - index))
                                   else -(index + 1) for index in range(3)]
                    actual = session.solve(assumptions, verify_core=True)
                    self.assertEqual(actual.satisfiable, bool(expected[assignment]))
                    self.assertTrue(actual.solver_authoritative)

    def test_sat_witness_is_checked_against_every_clause(self):
        expression = And(Or(Var(0), Var(1)), Not(Var(2)))
        formula = encode_expression_cnf(expression, 4)
        with ExactSatSession(formula) as session:
            answer = session.solve([1])
            self.assertTrue(answer.satisfiable)
            self.assertEqual(verify_model(formula, session._solver.get_model(), [1]),
                             answer.witness)
            assignment = sum((literal > 0) << (3 - index)
                             for index, literal in enumerate(answer.witness))
            self.assertEqual(eval_expr_tt(expression, 4)[assignment], 1)

    def test_unsat_core_is_subset_and_reconfirmed_by_complete_solver(self):
        formula = encode_expression_cnf(Or(Var(0), Var(1)), 2)
        with ExactSatSession(formula) as session:
            answer = session.solve([-1, -2], verify_core=True)
        self.assertFalse(answer.satisfiable)
        self.assertIsNone(answer.witness)
        self.assertTrue(set(answer.core).issubset({-1, -2}))
        self.assertGreater(answer.verification_ns, 0)

    def test_assumptions_replace_instead_of_accumulating(self):
        formula = encode_expression_cnf(Var(0), 2)
        with ExactSatSession(formula) as session:
            self.assertTrue(session.solve([1]).satisfiable)
            self.assertFalse(session.solve([-1]).satisfiable)
            self.assertTrue(session.solve([]).satisfiable)
            self.assertEqual(session.solve_calls, 3)

    def test_equivalence_miter_has_exact_sat_and_unsat_controls(self):
        left = Xor(Var(0), Var(1))
        with ExactSatSession(encode_equivalence_miter(left, Not(Not(left)), 3)) as session:
            self.assertFalse(session.solve().satisfiable)
        with ExactSatSession(encode_equivalence_miter(left, Not(left), 3)) as session:
            answer = session.solve()
            self.assertTrue(answer.satisfiable)
            self.assertIsNotNone(answer.witness)

    def test_version_change_invalidates_and_exact_digest_reuses(self):
        positive = encode_expression_cnf(Var(0), 2)
        negative = encode_expression_cnf(Not(Var(0)), 2)
        with VersionedSatSessionCache(capacity=2) as cache:
            first, first_status = cache.acquire("working", positive)
            again, again_status = cache.acquire("working", positive)
            changed, changed_status = cache.acquire("working", negative)
            self.assertIs(first, again)
            self.assertIsNot(first, changed)
            self.assertEqual((first_status, again_status, changed_status),
                             ("compiled_miss", "exact_digest_hit", "compiled_miss"))
            self.assertEqual((cache.hits, cache.misses, cache.invalidations), (1, 2, 1))


class SatGuidancePolicyTests(unittest.TestCase):
    def test_bounded_cost_tree_selects_actions_and_round_trips(self):
        features, costs = [], []
        for index in range(16):
            query_count = 1 if index < 8 else 16
            formula = encode_expression_cnf(
                And(Var(0), Var(1)), 3,
                clause_order="source")
            row = list(sat_guidance_features(formula, query_count))
            features.append(row)
            costs.append([1.0, 1.5, 1.6, 1.7] if query_count == 1
                         else [4.0, 1.4, 1.0, 1.2])
        model = fit_sat_guidance_cost_tree(
            features, costs, max_depth=1, min_leaf=4, min_gain=0.0)
        self.assertEqual(model.select(features[0]).action, "fresh_default")
        self.assertEqual(model.select(features[-1]).action, "reused_occurrence")
        restored = SatGuidanceCostTree.from_dict(model.to_dict())
        self.assertEqual(restored.to_dict(), model.to_dict())
        self.assertIn(restored.fallback, ACTIONS)
        self.assertEqual(restored.select(features[0], advice=False).reason, "advice_off")
        outside = list(features[0])
        outside[0] = 99.0
        self.assertEqual(restored.select(outside).reason, "outside_training_range")


if __name__ == "__main__":
    unittest.main()
