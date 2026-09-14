"""Create the final sanitized reconciliation for the successor benchmark Pod."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_runpod_config import load_runpod_config  # noqa: E402


BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
OUT = BASE / "successor-reconciliation-001"
RUN = BASE / "runpod-successor-001/RUN.json"
PRIOR = BASE / "campaign-reconciliation-003/RUNPOD_RECONCILIATION.json"
PRELAUNCH = BASE / "successor-prelaunch-002"
V1 = "https://rest.runpod.io/v1"
V2 = "https://api.runpod.io/v2"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def inventory(client: requests.Session, endpoint: str) -> int:
    response = client.get(endpoint + "/pods", timeout=20, allow_redirects=False)
    response.raise_for_status()
    value = response.json()
    rows = value if isinstance(value, list) else value.get("pods")
    if not isinstance(rows, list):
        raise RuntimeError("unexpected RunPod inventory schema")
    return len(rows)


def main() -> None:
    if OUT.exists():
        raise RuntimeError("successor reconciliation already exists")
    api_key = load_runpod_config().api_key
    if not api_key or any(char.isspace() for char in api_key):
        raise RuntimeError("credential unavailable")
    client = requests.Session()
    client.trust_env = False
    client.headers["Authorization"] = "Bearer " + api_key
    checked = now()
    response = client.get(
        V2 + "/billing/pods",
        params={"startTime": "2026-09-13T19:30:00Z", "endTime": checked},
        timeout=30,
        allow_redirects=False,
    )
    response.raise_for_status()
    metadata = response.json().get("metadata", {})
    billed = metadata.get("totals", {}).get("totalAmount")
    prior = load(PRIOR)
    run = load(RUN)
    summary = run.get("evidence", {}).get("summary", {})
    core = summary.get("core_screen", {})
    successor_hours = float(run.get("elapsed_since_create_s") or 0) / 3600
    successor_cost = float(run.get("estimated_compute_cost_usd") or 0)
    combined_hours = float(prior["totals"]["estimated_total_pod_hours"]) + successor_hours
    combined_cost = float(prior["totals"]["estimated_compute_cost_usd"]) + successor_cost
    document = {
        "schema": "cm-benchmark-runpod-successor-reconciliation/v1",
        "checked_utc": checked,
        "campaign_id": "cm-mega-successor-20260914-009",
        "inventories": {
            "v1_pod_count": inventory(client, V1),
            "v2_pod_count": inventory(client, V2),
        },
        "billing": {
            "window_start_utc": "2026-09-13T19:30:00Z",
            "window_end_utc": checked,
            "record_count": metadata.get("recordCount"),
            "total_amount_usd": billed,
            "billing_may_lag": True,
        },
        "successor_pod": {
            "run_sha256": digest(RUN),
            "status": run.get("status"),
            "actual_resources": run.get("actual_resources"),
            "uploaded_controls": run.get("uploaded_controls"),
            "uploaded_shards": run.get("uploaded_shards"),
            "evidence_sha256": run.get("evidence", {}).get("sha256"),
            "evidence_files": run.get("evidence", {}).get("files"),
            "measurements": summary.get("benchmark_measurements"),
            "cells": core.get("cells"),
            "status_counts": core.get("status_counts"),
            "correctness_mismatches": core.get("correctness_mismatches"),
            "elapsed_since_create_seconds": run.get("elapsed_since_create_s"),
            "estimated_compute_cost_usd": successor_cost,
            "owned_pod_absent": run.get("cleanup", {}).get("owned_pod_absent"),
        },
        "combined_original_and_successor": {
            "pods_created": int(prior["totals"]["pods_created"]) + 1,
            "create_requests": int(prior["totals"]["create_requests"]) + 1,
            "maximum_concurrent_pods": 1,
            "estimated_total_pod_hours": combined_hours,
            "estimated_compute_cost_usd": combined_cost,
            "maximum_total_pod_hours": 16,
            "maximum_total_runpod_charges_usd": 50,
        },
        "bound_sha256": {
            "upload_manifest": digest(PRELAUNCH / "UPLOAD_MANIFEST.json"),
            "approval_request": digest(PRELAUNCH / "RUNPOD_APPROVAL_REQUEST.json"),
            "authorization": digest(PRELAUNCH / "RUNPOD_AUTHORIZATION.json"),
            "evidence_zip": digest(BASE / "runpod-successor-001/evidence.zip"),
        },
        "authorization_exhausted": True,
        "further_create_authorized": False,
        "credentials_recorded": False,
        "reconciliation_resource_writes": 0,
    }
    if document["inventories"] != {"v1_pod_count": 0, "v2_pod_count": 0}:
        raise RuntimeError("RunPod inventory is not empty")
    if (
        run.get("status") != "complete"
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("uploaded_controls") != 2
        or run.get("uploaded_shards") != 1
        or core.get("cells") != 108
        or core.get("correctness_mismatches")
        or core.get("status_counts", {}).get("worker_error", 0)
        or core.get("status_counts", {}).get("error", 0)
    ):
        raise RuntimeError("successor run evidence mismatch")
    if combined_hours >= 16 or combined_cost >= 50:
        raise RuntimeError("combined campaign cap reached or exceeded")
    if billed is not None and float(billed) >= 50:
        raise RuntimeError("billing endpoint reports cumulative cap reached")
    OUT.mkdir(parents=True, exist_ok=False)
    record = OUT / "RUNPOD_RECONCILIATION.json"
    record.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = (
        "# CM successor RunPod reconciliation\n\n"
        "The single authorized successor Pod completed, its evidence was retrieved, "
        "the Pod was deleted, and both RunPod inventories are empty. No replacement "
        "or further creation is authorized.\n\n"
        f"The successor used {successor_hours:.6f} Pod-hours with controller-estimated "
        f"compute cost ${successor_cost:.6f}. Combined controller estimates are "
        f"{combined_hours:.6f} Pod-hours and ${combined_cost:.6f}. The billing endpoint "
        f"currently reports ${float(billed):.6f}; billing may lag.\n"
    )
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "inventory_empty": True,
                "successor_compute_cost_usd": successor_cost,
                "combined_compute_cost_usd": combined_cost,
                "combined_pod_hours": combined_hours,
                "billing_total_usd": billed,
                "reconciliation_sha256": digest(record),
                "authorization_exhausted": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
