"""Independent saved-evidence audit for the successful W8 semantic scout."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
RUN_ROOT = HERE / "w8-logikbench-semantic-v3-001"
EVIDENCE = RUN_ROOT / "evidence/run-output"
SEMANTIC = EVIDENCE / "w8-semantic"
CONVERSION = HERE / "w8-logikbench-conversion-v4-001/evidence/run-output/w8-conversion"
MANIFEST = HERE / "RUNPOD-W8-LOGIKBENCH-SEMANTIC-UPLOAD-MANIFEST-V1-20260830.json"
OUTPUT = HERE / "W8-LOGIKBENCH-SEMANTIC-FINAL-AUDIT.json"
EXPECTED_ARCHIVE_SHA256 = "e4bafaba09ae4a498c889d1a9e1ab766998384f3d878f5c5454795feb9872e5f"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def root_key(cluster_id: str, root: str) -> str:
    return digest(("cm-w8-root-v1\0" + cluster_id + "\0" + root).encode())


def primary_key(row: dict) -> str:
    return digest((
        "cm-w8-primary-v1\0" + row["cluster_id"] + "\0" + row["root"]
        + "\0" + row["blif_sha256"]
    ).encode())


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("final semantic audit already exists")
    failures: list[str] = []
    run = load(RUN_ROOT / "RUN.json")
    identity = load(RUN_ROOT / "POD-IDENTITY.json")
    resource = load(RUN_ROOT / "POD-RESOURCE-CHECK.json")
    transport = load(RUN_ROOT / "TRANSPORT-FREEZE.json")
    validation = load(EVIDENCE / "REMOTE-VALIDATION.json")
    runtime = load(EVIDENCE / "RUNTIME.json")
    before = load(EVIDENCE / "SOURCE-BEFORE.json")
    after = load(EVIDENCE / "SOURCE-AFTER.json")
    manifest = load(MANIFEST)
    scout = load(SEMANTIC / "semantic-scout.json")
    draft = load(SEMANTIC / "confirmation-draft.json")
    oracle = load(SEMANTIC / "oracle-package.json")

    archive = RUN_ROOT / "evidence.zip"
    archive_sha256 = digest(archive.read_bytes())
    with zipfile.ZipFile(archive) as zipped:
        archive_names = zipped.namelist()
        if len(archive_names) != len(set(archive_names)):
            failures.append("duplicate evidence archive member")
        archive_mismatches = []
        for name in archive_names:
            path = RUN_ROOT / "evidence" / Path(name)
            data = zipped.read(name)
            if not path.is_file() or path.read_bytes() != data:
                archive_mismatches.append(name)
    extracted_names = [
        path.relative_to(RUN_ROOT / "evidence").as_posix()
        for path in (RUN_ROOT / "evidence").rglob("*") if path.is_file()
    ]
    if set(archive_names) != set(extracted_names) or archive_mismatches:
        failures.append("evidence archive/extraction mismatch")
    if archive_sha256 != EXPECTED_ARCHIVE_SHA256:
        failures.append("evidence archive hash mismatch")

    if (
        run.get("status") != "complete"
        or run.get("pod_id") != "s7hrrp4easoesc"
        or run.get("uploaded_source_files") != 82
        or run.get("upload_chunks") != 33
        or run.get("evidence", {}).get("verified") is not True
        or run.get("cleanup", {}).get("owned_pod_absent") is not True
        or run.get("cleanup", {}).get("inventories") != {"v1": [], "v2": []}
        or identity.get("pod_id") != run.get("pod_id")
    ):
        failures.append("controller outcome or cleanup mismatch")
    pod = resource.get("pod") or {}
    if (
        pod.get("id") != run.get("pod_id")
        or pod.get("vcpuCount") != 2
        or pod.get("memoryInGb") != 4
        or float(pod.get("costPerHr", -1)) != 0.06
        or pod.get("containerDiskInGb") != 12
        or pod.get("volumeInGb") != 0
        or resource.get("network_volume_present") is not False
        or pod.get("verified_v2_cloud") != "SECURE"
    ):
        failures.append("resource identity mismatch")
    if (
        runtime.get("runpod_pod_id") != run.get("pod_id")
        or len(runtime.get("affinity") or []) != 2
        or runtime.get("source_files") != 82
        or runtime.get("performance_measurement") is not False
        or runtime.get("performance_claim_permitted") is not False
    ):
        failures.append("runtime identity mismatch")

    manifest_rows = manifest.get("files") or []
    source_expected = [
        {"target": row["target"], "bytes": row["bytes"], "sha256": row["sha256"]}
        for row in manifest_rows
    ]
    if before != source_expected or after != source_expected or before != after:
        failures.append("uploaded source identity mismatch")
    if (
        validation.get("status") != "complete"
        or validation.get("validation_errors") != []
        or validation.get("source_unchanged") is not True
        or validation.get("performance_measurement") is not False
        or validation.get("performance_claim_permitted") is not False
    ):
        failures.append("remote validation mismatch")

    dependencies = {str(key).lower(): value for key, value in load(EVIDENCE / "BASE-DEPENDENCIES.json").items()}
    required_dependencies = {
        "numpy": "2.3.2", "sympy": "1.14.0", "mpmath": "1.3.0",
        "requests": "2.32.5", "charset-normalizer": "3.4.3", "idna": "3.10",
        "urllib3": "2.5.0", "certifi": "2025.8.3", "pytest": "9.0.2",
        "iniconfig": "2.1.0", "packaging": "26.3", "pluggy": "1.6.0",
        "pygments": "2.19.2",
    }
    if any(dependencies.get(name) != version for name, version in required_dependencies.items()):
        failures.append("locked dependency mismatch")
    if (
        load(EVIDENCE / "focused-tests.json").get("returncode") != 0
        or "6 passed" not in (EVIDENCE / "focused-tests.stdout.txt").read_text(encoding="utf-8")
    ):
        failures.append("focused parser/oracle tests did not pass")

    rows = scout.get("rows") or []
    eligible = [row for row in rows if row.get("status") == "eligible"]
    rejected = [row for row in rows if row.get("status") == "rejected"]
    primary = [row for row in rows if row.get("primary_selected") is True]
    if (
        scout.get("converted_inputs") != 64
        or scout.get("terminal_rows") != 64
        or len(rows) != 64
        or len({row.get("cluster_id") for row in rows}) != 64
        or scout.get("eligible") != len(eligible)
        or len(eligible) != 36
        or len(rejected) != 28
        or scout.get("unique_eligible") != 36
        or scout.get("semantic_duplicates") != 0
        or scout.get("primary_selected") != len(primary)
        or len(primary) != 30
    ):
        failures.append("semantic terminal counts mismatch")

    for row in eligible:
        if (
            row.get("translation_compatible") is not True
            or row.get("translation_truth_sha256") != row.get("truth_sha256")
            or row.get("root_selection_key") != root_key(row["cluster_id"], row["root"])
            or row.get("primary_selection_key") != primary_key(row)
            or row.get("semantic_key") != f"{row['k']}:{row['truth_sha256']}"
            or row.get("performance_measurement") is not False
            or row.get("performance_claim_permitted") is not False
        ):
            failures.append("eligible row identity/oracle contract mismatch")
            break
    if any(row.get("ai_provenance_present") is not False for row in primary):
        failures.append("AI-provenance case entered primary confirmation")

    cases = draft.get("cases") or []
    oracle_rows = oracle.get("rows") or []
    case_by_cluster = {case["cluster_id"]: case for case in cases}
    oracle_by_cluster = {row["cluster_id"]: row for row in oracle_rows}
    if (
        draft.get("case_count") != 30
        or len(cases) != len(case_by_cluster)
        or len(case_by_cluster) != 30
        or len(oracle_rows) != len(oracle_by_cluster)
        or len(oracle_by_cluster) != 30
        or set(case_by_cluster) != {row["cluster_id"] for row in primary}
        or set(oracle_by_cluster) != set(case_by_cluster)
    ):
        failures.append("primary draft/oracle coverage mismatch")

    source_mismatches = []
    for row in primary:
        case = case_by_cluster[row["cluster_id"]]
        oracle_row = oracle_by_cluster[row["cluster_id"]]
        oracle_core = {
            "schema": "cm-comparative-w8-blif-oracle/v1",
            "cluster_id": row["cluster_id"],
            "blif_sha256": row["blif_sha256"],
            "root": row["root"],
            "support": row["support"],
            "k": row["k"],
            "encoding": "packed truth bits; assignment index; little-endian bytes; frozen sorted support order",
            "truth_sha256": row["truth_sha256"],
        }
        expected_case_id = "confirmation-logikbench-" + row["name"] + "-" + digest(row["root"].encode())[:12]
        if (
            row["oracle_sha256"] != digest(canonical(oracle_core))
            or case["case_id"] != expected_case_id
            or oracle_row != case["oracle"]
            or case["source"]["sha256"] != row["blif_sha256"]
            or case["strata"]["root"] != row["root"]
            or case["strata"]["support"] != row["support"]
        ):
            failures.append("primary case/oracle identity mismatch")
            break
        source = CONVERSION / "converted" / (row["cluster_id"] + ".blif")
        if not source.is_file() or digest(source.read_bytes()) != row["blif_sha256"]:
            source_mismatches.append(row["cluster_id"])
    if source_mismatches:
        failures.append("primary converted source mismatch")

    schedule = draft.get("schedule_contract") or {}
    if (
        schedule.get("ir") != {
            "blocks": 8,
            "arms": ["cm-ir-current", "cm-ir-two-memo", "cm-cse-flat", "cm-raw-flat"],
        }
        or schedule.get("relation") != {
            "blocks": 10,
            "arms": ["cm-dense", "cm-packed-bigint", "cm-packed-words", "cm-no-reinflate", "cm-cse-flat"],
        }
        or schedule.get("locality") != "round_robin"
        or schedule.get("seed") != 0
    ):
        failures.append("frozen timing schedule contract mismatch")

    strata = {
        "families": dict(sorted(Counter(row["group"] for row in primary).items())),
        "support": dict(sorted(Counter(str(row["k"]) for row in primary).items(), key=lambda item: int(item[0]))),
        "source_node_bins": dict(sorted(Counter(
            "1-64" if row["source_nodes"] <= 64 else "65-512" if row["source_nodes"] <= 512 else "513-4096"
            for row in primary
        ).items())),
    }
    result = {
        "schema": "cm-comparative-w8-logikbench-semantic-final-audit/v1",
        "verified": not failures,
        "failures": failures,
        "pod_id": run.get("pod_id"),
        "resource_identity_matches": "resource identity mismatch" not in failures,
        "cleanup_verified": run.get("cleanup", {}).get("owned_pod_absent") is True,
        "estimated_compute_cost_usd": run.get("estimated_compute_cost_usd"),
        "elapsed_since_create_s": run.get("elapsed_since_create_s"),
        "evidence_archive_sha256": archive_sha256,
        "evidence_archive_members": len(archive_names),
        "evidence_archive_members_match_extraction": not archive_mismatches and set(archive_names) == set(extracted_names),
        "source_files": len(manifest_rows),
        "source_unchanged": before == after == source_expected,
        "focused_tests": 6,
        "locked_dependencies": len(required_dependencies),
        "semantic": {
            "converted_inputs": len(rows),
            "eligible": len(eligible),
            "rejected": len(rejected),
            "rejection_reasons": dict(sorted(Counter(row.get("error", "unknown") for row in rejected).items())),
            "unique_eligible": scout.get("unique_eligible"),
            "semantic_duplicates": scout.get("semantic_duplicates"),
            "primary_selected": len(primary),
            "translation_oracle_agreement": all(
                row.get("translation_truth_sha256") == row.get("truth_sha256") for row in primary
            ),
        },
        "primary_strata": strata,
        "semantic_scout_sha256": digest((SEMANTIC / "semantic-scout.json").read_bytes()),
        "oracle_package_sha256": digest((SEMANTIC / "oracle-package.json").read_bytes()),
        "confirmation_draft_sha256": digest((SEMANTIC / "confirmation-draft.json").read_bytes()),
        "performance_measurement": False,
        "performance_claim_permitted": False,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(not result["verified"])


if __name__ == "__main__":
    raise SystemExit(main())
