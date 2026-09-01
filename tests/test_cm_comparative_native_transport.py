import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / (
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/continuation-20260829-125214"
)


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HERE))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(HERE))
    return module


controller = load_module("cm_native_scout_controller_fixture", "runpod_native_scout_controller_v1.py")
bootstrap = load_module("cm_native_scout_bootstrap_fixture", "http_native_scout_bootstrap_v1.py")
preflight = controller.preflight
retry_controller = load_module("cm_native_scout_retry_controller_fixture", "runpod_native_scout_controller_v2.py")
retry_preflight = retry_controller.preflight
chunk_controller = load_module("cm_native_scout_chunk_controller_fixture", "runpod_native_scout_controller_v3.py")
chunk_bootstrap = load_module("cm_native_scout_chunk_bootstrap_fixture", "http_native_scout_bootstrap_v2.py")
chunk_preflight = chunk_controller.preflight
closure_controller = load_module("cm_native_scout_closure_controller_fixture", "runpod_native_scout_controller_v4.py")
closure_preflight = closure_controller.preflight
p5_controller = load_module("cm_native_scout_p5_controller_fixture", "runpod_native_scout_controller_v5.py")
p5_preflight = p5_controller.preflight
procfs_controller = load_module("cm_native_scout_procfs_controller_fixture", "runpod_native_scout_controller_v6.py")
procfs_preflight = procfs_controller.preflight
host_controller = load_module("cm_native_scout_host_controller_fixture", "runpod_native_scout_controller_v7.py")
host_preflight = host_controller.preflight

audit_spec = importlib.util.spec_from_file_location(
    "cm_manifest_dependency_audit_fixture", ROOT / "scripts/cm_manifest_dependency_audit.py"
)
manifest_audit = importlib.util.module_from_spec(audit_spec)
audit_spec.loader.exec_module(manifest_audit)


