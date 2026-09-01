from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BASE = (
    ROOT
    / "docs/audits/2026-08-25-cm-deep-performance/remaining-work"
    / "maximal-safe-20260827-192909/continuation-20260829-125214"
)
W4 = ROOT / "docs/research/verification/comparative-p7-w4-timing-scout-v1-2026-08-31"


def load_module(name: str, path: Path):
    if str(BASE) not in sys.path:
        sys.path.insert(0, str(BASE))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class P7W4TimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preflight = load_module("cm_w4_preflight_test", BASE / "http_p7_w4_timing_preflight_v1.py")
        cls.controller = load_module("cm_w4_controller_test", BASE / "runpod_p7_w4_timing_controller_v1.py")

    def test_static_freeze_covers_declared_strata_and_exact_cycle(self):
        freeze = json.loads((W4 / "freeze.json").read_text(encoding="utf-8"))
        selection = json.loads((W4 / "selection.json").read_text(encoding="utf-8"))
        verification = json.loads((W4 / "verification.json").read_text(encoding="utf-8"))
        self.assertEqual(freeze["freeze_sha256"], "d81ab57d4fbfe8a49a28314cc645d9ddf24e7d7182abfe1d2f36c016430c7b31")
        self.assertEqual(len(freeze["cases"]), 12)
        self.assertEqual(selection["planned_primary_cells"], 984)
        self.assertFalse(selection["selection_rule"]["comparative_timing_inspected"])
        self.assertEqual(verification["synthetic_k"], [8, 12, 16])
        self.assertEqual(verification["synthetic_shapes"], ["shared", "tree"])
        self.assertEqual(
            verification["synthetic_families"],
            ["andor_dom", "impeqv_dom", "mixed", "xor_dom"],
        )
        self.assertEqual((verification["synthetic_cases"], verification["natural_cases"]), (6, 6))
        self.assertTrue(verification["complete_counterbalance_cycles"])

    def test_exact_96_file_payload_and_bundle_derived_freeze_are_verified(self):
        upload = self.preflight.verify_upload()
        package = json.loads(
            (BASE / "P7-W4-TIMING-PACKAGE-V2-LOCAL-VALIDATION.json").read_text(encoding="utf-8")
        )
        self.assertTrue(upload["verified"])
        self.assertEqual(upload["files"], 96)
        self.assertEqual(upload["manifest_sha256"], "9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74")
        self.assertEqual(upload["bundle_sha256"], "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668")
        self.assertTrue(package["exact_bundle_reproduces_freeze"])
        self.assertEqual(package["planned_primary_cells"], 984)
        self.assertEqual(package["plans"]["p7-ir"]["cells"], 384)
        self.assertEqual(package["plans"]["p7-relation"]["cells"], 600)

    def test_remote_runs_only_development_performance_cycles(self):
        source = (BASE / "runpod_p7_w4_timing_remote_v1.py").read_text(encoding="utf-8")
        self.assertIn('(("p7-ir", 8), ("p7-relation", 10))', source)
        self.assertIn('"--roles", "development"', source)
        self.assertIn('"--profile", "performance"', source)
        self.assertNotIn('"--roles", "confirmation"', source)
        self.assertNotIn("confirmation-logikbench-", source)
        self.assertIn('"CM_EXECUTION_DEADLINE"', source)

    def test_transport_payload_binds_both_deadlines_without_credentials(self):
        manifest = json.loads(
            (BASE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json").read_text(encoding="utf-8")
        )
        raw = self.controller.prepare_payload(b"payload", manifest, 1000.0)
        payload = json.loads(raw)
        environment = payload["environment"]
        self.assertEqual(environment["CM_SETUP_DEADLINE"], "1360.0")
        self.assertEqual(environment["CM_EXECUTION_DEADLINE"], "2035.0")
        self.assertEqual(set(environment), {"CM_BUNDLE_SHA256", "CM_IMAGE_TAG", "CM_IMAGE_DIGEST", "CM_SETUP_DEADLINE", "CM_EXECUTION_DEADLINE"})
        self.assertNotIn("RUNPOD_API_KEY", raw.decode("utf-8"))

    def test_actual_resource_gate_requires_exact_zero_volume_identity(self):
        state = {"name": "cm-p7-w4-timing-v1-123456abcdef"}
        offer = {"id": "cpu3c"}
        pod = {
            "id": "abcdefgh1234",
            "name": state["name"],
            "computeType": "CPU",
            "cloud": "SECURE",
            "cpuFlavorId": "cpu3c",
            "vcpuCount": 2,
            "memoryInGb": 4,
            "costPerHr": 0.06,
            "image": self.controller.base.IMAGE,
            "containerDiskInGb": 12,
            "volumeInGb": 0,
            "volumeMountPath": "/workspace",
            "ports": list(self.controller.EXPECTED_PORTS),
            "gpu": {"count": 0},
            "networkVolume": None,
        }
        original_load = self.controller.load

        def fake_load(path):
            if path == self.controller.IDENTITY:
                return {"pod_id": pod["id"]}
            return original_load(path)

        with mock.patch.object(self.controller, "load", side_effect=fake_load):
            accepted = self.controller.validate_pod(pod, state, offer, 0.5)
            self.assertEqual(accepted["pod_volume_gb"], 0)
            with self.assertRaises(RuntimeError):
                self.controller.validate_pod({**pod, "volumeInGb": 10}, state, offer, 0.5)

    def test_exact_authorization_is_hash_bound_and_scope_tamper_refuses(self):
        authorization = self.controller.require_authorization()
        self.assertTrue(authorization["authorized"])
        self.assertEqual(authorization["planned_primary_cells"], 984)
        original_load = self.controller.load

        def tampered_load(path):
            value = original_load(path)
            if path == self.controller.AUTHORIZATION_PATH:
                value = dict(value)
                value["relation_cells"] = 599
            return value

        with mock.patch.object(self.controller, "load", side_effect=tampered_load):
            with self.assertRaises(RuntimeError):
                self.controller.require_authorization()


if __name__ == "__main__":
    unittest.main()
