"""Independent small fake-input checks; no sockets, credentials or workloads."""
import base64
from contextlib import contextmanager
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TRANSPORT = ROOT / (
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/"
    "maximal-safe-20260827-192909/runpod-authorized-20260827-213104"
)


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, TRANSPORT / filename)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.object(sys, "path", [str(TRANSPORT), *sys.path]):
        spec.loader.exec_module(module)
    return module


server = load_module("independent_http_bootstrap", "http_transport_bootstrap.py")
controller = load_module("independent_http_controller", "runpod_http_smoke_controller_v2.py")
FAKE_TOKEN = "OFFLINE_ONLY_TOKEN_0123456789"
FAKE_POD = "offline123456"


class TransportIndependentTests(unittest.TestCase):
    def setUp(self):
        self.patch(controller.preflight, "session", side_effect=AssertionError("no credentials"))
        self.patch(controller.preflight, "check", side_effect=AssertionError("no live preflight"))
        self.patch(controller.base, "read_key", side_effect=AssertionError("no credentials"))
        self.patch(controller.requests, "Session", side_effect=AssertionError("no network"))
        self.patch(controller, "load", side_effect=AssertionError("no live run artifacts"))
        self.patch(controller, "windows_pid_running", return_value=True)
        self.patch(server.subprocess, "Popen", side_effect=AssertionError("no workload"))
        self.patch(server, "TOKEN", FAKE_TOKEN)
        self.patch(server, "DEADLINE", 99999999999)
        self.patch(server, "STATE", {
            "uploaded": False, "started": False, "done": False,
            "stage": "awaiting-upload", "error": None,
        })
        self.patch(server, "PAYLOAD", None)
        self.patch(server, "LOG", bytearray())
        self.payload = {
            "bundle": base64.b64encode(b"offline-fixture").decode(),
            "manifest": base64.b64encode(b"{}").decode(),
            "code": base64.b64encode(b"raise RuntimeError('must not execute')").decode(),
            "environment": {
                "CM_BUNDLE_SHA256": hashlib.sha256(b"offline-fixture").hexdigest(),
                "CM_IMAGE_TAG": "offline", "CM_IMAGE_DIGEST": "offline",
                "CM_SETUP_DEADLINE": "1000",
            },
        }
        self.raw = json.dumps(self.payload, sort_keys=True).encode()
        self.pin(self.raw)

    def patch(self, target, name, *args, **kwargs):
        patcher = mock.patch.object(target, name, *args, **kwargs)
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def pin(self, raw):
        self.patch(server, "EXPECTED_HASH", hashlib.sha256(raw).hexdigest())
        self.patch(server, "EXPECTED_SIZE", len(raw))

    def handler(self, path, port, content=b"", token=FAKE_TOKEN):
        handler = object.__new__(server.Handler)
        handler.path = path
        handler.server = SimpleNamespace(server_port=port)
        handler.headers = {"Content-Length": str(len(content))}
        if token is not None:
            handler.headers["X-CM-Token"] = token
        handler.rfile = io.BytesIO(content)
        handler.reply = mock.Mock()
        return handler

    def test_missing_and_wrong_tokens_deny_all_sensitive_routes(self):
        for token in (None, "wrong-offline-token"):
            for method, path, port in (
                ("GET", "/progress", 8081), ("GET", "/results", 8081),
                ("POST", "/payload", 8080), ("POST", "/run", 8081),
            ):
                with self.subTest(token=token, path=path):
                    handler = self.handler(path, port, token=token)
                    getattr(handler, "do_" + method)()
                    self.assertEqual(handler.reply.call_args.args[0], 403)
        self.assertFalse(server.STATE["uploaded"])
        self.assertFalse(server.STATE["started"])

    def test_health_is_minimal_and_does_not_disclose_state(self):
        handler = self.handler("/health", 8080, token=None)
        handler.do_GET()
        self.assertEqual(handler.reply.call_args.args, (200, {
            "service": "cm-memory-http", "ready": True,
        }))

    def test_upload_tampering_and_truncation_are_refused(self):
        for raw in (self.raw[:-1], b"X" + self.raw[1:]):
            with self.subTest(length=len(raw)):
                handler = self.handler("/payload", 8080, raw)
                handler.headers["Content-Length"] = str(len(self.raw))
                handler.do_POST()
                self.assertEqual(handler.reply.call_args.args[0], 400)
                self.assertFalse(server.STATE["uploaded"])

    def test_bad_lengths_and_transfer_encoding_are_refused(self):
        for headers in (
            {"Content-Length": "-1"}, {"Content-Length": "not-an-integer"},
            {"Content-Length": str(server.UPLOAD_CAP + 1)},
            {"Content-Length": "0", "Transfer-Encoding": "chunked"},
        ):
            with self.subTest(headers=headers):
                handler = self.handler("/payload", 8080)
                handler.headers.update(headers)
                handler.do_POST()
                self.assertEqual(handler.reply.call_args.args[0], 400)

    def test_expired_deadline_refuses_upload_and_run(self):
        self.patch(server, "DEADLINE", 0)
        for path, port in (("/payload", 8080), ("/run", 8081)):
            handler = self.handler(path, port)
            handler.do_POST()
            self.assertEqual(handler.reply.call_args.args[0], 410)

    def test_run_requires_upload_and_accepts_no_command(self):
        handler = self.handler("/run", 8081)
        handler.do_POST()
        self.assertEqual(handler.reply.call_args.args[0], 409)
        handler = self.handler("/run", 8081, b"unapproved command")
        handler.do_POST()
        self.assertEqual(handler.reply.call_args.args[0], 400)

    def test_run_is_at_most_once_and_later_upload_is_refused(self):
        self.handler("/payload", 8080, self.raw).do_POST()
        thread = self.patch(server.threading, "Thread")
        self.handler("/run", 8081).do_POST()
        self.handler("/run", 8081).do_POST()
        thread.assert_called_once()
        thread.return_value.start.assert_called_once()
        self.assertIsNone(server.PAYLOAD)
        handler = self.handler("/payload", 8080, self.raw)
        handler.do_POST()
        self.assertEqual(handler.reply.call_args.args[0], 409)

    def test_routes_are_bound_to_their_declared_ports(self):
        for method, path, port in (
            ("POST", "/payload", 8081), ("POST", "/run", 8080),
            ("GET", "/progress", 8080), ("GET", "/results", 8080),
        ):
            handler = self.handler(path, port, self.raw if path == "/payload" else b"")
            getattr(handler, "do_" + method)()
            self.assertEqual(handler.reply.call_args.args[0], 404)

    def test_results_refuse_incomplete_work_and_return_only_bounded_log(self):
        handler = self.handler("/results", 8081)
        handler.do_GET()
        self.assertEqual(handler.reply.call_args.args[0], 425)
        server.STATE["done"] = True
        server.LOG.extend(b"offline result")
        handler = self.handler("/results", 8081)
        handler.do_GET()
        self.assertEqual(handler.reply.call_args.args, (
            200, b"offline result", "application/octet-stream",
        ))

    def test_payload_cannot_add_environment_fields_even_with_matching_hash(self):
        self.payload["environment"]["RUNPOD_API_KEY"] = "OFFLINE_SENTINEL"
        raw = json.dumps(self.payload).encode()
        self.pin(raw)
        with self.assertRaises(ValueError):
            server.validate_payload(raw)

    def test_child_environment_drops_provider_and_bootstrap_secrets(self):
        self.patch(server.os, "environ", {
            "PATH": "/usr/bin", "RUNPOD_POD_ID": FAKE_POD,
            "RUNPOD_API_KEY": "OFFLINE_SENTINEL", "RP_TOKEN": "OFFLINE_SENTINEL",
            "CM_BOOTSTRAP_TOKEN": "OFFLINE_SENTINEL", "OTHER_PRIVATE": "OFFLINE_SENTINEL",
        })
        environment = server.child_environment(self.payload)
        self.assertNotIn("OFFLINE_SENTINEL", json.dumps(environment))
        self.assertEqual(environment["RUNPOD_POD_ID"], FAKE_POD)
        self.assertEqual(environment["OPENBLAS_NUM_THREADS"], "1")

    def test_declared_and_streamed_result_caps_are_enforced(self):
        response = SimpleNamespace(headers={"Content-Length": "5"}, iter_content=mock.Mock())
        with self.assertRaises(RuntimeError):
            controller.bounded_response(response, 4)
        response.iter_content.assert_not_called()
        response = SimpleNamespace(headers={}, iter_content=mock.Mock(return_value=[b"ab", b"cde"]))
        with self.assertRaises(RuntimeError):
            controller.bounded_response(response, 4)
        response.iter_content.return_value = [b"ab", b"cd"]
        self.assertEqual(controller.bounded_response(response, 4), b"abcd")

    def test_cleanup_ignores_unrelated_pods_and_refuses_ambiguous_ownership(self):
        self.patch(controller, "IDENTITY", SimpleNamespace(exists=lambda: False))
        snapshot = {"v1": [{"id": "other123456", "name": "unrelated"}], "v2": []}
        self.assertEqual(controller.find_owned(snapshot, {"name": "owned"}), [])
        snapshot = {"v1": [{"id": "first123456", "name": "owned"}],
                    "v2": [{"id": "second12345", "name": "owned"}]}
        with self.assertRaises(RuntimeError):
            controller.find_owned(snapshot, {"name": "owned"})

    def test_cleanup_refuses_reassigned_id_or_different_matching_id(self):
        self.patch(controller, "IDENTITY", SimpleNamespace(exists=lambda: True))
        self.patch(controller, "load", return_value={"pod_id": FAKE_POD})
        for pod in ({"id": FAKE_POD, "name": "unrelated"},
                    {"id": "other123456", "name": "owned"}):
            with self.assertRaises(RuntimeError):
                controller.find_owned({"v1": [pod], "v2": []}, {"name": "owned"})

    def documented_pod(self):
        return {
            "id": FAKE_POD, "name": "owned", "cpuFlavorId": "cpu3c",
            "vcpuCount": 2, "memoryInGb": 4, "costPerHr": 0.06,
            "image": controller.base.IMAGE, "containerDiskInGb": 12,
            "volumeInGb": 10, "volumeMountPath": "/workspace",
            "ports": ["8080/http", "8081/http"], "networkVolume": None,
            "gpu": None, "machine": {"secureCloud": True},
        }

    def test_documented_v1_response_field_names_are_accepted(self):
        # V1's response has image, not the create request's imageName.
        self.patch(controller, "load", return_value={"pod_id": FAKE_POD})
        result = controller.validate_pod(
            self.documented_pod(), {"name": "owned"}, {"id": "cpu3c"}, 0,
        )
        self.assertEqual(result["pod_id"], FAKE_POD)

    def test_documented_response_still_refuses_resource_and_budget_changes(self):
        self.patch(controller, "load", return_value={"pod_id": FAKE_POD})
        for key, value in (
            ("image", "wrong-image"), ("vcpuCount", 8), ("memoryInGb", 2),
            ("costPerHr", float("nan")), ("costPerHr", 0.26),
            ("ports", ["22/tcp"]), ("volumeInGb", 11),
            ("networkVolume", {"id": "not-approved"}),
            ("machine", {"secureCloud": False}), ("gpu", {"id": "not-approved"}),
        ):
            with self.subTest(key=key, value=value):
                pod = self.documented_pod()
                pod[key] = value
                with self.assertRaises(RuntimeError):
                    controller.validate_pod(pod, {"name": "owned"}, {"id": "cpu3c"}, 0)

    def test_watchdog_requires_exact_acknowledgment_and_live_process(self):
        state = {"name": "owned", "horizon_epoch": 1200}
        self.patch(controller, "STATE_ACK", SimpleNamespace(exists=lambda: True))
        loader = self.patch(controller, "load", return_value={"state": state, "pid": 123})
        proc = SimpleNamespace(pid=123, poll=mock.Mock(return_value=None))
        controller.confirm_watchdog(proc, state)
        self.assertEqual(proc.poll.call_count, 2)
        for ack in ({"state": {"name": "different"}, "pid": 123},
                    {"state": state, "pid": 456}):
            loader.return_value = ack
            with self.assertRaises(RuntimeError):
                controller.confirm_watchdog(proc, state)
        loader.return_value = {"state": state, "pid": 123}
        for statuses in ([1], [None, 1]):
            proc.poll = mock.Mock(side_effect=statuses)
            with self.assertRaises(RuntimeError):
                controller.confirm_watchdog(proc, state)

    def test_watchdog_missing_acknowledgment_times_out_without_real_waits(self):
        self.patch(controller, "STATE_ACK", SimpleNamespace(exists=lambda: False))
        sleeps = self.patch(controller.time, "sleep")
        proc = SimpleNamespace(pid=123, poll=mock.Mock(return_value=None))
        with self.assertRaises(RuntimeError):
            controller.confirm_watchdog(proc, {"name": "owned"})
        self.assertLessEqual(sleeps.call_count, 50)
        self.assertGreater(sleeps.call_count, 0)

    def test_windows_worker_binding_accepts_only_live_launcher_or_its_child(self):
        for ready in ({"pid": 123, "parent_pid": 99}, {"pid": 456, "parent_pid": 123}):
            proc = SimpleNamespace(pid=123, poll=mock.Mock(return_value=None))
            binding = controller.bind_watchdog(proc, ready)
            self.assertEqual(proc.cm_watchdog_pid, ready["pid"])
            self.assertEqual(binding["venv_redirector_observed"], ready["pid"] != proc.pid)
        for ready in ({"pid": 456, "parent_pid": 999}, {"pid": 0}, {"pid": "invalid"}):
            with self.assertRaises(RuntimeError):
                controller.bind_watchdog(SimpleNamespace(pid=123, poll=lambda: None), ready)
        self.patch(controller, "windows_pid_running", return_value=False)
        with self.assertRaises(RuntimeError):
            controller.bind_watchdog(SimpleNamespace(pid=123, poll=lambda: None),
                                     {"pid": 456, "parent_pid": 123})

    def test_bound_worker_ack_must_match_child_not_venv_launcher(self):
        state = {"name": "owned", "horizon_epoch": 1200}
        proc = SimpleNamespace(pid=123, cm_watchdog_pid=456, poll=lambda: None)
        self.patch(controller, "STATE_ACK", SimpleNamespace(exists=lambda: True))
        loader = self.patch(controller, "load", return_value={"state": state, "pid": 456})
        controller.confirm_watchdog(proc, state)
        loader.return_value = {"state": state, "pid": 123}
        with self.assertRaises(RuntimeError):
            controller.confirm_watchdog(proc, state)

    def test_placement_fallback_uses_same_pod_id_and_no_redirects(self):
        pod = self.documented_pod()
        pod.pop("machine")
        replies = [mock.Mock(), mock.Mock()]
        replies[0].json.return_value = pod
        replies[1].json.return_value = {"id": FAKE_POD, "cloud": "SECURE"}
        client = mock.Mock(spec_set=["get"])
        client.get.side_effect = replies
        result = controller.actual_pod(client, FAKE_POD)
        self.assertEqual(result["verified_v2_cloud"], "SECURE")
        self.assertEqual(client.get.call_args_list, [
            mock.call(controller.preflight.V1 + "/pods/" + FAKE_POD, timeout=10, allow_redirects=False),
            mock.call(controller.preflight.V2 + "/pods/" + FAKE_POD, timeout=10, allow_redirects=False),
        ])
        replies[1].json.return_value = {"id": "different123", "cloud": "SECURE"}
        client.get.side_effect = replies
        with self.assertRaises(RuntimeError):
            controller.actual_pod(client, FAKE_POD)

    def test_missing_or_conflicting_placement_and_image_evidence_is_refused(self):
        self.patch(controller, "load", return_value={"pod_id": FAKE_POD})
        for changes in (
            {"machine": {}}, {"cloud": "COMMUNITY"}, {"imageName": "different"},
            {"id": "different123"}, {"computeType": "GPU"},
        ):
            pod = {**self.documented_pod(), **changes}
            with self.assertRaises(RuntimeError):
                controller.validate_pod(pod, {"name": "owned"}, {"id": "cpu3c"}, 0)

    def test_control_state_is_not_visible_during_json_writes(self):
        # Deterministic publication-race probe; no timing-dependent threads.
        with tempfile.TemporaryDirectory(prefix="cm-state-publication-") as directory:
            target = Path(directory) / "controller-state.json"
            original_open = Path.open
            observed_partial_publication = []

            class ObservedStream:
                def __init__(self, stream):
                    self.stream = stream

                def write(self, value):
                    if target.exists():
                        observed_partial_publication.append(True)
                    return self.stream.write(value)

                def __getattr__(self, name):
                    return getattr(self.stream, name)

            @contextmanager
            def watched_open(path, mode="r", *args, **kwargs):
                with original_open(path, mode, *args, **kwargs) as stream:
                    yield ObservedStream(stream) if any(flag in mode for flag in "wax+") else stream

            with mock.patch.object(Path, "open", watched_open):
                controller.write(target, {"name": "owned", "horizon_epoch": 1000})
            self.assertFalse(observed_partial_publication,
                             "Final state filename became visible before JSON publication completed")
            self.assertEqual(json.loads(target.read_text()), {"name": "owned", "horizon_epoch": 1000})
            with self.assertRaises(FileExistsError):
                controller.write(target, {"must": "not overwrite"})


if __name__ == "__main__":
    unittest.main()
