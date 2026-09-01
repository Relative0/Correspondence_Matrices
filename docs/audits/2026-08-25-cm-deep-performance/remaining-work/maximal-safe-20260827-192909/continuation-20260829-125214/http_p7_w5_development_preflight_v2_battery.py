"""Battery-authorized read-only account, resource, and evidence preflight for P7 W5."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import zipfile

import http_p7_functional_scout_preflight_v6_exact96_retry as transport


HERE = Path(__file__).resolve().parent
V1, V2 = transport.V1, transport.V2
FLAVORS = ("cpu3c", "cpu3g", "cpu3m", "cpu5c", "cpu5g", "cpu5m")
RATE_CAP = 0.25
PHASE_CAP_USD = 0.10
CAMPAIGN_CAP_USD = 5.00
STORAGE_RATE_RESERVE_USD_PER_HOUR = 0.01
MISSING_COST_RESERVE_USD = 0.05
UNATTRIBUTED_OR_LAGGING_RESERVE_USD = 0.25
PRIOR_HTTP_RESERVE = UNATTRIBUTED_OR_LAGGING_RESERVE_USD
MINIMUM_BATTERY_PERCENT = 50
CAMPAIGN_START = "2026-08-27T00:00:00Z"
MANIFEST = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-MANIFEST-V2-20260830.json"
BUNDLE = HERE / "RUNPOD-P7-FUNCTIONAL-SCOUT-UPLOAD-BUNDLE-V2-20260830.zip"
PACKAGE_VALIDATION = HERE / "P7-W5-PACKAGE-V1-LOCAL-VALIDATION.json"
W3_AUDIT = HERE / "P7-W3-FINAL-INDEPENDENT-AUDIT.json"
W3_POSTFLIGHT = HERE / "P7-W3-FINAL-POSTFLIGHT.json"
W8_POSTFLIGHT = HERE / "W8-LOGIKBENCH-SEMANTIC-FINAL-POSTFLIGHT.json"
W8_FREEZE_VERIFICATION = (
    HERE.parents[5]
    / "docs"
    / "research"
    / "verification"
    / "comparative-w8-logikbench-confirmation-v1-2026-08-31"
    / "freeze-verification.json"
)
W5_FREEZE_VERIFICATION = (
    HERE.parents[5]
    / "docs"
    / "research"
    / "verification"
    / "comparative-p7-w5-development-v1-2026-09-01"
    / "verification.json"
)
W4_AUDIT = HERE / "P7-W4-TIMING-FINAL-INDEPENDENT-AUDIT.json"
W4_POSTFLIGHT = HERE / "P7-W4-TIMING-FINAL-POSTFLIGHT.json"

utc_now = transport.utc_now
session = transport.session
inventory = transport.inventory


def host_power_status() -> dict:
    if os.name != "nt":
        raise RuntimeError("battery-authorized W5 preflight is validated for Windows only")
    import ctypes
    from ctypes import wintypes

    class PowerStatus(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", wintypes.BYTE),
            ("BatteryFlag", wintypes.BYTE),
            ("BatteryLifePercent", wintypes.BYTE),
            ("SystemStatusFlag", wintypes.BYTE),
            ("BatteryLifeTime", wintypes.DWORD),
            ("BatteryFullLifeTime", wintypes.DWORD),
        ]

    value = PowerStatus()
    if not ctypes.WinDLL("kernel32", use_last_error=True).GetSystemPowerStatus(ctypes.byref(value)):
        raise RuntimeError("Windows power status unavailable")
    percent = int(value.BatteryLifePercent)
    ac_connected = int(value.ACLineStatus) == 1
    battery_known = 0 <= percent <= 100
    return {
        "ac_connected": ac_connected,
        "battery_percent": percent if battery_known else None,
        "battery_status_known": battery_known,
        "minimum_battery_percent_when_not_on_ac": MINIMUM_BATTERY_PERCENT,
        "battery_gate_passed": ac_connected or battery_known and percent >= MINIMUM_BATTERY_PERCENT,
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_upload() -> dict:
    manifest = load(MANIFEST)
    payload = BUNDLE.read_bytes()
    if (
        sha256(MANIFEST) != "9aba74a65c695eb134c5f2e45faa54389f70ccea137a0d6fcec6dc3e3651dc74"
        or hashlib.sha256(payload).hexdigest() != "83fdde6cde6d02628ba24fd932671bc40ae2067a7fbb49187a38b580c71cc668"
        or len(payload) != 3_197_013
        or manifest.get("file_count") != 96
        or manifest.get("bytes") != 19_484_163
    ):
        raise RuntimeError("exact 96-file payload identity changed")
    expected = {row["target"]: row for row in manifest["files"]}
    if len(expected) != 96:
        raise RuntimeError("duplicate upload target")
    with zipfile.ZipFile(BUNDLE) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise RuntimeError("upload ZIP membership changed")
        for name in names:
            data = archive.read(name)
            row = expected[name]
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise RuntimeError("upload ZIP member changed: " + name)
    return {
        "verified": True,
        "files": 96,
        "source_bytes": 19_484_163,
        "bundle_bytes": len(payload),
        "manifest_sha256": sha256(MANIFEST),
        "bundle_sha256": hashlib.sha256(payload).hexdigest(),
    }


def get_offer(flavor: str) -> dict:
    with session() as client:
        response = client.get(
            V2 + "/catalog/cpus/" + flavor,
            params={"include": "AVAILABILITY", "product": "POD", "vcpuCount": 2},
            timeout=15,
            allow_redirects=False,
        )
        response.raise_for_status()
        body = response.json()
    result = {
        field: body.get(field)
        for field in ("id", "availability", "price", "vcpu", "ramGbPerVcpu", "dataCenters")
    }
    result["checked_utc"] = utc_now()
    rate = float(body["price"]["securePerVcpu"]) * 2
    ram = float(body["ramGbPerVcpu"]) * 2
    result.update(rate_usd_per_hour=rate, ram_gb=ram)
    result["eligible"] = bool(
        body.get("id") == flavor
        and body.get("availability") in ("LOW", "MEDIUM", "HIGH")
        and math.isfinite(rate)
        and 0 < rate <= RATE_CAP
        and math.isfinite(ram)
        and ram >= 4
        and body["vcpu"]["min"] <= 2 <= body["vcpu"]["max"]
    )
    return result


def local_campaign_cost_bound() -> dict:
    by_pod: dict[str, float | None] = {}
    for path in HERE.rglob("RUN.json"):
        try:
            record = load(path)
        except (OSError, ValueError, TypeError):
            continue
        pod_id = record.get("pod_id")
        if not isinstance(pod_id, str) or not record.get("pod_created"):
            continue
        value = record.get("estimated_compute_cost_usd")
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
            prior = by_pod.get(pod_id)
            if prior is None or value > prior:
                by_pod[pod_id] = float(value)
        elif pod_id not in by_pod:
            by_pod[pod_id] = None
    known = sum(value for value in by_pod.values() if value is not None)
    missing = sorted(pod_id for pod_id, value in by_pod.items() if value is None)
    return {
        "unique_created_pods": len(by_pod),
        "known_estimated_compute_cost_usd": known,
        "missing_cost_pod_ids": missing,
        "missing_cost_reserve_each_usd": MISSING_COST_RESERVE_USD,
        "local_bound_before_unattributed_reserve_usd": known + len(missing) * MISSING_COST_RESERVE_USD,
    }


def check() -> dict:
    upload = verify_upload()
    package = load(PACKAGE_VALIDATION)
    w3 = load(W3_AUDIT)
    w3_postflight = load(W3_POSTFLIGHT)
    w8_postflight = load(W8_POSTFLIGHT)
    w8_freeze = load(W8_FREEZE_VERIFICATION)
    w5_freeze = load(W5_FREEZE_VERIFICATION)
    w4_audit = load(W4_AUDIT)
    w4_postflight = load(W4_POSTFLIGHT)
    if (
        package.get("ready") is not True
        or package.get("primary_cells") != 7524
        or package.get("total_cells_including_diagnostics") != 7852
        or package.get("remote_program_count") != 4
        or w3.get("status") != "passed_with_one_shared_oracle_feasibility_exclusion"
        or w3.get("combined", {}).get("verified_cells") != 513
        or w3.get("combined", {}).get("performance_measurement") is not False
        or w3.get("combined", {}).get("excluded_case")
        != "development-epfl-sqrt-31cdaf5d0213"
        or w3_postflight.get("all_created_pods_absent") is not True
        or w3_postflight.get("inventories") != {"v1": [], "v2": []}
        or w8_postflight.get("all_created_pods_absent") is not True
        or w8_postflight.get("all_inventories_empty") is not True
        or w8_freeze.get("verified") is not True
        or w8_freeze.get("case_count") != 30
        or w8_freeze.get("performance_measurement") is not False
        or w4_audit.get("verified") is not True
        or w4_audit.get("status") != "passed_diagnostic_development_timing_scout"
        or w4_postflight.get("all_owned_pods_absent") is not True
        or w4_postflight.get("inventories") != {"v1": [], "v2": []}
        or w5_freeze.get("verified") is not True
        or w5_freeze.get("principal_cases") != 57
        or w5_freeze.get("primary_cells") != 7524
        or w5_freeze.get("typed_exclusion_retained") is not True
        or w5_freeze.get("relation_maximum_blocks_frozen") is not True
    ):
        raise RuntimeError("W3/W4/W5/W8 readiness evidence changed")

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(get_offer, flavor) for flavor in FLAVORS]
        offers = []
        for flavor, future in zip(FLAVORS, futures):
            try:
                offers.append(future.result())
            except Exception as exc:
                offers.append({"id": flavor, "eligible": False, "error_type": type(exc).__name__})
    eligible = [offer for offer in offers if offer.get("eligible")]
    priority = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    eligible.sort(
        key=lambda offer: (
            offer["rate_usd_per_hour"],
            -priority[offer["availability"]],
            FLAVORS.index(offer["id"]),
        )
    )
    with session() as client:
        current = {"v1": inventory(client, V1), "v2": inventory(client, V2)}
        response = client.get(
            V2 + "/billing/pods",
            params={"startTime": CAMPAIGN_START, "endTime": utc_now()},
            timeout=15,
            allow_redirects=False,
        )
        response.raise_for_status()
        metadata = response.json()["metadata"]
        billing_total = float(metadata["totals"]["totalAmount"])
        response = client.post(
            "https://api.runpod.io/graphql",
            json={"query": "query { myself { clientBalance currentSpendPerHr spendLimit } }"},
            timeout=15,
            allow_redirects=False,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("errors"):
            raise RuntimeError("account readiness query failed")
        account = body["data"]["myself"]
    local = local_campaign_cost_bound()
    attributable_floor = max(local["local_bound_before_unattributed_reserve_usd"], billing_total)
    prior = attributable_floor + UNATTRIBUTED_OR_LAGGING_RESERVE_USD
    selected = eligible[0] if eligible else None
    projected = (
        (selected["rate_usd_per_hour"] + STORAGE_RATE_RESERVE_USD_PER_HOUR) / 3
        if selected else None
    )
    credit_sufficient = bool(projected is not None and float(account["clientBalance"]) >= projected)
    spend_limit_sufficient = bool(
        selected is not None
        and account.get("spendLimit") is not None
        and float(account["spendLimit"])
        >= float(account["currentSpendPerHr"])
        + selected["rate_usd_per_hour"]
        + STORAGE_RATE_RESERVE_USD_PER_HOUR
    )
    result = {
        "schema": "cm-runpod-p7-w5-development-read-only-preflight/v2-battery-authorized",
        "checked_utc": utc_now(),
        "ready": False,
        "resource_writes": 0,
        "credential_values_recorded": False,
        "host_power": host_power_status(),
        "battery_override_authorized": True,
        "upload_verification": upload,
        "package_validation_sha256": sha256(PACKAGE_VALIDATION),
        "offers": offers,
        "selected_offer": selected,
        "current_inventories": current,
        "billing": {field: metadata.get(field) for field in ("query", "recordCount", "uniquePodCount", "totals")},
        "billing_may_lag": True,
        "observed_campaign_billing_usd": billing_total,
        "local_campaign_accounting": local,
        "attributable_floor_usd": attributable_floor,
        "unattributed_or_lagging_reserve_usd": UNATTRIBUTED_OR_LAGGING_RESERVE_USD,
        "prior_cost_bound_usd": prior,
        "projected_20_min_cost_usd": projected,
        "projected_aggregate_cost_usd": None if projected is None else prior + projected,
        "authorized_phase_cap_usd": PHASE_CAP_USD,
        "authorized_aggregate_campaign_cap_usd": CAMPAIGN_CAP_USD,
        "credit_sufficient": credit_sufficient,
        "spend_limit_sufficient": spend_limit_sufficient,
        "w3_verified_cells": 513,
        "w8_confirmation_cases_frozen": 30,
        "w4_scout_cases": 12,
        "w5_principal_cases": 57,
        "w5_planned_primary_cells": 7524,
        "w5_cells_including_diagnostics": 7852,
        "performance_measurement": True,
        "principal_p7_result": True,
    }
    result["ready"] = bool(
        selected
        and current == {"v1": [], "v2": []}
        and result["host_power"]["battery_gate_passed"]
        and math.isfinite(prior)
        and projected is not None
        and projected <= PHASE_CAP_USD
        and prior + projected <= CAMPAIGN_CAP_USD
        and credit_sufficient
        and spend_limit_sufficient
    )
    return result


if __name__ == "__main__":
    try:
        value = check()
    except Exception as exc:
        value = {
            "schema": "cm-runpod-p7-w5-development-read-only-preflight/v2-battery-authorized",
            "checked_utc": utc_now(),
            "ready": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "resource_writes": 0,
            "credential_values_recorded": False,
        }
    print(json.dumps(value, indent=2, sort_keys=True))
    raise SystemExit(0 if value.get("ready") else 1)
