"""Trivial fake-client control-flow checks; no network, credentials, or workload."""
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    path = ROOT / "runpod_gpu_smoke_controller.py"
    module = load("gpu_check", path.name)
    base = load("cpu_check", "runpod_retry_cpu8_controller.py")
    ast.parse(path.read_text())
    compile(module.REMOTE_CODE, "<remote-bootstrap>", "exec")
    assert module.REMOTE_CODE == base.REMOTE_CODE
    manifest = json.loads(module.MANIFEST_PATH.read_text())
    bundle = module.make_bundle(manifest)
    fixtures = ROOT / ("gpu-fake-client-" + uuid.uuid4().hex[:8])
    fixtures.mkdir()
    cases = [("http400", 400), ("http500", 500), ("success", 201), ("wrong-gpu", 201),
             ("two-gpus", 201), ("overprice", 201), ("nan-price", 201), ("ports", 201),
             ("too-little-ram", 201), ("prior-budget", 201)]
    results = []
    for case, status in cases:
        module.OUT = fixtures / case
        module.OUT.mkdir()
        for attribute, filename in (("STATE", "controller-state.json"), ("POD_IDENTITY", "POD-IDENTITY.json"),
                                    ("WATCHDOG_READY", "watchdog-ready.json"), ("WATCHDOG_DONE", "watchdog-done"),
                                    ("RUN_RECORD", "RUN.json")):
            setattr(module, attribute, module.OUT / filename)
        captures = {}

        class Response:
            status_code = status
            headers = {"X-Request-Id": "FAKE-CLIENT-NOT-A-REAL-POD"}

            def __init__(self, body):
                self.body = body

            def json(self):
                return self.body

            def raise_for_status(self):
                pass

        class Client:
            def post(self, url, **kwargs):
                assert url == module.REST_V2 + "/pods"
                payload = kwargs["json"]
                assert payload["gpu"] == {"id": module.GPU_ID, "count": 1}
                assert payload["cloud"] == "SECURE" and payload["disk"] == 10
                assert payload["mounts"] == {} and payload["ports"] == []
                assert not any(key in payload for key in ("cpu", "globalNetworking", "startSsh", "startJupyter", "template", "registry"))
                assert "RUNPOD_API_KEY" not in payload["env"]
                assert payload["image"] == module.IMAGE
                captures["created"] = True
                captures["payload_keys"] = sorted(payload)
                return Response({"id": "FAKE-POD", "gpu": {
                    "id": "OTHER" if case == "wrong-gpu" else module.GPU_ID,
                    "count": 2 if case == "two-gpus" else 1}, "image": module.IMAGE,
                    "cloud": "SECURE", "ports": ["22/tcp"] if case == "ports" else [],
                    "mounts": {}, "cost": 0.57} if status == 201 else {"title": "fake error"})

            def get(self, url, **kwargs):
                assert url == module.REST_V1 + "/pods/FAKE-POD"
                return Response({"costPerHr": 0.59 if case == "overprice" else float("nan") if case == "nan-price" else 0.57,
                                 "vcpuCount": 8, "memoryInGb": 2 if case == "too-little-ram" else 32,
                                 "containerDiskInGb": 10, "volumeInGb": 0, "ports": []})

            def delete(self, url, **kwargs):
                captures.setdefault("delete_urls", []).append(url)
                response = Response({})
                response.status_code = 204
                return response

        with patch.object(module, "session", lambda: Client()), \
             patch.object(module, "read_key", lambda: "FAKE-CREDENTIAL-NOT-READ-FROM-DISK"), \
             patch.object(module, "safe_pods", lambda client: []), \
             patch.object(module, "inventory_both", lambda client: {"v1": [], "v2": []}), \
             patch.object(module, "account_preflight", lambda client: 0.02 if case == "prior-budget" else 0), \
             patch.object(module, "catalog_offer", lambda client: ({"availability": "LOW"}, 0.57)), \
             patch.object(module.subprocess, "Popen", lambda *args, **kwargs: module.WATCHDOG_READY.write_text('{"fake":true}')), \
             patch.object(module, "collect_logs", lambda *args, **kwargs: (["FAKE-LOG"], [{"kind": "done", "status": "complete"}])), \
             patch.object(module, "extract_evidence", lambda lines: {"fake_client_evidence": True}), \
             contextlib.redirect_stdout(io.StringIO()):
            exit_code = module.run()
        record = json.loads(module.RUN_RECORD.read_text())
        assert record["creation_uncertain"] == (status == 500)
        assert module.WATCHDOG_DONE.exists() == (status != 500)
        assert exit_code == (0 if case == "success" else 1), (case, record)
        if case == "prior-budget":
            assert not captures.get("created") and not record["creation_attempted"]
        else:
            assert record["creation_http_status"] == status and captures["created"]
        if status == 201 and case != "prior-budget":
            assert module.POD_IDENTITY.exists() and record["terminated"]
            assert captures["delete_urls"][0] == module.REST_V2 + "/pods/FAKE-POD"
        results.append({"case": case, "status": "pass"})
    result = {"status": "pass", "evidence_class": "local fake-client checks, not Runpod workload evidence",
              "controller_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "source_files": len(manifest["files"]),
              "source_bytes": sum(row["bytes"] for row in manifest["files"]),
              "approved_source_hashes_match": True, "compressed_bundle_bytes": len(bundle), "remote_bootstrap_unchanged": True,
              "syntax": "pass", "network_calls": 0, "pod_creations": 0, "credentials_read": False,
              "cases": results, "fixture_directory": str(fixtures)}
    module.write_exclusive(ROOT / "GPU-CONTROLLER-CHECKS.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
