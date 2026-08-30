from __future__ import annotations

import importlib.util
import json
import unittest

from cm_exprlib import And, Not, Or, Var, Xor, eval_expr_tt
from cmbench.backends.robdd_dd import robdd_interaction_order
from cmbench.recognition.bdd_ordering import (
    ExactBddArtifact, independent_bdd_truth_bits, load_bdd_artifact,
    validate_bdd_artifact,
)
from cmbench.recognition.bdd_order_policy import (
    BddOrderCostTree, ORDER_POLICIES, fit_bdd_order_cost_tree,
)
from cmbench.recognition.features import FEATURE_NAMES


class BddOrderCostTreeTests(unittest.TestCase):
    def test_small_tree_ranks_orders_and_round_trips_as_inert_json(self):
        features, costs = [], []
        for index in range(12):
            row = [0.0 for _ in FEATURE_NAMES]
            row[0] = 4.0 if index < 6 else 10.0
            row[2] = 3.0 if index < 6 else 7.0
            features.append(row)
            costs.append([1.0, 1.4, 1.6, 2.2] if index < 6
                         else [2.0, 1.5, 1.0, 1.8])
        model = fit_bdd_order_cost_tree(
            features, costs, max_depth=1, min_leaf=3, min_gain=0.0)
        self.assertEqual(model.select(features[0]).policy, "fixed")
        self.assertEqual(model.select(features[-1]).policy, "interaction")
        restored = BddOrderCostTree.from_dict(model.to_dict())
        self.assertEqual(restored.to_dict(), model.to_dict())
        self.assertIn(restored.fallback, ORDER_POLICIES)
        outside = list(features[0])
        outside[0] = 16.0
        self.assertEqual(restored.select(outside).reason, "outside_training_range")


@unittest.skipIf(importlib.util.find_spec("dd.autoref") is None,
                 "dd.autoref unavailable")
class ExactBddOrderingTests(unittest.TestCase):
    def setUp(self):
        selector = Var(2)
        self.expr = Or(And(selector, Xor(Var(0), Var(1))),
                       And(Not(selector), And(Var(1), Var(3))))
        self.n_vars = 4
        self.order = robdd_interaction_order(self.expr, self.n_vars)
        self.artifact = ExactBddArtifact.build(
            self.expr, self.n_vars, self.order, backend="autoref")
        self.expected = tuple(int(value) for value in
                              eval_expr_tt(self.expr, self.n_vars).tolist())

    def tearDown(self):
        self.artifact.close()

    def test_truth_count_sat_restriction_and_equivalence_are_exact(self):
        self.assertEqual(self.artifact.truth_bits(), self.expected)
        self.assertEqual(self.artifact.exact_count(), sum(self.expected))
        witness = self.artifact.sat_witness()
        self.assertIsNotNone(witness)
        index = 0
        for variable in range(self.n_vars):
            index = (index << 1) | witness[f"x{variable}"]
        self.assertEqual(self.expected[index], 1)
        remaining, restricted = self.artifact.restrict_truth_bits({"x2": 0})
        self.assertEqual(remaining, ("x0", "x1", "x3"))
        expected_restricted = tuple(
            self.expected[((index & 0b110) << 1) | (index & 0b001)]
            for index in range(8))
        self.assertEqual(restricted, expected_restricted)
        self.assertTrue(self.artifact.equivalent(Not(Not(self.expr))))
        self.assertFalse(self.artifact.equivalent(Not(self.expr)))

    def test_serialization_reload_and_independent_replay_preserve_order(self):
        first = self.artifact.to_bytes()
        second = self.artifact.to_bytes()
        self.assertEqual(first, second)
        decoded = validate_bdd_artifact(first)
        self.assertEqual(decoded["variable_order"], self.order)
        self.assertEqual(independent_bdd_truth_bits(first), self.expected)
        loaded = load_bdd_artifact(first, backend="autoref")
        try:
            self.assertEqual(loaded.variable_order, tuple(self.order))
            self.assertEqual(loaded.truth_bits(), self.expected)
            self.assertEqual(loaded.to_bytes(), first)
        finally:
            loaded.close()

    def test_changed_order_identity_is_rejected_if_not_a_permutation(self):
        data = json.loads(self.artifact.to_bytes())
        data["variable_order"][0] = data["variable_order"][1]
        payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        with self.assertRaisesRegex(ValueError, "variable-universe permutation"):
            validate_bdd_artifact(payload)


if __name__ == "__main__":
    unittest.main()
