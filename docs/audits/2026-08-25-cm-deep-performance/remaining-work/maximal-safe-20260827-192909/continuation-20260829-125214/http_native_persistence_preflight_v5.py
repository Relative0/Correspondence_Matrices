"""Read-only native-persistence V5 preflight preserving and reconciling V4."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import zipfile

import http_native_persistence_preflight_v4 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
V6_AUTHORIZATION = previous.V6_AUTHORIZATION
LOCAL_FAILURE = previous.LOCAL_FAILURE
V4_OUTPUT = HERE / "native-persistence-v4-001"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check
host_ac_connected = previous.host_ac_connected


def check():
    saved = json.loads((V4_OUTPUT / "RUN.json").read_text(encoding="utf-8"))
    cleanup = saved.get("cleanup", {})
    archive_path = V4_OUTPUT / "evidence.zip"
    if (
        saved.get("status") != "failed"
        or saved.get("error_type") != "FileExistsError"
        or saved.get("pod_id") != "vlfvhjewad21xf"
        or cleanup.get("owned_pod_absent") is not True
        or cleanup.get("inventories") != {"v1": [], "v2": []}
        or archive_path.stat().st_size != 36749
        or hashlib.sha256(archive_path.read_bytes()).hexdigest()
        != "30b6fdec25258b53f290da66bf8d074bd5012f4c6c21cb7c6b4c35961b808ee3"
    ):
        raise RuntimeError("native persistence V4 result is not reconciled")
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        folded = [name.lower() for name in names]
        validation = json.loads(archive.read("run-output/REMOTE-VALIDATION.json"))
        d4 = json.loads(archive.read("run-output/D4-BUILD.json"))
    if (
        len(folded) - len(set(folded)) != 1
        or folded.count("run-output/d4-build.json") != 2
        or validation.get("error") != "RuntimeError: focused-tests failed with exit code 1"
        or validation.get("junit_testcases")
        != {"tests": 24, "failures": 2, "errors": 0, "skipped": 0}
        or validation.get("source_unchanged") is not True
        or d4.get("status") != "passed"
        or d4.get("binary_sha256")
        != "ea86d879062828983695762650fbc20cd9b0b8b682757861779ccd3c79ec3aea"
    ):
        raise RuntimeError("native persistence V4 archive evidence mismatch")
    result = previous.check()
    client = session()
    try:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
    finally:
        client.close()
    if current != {"v1": [], "v2": []}:
        raise RuntimeError("nonempty RunPod inventory before native persistence V5")
    result["native_persistence_v4_reconciled"] = True
    result["native_persistence_v4_pod_id"] = saved["pod_id"]
    result["native_persistence_v4_estimated_compute_cost_usd"] = saved.get("estimated_compute_cost_usd")
    result["current_inventories"] = current
    result["authorized_aggregate_campaign_cap_usd"] = 10.0
    return result

