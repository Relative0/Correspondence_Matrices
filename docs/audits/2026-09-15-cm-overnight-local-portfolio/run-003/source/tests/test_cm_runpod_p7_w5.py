from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BASE = (
    ROOT
    / "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/continuation-20260829-125214"
)
PACKAGE = ROOT / "docs/research/verification/comparative-p7-w5-development-v1-2026-09-01"


def load_module(name: str, path: Path):
    if str(BASE) not in sys.path:
        sys.path.insert(0, str(BASE))
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


def literals(path: Path):
    values = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                values[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return values


class P7W5RunpodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preflight = load_module("cm_w5_preflight_test", BASE / "http_p7_w5_development_preflight_v1.py")
        cls.controller = load_module("cm_w5_controller_test", BASE / "runpod_p7_w5_controller_v1.py")
        cls.campaign = json.loads((PACKAGE / "campaign.json").read_text(encoding="utf-8"))
        cls.programs = json.loads((BASE / "P7-W5-REMOTE-PROGRAMS-V1.json").read_text(encoding="utf-8"))
        cls.analysis = load_module("cm_w5_analysis_test", BASE / "analyze_p7_w5_v1.py")
        cls.battery_preflight = load_module(
            "cm_w5_battery_preflight_test", BASE / "http_p7_w5_development_preflight_v2_battery.py"
        )
        cls.battery_controller = load_module(
            "cm_w5_battery_controller_test", BASE / "runpod_p7_w5_controller_v2_battery.py"
        )

    def test_exact_source_payload_is_reused_without_secret_paths(self):
        upload = self.preflight.verify_upload()
        manifest = json.loads(
            (BASE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(upload["verified"])
        self.assertEqual(upload["files"], 96)
        self.assertFalse(manifest["secrets_included"])
        self.assertFalse(any(Path(row["target"]).name.lower().startswith(".env") for row in manifest["files"]))

    def test_four_remote_programs_bind_exact_primary_and_anchor_freezes(self):
        definitions = {row["partition_id"]: row for row in self.campaign["definitions"]}
        self.assertEqual(len(self.programs["programs"]), 4)
        for row in self.programs["programs"]:
            values = literals(BASE / row["path"])
            primary = definitions[row["shard_id"]]
            anchor = definitions[row["policy_id"] + "-anchor"]
            self.assertEqual(values["PRIMARY_CASE_IDS"], primary["case_ids"])
            self.assertEqual(values["PRIMARY_BLOCKS"], primary["blocks"])
            self.assertEqual(values["PRIMARY_CELLS"], primary["planned_cells"])
            self.assertEqual(values["PRIMARY_FREEZE_SHA256"], primary["freeze_sha256"])
            self.assertEqual(values["ANCHOR_CASE_IDS"], anchor["case_ids"])
            self.assertEqual(values["ANCHOR_CELLS"], anchor["planned_cells"])
            source = (BASE / row["path"]).read_text(encoding="utf-8")
            self.assertIn('"--profile", "performance"', source)
            self.assertIn('("regression", "development")', source)
            self.assertNotIn('"--roles", "confirmation"', source)
            self.assertNotIn("confirmation-logikbench-", source)

    def test_controller_configuration_is_shard_specific_and_bounded(self):
        for row in self.programs["programs"]:
            self.controller.configure(row["shard_id"])
            self.assertEqual(self.controller.SHARD_ID, row["shard_id"])
            self.assertEqual(self.controller.SHARD, row)
            self.assertEqual(self.controller.OUT.name, "p7-w5-" + row["shard_id"] + "-v1-001")
            self.assertEqual(self.controller.HORIZON, 1200)
            self.assertEqual(self.controller.CLEANUP_AT, 1080)
            self.assertEqual(self.controller.CHUNK_BYTES, 256 << 10)
            self.assertEqual((self.controller.PHASE_CAP, self.controller.CAMPAIGN_CAP), (0.10, 5.00))

    def test_payload_binds_setup_and_execution_deadlines_without_credentials(self):
        self.controller.configure("p7-relation-a")
        manifest = json.loads(self.controller.MANIFEST_PATH.read_text(encoding="utf-8"))
        raw = self.controller.prepare_payload(b"payload", manifest, 1000.0)
        payload = json.loads(raw)
        self.assertEqual(
            set(payload["environment"]),
            {
                "CM_BUNDLE_SHA256", "CM_IMAGE_TAG", "CM_IMAGE_DIGEST",
                "CM_SETUP_DEADLINE", "CM_EXECUTION_DEADLINE",
            },
        )
        self.assertEqual(payload["environment"]["CM_EXECUTION_DEADLINE"], "2035.0")
        self.assertNotIn("RUNPOD_API_KEY", raw.decode("utf-8"))

    def test_authorization_is_hash_bound_for_each_shard(self):
        for row in self.programs["programs"]:
            self.controller.configure(row["shard_id"])
            authorization = self.controller.require_authorization()
            self.assertTrue(authorization["authorized"])
            self.assertEqual(authorization["primary_cells"], 7524)
            self.assertEqual(
                authorization["remote_program_sha256_by_shard"][row["shard_id"]],
                row["sha256"],
            )

    def test_battery_amendment_preserves_shards_and_requires_known_charge_floor(self):
        # This test validates the frozen authorization contract, not the current
        # machine's battery. Live host power is checked immediately before launch.
        self.assertEqual(self.battery_preflight.MINIMUM_BATTERY_PERCENT, 50)

        class FakeKernel:
            @staticmethod
            def GetSystemPowerStatus(pointer):
                pointer._obj.ACLineStatus = 0
                pointer._obj.BatteryLifePercent = 75
                return 1

        with mock.patch.object(self.battery_preflight.os, "name", "nt"), mock.patch(
            "ctypes.WinDLL", create=True, return_value=FakeKernel()
        ):
            status = self.battery_preflight.host_power_status()
        self.assertTrue(status["battery_status_known"])
        self.assertEqual(status["minimum_battery_percent_when_not_on_ac"], 50)
        self.assertTrue(status["battery_gate_passed"])
        for row in self.programs["programs"]:
            self.battery_controller.configure(row["shard_id"])
            self.assertEqual(self.battery_controller.SHARD, row)
            self.assertEqual(
                self.battery_controller.OUT.name,
                "p7-w5-" + row["shard_id"] + "-v2-battery-001",
            )
            authorization = self.battery_controller.require_authorization()
            self.assertTrue(authorization["battery_launch_authorized"])
            self.assertFalse(authorization["ac_power_required"])
            self.assertEqual(authorization["minimum_battery_percent_when_not_on_ac"], 50)

    def test_resource_gate_requires_exact_zero_volume_secure_cpu(self):
        self.controller.configure("p7-ir-a")
        state = {"name": "cm-p7-w5-p7-ir-a-v1-123456abcdef"}
        offer = {"id": "cpu3c"}
        pod = {
            "id": "abcdefgh1234", "name": state["name"], "computeType": "CPU",
            "cloud": "SECURE", "cpuFlavorId": "cpu3c", "vcpuCount": 2,
            "memoryInGb": 4, "costPerHr": 0.06, "image": self.controller.base.IMAGE,
            "containerDiskInGb": 12, "volumeInGb": 0, "volumeMountPath": "/workspace",
            "ports": list(self.controller.EXPECTED_PORTS), "gpu": {"count": 0},
            "networkVolume": None,
        }
        original_load = self.controller.load

        def fake_load(path):
            if path == self.controller.IDENTITY:
                return {"pod_id": pod["id"]}
            return original_load(path)

        with mock.patch.object(self.controller, "load", side_effect=fake_load):
            accepted = self.controller.validate_pod(pod, state, offer, 1.0)
            self.assertEqual(accepted["pod_volume_gb"], 0)
            with self.assertRaises(RuntimeError):
                self.controller.validate_pod({**pod, "volumeInGb": 10}, state, offer, 1.0)

    def test_local_package_validation_is_network_free_and_ready(self):
        result = json.loads((BASE / "P7-W5-PACKAGE-V1-LOCAL-VALIDATION.json").read_text(encoding="utf-8"))
        self.assertTrue(result["ready"])
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["network_requests"], 0)
        self.assertFalse(result["authentication_used"])
        self.assertEqual(result["remote_program_count"], 4)
        self.assertEqual(result["primary_cells"], 7524)
        self.assertEqual(result["total_cells_including_diagnostics"], 7852)

    def test_paired_analysis_uses_independent_case_clusters(self):
        rows = []
        for case_id, origin, role, base in (
            ("case-a", "synthetic", "regression", 100.0),
            ("case-b", "natural", "development", 200.0),
        ):
            for block in range(4):
                for arm, multiplier in (("base", 1.0), ("candidate", 0.5)):
                    value = base * (block + 1) * multiplier
                    rows.append(
                        {
                            "case_id": case_id,
                            "origin": origin,
                            "role": role,
                            "block": block,
                            "arm": arm,
                            "task_total_wall_ns": value,
                            "fresh_process_controller_wall_ns": value * 3,
                            "process_tree_peak_rss_bytes": value * 1000,
                        }
                    )
        result = self.analysis.paired_summary(rows, "base", "candidate", "task_total_wall_ns")
        self.assertEqual(result["paired_case_blocks"], 8)
        self.assertEqual(result["independent_cases"], 2)
        self.assertAlmostEqual(result["candidate_over_baseline"]["geometric_mean"], 0.5)
        self.assertAlmostEqual(
            result["cluster_bootstrap"]["candidate_over_baseline_geometric_mean"], 0.5
        )
        self.assertEqual(result["candidate_lower_count"], 8)
        self.assertEqual(set(result["by_origin"]), {"natural", "synthetic"})

    def test_paired_analysis_refuses_incomplete_or_nonpositive_metrics(self):
        row = {
            "case_id": "case-a", "origin": "synthetic", "role": "development",
            "block": 0, "arm": "base", "task_total_wall_ns": 1,
            "fresh_process_controller_wall_ns": 1, "process_tree_peak_rss_bytes": 1,
        }
        with self.assertRaises(ValueError):
            self.analysis.paired_summary([row], "base", "candidate", "task_total_wall_ns")
        with self.assertRaises(ValueError):
            self.analysis.absolute_summary([1.0, 0.0])


if __name__ == "__main__":
    unittest.main()
