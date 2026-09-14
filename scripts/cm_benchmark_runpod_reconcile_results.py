"""Create the final sanitized reconciliation after the bounded results Pod."""
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
OUT = BASE / "campaign-reconciliation-003"
V1, V2 = "https://rest.runpod.io/v1", "https://api.runpod.io/v2"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def inventory(client, endpoint):
    response = client.get(endpoint + "/pods", timeout=20, allow_redirects=False)
    response.raise_for_status()
    value = response.json()
    rows = value if isinstance(value, list) else value.get("pods")
    if not isinstance(rows, list):
        raise RuntimeError("inventory schema")
    return len(rows)


def main():
    if OUT.exists():
        raise RuntimeError("final reconciliation already exists")
    key = load_runpod_config().api_key
    if not key or any(char.isspace() for char in key):
        raise RuntimeError("credential unavailable")
    client = requests.Session()
    client.trust_env = False
    client.headers["Authorization"] = "Bearer " + key
    end = now()
    response = client.get(V2 + "/billing/pods", params={
        "startTime": "2026-09-13T19:30:00Z", "endTime": end,
    }, timeout=30, allow_redirects=False)
    response.raise_for_status()
    metadata = response.json().get("metadata", {})
    billed = metadata.get("totals", {}).get("totalAmount")

    prior = load(BASE / "campaign-reconciliation-002/RUNPOD_RECONCILIATION.json")
    failed = load(BASE / "runpod-results-001/RUN.json")
    result = load(BASE / "runpod-results-002/RUN.json")
    estimated_hours = (float(prior["totals"]["estimated_total_pod_hours"])
                       + float(result["elapsed_since_create_s"]) / 3600)
    estimated_cost = (float(prior["totals"]["estimated_compute_cost_usd"])
                      + float(result["estimated_compute_cost_usd"]))
    document = {
        "schema": "cm-benchmark-runpod-campaign-reconciliation/v3",
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
        "results_create_failure": {
            "run_sha256": digest(BASE / "runpod-results-001/RUN.json"),
            "http_status": failed.get("creation_http_status"),
            "pod_created": failed.get("pod_created"),
            "uploaded_shards": failed.get("uploaded_shards"),
            "owned_pod_absent": failed.get("cleanup", {}).get("owned_pod_absent"),
        },
        "results_pod": {
            "run_sha256": digest(BASE / "runpod-results-002/RUN.json"),
            "status": result.get("status"),
            "uploaded_controls": result.get("uploaded_controls"),
            "uploaded_shards": result.get("uploaded_shards"),
            "evidence_sha256": result.get("evidence", {}).get("sha256"),
            "measurements": result.get("evidence", {}).get("summary", {}).get("benchmark_measurements"),
            "estimated_compute_cost_usd": result.get("estimated_compute_cost_usd"),
            "elapsed_since_create_seconds": result.get("elapsed_since_create_s"),
            "owned_pod_absent": result.get("cleanup", {}).get("owned_pod_absent"),
        },
        "totals": {
            "pods_created": 4,
            "create_requests": 5,
            "concurrent_pods_max": 1,
            "estimated_total_pod_hours": estimated_hours,
            "estimated_compute_cost_usd": estimated_cost,
            "uploaded_shard_instances": int(prior["totals"]["uploaded_shard_instances"]) + 11,
            "distinct_authorized_shards": 11,
            "benchmark_measurements": 90,
        },
        "upload_manifest_sha256": digest(BASE / "prelaunch-008/UPLOAD_MANIFEST.json"),
        "results_analysis_sha256": digest(BASE / "results-analysis-001/RESULTS.json"),
        "authorization_exhausted": True,
        "further_create_authorized": False,
        "credentials_recorded": False,
        "resource_writes": 0,
    }
    if document["inventories"] != {"v1_pod_count": 0, "v2_pod_count": 0}:
        raise RuntimeError("RunPod inventory is not empty")
    if (failed.get("pod_created") is not False or failed.get("cleanup", {}).get("owned_pod_absent") is not True
            or result.get("status") != "complete" or result.get("cleanup", {}).get("owned_pod_absent") is not True):
        raise RuntimeError("results attempt or cleanup evidence mismatch")
    if estimated_hours >= 16 or estimated_cost >= 50 or (billed is not None and float(billed) >= 50):
        raise RuntimeError("campaign cap reached or exceeded")
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "RUNPOD_RECONCILIATION.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = (
        "# CM benchmark RunPod campaign final reconciliation\n\n"
        "All four campaign Pods were deleted and both RunPod inventories are empty. The separate first results-Pod "
        "create request returned HTTP 500 and did not create a resource. The successful fourth Pod retrieved 90 "
        "measurements from the bounded 192-cell screen. No further Pod or creation attempt is authorized.\n\n"
        f"Controller-estimated compute cost is ${estimated_cost:.6f} across {estimated_hours:.6f} Pod-hours. "
        f"The live billing endpoint currently reports ${float(billed):.6f}; billing may lag.\n"
    )
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"inventory_empty": True, "billing_total_usd": billed,
                      "estimated_compute_cost_usd": estimated_cost,
                      "estimated_total_pod_hours": estimated_hours,
                      "authorization_exhausted": True}, sort_keys=True))


if __name__ == "__main__":
    main()
