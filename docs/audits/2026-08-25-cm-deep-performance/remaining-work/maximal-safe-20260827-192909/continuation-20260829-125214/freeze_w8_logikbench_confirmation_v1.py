"""Publish the verified W8 LogikBench confirmation cohort without timing it."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = next(
    parent
    for parent in (HERE, *HERE.parents)
    if (parent / "cmbench").is_dir() and (parent / "docs").is_dir()
)
RUN_ROOT = HERE / "w8-logikbench-semantic-v3-001"
SEMANTIC_ROOT = RUN_ROOT / "evidence" / "run-output" / "w8-semantic"
CONVERTED_ROOT = (
    HERE
    / "w8-logikbench-conversion-v4-001"
    / "evidence"
    / "run-output"
    / "w8-conversion"
    / "converted"
)
DESTINATION = (
    PROJECT_ROOT
    / "docs"
    / "research"
    / "verification"
    / "comparative-w8-logikbench-confirmation-v1-2026-08-31"
)
PROPOSAL = HERE / "RUNPOD-W8-LOGIKBENCH-SEMANTIC-SCOUT-PROPOSAL-20260830.md"
UPLOAD_MANIFEST = HERE / "RUNPOD-W8-LOGIKBENCH-SEMANTIC-UPLOAD-MANIFEST-V1-20260830.json"
UPLOAD_BUNDLE = HERE / "RUNPOD-W8-LOGIKBENCH-SEMANTIC-UPLOAD-BUNDLE-V1-20260830.zip"
REMOTE_WRAPPER = HERE / "runpod_w8_logikbench_semantic_remote_v1.py"
FINAL_AUDIT = HERE / "W8-LOGIKBENCH-SEMANTIC-FINAL-AUDIT.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relative_manifest(root: Path, *, omitted: set[str] | None = None) -> list[dict]:
    omitted = omitted or set()
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in omitted:
            continue
        rows.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return rows


def main() -> int:
    if DESTINATION.exists():
        raise RuntimeError(f"confirmation freeze already exists: {DESTINATION}")
    required = [
        SEMANTIC_ROOT / "confirmation-draft.json",
        SEMANTIC_ROOT / "oracle-package.json",
        SEMANTIC_ROOT / "semantic-scout.json",
        PROPOSAL,
        UPLOAD_MANIFEST,
        UPLOAD_BUNDLE,
        REMOTE_WRAPPER,
        FINAL_AUDIT,
        RUN_ROOT / "RUN.json",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing verified input(s): {missing}")

    final_audit = load(FINAL_AUDIT)
    if not final_audit.get("verified") or final_audit.get("failures"):
        raise RuntimeError("final semantic audit is not clean")
    if not final_audit.get("cleanup_verified"):
        raise RuntimeError("successful semantic pod cleanup is not verified")

    draft_path = SEMANTIC_ROOT / "confirmation-draft.json"
    oracle_path = SEMANTIC_ROOT / "oracle-package.json"
    scout_path = SEMANTIC_ROOT / "semantic-scout.json"
    draft = load(draft_path)
    oracle = load(oracle_path)
    scout = load(scout_path)
    cases = draft.get("cases") or []
    rows = scout.get("rows") or []
    primary = [row for row in rows if row.get("status") == "eligible" and row.get("primary_selected")]
    rejected = [row for row in rows if row.get("status") == "rejected"]
    eligible_unselected = [
        row for row in rows if row.get("status") == "eligible" and not row.get("primary_selected")
    ]
    case_clusters = [case.get("cluster_id") for case in cases]
    if (
        draft.get("case_count") != 30
        or len(cases) != 30
        or len(set(case_clusters)) != 30
        or len(primary) != 30
        or {row["cluster_id"] for row in primary} != set(case_clusters)
        or len(rejected) != 28
        or len(eligible_unselected) != 6
        or len(oracle.get("rows") or []) != 30
        or final_audit.get("semantic", {}).get("translation_oracle_agreement") is not True
    ):
        raise RuntimeError("verified selection counts or identities changed")

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=DESTINATION.name + ".tmp-", dir=DESTINATION.parent))
    sources = temporary / "sources"
    sources.mkdir()
    source_rows = []
    for case in sorted(cases, key=lambda item: item["cluster_id"]):
        cluster_id = case["cluster_id"]
        relative = Path(case["source"]["path"])
        if relative.parts != ("sources", cluster_id + ".blif"):
            raise RuntimeError(f"unsafe or unexpected frozen path for {cluster_id}")
        source = CONVERTED_ROOT / (cluster_id + ".blif")
        if not source.is_file():
            raise RuntimeError(f"missing converted source: {source}")
        expected_hash = case["source"]["sha256"]
        if sha256(source) != expected_hash or case["oracle"]["input_sha256"] != expected_hash:
            raise RuntimeError(f"source identity mismatch: {cluster_id}")
        destination = temporary / relative
        shutil.copyfile(source, destination)
        if sha256(destination) != expected_hash:
            raise RuntimeError(f"copied source identity mismatch: {cluster_id}")
        source_rows.append(
            {
                "case_id": case["case_id"],
                "cluster_id": cluster_id,
                "path": relative.as_posix(),
                "bytes": destination.stat().st_size,
                "sha256": expected_hash,
                "upstream_repository": case["source"]["upstream_repository"],
                "upstream_commit": case["source"]["upstream_commit"],
                "upstream_rtl_paths": case["source"]["upstream_rtl_paths"],
                "upstream_rtl_sha256": case["source"]["upstream_rtl_sha256"],
                "license_ids": case["source"]["license_ids"],
                "license_paths": case["source"]["license_paths"],
                "conversion_tool": case["source"]["conversion_tool"],
            }
        )

    shutil.copyfile(draft_path, temporary / "confirmation-selection.json")
    shutil.copyfile(oracle_path, temporary / "oracle-package.json")
    shutil.copyfile(scout_path, temporary / "semantic-scout.json")
    source_manifest = {
        "schema": "cm-comparative-w8-confirmation-source-manifest/v1",
        "file_count": len(source_rows),
        "bytes": sum(row["bytes"] for row in source_rows),
        "files": source_rows,
    }
    write_json(temporary / "source-manifest.json", source_manifest)
    exclusions = {
        "schema": "cm-comparative-w8-confirmation-selection-ledger/v1",
        "terminal_inputs": len(rows),
        "selected": len(primary),
        "eligible_unselected": len(eligible_unselected),
        "rejected": len(rejected),
        "performance_measurement": False,
        "performance_claim_permitted": False,
        "eligible_unselected_rows": sorted(eligible_unselected, key=lambda item: item["cluster_id"]),
        "rejected_rows": sorted(rejected, key=lambda item: item["cluster_id"]),
    }
    write_json(temporary / "selection-exclusions.json", exclusions)

    provenance = {
        "semantic_proposal_sha256": sha256(PROPOSAL),
        "semantic_upload_manifest_sha256": sha256(UPLOAD_MANIFEST),
        "semantic_upload_bundle_sha256": sha256(UPLOAD_BUNDLE),
        "semantic_remote_wrapper_sha256": sha256(REMOTE_WRAPPER),
        "semantic_run_sha256": sha256(RUN_ROOT / "RUN.json"),
        "semantic_final_audit_sha256": sha256(FINAL_AUDIT),
        "semantic_scout_sha256": sha256(scout_path),
        "oracle_package_sha256": sha256(oracle_path),
        "confirmation_selection_sha256": sha256(draft_path),
        "semantic_pod_id": final_audit["pod_id"],
        "semantic_cleanup_verified": True,
    }
    freeze_core = {
        "schema": "cm-comparative-w8-logikbench-confirmation-freeze/v1",
        "date": "2026-08-31",
        "status": "frozen",
        "role": "untouched_confirmation",
        "performance_measurement": False,
        "performance_claim_permitted_by_semantic_scout": False,
        "case_count": 30,
        "independent_cluster_count": 30,
        "selection_rule": draft["selection_rule"],
        "cases": cases,
        "schedule_contract": draft["schedule_contract"],
        "primary_metrics": draft["primary_metrics"],
        "source_manifest_sha256": sha256(temporary / "source-manifest.json"),
        "selection_exclusions_sha256": sha256(temporary / "selection-exclusions.json"),
        "provenance": provenance,
        "use_boundary": {
            "development_timing": "prohibited",
            "first_permitted_comparative_execution": "P9/W10 untouched confirmation after development analysis and candidate are frozen",
            "case_dropping_after_execution_starts": "prohibited",
            "typed_failures": "retained in the denominator",
        },
    }
    freeze = dict(freeze_core)
    freeze["freeze_sha256"] = hashlib.sha256(canonical_bytes(freeze_core)).hexdigest()
    write_json(temporary / "freeze.json", freeze)

    readme = f"""# W8 LogikBench untouched confirmation freeze v1

