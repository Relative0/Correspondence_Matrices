"""Tests for fail-closed neural/backend readiness assessment."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cmbench.recognition.neural_reassessment import (
    ENGINE_METHODS,
    advice_decision,
    build_assessment,
    create_development_artifact,
    load_default_assessment_inputs,
    load_verified_run,
    verify_development_artifact,
)


ROOT = Path(__file__).resolve().parents[1]


class NeuralReassessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.restricted, cls.engine, cls.historical = load_default_assessment_inputs()

    def test_current_exact_economics_stop_training(self):
        result = build_assessment(self.restricted, self.engine, self.historical)
        self.assertFalse(result["decision"]["training_allowed"])
        self.assertFalse(result["decision"]["training_performed"])
        self.assertEqual(result["labels"]["post_r2_word_portfolio"]["counts"], {
            "compiled_truth_projection": 1,
            "restricted_r2_topological_liveness": 17,
        })
        self.assertEqual(result["labels"]["r2_plus_bigint_engine_portfolio"]["counts"], {
            "cse_bigint": 18,
        })
        self.assertEqual(result["economics"]["r2_plus_bigint_engine_portfolio"]["gross_headroom_speedup"], 1.0)
        self.assertLess(result["economics"]["r2_plus_bigint_engine_portfolio"]["optimistic_feature_only_charged_speedup"], 1.0)
        self.assertFalse(advice_decision(result, "full_projection", True)["accepted"])
        self.assertEqual(
            advice_decision(result, None, False)["fallback"],
            advice_decision(result, "full_projection", True)["fallback"],
        )

    def test_stale_or_incomplete_label_portfolios_are_rejected(self):
        restricted = {**self.restricted, "results": json.loads(json.dumps(self.restricted["results"]))}
        restricted["results"]["methods"].remove("restricted_r2_topological_liveness")
        with self.assertRaisesRegex(ValueError, "R0/R1/R2"):
            build_assessment(restricted, self.engine, self.historical)

        engine = {**self.engine, "results": json.loads(json.dumps(self.engine["results"]))}
        engine["results"]["methods"].remove("cse_bigint")
        with self.assertRaisesRegex(ValueError, "bigint"):
            build_assessment(self.restricted, engine, self.historical)
        self.assertIn("cse_bigint", ENGINE_METHODS)

    def test_tampered_exact_label_source_fails_closed(self):
        source = ROOT / "docs/recognition/runs/restricted-evaluator-development-20260902-003"
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            for name in ("results.json", "manifest.json", "independent_verification.json"):
                shutil.copy2(source / name, run / name)
            data = json.loads((run / "results.json").read_text(encoding="utf-8"))
            data["summary"]["checkpoints"]["64"]["per_case_optimized_oracle_total_ns"] += 1
            (run / "results.json").write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                load_verified_run(
                    run,
                    results_schema="crse-restricted-evaluator-development/v1",
                    manifest_schema="crse-restricted-evaluator-manifest/v1",
                    verification_schema="crse-restricted-evaluator-independent-verification/v1",
                )

    def test_artifact_replay_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "reassessment"
            create_development_artifact(run)
            result = verify_development_artifact(run)
            self.assertEqual(result["status"], "verified")
            labels = json.loads((run / "labels.json").read_text(encoding="utf-8"))
            labels["training_label_ready"] = True
            (run / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_development_artifact(run)


if __name__ == "__main__":
    unittest.main()
