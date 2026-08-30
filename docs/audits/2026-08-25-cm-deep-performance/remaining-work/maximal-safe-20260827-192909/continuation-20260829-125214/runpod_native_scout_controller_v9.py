"""V9 native scout: V8 upload retry with same-file watchdog binding."""

from __future__ import annotations

import hashlib
from pathlib import Path

import http_native_scout_preflight_v9 as preflight
import runpod_native_scout_controller_v8 as v8


previous = v8.previous
HERE = Path(__file__).resolve().parent
OUT = HERE / "native-procfs-v9-001"
PROPOSAL = HERE / "RUNPOD-NATIVE-SCOUT-V8-WATCHDOG-BINDING-AMENDMENT-20260829.md"
AUTHORIZATION = HERE / "HTTP-NATIVE-SCOUT-V9-WATCHDOG-BINDING-AUTHORIZED-20260829.json"


def require_authorization():
    if not AUTHORIZATION.is_file():
        raise RuntimeError("V9 bounded-campaign authorization record is absent")
    value = previous.load(AUTHORIZATION)
    expected = {
        "schema": "cm-runpod-native-scout-v9-watchdog-binding-authorization/v1",
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
        "v8_creation_attempted": False,
    }
    if any(value.get(key) != expected_value for key, expected_value in expected.items()):
        raise RuntimeError("V9 authorization scope mismatch")
    if value.get("proposal_sha256") != hashlib.sha256(PROPOSAL.read_bytes()).hexdigest():
        raise RuntimeError("V9 authorized proposal hash mismatch")
    if value.get("upload_manifest_sha256") != hashlib.sha256(previous.MANIFEST_PATH.read_bytes()).hexdigest():
        raise RuntimeError("V9 upload manifest hash mismatch")
    return value


def configure() -> None:
    v8.configure()
    previous.__file__ = __file__
    previous.OUT = OUT
    previous.base.OUT = OUT
    previous.PROPOSAL_PATH = PROPOSAL
    previous.AUTHORIZATION_PATH = AUTHORIZATION
    previous.preflight = preflight
    previous.STATE = OUT / "controller-state.json"
    previous.IDENTITY = OUT / "POD-IDENTITY.json"
    previous.READY = OUT / "watchdog-ready.json"
    previous.STATE_ACK = OUT / "watchdog-state-ack.json"
    previous.DONE = OUT / "watchdog-done.json"
    previous.ABORT = OUT / "abort-requested.json"
    previous.require_authorization = require_authorization


def main() -> int:
    configure()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
