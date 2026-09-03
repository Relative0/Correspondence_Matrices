"""Fail-closed readiness audit for neural exact-backend guidance.

This module does not train or route.  It binds exposed development evidence,
recomputes optimistic selector economics, and refuses training labels when the
exact portfolio or its source state is incomplete.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT_SCHEMA = "crse-neural-architecture-reassessment/v1"
LABEL_SCHEMA = "crse-exact-backend-development-labels/r2-bigint-v1"
ARTIFACT_SCHEMA = "crse-neural-reassessment-artifacts/v1"
VERIFICATION_SCHEMA = "crse-neural-reassessment-independent-verification/v1"
DEVELOPMENT_HEADROOM_GATE = 1.10
PROSPECTIVE_CHARGED_GATE = 1.05
MAX_JSON_BYTES = 64 * 1024 * 1024

RESTRICTED_METHODS = {
    "restricted_r0_occurrence",
    "restricted_r1_identity_memo",
    "restricted_r2_topological_liveness",
    "flattened_cse_words",
    "cm_ir_words",
    "compiled_truth_projection",
}
ENGINE_METHODS = {
    "r2_per_query",
    "cse_bigint",
    "cse_words",
    "cm_ir_bigint",
    "cm_ir_words",
    "full_projection",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    size = path.stat().st_size
    if not 0 < size <= MAX_JSON_BYTES:
        raise ValueError(f"JSON evidence outside size bound: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n")


def _require_hash(value: Any, field: str) -> str:
    if (type(value) is not str or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise ValueError(f"invalid SHA-256 field: {field}")
    return value


def _source_drift(manifest: dict[str, Any]) -> tuple[list[str], list[str]]:
    sources = manifest.get("local_sources", manifest.get("sources", {}))
    if type(sources) is not dict or not sources:
        raise ValueError("evidence manifest has no source binding")
    drift: list[str] = []
    missing: list[str] = []
    for name, expected in sorted(sources.items()):
        _require_hash(expected, f"source:{name}")
        path = Path(name)
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            missing.append(name)
        elif file_sha256(path) != expected:
            drift.append(name)
    return drift, missing


def load_verified_run(
    run: Path,
    *,
    results_schema: str,
    manifest_schema: str,
    verification_schema: str,
) -> dict[str, Any]:
    """Load a hash-bound run and independently verified result document."""
    run = run.resolve()
    results_path = run / "results.json"
    manifest_path = run / "manifest.json"
    verification_path = run / "independent_verification.json"
    results = read_json(results_path)
    manifest = read_json(manifest_path)
    verification = read_json(verification_path)
    if results.get("schema") != results_schema or results.get("status") != "complete":
        raise ValueError("stale or incomplete exact result schema")
    if manifest.get("schema") != manifest_schema:
        raise ValueError("stale exact manifest schema")
    if verification.get("schema") != verification_schema or verification.get("status") != "verified":
        raise ValueError("exact evidence lacks independent verified status")

    artifacts = manifest.get("artifacts")
    if type(artifacts) is not dict or "results.json" not in artifacts:
        raise ValueError("exact manifest does not bind results")
    for name, expected in sorted(artifacts.items()):
        _require_hash(expected, f"artifact:{name}")
        path = run / name
        if not path.is_file() or file_sha256(path) != expected:
            raise ValueError(f"exact artifact hash mismatch: {name}")
    results_sha = file_sha256(results_path)
    manifest_sha = file_sha256(manifest_path)
    if (verification.get("results_sha256") != results_sha
            or verification.get("manifest_sha256") != manifest_sha):
        raise ValueError("independent verification binding mismatch")
    if (verification.get("training_performed", False) is not False
            or verification.get("prospective_data_consumed", False) is not False
            or verification.get("production_write", False) is not False
            or verification.get("production_promotion", False) is not False):
        raise ValueError("exact label evidence violates development boundary")
    drift, missing = _source_drift(manifest)
    return {
        "run": run,
        "results": results,
        "manifest": manifest,
        "verification": verification,
        "results_sha256": results_sha,
        "manifest_sha256": manifest_sha,
        "verification_sha256": file_sha256(verification_path),
        "current_source_drift": drift,
        "current_source_missing": missing,
    }


def _checkpoint(results: dict[str, Any], query_count: int = 64) -> dict[str, Any]:
    checkpoints = results.get("summary", {}).get("checkpoints")
    row = checkpoints.get(str(query_count)) if type(checkpoints) is dict else None
    if type(row) is not dict:
        raise ValueError("exact results lack required q64 checkpoint")
    return row


def _label_counts(winners: Any, allowed: set[str]) -> dict[str, int]:
    if (type(winners) is not dict or len(winners) != 18
            or any(type(case) is not str or method not in allowed for case, method in winners.items())):
        raise ValueError("invalid or stale per-case backend labels")
    return dict(sorted(Counter(winners.values()).items()))


def _headroom(best_fixed_ns: Any, oracle_ns: Any, reported: Any) -> float:
    if (type(best_fixed_ns) is not int or type(oracle_ns) is not int
            or best_fixed_ns <= 0 or oracle_ns <= 0 or oracle_ns > best_fixed_ns):
        raise ValueError("invalid exact headroom totals")
    value = best_fixed_ns / oracle_ns
    if type(reported) not in (int, float) or not math.isclose(value, reported, rel_tol=1e-12):
        raise ValueError("reported exact headroom does not recompute")
    return value


def build_assessment(
    restricted: dict[str, Any],
    engine: dict[str, Any],
    historical_c36: dict[str, Any],
) -> dict[str, Any]:
    """Build the no-training decision from already validated evidence."""
    restricted_results = restricted["results"]
    engine_results = engine["results"]
    historical_results = historical_c36["results"]
    if set(restricted_results.get("methods", ())) != RESTRICTED_METHODS:
        raise ValueError("restricted labels omit R0/R1/R2 or changed exact baselines")
    if not ENGINE_METHODS.issubset(set(engine_results.get("methods", ()))):
        raise ValueError("engine labels omit bigint, words, R2, or projection")
    restricted_dataset = restricted_results.get("dataset", {})
    engine_dataset = engine_results.get("dataset", {})
    if (restricted_dataset.get("classification") != "development_exposed_c36_not_confirmation"
            or engine_dataset.get("classification") != "development_exposed_c36_not_confirmation"
            or restricted_dataset.get("sha256") != engine_dataset.get("sha256")):
        raise ValueError("backend evidence does not share the exposed C36 development cohort")

    restricted_q64 = _checkpoint(restricted_results)
    restricted_totals = restricted_q64.get("method_total_ns", {})
    if set(restricted_totals) != RESTRICTED_METHODS:
        raise ValueError("restricted q64 totals do not cover the declared methods")
    optimized_restricted = RESTRICTED_METHODS - {"restricted_r0_occurrence"}
    restricted_best = min(restricted_totals[method] for method in optimized_restricted)
    restricted_oracle = restricted_q64.get("per_case_optimized_oracle_total_ns")
    restricted_headroom = _headroom(
        restricted_best,
        restricted_oracle,
        restricted_q64.get("optimized_oracle_speedup_over_best_optimized_fixed"),
    )
    restricted_counts = _label_counts(
        restricted_q64.get("per_case_optimized_winners"), optimized_restricted
    )

    engine_q64 = _checkpoint(engine_results)
    engine_totals = engine_q64.get("method_total_ns", {})
    if not ENGINE_METHODS.issubset(set(engine_totals)):
        raise ValueError("engine q64 totals do not cover the current engine portfolio")
    best_engine_method = min(ENGINE_METHODS, key=lambda method: (engine_totals[method], method))
    best_engine_ns = engine_totals[best_engine_method]
    engine_oracle = engine_q64.get("per_case_oracle_total_ns")
    engine_headroom = _headroom(
        best_engine_ns, engine_oracle, engine_q64.get("oracle_speedup_over_best_fixed")
    )
    engine_counts = _label_counts(engine_q64.get("per_case_winners"), set(engine_totals))
    if engine_q64.get("best_fixed_method") != best_engine_method:
        raise ValueError("engine best-fixed summary mismatch")

    historical_routing = historical_results.get("summary", {}).get("routing_headroom", {})
    recognition_ns = historical_routing.get("charged_router_budget_ns_per_case")
    if type(recognition_ns) is not int or recognition_ns <= 0:
        raise ValueError("historical C36 recognition charge is unavailable")
    cases = 18
    charged_feature_ns = cases * recognition_ns
    restricted_charged_upper = restricted_best / (restricted_oracle + charged_feature_ns)
    engine_charged_upper = best_engine_ns / (engine_oracle + charged_feature_ns)

    complete_portfolio_single_run = False  # R1 and bigint were measured in different verified runs.
    current_engine_source_closed = not engine["current_source_drift"] and not engine["current_source_missing"]
    training_label_ready = complete_portfolio_single_run and current_engine_source_closed
    training_allowed = (
        training_label_ready
        and restricted_headroom >= DEVELOPMENT_HEADROOM_GATE
        and engine_headroom >= DEVELOPMENT_HEADROOM_GATE
    )
    return {
        "schema": ASSESSMENT_SCHEMA,
        "status": "complete",
        "classification": "development_only_exposed_c36_no_training",
        "neural_tasks": {
            "A_exact_answers_or_relations": "stop: exact prediction cannot replace the exact output contract and checker",
            "B_decomposition_or_cut_candidates": "stop current C5 branch: exact ANF control is faster and proposals do not avoid global-best completion",
            "C_partition_ranking": "stop: C21 completion and the tested bounds still evaluate essentially the same universe",
            "D_exact_backend_selection": "stop: optimized exposed-data oracle headroom is below the development gate",
            "E_runtime_or_cost_prediction": "reformulate only after a new exact decision surface has measurable regret to predict",
            "F_cm_representation_learning": "research-only: no current downstream task, matched ablation, or economic gate supports training",
        },
        "evidence": {
            "restricted_r2": _evidence_record(restricted),
            "current_engine_portfolio": _evidence_record(engine),
            "historical_c36": _evidence_record(historical_c36),
        },
        "labels": {
            "schema": LABEL_SCHEMA,
            "dataset_sha256": restricted_dataset["sha256"],
            "cases": cases,
            "historical_pre_r2_family_rule": {
                "status": "stale_rejected",
                "counts": {"direct_ast_restrict": 14, "compiled_truth_projection": 4},
            },
            "post_r2_word_portfolio": {
                "training_eligible": False,
                "counts": restricted_counts,
                "reason": "word-only CSE/CM arms omit the stronger bigint engine",
            },
            "r2_plus_bigint_engine_portfolio": {
                "training_eligible": False,
                "counts": engine_counts,
                "reason": "zero oracle headroom; the retained run also predates two current source hashes",
            },
            "complete_current_portfolio_in_one_run": complete_portfolio_single_run,
            "training_label_ready": training_label_ready,
        },
        "baselines_q64": {
            "restricted_same_run_ns": dict(sorted(restricted_totals.items())),
            "engine_same_run_ns": {method: engine_totals[method] for method in sorted(ENGINE_METHODS)},
            "cross_run_totals_must_not_be_combined_into_labels": True,
        },
        "economics": {
            "development_headroom_gate": DEVELOPMENT_HEADROOM_GATE,
            "prospective_charged_gate": PROSPECTIVE_CHARGED_GATE,
            "post_r2_word_portfolio": {
                "best_fixed_ns": restricted_best,
                "oracle_ns": restricted_oracle,
                "gross_headroom_ns": restricted_best - restricted_oracle,
                "gross_headroom_speedup": restricted_headroom,
                "optimistic_feature_only_charged_speedup": restricted_charged_upper,
            },
            "r2_plus_bigint_engine_portfolio": {
                "best_fixed_method": best_engine_method,
                "best_fixed_ns": best_engine_ns,
                "oracle_ns": engine_oracle,
                "gross_headroom_ns": best_engine_ns - engine_oracle,
                "gross_headroom_speedup": engine_headroom,
                "optimistic_feature_only_charged_speedup": engine_charged_upper,
            },
            "charged_boundary": {
                "cases": cases,
                "historical_feature_or_recognition_ns_per_case": recognition_ns,
                "feature_or_recognition_ns_total": charged_feature_ns,
                "model_inference_ns_assumed": 0,
                "verification_ns_assumed": 0,
                "fallback_ns_assumed": 0,
                "interpretation": "optimistic upper bound; every omitted nonnegative cost can only reduce speedup",
            },
        },
        "decision": {
            "training_allowed": training_allowed,
            "training_performed": False,
            "advice_enabled": False,
            "abstention": "all cases",
            "exact_fallback": "unchanged exact path",
            "production_write": False,
            "production_promotion": False,
            "prospective_data_consumed": False,
            "reason": "the current bigint portfolio has zero exposed-development oracle headroom",
        },
    }


def _evidence_record(loaded: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": loaded["results"].get("run_id"),
        "path": str(loaded["run"].relative_to(ROOT)).replace("\\", "/"),
        "results_sha256": loaded["results_sha256"],
        "manifest_sha256": loaded["manifest_sha256"],
        "independent_verification_sha256": loaded["verification_sha256"],
        "current_source_drift": loaded["current_source_drift"],
        "current_source_missing": loaded["current_source_missing"],
    }


def advice_decision(assessment: dict[str, Any], suggested_method: str | None, advice_enabled: bool) -> dict[str, Any]:
    """Research contract showing fail-closed abstention; it is not a router."""
    decision = assessment.get("decision", {})
    if assessment.get("schema") != ASSESSMENT_SCHEMA or decision.get("training_allowed") is not True:
        return {"accepted": False, "selected": None, "fallback": "unchanged exact path",
                "reason": "advice_disabled_or_training_gate_failed"}
    if not advice_enabled or type(suggested_method) is not str:
        return {"accepted": False, "selected": None, "fallback": "unchanged exact path",
                "reason": "advice_disabled_or_abstained"}
    return {"accepted": True, "selected": suggested_method, "fallback": "unchanged exact path",
            "reason": "development_advice"}


def load_default_assessment_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    restricted = load_verified_run(
        ROOT / "docs/recognition/runs/restricted-evaluator-development-20260902-003",
        results_schema="crse-restricted-evaluator-development/v1",
        manifest_schema="crse-restricted-evaluator-manifest/v1",
        verification_schema="crse-restricted-evaluator-independent-verification/v1",
    )
    engine = load_verified_run(
        ROOT / "docs/recognition/runs/multi-query-batch-development-20260902-001",
        results_schema="crse-multi-query-batch-development/v1",
        manifest_schema="crse-restricted-evaluator-manifest/v1",
        verification_schema="crse-multi-query-batch-independent-verification/v1",
    )
    historical = load_verified_run(
        ROOT / "docs/recognition/runs/c36-wide-repeated-windows-20260901-003",
        results_schema="crse-c36-wide-natural-repeated-query-experiment/v1",
        manifest_schema="crse-c36-run-manifest/v1",
        verification_schema="crse-c36-independent-verification/v1",
    )
    return restricted, engine, historical


def render_report(assessment: dict[str, Any]) -> str:
    restricted = assessment["economics"]["post_r2_word_portfolio"]
    engine = assessment["economics"]["r2_plus_bigint_engine_portfolio"]
    return "\n".join([
        "# Neural architecture reassessment development artifact",
        "",
        "Status: **training stopped by the exact-economics gate**",
        "",
        "This artifact consumes exposed C36 development evidence only. It does not train a model,",
        "change production routing, consume prospective data, or promote a backend.",
        "",
        "## Recomputed economics",
        "",
        f"- Post-R2 word-portfolio oracle headroom: `{restricted['gross_headroom_speedup']:.9f}x`.",
        f"- Current bigint-engine oracle headroom: `{engine['gross_headroom_speedup']:.9f}x`.",
        f"- Current best fixed development arm: `{engine['best_fixed_method']}`.",
        f"- Optimistic feature-only charged speedup: `{engine['optimistic_feature_only_charged_speedup']:.9f}x`.",
        "- Model inference, exact verification, and fallback were set to zero for that optimistic bound.",
        "",
        "## Decision",
        "",
        "Pre-R2 family labels and post-R2 word-only labels are rejected for training. The verified",
        "bigint comparison labels all 18 exposed cases `cse_bigint`, leaving no decision for a",
        "selector to learn. Existing C5 decomposition models remain frozen negative research",
        "artifacts; no architecture or hyperparameter update is scientifically justified.",
        "",
    ])


def create_development_artifact(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    restricted, engine, historical = load_default_assessment_inputs()
    assessment = build_assessment(restricted, engine, historical)
    labels = {"schema": LABEL_SCHEMA, **assessment["labels"]}
    environment = {
        "schema": "crse-neural-reassessment-environment/v1",
        "python": sys.version,
        "interpreter": sys.executable,
        "platform": platform.platform(),
        "torch_required": False,
        "training_performed": False,
    }
    _write_json(output / "assessment.json", assessment)
    _write_json(output / "labels.json", labels)
    _write_json(output / "environment.json", environment)
    (output / "report.md").write_text(render_report(assessment), encoding="utf-8", newline="\n")
    sources = [
        Path(__file__),
        ROOT / "scripts/cm_neural_architecture_reassessment.py",
        ROOT / "scripts/crse_neural_architecture_reassessment_verify.py",
    ]
    artifacts = ["assessment.json", "labels.json", "environment.json", "report.md"]
    manifest = {
        "schema": ARTIFACT_SCHEMA,
        "artifacts": {name: file_sha256(output / name) for name in artifacts},
        "sources": {str(path.relative_to(ROOT)).replace("\\", "/"): file_sha256(path) for path in sources},
        "input_manifests": {
            name: record["manifest_sha256"] for name, record in assessment["evidence"].items()
        },
    }
    _write_json(output / "manifest.json", manifest)
    return assessment


def verify_development_artifact(run: Path) -> dict[str, Any]:
    manifest = read_json(run / "manifest.json")
    if manifest.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError("invalid neural reassessment manifest schema")
    for group, base in ((manifest.get("artifacts"), run), (manifest.get("sources"), ROOT)):
        if type(group) is not dict or not group:
            raise ValueError("neural reassessment manifest group is empty")
        for name, expected in group.items():
            path = base / name
            if not path.is_file() or file_sha256(path) != _require_hash(expected, name):
                raise ValueError(f"neural reassessment hash mismatch: {name}")
    retained = read_json(run / "assessment.json")
    restricted, engine, historical = load_default_assessment_inputs()
    reproduced = build_assessment(restricted, engine, historical)
    if retained != reproduced or read_json(run / "labels.json") != {"schema": LABEL_SCHEMA, **reproduced["labels"]}:
        raise ValueError("neural reassessment replay mismatch")
    if (retained["decision"]["training_performed"] is not False
            or retained["decision"]["training_allowed"] is not False):
        raise ValueError("neural reassessment did not fail closed")
    return {
        "schema": VERIFICATION_SCHEMA,
        "status": "verified",
        "manifest_sha256": file_sha256(run / "manifest.json"),
        "assessment_sha256": file_sha256(run / "assessment.json"),
        "evidence_runs_replayed": 3,
        "backend_labels_replayed": 36,
        "training_performed": False,
        "prospective_data_consumed": False,
        "production_write": False,
        "production_promotion": False,
    }
