"""Fail-closed final RP-D0 campaign with a complete build-tool wheelhouse."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import cm_dependency_runpod_campaign_2026_08_26 as prior


campaign = prior.campaign
BASE = Path(__file__).resolve().parent
REPO = BASE.parent
CAMPAIGN_ROOT = (
    REPO
    / "docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541"
)
campaign.OUT_DIR = CAMPAIGN_ROOT / "runpod_dependency_feasibility_run3"
campaign.CAMPAIGN_NAME = "CM optional dependency feasibility RP-D0 Run 3 2026-08-26"
campaign.WORKER_FILENAME = "cm_dependency_runpod_worker_run3_2026_08_26.py"
campaign.AUDIT_FILENAME = "dependency_runpod_audit_run3_2026_08_26.json"
campaign.N_PODS = 1
campaign.TOTAL_BUDGET_USD = 0.25
campaign.PRIOR_ATTEMPT_COST_RESERVE_USD = 0.001302
campaign.MAX_PRICE_PER_HOUR_USD = 0.20
campaign.SETUP_TIMEOUT_S = 8 * 60
campaign.DRIVER_TIMEOUT_S = 12 * 60
campaign.HARD_LIFETIME_S = 20 * 60
campaign.ARCHIVE_PATHS = (
    "deliverables_n22_24/cm_dependency_runpod_campaign_run3_2026_08_26.py",
    "deliverables_n22_24/cm_dependency_runpod_worker_run3_2026_08_26.py",
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/PREREGISTRATION-RPD0-RUN3.md",
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/runpod_dependency_feasibility/dependency_runpod_audit_2026_08_26.json",
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/runpod_dependency_feasibility_run2/dependency_runpod_audit_run2_2026_08_26.json",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _snapshot_files() -> list[Path]:
    files = [REPO / relative for relative in campaign.ARCHIVE_PATHS]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise RuntimeError("missing RP-D0 Run 3 snapshot inputs: " + ", ".join(missing))
    return sorted(files, key=lambda path: path.relative_to(REPO).as_posix())


def _make_archive(temp_dir: Path) -> tuple[Path, dict]:
    archive_path = temp_dir / "rpd0_run3_snapshot.zip"
    files = _snapshot_files()
    file_hashes = {path.relative_to(REPO).as_posix(): _sha256(path) for path in files}
    snapshot = {
        "campaign": campaign.CAMPAIGN_NAME,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files_sha256": file_hashes,
        "corpus_sha256": {},
        "prior_attempt_cost_reserve_usd": campaign.PRIOR_ATTEMPT_COST_RESERVE_USD,
    }
    manifest = json.dumps(snapshot, indent=2, sort_keys=True).encode("utf-8")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(REPO).as_posix())
        archive.writestr("rpd0_run3_snapshot_manifest.json", manifest)
    snapshot["archive_sha256"] = _sha256(archive_path)
    snapshot["archive_bytes"] = archive_path.stat().st_size
    return archive_path, snapshot


campaign._snapshot_files = _snapshot_files
campaign._make_archive = _make_archive
campaign._run_pod = prior._run_pod


def _inventory(label: str) -> int:
    if label not in {"run3_preflight", "run3_postflight"}:
        raise SystemExit("inventory label must be run3_preflight or run3_postflight")
    config = campaign.load_runpod_config()
    if not config.api_key:
        raise SystemExit("Runpod API key is not configured")
    session = campaign.requests.Session()
    session.headers["Authorization"] = f"Bearer {config.api_key}"
    response = session.get(f"{campaign.REST}/pods", timeout=60)
    response.raise_for_status()
    payload = response.json()
    pods = payload.get("pods", []) if isinstance(payload, dict) else payload
    summary = [
        {
            "id": pod.get("id"),
            "name": pod.get("name"),
            "desired_status": pod.get("desiredStatus"),
        }
        for pod in (pods or [])
    ]
    result = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "pod_count": len(summary),
        "pods": summary,
    }
    path = CAMPAIGN_ROOT / f"runpod_{label}_inventory.json"
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path}")
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not summary else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--inventory":
        raise SystemExit(_inventory(sys.argv[2]))
    raise SystemExit(campaign.main())
