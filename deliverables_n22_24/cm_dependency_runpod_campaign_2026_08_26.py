"""Fail-closed one-pod campaign for optional CM dependency feasibility."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys
import tempfile
import time
import zipfile

import cm_selector_runpod_campaign_2026_08_24 as campaign


BASE = Path(__file__).resolve().parent
REPO = BASE.parent
CAMPAIGN_ROOT = (
    REPO
    / "docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541"
)
campaign.OUT_DIR = CAMPAIGN_ROOT / "runpod_dependency_feasibility"
campaign.CAMPAIGN_NAME = "CM optional dependency feasibility RP-D0 2026-08-26"
campaign.WORKER_FILENAME = "cm_dependency_runpod_worker_2026_08_26.py"
campaign.AUDIT_FILENAME = "dependency_runpod_audit_2026_08_26.json"
campaign.N_PODS = 1
campaign.TOTAL_BUDGET_USD = 0.25
campaign.PRIOR_ATTEMPT_COST_RESERVE_USD = 0.0
campaign.MAX_PRICE_PER_HOUR_USD = 0.20
campaign.SETUP_TIMEOUT_S = 8 * 60
campaign.DRIVER_TIMEOUT_S = 12 * 60
campaign.HARD_LIFETIME_S = 20 * 60
campaign.ARCHIVE_PATHS = (
    "deliverables_n22_24/cm_dependency_runpod_campaign_2026_08_26.py",
    "deliverables_n22_24/cm_dependency_runpod_worker_2026_08_26.py",
    "docs/audits/2026-08-25-cm-deep-performance/remaining-work/campaign-20260826-154541/PREREGISTRATION.md",
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
        raise RuntimeError("missing RP-D0 snapshot inputs: " + ", ".join(missing))
    return sorted(files, key=lambda path: path.relative_to(REPO).as_posix())


def _make_archive(temp_dir: Path) -> tuple[Path, dict]:
    archive_path = temp_dir / "rpd0_snapshot.zip"
    files = _snapshot_files()
    file_hashes = {path.relative_to(REPO).as_posix(): _sha256(path) for path in files}
    snapshot = {
        "campaign": campaign.CAMPAIGN_NAME,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files_sha256": file_hashes,
        "corpus_sha256": {},
    }
    manifest = json.dumps(snapshot, indent=2, sort_keys=True).encode("utf-8")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(REPO).as_posix())
        archive.writestr("rpd0_snapshot_manifest.json", manifest)
    snapshot["archive_sha256"] = _sha256(archive_path)
    snapshot["archive_bytes"] = archive_path.stat().st_size
    return archive_path, snapshot


campaign._snapshot_files = _snapshot_files
campaign._make_archive = _make_archive


def _acceptance(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "worker_acceptance": result.get("acceptance_pass") is True,
        "versions": result.get("versions_ok") is True,
        "numba_exact": result.get("numba_smoke", {}).get("exact_ok") is True,
        "cudd_exact": result.get("cudd_smoke", {}).get("exact_ok") is True,
        "no_performance_claim": result.get("performance_claim") is False,
        "wheels_hashed": bool(result.get("downloaded_distributions"))
        and all(len(item.get("sha256", "")) == 64 for item in result["downloaded_distributions"]),
    }
    return {"checks": checks, "pass": all(checks.values())}


def _run_pod(session, index: int, _archive_path: Path, worker_path: Path, spent_usd: float) -> dict:
    token = secrets.token_urlsafe(24)
    record: dict[str, object] = {"pod_index": index, "status": "creating", "terminated": False}
    pod_id = None
    created = time.time()
    try:
        pod_id, flavor, vcpus, rate, projected = campaign._create_pod(session, token, index, spent_usd)
        record.update(
            {
                "pod_id": pod_id,
                "cpu_flavor": flavor,
                "vcpu_count": vcpus,
                "cost_per_hour_usd": rate,
                "projected_hard_lifetime_cost_usd": projected,
                "status": "created",
            }
        )
        bootstrap_url = f"https://{pod_id}-8080.proxy.runpod.net"
        worker_url = f"https://{pod_id}-8081.proxy.runpod.net"
        if not campaign.deploy._wait_health(
            bootstrap_url, "cm-bootstrap", campaign.SETUP_TIMEOUT_S, 5.0
        ):
            raise RuntimeError("bootstrap did not become healthy before setup timeout")
        headers = {"X-CM-Token": token}
        campaign._post_retry(
            f"{bootstrap_url}/put",
            json={
                "name": "cm_remote_worker.py",
                "b64": base64.b64encode(worker_path.read_bytes()).decode("ascii"),
            },
            headers=headers,
            timeout=180,
        )
        campaign._post_retry(f"{bootstrap_url}/deploy", json={}, headers=headers, timeout=60)
        deadline = created + campaign.HARD_LIFETIME_S
        state: dict = {}
        while time.time() < deadline:
            try:
                response = campaign.requests.get(f"{worker_url}/progress", timeout=20)
                if response.ok:
                    state = response.json()
            except Exception:
                pass
            if state.get("done") or state.get("error"):
                break
            time.sleep(5)
        else:
            raise RuntimeError("hard pod lifetime exceeded")
        record["state"] = state
        payload = campaign.requests.get(f"{worker_url}/results", timeout=180).json()
        pod_dir = campaign.OUT_DIR / f"pod{index}_{pod_id}"
        pod_dir.mkdir(parents=True, exist_ok=False)
        files = payload.get("files", {})
        for relative, encoded in files.items():
            target = campaign._safe_result_target(pod_dir, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(encoded))
        record["files"] = sorted(files)
        if state.get("error"):
            raise RuntimeError(f"pod worker failed: {str(state['error'])[-6000:]}")
        result_path = pod_dir / "out/dependency_feasibility.json"
        if not result_path.is_file():
            raise RuntimeError("worker completed without dependency_feasibility.json")
        record["acceptance"] = _acceptance(result_path)
        record["status"] = "complete"
    except Exception as exc:
        record["status"] = "orchestrator_error"
        record["error"] = str(exc)
    finally:
        if pod_id:
            record["terminated"] = campaign._terminate(session, pod_id)
        record["lifetime_s"] = time.time() - created
        record["cost_usd_actual"] = round(
            float(record.get("cost_per_hour_usd", 0.0)) * float(record["lifetime_s"]) / 3600,
            6,
        )
    return record


campaign._run_pod = _run_pod


def _inventory(label: str) -> int:
    if label not in {"preflight", "postflight", "postflight_after_rpd0"}:
        raise SystemExit(
            "inventory label must be preflight, postflight, or postflight_after_rpd0"
        )
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
