"""Read-only RunPod inventory and billing reconciliation for a completed video run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import execute_approved_v4 as controller  # noqa: E402


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def reconcile(run_dir: Path) -> dict[str, object]:
    run = json.loads((run_dir / "RUN.json").read_text("utf-8"))
    pod_id = run["pod_id"]
    pod_name = run["pod_name"]
    with controller.api_session() as client:
        matches = sorted(controller.owned(client, pod_name, pod_id))
        response = client.get(
            controller.V1 + "/billing/pods",
            params={
                "podId": pod_id,
                "grouping": "podId",
                "bucketSize": "hour",
                "startTime": run["started_utc"],
                "endTime": datetime.now(timezone.utc).isoformat(),
            },
            timeout=20,
            allow_redirects=False,
        )
    body = response.json() if response.status_code == 200 else None
    candidates = body if isinstance(body, list) else (
        body.get("records", []) if isinstance(body, dict) else []
    )
    records = []
    for item in candidates:
        if not isinstance(item, dict) or item.get("podId") != pod_id:
            continue
        records.append({
            key: item.get(key)
            for key in ("podId", "time", "amount", "timeBilledMs", "diskSpaceBilledGb")
        })
    billed_amount = sum(
        float(item["amount"]) for item in records if isinstance(item.get("amount"), (int, float))
    )
    report = {
        "schema_version": "1.0",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "proposal_id": run["proposal_id"],
        "pod_id": pod_id,
        "owned_inventory_matches": matches,
        "owned_pod_absent_verified": not matches,
        "billing_http_status": response.status_code,
        "billing_records": records,
        "billing_record_count": len(records),
        "billed_amount_usd_visible": billed_amount,
        "billing_status": "records_visible" if records else "no_record_visible_billing_may_lag",
        "controller_compute_estimate_usd": run["estimated_compute_cost_usd"],
        "credential_value_recorded": False,
    }
    if matches or response.status_code != 200:
        raise RuntimeError("postflight inventory or billing request failed")
    atomic_json(run_dir / "RUNPOD_POSTFLIGHT.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    report = reconcile(args.run_dir.resolve())
    print(json.dumps({
        "owned_pod_absent_verified": report["owned_pod_absent_verified"],
        "billing_record_count": report["billing_record_count"],
        "billing_status": report["billing_status"],
        "billed_amount_usd_visible": report["billed_amount_usd_visible"],
    }, indent=2))


if __name__ == "__main__":
    main()
