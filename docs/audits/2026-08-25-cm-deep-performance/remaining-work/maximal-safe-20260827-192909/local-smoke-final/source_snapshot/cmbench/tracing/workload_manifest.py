"""Strict owner-declared intake contract for real CM workload tracing."""

from __future__ import annotations

import math
from typing import Any, Mapping


MANIFEST_SCHEMA_VERSION = "cm-real-workload/v1"
MANIFEST_STATUSES = frozenset({"template", "declared"})
ARTIFACT_KINDS = frozenset(
    {
        "packed_complete",
        "remaining_packed",
        "symbolic",
        "single_assignment",
        "equivalence",
        "other",
    }
)
PROCESS_LIFETIMES = frozenset(
    {"single_call", "short_lived", "long_lived", "mixed", "unknown"}
)

TOP_LEVEL_FIELDS = frozenset(
    {"schema_version", "manifest_status", "workload", "lifecycle", "approvals", "budgets", "trace"}
)
WORKLOAD_FIELDS = frozenset(
    {
        "label",
        "owner_role",
        "application",
        "repository_or_system",
        "caller_boundary",
        "requested_artifact",
        "output_order_contract",
        "expected_calls_per_expression",
    }
)
LIFECYCLE_FIELDS = frozenset(
    {"process_lifetime", "cold_start_relevant", "phase_changes_expected"}
)
APPROVAL_FIELDS = frozenset(
    {"metrics_capture", "replayable_expressions", "replayable_contexts", "external_upload"}
)
BUDGET_FIELDS = frozenset(
    {"max_output_bytes", "max_temporary_bytes", "max_cache_bytes", "p95_latency_s"}
)
TRACE_FIELDS = frozenset(
    {"sample_every", "max_bytes", "max_files", "planned_duration_or_calls"}
)
PLACEHOLDER = "REPLACE_ME"


class WorkloadManifestError(ValueError):
    pass


def _fail(message: str) -> None:
    raise WorkloadManifestError(message)


def _object(value: Any, name: str, expected: frozenset[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(f"{name} must be an object")
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        _fail(f"{name} missing fields: {sorted(missing)!r}")
    if unknown:
        _fail(f"{name} unknown fields: {sorted(unknown)!r}")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        _fail(f"{name} must be a nonempty string of at most 512 characters")
    return value


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{name} must be bool")
    return value


def _optional_nonnegative_int(value: Any, name: str, *, minimum: int = 0) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail(f"{name} must be null or an integer >= {minimum}")
    return value


def _optional_nonnegative_number(value: Any, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{name} must be null or finite and nonnegative")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        _fail(f"{name} must be null or finite and nonnegative")
    return numeric


def validate_workload_manifest(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a manifest and report whether owner declarations unblock capture."""
    manifest = _object(raw, "manifest", TOP_LEVEL_FIELDS)
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        _fail(f"unsupported schema_version: {manifest['schema_version']!r}")
    status = manifest["manifest_status"]
    if status not in MANIFEST_STATUSES:
        _fail(f"manifest_status must be one of {sorted(MANIFEST_STATUSES)!r}")

    workload = _object(manifest["workload"], "workload", WORKLOAD_FIELDS)
    for field in (
        "label",
        "owner_role",
        "application",
        "repository_or_system",
        "caller_boundary",
        "output_order_contract",
    ):
        _string(workload[field], f"workload.{field}")
    if workload["requested_artifact"] not in ARTIFACT_KINDS:
        _fail(f"workload.requested_artifact must be one of {sorted(ARTIFACT_KINDS)!r}")
    calls = _optional_nonnegative_int(
        workload["expected_calls_per_expression"],
        "workload.expected_calls_per_expression",
        minimum=1,
    )

    lifecycle = _object(manifest["lifecycle"], "lifecycle", LIFECYCLE_FIELDS)
    if lifecycle["process_lifetime"] not in PROCESS_LIFETIMES:
        _fail(f"lifecycle.process_lifetime must be one of {sorted(PROCESS_LIFETIMES)!r}")
    for field in ("cold_start_relevant", "phase_changes_expected"):
        _boolean(lifecycle[field], f"lifecycle.{field}")

    approvals = _object(manifest["approvals"], "approvals", APPROVAL_FIELDS)
    for field in sorted(APPROVAL_FIELDS):
        _boolean(approvals[field], f"approvals.{field}")

    budgets = _object(manifest["budgets"], "budgets", BUDGET_FIELDS)
    normalized_budgets = {
        field: _optional_nonnegative_int(budgets[field], f"budgets.{field}")
        for field in ("max_output_bytes", "max_temporary_bytes", "max_cache_bytes")
    }
    _optional_nonnegative_number(budgets["p95_latency_s"], "budgets.p95_latency_s")

    trace = _object(manifest["trace"], "trace", TRACE_FIELDS)
    sample_every = _optional_nonnegative_int(trace["sample_every"], "trace.sample_every", minimum=1)
    max_bytes = _optional_nonnegative_int(trace["max_bytes"], "trace.max_bytes", minimum=1024)
    max_files = _optional_nonnegative_int(trace["max_files"], "trace.max_files", minimum=1)
    duration = _string(trace["planned_duration_or_calls"], "trace.planned_duration_or_calls")
    if sample_every != 16:
        _fail("trace.sample_every must be 16 for the initial bounded capture")
    if max_bytes is None or max_files is None:
        _fail("trace.max_bytes and trace.max_files must be explicit bounded integers")

    blockers: list[str] = []
    if status != "declared":
        blockers.append("manifest_status_is_template")
    placeholder_fields = [
        f"workload.{field}"
        for field in (
            "label",
            "owner_role",
            "application",
            "repository_or_system",
            "caller_boundary",
            "output_order_contract",
        )
        if PLACEHOLDER in str(workload[field])
    ]
    if PLACEHOLDER in duration:
        placeholder_fields.append("trace.planned_duration_or_calls")
    blockers.extend(f"placeholder:{field}" for field in placeholder_fields)
    if calls is None:
        blockers.append("missing:workload.expected_calls_per_expression")
    if not approvals["metrics_capture"]:
        blockers.append("approval_required:metrics_capture")
    for field, value in normalized_budgets.items():
        if value is None:
            blockers.append(f"missing:budgets.{field}")

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "validation_status": "pass",
        "manifest_status": status,
        "ready_for_metrics_capture": not blockers,
        "ready_for_expression_replay": not blockers and approvals["replayable_expressions"],
        "ready_for_context_replay": not blockers and approvals["replayable_contexts"],
        "external_upload_approved": approvals["external_upload"],
        "blockers": blockers,
    }
