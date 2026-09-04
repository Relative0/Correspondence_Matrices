"""Re-run exact verification and bind the cross-machine query-ladder evidence locally."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/architecture_query_ladder_cross_machine_execution_20260904"
ATTEMPT = HERE / "runpod-architecture-query-ladder-cross-machine-execute-001"
EVIDENCE = ATTEMPT / "evidence/run-output"
STUDY = EVIDENCE / "architecture-query-ladder-linux-clang-20260904-003"
FREEZE = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904"
    / "FREEZE.json"
)
ORACLES = (
    ROOT
    / "docs/recognition/architecture_comparison_execution_retry_20260903/ORACLES.json"
)
REQUEST = (
    HERE
    / "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_AUTHORIZATION_REQUEST_20260904.json"
)
AUTHORIZATION = (
    HERE
    / "RUNPOD_ARCHITECTURE_QUERY_LADDER_CROSS_MACHINE_EXACT_PAYLOAD_AUTHORIZED_2026_09_04.json"
)
MANIFEST = HERE / "UPLOAD_MANIFEST.json"
POST_INVENTORY = HERE / "POST_RUN_INVENTORY.json"
CONTROLLER = ROOT / "scripts/runpod_architecture_query_ladder_cross_machine_controller.py"
VERIFIER = ROOT / "scripts/crse_verify_architecture_query_ladder_campaign.py"
OUTPUT = HERE / "LOCAL_INDEPENDENT_VERIFICATION.json"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_new(path: Path, value: Any) -> None:
    if path.exists() or not path.resolve().is_relative_to(ROOT):
        raise ValueError("local verification output must be a new in-project file")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _link_or_copy(source: Path, target: Path) -> None:
    try:
        os.link(source, target)
    except OSError:
        shutil.copyfile(source, target)


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite local cross-machine verification")
    spec = importlib.util.spec_from_file_location("cross_machine_exact_reverification", VERIFIER)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)

    with tempfile.TemporaryDirectory(prefix=".cm-qx-reverify-", dir=HERE) as temporary:
        replay = Path(temporary)
        for name in ("results.json", "raw_measurements.jsonl", "runtime_binding.json"):
            _link_or_copy(STUDY / name, replay / name)
        recomputed = verifier.verify(replay, FREEZE, ORACLES)
        recomputed_path = replay / "independent_verification.json"
        remote = _load(STUDY / "independent_verification.json")
        if recomputed != remote or recomputed_path.read_bytes() != (
            STUDY / "independent_verification.json"
        ).read_bytes():
            raise ValueError("local exact re-verification differs from remote verification")

    request = _load(REQUEST)
    authorization = _load(AUTHORIZATION)
    manifest = _load(MANIFEST)
    run = _load(ATTEMPT / "RUN.json")
    transport = _load(ATTEMPT / "TRANSPORT-FREEZE.json")
    runtime = _load(EVIDENCE / "RUNTIME.json")
    host = _load(EVIDENCE / "CROSS-MACHINE-HOST-PREFLIGHT.json")
    clang = _load(EVIDENCE / "CLANG-INSTALL.json")
    binding = _load(STUDY / "runtime_binding.json")
    post_inventory = _load(POST_INVENTORY)
    watchdog = _load(ATTEMPT / "WATCHDOG-RESULT.json")
    watchdog_done = _load(ATTEMPT / "watchdog-done.json")
    controller_release = _load(
        ATTEMPT / "HOST-AWAKE-RELEASED-architecture-query-ladder-controller.json"
    )
    watchdog_release = _load(
        ATTEMPT / "HOST-AWAKE-RELEASED-architecture-query-ladder-watchdog.json"
    )
    source_mismatches = []
    for row in manifest["files"]:
        source = ROOT.joinpath(*Path(row["source"]).parts)
        if source.stat().st_size != row["bytes"] or _sha256(source) != row["sha256"]:
            source_mismatches.append(row["source"])

    if (
        request.get("authorization", {}).get("granted") is not False
        or authorization.get("authorized") is not True
        or authorization.get("authorization_request_sha256") != _sha256(REQUEST)
        or authorization.get("controller_sha256") != _sha256(CONTROLLER)
        or transport.get("authorization_sha256") != _sha256(AUTHORIZATION)
        or transport.get("authorization_request_sha256") != _sha256(REQUEST)
        or transport.get("controller_sha256") != _sha256(CONTROLLER)
        or transport.get("manifest_sha256") != _sha256(MANIFEST)
        or transport.get("source_files") != manifest["file_count"]
        or manifest["file_count"] != 70
        or transport.get("source_bytes") != manifest["bytes"]
        or source_mismatches
        or run.get("status") != "complete"
        or run.get("selected_cpu") != "cpu5c"
        or run.get("creation_http_status") != 201
        or run.get("automatic_replacement_queued") is not False
        or run.get("uploaded_source_files") != 70
        or run.get("estimated_compute_cost_usd", 1) > 0.02
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
        or post_inventory.get("owned_pod_absent") is not True
        or post_inventory.get("inventories") != {"v1": [], "v2": []}
        or watchdog.get("status") != "controller_cleanup_verified"
        or watchdog.get("errors") != []
        or watchdog_done.get("owned_pod_absent_verified") is not True
        or controller_release.get("released") is not True
        or watchdog_release.get("released") is not True
        or host.get("status") != "pass"
        or host.get("prior_cpu_model") != "AMD EPYC 9655 96-Core Processor"
        or host.get("current_cpu_model") != "AMD EPYC 9575F 64-Core Processor"
        or host.get("cpu_model_differs") is not True
        or runtime.get("cpu_model") != host["current_cpu_model"]
        or runtime.get("runpod_pod_id") != run["pod_id"]
        or runtime.get("runpod_pod_id") != host["current_pod_id"]
        or clang.get("status") != "pass"
        or clang.get("apt_package") != "clang-14"
        or clang.get("apt_package_version") != "1:14.0.6-12"
        or binding.get("compiler_executable") != clang["compiler_executable"]
        or binding.get("compiler_executable_sha256") != clang["compiler_executable_sha256"]
        or binding.get("compiler_version") != clang["compiler_version"]
        or "clang version 14.0.6" not in binding.get("compiler_version", "")
    ):
        raise ValueError("cross-machine evidence, cleanup, host, or compiler binding mismatch")

    document = {
        "schema": "cm-architecture-query-ladder-cross-machine-local-verification/v1",
        "status": "verified_complete",
        "rows_reverified": recomputed["rows_checked"],
        "query_rows": recomputed["query_rows"],
        "counts": recomputed["counts"],
        "semantic_mismatches": 0,
        "schedule_mismatches": 0,
        "source_or_artifact_mismatches": 0,
        "memory_measurement_mismatches": 0,
        "manifest_source_mismatches": source_mismatches,
        "remote_verification_reproduced_byte_for_byte": True,
        "remote_verification_sha256": _sha256(STUDY / "independent_verification.json"),
        "results_sha256": _sha256(STUDY / "results.json"),
        "raw_measurements_sha256": _sha256(STUDY / "raw_measurements.jsonl"),
        "runtime_binding_sha256": _sha256(STUDY / "runtime_binding.json"),
        "run_sha256": _sha256(ATTEMPT / "RUN.json"),
        "transport_freeze_sha256": _sha256(ATTEMPT / "TRANSPORT-FREEZE.json"),
        "post_run_inventory_sha256": _sha256(POST_INVENTORY),
        "watchdog_result_sha256": _sha256(ATTEMPT / "WATCHDOG-RESULT.json"),
        "controller_guard_release_sha256": _sha256(
            ATTEMPT / "HOST-AWAKE-RELEASED-architecture-query-ladder-controller.json"
        ),
        "watchdog_guard_release_sha256": _sha256(
            ATTEMPT / "HOST-AWAKE-RELEASED-architecture-query-ladder-watchdog.json"
        ),
        "authorization_sha256": _sha256(AUTHORIZATION),
        "authorization_request_sha256": _sha256(REQUEST),
        "upload_manifest_sha256": _sha256(MANIFEST),
        "controller_sha256": _sha256(CONTROLLER),
        "pod_id": run["pod_id"],
        "machine_id": run["actual_resources"]["machine_id"],
        "cpu_flavor": run["selected_cpu"],
        "prior_cpu_model": host["prior_cpu_model"],
        "current_cpu_model": host["current_cpu_model"],
        "cpu_model_differs": True,
        "compiler": binding["compiler_executable"],
        "compiler_executable_sha256": binding["compiler_executable_sha256"],
        "compiler_version": binding["compiler_version"],
        "estimated_compute_cost_usd": run["estimated_compute_cost_usd"],
        "owned_pod_absent": True,
        "post_run_inventories": {"v1": [], "v2": []},
        "watchdog_status": watchdog["status"],
        "watchdog_errors": watchdog["errors"],
        "host_awake_guards_released": True,
        "selector_or_neural_claim_permitted": False,
        "website_update_permitted": False,
    }
    _write_new(OUTPUT, document)
    print(json.dumps({
        "status": document["status"],
        "rows_reverified": document["rows_reverified"],
        "local_verification_sha256": _sha256(OUTPUT),
        "cpu_model": document["current_cpu_model"],
        "compiler_executable_sha256": document["compiler_executable_sha256"],
        "estimated_compute_cost_usd": document["estimated_compute_cost_usd"],
        "owned_pod_absent": document["owned_pod_absent"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
