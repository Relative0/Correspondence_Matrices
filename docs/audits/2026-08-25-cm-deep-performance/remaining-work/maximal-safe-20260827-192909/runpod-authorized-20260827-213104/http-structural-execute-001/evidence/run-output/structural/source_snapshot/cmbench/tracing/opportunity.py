from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median
from typing import Any, Mapping, Sequence

from .replay import load_trace_events, summarize_trace_files


SCREEN_VERSION = "cm-workload-opportunity/v1"
EVIDENCE_CLASSES = frozenset({"real", "synthetic", "unknown"})
CONTEXT_STREAM_KINDS = frozenset({"natural", "synthetic", "unknown"})

DEFAULT_THRESHOLDS: dict[str, int] = {
    "cache_prepare_requests": 10_000,
    "cache_process_lifetimes": 2,
    "family_transitions": 200,
    "family_ids": 20,
    "context_transitions": 500,
    "context_streams": 5,
    "selector_independent_formulas": 50,
    "selector_eligible_calls": 500,
}


def _resolved_thresholds(overrides: Mapping[str, int] | None) -> dict[str, int]:
    thresholds = dict(DEFAULT_THRESHOLDS)
    if overrides:
        unknown = set(overrides) - set(thresholds)
        if unknown:
            raise ValueError(f"unknown opportunity thresholds: {sorted(unknown)!r}")
        thresholds.update(overrides)
    for key, value in thresholds.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"opportunity threshold {key!r} must be a positive integer")
    return thresholds


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = event.get("payload")
    return payload if isinstance(payload, Mapping) else {}


def _logical_call_key(event: Mapping[str, Any]) -> tuple[Any, ...]:
    payload = _payload(event)
    workload_id = payload.get("workload_id")
    if workload_id is None:
        workload_id = event.get("event_id")
    return (
        event.get("session_id"),
        workload_id,
        payload.get("expression_digest"),
        payload.get("trial"),
        payload.get("context_id"),
    )


