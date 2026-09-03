"""Development-only, fail-closed version-history learning protocol.

The protocol consumes an independently verified benchmark *artifact*.  It has
no benchmark execution entry point and never fits a selector.  Current exposed
data are used only to exercise provenance, source-blind feature extraction,
split isolation, analytical controls, and charged-economics gates.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Any, Callable, Mapping, Sequence

from cmbench.comparative.architecture_comparison_campaign import resolve_catalog
from cmbench.recognition import post_benchmark_neural_gate as benchmark_gate


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "crse-version-history-learning-protocol/v1"
ARTIFACT_SCHEMA = "crse-version-history-learning-protocol-artifacts/v1"
VERIFICATION_SCHEMA = (
    "crse-version-history-learning-protocol-independent-verification/v1"
)
DEFAULT_BENCHMARK_ARTIFACT = (
    ROOT
    / "docs/recognition/runs"
    / "post-benchmark-neural-eligibility-development-20260903-001"
)
DEFAULT_QUERY_LADDER_ANALYSIS = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904"
    / "ANALYSIS.json"
)
QUERY_LADDER_FREEZE = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_retry_002_freeze_20260904"
    / "FREEZE.json"
)
QUERY_LADDER_ATTEMPT_001_STATUS = (
    ROOT
    / "docs/recognition/architecture_query_ladder_followup_execution_20260903"
    / "ATTEMPT_001_STATUS.json"
)
SURFACE_ID = "lane_d_version_history_resident_engine"
DEVELOPMENT_HEADROOM_GATE = 1.10
MIN_GLOBAL_WORK_AVOIDED_FRACTION = 0.25
MAX_JSON_BYTES = 4 * 1024 * 1024
HEX = frozenset("0123456789abcdef")

# These splits remain development-only.  No bucket is prospective, and current
# exposed cases cannot become prospective merely because their names are hidden.
SPLIT_SALT = "crse-version-history-source-blind-development-split-v1"
SPLIT_BUCKETS = (
    ("development_fit", 0, 60),
    ("development_validation", 60, 80),
    ("development_audit", 80, 100),
)
MIN_SPLIT_SOURCE_GROUPS = {
    "development_fit": 16,
    "development_validation": 8,
    "development_audit": 8,
}
MIN_SOURCE_GROUPS_PER_LABEL = 8

FEATURE_NAMES = (
    "variable_count",
    "version_count",
    "total_clause_count",
    "minimum_version_clause_count",
    "maximum_version_clause_count",
    "clause_count_churn_l1",
    "query_count",
    "assumption_literal_count",
    "distinct_versions_queried",
    "version_query_revisit_count",
)
FORBIDDEN_MODEL_FIELDS = (
    "case_id",
    "case_token",
    "source_group_sha256",
    "source_path",
    "source_family",
    "cluster_id",
    "split",
    "backend_label",
    "method_timing",
    "oracle_timing",
    "arm_order",
    "block",
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


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


def _read_json(path: Path) -> Any:
    _require(path.is_file(), f"missing JSON evidence: {path}")
    size = path.stat().st_size
    _require(0 < size <= MAX_JSON_BYTES, f"JSON evidence outside size bound: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _project_path(value: Any, label: str) -> Path:
    _require(type(value) is str and value, f"invalid project path: {label}")
    path = (ROOT / value).resolve()
    _require(path.is_relative_to(ROOT) and path.is_file(), f"unsafe project path: {label}")
    return path


def load_verified_benchmark_artifact(
    artifact: str | Path = DEFAULT_BENCHMARK_ARTIFACT,
) -> dict[str, Any]:
    """Load and authenticate a completed benchmark result without replaying it."""
    artifact_path = Path(artifact).resolve()
    _require(
        artifact_path.is_relative_to(ROOT) and artifact_path.is_dir(),
        "benchmark artifact must be an existing in-project directory",
    )
    manifest_path = artifact_path / "manifest.json"
    assessment_path = artifact_path / "assessment.json"
    verification_path = artifact_path / "independent_verification.json"
    manifest = _read_json(manifest_path)
    assessment = _read_json(assessment_path)
    verification = _read_json(verification_path)

    _require(
        manifest.get("schema") == benchmark_gate.ARTIFACT_SCHEMA
        and set(manifest)
        == {
            "schema", "evidence_checkpoint", "evidence_tree", "evidence",
            "sources", "artifacts",
        }
        and set(manifest.get("artifacts", {})) == {"assessment.json", "report.md"},
        "benchmark manifest shape",
    )
    _require(
        file_sha256(assessment_path) == manifest["artifacts"]["assessment.json"]
        and file_sha256(artifact_path / "report.md")
        == manifest["artifacts"]["report.md"],
        "benchmark artifact hash mismatch",
    )
    benchmark_gate.validate_assessment(assessment)
    _require(
        verification.get("schema") == benchmark_gate.VERIFICATION_SCHEMA
        and verification.get("status") == "verified_no_training"
        and verification.get("replay_byte_identical") is True
        and verification.get("assessment_sha256") == file_sha256(assessment_path)
        and verification.get("manifest_sha256") == file_sha256(manifest_path)
        and verification.get("surface_count") == len(assessment["surfaces"])
        and verification.get("gross_gate_candidates")
        == assessment["gross_gate_candidates"]
        and verification.get("charged_gate_candidates")
        == assessment["charged_gate_candidates"]
        and verification.get("training_performed") is False
        and verification.get("selector_fitted") is False
        and verification.get("prospective_data_consumed") is False
        and verification.get("production_write") is False
        and verification.get("production_promotion") is False,
        "benchmark independent verification boundary",
    )
    _require(
        manifest["evidence"] == assessment["evidence_bindings"]
        and manifest["sources"] == assessment["source_bindings"],
        "benchmark manifest-to-assessment binding",
    )

    # Hash current bytes only.  The benchmark is not re-executed or reanalyzed.
    for name, expected in assessment["evidence_bindings"].items():
        path = _project_path(assessment["evidence_paths"].get(name), f"evidence:{name}")
        _require(file_sha256(path) == expected, f"drifted benchmark evidence: {name}")
    for name, expected in assessment["source_bindings"].items():
        path = _project_path(name, f"source:{name}")
        _require(file_sha256(path) == expected, f"drifted benchmark source: {name}")

    surface = assessment["surfaces"].get(SURFACE_ID)
    _require(isinstance(surface, Mapping), "verified version-history surface missing")
    _require(
        surface.get("gross_headroom_gate_passed") is True
        and surface.get("complete_cases") == 3
        and surface.get("labels_heterogeneous") is True
        and sum(surface.get("diagnostic_label_counts", {}).values()) == 3
        and len(surface.get("diagnostic_case_labels", {})) == 3
        and surface.get("exact_verification_ns_assumed") == 0
        and assessment["decision"].get("training_allowed") is False
        and assessment["decision"].get("advice_enabled") is False,
        "verified version-history decision boundary",
    )
    return {
        "artifact_path": artifact_path,
        "assessment": assessment,
        "manifest": manifest,
        "verification": verification,
        "hashes": {
            "assessment": file_sha256(assessment_path),
            "manifest": file_sha256(manifest_path),
            "independent_verification": file_sha256(verification_path),
        },
    }


def load_verified_query_ladder_result(
    analysis_path: str | Path = DEFAULT_QUERY_LADDER_ANALYSIS,
) -> dict[str, Any]:
    """Authenticate the Benchmark task's completed query-ladder handoff."""
    path = Path(analysis_path).resolve()
    _require(path.is_relative_to(ROOT) and path.is_file(), "query-ladder analysis path")
    analysis = _read_json(path)
    inputs = analysis.get("inputs", {})
    run_dir = (ROOT / inputs.get("run_dir", "")).resolve()
    _require(run_dir.is_relative_to(ROOT) and run_dir.is_dir(), "query-ladder run path")
    execution_root = path.parent
    controller_path = execution_root / "runpod-architecture-query-ladder-execute-002/RUN.json"
    inventory_path = execution_root / "POST_RUN_INVENTORY.json"
    evidence_paths = {
        "analysis": path,
        "attempt_001_status": QUERY_LADDER_ATTEMPT_001_STATUS,
        "controller": controller_path,
        "freeze": QUERY_LADDER_FREEZE,
        "independent_verification": run_dir / "independent_verification.json",
        "post_run_inventory": inventory_path,
        "raw_measurements": run_dir / "raw_measurements.jsonl",
        "results": run_dir / "results.json",
        "runtime_binding": run_dir / "runtime_binding.json",
    }
    _require(all(item.is_file() for item in evidence_paths.values()),
             "query-ladder evidence closure")
    hashes = {name: file_sha256(item) for name, item in evidence_paths.items()}
    verification = _read_json(evidence_paths["independent_verification"])
    results = _read_json(evidence_paths["results"])
    controller = _read_json(controller_path)
    inventory = _read_json(inventory_path)
    _require(
        analysis.get("schema") == "cm-architecture-query-ladder-analysis/v1"
        and analysis.get("status") == "verified_interpretation_complete"
        and analysis.get("verification", {}).get("status") == "verified_complete"
        and analysis.get("verification", {}).get("rows_checked") == 27_648
        and analysis.get("verification", {}).get("counts")
        == {"failed": 0, "ok": 27_648, "refused": 0}
        and all(
            analysis["verification"].get(name) == 0
            for name in (
                "schedule_mismatches", "semantic_mismatches",
                "source_or_artifact_mismatches", "memory_measurement_mismatches",
            )
        ),
        "query-ladder analysis verification boundary",
    )
    _require(
        inputs.get("attempt_001_status_sha256") == hashes["attempt_001_status"]
        and inputs.get("controller_sha256") == hashes["controller"]
        and inputs.get("freeze_sha256") == hashes["freeze"]
        and inputs.get("independent_verification_sha256")
        == hashes["independent_verification"]
        and inputs.get("post_run_inventory_sha256") == hashes["post_run_inventory"]
        and inputs.get("raw_measurements_sha256") == hashes["raw_measurements"]
        and inputs.get("results_sha256") == hashes["results"],
        "query-ladder analysis evidence binding",
    )
    _require(
        verification.get("schema")
        == "cm-architecture-query-ladder-independent-verification/v1"
        and verification.get("status") == "verified_complete"
        and verification.get("rows_checked") == 27_648
        and verification.get("counts") == {"failed": 0, "ok": 27_648, "refused": 0}
        and verification.get("raw_measurements_sha256") == hashes["raw_measurements"]
        and verification.get("results_sha256") == hashes["results"]
        and verification.get("runtime_binding_sha256") == hashes["runtime_binding"]
        and verification.get("selector_or_neural_claim_permitted") is False
        and verification.get("cross_machine_claim_permitted") is False
        and all(
            verification.get(name) == 0
            for name in (
                "schedule_mismatches", "semantic_mismatches",
                "source_or_artifact_mismatches", "memory_measurement_mismatches",
            )
        ),
        "query-ladder independent verification boundary",
    )
    _require(
        results.get("schema") == "cm-architecture-query-ladder-result/v1"
        and results.get("status") == "complete"
        and results.get("expected_rows") == 27_648
        and results.get("counts") == verification["counts"]
        and results.get("raw_measurements_sha256") == hashes["raw_measurements"]
        and results.get("decision", {}).get("selector_fitted") is False
        and results.get("decision", {}).get("neural_training") is False
        and results.get("decision", {}).get("production_routing_changed") is False,
        "query-ladder result boundary",
    )
    claim = analysis.get("claim_boundary", {})
    _require(
        claim.get("four_point_query_ladder_interpretation_permitted") is True
        and claim.get("selector_or_neural_claim_permitted") is False
        and claim.get("memory_router_fitting_permitted") is False
        and claim.get("production_routing_change_permitted") is False
        and claim.get("cross_machine_claim_permitted") is False,
        "query-ladder claim boundary",
    )
    _require(
        controller.get("status") == "complete"
        and controller.get("cleanup", {}).get("owned_pod_absent") is True
        and controller.get("cleanup", {}).get("inventories") == {"v1": [], "v2": []}
        and inventory.get("owned_pod_absent") is True
        and inventory.get("inventories") == {"v1": [], "v2": []},
        "query-ladder cleanup boundary",
    )
    q64 = analysis.get("query_counts", {}).get("64", {})
    fixed = q64.get("fixed_arm", {})
    best_fixed = fixed.get("best_fixed_arm")
    oracle_geomean = fixed.get("case_median_geomean_slowdown_to_per_case_oracle", {}).get(
        best_fixed
    )
    _require(
        best_fixed == "cse_flat_bigint"
        and type(oracle_geomean) is float
        and oracle_geomean > DEVELOPMENT_HEADROOM_GATE,
        "query-ladder q64 diagnostic",
    )
    return {
        "analysis_path": path,
        "analysis": analysis,
        "hashes": hashes,
        "summary": {
            "status": analysis["status"],
            "rows_checked": verification["rows_checked"],
            "query_counts": [1, 4, 16, 64],
            "q64_best_fixed_arm": best_fixed,
            "q64_best_fixed_case_median_geomean_slowdown_to_oracle": oracle_geomean,
            "metric_is_sum_based_charged_headroom": False,
            "selector_or_neural_claim_permitted": False,
            "cross_machine_claim_permitted": False,
        },
    }


