"""Record a sanitized read-only Runpod postflight for the P7 W4 scout."""

from __future__ import annotations

import json
import os
from pathlib import Path

import http_native_scout_preflight_v6 as billing_source
import http_p7_functional_scout_preflight_v6_exact96_retry as transport


HERE = Path(__file__).resolve().parent
RUN_DIRS = (HERE / "p7-w4-timing-v1-001", HERE / "p7-w4-timing-v2-retry-001")
AUDIT = HERE / "P7-W4-TIMING-FINAL-INDEPENDENT-AUDIT.json"
RECEIPT = HERE / "P7-W4-TIMING-FINAL-POSTFLIGHT.json"


def main() -> int:
    if RECEIPT.exists():
        raise FileExistsError(RECEIPT)
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    runs = [json.loads((directory / "RUN.json").read_text(encoding="utf-8")) for directory in RUN_DIRS]
    pod_ids = [run["pod_id"] for run in runs]

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
                response = client.get(endpoint + "/pods/" + pod_id, timeout=10, allow_redirects=False)
                details[pod_id][label] = {"http_status": response.status_code}
        billing = billing_source.billing_check(client)
    finally:
        client.close()

    rows = [row for row in billing["historical_account_rows"] if row["podId"] in pod_ids]
    observed = sum(row["amount"] for row in rows)
    estimated = float(audit.get("combined_attempt_estimated_compute_cost_usd") or 0.0)
    result = {
        "schema": "cm-runpod-p7-w4-timing-final-postflight/v1",
        "checked_utc": transport.utc_now(),
        "pod_ids": pod_ids,
        "inventories": inventories,
        "pod_details": details,
        "billing_rows_for_w4_pods": rows,
        "billing_observed_usd": observed,
        "billing_may_lag": True,
        "estimated_compute_cost_usd": estimated,
        "five_dollar_authorization_remaining_after_w4_estimate_usd": 5.0 - estimated,
        "all_owned_pods_absent": all(
            item["http_status"] == 404
            for pod in details.values()
            for item in pod.values()
        ),
    }
    if inventories != {"v1": [], "v2": []}:
        raise RuntimeError("postflight inventory is not empty")
    if not result["all_owned_pods_absent"]:
        raise RuntimeError("a W4 pod detail route did not return 404")

    temporary = RECEIPT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, RECEIPT)
    print(json.dumps({
        "checked_utc": result["checked_utc"],
        "inventories": inventories,
        "all_owned_pods_absent": result["all_owned_pods_absent"],
        "billing_observed_usd": observed,
        "billing_may_lag": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
