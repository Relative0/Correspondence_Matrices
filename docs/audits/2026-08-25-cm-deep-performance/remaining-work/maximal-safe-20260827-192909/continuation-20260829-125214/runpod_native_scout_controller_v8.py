"""One-create native scout with bounded retry of read-only upload-status 404s."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import requests

import http_native_scout_preflight_v8 as preflight
import runpod_native_scout_controller_v7 as previous


HERE = Path(__file__).resolve().parent
OUT = HERE / "native-procfs-v8-001"
PROPOSAL = HERE / "RUNPOD-NATIVE-SCOUT-UPLOAD-404-RETRY-PROPOSAL-20260829.md"
AUTHORIZATION = HERE / "HTTP-NATIVE-SCOUT-UPLOAD-404-RETRY-AUTHORIZED-20260829.json"


def require_authorization():
    if not AUTHORIZATION.is_file():
        raise RuntimeError("V8 bounded-campaign authorization record is absent")
    value = previous.load(AUTHORIZATION)
    expected = {
        "schema": "cm-runpod-native-scout-upload-404-retry-authorization/v1",
        "authorized": True,
        "one_create": True,
        "phase_cap_usd": 0.10,
        "aggregate_campaign_cap_usd": 10.0,
        "container_disk_gb": 12,
        "pod_volume_gb": 0,
        "network_volume": False,
        "lifetime_seconds": 1200,
        "chunk_bytes": previous.CHUNK_BYTES,
        "source_files": 37,
        "focused_tests": 63,
        "p5_smoke_cells": 144,
        "performance_ranking": False,
        "v7_failed_pod_id": "3o7r0za7cm72yn",
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise RuntimeError("V8 authorization scope mismatch")
    if value.get("proposal_sha256") != hashlib.sha256(PROPOSAL.read_bytes()).hexdigest():
        raise RuntimeError("V8 authorized proposal hash mismatch")
    if value.get("upload_manifest_sha256") != hashlib.sha256(previous.MANIFEST_PATH.read_bytes()).hexdigest():
        raise RuntimeError("V8 upload manifest hash mismatch")
    return value


def upload_payload(proxy, boot, raw, deadline):
    """Retry only GET status 404s; preserve V7 POST reconciliation rules."""
    original = previous.proxy_request

    def status_tolerant(client, method, url, **kwargs):
        while True:
            try:
                return original(client, method, url, **kwargs)
            except RuntimeError as exc:
                if method != "GET" or str(exc) != "proxy HTTP 404" or time.time() + 2 >= deadline:
                    raise
                time.sleep(2)

    previous.proxy_request = status_tolerant
    try:
        return previous._upload_payload_v7(proxy, boot, raw, deadline)
    finally:
        previous.proxy_request = original


def configure() -> None:
    previous.OUT = OUT
    previous.base.OUT = OUT
    previous.PROPOSAL_PATH = PROPOSAL
    previous.AUTHORIZATION_PATH = AUTHORIZATION
    previous.preflight = preflight
    previous.CAMPAIGN_CAP = 10.0
    previous.STATE = OUT / "controller-state.json"
    previous.IDENTITY = OUT / "POD-IDENTITY.json"
    previous.READY = OUT / "watchdog-ready.json"
    previous.STATE_ACK = OUT / "watchdog-state-ack.json"
    previous.DONE = OUT / "watchdog-done.json"
    previous.ABORT = OUT / "abort-requested.json"
    previous.require_authorization = require_authorization
    previous._upload_payload_v7 = previous.upload_payload
    previous.upload_payload = upload_payload


def main() -> int:
    configure()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
