from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


_FAILURE_KINDS = ("declined", "refused", "timeout", "error", "oom", "missing")
_KNOWN_STATUSES = {"success", *_FAILURE_KINDS}


@dataclass(frozen=True)
class PairedComparisonSpec:
    left_time: str
    right_time: str
    left_status: str | None = None
    right_status: str | None = None
    left_artifact: str | None = None
    right_artifact: str | None = None
    left_timing: str | None = None
    right_timing: str | None = None
    allow_incomplete_headline: bool = False


def _finite_positive(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0.0


def _status(row: Mapping[str, Any], status_field: str | None, time_field: str) -> str:
    if status_field:
        raw = row.get(status_field)
        if raw is not None and str(raw).strip():
            status = str(raw).strip().lower()
            if status not in _KNOWN_STATUSES:
                return "error"
            if status != "success":
                return status
    return "success" if _finite_positive(row.get(time_field)) else "missing"


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def aggregate_paired_comparison(
    rows: Iterable[Mapping[str, Any]],
    spec: PairedComparisonSpec,
) -> dict[str, Any]:
    observations = list(rows)
    result: dict[str, Any] = {
        "attempted": len(observations),
        "paired_success": 0,
        "pairing_complete": False,
        "headline_ratio_available": False,
        "ratio_of_medians": None,
        "median_of_paired_ratios": None,
        "paired_ratio_p10": None,
        "paired_ratio_p90": None,
        "paired_ratio_min": None,
        "paired_ratio_max": None,
    }
    for side in ("left", "right"):
        result[f"{side}_success"] = 0
        for kind in _FAILURE_KINDS:
            result[f"{side}_{kind}"] = 0

    left_values: list[float] = []
    right_values: list[float] = []
    ratios: list[float] = []
    incompatible = 0
    for row in observations:
        left_status = _status(row, spec.left_status, spec.left_time)
        right_status = _status(row, spec.right_status, spec.right_time)
        result[f"left_{left_status}"] += 1
        result[f"right_{right_status}"] += 1
        if left_status != "success" or right_status != "success":
            continue
        if (
            spec.left_artifact
            and spec.right_artifact
            and row.get(spec.left_artifact) != row.get(spec.right_artifact)
        ) or (
            spec.left_timing
            and spec.right_timing
            and row.get(spec.left_timing) != row.get(spec.right_timing)
        ):
            incompatible += 1
            continue
        left = float(row[spec.left_time])
        right = float(row[spec.right_time])
        left_values.append(left)
        right_values.append(right)
        ratios.append(left / right)

    result["incompatible_pairs"] = incompatible
    result["paired_success"] = len(ratios)
    complete = len(ratios) == len(observations) and incompatible == 0
    result["pairing_complete"] = complete
    if ratios:
        result["ratio_of_medians"] = statistics.median(left_values) / statistics.median(right_values)
        result["median_of_paired_ratios"] = statistics.median(ratios)
        result["paired_ratio_p10"] = _percentile(ratios, 0.10)
        result["paired_ratio_p90"] = _percentile(ratios, 0.90)
        result["paired_ratio_min"] = min(ratios)
        result["paired_ratio_max"] = max(ratios)
    result["headline_ratio_available"] = bool(
        ratios and (complete or spec.allow_incomplete_headline)
    )
    result["headline_ratio"] = (
        result["median_of_paired_ratios"] if result["headline_ratio_available"] else None
    )
    return result
