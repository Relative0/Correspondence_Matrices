import json

from scripts import cm_benchmark_runpod_controller as controller


def test_upload_retries_transient_404(monkeypatch):
    calls = []
    row = {"sha256": "a" * 64}

    def fake_proxy(*args, **kwargs):
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("proxy HTTP 404")
        return json.dumps({"accepted_sha256": row["sha256"]}).encode()

    monkeypatch.setattr(controller, "proxy", fake_proxy)
    monkeypatch.setattr(controller.time, "sleep", lambda _: None)
    history = controller.upload_shard(object(), "https://example", 1, row, b"data")
    assert len(calls) == 3
    assert history[-1] == {"attempt": 3, "status": "accepted"}


def test_upload_does_not_retry_digest_mismatch(monkeypatch):
    monkeypatch.setattr(controller, "proxy", lambda *args, **kwargs: b'{"accepted_sha256":"bad"}')
    try:
        controller.upload_shard(object(), "https://example", 1, {"sha256": "good"}, b"data")
    except RuntimeError as exc:
        assert str(exc) == "shard acknowledgement mismatch"
    else:
        raise AssertionError("digest mismatch must fail closed")
