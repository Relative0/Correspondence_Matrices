"""Create the sanitized final reconciliation for all three campaign Pods."""
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
OUT = BASE / "campaign-reconciliation-002"
V1, V2 = "https://rest.runpod.io/v1", "https://api.runpod.io/v2"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(client, endpoint):
    response = client.get(endpoint + "/pods", timeout=20, allow_redirects=False)
    response.raise_for_status()
    value = response.json()
    rows = value if isinstance(value, list) else value.get("pods")
    if not isinstance(rows, list):
        raise RuntimeError("inventory schema")
    return len(rows)


def main():
    key = load_runpod_config().api_key
    if not key or any(char.isspace() for char in key):
        raise RuntimeError("credential unavailable")
    client = requests.Session()
    client.trust_env = False
    client.headers["Authorization"] = "Bearer " + key
    end = now()
    response = client.get(
        V2 + "/billing/pods",
        params={"startTime": "2026-09-13T19:30:00Z", "endTime": end},
        timeout=30,
        allow_redirects=False,
    )
    response.raise_for_status()
    metadata = response.json().get("metadata", {})
    billed = metadata.get("totals", {}).get("totalAmount")
    runs = [json.loads((BASE / f"runpod-primary-00{i}/RUN.json").read_text(encoding="utf-8"))
            for i in (1, 2, 3)]
    attempts = [
        {
            "attempt": index,
            "run_sha256": digest(BASE / f"runpod-primary-00{index}/RUN.json"),
            "status": run.get("status"),
            "uploaded_shards": run.get("uploaded_shards"),
            "estimated_compute_cost_usd": run.get("estimated_compute_cost_usd"),
            "elapsed_since_create_seconds": run.get("elapsed_since_create_s"),
            "owned_pod_absent": run.get("cleanup", {}).get("owned_pod_absent"),
        }
        for index, run in enumerate(runs, 1)
    ]
    estimated_cost = sum(run.get("estimated_compute_cost_usd") or 0 for run in runs)
    estimated_hours = sum(run.get("elapsed_since_create_s") or 0 for run in runs) / 3600
    document = {
        "schema": "cm-benchmark-runpod-campaign-reconciliation/v2",
        "checked_utc": end,
        "campaign_id": "cm-mega-prelaunch-20260914-008",
        "inventories": {"v1_pod_count": inventory(client, V1), "v2_pod_count": inventory(client, V2)},
        "billing": {
            "window_start_utc": "2026-09-13T19:30:00Z",
            "window_end_utc": end,
            "record_count": metadata.get("recordCount"),
            "total_amount_usd": billed,
            "billing_may_lag": True,
        },
        "attempts": attempts,
        "totals": {
            "pods_created": 3,
            "concurrent_pods_max": 1,
            "estimated_total_pod_hours": estimated_hours,
            "estimated_compute_cost_usd": estimated_cost,
            "uploaded_shard_instances": sum(run.get("uploaded_shards") or 0 for run in runs),
            "distinct_authorized_shards": 11,
            "benchmark_measurements": 0,
        },
        "attempt_003_gates": {
            "corrected_python_sat_install_completed": True,
            "native_linux_smoke_completed": True,
            "focused_tests_completed": False,
            "functional_pilot_started": False,
        },
        "diagnostic_sha256": digest(BASE / "recovery-diagnostic-001/DIAGNOSTIC.json"),
        "upload_manifest_sha256": digest(BASE / "prelaunch-008/UPLOAD_MANIFEST.json"),
        "authorization_exhausted": True,
        "further_create_authorized": False,
        "credentials_recorded": False,
        "resource_writes": 0,
    }
    if document["inventories"] != {"v1_pod_count": 0, "v2_pod_count": 0}:
        raise RuntimeError("RunPod inventory is not empty")
    if not all(row["owned_pod_absent"] for row in attempts):
        raise RuntimeError("campaign-owned Pod cleanup is incomplete")
    if estimated_hours >= 16 or estimated_cost >= 50 or (billed is not None and float(billed) >= 50):
        raise RuntimeError("campaign cap reached or exceeded")
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "RUNPOD_RECONCILIATION.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = (
        "# CM benchmark RunPod campaign final reconciliation\n\n"
        "All three authorized serial Pods were deleted, both RunPod inventories are empty, and no further Pod is authorized. "
        "No benchmark measurements were produced.\n\n"
        "Attempt 1 stopped before upload on a transient proxy 404. Attempt 2 uploaded all 11 shards and stopped on the unavailable "
        "Python-SAT pin. Attempt 3 uploaded all 11 shards, installed the corrected pin, and completed the native Linux smoke, then "
        "stopped because the focused remote test selection included a Git-dependent prelaunch test even though `.git` was excluded.\n\n"
        f"Controller-estimated compute cost is ${estimated_cost:.6f} across {estimated_hours:.6f} Pod-hours. "
        f"The live billing endpoint currently reports ${float(billed):.6f}; billing may lag.\n"
    )
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({
        "inventory_empty": True,
        "billing_total_usd": billed,
        "estimated_compute_cost_usd": estimated_cost,
        "estimated_total_pod_hours": estimated_hours,
        "authorization_exhausted": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
