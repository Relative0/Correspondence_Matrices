"""Record read-only Runpod cleanup and billing evidence for W8 semantic attempts."""

from __future__ import annotations

import json
from pathlib import Path

import http_w8_logikbench_semantic_preflight_v2 as preflight


HERE = Path(__file__).resolve().parent
DESTINATION = HERE / "W8-LOGIKBENCH-SEMANTIC-FINAL-POSTFLIGHT.json"
POD_IDS = ["41by0ln85ailn7", "s7hrrp4easoesc"]
ESTIMATED = {
    "41by0ln85ailn7": 0.01242437371412913,
    "s7hrrp4easoesc": 0.0016170485258102418,
}


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
    observed = {}
    record_counts = {}
    for row in records:
        pod_id = row.get("podId")
        if pod_id in POD_IDS:
            observed[pod_id] = observed.get(pod_id, 0.0) + float(row.get("amount", 0.0))
            record_counts[pod_id] = record_counts.get(pod_id, 0) + 1
    result = {
        "schema": "cm-runpod-w8-logikbench-semantic-final-postflight/v1",
        "checked_utc": preflight.utc_now(),
        "inventories": inventories,
        "all_inventories_empty": inventories == {"v1": [], "v2": []},
        "pod_details": details,
        "all_created_pods_absent": all(
            item.get("http_status") == 404 for pod in details.values() for item in pod.values()
        ),
        "attempts": {
            "v1_transport_failure": {
                "pod_id": POD_IDS[0],
                "workload_started": False,
                "completed_source_upload": False,
            },
            "v2_local_preflight": {
                "pod_created": False,
                "creation_attempted": False,
            },
            "v3_success": {
                "pod_id": POD_IDS[1],
                "semantic_workload_completed": True,
                "performance_measurement": False,
            },
        },
        "controller_estimated_cost_usd": ESTIMATED,
        "controller_estimated_cost_total_usd": sum(ESTIMATED.values()),
        "billing_observed_by_pod_usd": observed,
        "billing_record_counts_by_pod": record_counts,
        "billing_observed_for_w8_semantic_pods_usd": sum(observed.values()),
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
