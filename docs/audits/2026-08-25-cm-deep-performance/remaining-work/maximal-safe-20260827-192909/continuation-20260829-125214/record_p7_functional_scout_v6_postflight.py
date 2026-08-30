"""Record sanitized Runpod inventory, deletion, billing, and campaign postflight."""

from __future__ import annotations

import json
import os
from pathlib import Path

import http_native_scout_preflight_v6 as billing_source
import http_p7_functional_scout_preflight_v6_exact96_retry as preflight


HERE = Path(__file__).resolve().parent
OUT = HERE / "p7-functional-scout-v6-exact96-001"
RECEIPT = OUT / "INDEPENDENT-POSTFLIGHT.json"
POD_IDS = ["1xh6csc4oxy067", "2fzt8mu6ji6nmw", "r044pqp2vgp7cy", "6mlqn19hnco1b0"]


def main() -> int:
    run = json.loads((OUT / "RUN.json").read_text(encoding="utf-8"))
    client = preflight.session()
    try:
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
        billing = billing_source.billing_check(client)
    finally:
        client.close()

    rows = [row for row in billing["historical_account_rows"] if row["podId"] in POD_IDS]
    observed = sum(row["amount"] for row in rows)
    incremental_bound = 0.001 + run["estimated_compute_cost_usd"]
    result = {
        "schema": "cm-runpod-p7-functional-scout-v6-postflight/v1",
        "checked_utc": preflight.utc_now(),
        "inventories": inventories,
        "pod_details": details,
        "billing_rows_for_related_pods": rows,
        "billing_observed_usd": observed,
        "billing_may_lag": True,
        "incremental_five_dollar_authorization_cost_bound_usd": incremental_bound,
        "incremental_five_dollar_authorization_remaining_bound_usd": 5.0 - incremental_bound,
        "current_run_estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "owned_pod_absent": not any(row.get("id") == run["pod_id"] for values in inventories.values() for row in values),
    }
    if inventories != {"v1": [], "v2": []} or result["owned_pod_absent"] is not True:
        raise RuntimeError("postflight inventory is not empty")
    temporary = RECEIPT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, RECEIPT)
    print(json.dumps({
        "checked_utc": result["checked_utc"],
        "inventories": result["inventories"],
        "pod_details": result["pod_details"],
        "billing_rows_for_related_pods": result["billing_rows_for_related_pods"],
        "billing_may_lag": True,
        "incremental_cost_bound_usd": incremental_bound,
        "incremental_remaining_bound_usd": 5.0 - incremental_bound,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
