from __future__ import annotations

import math
import re
from typing import Any, Mapping


SCHEMA_VERSION = "cm-workload-trace/v1"
CONTENT_MODE = "metrics"

EVENT_TYPES = frozenset(
    {
        "session_start",
        "session_end",
        "prepare_request",
        "prepare_result",
        "evaluation_request",
        "evaluation_result",
        "cache_lookup",
        "cache_insert",
        "cache_evict",
        "cache_reject",
        "family_version",
        "context_transition",
        "context_query",
        "process_restart",
        "failure",
        "refusal",
        "timeout",
        "trace_drop",
    }
)

CORE_FIELDS = frozenset(
    {
        "schema_version",
        "content_mode",
        "session_id",
        "sequence",
        "event_id",
        "event_type",
        "utc_ns",
        "monotonic_ns",
        "payload",
    }
)

STRING_FIELDS = frozenset(
    {
        "workload_id",
        "family_id",
        "context_id",
        "expression_digest",
        "compiler_identity",
        "options_digest",
        "cache_key_digest",
        "output_kind",
        "artifact_kind",
        "backend",
        "cache_state",
        "cache_action",
        "policy",
        "phase",
        "status",
        "status_reason",
        "timing_boundary",
    }
)

INTEGER_FIELDS = frozenset(
    {
        "n_vars",
        "semantic_support",
        "remaining_support",
        "structural_nodes",
        "tree_nodes",
        "instruction_count",
        "primitive_ops",
        "q",
        "trial",
        "variant_index",
        "family_size",
        "context_index",
        "context_count",
        "fixed_var_count",
        "artifact_bytes",
        "retained_bytes",
        "serialized_bytes",
        "output_bytes",
        "temporary_budget_bytes",
        "output_budget_bytes",
        "cache_budget_bytes",
        "cache_hits",
        "cache_misses",
        "cache_evictions",
        "event_count",
        "sample_every",
    }
)

FLOAT_FIELDS = frozenset(
    {
        "prepare_s",
        "lookup_s",
        "kernel_s",
        "conversion_s",
        "serialization_s",
        "total_s",
        "sharing_factor",
        "fixed_var_fraction",
        "context_overlap",
        "context_value_similarity",
    }
)

BOOLEAN_FIELDS = frozenset(
    {
        "cold",
        "cache_hit",
        "exact_ok",
        "refused",
        "timed_out",
    }
)

PAYLOAD_FIELDS = STRING_FIELDS | INTEGER_FIELDS | FLOAT_FIELDS | BOOLEAN_FIELDS
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z0-9_.:@+-]{1,256}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{16,128}$")
_ID_FIELDS = frozenset(
    {"workload_id", "family_id", "context_id", "expression_digest", "options_digest", "cache_key_digest"}
)
_FORBIDDEN_KEY_PARTS = (
    "expr_text",
    "expression_text",
    "variable_name",
    "source_path",
    "file_path",
    "environment",
    "credential",
    "password",
    "secret",
    "token",
)


class TraceValidationError(ValueError):
    pass


def _fail(message: str) -> None:
    raise TraceValidationError(message)


def _validate_identifier(name: str, value: str) -> None:
    if name in _ID_FIELDS:
        if not _DIGEST_RE.fullmatch(value):
            _fail(f"payload {name!r} must be a lowercase hexadecimal digest")
        return
    if not _IDENTIFIER_RE.fullmatch(value):
        _fail(f"payload {name!r} contains unsupported characters or is too long")


def _validate_payload(payload: Mapping[str, Any]) -> None:
    unknown = set(payload) - PAYLOAD_FIELDS
    if unknown:
        _fail(f"unknown payload fields: {sorted(unknown)!r}")
    for key, value in payload.items():
        lower = key.lower()
        if any(part in lower for part in _FORBIDDEN_KEY_PARTS):
            _fail(f"forbidden metrics payload field: {key!r}")
        if value is None:
            continue
        if key in STRING_FIELDS:
            if not isinstance(value, str):
                _fail(f"payload {key!r} must be str or null")
            _validate_identifier(key, value)
        elif key in BOOLEAN_FIELDS:
            if not isinstance(value, bool):
                _fail(f"payload {key!r} must be bool or null")
        elif key in INTEGER_FIELDS:
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                _fail(f"payload {key!r} must be a nonnegative int or null")
        elif key in FLOAT_FIELDS:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                _fail(f"payload {key!r} must be finite numeric or null")
            if not math.isfinite(float(value)) or float(value) < 0.0:
                _fail(f"payload {key!r} must be finite and nonnegative")


def validate_trace_event(event: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        _fail("trace event must be an object")
    missing = CORE_FIELDS - set(event)
    unknown = set(event) - CORE_FIELDS
    if missing:
        _fail(f"missing core fields: {sorted(missing)!r}")
    if unknown:
        _fail(f"unknown core fields: {sorted(unknown)!r}")
    if event["schema_version"] != SCHEMA_VERSION:
        _fail(f"unsupported schema_version: {event['schema_version']!r}")
    if event["content_mode"] != CONTENT_MODE:
        _fail(f"unsupported content_mode: {event['content_mode']!r}")
    session_id = event["session_id"]
    if not isinstance(session_id, str) or not _DIGEST_RE.fullmatch(session_id):
        _fail("session_id must be a lowercase hexadecimal digest")
    sequence = event["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        _fail("sequence must be a nonnegative int")
    expected_event_id = f"{session_id}:{sequence}"
    if event["event_id"] != expected_event_id:
        _fail("event_id does not match session_id and sequence")
    event_type = event["event_type"]
    if event_type not in EVENT_TYPES:
        _fail(f"unsupported event_type: {event_type!r}")
    for field in ("utc_ns", "monotonic_ns"):
        value = event[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _fail(f"{field} must be a nonnegative int")
    payload = event["payload"]
    if not isinstance(payload, Mapping):
        _fail("payload must be an object")
    _validate_payload(payload)
    return dict(event)