This directory freezes 30 independent LogikBench circuit/output cones selected
without comparative timing. The Linux semantic scout found 36 eligible unique
clusters among 64 converted inputs; the static predeclared selection chose 30.
Every selected translated CM expression exactly matched the independent packed
BLIF truth oracle.

The sources, roots, support order, oracle digests, selection/exclusion ledger,
schedule, and primary metrics are immutable under logical freeze
`{freeze['freeze_sha256']}`.

This cohort is reserved for untouched P9/W10 confirmation. It must not be used
to tune W4/W5 development arms, thresholds, schedules, exclusions, or analysis.
The semantic scout measured no performance. Any later typed refusal remains in
the denominator, and no case may be dropped after confirmation execution starts.

Files:

- `freeze.json`: authoritative cases, schedule, metrics, provenance, and use boundary.
- `sources/`: the 30 exact converted BLIF inputs.
- `oracle-package.json`: independent source-bound truth digests.
- `confirmation-selection.json`: the original Runpod-produced selection draft.
- `semantic-scout.json`: all 64 terminal semantic rows.
- `selection-exclusions.json`: 28 rejected and 6 eligible-unselected rows.
- `source-manifest.json`: source bytes, hashes, upstream paths, licenses, and conversion identity.
- `freeze-verification.json` and `checksums.json`: publication verification evidence.
"""
    (temporary / "README.md").write_text(readme, encoding="utf-8")

    copied_sources = sorted((temporary / "sources").glob("*.blif"))
    source_manifest_by_path = {row["path"]: row for row in source_rows}
    source_failures = []
    for path in copied_sources:
        relative = path.relative_to(temporary).as_posix()
        record = source_manifest_by_path.get(relative)
        if record is None or sha256(path) != record["sha256"] or path.stat().st_size != record["bytes"]:
            source_failures.append(relative)
    if len(copied_sources) != 30 or len(source_manifest_by_path) != 30 or source_failures:
        raise RuntimeError(f"frozen source verification failed: {source_failures}")
    verification = {
        "schema": "cm-comparative-w8-logikbench-confirmation-freeze-verification/v1",
        "verified": True,
        "failures": [],
        "freeze_sha256": freeze["freeze_sha256"],
        "case_count": len(cases),
        "independent_cluster_count": len(set(case_clusters)),
        "source_files": len(copied_sources),
        "source_bytes": sum(path.stat().st_size for path in copied_sources),
        "source_hashes_match": True,
        "oracle_rows": len(oracle["rows"]),
        "translation_oracle_agreement": True,
        "semantic_terminal_inputs": len(rows),
        "semantic_eligible": scout["eligible"],
        "semantic_unique_eligible": scout["unique_eligible"],
        "semantic_duplicates": scout["semantic_duplicates"],
        "selected": len(primary),
        "eligible_unselected": len(eligible_unselected),
        "rejected": len(rejected),
        "performance_measurement": False,
        "cleanup_verified": True,
    }
    write_json(temporary / "freeze-verification.json", verification)
    checksums = {
        "schema": "cm-comparative-artifact-checksums/v1",
        "scope": "all regular files in this freeze except checksums.json",
        "files": relative_manifest(temporary, omitted={"checksums.json"}),
    }
    write_json(temporary / "checksums.json", checksums)

    os.replace(temporary, DESTINATION)
    result = {
        "destination": str(DESTINATION),
        "freeze_sha256": freeze["freeze_sha256"],
        "case_count": len(cases),
        "source_files": len(copied_sources),
        "source_bytes": verification["source_bytes"],
        "artifact_files": len(checksums["files"]) + 1,
        "verified": True,
        "performance_measurement": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
