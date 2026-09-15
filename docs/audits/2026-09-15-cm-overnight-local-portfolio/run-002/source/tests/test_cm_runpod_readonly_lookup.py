"""Offline checks of the existing root-loader pod lookup; never load real keys."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / (
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/runpod-authorized-20260827-213104/"
    "inspect_root_config_pod.py"
)
spec = importlib.util.spec_from_file_location("root_lookup_offline_checks", HELPER)
lookup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lookup)

FAKE_KEY = "offline-fixture-not-a-real-api-key"
FAKE_POD = "offline123456"


def response(status, body=None, error=None):
    value = mock.Mock(spec_set=["status_code", "json"])
    value.status_code = status
    value.json.return_value = body
    value.json.side_effect = error
    return value


class RootLookupOfflineTests(unittest.TestCase):
    def setUp(self):
        # Fail closed if a test accidentally invokes the real credential loader.
        loader_patch = mock.patch.object(
            lookup, "load_runpod_config",
            side_effect=AssertionError("real credential loader is forbidden"),
        )
        self.loader = loader_patch.start()
        self.addCleanup(loader_patch.stop)
        session_patch = mock.patch.object(lookup.requests, "Session")
        self.session_factory = session_patch.start()
        self.addCleanup(session_patch.stop)

    def client(self, replies):
        # No POST/PUT/PATCH/DELETE/request method exists on this fake client.
        client = mock.MagicMock(spec_set=[
            "headers", "trust_env", "get", "__enter__", "__exit__",
        ])
        client.headers = {}
        client.trust_env = True
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.get.side_effect = replies
        return client

    def inspect(self, replies):
        client = self.client(replies)
        self.session_factory.return_value = client
        result = lookup.inspect("v1", "https://rest.runpod.io/v1", FAKE_POD, FAKE_KEY)
        self.loader.assert_not_called()
        self.assertNotIn(FAKE_KEY, json.dumps(result))
        return result, client

    def test_both_endpoints_use_only_bounded_nonredirecting_gets(self):
        for version, base in lookup.ENDPOINTS:
            with self.subTest(version=version):
                client = self.client([response(404), response(200, [])])
                self.session_factory.return_value = client
                result = lookup.inspect(version, base, FAKE_POD, FAKE_KEY)
                self.assertFalse(client.trust_env)
                self.assertEqual(client.headers, {"Authorization": "Bearer " + FAKE_KEY})
                self.assertEqual(client.get.call_args_list, [
                    mock.call(base + "/pods/" + FAKE_POD, timeout=15, allow_redirects=False),
                    mock.call(base + "/pods", timeout=15, allow_redirects=False),
                ])
                self.assertEqual(result["detail"]["http_status"], 404)
                self.assertEqual(result["inventory"]["pod_count"], 0)
                self.assertFalse(result["inventory"]["target_in_inventory"])
        self.loader.assert_not_called()

    def test_detail_and_inventory_drop_unselected_private_fields(self):
        pod = {"id": FAKE_POD, "status": "RUNNING", "env": {"KEY": FAKE_KEY},
               "privateToken": FAKE_KEY, "dockerStartCmd": [FAKE_KEY]}
        result, _ = self.inspect([response(200, {"pod": pod}), response(200, [pod])])
        self.assertEqual(result["detail"]["pod"], {"id": FAKE_POD, "status": "RUNNING"})
        self.assertEqual(result["inventory"]["pods"], [{"id": FAKE_POD, "status": "RUNNING"}])
        self.assertTrue(result["inventory"]["target_in_inventory"])

    def test_inventory_accepts_list_and_pods_wrapper(self):
        for body in ([], {"pods": []}):
            with self.subTest(body=body):
                result, _ = self.inspect([response(404), response(200, body)])
                self.assertEqual(result["inventory"]["pod_count"], 0)
                self.assertNotIn("error_type", result["inventory"])

    def test_http_error_bodies_are_never_parsed(self):
        for status in (401, 403, 404, 429, 500):
            with self.subTest(status=status):
                replies = [response(status, {"message": FAKE_KEY}) for _ in range(2)]
                result, _ = self.inspect(replies)
                for kind, reply in zip(("detail", "inventory"), replies):
                    self.assertEqual(result[kind], {"http_status": status})
                    reply.json.assert_not_called()

    def test_json_failure_records_exception_type_not_message(self):
        result, _ = self.inspect([
            response(200, error=ValueError(FAKE_KEY)), response(200, []),
        ])
        self.assertEqual(result["detail"], {"http_status": 200, "error_type": "ValueError"})
        self.assertEqual(result["inventory"]["pod_count"], 0)

    def test_malformed_inventory_is_not_reported_as_empty(self):
        for body in ({}, {"pods": None}, {"pods": "invalid"}, [None]):
            with self.subTest(body=body):
                result, _ = self.inspect([response(404), response(200, body)])
                self.assertIn("error_type", result["inventory"])
                self.assertFalse(result["inventory"].get("pod_count") == 0)

    def test_network_exception_is_redacted_and_other_request_is_retained(self):
        result, _ = self.inspect([
            lookup.requests.Timeout(FAKE_KEY), response(200, []),
        ])
        self.assertEqual(result["detail"], {"error_type": "Timeout"})
        self.assertEqual(result["inventory"]["pod_count"], 0)

    def test_invalid_pod_id_refuses_before_credentials_or_network(self):
        for pod in ("../other", "abc?token=value", "short", "x" * 41):
            with self.subTest(pod=pod), mock.patch.object(
                lookup.sys, "argv", [str(HELPER), "--pod-id", pod]
            ):
                with self.assertRaises(ValueError):
                    lookup.main()
        self.loader.assert_not_called()
        self.session_factory.assert_not_called()

    def test_missing_fake_key_refuses_before_network(self):
        self.loader.side_effect = None
        self.loader.return_value = SimpleNamespace(api_key="", pod_id="")
        with mock.patch.object(lookup.sys, "argv", [str(HELPER), "--pod-id", FAKE_POD]):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(lookup.main(), 2)
        self.session_factory.assert_not_called()

    def test_main_writes_new_sanitized_evidence_with_fake_auth_only(self):
        self.loader.side_effect = None
        self.loader.return_value = SimpleNamespace(api_key=FAKE_KEY, pod_id="")
        clients = [self.client([response(404), response(200, [])]) for _ in range(2)]
        self.session_factory.side_effect = clients
        with tempfile.TemporaryDirectory(prefix="cm-readonly-offline-") as directory:
            with mock.patch.object(lookup, "HERE", Path(directory)), mock.patch.object(
                lookup.sys, "argv", [str(HELPER), "--pod-id", FAKE_POD]
            ), redirect_stdout(io.StringIO()) as captured:
                self.assertEqual(lookup.main(), 0)
            files = list(Path(directory).glob("ROOT-CONFIG-POD-INSPECTION-*.json"))
            self.assertEqual(len(files), 1)
            raw = files[0].read_text(encoding="utf-8")
            result = json.loads(raw)
            self.assertNotIn(FAKE_KEY, raw + captured.getvalue())
            self.assertEqual(result["resource_writes"], 0)
            self.assertEqual(result["files_uploaded"], 0)
            self.assertTrue(result["read_only"])
            self.assertEqual(len(result["checks"]), 2)
            self.assertEqual(sum(client.get.call_count for client in clients), 4)


if __name__ == "__main__":
    unittest.main()
