"""Hardened controller for the separately authorized successor screen."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import cm_benchmark_runpod_results_controller_v2 as controller  # noqa: E402


CAMPAIGN = "cm-mega-successor-20260914-009"
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
PRELAUNCH = BASE / "successor-prelaunch-002"
AUTHORIZATION = PRELAUNCH / "RUNPOD_AUTHORIZATION.json"
REQUEST = PRELAUNCH / "RUNPOD_APPROVAL_REQUEST.json"
MANIFEST = PRELAUNCH / "UPLOAD_MANIFEST.json"
READINESS = BASE / "account-readiness-successor-001/ACCOUNT_READINESS.json"
POSTFIX_SMOKE = BASE / "postfix-linux-smoke-001/RESULT.json"
CORRECTED_REPLAY = BASE / "wsl-successor-remote-replay-003/REPLAY.json"
PRIOR_RECONCILIATION = BASE / "campaign-reconciliation-003/RUNPOD_RECONCILIATION.json"
BOOTSTRAP = ROOT / "scripts/cm_benchmark_runpod_bootstrap_v2.py"
REMOTE = ROOT / "scripts/cm_benchmark_runpod_successor_remote.py"
CORE_SCREEN = ROOT / "scripts/cm_benchmark_core_screen_v2.py"
CORE_PLAN = PRELAUNCH / "PLAN.json"
EXPECTED_OUT = BASE / "runpod-successor-001"
PHASE_HOURS = 2.0
PHASE_COST_CAP = 1.35


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def bound_hashes() -> dict[str, str]:
    return {
        "upload_manifest": digest(MANIFEST),
        "account_readiness": digest(READINESS),
        "postfix_linux_smoke": digest(POSTFIX_SMOKE),
        "corrected_wsl_remote_replay": digest(CORRECTED_REPLAY),
        "prior_campaign_reconciliation": digest(PRIOR_RECONCILIATION),
        "bootstrap": digest(BOOTSTRAP),
        "remote_worker": digest(REMOTE),
        "core_screen_runner": digest(CORE_SCREEN),
        "core_screen_plan": digest(CORE_PLAN),
        "controller": digest(Path(__file__).resolve()),
    }


def require_authorization() -> tuple[dict, dict, dict]:
    authorization = load(AUTHORIZATION)
    request = load(REQUEST)
    manifest = load(MANIFEST)
    readiness = load(READINESS)
    smoke = load(POSTFIX_SMOKE)
    replay = load(CORRECTED_REPLAY)
    reconciliation = load(PRIOR_RECONCILIATION)
    plan = load(CORE_PLAN)
    bound = bound_hashes()
    if (
        authorization.get("authorized") is not True
        or authorization.get("campaign_id") != CAMPAIGN
        or authorization.get("request_sha256") != digest(REQUEST)
        or authorization.get("exact_authorized_text")
        != request.get("approval_text_to_repeat")
        or authorization.get("bound_sha256") != bound
        or request.get("bound_sha256") != bound
        or authorization.get("maximum_total_pods") != 1
        or authorization.get("maximum_concurrent_pods") != 1
        or authorization.get("maximum_phase_pod_hours") != PHASE_HOURS
        or authorization.get("maximum_phase_runpod_charges_usd") != PHASE_COST_CAP
        or authorization.get("automatic_replacement") is not False
        or authorization.get("further_creation_after_failure") is not False
        or any(
            authorization.get(key) is not False
            for key in (
                "production_changes",
                "commit",
                "push",
                "publication",
                "credential_upload",
                "unrelated_resource_mutation",
            )
        )
        or manifest.get("campaign_id") != CAMPAIGN
        or manifest.get("authorization_granted") is not False
        or len(manifest.get("bundles", [])) != 1
        or len(manifest.get("controls", [])) != 2
        or plan.get("campaign_id") != CAMPAIGN
        or len(plan.get("cells", [])) != 108
        or smoke.get("status") != "passed"
        or smoke["d4_selected_exact_replay"]["status_counts"]["error"] != 0
        or replay.get("status") != "passed"
        or replay.get("summary", {}).get("core_screen", {}).get("cells") != 108
        or replay.get("summary", {}).get("core_screen", {}).get("correctness_mismatches")
        or replay.get("summary", {}).get("core_screen", {}).get("status_counts", {}).get("worker_error", 0)
        or replay.get("summary", {}).get("core_screen", {}).get("status_counts", {}).get("error", 0)
        or readiness.get("campaign_id") != CAMPAIGN
        or readiness.get("transport", {}).get("resource_writes") != 0
        or readiness.get("inventory", {}).get("v1", {}).get("pod_count") != 0
        or readiness.get("inventory", {}).get("v2", {}).get("pod_count") != 0
        or reconciliation.get("inventories", {}).get("v1_pod_count") != 0
        or reconciliation.get("inventories", {}).get("v2_pod_count") != 0
    ):
        raise RuntimeError("successor authorization or frozen evidence mismatch")
    for row in manifest["bundles"]:
        path = PRELAUNCH / row["path"]
        if path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise RuntimeError("authorized successor shard changed")
    return authorization, request, manifest


def extract_artifact(out: Path, data: bytes) -> dict:
    if len(data) > controller.RESULT_CAP:
        raise RuntimeError("successor result cap exceeded")
    archive_path = out / "evidence.zip"
    archive_path.write_bytes(data)
    evidence = out / "evidence"
    evidence.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        for info in infos:
            pure = PurePosixPath(info.filename)
            if pure.is_absolute() or ".." in pure.parts or info.is_dir():
                raise RuntimeError("unsafe successor result member")
            target = evidence.joinpath(*pure.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
    summary = load(evidence / "SUMMARY.json")
    core = summary.get("core_screen") or {}
    if (
        summary.get("status") != "passed"
        or summary.get("shards") != 1
        or summary.get("schema") != "cm-benchmark-runpod-successor-screen/v1"
        or core.get("cells") != 108
        or core.get("correctness_mismatches")
        or summary.get("benchmark_measurements", 0) <= 0
    ):
        raise RuntimeError("retrieved successor summary failed")
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "files": len(infos),
        "summary": summary,
    }


# Bind the reviewed successor constants and fail-closed checks into the hardened
# controller implementation. The active file identity is this wrapper so its
# watchdog subprocess re-applies the same bindings.
controller.__file__ = __file__
controller.BASE = BASE
controller.PRELAUNCH = PRELAUNCH
controller.AUTHORIZATION = AUTHORIZATION
controller.REQUEST = REQUEST
controller.MANIFEST = MANIFEST
controller.BOOTSTRAP = BOOTSTRAP
controller.REMOTE = REMOTE
controller.CORE_SCREEN = CORE_SCREEN
controller.CORE_PLAN = CORE_PLAN
controller.EXPECTED_OUT = EXPECTED_OUT
controller.CAMPAIGN = CAMPAIGN
controller.LIFETIME = int(PHASE_HOURS * 3600)
controller.HORIZON = controller.LIFETIME + 300
controller.PHASE_COST_CAP = PHASE_COST_CAP
controller.require_authorization = require_authorization
controller.extract_artifact = extract_artifact


def main() -> int:
    return controller.main()


if __name__ == "__main__":
    raise SystemExit(main())
