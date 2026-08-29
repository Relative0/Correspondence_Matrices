"""Trivial offline fake-client checks; no credentials, sockets, or workloads."""
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch
import uuid

import http_transport_bootstrap as server
import runpod_structural_controller_v4 as controller


def main():
    c = controller
    original_out = c.OUT
    fixture = c.HERE / ("http-structural-fake-checks-" + uuid.uuid4().hex[:8])
    fixture.mkdir()
    results = []
    # Publication is complete and refuses to replace existing evidence.
    atomic = fixture / "atomic.json"
    original_link = c.os.link
    published = []
    def checked_link(source, target):
        assert not target.exists()
        assert json.loads(source.read_text(encoding="utf-8")) == {"complete": True}
        published.append(True)
        return original_link(source, target)
    with patch.object(c.os, "link", checked_link):
        c.write(atomic, {"complete": True})
    assert published == [True] and c.load(atomic) == {"complete": True}
    try:
        c.write(atomic, {"complete": False})
        raise AssertionError("existing evidence was overwritten")
    except FileExistsError:
        pass
    assert c.load(atomic) == {"complete": True}
    c.STATE_ACK = fixture / "ack.json"
    with patch.object(c.time, "sleep", lambda seconds: None):
        for process in (SimpleNamespace(pid=123, poll=lambda: 0), SimpleNamespace(pid=123, poll=lambda: None)):
            try:
                c.confirm_watchdog(process, {"fake_state": True})
                raise AssertionError("unacknowledged/dead watchdog accepted")
            except RuntimeError:
                pass
    c.write(c.STATE_ACK, {"state": {"fake_state": True}, "pid": 123})
    c.confirm_watchdog(SimpleNamespace(pid=123, poll=lambda: None), {"fake_state": True})
    try:
        c.confirm_watchdog(SimpleNamespace(pid=456, poll=lambda: None), {"fake_state": True})
        raise AssertionError("wrong watchdog process accepted")
    except RuntimeError:
        pass
    results.append({"case": "atomic-no-overwrite-publication-and-watchdog-state-ack", "status": "pass"})
    manifest = c.load(c.base.MANIFEST_PATH)
    bundle = c.base.make_bundle(manifest)
    raw = c.prepare_payload(bundle, manifest, 1000)
    for filename in ("http_transport_bootstrap.py", "http_structural_preflight_v3.py", "runpod_structural_controller_v4.py"):
        ast.parse((c.HERE / filename).read_text(encoding="utf-8"))
    server.EXPECTED_SIZE = len(raw)
    server.EXPECTED_HASH = hashlib.sha256(raw).hexdigest()
    payload = server.validate_payload(raw)
    preserved = __import__("runpod_retry_cpu8_controller").REMOTE_CODE
    assert c.base.REMOTE_CODE != preserved
    assert hashlib.sha256((c.HERE / "runpod_http_smoke_controller_v3.py").read_bytes()).hexdigest() == \
           "3296099d0d6c30e83698d1638d7cdc4001fd9158ffce3d68d0d599ee44d4654f"
    assert "'--supports', '6', '8', '12', '16', '--families'" in c.base.REMOTE_CODE
    assert "'mixed-chain', 'shared-diamond', 'wide-and', 'alternating-tree'" in c.base.REMOTE_CODE
    assert "'reconvergent-xor', '--contexts', 'none'" in c.base.REMOTE_CODE
    assert "'--output-dir', str(OUT/'structural')], 600)" in c.base.REMOTE_CODE
    assert "OUT / 'structural/summary.json'" in c.base.REMOTE_CODE
    assert "OUT/'memory'" not in c.base.REMOTE_CODE and "memory/summary.json" not in c.base.REMOTE_CODE
    assert __import__("base64").b64decode(payload["code"]).decode() == c.base.REMOTE_CODE
    for bad in (raw[:-1], b"x" + raw[1:]):
        try:
            server.validate_payload(bad)
            raise AssertionError("corrupt payload accepted")
        except ValueError:
            pass
    with patch.object(server.os, "environ", {"PATH": "/usr/bin", "RUNPOD_POD_ID": "fakepod0123",
                "RUNPOD_API_KEY": "PRIVATE_SENTINEL", "CM_BOOTSTRAP_TOKEN": "PRIVATE_SENTINEL"}):
        env = server.child_environment(payload)
        assert "PRIVATE_SENTINEL" not in json.dumps(env)
        assert "RUNPOD_API_KEY" not in env and "CM_BOOTSTRAP_TOKEN" not in env
        assert env["RUNPOD_POD_ID"] == "fakepod0123"
    results.append({"case": "source-hashes-frozen-code-upload-hash-child-credentials", "status": "pass"})

    server.TOKEN = "OFFLINE_TOKEN_ONLY_0123456789"
    server.DEADLINE = 99999999999
    replies = []
    def handler(path, port, token=None, content=b""):
        obj = object.__new__(server.Handler)
        obj.path = path
        obj.server = SimpleNamespace(server_port=port)
        obj.headers = {"Content-Length": str(len(content))}
        if token is not None:
            obj.headers["X-CM-Token"] = token
        obj.rfile = io.BytesIO(content)
        obj.reply = lambda status, body, *args: replies.append((status, body))
        return obj
    for method, path, port in (("GET", "/progress", 8081), ("GET", "/results", 8081),
                               ("POST", "/payload", 8080), ("POST", "/run", 8081)):
        obj = handler(path, port)
        getattr(obj, "do_" + method)()
        assert replies[-1][0] == 403
    handler("/health", 8080).do_GET()
    assert replies[-1] == (200, {"service": "cm-memory-http", "ready": True})
    handler("/payload", 8080, server.TOKEN, raw).do_POST()
    assert replies[-1][0] == 200
    starts = []
    with patch.object(server.threading, "Thread", lambda **kwargs: SimpleNamespace(start=lambda: starts.append(True))):
        handler("/run", 8081, server.TOKEN).do_POST()
        handler("/run", 8081, server.TOKEN).do_POST()
        assert len(starts) == 1 and replies[-1][0] == 202
    handler("/payload", 8080, server.TOKEN, raw).do_POST()
    assert replies[-1][0] == 409
    handler("/run", 8081, server.TOKEN, b"unapproved command").do_POST()
    assert replies[-1][0] == 400
    results.append({"case": "endpoint-authentication-health-and-run-idempotency", "status": "pass"})

    class FakeProcess:
        pid = 123456
        stdout = io.BytesIO()
        calls = 0
        def wait(self, timeout):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("fake", timeout)
            return -9
        def poll(self): return -9
    kills = []
    server.STATE = {"done": False, "error": None}
    with patch.object(server.subprocess, "Popen", lambda *args, **kwargs: FakeProcess()), \
         patch.object(server, "kill_worker", lambda proc: kills.append(proc.pid)):
        server.run_worker(payload)
    assert kills == [123456] and server.STATE["error"] == "worker lifetime exceeded" and server.STATE["done"]
    results.append({"case": "worker-timeout-kills-only-owned-process", "status": "pass"})

    success_cases = ("success", "current-v1-shape", "v2-cloud-fallback")
    for case in (*success_cases, "http400", "http500", "wrong-image", "wrong-ports", "wrong-volume", "overprice", "nan-price", "wrong-cpu", "low-ram", "upload-timeout", "delete-failure", "preflight-failed", "conflicting-image", "conflicting-cloud", "unknown-cloud", "gpu-present", "wrong-compute-type"):
        c.OUT = fixture / case
        c.OUT.mkdir()
        c.base.OUT = c.OUT
        for attribute, name in (("STATE", "controller-state.json"), ("IDENTITY", "POD-IDENTITY.json"),
                               ("READY", "watchdog-ready.json"), ("STATE_ACK", "watchdog-state-ack.json"),
                               ("DONE", "watchdog-done.json"), ("ABORT", "abort-requested.json")):
            setattr(c, attribute, c.OUT / name)
        captures = {"created": 0, "deleted": [], "allocated": False, "uploaded": False}
        offer = {"id": "cpu3c", "rate_usd_per_hour": 0.06, "eligible": True}
        readiness = {"ready": case != "preflight-failed", "selected_offer": offer, "observed_previous_cost_usd": 0,
                     "prior_cost_bound_usd": 0.02}

        class Response:
            headers = {"X-Request-Id": "OFFLINE_FAKE_REQUEST"}
            def __init__(self, status, body): self.status_code, self.body = status, body
            def json(self): return self.body
            def raise_for_status(self):
                if self.status_code >= 400: raise c.requests.HTTPError("fake")

        class Client:
            headers = {"Authorization": "Bearer OFFLINE_CREDENTIAL_ONLY"}
            def post(self, url, **kwargs):
                assert url == c.preflight.V1 + "/pods"
                captures["created"] += 1
                assert captures["created"] == 1
                body = kwargs["json"]
                captures["name"] = body["name"]
                captures["token"] = body["env"]["CM_BOOTSTRAP_TOKEN"]
                assert body["ports"] == c.EXPECTED_PORTS and body["volumeInGb"] == 0
                assert body["containerDiskInGb"] == 12 and body["vcpuCount"] == 2
                assert body["imageName"] == c.base.IMAGE
                assert len(body["env"]) == 4 and "RUNPOD_API_KEY" not in body["env"]
                assert not any(key.startswith("CM_BUNDLE") for key in body["env"])
                if case.startswith("http"):
                    return Response(int(case[4:]), {"detail": "OFFLINE_CREDENTIAL_ONLY " + captures["token"]})
                captures["allocated"] = True
                return Response(201, {"id": "fakepod0123", "name": body["name"]})
            def get(self, url, **kwargs):
                if url.endswith("/pods"):
                    return Response(200, [{"id": "fakepod0123", "name": captures["name"]}] if captures["allocated"] else [])
                if url == c.preflight.V2 + "/pods/fakepod0123":
                    return Response(200, {"id": "fakepod0123", "cloud": "SECURE" if case == "v2-cloud-fallback" else None})
                assert url == c.preflight.V1 + "/pods/fakepod0123"
                pod = {"id": "fakepod0123", "name": captures["name"], "computeType": "CPU", "cloudType": "SECURE",
                       "cpuFlavorId": "cpu3c", "vcpuCount": 2, "memoryInGb": 4, "costPerHr": 0.06,
                       "imageName": c.base.IMAGE, "containerDiskInGb": 12, "volumeInGb": 0,
                       "volumeMountPath": "/workspace", "ports": c.EXPECTED_PORTS}
                changes = {"wrong-image": ("imageName", "other"), "wrong-ports": ("ports", ["22/tcp"]),
                           "wrong-volume": ("volumeInGb", 11), "overprice": ("costPerHr", 0.30),
                           "nan-price": ("costPerHr", float("nan")), "wrong-cpu": ("cpuFlavorId", "cpu3m"),
                           "low-ram": ("memoryInGb", 2)}
                if case in changes: pod[changes[case][0]] = changes[case][1]
                if case in ("current-v1-shape", "v2-cloud-fallback", "unknown-cloud"):
                    pod["image"] = pod.pop("imageName")
                    pod.pop("computeType")
                    pod.pop("cloudType")
                    if case == "current-v1-shape": pod["machine"] = {"secureCloud": True}
                if case == "conflicting-image": pod["image"] = "unexpected-image"
                if case == "conflicting-cloud": pod["machine"] = {"secureCloud": False}
                if case == "gpu-present": pod["gpu"] = {"id": "UNAPPROVED_GPU", "count": 1}
                if case == "wrong-compute-type": pod["computeType"] = "GPU"
                return Response(200, pod)
            def delete(self, url, **kwargs):
                assert url.endswith("/pods/fakepod0123")
                captures["deleted"].append(url)
                if case == "delete-failure": return Response(500, {})
                captures["allocated"] = False
                return Response(204, {})
            def close(self): pass

        def execute(*args):
            captures["uploaded"] = True
            if case == "upload-timeout": raise c.requests.Timeout("PRIVATE_SENTINEL")
            return "FAKE_LOG_ONLY"
        with patch.object(c.preflight, "check", lambda: readiness), \
             patch.object(c.preflight, "session", lambda: Client()), \
             patch.object(c, "arm_watchdog", lambda: None), \
             patch.object(c, "confirm_watchdog", lambda proc, state: None), \
             patch.object(c, "execute_remote", execute), \
             patch.object(c, "save_evidence", lambda log: {"fake_evidence": True}), \
             patch.object(c.time, "sleep", lambda seconds: None), \
             contextlib.redirect_stdout(io.StringIO()):
            code = c.run()
        record = c.load(c.OUT / "RUN.json")
        assert code == (0 if case in success_cases else 1), (case, record)
        assert captures["created"] == (0 if case == "preflight-failed" else 1)
        assert record["creation_uncertain"] == (case == "http500")
        assert c.DONE.exists() == (case not in ("http500", "delete-failure"))
        if case not in ("http400", "http500", "preflight-failed"):
            assert captures["deleted"] and c.IDENTITY.exists()
        if case in ("wrong-image", "wrong-ports", "wrong-volume", "overprice", "nan-price", "wrong-cpu", "low-ram", "conflicting-image", "conflicting-cloud", "unknown-cloud", "gpu-present", "wrong-compute-type"):
            assert not captures["uploaded"]
        serialized = json.dumps(record)
        assert "PRIVATE_SENTINEL" not in serialized and "OFFLINE_CREDENTIAL_ONLY" not in serialized
        assert captures.get("token", "NEVER_GENERATED") not in serialized
        results.append({"case": case, "status": "pass"})
    # A conflicting ownership name must never cause a deletion.
    try:
        c.find_owned({"v1": [{"id": "a12345678", "name": "same"}], "v2": [{"id": "b12345678", "name": "same"}]}, {"name": "same"})
        raise AssertionError("ambiguous ownership accepted")
    except RuntimeError:
        pass
    results.append({"case": "ambiguous-ownership-refused", "status": "pass"})
    result = {"status": "passed", "evidence_class": "offline fake clients, not cloud workload evidence",
              "network_requests": 0, "credentials_read": False, "source_hashes_match": True,
              "authorized_remote_transformation_exact": True, "cases": results, "fixture_directory": str(fixture)}
    c.write(c.HERE / ("HTTP-STRUCTURAL-TRANSPORT-CHECKS-" + uuid.uuid4().hex[:8] + ".json"), result)
    print(json.dumps(result, indent=2))


