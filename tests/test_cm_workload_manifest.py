from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cmbench.tracing.workload_manifest import WorkloadManifestError, validate_workload_manifest
from scripts import cm_validate_workload_manifest


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (
    ROOT
    / "docs"
    / "audits"
    / "2026-08-25-cm-deep-performance"
    / "remaining-work"
    / "three-lane-20260827-011536"
    / "WORKLOAD-MANIFEST-TEMPLATE.json"
)


def load_template() -> dict:
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def declared_manifest() -> dict:
    raw = load_template()
    raw["manifest_status"] = "declared"
    raw["workload"].update(
        {
            "label": "policy-evaluator-production",
            "owner_role": "application-owner",
            "application": "policy-evaluator",
            "repository_or_system": "internal-policy-service",
            "caller_boundary": "evaluate-policy-request",
            "expected_calls_per_expression": 25,
            "requested_artifact": "packed_complete",
            "output_order_contract": "x0 changes fastest; one bit per assignment",
        }
    )
    raw["approvals"]["metrics_capture"] = True
    raw["budgets"].update(
        {"max_output_bytes": 65536, "max_temporary_bytes": 16777216, "max_cache_bytes": 67108864}
    )
    raw["trace"]["planned_duration_or_calls"] = "10000 caller invocations"
    return raw


class WorkloadManifestTests(unittest.TestCase):
    def test_incomplete_template_is_valid_but_not_real_workload(self) -> None:
        result = validate_workload_manifest(load_template())
        self.assertEqual(result["validation_status"], "pass")
        self.assertFalse(result["ready_for_metrics_capture"])
        self.assertIn("manifest_status_is_template", result["blockers"])
        self.assertIn("approval_required:metrics_capture", result["blockers"])

    def test_declared_manifest_is_ready_only_for_approved_capture_modes(self) -> None:
        raw = declared_manifest()
        result = validate_workload_manifest(raw)
        self.assertTrue(result["ready_for_metrics_capture"])
        self.assertFalse(result["ready_for_expression_replay"])
        self.assertFalse(result["ready_for_context_replay"])
        self.assertFalse(result["external_upload_approved"])

        raw["approvals"]["replayable_expressions"] = True
        self.assertTrue(validate_workload_manifest(raw)["ready_for_expression_replay"])

    def test_unknown_field_and_invalid_budget_are_refused(self) -> None:
        unknown = declared_manifest()
        unknown["workload"]["expression_text"] = "must never be accepted here"
        with self.assertRaises(WorkloadManifestError):
            validate_workload_manifest(unknown)

        invalid = declared_manifest()
        invalid["budgets"]["max_temporary_bytes"] = -1
        with self.assertRaises(WorkloadManifestError):
            validate_workload_manifest(invalid)

    def test_initial_capture_sampling_is_fixed_and_bounded(self) -> None:
        invalid = declared_manifest()
        invalid["trace"]["sample_every"] = 1
        with self.assertRaisesRegex(WorkloadManifestError, "must be 16"):
            validate_workload_manifest(invalid)

        missing_bound = declared_manifest()
        missing_bound["trace"]["max_bytes"] = None
        with self.assertRaises(WorkloadManifestError):
            validate_workload_manifest(missing_bound)

    def test_cli_hashes_input_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "manifest.json"
            output_path = root / "validation.json"
            input_path.write_text(json.dumps(declared_manifest()), encoding="utf-8")

            self.assertEqual(
                cm_validate_workload_manifest.main(
                    ["--input", str(input_path), "--output", str(output_path)]
                ),
                0,
            )
            result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                result["input_file"]["sha256"],
                hashlib.sha256(input_path.read_bytes()).hexdigest(),
            )
            with self.assertRaises(FileExistsError):
                cm_validate_workload_manifest.main(
                    ["--input", str(input_path), "--output", str(output_path)]
                )


if __name__ == "__main__":
    unittest.main()
