"""Record a sanitized read-only Runpod postflight for the complete W3 campaign."""

from __future__ import annotations

import json
import os
from pathlib import Path

import http_native_scout_preflight_v6 as billing_source
import http_p7_functional_scout_preflight_v6_exact96_retry as transport


HERE = Path(__file__).resolve().parent
AUDIT = HERE / "P7-W3-FINAL-INDEPENDENT-AUDIT.json"
RECEIPT = HERE / "P7-W3-FINAL-POSTFLIGHT.json"
ATTEMPT_DIRS = (
    "p7-w3-correctness-v1-001",
    "p7-w3-shard-ir-regression-v1-001",
    "p7-w3-shard-ir-regression-v2-001",
    "p7-w3-shard-ir-development-v2-001",
    "p7-w3-shard-relation-regression-v3-001",
    "p7-w3-split-ir-development-a-v4-001",
    "p7-w3-split-ir-development-b-v4-001",
    "p7-w3-split-ir-development-b-v5-001",
    "p7-w3-tail-ir-development-b-light-v6-001",
    "p7-w3-tail-ir-development-sqrt-v6-001",
    "p7-w3-final-ir-development-square-v7-001",
    "p7-w3-final-relation-development-a-v7-001",
    "p7-w3-final-relation-development-b-light-v7-001",
    "p7-w3-final-relation-development-square-v7-001",
)


def main() -> int:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    runs = [
        json.loads((HERE / name / "RUN.json").read_text(encoding="utf-8"))
        for name in ATTEMPT_DIRS
    ]
    pod_ids = sorted({run["pod_id"] for run in runs if run.get("pod_id")})

    client = transport.session()
    try:
        inventories = {
            "v1": transport.inventory(client, transport.V1),
            "v2": transport.inventory(client, transport.V2),
        }
        details = {}
        for pod_id in pod_ids:
            details[pod_id] = {}
            for label, endpoint in (("v1", transport.V1), ("v2", transport.V2)):
                response = client.get(
                    endpoint + "/pods/" + pod_id,
                    timeout=10,
                    allow_redirects=False,
                )
                details[pod_id][label] = {"http_status": response.status_code}
        billing = billing_source.billing_check(client)
    finally:
        client.close()

    rows = [
        row for row in billing["historical_account_rows"]
        if row["podId"] in pod_ids
    ]
    observed_by_pod = {}
    for row in rows:
        observed_by_pod[row["podId"]] = observed_by_pod.get(row["podId"], 0.0) + row["amount"]
    observed = sum(observed_by_pod.values())
    estimated = float(audit["w3_attempt_estimated_compute_cost_usd"])
    all_details_absent = all(
        item["http_status"] == 404
        for values in details.values()
        for item in values.values()
    )
    result = {
        "schema": "cm-runpod-p7-w3-final-postflight/v1",
        "checked_utc": transport.utc_now(),
        "attempt_count": len(runs),
        "created_pod_ids": pod_ids,
        "inventories": inventories,
        "pod_details": details,
        "billing_rows_for_w3_pods": rows,
        "billing_observed_by_pod_usd": observed_by_pod,
        "billing_observed_usd": observed,
        "billing_may_lag": True,
        "w3_estimated_compute_cost_usd": estimated,
        "five_dollar_authorization_remaining_after_w3_estimate_usd": 5.0 - estimated,
        "all_created_pods_absent": all_details_absent,
    }
    if inventories != {"v1": [], "v2": []}:
        raise RuntimeError("postflight inventory is not empty")
    if not all_details_absent:
        raise RuntimeError("one or more W3 pod detail routes did not return 404")

    temporary = RECEIPT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, RECEIPT)
    print(json.dumps({
        "checked_utc": result["checked_utc"],
        "created_pods": len(pod_ids),
        "inventories": inventories,
        "all_created_pods_absent": all_details_absent,
        "billing_observed_usd": observed,
        "billing_may_lag": True,
        "w3_estimated_compute_cost_usd": estimated,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