def structural_checks():
    c, p = controller, controller.preflight
    results = []

    def refused(label, operation):
        try:
            operation()
        except (ValueError, RuntimeError):
            results.append({"case": label, "status": "pass"})
        else:
            raise AssertionError(label + " was accepted")

    def metadata(total=0, count=0, unique=0):
        return {"query": {"grouping": "podId"}, "recordCount": count, "uniquePodCount": unique,
                "totals": {"cpuAmount": total, "gpuAmount": 0, "diskAmount": 0, "totalAmount": total}}

    def rows(value, pod_id="eidn8uu97y3b6q"):
        return [{"podId": pod_id, "amount": value, "time": "2026-08-28T00:00:00Z"}]

    assert p.prior_attempts()["pod_ids"] == sorted(p.PRIOR_POD_IDS)
    assert p.analyze_billing(metadata(), [])["prior_cost_bound_usd"] == 0.02
    assert p.analyze_billing(metadata(0.0001, 1, 1), rows(0.0001))["prior_cost_bound_usd"] == 0.02
    assert p.analyze_billing(metadata(0.03, 1, 1), rows(0.03, "s2dpiij1msutml"))["prior_cost_bound_usd"] == 0.03
    split = p.analyze_billing(metadata(0.05, 1, 1), rows(0.05, "unrelated-pod"))
    assert split["prior_cost_bound_usd"] == 0.02 and not split["attributed_rows"]
    assert len(split["unrelated_account_rows"]) == 1
    component_row = [{"podId": "eidn8uu97y3b6q", "cpuAmount": 0.001, "gpuAmount": 0,
                      "diskAmount": 0, "totalAmount": 0.001,
                      "startTime": "2026-08-28T00:00:00Z", "endTime": "2026-08-29T00:00:00Z"}]
    assert p.analyze_billing(metadata(0.001, 1, 1), component_row)["record_source"] == "v2_metadata_and_records"
    refused("v2-row-component-mismatch", lambda: p.analyze_billing(metadata(0.002, 1, 1), component_row))
    results.append({"case": "two-prior-allocations-preserved-billing-reserved-and-unrelated-split", "status": "pass"})
    refused("missing-pod-attribution", lambda: p.analyze_billing(metadata(0.01, 1, 1), [{"amount": 0.01}]))
    refused("unreconciled-record-count", lambda: p.analyze_billing(metadata(0.01, 2, 1), rows(0.01)))
    refused("unreconciled-unique-count", lambda: p.analyze_billing(metadata(0.01, 1, 0), rows(0.01)))
    refused("unreconciled-total", lambda: p.analyze_billing(metadata(0.02, 1, 1), rows(0.01)))
    for value in (-1, float("nan"), float("inf"), True):
        refused("invalid-billing-amount-" + str(value), lambda value=value: p.analyze_billing(metadata(value, 1, 1), rows(value)))
    refused("boolean-record-count", lambda: p.analyze_billing(metadata(0, True, 1), rows(0)))
    assert p.budget(0.25, 0.02)["ready"]
    assert p.budget(0.06, 0.176)["ready"]
    for rate, prior in ((0.06, 0), (0.06, 0.18), (0.25001, 0.02), (0, 0.02)):
        assert not p.budget(rate, prior)["ready"]
    results.append({"case": "phase-campaign-price-caps-and-two-attempt-reserve", "status": "pass"})
    refused("nonfinite-budget", lambda: p.budget(float("nan"), 0.02))

    pod = {"id": "fakepod0123", "name": "fake-name", "cloudType": "SECURE", "cpuFlavorId": "cpu3c",
           "vcpuCount": 2, "memoryInGb": 4, "costPerHr": 0.06, "imageName": c.base.IMAGE,
           "containerDiskInGb": 12, "volumeInGb": 0, "volumeMountPath": "/workspace", "ports": c.EXPECTED_PORTS}
    with patch.object(c, "load", lambda path: {"pod_id": "fakepod0123"}):
        validate = lambda value, prior=0.02: c.validate_pod(value, {"name": "fake-name"}, {"id": "cpu3c"}, prior)
        assert validate(pod)["pod_volume_gb"] == 0
        for value in (None, False, -1, 1, 10, "0"):
            refused("nonzero-or-malformed-volume-" + str(value), lambda value=value: validate({**pod, "volumeInGb": value}))
        refused("actual-price-exhausts-campaign-cap", lambda: validate({**pod, "costPerHr": 0.25}, 0.12))
        refused("actual-resource-validation-requires-prior-reserve", lambda: validate(pod, 0))
        refused("network-volume-not-authorized", lambda: validate({**pod, "networkVolume": {"id": "unrelated-volume"}}))

    class Response:
        def __init__(self, body): self.body = body
        def json(self): return self.body
        def raise_for_status(self): pass

    for case in ("ready-zero-bill", "ready-attributed-bill", "ready-unrelated-bill", "active-pod", "low-credit", "low-spend-limit", "over-budget"):
        billed = 0.18 if case == "over-budget" else 0.05 if case == "ready-unrelated-bill" else 0.0001 if case == "ready-attributed-bill" else 0
        billed_pod = "unrelated-pod" if case == "ready-unrelated-bill" else "eidn8uu97y3b6q"
        class Client:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def get(self, url, **kwargs):
                if url.endswith("/pods") and "/billing/" not in url:
                    return Response([{"id": "unrelated-pod", "name": "unrelated"}] if case == "active-pod" else [])
                assert url == p.V2 + "/billing/pods"
                assert kwargs["params"]["grouping"] == "podId"
                billed_rows = rows(billed, billed_pod) if billed else []
                return Response({"metadata": metadata(billed, 1, 1) if billed else metadata(), "records": billed_rows})
            def post(self, url, **kwargs):
                assert url == "https://api.runpod.io/graphql"
                assert kwargs["json"]["query"].startswith("query ")
                return Response({"data": {"myself": {"clientBalance": 0 if case == "low-credit" else 1,
                    "spendLimit": 0 if case == "low-spend-limit" else 1, "currentSpendPerHr": 0}}})
        with patch.object(p, "session", lambda: Client()), patch.object(p, "get_offer", lambda flavor: {
                "id": flavor, "rate_usd_per_hour": 0.06, "eligible": True, "availability": "HIGH"}):
            checked = p.check()
        assert checked["ready"] == case.startswith("ready-"), (case, checked)
        assert checked["resource_writes"] == 0
        results.append({"case": "fake-preflight-" + case, "status": "pass"})

    report = {"status": "passed", "cases": results, "network_requests": 0, "credentials_read": False,
              "workload_executed": False, "controller_sha256": hashlib.sha256(Path(c.__file__).read_bytes()).hexdigest(),
              "preflight_sha256": hashlib.sha256(Path(p.__file__).read_bytes()).hexdigest()}
    c.write(c.HERE / ("HTTP-STRUCTURAL-BUDGET-CHECKS-" + uuid.uuid4().hex[:8] + ".json"), report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    # Reuse the validated v2 binding checks and real trivial child probe.
    import check_http_transport_v2 as binding_checks
    binding_checks.controller = controller
    binding_checks.checks = sys.modules[__name__]
    binding_checks.main()
    structural_checks()
