"""Build the reviewed, commit-pinned website download index.

Only explicitly allowlisted, already tracked evidence and verification files are
published.  The page links to immutable GitHub content; it does not copy or
bundle artifacts, and it fails closed if a reviewed file is missing or contains
an obvious credential marker.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "https://github.com/Relative0/Correspondence_Matrices"
REVIEWED_REVISION = "ff7511b401b0008ef3bff0f426f24c59a74c84f5"

TEXT_SUFFIXES = {
    ".csv", ".html", ".json", ".jsonl", ".md", ".py", ".sha256", ".txt", ".yml", ".yaml",
}
FORBIDDEN_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"ghp_",
    b"github_pat_",
    b"sk-proj-",
)


DOWNLOAD_SETS = (
    (
        "website-audit",
        "Website audit snapshot",
        "Claim-by-claim value, graph and downloadable-artifact review used for this update.",
        (
            ("deliverables_n22_24/master_explainer_2026_08_03/website_audit_2026-09-10/CM-WEBSITE-VALUE-AND-GRAPH-AUDIT-2026-09-10.md", "audit report", "site claims and plotted values", "repository-wide review"),
            ("deliverables_n22_24/master_explainer_2026_08_03/website_audit_2026-09-10/CM-WEBSITE-UPDATE-BACKLOG-2026-09-10.md", "update backlog", "P0/P1/P2 publication actions", "repository-wide review"),
            ("deliverables_n22_24/master_explainer_2026_08_03/website_audit_2026-09-10/CM-WEBSITE-POSITIVE-USE-CASE-AUDIT-2026-09-10.md", "positive-use-case audit", "favorable results and their boundaries", "repository-wide review"),
            ("deliverables_n22_24/master_explainer_2026_08_03/website_audit_2026-09-10/CM-WEBSITE-CLAIM-LEDGER-2026-09-10.json", "claim ledger", "rendered claim inventory and classifications", "all generated pages"),
            ("deliverables_n22_24/master_explainer_2026_08_03/website_audit_2026-09-10/CM-WEBSITE-DOWNLOADABLE-ARTIFACT-MANIFEST-2026-09-10.json", "artifact inventory", "candidate download inventory and dispositions", "tracked repository artifacts"),
            ("deliverables_n22_24/master_explainer_2026_08_03/website_audit_2026-09-10/generate_audit.py", "audit tool", "rebuild claim/link/artifact audit", "offline repository checkout"),
        ),
    ),
    (
        "symmetric-v3",
        "Flattened-CSE comparison · B2/B4 V3",
        "Current formula-balanced bare-kernel comparison plus its audit, summary and integrity test.",
        (
            ("deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_inference.csv", "inference table", "paired formula-cluster estimates and confidence intervals", "Windows; B2/B4 frozen formulas"),
            ("deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_audit.json", "independent audit", "protocol, acceptance and source identity", "exactly counterbalanced rows"),
            ("deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_summary.csv", "summary data", "formula-level timing summary", "bare and wrapper timing boundaries"),
            ("deliverables_n22_24/corrections_2026_08_25/symmetric/audited_v3_source_snapshot/scripts/cm_symmetric_wrapper_followup.py", "frozen runner", "reproduce the V3 experiment", "frozen source snapshot"),
            ("tests/test_cm_benchmark_audit_integrity.py", "integrity test", "audit and symmetric-workflow invariants", "repository test suite"),
        ),
    ),
    (
        "c6-packed-core",
        "C6 packed exact source-ANF core",
        "Positive exact-core result. The packed core advanced; the learned hybrid and production routing did not.",
        (
            ("docs/recognition/LEARNING_MILESTONE_C6_PACKED_SOURCE_ANF_2026_08_30.md", "report", "interpretation, gates and exact boundary", "held-out test and confirmatory splits"),
            ("docs/recognition/learning_milestone_c6_packed_source_anf_results.json", "results", "per-method accuracy and timing summaries", "188 natural-source cases"),
            ("docs/recognition/verification/natural-source-anf-hybrid-20260830-004.json", "verification", "independent replay and mismatch counts", "940 raw timing rows replayed"),
            ("scripts/crse_natural_source_anf_verify.py", "verifier", "independent exactness and summary replay", "saved C6 run"),
            ("scripts/crse_register_milestone_c6.py", "publication guard", "fail-closed milestone registration", "reviewed result identity"),
        ),
    ),
    (
        "c16-screening",
        "C16 exact-screened GF(2)",
        "Task-equivalent whole-path screening on local Windows and an independently verified Linux host.",
        (
            ("docs/recognition/LEARNING_MILESTONE_C16_EXACT_SCREENED_GF2_2026_08_30.md", "report", "local and second-machine interpretation", "40 source cases plus controls"),
            ("docs/recognition/learning_milestone_c16_exact_screened_gf2_results.json", "consolidated results", "local timing, exactness and promotion boundary", "Windows local validation"),
            ("docs/recognition/c16_linux_confirmation/RUNPOD_C16_PACKAGE_V2_FINAL_VERIFICATION_20260831.json", "Linux verification", "second-machine whole-path and p95 result", "Linux; 40 cases, 360 rows"),
            ("docs/recognition/c16_linux_confirmation/C16_SECOND_MACHINE_TIMING_PACKAGE_V2_PROTOCOL_2026_08_31.md", "protocol", "frozen second-machine timing contract", "dependency-complete package v2"),
            ("scripts/crse_gf2_screening_verify.py", "local verifier", "artifact, exactness and timing replay", "saved local run"),
            ("docs/recognition/c16_linux_confirmation/verify_runpod_c16_package_v2_attempt.py", "Linux verifier", "final package-v2 verification", "saved Linux output"),
        ),
    ),
    (
        "feature-model",
        "Feature-model evidence",
        "Correctness-checked bounded configuration evidence; performance remains provisional.",
        (
            ("deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/CONFIGURATION-REPRESENTATION-BATTERY-RESULTS.md", "results", "CM, direct CNF, ROBDD and d-DNNF comparison", "bounded official-model cohort"),
            ("deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/CONFIGURATION-FM-INDEPENDENCE-AUDIT-2026-08-27.md", "independence audit", "measurement and source-independence gaps", "feature-model evidence"),
            ("deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/runs/configuration-representation-battery-cudd-smoke-2026-08-27/independent-audit.json", "machine audit", "bounded replay results and gaps", "CUDD-enabled smoke cohort"),
            ("deliverables_n22_24/master_explainer_2026_08_03/use_case_benchmarks_2026-08-27/cm_feature_model_representation_battery.py", "runner", "build the representation battery", "offline repository checkout"),
            ("tests/test_cm_feature_model_website.py", "website test", "rendered values and conservative wording", "repository test suite"),
            ("tests/test_cm_feature_model_representation_battery.py", "battery test", "exact relation and output contracts", "repository test suite"),
        ),
    ),
    (
        "architecture",
        "Current architecture evidence",
        "Task-separated exact architecture comparisons and cross-machine query-ladder evidence.",
        (
            ("docs/recognition/architecture_comparison_execution_retry_20260903/ANALYSIS.json", "architecture analysis", "complete-relation and small-query task comparisons", "verified Linux/GCC execution"),
            ("docs/recognition/architecture_comparison_execution_retry_20260903/VERIFIED_INTERPRETATION.md", "interpretation", "task boundaries and retained conclusions", "verified Linux/GCC execution"),
            ("docs/recognition/architecture_query_ladder_cross_machine_execution_20260904/CROSS_MACHINE_ANALYSIS.json", "cross-machine analysis", "q1/q4/q16/q64 within-host ratios", "Linux GCC and Clang hosts"),
            ("docs/recognition/architecture_query_ladder_cross_machine_execution_20260904/VERIFIED_CROSS_MACHINE_INTERPRETATION.md", "cross-machine interpretation", "label, timing and portability boundary", "two physical machines"),
            ("scripts/cm_analyze_architecture_comparison.py", "analysis tool", "derive architecture task comparisons", "saved execution outputs"),
            ("scripts/cm_analyze_architecture_query_ladder_cross_machine.py", "analysis tool", "derive cross-machine query-ladder comparisons", "saved execution outputs"),
            ("tests/test_cm_architecture_comparison_analysis.py", "analysis test", "architecture-analysis invariants", "repository test suite"),
            ("tests/test_cm_architecture_query_ladder_cross_machine_package.py", "package test", "cross-machine package and verifier contracts", "repository test suite"),
        ),
    ),
)


def _reviewed_bytes(path: Path) -> bytes:
    payload = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        payload = payload.replace(b"\r\n", b"\n")
    if any(marker in payload for marker in FORBIDDEN_MARKERS):
        raise ValueError(f"Credential-like marker in reviewed download: {path.relative_to(ROOT)}")
    return payload


def build_downloads_evidence() -> dict:
    sets = []
    artifact_count = 0
    for set_id, title, description, records in DOWNLOAD_SETS:
        artifacts = []
        for relative, role, contract, scope in records:
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():
                raise ValueError(f"Missing reviewed download: {relative}")
            payload = _reviewed_bytes(path)
            encoded = quote(relative, safe="/")
            artifacts.append({
                "path": relative,
                "name": path.name,
                "role": role,
                "contract": contract,
                "scope": scope,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "view": f"{REPOSITORY}/blob/{REVIEWED_REVISION}/{encoded}",
                "raw": f"https://raw.githubusercontent.com/Relative0/Correspondence_Matrices/{REVIEWED_REVISION}/{encoded}",
                "license": "No repository license declared; review rights before reuse.",
                "privacy": "Explicit publication allowlist; credential-marker scan passed.",
            })
        artifact_count += len(artifacts)
        sets.append({"id": set_id, "title": title, "description": description, "artifacts": artifacts})

    inventory_path = ROOT / "deliverables_n22_24/master_explainer_2026_08_03/website_audit_2026-09-10/CM-WEBSITE-DOWNLOADABLE-ARTIFACT-MANIFEST-2026-09-10.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    candidate_artifact_count = len(inventory.get("artifacts", []))
    if candidate_artifact_count < artifact_count:
        raise ValueError("Full artifact inventory is smaller than the reviewed direct-download set")

    return {
        "schema": "cm-reviewed-download-index/v1",
        "reviewed": "2026-09-10",
        "revision": REVIEWED_REVISION,
        "repository": REPOSITORY,
        "latest_repository": REPOSITORY,
        "artifact_count": artifact_count,
        "candidate_artifact_count": candidate_artifact_count,
        "sets": sets,
        "license_status": "No LICENSE or COPYING file exists at the repository root as of the reviewed revision.",
        "privacy_status": "Every listed path is explicitly allowlisted and passed a credential-marker scan; no directory dump or operational bundle is published.",
    }