def _field_coverage(events: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> dict[str, Any]:
    total = len(events)
    populated = {
        field: sum(_payload(event).get(field) is not None for event in events)
        for field in fields
    }
    return {
        "event_count": total,
        "populated": populated,
        "complete": bool(total) and all(count == total for count in populated.values()),
    }


def screen_trace_events(
    events: Sequence[Mapping[str, Any]],
    *,
    workload_label: str,
    evidence_class: str,
    context_stream_kind: str = "unknown",
    complete_workload: bool = False,
    complete_family_population: bool = False,
    threshold_overrides: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    if not workload_label.strip():
        raise ValueError("workload_label must not be empty")
    if evidence_class not in EVIDENCE_CLASSES:
        raise ValueError(f"unsupported evidence_class: {evidence_class!r}")
    if context_stream_kind not in CONTEXT_STREAM_KINDS:
        raise ValueError(f"unsupported context_stream_kind: {context_stream_kind!r}")

    thresholds = _resolved_thresholds(threshold_overrides)
    event_counts = Counter(str(event.get("event_type")) for event in events)
    sessions = {event.get("session_id") for event in events if event.get("session_id") is not None}
    sample_every_values = sorted(
        {
            int(value)
            for event in events
            for value in [_payload(event).get("sample_every")]
            if isinstance(value, int) and not isinstance(value, bool) and value >= 1
        }
    )
    drop_count = int(event_counts.get("trace_drop", 0))
    complete_capture = sample_every_values == [1] and drop_count == 0
    process_lifetimes = max(len(sessions), int(event_counts.get("process_restart", 0)))

    phase_values = sorted(
        {
            str(value)
            for event in events
            for value in [_payload(event).get("phase")]
            if value is not None
        }
    )
    phase_change_observed = len(phase_values) >= 2

    prepare_requests = [event for event in events if event.get("event_type") == "prepare_request"]
    cache_accesses = [
        event
        for event in events
        if event.get("event_type") in {"prepare_request", "cache_lookup"}
    ]
    cache_coverage = _field_coverage(
        cache_accesses,
        ("cache_key_digest", "artifact_bytes", "prepare_s"),
    )

    family_by_id: dict[str, int] = defaultdict(int)
    for event in events:
        if event.get("event_type") != "family_version":
            continue
        family_id = _payload(event).get("family_id")
        if family_id is not None:
            family_by_id[str(family_id)] += 1
    family_transitions = sum(max(0, count - 1) for count in family_by_id.values())

    context_by_stream: dict[tuple[Any, Any], int] = defaultdict(int)
    for event in events:
        if event.get("event_type") != "context_transition":
            continue
        payload = _payload(event)
        context_by_stream[(event.get("session_id"), payload.get("workload_id"))] += 1
    context_transitions = sum(max(0, count - 1) for count in context_by_stream.values())

    eligible_formula_digests_13_15: set[str] = set()
    eligible_formula_digests_13_16: set[str] = set()
    eligible_calls_13_15: set[tuple[Any, ...]] = set()
    eligible_calls_13_16: set[tuple[Any, ...]] = set()
    for event in events:
        payload = _payload(event)
        support = payload.get("semantic_support")
        expression_digest = payload.get("expression_digest")
        if not isinstance(support, int) or isinstance(support, bool):
            continue
        if expression_digest is not None and 13 <= support <= 15:
            eligible_formula_digests_13_15.add(str(expression_digest))
        if expression_digest is not None and 13 <= support <= 16:
            eligible_formula_digests_13_16.add(str(expression_digest))
        if event.get("event_type") not in {"evaluation_request", "evaluation_result"}:
            continue
        if 13 <= support <= 15:
            eligible_calls_13_15.add(_logical_call_key(event))
        if 13 <= support <= 16:
            eligible_calls_13_16.add(_logical_call_key(event))

    q_values: list[int] = []
    kernel_fractions: list[float] = []
    for event in events:
        payload = _payload(event)
        q = payload.get("q")
        if isinstance(q, int) and not isinstance(q, bool):
            q_values.append(q)
        kernel_s = payload.get("kernel_s")
        total_s = payload.get("total_s")
        if isinstance(kernel_s, (int, float)) and isinstance(total_s, (int, float)) and total_s > 0:
            kernel_fractions.append(float(kernel_s) / float(total_s))

    cache_volume_adequate = (
        len(prepare_requests) >= thresholds["cache_prepare_requests"] or complete_workload
    ) and process_lifetimes >= thresholds["cache_process_lifetimes"] and phase_change_observed
    cache_exact_replay_ready = (
        evidence_class == "real"
        and cache_volume_adequate
        and complete_capture
        and cache_coverage["complete"]
    )

    family_volume_adequate = (
        (
            family_transitions >= thresholds["family_transitions"]
            and len(family_by_id) >= thresholds["family_ids"]
        )
        or (complete_family_population and bool(family_by_id))
    )
    family_followup_ready = evidence_class == "real" and family_volume_adequate

    context_volume_adequate = (
        context_transitions >= thresholds["context_transitions"]
        and len(context_by_stream) >= thresholds["context_streams"]
    )
    context_followup_ready = (
        evidence_class == "real"
        and context_stream_kind == "natural"
        and context_volume_adequate
    )

    selector_volume_adequate = (
        len(eligible_formula_digests_13_15) >= thresholds["selector_independent_formulas"]
        and len(eligible_calls_13_15) >= thresholds["selector_eligible_calls"]
    )
    selector_traffic_ready = evidence_class == "real" and selector_volume_adequate

    if evidence_class != "real":
        recommended_next_step = "collect_named_real_metrics_trace"
    elif drop_count:
        recommended_next_step = "repair_trace_loss_before_screening"
    elif cache_exact_replay_ready:
        recommended_next_step = "preregister_offline_cache_policy_replay"
    elif family_followup_ready or context_followup_ready or selector_traffic_ready:
        recommended_next_step = "capture_missing_replay_or_counterfactual_fields"
    else:
        recommended_next_step = "continue_collection_or_record_absent_opportunity"

    return {
        "screen_version": SCREEN_VERSION,
        "screen_status": "pass",
        "workload": {
            "label": workload_label,
            "declared_evidence_class": evidence_class,
            "context_stream_kind": context_stream_kind,
            "complete_workload_declared": bool(complete_workload),
            "complete_family_population_declared": bool(complete_family_population),
            "provenance_verified_by_tool": False,
        },
        "thresholds": thresholds,
        "trace_quality": {
            "event_count": len(events),
            "event_counts": dict(sorted(event_counts.items())),
            "session_count": len(sessions),
            "process_lifetimes_observed": process_lifetimes,
            "sample_every_values": sample_every_values,
            "trace_drop_count": drop_count,
            "complete_capture": complete_capture,
            "phase_values": phase_values,
            "phase_change_observed": phase_change_observed,
        },
        "observations": {
            "prepare_request_count": len(prepare_requests),
            "cache_access_count": len(cache_accesses),
            "cache_access_field_coverage": cache_coverage,
            "family_id_count": len(family_by_id),
            "family_version_event_count": int(event_counts.get("family_version", 0)),
            "family_transition_count": family_transitions,
            "context_stream_count": len(context_by_stream),
            "context_transition_event_count": int(event_counts.get("context_transition", 0)),
            "context_transition_count": context_transitions,
            "eligible_formula_count_k13_15": len(eligible_formula_digests_13_15),
            "eligible_formula_count_k13_16": len(eligible_formula_digests_13_16),
            "eligible_call_count_k13_15": len(eligible_calls_13_15),
            "eligible_call_count_k13_16": len(eligible_calls_13_16),
            "q_observation_count": len(q_values),
            "q_max": max(q_values, default=None),
            "kernel_fraction_observation_count": len(kernel_fractions),
            "kernel_fraction_median": median(kernel_fractions) if kernel_fractions else None,
        },
        "gates": {
            "cache": {
                "collection_adequate": cache_volume_adequate,
                "exact_logical_replay_ready": cache_exact_replay_ready,
                "requires_real_provenance": evidence_class != "real",
                "requires_complete_unsampled_capture": not complete_capture,
                "requires_complete_cache_fields": not cache_coverage["complete"],
            },
            "incremental_family": {
                "collection_adequate": family_volume_adequate,
                "followup_capture_ready": family_followup_ready,
                "incremental_replay_ready": False,
                "missing_capability": "metrics V1 lacks parent-version/change-set and replayable expression data",
            },
            "partial_context": {
                "collection_adequate": context_volume_adequate,
                "followup_capture_ready": context_followup_ready,
                "exact_context_replay_ready": False,
                "missing_capability": "metrics V1 stores context digests/overlap, not assignments",
            },
            "feature_selector": {
                "volume_adequate": selector_volume_adequate,
                "traffic_ready": selector_traffic_ready,
                "opportunity_fraction_computable": False,
                "missing_capability": "current trace lacks per-call current-vs-best eligible counterfactual timings",
            },
            "numba_or_native": {
                "repeated_q_observed": any(value > 1 for value in q_values),
                "break_even_computable": False,
                "missing_capability": "requires prototype import/JIT/copy timings and measured q-star",
            },
            "simd": {
                "eligible": False,
                "reason": "requires an accepted workload-backed Numba result first",
            },
        },
        "recommended_next_step": recommended_next_step,
        "limitations": [
            "declared evidence provenance is not cryptographically or operationally verified",
            "sampled metrics are an opportunity screen, not an exact request replay",
            "no performance benefit is inferred from collection volume alone",
        ],
    }


def screen_trace_files(
    paths: Sequence[str],
    **kwargs: Any,
) -> dict[str, Any]:
    events = load_trace_events(paths)
    result = screen_trace_events(events, **kwargs)
    summary = summarize_trace_files(paths)
    result["inputs"] = summary["input_files"]
    result["trace_schema_version"] = summary["schema_version"]
    result["content_modes"] = summary["content_modes"]
    return result
