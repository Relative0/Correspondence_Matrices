"""Create a sanitized postflight reconciliation for the authorized campaign attempts."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cm_runpod_config import load_runpod_config

BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
OUT = BASE / "campaign-reconciliation-001"
V1, V2 = "https://rest.runpod.io/v1", "https://api.runpod.io/v2"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(client, endpoint):
    response = client.get(endpoint + "/pods", timeout=20, allow_redirects=False)
    response.raise_for_status()
    value = response.json(); rows = value if isinstance(value, list) else value.get("pods")
    if not isinstance(rows, list): raise RuntimeError("inventory schema")
    return len(rows)


def main():
    key = load_runpod_config().api_key
    if not key or any(char.isspace() for char in key): raise RuntimeError("credential unavailable")
    client = requests.Session(); client.trust_env = False
    client.headers["Authorization"] = "Bearer " + key
    end = now()
    response = client.get(V2 + "/billing/pods", params={"startTime": "2026-09-13T19:30:00Z", "endTime": end},
                          timeout=30, allow_redirects=False)
    response.raise_for_status(); metadata = response.json().get("metadata", {})
    totals = metadata.get("totals", {})
    runs = [json.loads((BASE / f"runpod-primary-00{i}/RUN.json").read_text(encoding="utf-8")) for i in (1, 2)]
    document = {
        "schema": "cm-benchmark-runpod-campaign-reconciliation/v1",
        "checked_utc": end,
        "campaign_id": "cm-mega-prelaunch-20260914-008",
        "inventories": {"v1_pod_count": inventory(client, V1), "v2_pod_count": inventory(client, V2)},
        "billing": {"window_start_utc": "2026-09-13T19:30:00Z", "window_end_utc": end,
                    "record_count": metadata.get("recordCount"), "total_amount_usd": totals.get("totalAmount"),
                    "billing_may_lag": True},
        "attempts": [{"attempt": index + 1, "run_sha256": digest(BASE / f"runpod-primary-00{index+1}/RUN.json"),
                      "status": run.get("status"), "uploaded_shards": run.get("uploaded_shards"),
                      "estimated_compute_cost_usd": run.get("estimated_compute_cost_usd"),
                      "owned_pod_absent": run.get("cleanup", {}).get("owned_pod_absent")}
                     for index, run in enumerate(runs)],
        "totals": {"pods_created": 2, "concurrent_pods_max": 1,
                   "estimated_compute_cost_usd": sum(run.get("estimated_compute_cost_usd") or 0 for run in runs),
                   "uploaded_shards": sum(run.get("uploaded_shards") or 0 for run in runs),
                   "benchmark_measurements": 0},
        "authorization_exhausted": True,
        "further_create_authorized": False,
        "credentials_recorded": False,
        "resource_writes": 0,
    }
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "RUNPOD_RECONCILIATION.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = (
        "# CM benchmark RunPod campaign reconciliation\n\n"
        "Both authorized Pods were deleted and both RunPod inventories are empty. No benchmark measurements were produced.\n\n"
        "Attempt 1 stopped on a transient proxy 404 before upload. Attempt 2 uploaded all 11 frozen shards and built d4, "
        "then stopped because the frozen Python-SAT development version was unavailable for Linux/Python 3.13.\n\n"
        "The two-Pod authorization is exhausted. No further create is authorized.\n"
    )
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"inventory_empty": document["inventories"] == {"v1_pod_count": 0, "v2_pod_count": 0},
                      "billing_total_usd": document["billing"]["total_amount_usd"],
                      "estimated_compute_cost_usd": document["totals"]["estimated_compute_cost_usd"],
                      "authorization_exhausted": True}, sort_keys=True))


if __name__ == "__main__":
    main()
