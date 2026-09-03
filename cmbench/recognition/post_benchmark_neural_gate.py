"""Fail-closed neural eligibility audit for architecture-comparison retry 002.

This module only reinterprets already recorded exact timing evidence.  It does
not fit a selector, train a model, inspect a new corpus, run timings, change a
route, or publish a result.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "crse-post-benchmark-neural-eligibility/v1"
ARTIFACT_SCHEMA = "crse-post-benchmark-neural-eligibility-artifacts/v1"
VERIFICATION_SCHEMA = (
    "crse-post-benchmark-neural-eligibility-independent-verification/v1"
)
DEVELOPMENT_HEADROOM_GATE = 1.10
PROSPECTIVE_CHARGED_GATE = 1.05
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_JSONL_BYTES = 32 * 1024 * 1024
EXPECTED_ROWS = 19_646
EXPECTED_LANE_ROWS = {"A": 10_880, "B": 6_912, "C": 384, "D": 1_470}
HEX = frozenset("0123456789abcdef")

RETRY_ROOT = (
    ROOT / "docs/recognition/architecture_comparison_execution_retry_20260903"
)
RUN_DIR = (
    RETRY_ROOT
    / "runpod-architecture-comparison-retry-002/evidence/run-output"
    / "architecture-comparison-linux-gcc-20260903-002"
)
FREEZE_PATH = (
    ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"
)
PRIOR_ROOT = (
    ROOT
    / "docs/recognition/runs"
    / "neural-architecture-reassessment-development-20260902-001"
)
ANALYSIS_SCRIPT_PATH = ROOT / "scripts/cm_analyze_architecture_comparison.py"

EVIDENCE_PATHS = {
    "analysis": RETRY_ROOT / "ANALYSIS.json",
    "authorization": RETRY_ROOT
    / "RUNPOD_ARCHITECTURE_COMPARISON_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_09_03.json",
    "controller_state": RETRY_ROOT
    / "runpod-architecture-comparison-retry-002/RUN.json",
    "execution_contract": RETRY_ROOT / "EXECUTION_CONTRACT.json",
    "freeze": FREEZE_PATH,
    "independent_verification": RUN_DIR / "independent_verification.json",
    "prior_assessment": PRIOR_ROOT / "assessment.json",
    "prior_manifest": PRIOR_ROOT / "manifest.json",
    "prior_verification": PRIOR_ROOT / "independent_verification.json",
    "raw_measurements": RUN_DIR / "raw_measurements.jsonl",
    "results": RUN_DIR / "results.json",
    "runtime_binding": RUN_DIR / "runtime_binding.json",
    "upload_manifest": RETRY_ROOT / "UPLOAD_MANIFEST.json",
    "analysis_script": ANALYSIS_SCRIPT_PATH,
}


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_hash(value: Any, label: str) -> str:
    _require(
        type(value) is str and len(value) == 64 and set(value) <= HEX,
        f"invalid SHA-256: {label}",
    )
    return value


def _validate_commit(value: Any, label: str) -> str:
    _require(
        type(value) is str and len(value) == 40 and set(value) <= HEX,
        f"invalid Git identity: {label}",
    )
    return value


def read_json(path: Path) -> Any:
    size = path.stat().st_size
    _require(0 < size <= MAX_JSON_BYTES, f"JSON evidence outside size bound: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    size = path.stat().st_size
    _require(0 < size <= MAX_JSONL_BYTES, "raw evidence outside size bound")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            _require(bool(line.strip()), f"blank raw row: {line_number}")
            value = json.loads(line)
            _require(type(value) is dict, f"non-object raw row: {line_number}")
            rows.append(value)
    return rows


def load_default_inputs() -> dict[str, Any]:
    documents = {
        name: read_json(path)
        for name, path in EVIDENCE_PATHS.items()
        if name not in {"raw_measurements", "analysis_script"}
    }
    return {
        "documents": documents,
        "rows": read_jsonl(EVIDENCE_PATHS["raw_measurements"]),
        "hashes": {
            name: file_sha256(path) for name, path in EVIDENCE_PATHS.items()
        },
        "paths": {
            name: str(path.relative_to(ROOT)).replace("\\", "/")
            for name, path in EVIDENCE_PATHS.items()
        },
    }


def validate_inputs(inputs: Mapping[str, Any]) -> None:
    _require(isinstance(inputs, Mapping), "input bundle")
    documents = inputs.get("documents")
    rows = inputs.get("rows")
    hashes = inputs.get("hashes")
    paths = inputs.get("paths")
    expected_documents = set(EVIDENCE_PATHS) - {"raw_measurements", "analysis_script"}
    _require(
        isinstance(documents, Mapping) and set(documents) == expected_documents,
        "evidence document set",
    )
    _require(
        isinstance(hashes, Mapping) and set(hashes) == set(EVIDENCE_PATHS)
        and all(
            _validate_hash(value, f"input:{name}") == value
            for name, value in hashes.items()
        ),
        "evidence hash set",
    )
    _require(
        isinstance(paths, Mapping) and set(paths) == set(EVIDENCE_PATHS)
        and all(type(value) is str and value for value in paths.values()),
        "evidence path set",
    )
    _require(type(rows) is list and len(rows) == EXPECTED_ROWS, "raw row count")

    analysis = documents["analysis"]
    authorization = documents["authorization"]
    controller = documents["controller_state"]
    freeze = documents["freeze"]
    results = documents["results"]
    verification = documents["independent_verification"]
    runtime = documents["runtime_binding"]
    prior = documents["prior_assessment"]
    prior_manifest = documents["prior_manifest"]
    prior_verification = documents["prior_verification"]

    _require(
        analysis.get("schema") == "cm-architecture-comparison-analysis/v1"
        and analysis.get("status") == "verified_interpretation_complete"
        and analysis.get("verification", {}).get("rows_checked") == EXPECTED_ROWS
        and analysis.get("verification", {}).get("lane_rows") == EXPECTED_LANE_ROWS
        and all(
            analysis.get("verification", {}).get(field) == 0
            for field in (
                "schedule_mismatches", "semantic_mismatches",
                "source_or_artifact_mismatches",
            )
        )
        and analysis.get("measurement_limits", {}).get(
            "selector_or_neural_claim_permitted"
        ) is False,
        "analysis decision boundary",
    )
    analysis_inputs = analysis.get("inputs", {})
    _require(
        analysis_inputs.get("results_sha256") == hashes["results"]
        and analysis_inputs.get("independent_verification_sha256")
        == hashes["independent_verification"]
        and analysis_inputs.get("raw_measurements_sha256")
        == hashes["raw_measurements"]
        and analysis_inputs.get("freeze_sha256") == hashes["freeze"]
        and analysis_inputs.get("controller_state_sha256")
        == hashes["controller_state"],
        "analysis evidence binding",
    )
    _require(
        results.get("schema") == "cm-architecture-comparison-campaign-result/v1"
        and results.get("status") == "complete"
        and results.get("expected_rows") == EXPECTED_ROWS
        and results.get("lane_rows") == EXPECTED_LANE_ROWS
        and results.get("raw_measurements_sha256") == hashes["raw_measurements"]
        and results.get("decision", {}).get("selector_fitted") is False
        and results.get("decision", {}).get("neural_training") is False
        and results.get("decision", {}).get("production_routing_changed") is False,
        "campaign result boundary",
    )
    _require(
        verification.get("schema")
        == "cm-architecture-comparison-independent-verification/v1"
        and verification.get("status") == "verified_complete"
        and verification.get("rows_checked") == EXPECTED_ROWS
        and verification.get("lane_rows") == EXPECTED_LANE_ROWS
        and verification.get("results_sha256") == hashes["results"]
        and verification.get("raw_measurements_sha256")
        == hashes["raw_measurements"]
        and verification.get("runtime_binding_sha256") == hashes["runtime_binding"]
        and verification.get("selector_or_neural_claim_permitted") is False
        and verification.get("unfavorable_and_refused_cells_retained") is True
        and all(
            verification.get(field) == 0
            for field in (
                "schedule_mismatches", "semantic_mismatches",
                "source_or_artifact_mismatches",
            )
        ),
        "independent verification boundary",
    )
    _require(
        freeze.get("schema") == "cm-architecture-comparison-freeze/v1"
        and freeze.get("status") == "frozen_not_authorized"
        and freeze.get("permissions", {}).get("selector_fitting") is False
        and freeze.get("permissions", {}).get("neural_training") is False,
        "freeze boundary",
    )
    _require(
        results.get("freeze_sha256") == hashes["freeze"]
        and verification.get("freeze_sha256") == hashes["freeze"],
        "freeze hash binding",
    )
    _require(
        runtime.get("role") == "decision_bearing_linux_campaign"
        and runtime.get("native_library_sha256")
        == results.get("native_library_sha256"),
        "runtime binding",
    )
    _require(
        authorization.get("schema")
        == "cm-runpod-architecture-comparison-retry-002-exact-payload-authorization/v1"
        and authorization.get("authorized") is True
        and authorization.get("training") is False
        and authorization.get("selector_fit") is False
        and authorization.get("production_write") is False
        and authorization.get("website_update") is False
        and authorization.get("upload_manifest_sha256")
        == hashes["upload_manifest"]
        and authorization.get("execution_contract_sha256")
        == hashes["execution_contract"],
        "authorization boundary",
    )
    _require(
        controller.get("cleanup", {}).get("owned_pod_absent") is True
        and controller.get("cleanup", {}).get("inventories") == {"v1": [], "v2": []},
        "cloud cleanup boundary",
    )
    _require(
        prior.get("schema") == "crse-neural-architecture-reassessment/v1"
        and prior.get("decision", {}).get("training_allowed") is False
        and prior.get("decision", {}).get("training_performed") is False
        and prior.get("decision", {}).get("prospective_data_consumed") is False
        and prior_manifest.get("schema") == "crse-neural-reassessment-artifacts/v1"
        and prior_manifest.get("artifacts", {}).get("assessment.json")
        == hashes["prior_assessment"]
        and prior_verification.get("schema")
        == "crse-neural-reassessment-independent-verification/v1"
        and prior_verification.get("status") == "verified"
        and prior_verification.get("assessment_sha256")
        == hashes["prior_assessment"]
        and prior_verification.get("manifest_sha256") == hashes["prior_manifest"],
        "prior neural assessment boundary",
    )

    counts = Counter()
    lane_counts = Counter()
    for index, row in enumerate(rows):
        _require(
            row.get("schema") == "cm-architecture-comparison-timed-cell/v1",
            f"raw row schema: {index}",
        )
        status = row.get("status")
        lane = row.get("lane")
        _require(status in {"ok", "refused"} and lane in EXPECTED_LANE_ROWS,
                 f"raw row classification: {index}")
        counts[status] += 1
        lane_counts[lane] += 1
        if status == "ok":
            total = row.get("timings_ns", {}).get("accounted_total_ns")
            _require(type(total) is int and total > 0, f"raw timing: {index}")
            _require(row.get("exact_check_passed") is True, f"raw exactness: {index}")
    _require(dict(lane_counts) == EXPECTED_LANE_ROWS, "raw lane counts")
    normalized_counts = {
        name: counts.get(name, 0) for name in ("failed", "ok", "refused")
    }
    _require(
        normalized_counts == results.get("counts") == verification.get("counts"),
        "raw status counts",
    )


def _median_twice(values: Iterable[int]) -> int:
    ordered = sorted(values)
    _require(bool(ordered), "median values")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return 2 * ordered[middle]
    return ordered[middle - 1] + ordered[middle]


def _surface(
    rows: Sequence[Mapping[str, Any]],
    *,
    surface_id: str,
    lane: str,
    arms: Sequence[str],
    sublane: str | None = None,
    lifecycle: str | None = None,
    allowed_case_ids: set[str] | None = None,
    recognition_ns_per_case: int,
) -> dict[str, Any]:
    arm_set = set(arms)
    _require(len(arm_set) == len(arms) and bool(arm_set), "surface arms")
    selected: list[Mapping[str, Any]] = []
    scheduled_cases: set[str] = set()
    refused_rows = 0
    for row in rows:
        if row.get("lane") != lane:
            continue
        if sublane is not None and row.get("sublane") != sublane:
            continue
        arm = row.get("arm")
        if lifecycle is not None and (
            type(arm) is not str or not arm.endswith(f"/{lifecycle}")
        ):
            continue
        if arm not in arm_set:
            continue
        case_id = row.get("case_id")
        if type(case_id) is not str or (
            allowed_case_ids is not None and case_id not in allowed_case_ids
        ):
            continue
        scheduled_cases.add(case_id)
        if row.get("status") == "refused":
            refused_rows += 1
        elif row.get("status") == "ok":
            selected.append(row)

    by_case_arm: dict[tuple[str, str], dict[int, int]] = defaultdict(dict)
    for row in selected:
        key = (str(row["case_id"]), str(row["arm"]))
        block = int(row["block"])
        _require(block not in by_case_arm[key], "duplicate surface cell")
        by_case_arm[key][block] = int(row["timings_ns"]["accounted_total_ns"])

    complete_cases: list[str] = []
    excluded_cases: list[str] = []
    for case_id in sorted(scheduled_cases):
        block_sets = [set(by_case_arm.get((case_id, arm), {})) for arm in arms]
        if all(block_sets) and all(value == block_sets[0] for value in block_sets):
            complete_cases.append(case_id)
        else:
            excluded_cases.append(case_id)
    _require(bool(complete_cases), f"no complete cases: {surface_id}")

    medians_twice = {
        (case_id, arm): _median_twice(by_case_arm[(case_id, arm)].values())
        for case_id in complete_cases
        for arm in arms
    }
    totals_twice = {
        arm: sum(medians_twice[(case_id, arm)] for case_id in complete_cases)
        for arm in arms
    }
    best_fixed = min(arms, key=lambda arm: (totals_twice[arm], arm))
    labels = {
        case_id: min(
            arms, key=lambda arm: (medians_twice[(case_id, arm)], arm)
        )
        for case_id in complete_cases
    }
    oracle_twice = sum(
        medians_twice[(case_id, labels[case_id])] for case_id in complete_cases
    )
    best_twice = totals_twice[best_fixed]
    _require(0 < oracle_twice <= best_twice, "surface oracle economics")
    headroom = best_twice / oracle_twice
    cases = len(complete_cases)
    recognition_total = recognition_ns_per_case * cases
    charged = best_twice / (oracle_twice + 2 * recognition_total)
    allowable_total = max(0.0, best_twice / (2 * DEVELOPMENT_HEADROOM_GATE)
                          - oracle_twice / 2)
    return {
        "surface_id": surface_id,
        "lane": lane,
        "sublane": sublane,
        "lifecycle": lifecycle,
        "arms": list(arms),
        "scheduled_cases": len(scheduled_cases),
        "complete_cases": cases,
        "excluded_case_ids": excluded_cases,
        "refused_rows_retained": refused_rows,
        "blocks_per_complete_case_arm": len(
            by_case_arm[(complete_cases[0], arms[0])]
        ),
        "best_fixed_method": best_fixed,
        "best_fixed_median_sum_ns": best_twice / 2,
        "oracle_median_sum_ns": oracle_twice / 2,
        "gross_headroom_ns": (best_twice - oracle_twice) / 2,
        "gross_headroom_speedup": headroom,
        "gross_headroom_gate_passed": headroom >= DEVELOPMENT_HEADROOM_GATE,
        "diagnostic_label_counts": dict(sorted(Counter(labels.values()).items())),
        "diagnostic_case_labels": dict(sorted(labels.items())),
        "labels_heterogeneous": len(set(labels.values())) > 1,
        "historical_recognition_ns_per_case": recognition_ns_per_case,
        "historical_recognition_ns_total": recognition_total,
        "optimistic_feature_only_charged_speedup": charged,
        "prospective_charged_gate_passed": charged >= PROSPECTIVE_CHARGED_GATE,
        "maximum_total_overhead_ns_preserving_1_10x": allowable_total,
        "maximum_overhead_ns_per_case_preserving_1_10x": allowable_total / cases,
        "model_inference_ns_assumed": 0,
        "exact_verification_ns_assumed": 0,
        "fallback_ns_assumed": 0,
    }


def _build_surfaces(
    rows: Sequence[Mapping[str, Any]], freeze: Mapping[str, Any],
    recognition_ns_per_case: int,
) -> dict[str, dict[str, Any]]:
    schedules = freeze["schedules"]
    observed = freeze["observed_regression_bindings"]
    result: dict[str, dict[str, Any]] = {}
    for lane, observed_key in (
        ("A", "public_complete_relation_regression"),
        ("B", "repeated_restriction_regression"),
        ("C", "related_root_regression"),
    ):
        arms = list(schedules[lane]["arms"])
        observed_cases = set(observed[observed_key]["case_ids"])
        scheduled_cases = {
            str(row["case_id"]) for row in rows if row.get("lane") == lane
        }
        for cohort, case_ids in (
            ("all", None),
            ("observed", observed_cases),
            ("fresh", scheduled_cases - observed_cases),
        ):
            surface_id = f"lane_{lane.lower()}_{cohort}"
            result[surface_id] = _surface(
                rows,
                surface_id=surface_id,
                lane=lane,
                arms=arms,
                allowed_case_ids=case_ids,
                recognition_ns_per_case=recognition_ns_per_case,
            )

    d_schedule = schedules["D"]
    for sublane in sorted(d_schedule["task_sublanes"]):
        base_arms = list(d_schedule["task_sublanes"][sublane]["arms"])
        for lifecycle in d_schedule["task_lifecycles"]:
            arms = [f"{arm}/{lifecycle}" for arm in base_arms]
            surface_id = f"lane_d_{sublane}_{lifecycle}"
            result[surface_id] = _surface(
                rows,
                surface_id=surface_id,
                lane="D",
                sublane=sublane,
                lifecycle=lifecycle,
                arms=arms,
                recognition_ns_per_case=recognition_ns_per_case,
            )
    reload_arms = list(d_schedule["structural_reload"]["arms"])
    surface_id = "lane_d_structural_reload"
    result[surface_id] = _surface(
        rows,
        surface_id=surface_id,
        lane="D",
        sublane="structural_reload",
        arms=reload_arms,
        recognition_ns_per_case=recognition_ns_per_case,
    )
    return dict(sorted(result.items()))


def build_assessment(
    inputs: Mapping[str, Any],
    *,
    evidence_checkpoint: str,
    evidence_tree: str,
    source_bindings: Mapping[str, str],
) -> dict[str, Any]:
    validate_inputs(inputs)
    _validate_commit(evidence_checkpoint, "evidence checkpoint")
    _validate_commit(evidence_tree, "evidence tree")
    _require(
        isinstance(source_bindings, Mapping) and bool(source_bindings)
        and all(
            type(name) is str and name
            and _validate_hash(value, f"source:{name}") == value
            for name, value in source_bindings.items()
        ),
        "assessment source bindings",
    )
    documents = inputs["documents"]
    prior = documents["prior_assessment"]
    recognition_ns = prior["economics"]["charged_boundary"][
        "historical_feature_or_recognition_ns_per_case"
    ]
    _require(type(recognition_ns) is int and recognition_ns > 0,
             "historical recognition allowance")
    surfaces = _build_surfaces(inputs["rows"], documents["freeze"], recognition_ns)
    gross_candidates = sorted(
        name for name, value in surfaces.items()
        if value["gross_headroom_gate_passed"]
    )
    charged_candidates = sorted(
        name for name, value in surfaces.items()
        if value["prospective_charged_gate_passed"]
    )
    strongest_name = max(
        surfaces, key=lambda name: surfaces[name]["gross_headroom_speedup"]
    )
    strongest = surfaces[strongest_name]
    result = {
        "schema": SCHEMA,
        "status": "complete_no_training",
        "classification": "post_benchmark_development_only_fail_closed",
        "evidence_checkpoint": evidence_checkpoint,
        "evidence_tree": evidence_tree,
        "evidence_bindings": dict(sorted(inputs["hashes"].items())),
        "evidence_paths": dict(sorted(inputs["paths"].items())),
        "source_bindings": dict(sorted(source_bindings.items())),
        "methodology": {
            "surface_count": len(surfaces),
            "case_statistic": "median accounted_total_ns over counterbalanced blocks",
            "fixed_method_selection": "minimum sum of per-case medians with lexical tie break",
            "oracle_selection": "minimum per-case median among task-identical exact arms",
            "refused_rows_retained": True,
            "cross_surface_timing_synthesis": False,
            "development_headroom_gate": DEVELOPMENT_HEADROOM_GATE,
            "prospective_charged_gate": PROSPECTIVE_CHARGED_GATE,
            "historical_recognition_ns_per_case": recognition_ns,
        },
        "surfaces": surfaces,
        "gross_gate_candidates": gross_candidates,
        "charged_gate_candidates": charged_candidates,
        "strongest_surface": {
            "surface_id": strongest_name,
            "complete_cases": strongest["complete_cases"],
            "best_fixed_method": strongest["best_fixed_method"],
            "gross_headroom_speedup": strongest["gross_headroom_speedup"],
            "gross_headroom_ns": strongest["gross_headroom_ns"],
            "optimistic_feature_only_charged_speedup": strongest[
                "optimistic_feature_only_charged_speedup"
            ],
            "maximum_overhead_ns_per_case_preserving_1_10x": strongest[
                "maximum_overhead_ns_per_case_preserving_1_10x"
            ],
            "diagnostic_label_counts": strongest["diagnostic_label_counts"],
        },
        "neural_task_disposition": {
            "B_decomposition_or_cut_candidates": (
                "unchanged stop: retry 002 supplies no global-best early-termination certificate"
            ),
            "C_partition_ranking": (
                "unchanged stop: no material exact completion work is avoided"
            ),
            "D_exact_backend_selection": (
                "new gross signal only in resident version-history; charged economics and "
                "evidence sufficiency still fail"
            ),
            "E_runtime_or_cost_prediction": (
                "protocol design may study sub-3.6us analytical recognition, but no fitting is allowed"
            ),
        },
        "permissions": {
            "post_benchmark_economics_reassessment": True,
            "protocol_template_maintenance": True,
            "fresh_corpus_selection_or_inspection": False,
            "prospective_data_consumption": False,
            "new_timing_campaign": False,
            "cloud_execution": False,
            "selector_fitting": False,
            "neural_training": False,
            "production_routing_change": False,
            "website_or_publication_change": False,
        },
        "decision": {
            "new_gross_headroom_signal_detected": bool(gross_candidates),
            "charged_candidate_detected": bool(charged_candidates),
            "training_label_table_ready": False,
            "training_allowed": False,
            "training_performed": False,
            "selector_fitted": False,
            "advice_enabled": False,
            "complete_abstention": True,
            "exact_fallback": "unchanged exact path",
            "prospective_data_consumed_by_reassessment": False,
            "production_write": False,
            "production_promotion": False,
            "reason": (
                "the sole gross-gate surface has three complete cases and falls below 1.0x "
                "after the historical recognition allowance, before inference, verification, "
                "or fallback"
            ),
        },
    }
    validate_assessment(result)
    return result


def validate_assessment(assessment: Mapping[str, Any]) -> None:
    _require(isinstance(assessment, Mapping), "assessment")
    expected_fields = {
        "schema", "status", "classification", "evidence_checkpoint",
        "evidence_tree", "evidence_bindings", "evidence_paths", "source_bindings",
        "methodology", "surfaces", "gross_gate_candidates", "charged_gate_candidates",
        "strongest_surface", "neural_task_disposition", "permissions", "decision",
    }
    _require(set(assessment) == expected_fields, "assessment fields")
    _require(
        assessment["schema"] == SCHEMA
        and assessment["status"] == "complete_no_training"
        and assessment["classification"]
        == "post_benchmark_development_only_fail_closed",
        "assessment identity",
    )
    _validate_commit(assessment["evidence_checkpoint"], "evidence checkpoint")
    _validate_commit(assessment["evidence_tree"], "evidence tree")
    _require(
        set(assessment["evidence_bindings"]) == set(EVIDENCE_PATHS)
        and all(
            _validate_hash(value, f"evidence:{name}") == value
            for name, value in assessment["evidence_bindings"].items()
        )
        and set(assessment["evidence_paths"]) == set(EVIDENCE_PATHS),
        "assessment evidence bindings",
    )
    _require(
        isinstance(assessment["source_bindings"], Mapping)
        and bool(assessment["source_bindings"])
        and all(
            _validate_hash(value, f"source:{name}") == value
            for name, value in assessment["source_bindings"].items()
        ),
        "assessment source binding",
    )
    methodology = assessment["methodology"]
    surfaces = assessment["surfaces"]
    _require(
        methodology.get("surface_count") == len(surfaces) == 22
        and methodology.get("development_headroom_gate")
        == DEVELOPMENT_HEADROOM_GATE
        and methodology.get("prospective_charged_gate") == PROSPECTIVE_CHARGED_GATE
        and methodology.get("cross_surface_timing_synthesis") is False
        and methodology.get("refused_rows_retained") is True,
        "assessment methodology",
    )
    for name, surface in surfaces.items():
        _require(surface.get("surface_id") == name, "surface identity")
        totals = surface.get("best_fixed_median_sum_ns")
        oracle = surface.get("oracle_median_sum_ns")
        cases = surface.get("complete_cases")
        recognition = surface.get("historical_recognition_ns_total")
        _require(
            type(totals) in (int, float) and type(oracle) in (int, float)
            and type(cases) is int and cases > 0
            and type(recognition) is int and recognition > 0
            and 0 < oracle <= totals
            and math.isclose(
                surface.get("gross_headroom_speedup"), totals / oracle,
                rel_tol=1e-15,
            )
            and surface.get("gross_headroom_gate_passed")
            is (totals / oracle >= DEVELOPMENT_HEADROOM_GATE)
            and math.isclose(
                surface.get("optimistic_feature_only_charged_speedup"),
                totals / (oracle + recognition), rel_tol=1e-15,
            )
            and surface.get("prospective_charged_gate_passed")
            is (totals / (oracle + recognition) >= PROSPECTIVE_CHARGED_GATE)
            and sum(surface.get("diagnostic_label_counts", {}).values()) == cases
            and len(surface.get("diagnostic_case_labels", {})) == cases
            and surface.get("model_inference_ns_assumed") == 0
            and surface.get("exact_verification_ns_assumed") == 0
            and surface.get("fallback_ns_assumed") == 0,
            f"surface economics: {name}",
        )
    gross = sorted(
        name for name, surface in surfaces.items()
        if surface["gross_headroom_gate_passed"]
    )
    charged = sorted(
        name for name, surface in surfaces.items()
        if surface["prospective_charged_gate_passed"]
    )
    _require(
        assessment["gross_gate_candidates"] == gross
        and assessment["charged_gate_candidates"] == charged,
        "candidate surface lists",
    )
    strongest_name = max(
        surfaces, key=lambda name: surfaces[name]["gross_headroom_speedup"]
    )
    strongest = assessment["strongest_surface"]
    _require(
        strongest.get("surface_id") == strongest_name
        and strongest.get("gross_headroom_speedup")
        == surfaces[strongest_name]["gross_headroom_speedup"],
        "strongest surface",
    )
    permissions = assessment["permissions"]
    _require(
        set(permissions)
        == {
            "post_benchmark_economics_reassessment", "protocol_template_maintenance",
            "fresh_corpus_selection_or_inspection", "prospective_data_consumption",
            "new_timing_campaign", "cloud_execution", "selector_fitting",
            "neural_training", "production_routing_change",
            "website_or_publication_change",
        }
        and permissions["post_benchmark_economics_reassessment"] is True
        and permissions["protocol_template_maintenance"] is True
        and all(
            value is False for name, value in permissions.items()
            if name not in {
                "post_benchmark_economics_reassessment",
                "protocol_template_maintenance",
            }
        ),
        "assessment permissions",
    )
    decision = assessment["decision"]
    _require(
        decision.get("new_gross_headroom_signal_detected") is bool(gross)
        and decision.get("charged_candidate_detected") is bool(charged)
        and decision.get("training_label_table_ready") is False
        and decision.get("training_allowed") is False
        and decision.get("training_performed") is False
        and decision.get("selector_fitted") is False
        and decision.get("advice_enabled") is False
        and decision.get("complete_abstention") is True
        and decision.get("exact_fallback") == "unchanged exact path"
        and decision.get("prospective_data_consumed_by_reassessment") is False
        and decision.get("production_write") is False
        and decision.get("production_promotion") is False,
        "assessment decision boundary",
    )


def render_report(assessment: Mapping[str, Any]) -> str:
    strongest = assessment["strongest_surface"]
    surface = assessment["surfaces"][strongest["surface_id"]]
    return "\n".join([
        "# Post-benchmark neural eligibility reassessment",
        "",
        "Date: 2026-09-03  ",
        "Status: **complete; neural training remains prohibited**",
        "",
        "Retry 002 is valid exact, source-bound, one-host development evidence. This",
        "reassessment recomputes fixed-versus-per-case-oracle economics from per-case",
        "median accounted-total timings. It does not fit a selector or consume new data.",
        "",
        "## Decision",
        "",
        f"Across {assessment['methodology']['surface_count']} task/cohort surfaces, only",
        f"`{strongest['surface_id']}` reaches the 1.10x gross point gate. Its best fixed",
        f"method is `{strongest['best_fixed_method']}` and its gross headroom is",
        f"`{strongest['gross_headroom_speedup']:.9f}x` across only",
        f"{strongest['complete_cases']} complete cases, with diagnostic labels",
        f"`{json.dumps(strongest['diagnostic_label_counts'], sort_keys=True)}`.",
        "",
        f"The gross saving is only {strongest['gross_headroom_ns']:.1f} ns in total.",
        "Charging the historical recognition allowance of",
        f"{surface['historical_recognition_ns_per_case']:,} ns per case reduces the",
        f"optimistic speedup to `{strongest['optimistic_feature_only_charged_speedup']:.9f}x`,",
        "while model inference, exact verification, and fallback are still assumed free.",
        f"Only {strongest['maximum_overhead_ns_per_case_preserving_1_10x']:.1f} ns per case",
        "of total overhead could preserve the 1.10x gate.",
        "",
        "Therefore the run contains a new gross signal worth recording, but not a",
        "trainable or prospectively confirmable neural decision. Advice remains disabled,",
        "all cases abstain, and the exact fallback is unchanged.",
        "",
        "## Task boundary",
        "",
        "- C5 decomposition and partition work remains stopped: retry 002 supplies no",
        "  sound early-termination or certificate mechanism that avoids global-best work.",
        "- Lane B q64, complete-relation, and related-root surfaces remain below 1.10x.",
        "- A future version-history investigation must start with a source-blind expanded",
        "  development design and analytical controls capable of sub-3.6 microsecond",
        "  recognition. It is not authorized by this artifact.",
        "",
        "No fresh corpus selection or inspection, prospective data, timing, cloud resource,",
        "selector fit, neural training, route change, production write, or publication",
        "occurred in this reassessment.",
        "",
    ])
