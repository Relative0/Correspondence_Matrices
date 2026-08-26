"""Guarded three-pod CM one-memo preparation replication."""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import math
import secrets
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import cm_selector_runpod_campaign_2026_08_24 as campaign


BASE = Path(__file__).resolve().parent
REPO = BASE.parent
campaign.OUT_DIR = BASE / "memo_runpod_2026_08_26"
campaign.CAMPAIGN_NAME = "CM one-memo preparation Runpod replication 2026-08-26"
campaign.WORKER_FILENAME = "cm_memo_runpod_worker_2026_08_26.py"
campaign.AUDIT_FILENAME = "memo_runpod_audit_2026_08_26.json"
campaign.N_PODS = 3
campaign.TOTAL_BUDGET_USD = 1.0
campaign.PRIOR_ATTEMPT_COST_RESERVE_USD = 0.0
campaign.MAX_PRICE_PER_HOUR_USD = 0.25
campaign.SETUP_TIMEOUT_S = 10 * 60
campaign.DRIVER_TIMEOUT_S = 55 * 60
campaign.HARD_LIFETIME_S = 65 * 60
campaign.ARCHIVE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cmbench/backends/bitset_engine.py",
    "cmbench/output_budget.py",
    "cmbench/reporting/__init__.py",
    "cmbench/reporting/provenance.py",
    "cmbench/reporting/summary_tables.py",
    "scripts/cm_benchmark_provenance.py",
    "scripts/cm_deep_performance_audit.py",
    "scripts/cm_prepare_memo_ablation.py",
    "deliverables_n22_24/bx1_crossover_2026_08_03/CM_bx1_crossover_corpus_2026_08_03.jsonl",
    "deliverables_n22_24/b2_wrapper_2026_08_03/CM_b2_wrapper_corpus_2026_08_03.jsonl",
    "deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl",
)


def _snapshot_files() -> list[Path]:
    files = [REPO / relative for relative in campaign.ARCHIVE_PATHS]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise RuntimeError("missing archive inputs: " + ", ".join(missing))
    return sorted(files, key=lambda path: path.relative_to(REPO).as_posix())


campaign._snapshot_files = _snapshot_files


def _make_archive(temp_dir: Path) -> tuple[Path, dict]:
    archive_path = temp_dir / "repo.zip"
    files = _snapshot_files()
    file_hashes = {
        path.relative_to(REPO).as_posix(): _sha(path)
        for path in files
    }
    snapshot = {
        "campaign": campaign.CAMPAIGN_NAME,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files_sha256": file_hashes,
        "corpus_sha256": {
            "bx1": file_hashes[
                "deliverables_n22_24/bx1_crossover_2026_08_03/CM_bx1_crossover_corpus_2026_08_03.jsonl"
            ],
            "b2": file_hashes[
                "deliverables_n22_24/b2_wrapper_2026_08_03/CM_b2_wrapper_corpus_2026_08_03.jsonl"
            ],
            "epfl": file_hashes["deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl"],
        },
    }
    manifest = json.dumps(snapshot, indent=2, sort_keys=True).encode("utf-8")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(REPO).as_posix())
        archive.writestr("selector_runpod_snapshot_manifest_2026_08_24.json", manifest)
    snapshot["archive_sha256"] = _sha(archive_path)
    snapshot["archive_bytes"] = archive_path.stat().st_size
    return archive_path, snapshot


campaign._make_archive = _make_archive


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _validate_rows(rows: list[dict[str, str]], expected: int) -> dict:
    ids = [row["id"] for row in rows]
    duplicate_ids = sorted({identifier for identifier in ids if ids.count(identifier) > 1})
    canonical_failures = [row["id"] for row in rows if row["canonical_key_equal"] != "True"]
    packed_failures = [row["id"] for row in rows if row["packed_output_equal"] != "True"]
    return {
        "rows": len(rows),
        "expected_rows": expected,
        "duplicate_ids": duplicate_ids,
        "canonical_failures": canonical_failures,
        "packed_failures": packed_failures,
        "candidate_over_baseline_geomean": (
            math.exp(sum(math.log(float(row["ratio"])) for row in rows) / len(rows))
            if rows
            else None
        ),
        "pass": len(rows) == expected and not duplicate_ids and not canonical_failures and not packed_failures,
    }


def _source_snapshots(pod_dir: Path) -> dict:
    manifests = sorted(pod_dir.glob("deliverables_n22_24/pod_out/*_source_snapshot/source_manifest.json"))
    failures = []
    file_count = 0
    for manifest_path in manifests:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in document["files"]:
            file_count += 1
            source = manifest_path.parent / entry["path"]
            if not source.is_file() or _sha(source) != entry["sha256"]:
                failures.append(source.relative_to(pod_dir).as_posix())
    return {
        "manifest_count": len(manifests),
        "file_count": file_count,
        "failures": failures,
        "pass": len(manifests) == 8 and not failures,
    }


