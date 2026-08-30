"""Read-only V12 preflight preserving the concurrent V11 no-create refusal."""

from __future__ import annotations

from pathlib import Path
import json

import http_native_scout_preflight_v11 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
V11_OUTPUT = HERE / "native-procfs-v11-001"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = json.loads((V11_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    if (
        saved.get("status") != "failed"
        or saved.get("error") != "native-scout authorization scope mismatch"
        or saved.get("creation_attempted") is not False
        or saved.get("pod_created") is not False
        or saved.get("uploaded_source_files") != 0
    ):
        raise RuntimeError("V11 no-create authorization refusal is not preserved")
    result = previous.check()
    result["v11_no_create_refusal_preserved"] = True
    result["v11_cloud_create_consumed"] = False
    result["authorized_aggregate_campaign_cap_usd"] = 10.0
    return result
