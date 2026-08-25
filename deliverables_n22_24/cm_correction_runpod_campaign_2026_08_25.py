"""Guarded three-pod replication of the corrected CM benchmark audit."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import cm_selector_runpod_campaign_2026_08_24 as campaign

BASE = Path(__file__).resolve().parent
campaign.OUT_DIR = BASE / "correction_runpod_2026_08_25"
campaign.CAMPAIGN_NAME = "CM corrected benchmark Runpod replication 2026-08-25"
campaign.WORKER_FILENAME = "cm_correction_runpod_worker_2026_08_25.py"
campaign.AUDIT_FILENAME = "correction_runpod_audit_2026_08_25.json"
campaign.PRIOR_ATTEMPT_COST_RESERVE_USD = 0.021215
campaign.ARCHIVE_PATHS += (
    "scripts/cm_benchmark_provenance.py",
    "scripts/cm_selector_gap_study.py",
    "scripts/cm_symmetric_wrapper_followup.py",
    "deliverables_n22_24/followups_2026_08_24/selector_gap/selector_gap_corpus.jsonl",
    "deliverables_n22_24/b4_sweep_2026_08_03/CM_b4_headline_corpus_2026_08_03.jsonl",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _source_snapshots(pod_dir: Path) -> dict:
    manifests = sorted(
        pod_dir.glob(
            "deliverables_n22_24/pod_out/**/*_source_snapshot/source_manifest.json"
        )
    )
    failures = []
    file_count = 0
    for manifest_path in manifests:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in document["files"]:
            file_count += 1
            source_path = manifest_path.parent / entry["path"]
            if not source_path.is_file() or _sha(source_path) != entry["sha256"]:
                failures.append(
                    source_path.relative_to(pod_dir).as_posix()
                )
    return {
        "manifest_count": len(manifests),
        "file_count": file_count,
        "failures": failures,
        "pass": len(manifests) == 3 and not failures,
    }


def _integrity_acceptance(pod_dir: Path) -> dict:
    root = pod_dir / "deliverables_n22_24/pod_out"
    selector = _csv_rows(root / "current_raw.csv")
    gap = _csv_rows(root / "gap/current_raw.csv")
    symmetric = _csv_rows(root / "symmetric/current_raw.csv")

    selector_failures = [
        row["id"]
        for row in selector
        if row["frozen_truth_sha256_verified"] != row["truth_sha256_expected"]
        or row["packed_equal"] != "True"
    ]
    gap_failures = [
        row["id"]
        for row in gap
        if row["frozen_truth_sha256_verified"] != row["truth_sha256_expected"]
        or row["packed_equal"] != "True"
    ]
    symmetric_failures = [
        row["id"]
        for row in symmetric
        if row["packed_sha256"] != row["truth_sha256_expected"]
        or row["packed_equal_all_arms"] != "True"
    ]
    roles = {
        role: sum(row["role"] == role for row in selector)
        for role in {row["role"] for row in selector}
    }
    snapshots = _source_snapshots(pod_dir)
    checks = {
        "selector": {
            "rows": len(selector),
            "failures": selector_failures,
            "roles": roles,
            "pass": len(selector) == 401
            and roles == {"tuning": 80, "validation_reused": 321}
            and not selector_failures,
        },
        "selector_gap": {
            "rows": len(gap),
            "failures": gap_failures,
            "pass": len(gap) == 71 and not gap_failures,
        },
        "symmetric": {
            "rows": len(symmetric),
            "failures": symmetric_failures,
            "pass": len(symmetric) == 264 and not symmetric_failures,
        },
        "source_snapshots": snapshots,
    }
    checks["pass"] = all(
        checks[name]["pass"]
        for name in ("selector", "selector_gap", "symmetric", "source_snapshots")
    )
    return checks


_base_run_pod = campaign._run_pod


def _run_pod(*args, **kwargs) -> dict:
    record = _base_run_pod(*args, **kwargs)
    if record.get("status") != "complete":
        return record
    index = int(record["pod_index"])
    pod_id = str(record["pod_id"])
    pod_dir = campaign.OUT_DIR / f"pod{index}_{pod_id}"
    performance_gate = record["acceptance"].pop("selector")
    integrity = _integrity_acceptance(pod_dir)
    gap_audit = json.loads(
        (
            pod_dir
            / "deliverables_n22_24/pod_out/gap/current_audit.json"
        ).read_text(encoding="utf-8")
    )
    record["acceptance"].update(
        {
            "selector_performance_gate": performance_gate,
            "selector_gap_performance_gate": gap_audit["acceptance"],
            "correction_integrity": integrity,
        }
    )
    record["acceptance"]["pass"] = bool(
        integrity["pass"] and record["acceptance"]["b1_control"]["pass"]
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
        {
            "id": pod.get("id"),
            "name": pod.get("name"),
            "desired_status": pod.get("desiredStatus"),
        }
        for pod in (pods or [])
    ]
    result = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "pod_count": len(summary),
        "pods": summary,
    }
    output_path = campaign.OUT_DIR / "postflight_runpod_inventory.json"
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite {output_path}")
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if not summary else 1


def _write_evidence_manifest() -> int:
    output_path = campaign.OUT_DIR / "runpod_evidence_manifest.json"
    if output_path.exists():
        raise SystemExit(f"refusing to overwrite {output_path}")
    files = []
    for path in sorted(campaign.OUT_DIR.rglob("*")):
        if path.is_file() and path != output_path:
            files.append(
                {
                    "path": path.relative_to(campaign.OUT_DIR).as_posix(),
                    "sha256": _sha(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    audit = json.loads(
        (campaign.OUT_DIR / campaign.AUDIT_FILENAME).read_text(encoding="utf-8")
    )
    inventory = json.loads(
        (campaign.OUT_DIR / "postflight_runpod_inventory.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = {
        "campaign": campaign.CAMPAIGN_NAME,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "files": files,
        "postflight_pod_count": inventory["pod_count"],
        "runpod_verdict": audit["verdict"],
        "schema_version": 1,
        "total_cost_usd": audit["total_cost_usd"],
    }
    output_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "path": str(output_path),
                "file_count": len(files),
                "sha256": _sha(output_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--inventory"]:
        raise SystemExit(_inventory())
    if sys.argv[1:] == ["--manifest"]:
        raise SystemExit(_write_evidence_manifest())
    raise SystemExit(campaign.main())
