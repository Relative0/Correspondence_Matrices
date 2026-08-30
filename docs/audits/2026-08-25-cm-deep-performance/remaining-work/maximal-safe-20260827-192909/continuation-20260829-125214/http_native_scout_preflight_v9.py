"""Read-only preflight preserving the no-create V8 watchdog refusal."""

from __future__ import annotations

from pathlib import Path

import http_native_scout_preflight_v8 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
V8_OUTPUT = HERE / "native-procfs-v8-001"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = previous.previous.previous.load(V8_OUTPUT / "RUN.json")
    if (
        saved.get("status") != "failed"
        or saved.get("error") != "watchdog exited before readiness"
        or saved.get("creation_attempted") is not False
        or saved.get("pod_created") is not False
        or saved.get("uploaded_source_files") != 0
    ):
        raise RuntimeError("V8 local watchdog refusal is not preserved")
    result = previous.check()
    result["v8_local_watchdog_refusal_preserved"] = True
    result["v8_cloud_create_consumed"] = False
    return result
