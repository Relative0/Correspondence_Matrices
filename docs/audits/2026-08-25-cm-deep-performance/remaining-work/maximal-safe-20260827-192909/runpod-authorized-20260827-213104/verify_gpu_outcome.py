"""Final read-only billing/inventory and trivial local integrity verification."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    spec = importlib.util.spec_from_file_location("gpu_final", HERE / "runpod_gpu_smoke_controller.py")
    controller = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(controller)
    final = json.loads((HERE / "GPU-FINAL-RECONCILIATION.json").read_text())
    assert final["status"] == "owned_pod_absent_after_horizon"
    assert final["snapshot"]["after_original_horizon"] and final["snapshot"]["zero_pods_observed"]
    attempt = HERE / "gpu-execute-001"
    releases = {}
    for label, path in (
        ("controller", attempt / "HOST-AWAKE-RELEASED-controller.json"),
        ("watchdog", attempt / "HOST-AWAKE-RELEASED-watchdog.json"),
        ("reconciliation", HERE / "gpu-final-cleanup-guard/HOST-AWAKE-RELEASED-reconciliation.json"),
    ):
        releases[label] = json.loads(path.read_text())
        assert releases[label]["released"]
    with controller.session() as client:
        inventories = controller.inventory_both(client)
        assert not any(inventories.values()), "nonempty final inventory requires review"
        response = client.get(controller.REST_V2 + "/billing/pods",
                              params={"startTime": "2026-08-27T14:30:00Z", "endTime": controller.utc_now()},
                              timeout=20, allow_redirects=False)
        response.raise_for_status()
        metadata = response.json()["metadata"]
    checks = json.loads((HERE / "GPU-CONTROLLER-CHECKS.json").read_text())
    controller_hash = hashlib.sha256((HERE / "runpod_gpu_smoke_controller.py").read_bytes()).hexdigest()
    assert controller_hash == checks["controller_sha256"]
    assert hashlib.sha256((HERE / "runpod_retry_cpu8_controller.py").read_bytes()).hexdigest() == "a7728ee101a3c04cda50d5a8b52e9b1628dc31d2098def0a0ab348587aa0edb2"
    assert hashlib.sha256((HERE / "runpod_retry_cpu8_v1_controller.py").read_bytes()).hexdigest() == "40adb66b61ba59dda9282bf264b6767c738d168ed31abc84c790e1c6c2b3ccac"
    manifest = json.loads(controller.MANIFEST_PATH.read_text())
    for row in manifest["files"]:
        data = (controller.ROOT / row["source"]).read_bytes()
        assert len(data) == row["bytes"] and hashlib.sha256(data).hexdigest() == row["sha256"]
    run = json.loads((attempt / "RUN.json").read_text())
    snapshots = [json.loads(path.read_text()) for path in sorted(attempt.glob("INDEPENDENT-INVENTORY-*.json"))]
    git = {}
    for label, arguments in (("head", ["rev-parse", "HEAD"]), ("branch", ["branch", "--show-current"]),
                             ("status", ["status", "--short"]), ("diff_stat", ["diff", "--stat"]),
                             ("campaign_diff_stat", ["diff", "--stat", "--", "cm_ir.py", "cm_remote_worker.py",
                                                     "cm_runpod_protocol.py", "cmbench/output_budget.py", "tests/test_output_budget.py"])):
        process = subprocess.run(["git", *arguments], cwd=controller.ROOT, capture_output=True, text=True)
        git[label] = {"exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr}
        assert process.returncode == 0
    controller.write_exclusive(HERE / "GPU-FINAL-REPOSITORY-STATE.json", {"checked_utc": controller.utc_now(), **git})
    result = {"checked_utc": controller.utc_now(), "status": "creation_failed_no_pod_observed_after_horizon",
              "verification_resource_writes": 0, "creation_requests_this_attempt": 1, "pod_ids_returned": 0,
              "remote_workload_execution_observed": False, "remote_workload_evidence": False,
              "creation_http_status": run["creation_http_status"], "creation_request_utc": run["creation_request_utc"],
              "request_id": run["creation_response_headers"]["X-Request-Id"], "inventories": inventories,
              "final_reconciliation": final["status"], "guard_releases": releases,
              "inventory_snapshots": len(snapshots),
              "all_snapshots_empty_and_successful": all(row["zero_pods_observed"] for row in snapshots),
              "billing_metadata": metadata, "billing_may_lag": True,
              "controller_sha256": controller_hash, "executed_controllers_preserved": True,
              "source_files": len(manifest["files"]), "approved_source_hashes_match": True,
              "local_fake_checks": checks["status"], "automatic_replacement_queued": False,
              "support_draft_sent": False, "source_or_policy_changes_this_continuation": False}
    controller.write_exclusive(HERE / "GPU-FINAL-OUTCOME.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
