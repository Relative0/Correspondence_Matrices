from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cmbench.recognition.profitability_policy import (
    CALIBRATION_SCHEMA,
    EnvironmentCalibration,
    ProfitabilityMetadata,
    ProfitabilityTree,
    feature_vector,
    fit_profitability_tree,
    sha256_document,
)


def calibration(matcher: float = 10.0) -> EnvironmentCalibration:
    return EnvironmentCalibration.from_dict({
        "schema": CALIBRATION_SCHEMA,
        "environment": {"machine": "test"},
        "probe": {"rounds": 3},
        "matcher_node_ns": matcher,
        "kernel_node_execution_ns": 1.0,
        "semantic_mismatches": 0,
    })


class ProfitabilityPolicyTests(unittest.TestCase):
    def test_fit_save_reload_and_conservative_range_fallback(self) -> None:
        environment = calibration()
        rows = [ProfitabilityMetadata(8, reuse, 16 + index, 24 + index, 5, 4, 10)
                for reuse in (1, 1, 1, 128, 128, 128) for index in (0,)]
        features = [feature_vector(row, environment) for row in rows]
        costs = [(100.0, 180.0)] * 3 + [(180.0, 100.0)] * 3
        manifest_hash = sha256_document({"training": "fixture"})
        model = fit_profitability_tree(features, costs,
            calibration_sha256=environment.digest,
            training_manifest_sha256=manifest_hash, min_leaf=2)

        low = model.decide(rows[0], environment)
        high = model.decide(rows[-1], environment)
        outside = model.decide(ProfitabilityMetadata(12, 128, 18, 26, 5, 4, 10), environment)

        self.assertEqual(low.action, "no_rewrite")
        self.assertEqual(high.action, "one_pass")
        self.assertEqual(outside.action, "no_rewrite")
        self.assertEqual(outside.reason, "outside_training_range")

        with tempfile.TemporaryDirectory(prefix="crse-policy-") as directory:
            path = Path(directory) / "policy.json"
            model.save(path)
            loaded = ProfitabilityTree.load(path)
        self.assertEqual(loaded.to_dict(), model.to_dict())
        self.assertEqual(loaded.decide(rows[-1], environment).action, "one_pass")

    def test_calibration_identity_mismatch_abstains(self) -> None:
        first = calibration(10.0)
        row = ProfitabilityMetadata(8, 32, 16, 20, 4, 3, 8)
        model = fit_profitability_tree([feature_vector(row, first)], [(100.0, 80.0)],
            calibration_sha256=first.digest,
            training_manifest_sha256=sha256_document({"training": 1}),
            max_depth=0, min_leaf=1, min_gain=0.0)
        decision = model.decide(row, calibration(11.0))
        self.assertEqual(decision.action, "no_rewrite")
        self.assertEqual(decision.reason, "calibration_identity_mismatch")

    def test_invalid_metadata_is_rejected_before_vector_allocation(self) -> None:
        with self.assertRaisesRegex(ValueError, "metadata"):
            feature_vector(ProfitabilityMetadata(0, 1, 1, 0, 1, 1, 1), calibration())


if __name__ == "__main__":
    unittest.main()
