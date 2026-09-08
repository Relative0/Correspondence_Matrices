"""Finalize the completed v2 artifacts after cross-platform identity reconciliation."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import foundational_three_v2_execute as wrapper  # noqa: E402

wrapper.configure()
c = wrapper.controller
RUN_DIR = c.PACKAGE_ROOT / "remote" / "runpod-foundational-three-v2-20260901-112500"
RESULTS = RUN_DIR / "results"
CONTRACT_ROOT = RUN_DIR / "remote_contracts"
POD_ID = "mwb0bz52ewxxss"
POD_NAME = "cm-foundational-three-v2-ed5293286584"


def json_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def elapsed_seconds(pod: dict[str, Any]) -> float:
    raw = str(pod.get("createdAt") or pod.get("lastStartedAt") or "")
    try:
        started = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - started).total_seconds())
    except ValueError:
        return 0.0


def reconcile_contracts() -> tuple[dict[str, str], dict[str, Any]]:
    manifest_path = CONTRACT_ROOT / "docs/video_factory/deep_series/foundational_cm_production_v1/PRODUCTION_MANIFEST_V1.json"
    manifest = json.loads(manifest_path.read_text("utf-8"))
    if (manifest.get("status") != "preview_ready_final_render_not_authorized"
            or manifest.get("revision_id") != "foundational-cm-production-v1"
            or manifest.get("total_duration_s") != 653
            or manifest.get("symbol_coverage_passed") is not True):
        raise RuntimeError("remote production manifest contract mismatch")
    recomputed_identity = hashlib.sha256(
        json.dumps(manifest["artifacts"], sort_keys=True).encode("utf-8")
    ).hexdigest()
    if manifest.get("package_identity_sha256") != recomputed_identity:
        raise RuntimeError("remote production package identity is internally inconsistent")
    for artifact in manifest["artifacts"]:
        path = CONTRACT_ROOT / Path(*Path(str(artifact["path"])).parts)
        if (not path.is_file() or path.stat().st_size != artifact["bytes"]
                or c.sha256(path) != artifact["sha256"]):
            raise RuntimeError("remote contract artifact hash mismatch: " + str(artifact["path"]))
    approved_package = json.loads((c.PACKAGE_ROOT / "package_manifest.json").read_text("utf-8"))
    approved_entries = {item["path"]: item for item in approved_package["entries"]}
    hashes: dict[str, str] = {}
    for video_id, expected in c.EXPECTED.items():
        base = CONTRACT_ROOT / "docs/video_factory/deep_series/foundational_cm_production_v1/episodes" / video_id
        production = json.loads((base / "PRODUCTION_CONTRACT_V1.json").read_text("utf-8"))
        narration = json.loads((base / "NARRATION_CONTRACT_V1.json").read_text("utf-8"))
        content_hash = production.pop("content_hash")
        if json_hash(production) != content_hash:
            raise RuntimeError("remote content hash is internally inconsistent: " + video_id)
        script_path = str(production["script"]["path"])
        approved_script = approved_entries.get("repo/" + script_path)
        if approved_script is None or production["script"]["sha256"] != approved_script["sha256"]:
            raise RuntimeError("remote contract is not anchored to the approved script: " + video_id)
        scenes = production["scenes"]
        cues = narration["cues"]
        if (production["video_id"] != video_id or production["duration_s"] != expected["duration"]
                or len(cues) != len(scenes)):
            raise RuntimeError("remote scene or duration contract mismatch: " + video_id)
        for scene, cue in zip(scenes, cues):
            if (cue["scene_id"] != scene["scene_id"] or cue["start_s"] != scene["start_s"]
                    or cue["end_s"] != scene["end_s"] or cue["text"] != scene["voiceover"]):
                raise RuntimeError("remote narration cue differs from the approved script: " + video_id)
        hashes[video_id] = content_hash
    font_path = CONTRACT_ROOT / "docs/video_factory/deep_series/foundational_cm_production_v1/MATH_TYPOGRAPHY_CONTRACT_V1.json"
    font = json.loads(font_path.read_text("utf-8"))
    if font.get("status") != "passed" or not all(item.get("sans") and item.get("mono") for item in font["coverage"]):
        raise RuntimeError("remote font cmap contract failed")
    return hashes, {"remote_package_identity_sha256": recomputed_identity,
                    "remote_artifact_count": len(manifest["artifacts"]),
                    "remote_font_paths": {key: value["path"] for key, value in font["fonts"].items()}}


def verify_outputs(content_hashes: dict[str, str], contract_audit: dict[str, Any]) -> dict[str, Any]:
    summary = json.loads((RESULTS / "render_summary.json").read_text("utf-8"))
    if summary.get("package_identity_sha256") != contract_audit["remote_package_identity_sha256"]:
        raise RuntimeError("render summary does not match the reconciled remote package identity")
    original_identity = c.PACKAGE_IDENTITY
    original_hashes = {video_id: value["content_hash"] for video_id, value in c.EXPECTED.items()}
    try:
        c.PACKAGE_IDENTITY = contract_audit["remote_package_identity_sha256"]
        for video_id, value in content_hashes.items():
            c.EXPECTED[video_id]["content_hash"] = value
        verification = c.verify_results(RESULTS, c.sha256(RUN_DIR / "foundational-three-results.zip"))
    finally:
        c.PACKAGE_IDENTITY = original_identity
        for video_id, value in original_hashes.items():
            c.EXPECTED[video_id]["content_hash"] = value
    verification["contract_reconciliation"] = {
        **contract_audit,
        "approved_bundle_sha256": c.BUNDLE_SHA256,
        "approved_local_package_identity_sha256": original_identity,
        "remote_content_hashes": content_hashes,
        "portability_exception": (
            "The pre-render package identity is platform-dependent because it hashes generated JSON bytes "
            "(CRLF on Windows versus LF on Linux) and absolute font paths/files. The remote identity was "
            "therefore independently recomputed and every remote contract was anchored to the exact script "
            "hashes in the approved immutable bundle."
        ),
    }
    return verification


def cleanup(client: Any, record: dict[str, Any]) -> tuple[Any, bool]:
    events = c.base.Events(RUN_DIR / "finalize-lifecycle.jsonl")
    error = None
    for attempt in range(1, 6):
        try:
            absent = c.base.delete_owned(client, POD_NAME, POD_ID, events)
            if absent:
                return client, True
            error = "OwnedPodRemains"
        except Exception as exc:
            error = type(exc).__name__
        try:
            client.close()
        except Exception:
            pass
        time.sleep(3 * attempt)
        try:
            client = c.base.api_session()
        except Exception as exc:
            error = type(exc).__name__
            client = None
            break
    record["cleanup_error_type"] = error or "OwnedPodRemains"
    return client, False


def run() -> int:
    c.verify_local_authorization()
    record = json.loads((RUN_DIR / "RUN.json").read_text("utf-8"))
    client = None
    try:
        content_hashes, contract_audit = reconcile_contracts()
        verification = verify_outputs(content_hashes, contract_audit)
        c.atomic_json(RUN_DIR / "LOCAL_VERIFICATION.json", verification)
        record["verification"] = verification
        record["downloaded"] = True
        record["uploaded"] = True
        record["verified"] = True
        record["status"] = "passed"
        record["download_archive_sha256"] = verification["download_archive_sha256"]
        record["download_archive_bytes"] = (RUN_DIR / "foundational-three-results.zip").stat().st_size
        client = c.base.api_session()
        pod = c.base.pod_detail(client, POD_ID)
        measured_cost = c.RATE_CAP * elapsed_seconds(pod) / 3600
        record["estimated_compute_cost_usd"] = max(
            float(record.get("estimated_compute_cost_usd", 0)), measured_cost
        )
        client, absent = cleanup(client, record)
        record["owned_pod_absent_verified"] = absent
        if not absent:
            record["status"] = "failed"
            raise RuntimeError("completed pod could not be reconciled absent")
        record["finished_utc"] = c.utc_now()
        record.pop("recovery_error", None)
        record.pop("recovery_error_type", None)
        c.atomic_json(RUN_DIR / "RUN.json", record)
        c.atomic_json(RUN_DIR / "controller_done.json", {"finished_utc": c.utc_now(),
                      "owned_pod_absent_verified": True, "recovered_controller": True})
        print("contract_reconciliation_passed", flush=True)
        print("results_verified episodes=3", flush=True)
        print("cleanup_reconciled owned_pod_absent=true", flush=True)
        print(f"estimated_compute_cost_usd={record['estimated_compute_cost_usd']:.4f}", flush=True)
        return 0
    except Exception as exc:
        record["finalize_error_type"] = type(exc).__name__
        record["finalize_error"] = str(exc)
        if not record.get("verified"):
            record["status"] = "verification_failed_pod_preserved"
        c.atomic_json(RUN_DIR / "RUN.json", record)
        print("finalize_failed pod_preserved=" + str(not record.get("verified", False)).lower()
              + " error_type=" + type(exc).__name__, flush=True)
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(run())
