"""Guarded Runpod orchestrator for current selector cross-machine evidence.

Creates three independent secure Linux CPU pods sequentially, verifies a
content-addressed source/corpus snapshot on every pod, collects current
selector plus frozen-B1 evidence, and terminates each pod in ``finally``.

Safety invariants are fixed in code: total projected and actual cost below
$1, price below $0.25/hour, at most three pods, bounded setup/driver lifetime,
refuse-overwrite outputs, and no local fallback evidence.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import secrets
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

import requests


REPO = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

import cm_runpod_deploy as deploy
from cm_runpod_config import load_runpod_config


REST = "https://rest.runpod.io/v1"
N_PODS = 3
TOTAL_BUDGET_USD = 1.0
PRIOR_ATTEMPT_COST_RESERVE_USD = 0.01
MAX_PRICE_PER_HOUR_USD = 0.25
SETUP_TIMEOUT_S = 10 * 60
DRIVER_TIMEOUT_S = 22 * 60
HARD_LIFETIME_S = 35 * 60
OUT_DIR = BASE / "selector_runpod_2026_08_24_run2"
CAMPAIGN_NAME = "CM selector Runpod replication 2026-08-24"
WORKER_FILENAME = "cm_selector_runpod_worker_2026_08_24.py"
AUDIT_FILENAME = "selector_runpod_audit_2026_08_24.json"
IMAGE = "python:3.13.5-slim"
EXPECTED_NUMPY = "2.3.2"
LOCAL_B1_REFERENCE = 0.8876
SELECTOR_REGRET_GEOMEAN_MAX = 1.10

ARCHIVE_PATHS = (
    "scripts/cm_deep_performance_audit.py",
    "deliverables_n22_24/CM_gap_e3_corrected_corpus_2026_08_02.jsonl",
    "deliverables_n22_24/cm_gap_e3_corrected_2026_08_02.py",
    "deliverables_n22_24/bx1_crossover_2026_08_03/CM_bx1_crossover_corpus_2026_08_03.jsonl",
    "deliverables_n22_24/b2_wrapper_2026_08_03/CM_b2_wrapper_corpus_2026_08_03.jsonl",
    "deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl",
)

START_CMD = deploy.START_CMD.replace(
    "pip install --no-cache-dir numpy",
    f"pip install --no-cache-dir numpy=={EXPECTED_NUMPY}",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _snapshot_files() -> list[Path]:
    files = [path for path in REPO.glob("*.py") if path.is_file()]
    files.extend(path for path in (REPO / "cmbench").rglob("*.py") if path.is_file())
    files.extend(REPO / relative for relative in ARCHIVE_PATHS)
    unique = sorted(set(files), key=lambda path: path.relative_to(REPO).as_posix())
    missing = [str(path) for path in unique if not path.is_file()]
    if missing:
        raise RuntimeError("missing archive inputs: " + ", ".join(missing))
    return unique


def _make_archive(temp_dir: Path) -> tuple[Path, dict]:
    archive_path = temp_dir / "repo.zip"
    files = _snapshot_files()
    file_hashes = {
        path.relative_to(REPO).as_posix(): _sha256(path)
        for path in files
    }
    snapshot = {
        "campaign": CAMPAIGN_NAME,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files_sha256": file_hashes,
        "corpus_sha256": {
            "b1": file_hashes["deliverables_n22_24/CM_gap_e3_corrected_corpus_2026_08_02.jsonl"],
            "bx1": file_hashes["deliverables_n22_24/bx1_crossover_2026_08_03/CM_bx1_crossover_corpus_2026_08_03.jsonl"],
            "b2": file_hashes["deliverables_n22_24/b2_wrapper_2026_08_03/CM_b2_wrapper_corpus_2026_08_03.jsonl"],
            "epfl": file_hashes["deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl"],
        },
    }
    manifest_bytes = json.dumps(snapshot, indent=2, sort_keys=True).encode("utf-8")
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(REPO).as_posix())
        archive.writestr(
            "selector_runpod_snapshot_manifest_2026_08_24.json",
            manifest_bytes,
        )
    snapshot["archive_sha256"] = _sha256(archive_path)
    snapshot["archive_bytes"] = archive_path.stat().st_size
    return archive_path, snapshot


def _post_retry(url: str, **kwargs) -> requests.Response:
    last_error: object = None
    for _ in range(15):
        try:
            response = requests.post(url, **kwargs)
            if response.status_code not in (404, 502, 503):
                response.raise_for_status()
                return response
            last_error = f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(8)
    raise RuntimeError(f"POST failed after retries: {last_error}")


def _terminate(session: requests.Session, pod_id: str) -> bool:
    for _ in range(5):
        try:
            response = session.delete(f"{REST}/pods/{pod_id}", timeout=60)
            if response.ok or response.status_code == 404:
                return True
        except requests.RequestException:
            pass
        time.sleep(3)
    try:
        session.post(f"{REST}/pods/{pod_id}/stop", timeout=60)
    except requests.RequestException:
        pass
    return False


def _create_pod(
    session: requests.Session,
    token: str,
    index: int,
    spent_usd: float,
) -> tuple[str, str, int, float, float]:
    flavor_orders = (
        ("cpu3c", "cpu3m", "cpu5c"),
        ("cpu3m", "cpu5c", "cpu3c"),
        ("cpu5c", "cpu3c", "cpu3m"),
    )
    common = {
        "name": f"cm-selector-r{index}-{int(time.time())}",
        "computeType": "CPU",
        "cloudType": "SECURE",
        "imageName": IMAGE,
        "containerDiskInGb": 12,
        "volumeInGb": 10,
        "volumeMountPath": "/workspace",
        "ports": ["8080/http", "8081/http"],
        "env": {"CM_BOOTSTRAP_TOKEN": token},
        "dockerEntrypoint": ["sh", "-c"],
        "dockerStartCmd": [START_CMD],
    }
    errors = []
    for flavor in flavor_orders[index - 1]:
        response = session.post(
            f"{REST}/pods",
            json={**common, "cpuFlavorIds": [flavor], "vcpuCount": 2},
            timeout=180,
        )
        if not response.ok:
            errors.append(f"{flavor}: HTTP {response.status_code}")
            continue
        pod = response.json()
        pod_id = pod.get("id") or (pod.get("pod") or {}).get("id")
        cost_per_hour = float(
            pod.get("costPerHr") or (pod.get("pod") or {}).get("costPerHr") or 99
        )
        projected = cost_per_hour * HARD_LIFETIME_S / 3600
        if cost_per_hour >= MAX_PRICE_PER_HOUR_USD:
            _terminate(session, pod_id)
            raise RuntimeError(
                f"refusing pod price ${cost_per_hour:.4f}/hour "
                f"(cap ${MAX_PRICE_PER_HOUR_USD:.2f})"
            )
        if spent_usd + projected >= TOTAL_BUDGET_USD:
            _terminate(session, pod_id)
            raise RuntimeError(
                f"refusing projected total ${spent_usd + projected:.4f} "
                f"(hard cap ${TOTAL_BUDGET_USD:.2f})"
            )
        return pod_id, flavor, 2, cost_per_hour, projected
    raise RuntimeError("no CPU flavor available: " + "; ".join(errors))


def _safe_result_target(pod_dir: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise RuntimeError(f"unsafe result path from pod: {relative!r}")
    return pod_dir.joinpath(*pure.parts)


def _selector_acceptance(selector_path: Path) -> dict:
    with selector_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    current = [row for row in rows if row["is_current_policy"] == "True"]
    checks = []
    for row in current:
        geomean = float(row["regret_geomean"])
        catastrophic = int(row["catastrophic_ge_2_count"])
        checks.append(
            {
                "arm": row["arm"],
                "role": row["role"],
                "n": int(row["n"]),
                "refused_or_ineligible_count": int(row["refused_or_ineligible_count"]),
                "regret_geomean": geomean,
                "regret_ci95": [
                    float(row["regret_geomean_cluster_bootstrap_ci95_low"]),
                    float(row["regret_geomean_cluster_bootstrap_ci95_high"]),
                ],
                "regret_max": float(row["regret_max"]),
                "catastrophic_ge_2_count": catastrophic,
                "pass": geomean <= SELECTOR_REGRET_GEOMEAN_MAX and catastrophic == 0,
            }
        )
    return {
        "checks": checks,
        "pass": len(checks) == 4 and all(check["pass"] for check in checks),
        "gate": {
            "regret_geomean_max": SELECTOR_REGRET_GEOMEAN_MAX,
            "catastrophic_ge_2_count": 0,
        },
    }


def _b1_acceptance(results_path: Path) -> dict:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    all_rows = [
        row for row in results["summary_blocked"]
        if row.get("group") in {"all", "all-corpus", "all_corpus"}
    ]
    if len(all_rows) != 1:
        return {"pass": False, "error": "missing unique all-corpus B1 summary"}
    row = all_rows[0]
    geomean = float(row["geomean"])
    interval = [float(row["ci95_lo"]), float(row["ci95_hi"])]
    return {
        "geomean": geomean,
        "ci95": interval,
        "reference": LOCAL_B1_REFERENCE,
        "pass": abs(geomean - LOCAL_B1_REFERENCE) <= 0.05 and interval[1] < 1.0,
    }


def _run_pod(
    session: requests.Session,
    index: int,
    archive_path: Path,
    worker_path: Path,
    spent_usd: float,
) -> dict:
    token = secrets.token_urlsafe(24)
    record = {"pod_index": index, "status": "creating", "terminated": False}
    pod_id = None
    created = time.time()
    try:
        pod_id, flavor, vcpus, cost_per_hour, projected = _create_pod(
            session, token, index, spent_usd
        )
        record.update(
            {
                "pod_id": pod_id,
                "cpu_flavor": flavor,
                "vcpu_count": vcpus,
                "cost_per_hour_usd": cost_per_hour,
                "projected_hard_lifetime_cost_usd": projected,
                "status": "created",
            }
        )
        boot_url = f"https://{pod_id}-8080.proxy.runpod.net"
        worker_url = f"https://{pod_id}-8081.proxy.runpod.net"
        if not deploy._wait_health(boot_url, "cm-bootstrap", SETUP_TIMEOUT_S, 8.0):
            raise RuntimeError("bootstrap did not become healthy before setup timeout")
        headers = {"X-CM-Token": token}
        for source, remote_name in (
            (archive_path, "repo.zip"),
            (worker_path, "cm_remote_worker.py"),
        ):
            _post_retry(
                f"{boot_url}/put",
                json={
                    "name": remote_name,
                    "b64": base64.b64encode(source.read_bytes()).decode("ascii"),
                },
                headers=headers,
                timeout=300,
            )
        _post_retry(f"{boot_url}/deploy", json={}, headers=headers, timeout=60)

        driver_started = None
        deadline = created + HARD_LIFETIME_S
        state = {}
        while time.time() < deadline:
            try:
                state = requests.get(f"{worker_url}/progress", timeout=20).json()
            except Exception:
                state = state or {}
            stage = state.get("stage")
            if stage in {"selector-driver", "b1-control"} and driver_started is None:
                driver_started = time.time()
            if state.get("done") or state.get("error"):
                break
            if driver_started and time.time() - driver_started > DRIVER_TIMEOUT_S:
                raise RuntimeError("combined driver timeout exceeded")
            time.sleep(8)
        else:
            raise RuntimeError("hard pod lifetime exceeded")
        record["state"] = state
        if state.get("error"):
            raise RuntimeError(f"pod worker failed: {state['error'][-4000:]}")

        payload = requests.get(f"{worker_url}/results", timeout=180).json()
        files = payload.get("files", {})
        pod_dir = OUT_DIR / f"pod{index}_{pod_id}"
        pod_dir.mkdir(parents=True, exist_ok=False)
        for relative, encoded in files.items():
            target = _safe_result_target(pod_dir, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(base64.b64decode(encoded))
        record["files"] = sorted(files)
        selector_path = pod_dir / "deliverables_n22_24/pod_out/current_selector.csv"
        b1_path = pod_dir / (
            "deliverables_n22_24/pod_out/b1/"
            "cm_gap_e3_corrected_results_2026_08_02.json"
        )
        record["acceptance"] = {
            "selector": _selector_acceptance(selector_path),
            "b1_control": _b1_acceptance(b1_path),
        }
        record["acceptance"]["pass"] = (
            record["acceptance"]["selector"]["pass"]
            and record["acceptance"]["b1_control"]["pass"]
        )
        record["status"] = "complete"
    except Exception as exc:
        record["status"] = "orchestrator_error"
        record["error"] = str(exc)
    finally:
        if pod_id:
            record["terminated"] = _terminate(session, pod_id)
        record["lifetime_s"] = time.time() - created
        record["cost_usd_actual"] = round(
            record.get("cost_per_hour_usd", 0.0) * record["lifetime_s"] / 3600,
            6,
        )
    return record


def _write_audit(audit: dict) -> None:
    audit_path = OUT_DIR / AUDIT_FILENAME
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")


def _dry_run() -> int:
    with tempfile.TemporaryDirectory() as temp:
        archive_path, snapshot = _make_archive(Path(temp))
        with zipfile.ZipFile(archive_path) as archive:
            bad = archive.testzip()
        projected_max = (
            PRIOR_ATTEMPT_COST_RESERVE_USD
            + N_PODS * MAX_PRICE_PER_HOUR_USD * HARD_LIFETIME_S / 3600
        )
        print(
            json.dumps(
                {
                    "ok": bad is None and projected_max < TOTAL_BUDGET_USD,
                    "archive_sha256": snapshot["archive_sha256"],
                    "archive_bytes": snapshot["archive_bytes"],
                    "source_file_count": len(snapshot["files_sha256"]),
                    "corpus_sha256": snapshot["corpus_sha256"],
                    "n_pods": N_PODS,
                    "image": IMAGE,
                    "projected_max_cost_usd": projected_max,
                    "hard_budget_usd": TOTAL_BUDGET_USD,
                    "bad_zip_member": bad,
                },
                indent=2,
            )
        )
    return 0 if bad is None and projected_max < TOTAL_BUDGET_USD else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run:
        return _dry_run()

    config = load_runpod_config()
    if not config.api_key:
        raise SystemExit("Runpod API key is not configured")
    if OUT_DIR.exists():
        raise SystemExit(f"refusing to overwrite {OUT_DIR}")
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {config.api_key}"
    preflight = session.get(f"{REST}/pods", timeout=60)
    preflight.raise_for_status()
    OUT_DIR.mkdir(parents=True)
    audit = {
        "campaign": CAMPAIGN_NAME,
        "guards": {
            "n_pods": N_PODS,
            "total_budget_usd": TOTAL_BUDGET_USD,
            "max_price_per_hour_usd": MAX_PRICE_PER_HOUR_USD,
            "setup_timeout_s": SETUP_TIMEOUT_S,
            "driver_timeout_s": DRIVER_TIMEOUT_S,
            "hard_lifetime_s": HARD_LIFETIME_S,
            "image": IMAGE,
            "numpy": EXPECTED_NUMPY,
        },
        "pods": [],
        "prior_attempt_cost_reserve_usd": PRIOR_ATTEMPT_COST_RESERVE_USD,
        "total_cost_usd": PRIOR_ATTEMPT_COST_RESERVE_USD,
        "all_pods_terminated": False,
        "verdict": "running",
    }
    try:
        with tempfile.TemporaryDirectory() as temp:
            archive_path, snapshot = _make_archive(Path(temp))
            audit["snapshot"] = snapshot
            worker_path = BASE / WORKER_FILENAME
            for index in range(1, N_PODS + 1):
                spent = PRIOR_ATTEMPT_COST_RESERVE_USD + sum(
                    pod.get("cost_usd_actual", 0.0) for pod in audit["pods"]
                )
                if spent >= TOTAL_BUDGET_USD:
                    audit["pods"].append(
                        {
                            "pod_index": index,
                            "status": "skipped_budget_guard",
                            "spent_so_far_usd": spent,
                            "terminated": True,
                        }
                    )
                    continue
                print(f"pod {index}/{N_PODS} ...", flush=True)
                record = _run_pod(
                    session,
                    index,
                    archive_path,
                    worker_path,
                    spent,
                )
                audit["pods"].append(record)
                audit["total_cost_usd"] = round(
                    PRIOR_ATTEMPT_COST_RESERVE_USD
                    + sum(pod.get("cost_usd_actual", 0.0) for pod in audit["pods"]),
                    6,
                )
                _write_audit(audit)
                print(
                    f"pod {index}: {record['status']} "
                    f"acceptance={record.get('acceptance', {}).get('pass')} "
                    f"cost=${record.get('cost_usd_actual', 0.0):.6f} "
                    f"terminated={record.get('terminated')}",
                    flush=True,
                )
                if record.get("terminated") is not True:
                    print(
                        "termination could not be confirmed; refusing to create "
                        "any additional pods",
                        flush=True,
                    )
                    break
    finally:
        audit["total_cost_usd"] = round(
            PRIOR_ATTEMPT_COST_RESERVE_USD
            + sum(pod.get("cost_usd_actual", 0.0) for pod in audit["pods"]),
            6,
        )
        audit["all_pods_terminated"] = all(
            pod.get("terminated") is True for pod in audit["pods"]
        )
        complete = [pod for pod in audit["pods"] if pod.get("status") == "complete"]
        audit["verdict"] = (
            "passed"
            if len(complete) == N_PODS
            and audit["all_pods_terminated"]
            and audit["total_cost_usd"] < TOTAL_BUDGET_USD
            and all(pod.get("acceptance", {}).get("pass") for pod in complete)
            else "failed"
        )
        _write_audit(audit)
    print(
        json.dumps(
            {
                "verdict": audit["verdict"],
                "total_cost_usd": audit["total_cost_usd"],
                "all_pods_terminated": audit["all_pods_terminated"],
            },
            indent=2,
        )
    )
    return 0 if audit["verdict"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
