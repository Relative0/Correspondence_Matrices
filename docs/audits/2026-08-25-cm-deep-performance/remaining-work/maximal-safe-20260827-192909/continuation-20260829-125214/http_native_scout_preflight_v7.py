"""Read-only preflight after the V6 local host-power refusal."""

import hashlib
import os
from pathlib import Path

import http_native_scout_preflight_v6 as previous


HERE = Path(__file__).resolve().parent
V1, V2 = previous.V1, previous.V2
PRIOR_HTTP_RESERVE = previous.PRIOR_HTTP_RESERVE
LOCAL_FAILURE = HERE / "HTTP-NATIVE-SCOUT-PROCFS-V6-LOCAL-PREFLIGHT-FAILURE-20260829.json"
V6_OUTPUT = HERE / "http-native-scout-procfs-race-retry-execute-001"
V6_AUTHORIZATION = HERE / "HTTP-NATIVE-SCOUT-PROCFS-RACE-RETRY-AUTHORIZED-20260829.json"

utc_now = previous.utc_now
session = previous.session
inventory = previous.inventory
prior_attempts = previous.prior_attempts
billing_check = previous.billing_check


def host_ac_connected():
    if os.name != "nt":
        raise RuntimeError("host power check is validated for Windows only")
    import ctypes
    from ctypes import wintypes

    class PowerStatus(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", wintypes.BYTE), ("BatteryFlag", wintypes.BYTE),
            ("BatteryLifePercent", wintypes.BYTE), ("SystemStatusFlag", wintypes.BYTE),
            ("BatteryLifeTime", wintypes.DWORD), ("BatteryFullLifeTime", wintypes.DWORD),
        ]

    power = PowerStatus()
    if not ctypes.WinDLL("kernel32", use_last_error=True).GetSystemPowerStatus(ctypes.byref(power)):
        raise RuntimeError("host power status unavailable")
    return power.ACLineStatus == 1


def check():
    failure = previous.load(LOCAL_FAILURE)
    if (
        failure.get("status") != "local_preflight_refused"
        or failure.get("host_ac_line_status") != 0
        or failure.get("controller_run_entered") is not False
        or failure.get("creation_attempted") is not False
        or failure.get("runpod_create_requests") != 0
        or failure.get("authorization_cloud_create_consumed") is not False
        or failure.get("output_directory") != V6_OUTPUT.name
        or failure.get("output_directory_children") != 0
        or failure.get("replacement_or_create_queued") is not False
        or failure.get("authorization_sha256") != hashlib.sha256(V6_AUTHORIZATION.read_bytes()).hexdigest()
        or not V6_OUTPUT.is_dir()
        or any(V6_OUTPUT.iterdir())
    ):
        raise RuntimeError("V6 local preflight refusal is not safely preserved")
    result = previous.check()
    result["v6_local_preflight_refusal_preserved"] = True
    result["v6_cloud_create_authorization_unconsumed"] = True
    result["host_ac_connected"] = host_ac_connected()
    result["ready"] = bool(result.get("ready") and result["host_ac_connected"])
    return result
