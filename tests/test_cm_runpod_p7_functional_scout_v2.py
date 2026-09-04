from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock
import zipfile

from cmbench.comparative import linux_supervisor, p7_runner
from scripts.cm_manifest_dependency_audit import audit_manifest
import scripts.cm_comparative_p7_runner as p7_cli


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / (
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/continuation-20260829-125214"
)
MANIFEST = BASE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json"
BUNDLE = BASE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V2-20260830.zip"
V6_CONTROLLER = BASE / "runpod_p7_functional_scout_controller_v6_exact96_retry.py"
V6_PREFLIGHT = BASE / "http_p7_functional_scout_preflight_v6_exact96_retry.py"
W3_CONTROLLER = BASE / "runpod_p7_w3_correctness_controller_v1.py"
W3_REMOTE = BASE / "runpod_p7_w3_correctness_remote_v1.py"
W3_SHARD_CONTROLLER = BASE / "runpod_p7_w3_shard_controller_v2.py"
W3_SPLIT_CONTROLLER = BASE / "runpod_p7_w3_split_controller_v4.py"
W3_SPLIT_V5_CONTROLLER = BASE / "runpod_p7_w3_split_controller_v5.py"
W3_SPLIT_VALIDATION = BASE / "P7-W3-SPLIT-V4-OFFLINE-VALIDATION.json"
W3_TAIL_V6_CONTROLLER = BASE / "runpod_p7_w3_tail_controller_v6.py"
W3_TAIL_V6_VALIDATION = BASE / "P7-W3-TAIL-V6-OFFLINE-VALIDATION.json"
W3_FINAL_V7_CONTROLLER = BASE / "runpod_p7_w3_final_controller_v7.py"
W3_FINAL_AUDIT = BASE / "P7-W3-FINAL-INDEPENDENT-AUDIT.json"
W3_FINAL_POSTFLIGHT = BASE / "P7-W3-FINAL-POSTFLIGHT.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RunpodP7FunctionalScoutV2Tests(unittest.TestCase):
    def test_exact_package_is_closed_and_zip_matches_manifest(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual((manifest["file_count"], manifest["bytes"]), (96, 19484163))
        self.assertEqual(digest(MANIFEST),
                         "9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74")
        self.assertEqual((BUNDLE.stat().st_size, digest(BUNDLE)), (
            3197013, "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668",
        ))
        expected = {row["target"]: row for row in manifest["files"]}
        with zipfile.ZipFile(BUNDLE) as archive:
            self.assertEqual(set(archive.namelist()), set(expected))
            self.assertEqual(len(archive.namelist()), len(expected))
            for name, row in expected.items():
                data = archive.read(name)
                self.assertEqual(len(data), row["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])
        self.assertTrue(audit_manifest(ROOT, MANIFEST)["complete"])

    def test_controller_is_blocked_without_exact_authorization(self):
        controller_path = BASE / "runpod_p7_functional_scout_controller_v2.py"
        self.assertEqual(digest(controller_path),
                         "7e92a91542463a25959e5796d7b427a91c93a70696069438ded2d7bd3c110aeb")
        sys.path.insert(0, str(BASE))
        try:
            spec = importlib.util.spec_from_file_location("p7_scout_v2_test", controller_path)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            authorization_path = module.AUTHORIZATION_PATH
            module.AUTHORIZATION_PATH = BASE / "intentionally-absent-p7-v2-authorization.json"
            with self.assertRaisesRegex(RuntimeError, "authorization record is absent"):
                module.require_authorization()
            module.AUTHORIZATION_PATH = authorization_path
            if authorization_path.exists():
                self.assertTrue(module.require_authorization()["authorized"])
            self.assertEqual(module.CAMPAIGN_CAP, 0.20)
            self.assertEqual(module.OUT.name, "p7-functional-scout-v2-001")
        finally:
            sys.path.remove(str(BASE))

    def test_remote_contract_uses_v6_gate_locked_binary_install_and_42_tests(self):
        remote = (BASE / "runpod_p7_functional_scout_remote_v2.py").read_text(encoding="utf-8")
        self.assertIn("comparative-p7-offline-gate-v6-2026-08-30", remote)
        self.assertIn("tests/test_cm_comparative_p7_package.py", remote)
        self.assertIn("--only-binary=:all:", remote)
        self.assertIn("runpod-requirements.lock", remote)

    def test_v1_failure_is_consumed_and_clean(self):
        run = json.loads((BASE / "p7-functional-scout-v1-001/RUN.json").read_text(encoding="utf-8"))
        self.assertEqual((run["status"], run["pod_id"]), ("failed", "1xh6csc4oxy067"))
        self.assertEqual(run["cleanup"]["inventories"], {"v1": [], "v2": []})
        self.assertTrue(run["cleanup"]["owned_pod_absent"])
        self.assertEqual(run["evidence"]["validation"]["junit_testcases"],
                         {"tests": 3, "failures": 0, "errors": 3, "skipped": 0})

    def test_v2_failure_was_local_before_upload_and_is_clean(self):
        run = json.loads((BASE / "p7-functional-scout-v2-001/RUN.json").read_text(encoding="utf-8"))
        self.assertEqual((run["status"], run["error_type"]), ("failed", "AttributeError"))
        self.assertEqual((run["pod_id"], run["uploaded_source_files"]),
                         ("r044pqp2vgp7cy", 0))
        self.assertTrue(run["cleanup"]["owned_pod_absent"])
        self.assertEqual(run["cleanup"]["inventories"], {"v1": [], "v2": []})

    def test_v6_reexports_reserve_and_accepts_recorded_v2_pod_shape(self):
        self.assertIn("PRIOR_HTTP_RESERVE =", V6_PREFLIGHT.read_text(encoding="utf-8"))
        sys.path.insert(0, str(BASE))
        try:
            spec = importlib.util.spec_from_file_location("p7_scout_v6_test", V6_CONTROLLER)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            self.assertTrue(module.require_authorization()["same_exact_external_payload_authorization"])
            resource = json.loads(
                (BASE / "p7-functional-scout-v2-001/POD-RESOURCE-CHECK.json").read_text(encoding="utf-8")
            )["pod"]
            resource.update({"machine": {}, "gpu": {}, "networkVolume": None})
            state = {"name": resource["name"]}
            with mock.patch.object(module, "load", return_value={"pod_id": resource["id"]}):
                actual = module.validate_pod(resource, state, {"id": "cpu3c"}, 0.02)
            self.assertEqual(actual["pod_id"], "r044pqp2vgp7cy")
            self.assertEqual(actual["image"], module.base.IMAGE)
            self.assertEqual(actual["cloud_evidence"], ["SECURE"])
        finally:
            sys.path.remove(str(BASE))

    def test_w3_plan_is_all_58_cases_and_522_functional_cells(self):
        freeze = json.loads((
            ROOT / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"
        ).read_text(encoding="utf-8"))
        limits = linux_supervisor.Limits(
            timeout_seconds=30.0,
            rss_stop_bytes=1 << 30,
            stdout_bytes=p7_runner.MAX_WORKER_BYTES,
            stderr_bytes=256 << 10,
            input_bytes=p7_runner.MAX_REQUEST_BYTES,
            processes=4,
        )
        common = {
            "roles": ["regression", "development"],
            "blocks": 1,
            # Plan construction only requires a bound source-manifest identity.
            # Executable source verification is covered separately and depends on
            # intentionally untracked external corpora that are absent in clean CI.
            "worker_source_manifest_sha256": p7_runner.record_sha256({
                "fixture": "clean-checkout-plan-test",
                "freeze_sha256": freeze["freeze_sha256"],
            }),
            "resource_limits": p7_runner.limits_record(limits),
            "profile": "functional",
        }
        ir = p7_runner.build_plan(freeze, policy_id="p7-ir", **common)
        relation = p7_runner.build_plan(freeze, policy_id="p7-relation", **common)
        self.assertEqual((len(ir["case_ids"]), len(ir["cells"])), (58, 232))
        self.assertEqual((len(relation["case_ids"]), len(relation["cells"])), (58, 290))
        self.assertEqual({row["role"] for row in ir["cells"]}, {"regression", "development"})
        self.assertEqual({row["role"] for row in relation["cells"]}, {"regression", "development"})
        self.assertTrue(all(row["lifecycle"] == "fresh_process" for row in ir["cells"] + relation["cells"]))
        self.assertTrue(all(row["performance_measurement"] is False for row in (ir, relation)))

    def test_w3_remote_and_controller_keep_correctness_only_contract(self):
        remote = W3_REMOTE.read_text(encoding="utf-8")
        controller = W3_CONTROLLER.read_text(encoding="utf-8")
        self.assertIn('"--roles", "regression", "development", "--blocks", "1"', remote)
        self.assertNotIn('"--case-limit"', remote)
        self.assertIn('_p7_terminal_check(evidence_root / "p7-ir", 232', controller)
        self.assertIn('evidence_root / "p7-relation", 290', controller)
        self.assertIn('len(set(ir_pids + relation_pids)) != 522', controller)
        self.assertIn('"performance_ranking": False', controller)
        sys.path.insert(0, str(BASE))
        try:
            spec = importlib.util.spec_from_file_location("p7_w3_controller_test", W3_CONTROLLER)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            authorization = module.require_authorization()
            self.assertEqual((authorization["p7_cases_per_policy"], authorization["fresh_cell_processes"]),
                             (58, 522))
            self.assertFalse(authorization["performance_ranking"])
        finally:
            sys.path.remove(str(BASE))

    def test_w3_four_shards_are_exact_and_sequential(self):
        expected = {
            "ir-regression": ("p7-ir", "regression", 24, 96),
            "ir-development": ("p7-ir", "development", 34, 136),
            "relation-regression": ("p7-relation", "regression", 24, 120),
            "relation-development": ("p7-relation", "development", 34, 170),
        }
        sys.path.insert(0, str(BASE))
        try:
            for index, (shard_id, values) in enumerate(expected.items()):
                expected_output = BASE / f"p7-w3-shard-{shard_id}-v2-001"
                output_existed = expected_output.exists()
                output_mtime = expected_output.stat().st_mtime_ns if output_existed else None
                remote = (BASE / (
                    "runpod_p7_w3_shard_remote_v2_" + shard_id.replace("-", "_") + ".py"
                )).read_text(encoding="utf-8")
                self.assertIn(f'SHARD_ID = "{shard_id}"', remote)
                self.assertNotIn('os.environ.pop("CM_W3_SHARD_ID")', remote)
                self.assertIn('"--roles", SHARD["role"], "--blocks", "1"', remote)
                self.assertIn('for name in (SHARD["policy"],):', remote)
                self.assertIn('780,', remote)
                sys.modules.pop("http_p7_w3_shard_preflight_v2", None)
                with mock.patch.dict(os.environ, {"CM_W3_SHARD_ID": shard_id}):
                    spec = importlib.util.spec_from_file_location(
                        f"p7_w3_shard_controller_test_{index}", W3_SHARD_CONTROLLER
                    )
                    module = importlib.util.module_from_spec(spec)
                    assert spec.loader is not None
                    spec.loader.exec_module(module)
                    authorization = module.require_authorization()
                self.assertEqual(
                    (authorization["shard_policy"], authorization["shard_role"],
                     authorization["shard_cases"], authorization["shard_cells"]),
                    values,
                )
                self.assertTrue(authorization["sequential_shards_only"])
                self.assertFalse(authorization["performance_ranking"])
                self.assertEqual(module.OUT, expected_output)
                self.assertEqual(module.OUT.exists(), output_existed)
                if output_existed:
                    self.assertEqual(module.OUT.stat().st_mtime_ns, output_mtime)
        finally:
            sys.modules.pop("http_p7_w3_shard_preflight_v2", None)
            sys.path.remove(str(BASE))

    def test_w3_development_partitions_are_disjoint_complete_and_authorized(self):
        report = json.loads(W3_SPLIT_VALIDATION.read_text(encoding="utf-8"))
        self.assertTrue(report["ready"])
        self.assertEqual(
            report["source_bundle_sha256"],
            "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668",
        )
        for policy in ("p7-ir", "p7-relation"):
            coverage = report["coverage"][policy]
            self.assertEqual((coverage["parent_cases"], coverage["partition_cases"]), (34, [17, 17]))
            self.assertTrue(coverage["disjoint"])
            self.assertTrue(coverage["union_matches_parent"])

        expected = {
            "ir-development-a": ("p7-ir", 0, 68),
            "ir-development-b": ("p7-ir", 17, 68),
            "relation-development-a": ("p7-relation", 0, 85),
            "relation-development-b": ("p7-relation", 17, 85),
        }
        sys.path.insert(0, str(BASE))
        try:
            for index, (partition_id, (policy, offset, cells)) in enumerate(expected.items()):
                sys.modules.pop("http_p7_w3_split_preflight_v4", None)
                with mock.patch.dict(os.environ, {"CM_W3_SPLIT_ID": partition_id}):
                    spec = importlib.util.spec_from_file_location(
                        f"p7_w3_split_controller_test_{index}", W3_SPLIT_CONTROLLER
                    )
                    module = importlib.util.module_from_spec(spec)
                    assert spec.loader is not None
                    spec.loader.exec_module(module)
                    authorization = module.require_authorization()
                self.assertEqual(authorization["shard_policy"], policy)
                self.assertEqual(authorization["case_offset"], offset)
                self.assertEqual((authorization["case_limit"], authorization["shard_cells"]), (17, cells))
                self.assertTrue(authorization["partition_validation_ready"])
                self.assertFalse(authorization["performance_ranking"])
        finally:
            sys.modules.pop("http_p7_w3_split_preflight_v4", None)
            sys.path.remove(str(BASE))

    def test_first_w3_development_partition_preflight_reconciles_prior_runs(self):
        sys.path.insert(0, str(BASE))
        try:
            sys.modules.pop("http_p7_w3_split_preflight_v4", None)
            with mock.patch.dict(os.environ, {"CM_W3_SPLIT_ID": "ir-development-a"}):
                import http_p7_w3_split_preflight_v4 as preflight

                fake_client = mock.Mock()
                fake_client.close.return_value = None
                with (
                    mock.patch.object(preflight, "session", return_value=fake_client),
                    mock.patch.object(preflight, "inventory", return_value=[]),
                    mock.patch.object(preflight.previous, "check", return_value={
                        "ready": True,
                        "prior_cost_bound_usd": 0.005,
                        "selected_offer": {"rate_usd_per_hour": 0.06},
                    }),
                ):
                    result = preflight.check()
            self.assertTrue(result["ready"])
            self.assertEqual(result["shard_id"], "ir-development-a")
            self.assertEqual(result["shard_cells"], 68)
            self.assertEqual(result["current_inventories"], {"v1": [], "v2": []})
        finally:
            sys.modules.pop("http_p7_w3_split_preflight_v4", None)
            sys.path.remove(str(BASE))

    def test_w3_v5_continuation_reconciles_unrelated_inventory_refusal(self):
        expected = {
            "ir-development-b": ("p7-ir", 17, 68),
            "relation-development-a": ("p7-relation", 0, 85),
            "relation-development-b": ("p7-relation", 17, 85),
        }
        sys.path.insert(0, str(BASE))
        try:
            for index, (partition_id, (policy, offset, cells)) in enumerate(expected.items()):
                sys.modules.pop("http_p7_w3_split_preflight_v5", None)
                with mock.patch.dict(os.environ, {"CM_W3_SPLIT_ID": partition_id}):
                    spec = importlib.util.spec_from_file_location(
                        f"p7_w3_split_v5_controller_test_{index}", W3_SPLIT_V5_CONTROLLER
                    )
                    module = importlib.util.module_from_spec(spec)
                    assert spec.loader is not None
                    spec.loader.exec_module(module)
                    authorization = module.require_authorization()
                self.assertEqual(authorization["shard_policy"], policy)
                self.assertEqual(authorization["case_offset"], offset)
                self.assertEqual(authorization["shard_cells"], cells)
                self.assertIn(
                    "p7-w3-split-ir-development-b-v4-001",
                    authorization["prior_no_create_attempts"],
                )
        finally:
            sys.modules.pop("http_p7_w3_split_preflight_v5", None)
            sys.path.remove(str(BASE))

    def test_w3_v6_tail_is_complete_and_authorized(self):
        report = json.loads(W3_TAIL_V6_VALIDATION.read_text(encoding="utf-8"))
        self.assertTrue(report["ready"])
        self.assertTrue(report["coverage"]["p7-ir"]["union_matches_parent"])
        self.assertTrue(report["coverage"]["p7-relation"]["union_matches_parent"])
        expected = {
            "ir-development-b-light": ("p7-ir", 17, 15, 60),
            "ir-development-sqrt": ("p7-ir", 32, 1, 4),
            "ir-development-square": ("p7-ir", 33, 1, 4),
            "relation-development-a": ("p7-relation", 0, 17, 85),
            "relation-development-b-light": ("p7-relation", 17, 15, 75),
            "relation-development-sqrt": ("p7-relation", 32, 1, 5),
            "relation-development-square": ("p7-relation", 33, 1, 5),
        }
        sys.path.insert(0, str(BASE))
        try:
            for index, (partition_id, values) in enumerate(expected.items()):
                sys.modules.pop("http_p7_w3_tail_preflight_v6", None)
                with mock.patch.dict(os.environ, {"CM_W3_SPLIT_ID": partition_id}):
                    spec = importlib.util.spec_from_file_location(
                        f"p7_w3_tail_v6_controller_test_{index}", W3_TAIL_V6_CONTROLLER
                    )
                    module = importlib.util.module_from_spec(spec)
                    assert spec.loader is not None
                    spec.loader.exec_module(module)
                    authorization = module.require_authorization()
                self.assertEqual(
                    (
                        authorization["shard_policy"], authorization["case_offset"],
                        authorization["case_limit"], authorization["shard_cells"],
                    ),
                    values,
                )
                self.assertTrue(authorization["partition_validation_ready"])
                self.assertFalse(authorization["performance_ranking"])
        finally:
            sys.modules.pop("http_p7_w3_tail_preflight_v6", None)
            sys.path.remove(str(BASE))

    def test_w3_v7_completion_and_postflight_are_exact(self):
        expected = {
            "ir-development-square": ("p7-ir", 33, 1, 4),
            "relation-development-a": ("p7-relation", 0, 17, 85),
            "relation-development-b-light": ("p7-relation", 17, 15, 75),
            "relation-development-square": ("p7-relation", 33, 1, 5),
        }
        sys.path.insert(0, str(BASE))
        try:
            for index, (partition_id, values) in enumerate(expected.items()):
                sys.modules.pop("http_p7_w3_final_preflight_v7", None)
                with mock.patch.dict(os.environ, {"CM_W3_SPLIT_ID": partition_id}):
                    spec = importlib.util.spec_from_file_location(
                        f"p7_w3_final_v7_controller_test_{index}", W3_FINAL_V7_CONTROLLER
                    )
                    module = importlib.util.module_from_spec(spec)
                    assert spec.loader is not None
                    spec.loader.exec_module(module)
                    authorization = module.require_authorization()
                self.assertEqual(
                    (
                        authorization["shard_policy"], authorization["case_offset"],
                        authorization["case_limit"], authorization["shard_cells"],
                    ),
                    values,
                )
                self.assertIn("policy-independent scalar oracle timed out",
                              authorization["authorization_basis"])
                self.assertFalse(authorization["performance_ranking"])
        finally:
            sys.modules.pop("http_p7_w3_final_preflight_v7", None)
            sys.path.remove(str(BASE))

        audit = json.loads(W3_FINAL_AUDIT.read_text(encoding="utf-8"))
        self.assertTrue(audit["verified"])
        self.assertEqual(audit["combined"]["verified_cells"], 513)
        self.assertEqual(audit["combined"]["excluded_cells"], 9)
        self.assertEqual(len(audit["successful_shards"]), 8)
        self.assertTrue(audit["all_created_attempts_cleaned"])
        self.assertFalse(audit["combined"]["performance_ranking_permitted"])

        postflight = json.loads(W3_FINAL_POSTFLIGHT.read_text(encoding="utf-8"))
        self.assertEqual(postflight["inventories"], {"v1": [], "v2": []})
        self.assertTrue(postflight["all_created_pods_absent"])
        self.assertEqual(len(postflight["created_pod_ids"]), 13)
        self.assertTrue(all(
            endpoint["http_status"] == 404
            for versions in postflight["pod_details"].values()
            for endpoint in versions.values()
        ))


if __name__ == "__main__":
    unittest.main()
