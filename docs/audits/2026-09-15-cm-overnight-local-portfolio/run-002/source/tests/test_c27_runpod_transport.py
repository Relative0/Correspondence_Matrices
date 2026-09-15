from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import time


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = (
    ROOT / "docs/recognition/c27_linux_confirmation/runpod_c27_linux_controller.py"
)


def load_controller():
    spec = importlib.util.spec_from_file_location("c27_transport_test", CONTROLLER)
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    return controller


def test_payload_retry_survives_transient_proxy_404_health_recheck(
        monkeypatch, tmp_path):
    controller = load_controller()
    controller.OUT = tmp_path
    raw = b"frozen-c27-payload"
    calls: list[tuple[str, str]] = []
    payload_posts = 0
    health_gets = 0

    class Session:
        def __init__(self):
            self.headers = {}
            self.trust_env = True

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def proxy_request(_session, method, url, **_kwargs):
        nonlocal payload_posts, health_gets
        calls.append((method, url.rsplit("/", 1)[-1]))
        if method == "GET" and url.endswith("/health"):
            health_gets += 1
            if health_gets == 3:
                raise RuntimeError("proxy HTTP 404")
            return json.dumps({"service": "cm-memory-http", "ready": True}).encode()
        if method == "POST" and url.endswith("/payload"):
            payload_posts += 1
            if payload_posts == 1:
                raise RuntimeError("proxy HTTP 404")
            return json.dumps({
                "accepted_sha256": hashlib.sha256(raw).hexdigest(),
            }).encode()
        if method == "POST" and url.endswith("/run"):
            return b"{}"
        if method == "GET" and url.endswith("/progress"):
            return json.dumps({
                "stage": "c27-linux-verification", "done": True, "error": None,
            }).encode()
        if method == "GET" and url.endswith("/results"):
            return b"bounded-results"
        raise AssertionError((method, url))

    monkeypatch.setattr(controller.shared.requests, "Session", Session)
    monkeypatch.setattr(controller.shared, "proxy_request", proxy_request)
    monkeypatch.setattr(controller.time, "sleep", lambda _seconds: None)
    record = {}

    result = controller.execute_remote(
        "pod-id", "token", raw, time.time(), record)

    assert result == "bounded-results"
    assert payload_posts == 2
    assert record["uploaded_source_files"] == 63
    assert record["payload_attempts"] == [
        {
            "attempt": 1,
            "checked_utc": record["payload_attempts"][0]["checked_utc"],
            "status": "proxy HTTP 404",
            "health_recheck": "RuntimeError",
            "health_recheck_status": "proxy HTTP 404",
        },
        {
            "attempt": 2,
            "checked_utc": record["payload_attempts"][1]["checked_utc"],
            "status": "accepted",
        },
    ]
    assert ("POST", "payload") in calls
