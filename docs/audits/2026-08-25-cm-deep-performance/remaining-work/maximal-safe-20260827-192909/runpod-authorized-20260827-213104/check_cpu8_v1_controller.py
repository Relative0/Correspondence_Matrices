"""Trivial offline checks; all resource responses are fake, with no credentials read."""
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
    path = ROOT / "runpod_retry_cpu8_v1_controller.py"
    module = load("v1_check", path.name)
    base = load("v2_check", "runpod_retry_cpu8_controller.py")
    ast.parse(path.read_text())
    compile(module.REMOTE_CODE, "<remote-bootstrap>", "exec")
    assert module.REMOTE_CODE == base.REMOTE_CODE
    manifest = json.loads(module.MANIFEST_PATH.read_text())
    bundle = module.make_bundle(manifest)
    fixtures = ROOT / ("cpu8-v1-fake-client-" + uuid.uuid4().hex[:8])
    fixtures.mkdir()
    results = []
    for status in (400, 500, 201):
        module.OUT = fixtures / str(status)
        module.OUT.mkdir()
        for attribute, filename in (("STATE", "controller-state.json"), ("POD_IDENTITY", "POD-IDENTITY.json"),
                                    ("WATCHDOG_READY", "watchdog-ready.json"), ("WATCHDOG_DONE", "watchdog-done"),
                                    ("RUN_RECORD", "RUN.json")):
            setattr(module, attribute, module.OUT / filename)
        captures = {}

        class Response:
            status_code = status
            headers = {"X-Request-Id": "FAKE-CLIENT-NOT-A-REAL-POD"}

            def __init__(self, body=None):
                self.body = body

            def json(self):
                return self.body if self.body is not None else ({"id": "FAKE-POD"} if status == 201 else {"title": "fake error"})

            def raise_for_status(self):
                pass

        class Client:
            def post(self, url, **kwargs):
                assert url == module.REST_V1 + "/pods"
                payload = kwargs["json"]
                assert payload["computeType"] == "CPU" and payload["cpuFlavorIds"] == ["cpu3c"] and payload["vcpuCount"] == 8
                assert payload["containerDiskInGb"] == 10 and payload["volumeInGb"] == 0 and payload["ports"] == []
                assert not any(key in payload for key in ("globalNetworking", "startSsh", "startJupyter", "gpu", "gpuTypeIds", "templateId", "mounts"))
                assert "RUNPOD_API_KEY" not in payload["env"]
                assert payload["imageName"] == module.IMAGE and payload["dockerEntrypoint"] == ["python", "-u", "-c"]
                compile(payload["dockerStartCmd"][0], "<bootstrap-command>", "exec")
                captures["payload_keys"] = list(payload)
                return Response()

            def get(self, url, **kwargs):
                assert url == module.REST_V1 + "/pods/FAKE-POD"
                return Response({"costPerHr": 0.24, "cpuFlavorId": "cpu3c", "vcpuCount": 8,
                                 "memoryInGb": 16, "containerDiskInGb": 10, "volumeInGb": 0})

            def delete(self, url, **kwargs):
                captures.setdefault("delete_urls", []).append(url)
                response = Response({})
                response.status_code = 204
                return response

        with patch.object(module, "session", lambda: Client()), \
             patch.object(module, "read_key", lambda: "FAKE-CREDENTIAL-NOT-READ-FROM-DISK"), \
             patch.object(module, "safe_pods", lambda client: []), \
             patch.object(module, "catalog_offer", lambda client: ({"availability": "HIGH"}, 0.24, 16)), \
             patch.object(module.subprocess, "Popen", lambda *args, **kwargs: module.WATCHDOG_READY.write_text('{"fake":true}')), \
             patch.object(module, "collect_logs", lambda *args, **kwargs: (["FAKE-LOG"], [{"kind": "done", "status": "complete"}])), \
             patch.object(module, "extract_evidence", lambda lines: {"fake_client_evidence": True}), \
             contextlib.redirect_stdout(io.StringIO()):
            exit_code = module.run()
        record = json.loads(module.RUN_RECORD.read_text())
        assert record["creation_http_status"] == status and record["creation_endpoint"] == module.REST_V1 + "/pods"
        assert record["creation_uncertain"] == (status == 500)
        assert module.WATCHDOG_DONE.exists() == (status != 500)
        assert exit_code == (0 if status == 201 else 1)
        if status == 201:
            assert record["terminated"] and captures["delete_urls"][0] == module.REST_V1 + "/pods/FAKE-POD"
        results.append({"http_case": status, "status": "pass", "payload_keys": captures["payload_keys"]})
    result = {"status": "pass", "evidence_class": "local fake-client checks, not Runpod workload evidence",
              "controller_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "source_files": len(manifest["files"]),
              "approved_source_hashes_match": True, "compressed_bundle_bytes": len(bundle), "remote_bootstrap_unchanged": True,
              "syntax": "pass", "network_calls": 0, "pod_creations": 0, "credentials_read": False,
              "cases": results, "fixture_directory": str(fixtures)}
    module.write_exclusive(ROOT / "CPU8-V1-CONTROLLER-CHECKS.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