def _acceptance(pod_dir: Path) -> dict:
    root = pod_dir / "deliverables_n22_24/pod_out"
    bx1_b2 = _validate_rows(_read_rows(root / "memo_bx1_b2_raw.csv"), 272)
    epfl_rows = []
    chunk_counts = {}
    for start, expected in ((0, 20), (20, 20), (40, 20), (60, 20), (80, 20), (100, 20), (120, 9)):
        rows = _read_rows(root / f"memo_epfl_{start:03d}_raw.csv")
        epfl_rows.extend(rows)
        chunk_counts[f"{start:03d}"] = len(rows)
        if len(rows) != expected:
            chunk_counts[f"{start:03d}_expected"] = expected
    epfl = _validate_rows(epfl_rows, 129)
    epfl["chunk_counts"] = chunk_counts
    snapshots = _source_snapshots(pod_dir)
    return {
        "bx1_b2": bx1_b2,
        "epfl": epfl,
        "source_snapshots": snapshots,
        "pass": bx1_b2["pass"] and epfl["pass"] and snapshots["pass"],
    }


def _run_pod(session, index: int, archive_path: Path, worker_path: Path, spent_usd: float) -> dict:
    token = secrets.token_urlsafe(24)
    record = {"pod_index": index, "status": "creating", "terminated": False}
    pod_id = None
    created = time.time()
    try:
        pod_id, flavor, vcpus, rate, projected = campaign._create_pod(
            session, token, index, spent_usd
        )
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
        boot_url = f"https://{pod_id}-8080.proxy.runpod.net"
        worker_url = f"https://{pod_id}-8081.proxy.runpod.net"
        if not campaign.deploy._wait_health(boot_url, "cm-bootstrap", campaign.SETUP_TIMEOUT_S, 8.0):
            raise RuntimeError("bootstrap did not become healthy before setup timeout")
        headers = {"X-CM-Token": token}
        uploads = (
            ("repo.zip", archive_path.read_bytes()),
            ("repo.zip.sha256", (_sha(archive_path) + "\n").encode("ascii")),
            ("cm_remote_worker.py", worker_path.read_bytes()),
        )
        for remote_name, content in uploads:
            campaign._post_retry(
                f"{boot_url}/put",
                json={"name": remote_name, "b64": base64.b64encode(content).decode("ascii")},
                headers=headers,
                timeout=300,
            )
        campaign._post_retry(f"{boot_url}/deploy", json={}, headers=headers, timeout=60)

        driver_started = None
        deadline = created + campaign.HARD_LIFETIME_S
        state = {}
        while time.time() < deadline:
            try:
                state = campaign.requests.get(f"{worker_url}/progress", timeout=20).json()
            except Exception:
                state = state or {}
            if state.get("stage") == "selector-driver" and driver_started is None:
                driver_started = time.time()
            if state.get("done") or state.get("error"):
                break
            if driver_started and time.time() - driver_started > campaign.DRIVER_TIMEOUT_S:
                raise RuntimeError("combined driver timeout exceeded")
            time.sleep(8)
        else:
            raise RuntimeError("hard pod lifetime exceeded")
        record["state"] = state
        if state.get("error"):
            raise RuntimeError(f"pod worker failed: {state['error'][-4000:]}")

        payload = campaign.requests.get(f"{worker_url}/results", timeout=300).json()
        files = payload.get("files", {})
        pod_dir = campaign.OUT_DIR / f"pod{index}_{pod_id}"
        pod_dir.mkdir(parents=True, exist_ok=False)
        for relative, encoded in files.items():
            target = campaign._safe_result_target(pod_dir, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(encoded))
        record["files"] = sorted(files)
        record["acceptance"] = _acceptance(pod_dir)
        record["status"] = "complete"
    except Exception as exc:
        record["status"] = "orchestrator_error"
        record["error"] = str(exc)
    finally:
        if pod_id:
            record["terminated"] = campaign._terminate(session, pod_id)
        record["lifetime_s"] = time.time() - created
        record["cost_usd_actual"] = round(
            record.get("cost_per_hour_usd", 0.0) * record["lifetime_s"] / 3600, 6
        )
    return record


campaign._run_pod = _run_pod


def _inventory() -> int:
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
        {"id": pod.get("id"), "name": pod.get("name"), "desired_status": pod.get("desiredStatus")}
        for pod in (pods or [])
    ]
    result = {"checked_utc": datetime.now(timezone.utc).isoformat(), "pod_count": len(summary), "pods": summary}
    path = campaign.OUT_DIR / "postflight_runpod_inventory.json"
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path}")
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not summary else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--inventory"]:
        raise SystemExit(_inventory())
    raise SystemExit(campaign.main())