def version_history_trace(scenario: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Recreate the frozen trace shape, not any backend work or timing."""
    if scenario.get("id") == "architecture-refresh-control-k6":
        return (
            {"version": 0, "assumptions": [-1]},
            {"version": 1, "assumptions": [-1, -6]},
            {"version": 2, "assumptions": [-1]},
            {"version": 0, "assumptions": []},
        )
    versions = len(scenario["versions"])
    k = int(scenario["k"])
    assumptions = ((), (1,), (-1,), (k,), (-k,))
    return tuple(
        {"version": version, "assumptions": values}
        for version in range(versions)
        for values in assumptions
    )


def extract_cheap_features(
    scenario: Mapping[str, Any], trace: Sequence[Mapping[str, Any]]
) -> tuple[int, ...]:
    """Extract only source-blind structural counts available before timing."""
    versions = scenario["versions"]
    _require(type(versions) in (list, tuple) and len(versions) > 0, "scenario versions")
    first_count = len(versions[0]["clauses"])
    minimum_count = first_count
    maximum_count = first_count
    total_count = first_count
    churn = 0
    previous_count = first_count
    for version in versions[1:]:
        count = len(version["clauses"])
        total_count += count
        if count < minimum_count:
            minimum_count = count
        if count > maximum_count:
            maximum_count = count
        churn += abs(count - previous_count)
        previous_count = count

    assumption_count = 0
    version_mask = 0
    for query in trace:
        version = int(query["version"])
        _require(0 <= version < len(versions), "trace version")
        version_mask |= 1 << version
        assumption_count += len(query.get("assumptions", ()))
    distinct_versions = version_mask.bit_count()
    return (
        int(scenario["k"]),
        len(versions),
        total_count,
        minimum_count,
        maximum_count,
        churn,
        len(trace),
        assumption_count,
        distinct_versions,
        len(trace) - distinct_versions,
    )


def fixed_sat_control(features: Sequence[int]) -> str:
    del features
    return "sat/resident_engine"


def fixed_cnf_control(features: Sequence[int]) -> str:
    del features
    return "cnf/resident_engine"


def bounded_cnf_then_sat_control(features: Sequence[int]) -> str:
    """Cheap analytical sanity control; not a fitted or promotable selector."""
    return (
        "cnf/resident_engine"
        if features[0] <= 6 and features[4] <= 8
        else "sat/resident_engine"
    )


CONTROLS: dict[str, Callable[[Sequence[int]], str]] = {
    "fixed_cnf": fixed_cnf_control,
    "fixed_sat": fixed_sat_control,
    "bounded_cnf_then_sat": bounded_cnf_then_sat_control,
}


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    _require(bool(ordered), "timing samples")
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def _batch_timing(
    function: Callable[[Mapping[str, Any], Sequence[Mapping[str, Any]]], Any],
    cases: Sequence[tuple[Mapping[str, Any], Sequence[Mapping[str, Any]]]],
    *,
    batches: int,
    repetitions: int,
) -> dict[str, Any]:
    _require(batches >= 5 and repetitions >= 100, "timing configuration")
    _require(bool(cases), "timing cases")
    samples: list[float] = []
    checksum = 0
    for _ in range(batches):
        started = time.perf_counter_ns()
        for _ in range(repetitions):
            for scenario, trace in cases:
                value = function(scenario, trace)
                if isinstance(value, tuple):
                    checksum ^= value[0] + value[-1]
                else:
                    checksum ^= len(value)
        elapsed = time.perf_counter_ns() - started
        samples.append(elapsed / (repetitions * len(cases)))
    return {
        "batches": batches,
        "repetitions_per_case_per_batch": repetitions,
        "samples": len(samples),
        "minimum_ns_per_case": min(samples),
        "median_ns_per_case": statistics.median(samples),
        "p95_ns_per_case": _percentile(samples, 0.95),
        "checksum": checksum,
    }


def benchmark_analytical_controls(
    cases: Sequence[tuple[Mapping[str, Any], Sequence[Mapping[str, Any]]]],
    *,
    budget_ns_per_case: float,
    batches: int = 21,
    repetitions: int = 2_000,
) -> dict[str, Any]:
    """Time feature extraction and controls only; never execute exact backends."""
    feature = _batch_timing(
        lambda scenario, trace: extract_cheap_features(scenario, trace),
        cases,
        batches=batches,
        repetitions=repetitions,
    )
    combined: dict[str, Any] = {}
    for name, control in CONTROLS.items():
        def execute(
            scenario: Mapping[str, Any], trace: Sequence[Mapping[str, Any]],
            selected: Callable[[Sequence[int]], str] = control,
        ) -> str:
            return selected(extract_cheap_features(scenario, trace))

        measured = _batch_timing(
            execute, cases, batches=batches, repetitions=repetitions
        )
        measured["p95_within_budget"] = (
            measured["p95_ns_per_case"] <= budget_ns_per_case
        )
        combined[name] = measured
    return {
        "measurement_role": "local_development_diagnostic_not_cross_host_evidence",
        "clock": "time.perf_counter_ns",
        "host": {
            "python": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "budget_ns_per_case": budget_ns_per_case,
        "exact_backend_executions": 0,
        "feature_extraction": feature,
        "combined_feature_and_control": combined,
    }


def _assign_split(source_group_sha256: str) -> str:
    _validate_hash(source_group_sha256, "source group")
    bucket = int(hashlib.sha256(
        f"{SPLIT_SALT}:{source_group_sha256}".encode("ascii")
    ).hexdigest()[:8], 16) % 100
    for name, start, stop in SPLIT_BUCKETS:
        if start <= bucket < stop:
            return name
    raise AssertionError(bucket)  # pragma: no cover


def _source_group(case_id: str, scenario: Mapping[str, Any], freeze: Mapping[str, Any]) -> str:
    histories = {
        row["case_id"]: row for row in freeze["fresh_corpus"]["history_pairs"]
    }
    if case_id in histories:
        row = histories[case_id]
        return canonical_sha256({
            "role": "source_expression_group",
            "source_expression_v2_sha256": row["source_expression_v2_sha256"],
        })
    _require(case_id == "architecture-refresh-control-k6", "unbound history source")
    return canonical_sha256({
        "role": "synthetic_functional_control_group",
        "k": scenario["k"],
        "versions": scenario["versions"],
    })


def build_source_blind_rows(bundle: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[Any]]:
    assessment = bundle["assessment"]
    surface = assessment["surfaces"][SURFACE_ID]
    freeze_path = _project_path(
        assessment["evidence_paths"]["freeze"], "verified freeze"
    )
    freeze = _read_json(freeze_path)
    catalog = resolve_catalog(ROOT, freeze)["D"]
    labels = surface["diagnostic_case_labels"]
    _require(set(labels) <= set(catalog), "label-to-scenario binding")
    rows: list[dict[str, Any]] = []
    timing_cases: list[Any] = []
    for case_id in sorted(labels):
        scenario = catalog[case_id]
        _require("refusal" not in scenario, "refused case received a label")
        trace = version_history_trace(scenario)
        features = extract_cheap_features(scenario, trace)
        _require(len(features) == len(FEATURE_NAMES), "feature vector width")
        group = _source_group(case_id, scenario, freeze)
        scenario_hash = canonical_sha256(scenario)
        token = canonical_sha256({
            "source_group_sha256": group,
            "scenario_sha256": scenario_hash,
            "protocol": SCHEMA,
        })
        rows.append({
            "case_token": token,
            "source_group_sha256": group,
            "split": _assign_split(group),
            "features": list(features),
            "backend_label": labels[case_id],
            "label_source": "independently_verified_exact_per_case_median_oracle",
        })
        timing_cases.append((scenario, trace))
    _require(len({row["case_token"] for row in rows}) == len(rows), "duplicate case token")
    return rows, timing_cases


def _split_audit(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    groups_by_split: dict[str, set[str]] = {
        name: set() for name, _, _ in SPLIT_BUCKETS
    }
    for row in rows:
        groups_by_split[row["split"]].add(row["source_group_sha256"])
    intersections = 0
    names = list(groups_by_split)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            intersections += len(groups_by_split[left] & groups_by_split[right])
    counts = {name: len(groups_by_split[name]) for name in names}
    requirements_passed = all(
        counts[name] >= minimum
        for name, minimum in MIN_SPLIT_SOURCE_GROUPS.items()
    )
    return {
        "assignment": "sha256(salt:source_group_sha256) modulo 100",
        "split_ranges": {
            name: [start, stop] for name, start, stop in SPLIT_BUCKETS
        },
        "source_groups_by_split": counts,
        "cross_split_source_group_intersections": intersections,
        "split_isolation_passed": intersections == 0,
        "minimum_source_groups_by_split": dict(MIN_SPLIT_SOURCE_GROUPS),
        "minimum_split_sizes_passed": requirements_passed,
    }


def charged_speedup(
    *,
    best_fixed_ns: float,
    selected_exact_ns: float,
    cases: int,
    per_case_costs_ns: Mapping[str, int | float | None],
) -> float | None:
    _require(best_fixed_ns > 0 and selected_exact_ns > 0 and cases > 0, "economics")
    required = {
        "feature_extraction_and_control",
        "model_inference",
        "exact_verification",
        "expected_fallback",
    }
    _require(set(per_case_costs_ns) == required, "charged cost fields")
    if any(value is None for value in per_case_costs_ns.values()):
        return None
    total_cost = 0.0
    for name, value in per_case_costs_ns.items():
        _require(
            type(value) in (int, float) and math.isfinite(value) and value >= 0,
            f"invalid charged cost: {name}",
        )
        total_cost += float(value)
    return best_fixed_ns / (selected_exact_ns + cases * total_cost)


def evaluate_partition_certificate(record: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate whether a future C5 proposal can soundly avoid global-best work."""
    required_true = (
        "certificate_present",
        "global_objective_bound_sound",
        "all_unexplored_partitions_covered",
        "checker_independent_of_model",
        "candidate_reconstruction_exact",
        "exact_fallback_unchanged",
        "completion_search_not_run",
    )
    booleans_passed = all(record.get(name) is True for name in required_true)
    work = record.get("measured_global_work_avoided_fraction")
    work_passed = type(work) in (int, float) and math.isfinite(work) and (
        MIN_GLOBAL_WORK_AVOIDED_FRACTION <= work <= 1.0
    )
    verification_cost = record.get("certificate_verification_ns_per_case")
    cost_measured = type(verification_cost) is int and verification_cost >= 0
    tests_passed = (
        record.get("adversarial_certificate_failures") == 0
        and record.get("variable_renaming_failures") == 0
        and record.get("sharing_or_operand_order_failures") == 0
    )
    eligible = booleans_passed and work_passed and cost_measured and tests_passed
    return {
        "required_properties": list(required_true),
        "minimum_global_work_avoided_fraction": MIN_GLOBAL_WORK_AVOIDED_FRACTION,
        "soundness_properties_passed": booleans_passed,
        "material_work_avoidance_passed": work_passed,
        "verification_cost_measured": cost_measured,
        "metamorphic_and_adversarial_tests_passed": tests_passed,
        "partition_learning_eligible": eligible,
        "reason": (
            "certificate satisfies soundness, charged-cost, and material-work gates"
            if eligible
            else "no sound charged certificate currently avoids material global-best work"
        ),
    }


def _validate_timing(timing: Mapping[str, Any], budget: float) -> None:
    _require(
        timing.get("measurement_role")
        == "local_development_diagnostic_not_cross_host_evidence"
        and timing.get("clock") == "time.perf_counter_ns"
        and timing.get("budget_ns_per_case") == budget
        and timing.get("exact_backend_executions") == 0
        and set(timing.get("combined_feature_and_control", {})) == set(CONTROLS),
        "analytical-control timing boundary",
    )
    for name, measured in {
        "feature_extraction": timing.get("feature_extraction"),
        **timing["combined_feature_and_control"],
    }.items():
        _require(
            isinstance(measured, Mapping)
            and type(measured.get("batches")) is int
            and measured["batches"] >= 5
            and type(measured.get("repetitions_per_case_per_batch")) is int
            and measured["repetitions_per_case_per_batch"] >= 100
            and type(measured.get("samples")) is int
            and measured["samples"] == measured["batches"]
            and all(
                type(measured.get(field)) in (int, float)
                and math.isfinite(measured[field])
                and measured[field] > 0
                for field in (
                    "minimum_ns_per_case", "median_ns_per_case", "p95_ns_per_case"
                )
            )
            and measured["minimum_ns_per_case"]
            <= measured["median_ns_per_case"] <= measured["p95_ns_per_case"],
            f"invalid timing measurement: {name}",
        )
    for name, measured in timing["combined_feature_and_control"].items():
        _require(
            measured.get("p95_within_budget")
            is (measured["p95_ns_per_case"] <= budget),
            f"timing budget flag: {name}",
        )


def build_assessment(
    bundle: Mapping[str, Any],
    query_ladder: Mapping[str, Any],
    timing: Mapping[str, Any],
    *,
    source_bindings: Mapping[str, str],
    source_checkpoint: str,
) -> dict[str, Any]:
    assessment = bundle["assessment"]
    query_summary = query_ladder["summary"]
    _require(
        query_summary.get("status") == "verified_interpretation_complete"
        and query_summary.get("selector_or_neural_claim_permitted") is False
        and query_summary.get("cross_machine_claim_permitted") is False,
        "query-ladder handoff boundary",
    )
    surface = assessment["surfaces"][SURFACE_ID]
    budget = float(surface["maximum_overhead_ns_per_case_preserving_1_10x"])
    _validate_timing(timing, budget)
    rows, _ = build_source_blind_rows(bundle)
    split_audit = _split_audit(rows)
    label_counts = Counter(row["backend_label"] for row in rows)
    label_group_counts = Counter()
    for label in label_counts:
        label_group_counts[label] = len({
            row["source_group_sha256"] for row in rows
            if row["backend_label"] == label
        })
    source_groups = len({row["source_group_sha256"] for row in rows})
    label_support_passed = (
        len(label_counts) >= 2
        and all(value >= MIN_SOURCE_GROUPS_PER_LABEL for value in label_group_counts.values())
    )

    control_predictions = {
        name: [control(row["features"]) for row in rows]
        for name, control in CONTROLS.items()
    }
    analytical = control_predictions["bounded_cnf_then_sat"]
    analytical_matches_oracle = all(
        predicted == row["backend_label"]
        for predicted, row in zip(analytical, rows)
    )
    analytical_p95 = timing["combined_feature_and_control"][
        "bounded_cnf_then_sat"
    ]["p95_ns_per_case"]
    optimistic_costs = {
        "feature_extraction_and_control": analytical_p95,
        "model_inference": 0,
        "exact_verification": 0,
        "expected_fallback": 0,
    }
    optimistic_speedup = charged_speedup(
        best_fixed_ns=surface["best_fixed_median_sum_ns"],
        selected_exact_ns=surface["oracle_median_sum_ns"],
        cases=len(rows),
        per_case_costs_ns=optimistic_costs,
    ) if analytical_matches_oracle else None
    complete_costs = {
        "feature_extraction_and_control": analytical_p95,
        "model_inference": None,
        "exact_verification": None,
        "expected_fallback": None,
    }
    fully_charged_speedup = charged_speedup(
        best_fixed_ns=surface["best_fixed_median_sum_ns"],
        selected_exact_ns=surface["oracle_median_sum_ns"],
        cases=len(rows),
        per_case_costs_ns=complete_costs,
    )

    c5_record = {
        "certificate_present": False,
        "global_objective_bound_sound": False,
        "all_unexplored_partitions_covered": False,
        "checker_independent_of_model": False,
        "candidate_reconstruction_exact": True,
        "exact_fallback_unchanged": True,
        "completion_search_not_run": False,
        "measured_global_work_avoided_fraction": 0.0,
        "certificate_verification_ns_per_case": None,
        "adversarial_certificate_failures": None,
        "variable_renaming_failures": 0,
        "sharing_or_operand_order_failures": None,
    }
    certificate = evaluate_partition_certificate(c5_record)
    gates = {
        "benchmark_artifact_independently_verified": True,
        "benchmark_evidence_hashes_current": True,
        "query_ladder_result_independently_verified": True,
        "query_ladder_sum_based_charged_headroom_available": False,
        "query_ladder_selector_or_neural_claim_permitted": False,
        "query_ladder_cross_machine_replication_complete": False,
        "benchmark_execution_performed_here": False,
        "gross_exact_headroom_at_least_1_10": (
            surface["gross_headroom_speedup"] >= DEVELOPMENT_HEADROOM_GATE
        ),
        "source_blind_model_features": True,
        "split_isolation": split_audit["split_isolation_passed"],
        "minimum_split_sizes": split_audit["minimum_split_sizes_passed"],
        "minimum_label_support": label_support_passed,
        "protocol_precommitted_before_current_labels": False,
        "timing_host_matches_exact_benchmark_host": False,
        "all_recognition_verification_and_fallback_costs_measured": False,
        "fully_charged_speedup_at_least_1_10": (
            fully_charged_speedup is not None
            and fully_charged_speedup >= DEVELOPMENT_HEADROOM_GATE
        ),
        "c5_sound_early_termination_certificate": certificate[
            "partition_learning_eligible"
        ],
    }
    training_allowed = all(
        value for name, value in gates.items()
        if name != "benchmark_execution_performed_here"
    ) and gates["benchmark_execution_performed_here"] is False
    _require(training_allowed is False, "current evidence unexpectedly authorized training")
    result = {
        "schema": SCHEMA,
        "status": "complete_no_training",
        "classification": "source_blind_development_only_fail_closed",
        "source_checkpoint": source_checkpoint,
        "source_bindings": dict(sorted(source_bindings.items())),
        "benchmark_input": {
            "artifact_path": str(bundle["artifact_path"].relative_to(ROOT)).replace("\\", "/"),
            "assessment_sha256": bundle["hashes"]["assessment"],
            "manifest_sha256": bundle["hashes"]["manifest"],
            "independent_verification_sha256": bundle["hashes"][
                "independent_verification"
            ],
            "verification_status": bundle["verification"]["status"],
            "surface_id": SURFACE_ID,
            "consumption_mode": "verified_artifact_only_no_benchmark_replay",
            "exact_backend_executions": 0,
        },
        "query_ladder_input": {
            "analysis_path": str(query_ladder["analysis_path"].relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "evidence_sha256": dict(sorted(query_ladder["hashes"].items())),
            "summary": dict(query_summary),
            "consumption_mode": "verified_analysis_only_no_benchmark_replay",
            "exact_backend_executions": 0,
        },
        "protocol": {
            "role": "post-label mechanics audit and future development protocol",
            "current_labels_were_exposed_before_protocol": True,
            "current_results_are_retrospective_diagnostics_only": True,
            "prospective_split_defined_or_consumed": False,
            "selector_fit_performed": False,
            "feature_names": list(FEATURE_NAMES),
            "forbidden_model_fields": list(FORBIDDEN_MODEL_FIELDS),
            "model_input_contains_only_feature_vector": True,
            "source_grouping_visible_to_split_auditor_only": True,
            "split_salt": SPLIT_SALT,
            "minimum_source_groups_per_label": MIN_SOURCE_GROUPS_PER_LABEL,
        },
        "dataset": {
            "role": "already_exposed_development_only",
            "cases": len(rows),
            "source_groups": source_groups,
            "label_counts": dict(sorted(label_counts.items())),
            "source_groups_per_label": dict(sorted(label_group_counts.items())),
            "rows": rows,
            "split_audit": split_audit,
            "case_ids_exposed_to_model": False,
            "prospective_cases_consumed": 0,
        },
        "analytical_controls": {
            "controls": {
                "fixed_sat": "zero-fit exact fixed baseline",
                "fixed_cnf": "zero-fit exact fixed baseline",
                "bounded_cnf_then_sat": (
                    "structural width/clause bound; retrospective sanity only"
                ),
            },
            "predictions_by_opaque_case_order": control_predictions,
            "bounded_control_matches_current_oracle_labels": analytical_matches_oracle,
            "credit_toward_training_gate": False,
            "timing": timing,
        },
        "economics": {
            "development_gate": DEVELOPMENT_HEADROOM_GATE,
            "verified_best_fixed_ns": surface["best_fixed_median_sum_ns"],
            "verified_oracle_ns": surface["oracle_median_sum_ns"],
            "verified_gross_speedup": surface["gross_headroom_speedup"],
            "verified_gross_saving_ns": surface["gross_headroom_ns"],
            "maximum_total_overhead_ns_per_case_preserving_1_10": budget,
            "optimistic_p95_costs_ns_per_case": optimistic_costs,
            "optimistic_p95_speedup_if_retrospective_control_is_oracle": optimistic_speedup,
            "fully_charged_costs_ns_per_case": complete_costs,
            "fully_charged_speedup": fully_charged_speedup,
            "cost_coverage_complete": False,
            "cross_host_timing_used_for_authorization": False,
        },
        "c5_certificate_investigation": {
            "current_record": c5_record,
            "evaluation": certificate,
            "global_best_completion_still_required": True,
            "future_requirement": (
                "an independently checked global bound must cover every unexplored "
                "partition and avoid at least 25% of measured completion work after "
                "certificate-verification cost"
            ),
        },
        "gates": gates,
        "decision": {
            "training_label_table_ready": False,
            "training_allowed": False,
            "training_performed": False,
            "selector_fitted": False,
            "advice_enabled": False,
            "complete_abstention": True,
            "exact_fallback": "unchanged exact path",
            "prospective_data_consumed": False,
            "benchmark_executed_by_learning_task": False,
            "production_write": False,
            "production_promotion": False,
            "reason": (
                "three exposed source groups are insufficient; protocol postdates the "
                "labels; local recognition timing is cross-host; full verification, "
                "inference, and fallback costs are absent; the new query ladder is one-host "
                "and forbids selector/neural claims; C5 has no early-stop certificate"
            ),
        },
    }
    validate_assessment(result)
    return result


def fail_closed_decision(reason: str = "verified_benchmark_input_rejected") -> dict[str, Any]:
    """Return the only permitted behavior when a prerequisite is absent or invalid."""
    return {
        "status": "abstained",
        "reason": reason,
        "training_allowed": False,
        "training_performed": False,
        "selector_fitted": False,
        "advice_enabled": False,
        "complete_abstention": True,
        "exact_fallback": "unchanged exact path",
        "prospective_data_consumed": False,
        "production_write": False,
        "production_promotion": False,
    }


def evaluate_or_abstain(
    artifact: str | Path,
    query_ladder_analysis: str | Path,
    timing: Mapping[str, Any],
    *,
    source_bindings: Mapping[str, str],
    source_checkpoint: str,
) -> dict[str, Any]:
    try:
        bundle = load_verified_benchmark_artifact(artifact)
        query_ladder = load_verified_query_ladder_result(query_ladder_analysis)
        return build_assessment(
            bundle,
            query_ladder,
            timing,
            source_bindings=source_bindings,
            source_checkpoint=source_checkpoint,
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return fail_closed_decision()


def run_with_exact_fallback(
    assessment: Mapping[str, Any], exact_fallback: Callable[..., Any], *args: Any, **kwargs: Any
) -> Any:
    decision = assessment.get("decision", assessment)
    _require(
        decision.get("advice_enabled") is False
        and decision.get("complete_abstention") is True
        and decision.get("exact_fallback") == "unchanged exact path",
        "unsafe advice contract",
    )
    return exact_fallback(*args, **kwargs)


def validate_assessment(assessment: Mapping[str, Any]) -> None:
    _require(
        assessment.get("schema") == SCHEMA
        and assessment.get("status") == "complete_no_training"
        and assessment.get("classification")
        == "source_blind_development_only_fail_closed",
        "assessment identity",
    )
    expected = {
        "schema", "status", "classification", "source_checkpoint", "source_bindings",
        "benchmark_input", "query_ladder_input", "protocol", "dataset",
        "analytical_controls", "economics", "c5_certificate_investigation", "gates",
        "decision",
    }
    _require(set(assessment) == expected, "assessment fields")
    _require(
        type(assessment["source_checkpoint"]) is str
        and len(assessment["source_checkpoint"]) == 40
        and set(assessment["source_checkpoint"]) <= HEX
        and isinstance(assessment["source_bindings"], Mapping)
        and bool(assessment["source_bindings"])
        and all(
            _validate_hash(value, f"source:{name}") == value
            for name, value in assessment["source_bindings"].items()
        ),
        "assessment source binding",
    )
    benchmark = assessment["benchmark_input"]
    _require(
        benchmark.get("verification_status") == "verified_no_training"
        and benchmark.get("surface_id") == SURFACE_ID
        and benchmark.get("consumption_mode")
        == "verified_artifact_only_no_benchmark_replay"
        and benchmark.get("exact_backend_executions") == 0
        and all(
            _validate_hash(benchmark.get(field), field) == benchmark[field]
            for field in (
                "assessment_sha256", "manifest_sha256",
                "independent_verification_sha256",
            )
        ),
        "benchmark consumption boundary",
    )
    query_ladder = assessment["query_ladder_input"]
    _require(
        query_ladder.get("consumption_mode")
        == "verified_analysis_only_no_benchmark_replay"
        and query_ladder.get("exact_backend_executions") == 0
        and query_ladder.get("summary", {}).get("status")
        == "verified_interpretation_complete"
        and query_ladder["summary"].get("metric_is_sum_based_charged_headroom") is False
        and query_ladder["summary"].get("selector_or_neural_claim_permitted") is False
        and query_ladder["summary"].get("cross_machine_claim_permitted") is False
        and isinstance(query_ladder.get("evidence_sha256"), Mapping)
        and all(
            _validate_hash(value, f"query-ladder:{name}") == value
            for name, value in query_ladder["evidence_sha256"].items()
        ),
        "query-ladder consumption boundary",
    )
    protocol = assessment["protocol"]
    _require(
        protocol.get("feature_names") == list(FEATURE_NAMES)
        and protocol.get("forbidden_model_fields") == list(FORBIDDEN_MODEL_FIELDS)
        and protocol.get("model_input_contains_only_feature_vector") is True
        and protocol.get("source_grouping_visible_to_split_auditor_only") is True
        and protocol.get("current_labels_were_exposed_before_protocol") is True
        and protocol.get("current_results_are_retrospective_diagnostics_only") is True
        and protocol.get("prospective_split_defined_or_consumed") is False
        and protocol.get("selector_fit_performed") is False,
        "protocol boundary",
    )
    dataset = assessment["dataset"]
    rows = dataset.get("rows")
    _require(
        dataset.get("role") == "already_exposed_development_only"
        and type(rows) is list
        and dataset.get("cases") == len(rows) == 3
        and dataset.get("source_groups")
        == len({row.get("source_group_sha256") for row in rows})
        and dataset.get("case_ids_exposed_to_model") is False
        and dataset.get("prospective_cases_consumed") == 0,
        "dataset boundary",
    )
    allowed_row_fields = {
        "case_token", "source_group_sha256", "split", "features",
        "backend_label", "label_source",
    }
    for row in rows:
        _require(
            set(row) == allowed_row_fields
            and _validate_hash(row["case_token"], "case token") == row["case_token"]
            and _validate_hash(row["source_group_sha256"], "source group")
            == row["source_group_sha256"]
            and row["split"] in {name for name, _, _ in SPLIT_BUCKETS}
            and type(row["features"]) is list
            and len(row["features"]) == len(FEATURE_NAMES)
            and all(type(value) is int and value >= 0 for value in row["features"])
            and row["backend_label"]
            in {"cm/resident_engine", "cse/resident_engine", "cnf/resident_engine", "sat/resident_engine"}
            and row["label_source"]
            == "independently_verified_exact_per_case_median_oracle",
            "source-blind row boundary",
        )
    split = dataset["split_audit"]
    recomputed_split = _split_audit(rows)
    _require(
        split == recomputed_split
        and all(row["split"] == _assign_split(row["source_group_sha256"]) for row in rows)
        and split.get("cross_split_source_group_intersections") == 0
        and split.get("split_isolation_passed") is True,
        "split isolation",
    )
    recomputed_labels = Counter(row["backend_label"] for row in rows)
    recomputed_group_labels = {
        label: len({
            row["source_group_sha256"] for row in rows
            if row["backend_label"] == label
        })
        for label in recomputed_labels
    }
    _require(
        dataset.get("label_counts") == dict(sorted(recomputed_labels.items()))
        and dataset.get("source_groups_per_label")
        == dict(sorted(recomputed_group_labels.items())),
        "dataset label accounting",
    )
    timing = assessment["analytical_controls"]["timing"]
    budget = assessment["economics"][
        "maximum_total_overhead_ns_per_case_preserving_1_10"
    ]
    _validate_timing(timing, budget)
    controls = assessment["analytical_controls"]
    recomputed_predictions = {
        name: [control(row["features"]) for row in rows]
        for name, control in CONTROLS.items()
    }
    _require(
        controls.get("predictions_by_opaque_case_order") == recomputed_predictions
        and controls.get("bounded_control_matches_current_oracle_labels")
        is all(
            predicted == row["backend_label"]
            for predicted, row in zip(
                recomputed_predictions["bounded_cnf_then_sat"], rows
            )
        )
        and controls.get("credit_toward_training_gate") is False,
        "analytical control replay",
    )
    economics = assessment["economics"]
    _require(
        economics.get("development_gate") == DEVELOPMENT_HEADROOM_GATE
        and economics.get("verified_gross_speedup") >= DEVELOPMENT_HEADROOM_GATE
        and economics.get("fully_charged_speedup") is None
        and economics.get("cost_coverage_complete") is False
        and economics.get("cross_host_timing_used_for_authorization") is False,
        "charged economics boundary",
    )
    certificate = assessment["c5_certificate_investigation"]
    _require(
        certificate.get("global_best_completion_still_required") is True
        and certificate.get("evaluation", {}).get("partition_learning_eligible") is False,
        "C5 certificate boundary",
    )
    gates = assessment["gates"]
    _require(
        gates.get("benchmark_artifact_independently_verified") is True
        and gates.get("benchmark_evidence_hashes_current") is True
        and gates.get("query_ladder_result_independently_verified") is True
        and gates.get("query_ladder_sum_based_charged_headroom_available") is False
        and gates.get("query_ladder_selector_or_neural_claim_permitted") is False
        and gates.get("query_ladder_cross_machine_replication_complete") is False
        and gates.get("benchmark_execution_performed_here") is False
        and gates.get("gross_exact_headroom_at_least_1_10") is True
        and gates.get("source_blind_model_features") is True
        and gates.get("split_isolation") is True
        and gates.get("minimum_split_sizes") is False
        and gates.get("minimum_label_support") is False
        and gates.get("protocol_precommitted_before_current_labels") is False
        and gates.get("timing_host_matches_exact_benchmark_host") is False
        and gates.get("all_recognition_verification_and_fallback_costs_measured") is False
        and gates.get("fully_charged_speedup_at_least_1_10") is False
        and gates.get("c5_sound_early_termination_certificate") is False,
        "learning gates",
    )
    decision = assessment["decision"]
    _require(
        decision == {
            "training_label_table_ready": False,
            "training_allowed": False,
            "training_performed": False,
            "selector_fitted": False,
            "advice_enabled": False,
            "complete_abstention": True,
            "exact_fallback": "unchanged exact path",
            "prospective_data_consumed": False,
            "benchmark_executed_by_learning_task": False,
            "production_write": False,
            "production_promotion": False,
            "reason": decision["reason"],
        },
        "fail-closed decision",
    )


def render_report(assessment: Mapping[str, Any]) -> str:
    economics = assessment["economics"]
    timing = assessment["analytical_controls"]["timing"]
    combined = timing["combined_feature_and_control"]
    split = assessment["dataset"]["split_audit"]
    certificate = assessment["c5_certificate_investigation"]["evaluation"]
    query = assessment["query_ladder_input"]["summary"]
    timing_rows = [
        f"| `{name}` | {value['median_ns_per_case']:.1f} | "
        f"{value['p95_ns_per_case']:.1f} | {value['p95_within_budget']} |"
        for name, value in sorted(combined.items())
    ]
    return "\n".join([
        "# Source-blind version-history learning protocol",
        "",
        "Date: 2026-09-04  ",
        "Status: **implemented and verified mechanically; training remains disabled**",
        "",
        "## Outcome",
        "",
        "The learning gate consumes only the independently verified post-benchmark",
        "artifact. It hash-checks that artifact, its independent verification, every",
        "bound evidence file, and every bound analysis source. It does not invoke a",
        "benchmark runner, exact backend, cloud job, selector fit, or neural trainer.",
        "",
        "It also consumes the Benchmark task's completed 27,648-row query-ladder",
        "analysis through its independent verifier and bound file hashes. At q64 its",
        f"best fixed arm is `{query['q64_best_fixed_arm']}` and its case-median",
        f"geometric-mean slowdown to the per-case oracle is "
        f"`{query['q64_best_fixed_case_median_geomean_slowdown_to_oracle']:.9f}x`.",
        "That is not the required sum-based, fully charged headroom metric; the artifact",
        "explicitly forbids selector/neural claims and still requires cross-machine",
        "replication. The learning gate therefore records it but cannot promote it.",
        "",
        f"The verified resident version-history surface retains "
        f"`{economics['verified_gross_speedup']:.9f}x` gross headroom across only",
        f"{assessment['dataset']['cases']} already exposed source groups. The maximum",
        f"total overhead preserving 1.10x is only "
        f"`{economics['maximum_total_overhead_ns_per_case_preserving_1_10']:.1f} ns/case`.",
        "",
        "## Source-blind protocol",
        "",
        "Only ten pre-timing structural counts enter the model feature vector. Case and",
        "source identity, provenance hashes, split names, labels, arm order, blocks, and",
        "all timings are forbidden model fields. Opaque source-group hashes are visible",
        "only to the split auditor. Deterministic salted group assignment produces three",
        "development-only buckets; it does not manufacture a prospective split from",
        "already exposed cases.",
        "",
        f"Cross-split source-group intersections are "
        f"`{split['cross_split_source_group_intersections']}`. Minimum split sizes pass:",
        f"`{split['minimum_split_sizes_passed']}`. Current labels predate this protocol,",
        "so current control accuracy is retrospective and receives no training credit.",
        "",
        "## Ultra-cheap analytical controls",
        "",
        f"Local `{timing['host']['platform']}` development timing used",
        "`time.perf_counter_ns`; it is diagnostic, not cross-host authorization evidence.",
        "No exact backend was executed by the timing harness.",
        "",
        "| Feature + control | Median ns/case | p95 ns/case | p95 within budget |",
        "|---|---:|---:|---|",
        *timing_rows,
        "",
        "Even if the retrospective bounded control is credited as an oracle and model",
        "inference, exact verification, and fallback are assumed free, that is only an",
        "optimistic diagnostic. The fully charged speedup is deliberately `null` because",
        "those costs are unmeasured; the gate fails closed instead of substituting zeros.",
        "",
        "## C5 certificate / early termination",
        "",
        "A ranked partition or exactly reconstructed candidate is not a global-best",
        "certificate. Eligibility requires an independently checked sound bound covering",
        "every unexplored partition, exact candidate reconstruction, unchanged exact",
        "fallback, no completion search, zero adversarial/metamorphic failures, measured",
        f"certificate cost, and at least "
        f"`{certificate['minimum_global_work_avoided_fraction']:.0%}` measured global",
        "completion work avoided after charging that cost. C5 supplies no such certificate.",
        "",
        "## Decision",
        "",
        "Training, selector fitting, prospective consumption, and routing advice remain",
        "disabled. Every request abstains to the unchanged exact path. A later Benchmark",
        "task result can enter only as an independently verified artifact; this learning",
        "implementation will not reproduce its measurements.",
        "",
    ])
