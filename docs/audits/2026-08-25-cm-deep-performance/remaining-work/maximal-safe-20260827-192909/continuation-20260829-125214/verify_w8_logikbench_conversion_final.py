"""Independent saved-evidence verifier for the successful W8 conversion scout."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "w8-logikbench-conversion-v4-001"
EVIDENCE = OUTPUT / "evidence/run-output"
CONVERSION = EVIDENCE / "w8-conversion"
DESTINATION = HERE / "W8-LOGIKBENCH-CONVERSION-FINAL-AUDIT.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify() -> dict:
    run = load(OUTPUT / "RUN.json")
    transport = load(OUTPUT / "TRANSPORT-FREEZE.json")
    resource = load(OUTPUT / "POD-RESOURCE-CHECK.json")
    validation = load(EVIDENCE / "REMOTE-VALIDATION.json")
    runtime = load(EVIDENCE / "RUNTIME.json")
    before = load(EVIDENCE / "SOURCE-BEFORE.json")
    after = load(EVIDENCE / "SOURCE-AFTER.json")
    conversions = load(CONVERSION / "conversions.json")
    fixtures = load(CONVERSION / "fixture-summary.json")
    environment = load(CONVERSION / "environment.json")
    checksums = load(CONVERSION / "checksums.json")

    expected_hashes = {
        "controller_sha256": (HERE / "runpod_w8_logikbench_conversion_controller_v4.py"),
        "authorization_sha256": (HERE / "HTTP-W8-LOGIKBENCH-CONVERSION-V4-AUTHORIZED-20260830.json"),
        "proposal_sha256": (HERE / "RUNPOD-W8-LOGIKBENCH-CONVERSION-V3-RETRY-PROPOSAL-20260830.md"),
        "bootstrap_sha256": (HERE / "http_native_scout_bootstrap_v2.py"),
        "preflight_sha256": (HERE / "http_w8_logikbench_conversion_preflight_v2.py"),
        "remote_program_sha256": (HERE / "runpod_w8_logikbench_conversion_remote_v3.py"),
        "manifest_sha256": (HERE / "RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-MANIFEST-V3-20260830.json"),
        "source_bundle_sha256": (HERE / "RUNPOD-W8-LOGIKBENCH-CONVERSION-UPLOAD-BUNDLE-V3-20260830.zip"),
    }
    mismatched_transport_hashes = {
        key: {"recorded": transport.get(key), "actual": sha256(path)}
        for key, path in expected_hashes.items()
        if transport.get(key) != sha256(path)
    }

    archive = OUTPUT / "evidence.zip"
    archive_members_match = True
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        extracted = sorted(
            path.relative_to(OUTPUT / "evidence").as_posix()
            for path in (OUTPUT / "evidence").rglob("*") if path.is_file()
        )
        archive_members_match = sorted(names) == extracted
        if archive_members_match:
            for name in names:
                if zipped.read(name) != (OUTPUT / "evidence" / name).read_bytes():
                    archive_members_match = False
                    break

    checksum_rows = checksums.get("files") or []
    checksum_failures = []
    for row in checksum_rows:
        path = CONVERSION / row["path"]
        if (
            not path.is_file()
            or path.stat().st_size != row["bytes"]
            or sha256(path) != row["sha256"]
        ):
            checksum_failures.append(row["path"])
    expected_checksum_paths = sorted(
        path.relative_to(CONVERSION).as_posix()
        for path in CONVERSION.rglob("*")
        if path.is_file() and path.name != "checksums.json"
    )
    checksum_coverage_complete = sorted(row["path"] for row in checksum_rows) == expected_checksum_paths

    rows = conversions.get("rows") or []
    converted = [row for row in rows if row.get("status") == "converted"]
    rejected = [row for row in rows if row.get("status") == "rejected"]
    converted_failures = []
    for row in converted:
        path = CONVERSION / "converted" / (row["cluster_id"] + ".blif")
        if (
            not path.is_file()
            or path.stat().st_size != row.get("bytes")
            or sha256(path) != row.get("sha256")
        ):
            converted_failures.append(row["cluster_id"])
    fixture_ok = bool(
        fixtures.get("fixture_count") == 5
        and fixtures.get("semantic_equivalence") is True
        and len(fixtures.get("fixtures") or []) == 5
        and all(row.get("semantic_equivalence") is True for row in fixtures["fixtures"])
    )
    source_rows_ok = bool(
        len(before) == len(after) == 159
        and before == after
        and validation.get("source_unchanged") is True
        and validation.get("source_before_sha256") == validation.get("source_after_sha256")
    )
    resource_pod = resource.get("pod") or {}
    resource_ok = bool(
        resource_pod.get("id") == run.get("pod_id") == "gdephx6ldtg77z"
        and resource_pod.get("cpuFlavorId") == "cpu3c"
        and resource_pod.get("vcpuCount") == 2
        and resource_pod.get("memoryInGb") == 4
        and resource_pod.get("verified_v2_cloud") == "SECURE"
        and resource_pod.get("containerDiskInGb") == 12
        and type(resource_pod.get("volumeInGb")) is int
        and resource_pod.get("volumeInGb") == 0
        and resource.get("network_volume_present") is False
    )
    evidence_record = run.get("evidence") or {}
    cleanup = run.get("cleanup") or {}
    valid = bool(
        run.get("status") == "complete"
        and run.get("creation_http_status") == 201
        and run.get("uploaded_source_files") == 159
        and evidence_record.get("verified") is True
        and evidence_record.get("sha256") == sha256(archive)
        and evidence_record.get("bytes") == archive.stat().st_size
        and evidence_record.get("files") == len(names) == 94
        and archive_members_match
        and not mismatched_transport_hashes
        and validation.get("status") == "complete"
        and validation.get("validation_errors") == []
        and source_rows_ok
        and runtime.get("runpod_pod_id") == run.get("pod_id")
        and len(runtime.get("affinity") or []) == 2
        and environment.get("performance_measurement") is False
        and conversions.get("performance_measurement") is False
        and conversions.get("performance_claim_permitted") is False
        and conversions.get("attempted") == len(rows) == 70
        and conversions.get("converted") == len(converted) == 64
        and conversions.get("rejected") == len(rejected) == 6
        and conversions.get("retained_blif_bytes") == sum(row["bytes"] for row in converted) == 13542979
        and len({row["cluster_id"] for row in rows}) == 70
        and not converted_failures
        and fixture_ok
        and not checksum_failures
        and checksum_coverage_complete
        and resource_ok
        and cleanup.get("owned_pod_absent") is True
        and cleanup.get("inventories") == {"v1": [], "v2": []}
    )
    return {
        "schema": "cm-comparative-w8-logikbench-conversion-final-audit/v1",
        "verified": valid,
        "pod_id": run.get("pod_id"),
        "estimated_compute_cost_usd": run.get("estimated_compute_cost_usd"),
        "elapsed_since_create_s": run.get("elapsed_since_create_s"),
        "source_files": len(before),
        "source_unchanged": source_rows_ok,
        "transport_hashes_match": not mismatched_transport_hashes,
        "mismatched_transport_hashes": mismatched_transport_hashes,
        "resource_identity_matches": resource_ok,
        "evidence_archive_sha256": sha256(archive),
        "evidence_archive_members": len(names),
        "evidence_archive_members_match_extraction": archive_members_match,
        "conversion": {
            "attempted": len(rows),
            "converted": len(converted),
            "rejected": len(rejected),
            "retained_blif_bytes": sum(row["bytes"] for row in converted),
            "rejection_reasons": dict(sorted(Counter(row.get("error") for row in rejected).items())),
            "rejected_clusters": [row["cluster_id"] for row in rejected],
            "converted_payload_failures": converted_failures,
        },
        "fixtures": {"count": 5, "semantic_equivalence": fixture_ok},
        "checksums": {
            "rows": len(checksum_rows),
            "failures": checksum_failures,
            "coverage_complete": checksum_coverage_complete,
        },
        "runtime": {
            "python": runtime.get("python"),
            "platform": runtime.get("platform"),
            "logical_cpus_host_visible": runtime.get("logical_cpus_host_visible"),
            "affinity": runtime.get("affinity"),
            "yosys_version": environment.get("yosys_version"),
            "yosys_package": environment.get("yosys_package"),
        },
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "cleanup_verified": cleanup.get("owned_pod_absent") is True,
    }


if __name__ == "__main__":
    if DESTINATION.exists():
        raise RuntimeError("final W8 audit output already exists")
    result = verify()
    DESTINATION.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["verified"] else 1)
