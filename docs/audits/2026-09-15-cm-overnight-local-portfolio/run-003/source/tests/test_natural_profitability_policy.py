from __future__ import annotations

import unittest

from bitset_backend import build_bitset_env, eval_expr_bitset
from cm_exprlib import And, Not, Or, Var

from cmbench.recognition.features import structural_digest
from cmbench.recognition.natural_profitability_policy_experiment import (
    ARMS, SPLITS, NaturalPolicyCase, measure, summarize_split,
)
from cmbench.recognition.profitability_policy import (
    CALIBRATION_SCHEMA, EnvironmentCalibration, ProfitabilityMetadata,
    feature_vector, fit_profitability_tree,
)
from cmbench.recognition.rule_pack import compile_rule_pack, factored_or_expr, prove_rule_pack_v2


class NaturalProfitabilityPolicyTests(unittest.TestCase):
    def _calibration(self) -> EnvironmentCalibration:
        return EnvironmentCalibration.from_dict({"schema": CALIBRATION_SCHEMA,
            "environment": {"fixture": True}, "probe": {"fixture": True},
            "matcher_node_ns": 10.0, "kernel_node_execution_ns": 1.0,
            "semantic_mismatches": 0})

    def test_declared_circuit_splits_are_disjoint(self) -> None:
        circuits = {split: set(value[1]) for split, value in SPLITS.items()}
        self.assertFalse(circuits["training"] & circuits["validation"])
        self.assertFalse(circuits["training"] & circuits["evaluation"])
        self.assertFalse(circuits["validation"] & circuits["evaluation"])

    def test_measured_frozen_decision_is_exact_and_charges_decision(self) -> None:
        a, b, c = Var(0), Var(1), Var(2)
        expression = And(factored_or_expr(a, b, c), Or(Var(8), Not(Var(8))))
        metadata = ProfitabilityMetadata(9, 8, 7, 9, 3, 2, 6)
        oracle = eval_expr_bitset(expression, build_bitset_env(tuple(f"x{i}" for i in range(9))))
        case = NaturalPolicyCase("fixture", "evaluation", "fixture", "size", "fixture.blif",
            "0" * 64, "y", expression, oracle, metadata,
            structural_digest(expression, alpha_rename=True), structural_digest(expression))
        calibration = self._calibration()
        vector = feature_vector(metadata, calibration)
        policy = fit_profitability_tree([vector], [[2.0, 1.0]],
            calibration_sha256=calibration.digest, training_manifest_sha256="1" * 64,
            max_depth=0, min_leaf=1, min_gain=0.05)
        row = measure(case, 8, "frozen_gate", 0,
            compile_rule_pack(prove_rule_pack_v2()), policy, calibration)

        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["mismatches"], 0)
        self.assertEqual(row["selected_action"], "one_pass")
        self.assertGreater(row["decision_ns"], 0)
        self.assertEqual(row["total_ns"], sum(row[key] for key in (
            "decision_ns", "rewrite_ns", "cse_build_ns", "cse_kernel_ns")))

    def test_summary_compares_policy_to_both_controls(self) -> None:
        rows = []
        for case_id in ("a", "b"):
            for arm, total, action in (
                    ("no_rewrite", 100, "no_rewrite"),
                    ("one_pass", 80, "one_pass"),
                    ("frozen_gate", 82, "one_pass")):
                rows.append({"case_id": case_id, "expected_reuses": 32, "arm": arm,
                    "total_ns": total, "selected_action": action,
                    "decision_reason": "learned_profitable" if arm == "frozen_gate" else "fixed_arm"})
        summary = summarize_split(rows)
        self.assertEqual(summary["workloads"], 2)
        self.assertAlmostEqual(summary["frozen_gate_speedup_over_no_rewrite"], 100 / 82)
        self.assertEqual(summary["gate_apply_count"], 2)
        self.assertEqual(set(ARMS), set(summary["median_cell_totals_ns"]))


if __name__ == "__main__":
    unittest.main()
