"""Read-only V15 preflight preserving V14's no-create receipt."""

from __future__ import annotations

from pathlib import Path
import json

import http_native_gap_preflight_v14 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
V14_OUTPUT = HERE / "native-gap-v14-001"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = json.loads((V14_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    if (
        saved.get("status") != "failed"
        or saved.get("creation_attempted") is not False
        or saved.get("pod_created") is not False
        or saved.get("uploaded_source_files") != 0
        or saved.get("error_type") != "ReadTimeout"
        or saved.get("pod_id") is not None
    ):
        raise RuntimeError("V14 no-create receipt is not reconciled")
    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before V15")
    result["v14_no_create_reconciled"] = True
    result["current_inventories"] = current
    result["authorized_aggregate_campaign_cap_usd"] = 10.0
    return result
