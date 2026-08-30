"""Record a read-only Runpod inventory, pod-detail, and billing postflight."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import http_w8_logikbench_conversion_preflight_v2 as preflight


HERE = Path(__file__).resolve().parent
DESTINATION = HERE / "W8-LOGIKBENCH-CONVERSION-FINAL-POSTFLIGHT.json"
POD_IDS = ["71gv8a3dttwnma", "gdephx6ldtg77z"]


def main() -> int:
    if DESTINATION.exists():
        raise RuntimeError("postflight output already exists")
    with preflight.session() as client:
        inventories = {
            "v1": preflight.inventory(client, preflight.V1),
            "v2": preflight.inventory(client, preflight.V2),
        }
        details = {}
        for pod_id in POD_IDS:
            details[pod_id] = {}
            for label, endpoint in (("v1", preflight.V1), ("v2", preflight.V2)):
                response = client.get(endpoint + "/pods/" + pod_id, timeout=10, allow_redirects=False)
                details[pod_id][label] = {"http_status": response.status_code}
        response = client.get(
            preflight.V2 + "/billing/pods",
            params={"startTime": preflight.CAMPAIGN_START, "endTime": preflight.utc_now()},
            timeout=15,
            allow_redirects=False,
        )
        response.raise_for_status()
        metadata = response.json()["metadata"]
    records = metadata.get("records") or []
    by_pod = {}
    for row in records:
        pod_id = row.get("podId")
        if pod_id in POD_IDS:
            by_pod[pod_id] = by_pod.get(pod_id, 0.0) + float(row.get("amount", 0.0))
    result = {
        "schema": "cm-runpod-w8-logikbench-conversion-final-postflight/v1",
        "checked_utc": preflight.utc_now(),
        "inventories": inventories,
        "all_inventories_empty": inventories == {"v1": [], "v2": []},
        "pod_details": details,
        "all_created_pods_absent": all(
            item.get("http_status") == 404 for pod in details.values() for item in pod.values()
        ),
        "controller_estimated_cost_usd": {
            "71gv8a3dttwnma": 0.0008094880898793538,
            "gdephx6ldtg77z": 0.0032521194100379944,
        },
        "controller_estimated_cost_total_usd": 0.004061607499917348,
        "billing_observed_by_pod_usd": by_pod,
        "billing_observed_for_w8_pods_usd": sum(by_pod.values()),
        "billing_metadata": {
            key: metadata.get(key) for key in ("query", "recordCount", "uniquePodCount", "totals")
        },
        "billing_may_lag": True,
        "resource_writes": 0,
        "credentials_recorded": False,
    }
    DESTINATION.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(not result["all_inventories_empty"] or not result["all_created_pods_absent"])


if __name__ == "__main__":
    raise SystemExit(main())
