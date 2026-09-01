"""Opt-in exact source-ANF/CM portfolio boundary derived from C21 evidence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import time
from typing import Any

from cm_expr_serde import expr_from_json

from .gf2_decomposition import (
    ExactGF2Analysis,
    ExactGF2Artifact,
    analyze_exact_gf2,
    analyze_screened_exact_gf2,
    truth_sha256,
)
from .gf2_task_dispatcher import EXHAUSTIVE, GF2DecompositionTask, canonical_sha256
from .portfolio import reference_bits
from .source_anf_hybrid import packed_truth_bits, source_anf_packed

SOURCE_PACKED_SCREENED = "source_packed_anf_screened"
POLICY_SCHEMA = "crse-c22-gf2-source-portfolio-policy/v1"
EXECUTION_SCHEMA = "crse-c22-gf2-source-portfolio-execution/v1"
SHA256 = re.compile(r"[0-9a-f]{64}")


def _policy_body(c21_manifest_sha256: str, c21_dataset_sha256: str) -> dict[str, Any]:
    return {
        "schema": POLICY_SCHEMA,
        "status": "frozen",
        "objective": "best_exact_gf2_artifact",
        "selected_arm": SOURCE_PACKED_SCREENED,
        "advice_off_arm": EXHAUSTIVE,
        "exact_fallback_arm": EXHAUSTIVE,
        "max_partitions": 64,
        "materialize_budget": 4,
        "evidence_milestone": "C21/F2",
        "c21_manifest_sha256": c21_manifest_sha256,
        "c21_dataset_sha256": c21_dataset_sha256,
        "training_use": False,
        "fresh_confirmation": False,
        "production_promotion": False,
    }


def freeze_source_portfolio_policy(*, c21_manifest_sha256: str, c21_dataset_sha256: str) -> dict[str, Any]:
    if not all(type(value) is str and SHA256.fullmatch(value) for value in (
            c21_manifest_sha256, c21_dataset_sha256)):
        raise ValueError("invalid C22 evidence fingerprint")
    body = _policy_body(c21_manifest_sha256, c21_dataset_sha256)
    return {**body, "policy_sha256": canonical_sha256(body)}


def validate_source_portfolio_policy(policy: dict[str, Any]) -> None:
    expected_keys = set(_policy_body("0" * 64, "0" * 64)) | {"policy_sha256"}
    if type(policy) is not dict or set(policy) != expected_keys:
        raise ValueError("invalid C22 policy fields")
    if not all(type(policy.get(field)) is str and SHA256.fullmatch(policy[field]) for field in (
            "c21_manifest_sha256", "c21_dataset_sha256")):
        raise ValueError("invalid C22 policy evidence fingerprint")
    body = _policy_body(policy["c21_manifest_sha256"], policy["c21_dataset_sha256"])
    if policy != {**body, "policy_sha256": canonical_sha256(body)}:
        raise ValueError("invalid frozen C22 policy")


def save_source_portfolio_policy(policy: dict[str, Any], path: Path) -> None:
    validate_source_portfolio_policy(policy)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(policy, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def load_source_portfolio_policy(path: Path, *, max_bytes: int = 64_000) -> dict[str, Any]:
    raw = path.read_bytes()
    if not raw or len(raw) > max_bytes:
        raise ValueError("C22 policy exceeds size bound")

    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("duplicate C22 policy key")
            value[key] = item
        return value

    policy = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _value: (
        _ for _ in ()).throw(ValueError("nonfinite C22 policy value")))
    validate_source_portfolio_policy(policy)
    return policy


@dataclass(frozen=True)
class SourcePortfolioExecution:
    n_vars: int
    source_sha256: str
    policy_sha256: str
    requested_arm: str
    selected_arm: str
    decision_reason: str
    advice_enabled: bool
    fallback_used: bool
    fallback_reason: str | None
    best_artifact: dict[str, Any] | None
    exact_check_passed: bool
    partitions_tested: int
    descriptors_screened: int
    artifacts_materialized: int
    representation_ns: int
    analysis_ns: int
    exact_check_ns: int
    shadow_ns: int
    total_ns: int
    shadow_arm: str | None
    shadow_best_identity_match: bool | None
    schema: str = EXECUTION_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _best(analysis: ExactGF2Analysis) -> dict[str, Any] | None:
    return analysis.best.to_dict() if analysis.best else None


class CompiledSourcePortfolio:
    def __init__(self, policy: dict[str, Any], task: GF2DecompositionTask, *,
                 advice_enabled: bool, shadow: bool):
        validate_source_portfolio_policy(policy)
        task.validate()
        if type(advice_enabled) is not bool or type(shadow) is not bool:
            raise ValueError("invalid C22 advice or shadow switch")
        self.policy = json.loads(json.dumps(policy, allow_nan=False))
        self.task = task
        self.advice_enabled = advice_enabled
        self.shadow = shadow

    def _exhaustive(self, document: dict[str, Any]):
        started = time.perf_counter_ns()
        expression = expr_from_json(document)
        bits = reference_bits(expression, self.task.n_vars)
        representation_ns = max(1, time.perf_counter_ns() - started)
        started = time.perf_counter_ns()
        analysis = analyze_exact_gf2(
            bits, self.task.n_vars, max_partitions=self.task.max_partitions)
        return bits, analysis, representation_ns, max(1, time.perf_counter_ns() - started)

    def _source_packed(self, document: dict[str, Any]):
        started = time.perf_counter_ns()
        polynomial, _stats = source_anf_packed(document, self.task.n_vars)
        bits = packed_truth_bits(polynomial, self.task.n_vars)
        representation_ns = max(1, time.perf_counter_ns() - started)
        started = time.perf_counter_ns()
        analysis = analyze_screened_exact_gf2(
            bits, self.task.n_vars, max_partitions=self.task.max_partitions,
            materialize_budget=self.task.materialize_budget)
        return bits, analysis, representation_ns, max(1, time.perf_counter_ns() - started)

    def execute(self, document: dict[str, Any]) -> SourcePortfolioExecution:
        requested = SOURCE_PACKED_SCREENED if self.advice_enabled else EXHAUSTIVE
        reason = "c21_best_fixed_source_path" if self.advice_enabled else "advice_globally_disabled"
        fallback_used, fallback_reason = False, None
        try:
            if requested == SOURCE_PACKED_SCREENED:
                bits, analysis, representation_ns, analysis_ns = self._source_packed(document)
                selected = SOURCE_PACKED_SCREENED
            else:
                bits, analysis, representation_ns, analysis_ns = self._exhaustive(document)
                selected = EXHAUSTIVE
        except ValueError as exc:
            if requested != SOURCE_PACKED_SCREENED:
                raise
            bits, analysis, representation_ns, analysis_ns = self._exhaustive(document)
            selected, reason = EXHAUSTIVE, "source_packed_refused_exact_fallback"
            fallback_used, fallback_reason = True, type(exc).__name__

        started = time.perf_counter_ns()
        reference = reference_bits(expr_from_json(document), self.task.n_vars)
        best = _best(analysis)
        exact = (
            bits == reference
            and analysis.source_sha256 == truth_sha256(reference, self.task.n_vars)
            and all(candidate.reconstruct() == reference for candidate in analysis.candidates)
        )
        if best is not None:
            exact = exact and ExactGF2Artifact.from_dict(best).reconstruct() == reference
        exact_check_ns = max(1, time.perf_counter_ns() - started)
        if not exact:
            raise RuntimeError("C22 selected arm failed independent exact replay")

        shadow_ns, shadow_arm, shadow_match = 0, None, None
        if self.shadow:
            started = time.perf_counter_ns()
            if selected == SOURCE_PACKED_SCREENED:
                shadow_bits, shadow_analysis, _representation, _analysis = self._exhaustive(document)
                shadow_arm = EXHAUSTIVE
            else:
                shadow_bits, shadow_analysis, _representation, _analysis = self._source_packed(document)
                shadow_arm = SOURCE_PACKED_SCREENED
            shadow_match = shadow_bits == reference and _best(shadow_analysis) == best and all(
                candidate.reconstruct() == reference for candidate in shadow_analysis.candidates)
            shadow_ns = max(1, time.perf_counter_ns() - started)
            if not shadow_match:
                raise RuntimeError("C22 shadow arm changed the exact best artifact")
        total_ns = representation_ns + analysis_ns + exact_check_ns + shadow_ns
        return SourcePortfolioExecution(
            n_vars=self.task.n_vars,
            source_sha256=truth_sha256(reference, self.task.n_vars),
            policy_sha256=self.policy["policy_sha256"],
            requested_arm=requested,
            selected_arm=selected,
            decision_reason=reason,
            advice_enabled=self.advice_enabled,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            best_artifact=best,
            exact_check_passed=True,
            partitions_tested=analysis.partitions_tested,
            descriptors_screened=analysis.descriptors_screened,
            artifacts_materialized=analysis.artifacts_materialized,
            representation_ns=representation_ns,
            analysis_ns=analysis_ns,
            exact_check_ns=exact_check_ns,
            shadow_ns=shadow_ns,
            total_ns=total_ns,
            shadow_arm=shadow_arm,
            shadow_best_identity_match=shadow_match,
        )


def compile_source_portfolio(policy: dict[str, Any], task: GF2DecompositionTask, *,
                             advice_enabled: bool = True, shadow: bool = False) -> CompiledSourcePortfolio:
    return CompiledSourcePortfolio(
        policy, task, advice_enabled=advice_enabled, shadow=shadow)


def verify_source_portfolio_execution(document: dict[str, Any], expression_document: dict[str, Any],
                                      *, policy_sha256: str | None = None) -> None:
    expected = {field.name for field in SourcePortfolioExecution.__dataclass_fields__.values()}
    if type(document) is not dict or set(document) != expected:
        raise ValueError("invalid C22 execution fields")
    n_vars = document.get("n_vars")
    bits = reference_bits(expr_from_json(expression_document), n_vars)
    if (
        document.get("schema") != EXECUTION_SCHEMA
        or document.get("requested_arm") not in {SOURCE_PACKED_SCREENED, EXHAUSTIVE}
        or document.get("selected_arm") not in {SOURCE_PACKED_SCREENED, EXHAUSTIVE}
        or document.get("source_sha256") != truth_sha256(bits, n_vars)
        or policy_sha256 is not None and document.get("policy_sha256") != policy_sha256
        or document.get("exact_check_passed") is not True
        or document.get("shadow_best_identity_match") is False
        or any(type(document.get(field)) is not int or document[field] < 0 for field in (
            "representation_ns", "analysis_ns", "exact_check_ns", "shadow_ns", "total_ns",
            "partitions_tested", "descriptors_screened", "artifacts_materialized"))
        or document["total_ns"] != sum(document[field] for field in (
            "representation_ns", "analysis_ns", "exact_check_ns", "shadow_ns"))
    ):
        raise ValueError("invalid C22 exact execution")
    artifact = document.get("best_artifact")
    if artifact is not None and ExactGF2Artifact.from_dict(artifact).reconstruct() != bits:
        raise ValueError("C22 execution artifact failed reconstruction")

