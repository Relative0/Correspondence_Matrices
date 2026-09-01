from __future__ import annotations

import importlib.util
import hashlib
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
        cls.retry_controller = load_module("cm_w4_retry_controller_test", BASE / "runpod_p7_w4_timing_controller_v2_retry.py")
        cls.bootstrap_v2 = load_module("cm_w4_bootstrap_v2_test", BASE / "http_native_scout_bootstrap_v2.py")
        cls.bootstrap_v3 = load_module("cm_w4_bootstrap_v3_test", BASE / "http_native_scout_bootstrap_v3_w4_deadlines.py")
        cls.audit = load_module("cm_w4_audit_test", BASE / "verify_p7_w4_timing_v1_outcome.py")
        cls.noise = load_module("cm_w4_noise_test", BASE / "analyze_p7_w4_noise_v1.py")

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

    def test_audit_paired_diagnostics_preserve_direction_and_origin(self):
        rows = []
        for case_id, origin, base in (("synthetic-case", "synthetic", 100), ("natural-case", "natural", 200)):
            for block in range(2):
                rows.extend([
                    {
                        "case_id": case_id,
                        "origin": origin,
                        "block": block,
                        "arm": "base",
                        "task_total_wall_ns": base + block,
                        "fresh_process_controller_wall_ns": (base + block) * 3,
                        "process_tree_peak_rss_bytes": base * 1000,
                    },
                    {
                        "case_id": case_id,
                        "origin": origin,
                        "block": block,
                        "arm": "candidate",
                        "task_total_wall_ns": (base + block) * 2,
                        "fresh_process_controller_wall_ns": (base + block) * 5,
                        "process_tree_peak_rss_bytes": base * 500,
                    },
                ])
        task = self.audit.paired_summary(rows, "base", "candidate", "task_total_wall_ns")
        rss = self.audit.paired_summary(rows, "base", "candidate", "process_tree_peak_rss_bytes")
        self.assertEqual(task["pairs"], 4)
        self.assertAlmostEqual(task["candidate_over_baseline_geometric_mean"], 2.0)
        self.assertEqual(task["candidate_higher_count"], 4)
        self.assertAlmostEqual(rss["candidate_over_baseline_median"], 0.5)
        self.assertEqual(rss["candidate_lower_count"], 4)

    def test_audit_rejects_incomplete_pair_and_invalid_metrics(self):
        row = {
            "case_id": "one",
            "origin": "synthetic",
            "block": 0,
            "arm": "base",
            "task_total_wall_ns": 1,
        }
        with self.assertRaises(ValueError):
            self.audit.paired_summary([row], "base", "candidate", "task_total_wall_ns")
        with self.assertRaises(ValueError):
            self.audit.metric_summary([1, 0])

    def test_audit_policy_summary_reconciles_full_case_block_arm_grid(self):
        rows = []
        for case_index in range(12):
            for block in range(2):
                for arm, multiplier in (("base", 1), ("candidate", 2)):
                    task = (case_index + 1) * (block + 1) * multiplier
                    rows.append({
                        "case_id": f"case-{case_index}",
                        "origin": "synthetic" if case_index < 6 else "natural",
                        "block": block,
                        "arm": arm,
                        "task_total_wall_ns": task,
                        "fresh_process_controller_wall_ns": task * 3,
                        "process_tree_peak_rss_bytes": task * 1000,
                    })
        summary = self.audit.summarize_policy(rows, {
            "blocks": 2,
            "arms": ("base", "candidate"),
            "baseline": "base",
        })
        self.assertEqual(summary["cells"], 48)
        self.assertEqual(summary["arms"]["candidate"]["cells"], 24)
        self.assertEqual(summary["paired_diagnostics"]["candidate"]["task_total_wall_ns"]["pairs"], 24)
        self.assertEqual(
            summary["paired_diagnostics"]["candidate"]["by_origin"]["natural"]["task_total_wall_ns"]["pairs"],
            12,
        )

    def test_retry_bootstrap_exactly_fixes_w4_execution_deadline_allowlist(self):
        payload = {
            "bundle": "",
            "manifest": "",
            "code": "",
            "environment": {
                "CM_BUNDLE_SHA256": "bundle",
                "CM_IMAGE_TAG": "tag",
                "CM_IMAGE_DIGEST": "digest",
                "CM_SETUP_DEADLINE": "1.0",
                "CM_EXECUTION_DEADLINE": "2.0",
            },
        }
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        for bootstrap in (self.bootstrap_v2, self.bootstrap_v3):
            bootstrap.EXPECTED_SIZE = len(raw)
            bootstrap.EXPECTED_HASH = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, "payload environment mismatch"):
            self.bootstrap_v2.validate_payload(raw)
        self.assertEqual(self.bootstrap_v3.validate_payload(raw), payload)

    def test_failed_v1_transport_is_preserved_and_retry_has_fresh_identity(self):
        prior = json.loads((BASE / "p7-w4-timing-v1-001/RUN.json").read_text(encoding="utf-8"))
        progress = [
            json.loads(line)
            for line in (BASE / "p7-w4-timing-v1-001/upload-progress.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(prior["pod_id"], "fixszqtou7pal8")
        self.assertEqual(prior["error"], "proxy HTTP 400")
        self.assertEqual(prior["uploaded_source_files"], 0)
        self.assertTrue(prior["cleanup"]["owned_pod_absent"])
        self.assertEqual(prior["cleanup"]["inventories"], {"v1": [], "v2": []})
        self.assertEqual(progress[-1]["accepted_bytes"], 16 * (256 << 10))
        self.assertEqual(self.retry_controller.OUT.name, "p7-w4-timing-v2-retry-001")
        retry = json.loads((self.retry_controller.OUT / "RUN.json").read_text(encoding="utf-8"))
        self.assertEqual(retry["status"], "complete")
        self.assertEqual(retry["evidence"]["p7_w4_timing"]["terminal_ok_cells"], 984)
        self.assertTrue(retry["cleanup"]["owned_pod_absent"])
        self.assertEqual(retry["cleanup"]["inventories"], {"v1": [], "v2": []})
        self.assertEqual(
            hashlib.sha256(self.retry_controller.REMOTE_CODE_PATH.read_bytes()).hexdigest(),
            "dfb40c8b82c788c55b9662b250ceaa000787697825bc845443ffeadd1dd4c913",
        )
        authorization = self.retry_controller.require_authorization()
        self.assertTrue(authorization["standing_failed_run_rerun_authorization"])
        self.assertEqual(authorization["retry_of_pod_id"], prior["pod_id"])
        audit = json.loads((BASE / "P7-W4-TIMING-FINAL-INDEPENDENT-AUDIT.json").read_text(encoding="utf-8"))
        self.assertTrue(audit["verified"])
        self.assertEqual(audit["combined"]["verified_primary_cells"], 984)

    def test_noise_rule_uses_exact_mad_over_median_ppm(self):
        stable = self.noise.median_mad_ppm([90, 100, 100, 110])
        noisy = self.noise.median_mad_ppm([80, 100, 100, 120])
        self.assertEqual(stable["median"], 100)
        self.assertEqual(stable["mad"], 5)
        self.assertEqual(stable["mad_over_median_ppm"], 50_000)
        self.assertEqual(noisy["mad_over_median_ppm"], 100_000)


if __name__ == "__main__":
    unittest.main()