class ComparativeNativeTransportTests(unittest.TestCase):
    def test_historical_v6_manifest_is_immutable_and_live_source_drift_is_explicit(self):
        manifest = procfs_controller.load(procfs_controller.MANIFEST_PATH)
        self.assertEqual(manifest["package_id"], "CM-COMPARATIVE-NATIVE-SCOUT-PROCFS-V6-20260829")
        self.assertEqual(len(manifest["files"]), 37)
        self.assertEqual(manifest["bytes"], 5504396)
        self.assertEqual(len({row["target"] for row in manifest["files"]}), 37)
        self.assertEqual(
            hashlib.sha256(procfs_controller.MANIFEST_PATH.read_bytes()).hexdigest(),
            "4883f93e3147bd2aa6c986d99685d20e18974fc6d2da1c3645b269579fe38c2c",
        )
        mismatches = []
        for row in manifest["files"]:
            data = (ROOT / row["source"]).read_bytes()
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                mismatches.append(row["source"])
            self.assertNotIn(".env", row["source"].lower())
        self.assertEqual(
            mismatches,
            [
                "cm_exprlib.py",
                "cmbench/comparative/contracts.py",
                "cmbench/comparative/linux_supervisor.py",
                "scripts/cm_comparative_native_scout.py",
                "scripts/cm_native_contracts.py",
                "tests/test_cm_comparative_linux_supervisor.py",
                "tests/test_cm_comparative_native_scout.py",
                "tests/test_cm_native_contracts.py",
            ],
        )
        self.assertEqual(
            next(row["sha256"] for row in manifest["files"] if row["target"].endswith("/d4")),
            procfs_controller.base.D4_SHA256 if hasattr(procfs_controller.base, "D4_SHA256") else
            "29cb30f351ed92b02343e5e7a98b082e949d9838245f37c0bcdecf68a57ffd39",
        )

    def test_historical_v6_bundle_rebuild_refuses_live_source_drift(self):
        manifest = procfs_controller.load(procfs_controller.MANIFEST_PATH)
        with self.assertRaisesRegex(RuntimeError, "approved upload hash mismatch: cm_exprlib.py"):
            procfs_controller.base.make_bundle(manifest)

    def test_bounded_transport_payload_fits_new_bootstrap(self):
        manifest = procfs_controller.load(procfs_controller.MANIFEST_PATH)
        bundle = b"frozen-v6-bundle-fixture\n" * 40_000
        raw = procfs_controller.prepare_payload(bundle, manifest, time.time())
        self.assertLessEqual(len(raw), bootstrap.UPLOAD_CAP)
        self.assertGreater(len(raw), 1 << 20)
        value = json.loads(raw)
        with patch.object(bootstrap, "EXPECTED_SIZE", len(raw)), \
                patch.object(bootstrap, "EXPECTED_HASH", hashlib.sha256(raw).hexdigest()):
            checked = bootstrap.validate_payload(raw)
        self.assertEqual(hashlib.sha256(base64.b64decode(checked["bundle"])).hexdigest(),
                         hashlib.sha256(bundle).hexdigest())
        self.assertEqual(len(base64.b64decode(checked["code"])), len(procfs_controller.base.REMOTE_CODE.encode()))

    def test_bootstrap_uses_bounded_files_not_multi_megabyte_child_environment(self):
        payload = {"environment": {key: "x" for key in (
            "CM_BUNDLE_SHA256", "CM_IMAGE_TAG", "CM_IMAGE_DIGEST", "CM_SETUP_DEADLINE"
        )}}
        with patch.dict(bootstrap.os.environ, {"RUNPOD_API_KEY": "must-not-propagate", "RUNPOD_POD_ID": "pod"}, clear=True):
            environment = bootstrap.child_environment(payload, "/tmp/bundle.zip", "/tmp/manifest.json")
        self.assertEqual(environment["CM_BUNDLE_PATH"], "/tmp/bundle.zip")
        self.assertEqual(environment["CM_UPLOAD_MANIFEST_PATH"], "/tmp/manifest.json")
        self.assertFalse(any(key.startswith("CM_BUNDLE_") and key[10:].isdigit() for key in environment))
        self.assertNotIn("RUNPOD_API_KEY", environment)

    def test_authorization_is_exactly_required_and_current_record_matches(self):
        with tempfile.TemporaryDirectory(prefix="cm-auth-absent-") as directory, \
                patch.object(controller, "AUTHORIZATION_PATH", Path(directory) / "absent.json"), \
                self.assertRaisesRegex(RuntimeError, "authorization record is absent"):
            controller.require_authorization()

        current = controller.require_authorization()
        self.assertTrue(current["authorized"])
        authorization = {
            "schema": "cm-runpod-native-scout-authorization/v1",
            "authorized": True,
            "one_create": True,
            "no_replacement": True,
            "source_files": 30,
            "focused_tests": 60,
            "p5_smoke_cells": 144,
            "performance_ranking": False,
            "source_builds_allowed": ["astutils==0.0.6", "ply==3.10"],
            "container_disk_gb": 12,
            "pod_volume_gb": 0,
            "network_volume": False,
            "lifetime_seconds": 1200,
            "phase_cap_usd": 0.10,
            "campaign_cap_usd": 0.20,
            "proposal_sha256": hashlib.sha256(controller.PROPOSAL_PATH.read_bytes()).hexdigest(),
            "upload_manifest_sha256": hashlib.sha256(controller.MANIFEST_PATH.read_bytes()).hexdigest(),
        }
        with tempfile.TemporaryDirectory(prefix="cm-auth-invalid-") as directory:
            path = Path(directory) / "authorization.json"
            path.write_text(json.dumps(authorization), encoding="utf-8")
            with patch.object(controller, "AUTHORIZATION_PATH", path):
                self.assertTrue(controller.require_authorization()["authorized"])
                authorization["source_files"] = 31
                path.write_text(json.dumps(authorization), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "scope mismatch"):
                    controller.require_authorization()

    def test_create_body_has_one_zero_volume_secure_cpu(self):
        raw = b"payload"
        body = controller.create_payload("cm-native-scout-123456abcdef", {"id": "cpu3c"}, "x" * 32, raw, 100.0)
        self.assertEqual(body["computeType"], "CPU")
        self.assertEqual(body["cloudType"], "SECURE")
        self.assertEqual(body["vcpuCount"], 2)
        self.assertEqual(body["containerDiskInGb"], 12)
        self.assertEqual(body["volumeInGb"], 0)
        self.assertNotIn("networkVolume", body)
        self.assertEqual(body["ports"], ["8080/http", "8081/http"])

    def test_resource_validation_binds_identity_budget_and_zero_storage(self):
        pod = {
            "id": "abcdefgh1234", "name": "cm-native-scout-123456abcdef", "computeType": "CPU",
            "cloudType": "SECURE", "cpuFlavorId": "cpu3c", "vcpuCount": 2, "memoryInGb": 4,
            "costPerHr": 0.06, "image": controller.base.IMAGE, "containerDiskInGb": 12,
            "volumeInGb": 0, "volumeMountPath": "/workspace", "ports": ["8080/http", "8081/http"],
            "machine": {"secureCloud": True}, "gpu": {"count": 0},
        }
        state = {"name": pod["name"]}
        with tempfile.TemporaryDirectory(prefix="cm-identity-") as directory:
            identity = Path(directory) / "identity.json"
            identity.write_text(json.dumps({"pod_id": pod["id"]}), encoding="utf-8")
            with patch.object(controller, "IDENTITY", identity):
                result = controller.validate_pod(pod, state, {"id": "cpu3c"}, 0.0)
                self.assertLessEqual(result["projected_20_min_cost_usd"], 0.10)
                changed = dict(pod, volumeInGb=1)
                with self.assertRaises(RuntimeError):
                    controller.validate_pod(changed, state, {"id": "cpu3c"}, 0.0)

    def test_new_campaign_budget_and_prior_cleanup_are_explicit(self):
        budget = preflight.budget(0.06)
        self.assertTrue(budget["ready"])
        self.assertEqual(budget["comparative_campaign_prior_cost_usd"], 0.0)
        self.assertLessEqual(budget["projected_phase_cost_usd"], 0.10)
        with self.assertRaises(ValueError):
            preflight.budget(True)
        prior = preflight.prior_attempts()
        self.assertTrue(prior["cleanup_verified"])
        self.assertEqual(len(prior["pod_ids"]), 4)

    def test_remote_program_is_frozen_readable_code_without_performance_claims(self):
        source = controller.REMOTE_CODE_PATH.read_text(encoding="utf-8")
        compile(source, str(controller.REMOTE_CODE_PATH), "exec")
        self.assertIn('performance_ranking_permitted', source)
        self.assertIn('"native-scout"', source)
        self.assertNotIn("RUNPOD_API_KEY", source)

    def test_proposal_records_current_frozen_transport_hashes(self):
        proposal = controller.PROPOSAL_PATH.read_text(encoding="utf-8")
        for path in (
            controller.MANIFEST_PATH,
            HERE / "RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json",
            Path(controller.__file__),
            Path(preflight.__file__),
            controller.BOOTSTRAP_PATH,
            controller.REMOTE_CODE_PATH,
        ):
            with self.subTest(path=path.name):
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), proposal)

    def test_retry_preflight_and_controller_share_prior_cost_contract(self):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": {"myself": {
                    "clientBalance": 10,
                    "currentSpendPerHr": 0,
                    "spendLimit": 10,
                }}}

        class Client:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def post(self, *_args, **_kwargs):
                return Response()

        def offer(flavor):
            return {
                "id": flavor,
                "eligible": True,
                "availability": "HIGH",
                "rate_usd_per_hour": 0.06,
            }

        billing = {
            "metadata": {},
            "historical_account_rows": [],
            "historical_total_usd": 0.0,
            "new_comparative_campaign_observed_cost_usd": 0.0,
            "billing_may_lag": True,
        }
        with patch.object(retry_preflight, "get_offer", side_effect=offer), \
                patch.object(retry_preflight, "session", return_value=Client()), \
                patch.object(retry_preflight, "inventory", return_value=[]), \
                patch.object(retry_preflight, "billing_check", return_value=billing):
            ready = retry_preflight.check()
        self.assertTrue(ready["ready"])
        self.assertGreater(ready["prior_cost_bound_usd"], 0)
        self.assertEqual(
            ready["prior_cost_bound_usd"],
            ready["budget"]["comparative_campaign_prior_cost_usd"],
        )
        self.assertEqual(len(ready["prior_attempts"]["pod_ids"]), 5)

        pod = {
            "id": "abcdefgh1234", "name": "cm-native-scout-123456abcdef", "computeType": "CPU",
            "cloudType": "SECURE", "cpuFlavorId": "cpu3c", "vcpuCount": 2, "memoryInGb": 4,
            "costPerHr": 0.06, "image": retry_controller.base.IMAGE, "containerDiskInGb": 12,
            "volumeInGb": 0, "volumeMountPath": "/workspace", "ports": ["8080/http", "8081/http"],
            "machine": {"secureCloud": True}, "gpu": {"count": 0},
        }
        with tempfile.TemporaryDirectory(prefix="cm-retry-identity-") as directory:
            identity = Path(directory) / "identity.json"
            identity.write_text(json.dumps({"pod_id": pod["id"]}), encoding="utf-8")
            with patch.object(retry_controller, "IDENTITY", identity):
                validated = retry_controller.validate_pod(
                    pod,
                    {"name": pod["name"]},
                    {"id": "cpu3c"},
                    ready["prior_cost_bound_usd"],
                )
        self.assertEqual(validated["prior_cost_bound_usd"], ready["prior_cost_bound_usd"])

    def test_retry_refuses_without_separate_authorization_and_accepts_current_record(self):
        with tempfile.TemporaryDirectory(prefix="cm-retry-auth-absent-") as directory, \
                patch.object(retry_controller, "AUTHORIZATION_PATH", Path(directory) / "absent.json"), \
                self.assertRaisesRegex(RuntimeError, "authorization record is absent"):
            retry_controller.require_authorization()
        self.assertTrue(retry_controller.require_authorization()["authorized"])

    def test_retry_authorization_schema_and_frozen_hashes(self):
        authorization = {
            "schema": "cm-runpod-native-scout-retry-authorization/v1",
            "authorized": True,
            "one_create": True,
            "no_replacement": True,
            "source_files": 30,
            "focused_tests": 60,
            "p5_smoke_cells": 144,
            "performance_ranking": False,
            "source_builds_allowed": ["astutils==0.0.6", "ply==3.10"],
            "container_disk_gb": 12,
            "pod_volume_gb": 0,
            "network_volume": False,
            "lifetime_seconds": 1200,
            "phase_cap_usd": 0.10,
            "campaign_cap_usd": 0.20,
            "prior_failed_pod_id": "84442bdg4m47x8",
            "proposal_sha256": hashlib.sha256(retry_controller.PROPOSAL_PATH.read_bytes()).hexdigest(),
            "upload_manifest_sha256": hashlib.sha256(retry_controller.MANIFEST_PATH.read_bytes()).hexdigest(),
        }
        with tempfile.TemporaryDirectory(prefix="cm-retry-auth-") as directory:
            path = Path(directory) / "authorization.json"
            path.write_text(json.dumps(authorization), encoding="utf-8")
            with patch.object(retry_controller, "AUTHORIZATION_PATH", path):
                self.assertTrue(retry_controller.require_authorization()["authorized"])
                authorization["prior_failed_pod_id"] = "different"
                path.write_text(json.dumps(authorization), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "scope mismatch"):
                    retry_controller.require_authorization()

        proposal = retry_controller.PROPOSAL_PATH.read_text(encoding="utf-8")
        for path in (
            retry_controller.MANIFEST_PATH,
            HERE / "RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json",
            Path(retry_controller.__file__),
            Path(retry_preflight.__file__),
            retry_controller.BOOTSTRAP_PATH,
            retry_controller.REMOTE_CODE_PATH,
            retry_preflight.SCOUT_FINAL,
        ):
            with self.subTest(path=path.name):
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), proposal)

    def test_chunk_bootstrap_accepts_ordered_idempotent_chunks(self):
        raw = json.dumps({
            "bundle": base64.b64encode(b"bundle").decode(),
            "manifest": base64.b64encode(b"manifest").decode(),
            "code": base64.b64encode(b"code").decode(),
            "environment": {
                "CM_BUNDLE_SHA256": "x",
                "CM_IMAGE_TAG": "x",
                "CM_IMAGE_DIGEST": "x",
                "CM_SETUP_DEADLINE": "x",
            },
        }, separators=(",", ":")).encode()
        chunk_bootstrap.EXPECTED_SIZE = len(raw)
        chunk_bootstrap.EXPECTED_HASH = hashlib.sha256(raw).hexdigest()
        chunk_bootstrap.PAYLOAD = None
        chunk_bootstrap.UPLOAD.clear()
        chunk_bootstrap.STATE.clear()
        chunk_bootstrap.STATE.update({
            "uploaded": False, "validating": False, "accepted_bytes": 0,
            "started": False, "done": False, "stage": "awaiting-upload", "error": None,
        })
        first = raw[:17]
        with self.assertRaises(ValueError):
            chunk_bootstrap.accept_chunk(1, first, hashlib.sha256(first).hexdigest())
        status = chunk_bootstrap.accept_chunk(0, first, hashlib.sha256(first).hexdigest())
        self.assertEqual(status["accepted_bytes"], len(first))
        duplicate = chunk_bootstrap.accept_chunk(0, first, hashlib.sha256(first).hexdigest())
        self.assertEqual(duplicate["accepted_bytes"], len(first))
        with self.assertRaises(ValueError):
            changed = b"z" * len(first)
            chunk_bootstrap.accept_chunk(0, changed, hashlib.sha256(changed).hexdigest())
        rest = raw[len(first):]
        final = chunk_bootstrap.accept_chunk(len(first), rest, hashlib.sha256(rest).hexdigest())
        self.assertTrue(final["uploaded"])
        self.assertEqual(final["payload_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertIsInstance(chunk_bootstrap.PAYLOAD, dict)

    def test_chunk_controller_reconciles_timeout_after_server_acceptance(self):
        padding = b"x" * chunk_controller.CHUNK_BYTES
        raw = json.dumps({
            "bundle": base64.b64encode(padding).decode(),
            "manifest": base64.b64encode(b"manifest").decode(),
            "code": base64.b64encode(b"code").decode(),
            "environment": {
                "CM_BUNDLE_SHA256": "x",
                "CM_IMAGE_TAG": "x",
                "CM_IMAGE_DIGEST": "x",
                "CM_SETUP_DEADLINE": "x",
            },
        }, separators=(",", ":")).encode()
        chunk_bootstrap.EXPECTED_SIZE = len(raw)
        chunk_bootstrap.EXPECTED_HASH = hashlib.sha256(raw).hexdigest()
        chunk_bootstrap.PAYLOAD = None
        chunk_bootstrap.UPLOAD.clear()
        chunk_bootstrap.STATE.clear()
        chunk_bootstrap.STATE.update({
            "uploaded": False, "validating": False, "accepted_bytes": 0,
            "started": False, "done": False, "stage": "awaiting-upload", "error": None,
        })
        posts = []

        def request(_proxy, method, url, *, data=None, headers=None, **_kwargs):
            if method == "GET" and url.endswith("/upload"):
                return json.dumps(chunk_bootstrap.upload_status()).encode()
            self.assertEqual(method, "POST")
            posts.append(int(headers["X-CM-Offset"]))
            value = chunk_bootstrap.accept_chunk(
                int(headers["X-CM-Offset"]), data, headers["X-CM-Chunk-SHA256"]
            )
            if len(posts) == 1:
                raise chunk_controller.requests.ReadTimeout("simulated after acceptance")
            return json.dumps(value).encode()

        with patch.object(chunk_controller, "proxy_request", side_effect=request):
            result = chunk_controller.upload_payload(object(), "https://bootstrap", raw, time.time() + 60)
        self.assertTrue(result["uploaded"])
        self.assertEqual(result["accepted_bytes"], len(raw))
        self.assertEqual(posts, [0, chunk_controller.CHUNK_BYTES])

    def test_bounded_payload_uses_chunk_protocol_and_create_body(self):
        manifest = procfs_controller.load(procfs_controller.MANIFEST_PATH)
        bundle = b"frozen-v6-bundle-fixture\n" * 40_000
        raw = procfs_controller.prepare_payload(bundle, manifest, time.time())
        chunk_bootstrap.EXPECTED_SIZE = len(raw)
        chunk_bootstrap.EXPECTED_HASH = hashlib.sha256(raw).hexdigest()
        chunk_bootstrap.PAYLOAD = None
        chunk_bootstrap.UPLOAD.clear()
        chunk_bootstrap.STATE.clear()
        chunk_bootstrap.STATE.update({
            "uploaded": False, "validating": False, "accepted_bytes": 0,
            "started": False, "done": False, "stage": "awaiting-upload", "error": None,
        })
        posts = []

        def request(_proxy, method, url, *, data=None, headers=None, **_kwargs):
            if method == "GET" and url.endswith("/upload"):
                return json.dumps(chunk_bootstrap.upload_status()).encode()
            posts.append((int(headers["X-CM-Offset"]), len(data)))
            value = chunk_bootstrap.accept_chunk(
                int(headers["X-CM-Offset"]), data, headers["X-CM-Chunk-SHA256"]
            )
            return json.dumps(value).encode()

        with patch.object(procfs_controller, "proxy_request", side_effect=request):
            result = procfs_controller.upload_payload(object(), "https://bootstrap", raw, time.time() + 60)
        self.assertTrue(result["uploaded"])
        self.assertEqual(len(posts), (len(raw) + procfs_controller.CHUNK_BYTES - 1) // procfs_controller.CHUNK_BYTES)
        self.assertTrue(all(length <= procfs_controller.CHUNK_BYTES for _, length in posts))
        self.assertEqual(posts[0][0], 0)
        self.assertEqual(posts[-1][0] + posts[-1][1], len(raw))
        body = procfs_controller.create_payload(
            "cm-native-scout-123456abcdef", {"id": "cpu3c"}, "x" * 32, raw, time.time()
        )
        self.assertEqual(body["containerDiskInGb"], 12)
        self.assertEqual(body["volumeInGb"], 0)
        self.assertLess(len(body["dockerStartCmd"][0].encode()), 16 << 10)

    def test_chunked_retry_carries_both_attempt_costs_and_is_not_authorized(self):
        prior = chunk_preflight.prior_attempts()
        self.assertTrue(prior["failed_scout_attempt_reconciled"])
        self.assertTrue(prior["failed_scout_retry_reconciled"])
        self.assertEqual(len(prior["pod_ids"]), 6)
        self.assertGreater(prior["new_comparative_campaign_cost_before_scout_usd"], 0.001)
        with tempfile.TemporaryDirectory(prefix="cm-chunk-auth-absent-") as directory, \
                patch.object(chunk_controller, "AUTHORIZATION_PATH", Path(directory) / "absent.json"), \
                self.assertRaisesRegex(RuntimeError, "authorization record is absent"):
            chunk_controller.require_authorization()
        self.assertTrue(chunk_controller.require_authorization()["authorized"])

    def test_chunked_retry_authorization_schema_and_frozen_hashes(self):
        authorization = {
            "schema": "cm-runpod-native-scout-chunked-retry-authorization/v1",
            "authorized": True,
            "one_create": True,
            "no_replacement": True,
            "source_files": 30,
            "focused_tests": 60,
            "p5_smoke_cells": 144,
            "performance_ranking": False,
            "source_builds_allowed": ["astutils==0.0.6", "ply==3.10"],
            "container_disk_gb": 12,
            "pod_volume_gb": 0,
            "network_volume": False,
            "lifetime_seconds": 1200,
            "phase_cap_usd": 0.10,
            "campaign_cap_usd": 0.20,
            "prior_failed_pod_ids": ["84442bdg4m47x8", "76exgpsv0y39bl"],
            "chunk_bytes": 256 << 10,
            "proposal_sha256": hashlib.sha256(chunk_controller.PROPOSAL_PATH.read_bytes()).hexdigest(),
            "upload_manifest_sha256": hashlib.sha256(chunk_controller.MANIFEST_PATH.read_bytes()).hexdigest(),
        }
        with tempfile.TemporaryDirectory(prefix="cm-chunk-auth-") as directory:
            path = Path(directory) / "authorization.json"
            path.write_text(json.dumps(authorization), encoding="utf-8")
            with patch.object(chunk_controller, "AUTHORIZATION_PATH", path):
                self.assertTrue(chunk_controller.require_authorization()["authorized"])
                authorization["chunk_bytes"] += 1
                path.write_text(json.dumps(authorization), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "scope mismatch"):
                    chunk_controller.require_authorization()

        proposal = chunk_controller.PROPOSAL_PATH.read_text(encoding="utf-8")
        for path in (
            chunk_controller.MANIFEST_PATH,
            HERE / "RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json",
            Path(chunk_controller.__file__),
            Path(chunk_preflight.__file__),
            chunk_controller.BOOTSTRAP_PATH,
            chunk_controller.REMOTE_CODE_PATH,
            chunk_preflight.RETRY_FINAL,
        ):
            with self.subTest(path=path.name):
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), proposal)

    def test_dependency_closure_audit_explains_failure_and_accepts_v6(self):
        v2 = manifest_audit.audit_manifest(
            ROOT, HERE / "RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V2-20260829.json"
        )
        self.assertFalse(v2["complete"])
        missing = {item for rows in v2["missing"].values() for item in rows}
        self.assertEqual(missing, {
            "cmbench/backends/__init__.py",
            "cmbench/backends/bitset_engine.py",
            "scripts/cm_benchmark_provenance.py",
            "scripts/cm_process_supervisor.py",
        })
        v6 = manifest_audit.audit_manifest(
            ROOT, HERE / "RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V6-20260829.json"
        )
        self.assertTrue(v6["complete"])
        self.assertEqual(v6["python_files_checked"], 34)
        self.assertEqual(v6["missing"], {})

    def test_v6_focused_sources_run_in_an_isolated_directory(self):
        manifest = json.loads((HERE / "RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V6-20260829.json").read_text())
        with tempfile.TemporaryDirectory(prefix="cm-native-scout-v6-") as directory:
            isolated = Path(directory)
            for row in manifest["files"]:
                target = isolated / row["target"]
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / row["source"], target)
            # test_program_metrics imports pytest but does not call it. The
            # locked remote environment supplies pytest; this import-only shim
            # lets the source-closure check stay independent of local packages.
            (isolated / "pytest.py").write_text("# import-only isolation shim\n", encoding="utf-8")
            code = """
import importlib
import unittest

modules = [
    'tests.test_cm_comparative_foundation',
    'tests.test_cm_comparative_linux_supervisor',
    'tests.test_cm_comparative_native_scout',
    'tests.test_cm_comparative_readiness',
    'tests.test_cm_native_contracts',
    'tests.test_cm_no_reinflate',
]
suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
if suite.countTestCases() != 60:
    raise SystemExit('unexpected unittest count: ' + str(suite.countTestCases()))
result = unittest.TextTestRunner(verbosity=0).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
program_metrics = importlib.import_module('tests.test_program_metrics')
functions = [getattr(program_metrics, name) for name in sorted(dir(program_metrics)) if name.startswith('test_')]
if len(functions) != 8:
    raise SystemExit('unexpected function count: ' + str(len(functions)))
for function in functions:
    function()
print('isolated_focused_tests=68')
"""
            environment = dict(os.environ)
            environment.pop("PYTHONPATH", None)
            completed = subprocess.run(
                [sys.executable, "-c", code], cwd=isolated, env=environment,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180,
            )
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("isolated_focused_tests=68", completed.stdout)

    def test_remote_v2_counts_junit_elements_and_keeps_source_after_on_failure(self):
        source = (HERE / "runpod_native_scout_remote_v2.py").read_text(encoding="utf-8")
        # Loading the whole remote script would execute its workload. Compile
        # only the definitions and imports needed by the evidence helper.
        import ast
        syntax = ast.parse(source)
        keep = []
        for node in syntax.body:
            if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
                keep.append(node)
            elif isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id in {"ROOT", "OUT", "CAP"}
                    for target in node.targets):
                keep.append(node)
        namespace = {"__name__": "cm_remote_evidence_fixture"}
        exec(compile(ast.Module(body=keep, type_ignores=[]), "remote-evidence-fixture", "exec"), namespace)
        failure_xml = (
            HERE / "http-native-scout-chunked-retry-execute-001/evidence/run-output/focused.xml"
        )
        metadata, testcases = namespace["_junit_counts"](failure_xml)
        self.assertEqual(metadata, {"tests": 180, "failures": 22, "errors": 0, "skipped": 0})
        self.assertEqual(testcases, {"tests": 60, "failures": 7, "errors": 0, "skipped": 0})

        with tempfile.TemporaryDirectory(prefix="cm-remote-v2-evidence-") as directory:
            root = Path(directory)
            output = root / "run-output"
            output.mkdir()
            shutil.copy2(failure_xml, output / "focused.xml")
            payload = b"unchanged"
            (root / "source.py").write_bytes(payload)
            manifest = {"files": [{
                "target": "source.py", "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }]}
            before = [{
                "target": "source.py", "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }]
            namespace["ROOT"] = root
            namespace["OUT"] = output
            with patch("sys.stdout", new=io.StringIO()):
                namespace["publish_evidence"]("failed", "focused tests failed", manifest, before)
            validation = json.loads((output / "REMOTE-VALIDATION.json").read_text())
            self.assertEqual(validation["junit_metadata"], metadata)
            self.assertEqual(validation["junit_testcases"], testcases)
            self.assertTrue(validation["source_unchanged"])
            self.assertTrue((output / "SOURCE-AFTER.json").is_file())
            self.assertEqual(
                {row["section"] for row in validation["validation_errors"]},
                {"p5-smoke", "native-scout"},
            )

    def test_v4_controller_preserves_bounded_partial_remote_evidence(self):
        validation = {
            "status": "failed", "error": "RuntimeError: focused-tests failed with exit code 1",
            "junit_metadata": {"tests": 180, "failures": 22, "errors": 0, "skipped": 0},
            "junit_testcases": {"tests": 60, "failures": 7, "errors": 0, "skipped": 0},
            "source_unchanged": True, "validation_errors": [],
        }
        runtime = {"runpod_pod_id": "fixturepod123", "source_files": 37, "affinity": [1, 2]}
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            output.writestr("run-output/REMOTE-VALIDATION.json", json.dumps(validation))
            output.writestr("run-output/RUNTIME.json", json.dumps(runtime))
        data = archive.getvalue()
        encoded = base64.b64encode(data).decode("ascii")
        chunks = [encoded[index:index + 3072] for index in range(0, len(encoded), 3072)]
        lines = ["CM_EVENT " + json.dumps({
            "kind": "evidence_start", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "chunks": len(chunks), "uncompressed_bytes": sum(len(row) for row in (
                json.dumps(validation), json.dumps(runtime)
            )),
        })]
        lines.extend("CM_EVIDENCE %06d %s" % (index, chunk) for index, chunk in enumerate(chunks))
        lines.append("CM_EVENT " + json.dumps({"kind": "evidence_end", "sha256": hashlib.sha256(data).hexdigest()}))
        with tempfile.TemporaryDirectory(prefix="cm-controller-v4-partial-") as directory, \
                patch.object(closure_controller, "OUT", Path(directory)), \
                patch.object(closure_controller.base, "OUT", Path(directory)):
            result = closure_controller.save_evidence("\n".join(lines))
        self.assertFalse(result["verified"])
        self.assertEqual(result["validation"], validation)
        self.assertEqual(result["partial_evidence"]["junit_testcases"]["failures"], 7)

    def test_closure_retry_authorization_is_exact_and_carries_three_attempts(self):
        self.assertTrue(closure_controller.AUTHORIZATION_PATH.is_file())
        self.assertTrue(closure_controller.require_authorization()["authorized"])
        authorization = {
            "schema": "cm-runpod-native-scout-closure-retry-authorization/v1",
            "authorized": True,
            "one_create": True,
            "no_replacement": True,
            "source_files": 37,
            "focused_tests": 60,
            "p5_smoke_cells": 144,
            "performance_ranking": False,
            "source_builds_allowed": ["astutils==0.0.6", "ply==3.10"],
            "container_disk_gb": 12,
            "pod_volume_gb": 0,
            "network_volume": False,
            "lifetime_seconds": 1200,
            "phase_cap_usd": 0.10,
            "campaign_cap_usd": 0.20,
            "prior_failed_pod_ids": ["84442bdg4m47x8", "76exgpsv0y39bl", "mljd0t0sb3h1u3"],
            "chunk_bytes": 256 << 10,
            "proposal_sha256": hashlib.sha256(closure_controller.PROPOSAL_PATH.read_bytes()).hexdigest(),
            "upload_manifest_sha256": hashlib.sha256(closure_controller.MANIFEST_PATH.read_bytes()).hexdigest(),
        }
        with tempfile.TemporaryDirectory(prefix="cm-closure-auth-") as directory:
            path = Path(directory) / "authorization.json"
            path.write_text(json.dumps(authorization), encoding="utf-8")
            with patch.object(closure_controller, "AUTHORIZATION_PATH", path):
                self.assertTrue(closure_controller.require_authorization()["authorized"])
                authorization["source_files"] = 36
                path.write_text(json.dumps(authorization), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "scope mismatch"):
                    closure_controller.require_authorization()
        prior = closure_preflight.prior_attempts()
        self.assertTrue(prior["failed_chunked_scout_retry_reconciled"])
        self.assertEqual(len(prior["pod_ids"]), 7)
        self.assertAlmostEqual(
            prior["new_comparative_campaign_cost_before_scout_usd"],
            0.0025742050521903566,
        )

    def test_closure_proposal_freezes_the_executable_inputs(self):
        proposal = closure_controller.PROPOSAL_PATH.read_text(encoding="utf-8")
        for path in (
            closure_controller.MANIFEST_PATH,
            closure_controller.base.LOCK_PATH,
            Path(closure_controller.__file__),
            Path(closure_preflight.__file__),
            closure_controller.BOOTSTRAP_PATH,
            closure_controller.REMOTE_CODE_PATH,
            ROOT / "scripts/cm_manifest_dependency_audit.py",
            closure_preflight.CHUNK_FINAL,
        ):
            with self.subTest(path=path.name):
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), proposal)

    def test_remote_v3_cli_contracts_match_both_parsers(self):
        import ast

        path = HERE / "runpod_native_scout_remote_v3.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        commands = {}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "run_command" and len(node.args) >= 2
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
                    and isinstance(node.args[1], ast.List)):
                commands[node.args[0].value] = [
                    item.value if isinstance(item, ast.Constant) else None for item in node.args[1].elts
                ]
        self.assertEqual(commands["p5-smoke"][1:4], [
            "scripts/cm_comparative_smoke.py", "run", "--output"
        ])
        self.assertEqual(commands["p5-smoke-verify"][1:4], [
            "scripts/cm_comparative_smoke.py", "verify", "--output"
        ])
        self.assertEqual(commands["native-scout"][1:3], [
            "scripts/cm_comparative_native_scout.py", "--output-dir"
        ])
        smoke_source = (ROOT / "scripts/cm_comparative_smoke.py").read_text(encoding="utf-8")
        native_source = (ROOT / "scripts/cm_comparative_native_scout.py").read_text(encoding="utf-8")
        self.assertIn('run_parser.add_argument("--output"', smoke_source)
        self.assertIn('parser.add_argument("--output-dir"', native_source)

    def test_v5_controller_accepts_the_actual_nested_p5_summary_schema(self):
        validation = {
            "status": "complete", "error": None, "source_unchanged": True,
            "source_files": 37, "validation_errors": [],
            "junit_metadata": {"tests": 180, "failures": 0, "errors": 0, "skipped": 0},
            "junit_testcases": {"tests": 60, "failures": 0, "errors": 0, "skipped": 0},
            "smoke_summary": {"status": "passed", "planned_cells": 144,
                              "observed_cells": 144, "statuses": {"ok": 144}},
            "native_summary": {"status": "passed"},
        }
        runtime = {"runpod_pod_id": "fixturepod123", "source_files": 37, "affinity": [1, 2]}
        smoke = json.loads((HERE / "p5-local-smoke-20260829-003/summary.json").read_text())
        native = {
            "status": "passed", "dependencies": "passed", "linux_controls": "passed",
            "cadical": "passed", "cudd": "passed", "d4": "passed", "perf": "unavailable",
            "native_failures": 0, "semantic_mismatches": 0, "performance_measurement": False,
            "performance_ranking_permitted": False,
        }
        dependencies = {"versions": {
            "setuptools": "84.0.0", "wheel": "0.48.0", "ply": "3.10", "astutils": "0.0.6",
            "networkx": "3.6.1", "dd": "0.6.0", "six": "1.17.0", "python-sat": "1.9.dev15",
        }, "temporary_artifacts_retained": False}
        controls = {name: {"status": status} for name, status in {
            "echo": "ok", "flood": "output_limit", "tree": "timeout", "memory": "memory_limit",
        }.items()}
        files = {
            "run-output/REMOTE-VALIDATION.json": validation,
            "run-output/RUNTIME.json": runtime,
            "run-output/p5-smoke/summary.json": smoke,
            "run-output/p5-smoke-verify.json": {"returncode": 0},
            "run-output/native-scout/summary.json": native,
            "run-output/native-scout/dependencies.json": dependencies,
            "run-output/native-scout/linux-controls.json": controls,
            "run-output/native-scout/cadical.json": {"worker": {"status": "passed", "native_execution": True}},
            "run-output/native-scout/cudd.json": {"worker": {
                "status": "passed", "native_execution": True, "autoref_substituted": False,
            }},
            "run-output/native-scout/d4.json": {
                "status": "passed", "native_execution": True, "cases": [{"id": index} for index in range(5)],
            },
        }
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for name, value in files.items():
                output.writestr(name, json.dumps(value))
        data = archive.getvalue()
        encoded = base64.b64encode(data).decode("ascii")
        chunks = [encoded[index:index + 3072] for index in range(0, len(encoded), 3072)]
        lines = ["CM_EVENT " + json.dumps({
            "kind": "evidence_start", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "chunks": len(chunks), "uncompressed_bytes": sum(len(json.dumps(value)) for value in files.values()),
        })]
        lines.extend("CM_EVIDENCE %06d %s" % (index, chunk) for index, chunk in enumerate(chunks))
        lines.append("CM_EVENT " + json.dumps({"kind": "evidence_end", "sha256": hashlib.sha256(data).hexdigest()}))
        with tempfile.TemporaryDirectory(prefix="cm-controller-v5-success-") as directory:
            output = Path(directory)
            identity = output / "POD-IDENTITY.json"
            identity.write_text(json.dumps({"pod_id": "fixturepod123"}), encoding="utf-8")
            with patch.object(p5_controller, "OUT", output), \
                    patch.object(p5_controller.base, "OUT", output), \
                    patch.object(p5_controller, "IDENTITY", identity):
                result = p5_controller.save_evidence("\n".join(lines))
        self.assertTrue(result["verified"])
        self.assertEqual(result["scout"]["p5_smoke_cells"], 144)

        validation["junit_metadata"]["tests"] = 189
        validation["junit_testcases"]["tests"] = 63
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for name, value in files.items():
                output.writestr(name, json.dumps(value))
        data = archive.getvalue()
        encoded = base64.b64encode(data).decode("ascii")
        chunks = [encoded[index:index + 3072] for index in range(0, len(encoded), 3072)]
        lines = ["CM_EVENT " + json.dumps({
            "kind": "evidence_start", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "chunks": len(chunks), "uncompressed_bytes": sum(len(json.dumps(value)) for value in files.values()),
        })]
        lines.extend("CM_EVIDENCE %06d %s" % (index, chunk) for index, chunk in enumerate(chunks))
        lines.append("CM_EVENT " + json.dumps({"kind": "evidence_end", "sha256": hashlib.sha256(data).hexdigest()}))
        with tempfile.TemporaryDirectory(prefix="cm-controller-v6-success-") as directory:
            output = Path(directory)
            identity = output / "POD-IDENTITY.json"
            identity.write_text(json.dumps({"pod_id": "fixturepod123"}), encoding="utf-8")
            with patch.object(procfs_controller, "OUT", output), \
                    patch.object(procfs_controller.base, "OUT", output), \
                    patch.object(procfs_controller, "IDENTITY", identity):
                result = procfs_controller.save_evidence("\n".join(lines))
        self.assertTrue(result["verified"])
        self.assertEqual(result["scout"]["focused_tests"], 63)

    def test_p5_cli_retry_authorization_is_exact_and_carries_four_attempts(self):
        self.assertTrue(p5_controller.AUTHORIZATION_PATH.is_file())
        self.assertTrue(p5_controller.require_authorization()["authorized"])
        authorization = {
            "schema": "cm-runpod-native-scout-p5-cli-retry-authorization/v1",
            "authorized": True, "one_create": True, "no_replacement": True,
            "source_files": 37, "focused_tests": 60, "p5_smoke_cells": 144,
            "performance_ranking": False,
            "source_builds_allowed": ["astutils==0.0.6", "ply==3.10"],
            "container_disk_gb": 12, "pod_volume_gb": 0, "network_volume": False,
            "lifetime_seconds": 1200, "phase_cap_usd": 0.10, "campaign_cap_usd": 0.20,
            "prior_failed_pod_ids": [
                "84442bdg4m47x8", "76exgpsv0y39bl", "mljd0t0sb3h1u3", "pes90ta8wgi2g6",
            ],
            "chunk_bytes": 256 << 10,
            "proposal_sha256": hashlib.sha256(p5_controller.PROPOSAL_PATH.read_bytes()).hexdigest(),
            "upload_manifest_sha256": hashlib.sha256(p5_controller.MANIFEST_PATH.read_bytes()).hexdigest(),
        }
        with tempfile.TemporaryDirectory(prefix="cm-p5-cli-auth-") as directory:
            path = Path(directory) / "authorization.json"
            path.write_text(json.dumps(authorization), encoding="utf-8")
            with patch.object(p5_controller, "AUTHORIZATION_PATH", path):
                self.assertTrue(p5_controller.require_authorization()["authorized"])
                authorization["chunk_bytes"] += 1
                path.write_text(json.dumps(authorization), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "scope mismatch"):
                    p5_controller.require_authorization()
        prior = p5_preflight.prior_attempts()
        self.assertTrue(prior["failed_dependency_closed_scout_retry_reconciled"])
        self.assertEqual(len(prior["pod_ids"]), 8)
        self.assertAlmostEqual(
            prior["new_comparative_campaign_cost_before_scout_usd"],
            0.004289398746358024,
        )

    def test_p5_cli_proposal_freezes_the_executable_inputs(self):
        proposal = p5_controller.PROPOSAL_PATH.read_text(encoding="utf-8")
        for path in (
            p5_controller.MANIFEST_PATH,
            p5_controller.base.LOCK_PATH,
            HERE / "RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json",
            Path(p5_controller.__file__),
            Path(p5_preflight.__file__),
            p5_controller.BOOTSTRAP_PATH,
            p5_controller.REMOTE_CODE_PATH,
            p5_preflight.CLOSURE_FINAL,
        ):
            with self.subTest(path=path.name):
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), proposal)

    def test_procfs_retry_manifest_changes_only_supervisor_and_regressions(self):
        old = json.loads((HERE / "RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V5-20260829.json").read_text())
        new = json.loads((HERE / "RUNPOD-NATIVE-SCOUT-UPLOAD-MANIFEST-V6-20260829.json").read_text())
        old_rows = {row["source"]: (row["bytes"], row["sha256"]) for row in old["files"]}
        new_rows = {row["source"]: (row["bytes"], row["sha256"]) for row in new["files"]}
        self.assertEqual(set(old_rows), set(new_rows))
        self.assertEqual(
            {path for path in old_rows if old_rows[path] != new_rows[path]},
            {"cmbench/comparative/linux_supervisor.py", "tests/test_cm_comparative_linux_supervisor.py"},
        )
        self.assertIn('TERMINAL_PROC_STATES = frozenset({"Z", "X", "x"})',
                      (ROOT / "cmbench/comparative/linux_supervisor.py").read_text())

    def test_procfs_retry_authorization_is_exact_and_carries_five_attempts(self):
        self.assertTrue(procfs_controller.AUTHORIZATION_PATH.is_file())
        self.assertTrue(procfs_controller.require_authorization()["authorized"])
        with tempfile.TemporaryDirectory(prefix="cm-procfs-auth-") as directory:
            path = Path(directory) / "authorization.json"
            with patch.object(procfs_controller, "AUTHORIZATION_PATH", path), \
                    self.assertRaisesRegex(RuntimeError, "authorization record is absent"):
                procfs_controller.require_authorization()
            authorization = {
                "schema": "cm-runpod-native-scout-procfs-race-retry-authorization/v1",
                "authorized": True, "one_create": True, "no_replacement": True,
                "source_files": 37, "focused_tests": 63, "p5_smoke_cells": 144,
                "performance_ranking": False,
                "source_builds_allowed": ["astutils==0.0.6", "ply==3.10"],
                "container_disk_gb": 12, "pod_volume_gb": 0, "network_volume": False,
                "lifetime_seconds": 1200, "phase_cap_usd": 0.10, "campaign_cap_usd": 0.20,
                "prior_failed_pod_ids": [
                    "84442bdg4m47x8", "76exgpsv0y39bl", "mljd0t0sb3h1u3", "pes90ta8wgi2g6",
                    "pow0qre2q39m4t",
                ],
                "chunk_bytes": 256 << 10,
                "proposal_sha256": hashlib.sha256(procfs_controller.PROPOSAL_PATH.read_bytes()).hexdigest(),
                "upload_manifest_sha256": hashlib.sha256(procfs_controller.MANIFEST_PATH.read_bytes()).hexdigest(),
            }
            path.write_text(json.dumps(authorization), encoding="utf-8")
            with patch.object(procfs_controller, "AUTHORIZATION_PATH", path):
                self.assertTrue(procfs_controller.require_authorization()["authorized"])
                authorization["focused_tests"] = 60
                path.write_text(json.dumps(authorization), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "scope mismatch"):
                    procfs_controller.require_authorization()
        prior = procfs_preflight.prior_attempts()
        self.assertTrue(prior["failed_p5_procfs_scout_retry_reconciled"])
        self.assertEqual(len(prior["pod_ids"]), 9)
        self.assertAlmostEqual(prior["new_comparative_campaign_cost_before_scout_usd"], 0.005954736242691676)

    def test_procfs_retry_proposal_freezes_the_executable_inputs(self):
        proposal = procfs_controller.PROPOSAL_PATH.read_text(encoding="utf-8")
        for path in (
            procfs_controller.MANIFEST_PATH,
            procfs_controller.base.LOCK_PATH,
            HERE / "RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json",
            Path(procfs_controller.__file__),
            Path(procfs_preflight.__file__),
            procfs_controller.BOOTSTRAP_PATH,
            procfs_controller.REMOTE_CODE_PATH,
            procfs_preflight.P5_FINAL,
            HERE / "NATIVE-SCOUT-PROCFS-RACE-LOCAL-VERIFICATION-20260829.json",
            HERE / "HTTP-NATIVE-SCOUT-PROCFS-RACE-RETRY-PREFLIGHT-20260829-123952-121671.json",
        ):
            with self.subTest(path=path.name):
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), proposal)

    def test_host_preflight_amendment_preserves_zero_create_refusal(self):
        failure = json.loads(host_preflight.LOCAL_FAILURE.read_text())
        self.assertEqual(failure["status"], "local_preflight_refused")
        self.assertEqual(failure["host_ac_line_status"], 0)
        self.assertFalse(failure["controller_run_entered"])
        self.assertFalse(failure["creation_attempted"])
        self.assertEqual(failure["runpod_create_requests"], 0)
        self.assertFalse(failure["authorization_cloud_create_consumed"])
        self.assertTrue(host_preflight.V6_OUTPUT.is_dir())
        self.assertEqual(list(host_preflight.V6_OUTPUT.iterdir()), [])
        with patch.object(host_preflight.previous, "check", return_value={"ready": True}), \
                patch.object(host_preflight, "host_ac_connected", return_value=True):
            checked = host_preflight.check()
        self.assertTrue(checked["v6_local_preflight_refusal_preserved"])
        self.assertTrue(checked["v6_cloud_create_authorization_unconsumed"])
        self.assertTrue(checked["host_ac_connected"])
        self.assertTrue(checked["ready"])

    def test_host_preflight_controller_corrects_only_local_launch_contract(self):
        self.assertTrue(host_controller.AUTHORIZATION_PATH.exists())
        self.assertTrue(host_controller.require_authorization()["authorized"])
        self.assertEqual(host_controller.OUT.name, "native-procfs-v7-001")
        self.assertLess(len(str((host_controller.OUT / "HOST-AWAKE-http-controller.json").resolve())), 220)
        manifest = host_controller.load(host_controller.MANIFEST_PATH)
        self.assertEqual(manifest["bytes"], 5504396)
        source = Path(host_controller.__file__).read_text(encoding="utf-8")
        self.assertIn('manifest.get("bytes") != 5504396', source)
        self.assertNotIn('manifest.get("bytes") != 5500977', source)
        with tempfile.TemporaryDirectory(prefix="cm-host-auth-") as directory, \
                patch.object(host_controller, "AUTHORIZATION_PATH", Path(directory) / "absent.json"), \
                self.assertRaisesRegex(RuntimeError, "authorization record is absent"):
            host_controller.require_authorization()
        authorization = {
            "schema": "cm-runpod-native-scout-host-preflight-amendment-authorization/v1",
            "authorized": True, "one_create": True, "no_replacement": True,
            "source_files": 37, "focused_tests": 63, "p5_smoke_cells": 144,
            "performance_ranking": False,
            "source_builds_allowed": ["astutils==0.0.6", "ply==3.10"],
            "container_disk_gb": 12, "pod_volume_gb": 0, "network_volume": False,
            "lifetime_seconds": 1200, "phase_cap_usd": 0.10, "campaign_cap_usd": 0.20,
            "prior_failed_pod_ids": [
                "84442bdg4m47x8", "76exgpsv0y39bl", "mljd0t0sb3h1u3", "pes90ta8wgi2g6",
                "pow0qre2q39m4t",
            ],
            "chunk_bytes": 256 << 10,
            "prior_authorization_sha256": hashlib.sha256(host_preflight.V6_AUTHORIZATION.read_bytes()).hexdigest(),
            "local_preflight_failure_sha256": hashlib.sha256(host_preflight.LOCAL_FAILURE.read_bytes()).hexdigest(),
            "proposal_sha256": hashlib.sha256(host_controller.PROPOSAL_PATH.read_bytes()).hexdigest(),
            "upload_manifest_sha256": hashlib.sha256(host_controller.MANIFEST_PATH.read_bytes()).hexdigest(),
        }
        with tempfile.TemporaryDirectory(prefix="cm-host-auth-valid-") as directory:
            path = Path(directory) / "authorization.json"
            path.write_text(json.dumps(authorization), encoding="utf-8")
            with patch.object(host_controller, "AUTHORIZATION_PATH", path):
                self.assertTrue(host_controller.require_authorization()["authorized"])
                authorization["local_preflight_failure_sha256"] = "0" * 64
                path.write_text(json.dumps(authorization), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "scope mismatch"):
                    host_controller.require_authorization()
        proposal = host_controller.PROPOSAL_PATH.read_text(encoding="utf-8")
        for path in (
            Path(host_controller.__file__), Path(host_preflight.__file__), host_controller.MANIFEST_PATH,
            host_controller.BOOTSTRAP_PATH, host_controller.REMOTE_CODE_PATH, host_controller.base.LOCK_PATH,
            HERE / "RUNPOD-NATIVE-SCOUT-DEPENDENCY-LOCK-20260829.json",
            host_preflight.V6_AUTHORIZATION, host_preflight.LOCAL_FAILURE,
            HERE / "NATIVE-SCOUT-HOST-PREFLIGHT-AMENDMENT-LOCAL-VERIFICATION-20260829.json",
            HERE / "HTTP-NATIVE-SCOUT-HOST-PREFLIGHT-AMENDMENT-PREFLIGHT-20260829.json",
        ):
            with self.subTest(path=path.name):
                self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), proposal)

if __name__ == "__main__":
    unittest.main()
