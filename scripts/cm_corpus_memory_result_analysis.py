#!/usr/bin/env python3
"""Recompute postflight statistics from a frozen corpus-memory Runpod result.

This is a read-only analysis.  It performs no CM evaluation, model fitting, or
cloud operation.  Temporary-memory comparisons use the recorded call-window
``tracemalloc`` peak.  RSS comparisons use the separately recorded whole-child
``/proc`` samples and must not be interpreted as per-call measurements.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Callable, Iterable, Mapping, Sequence


SCHEMA = "cm-corpus-memory-result-analysis/v1"
MAX_JSON_BYTES = 32 << 20
MAX_ROWS = 10_000
FIXED_LIMITS = (4 << 20, 16 << 20, 64 << 20)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError(f"input exceeds {MAX_JSON_BYTES} bytes: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError(f"input exceeds {MAX_JSON_BYTES} bytes: {path}")
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            if len(rows) >= MAX_ROWS:
                raise ValueError(f"input exceeds {MAX_ROWS} rows: {path}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"line {line_number} is not an object: {path}")
            rows.append(value)
    return rows


def _nonnegative_integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _nearest_rank(values: Sequence[float | int], fraction: float) -> float | int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def distribution(values: Iterable[float | int]) -> dict[str, Any]:
    materialized = list(values)
    return {
        "count": len(materialized),
        "min": min(materialized, default=None),
        "median": statistics.median(materialized) if materialized else None,
        "p95_nearest_rank": _nearest_rank(materialized, 0.95),
        "max": max(materialized, default=None),
    }


def _estimate(row: Mapping[str, Any], model: str) -> int:
    if model == "legacy":
        return _nonnegative_integer(row.get("legacy_estimate"), "legacy_estimate")
    candidate = row.get("candidate")
    if not isinstance(candidate, Mapping):
        raise ValueError("candidate must be an object")
    return _nonnegative_integer(candidate.get("temporary_bytes"), "candidate.temporary_bytes")


def _model_group(rows: Sequence[Mapping[str, Any]], model: str) -> dict[str, Any]:
    peaks = [_nonnegative_integer(row.get("tracemalloc_peak_bytes"), "tracemalloc_peak_bytes") for row in rows]
    estimates = [_estimate(row, model) for row in rows]
    ratios = [estimate / peak for estimate, peak in zip(estimates, peaks) if peak]
    relations = Counter(
        "under" if estimate < peak else "over" if estimate > peak else "equal"
        for estimate, peak in zip(estimates, peaks)
    )
    return {
        "rows": len(rows),
        "relations_to_tracemalloc_peak": dict(sorted(relations.items())),
        "estimate_over_tracemalloc_peak": distribution(ratios),
    }


def _grouped(
    rows: Sequence[Mapping[str, Any]],
    keys: Sequence[str],
    summarize: Callable[[Sequence[Mapping[str, Any]]], dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(key) for key in keys)].append(row)
    result: list[dict[str, Any]] = []
    for values, group in sorted(groups.items(), key=lambda item: tuple(str(v) for v in item[0])):
        result.append({**dict(zip(keys, values)), **summarize(group)})
    return result


def _boundary(rows: Sequence[Mapping[str, Any]], model: str, limit: int) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    error_groups: dict[str, Counter[tuple[Any, ...]]] = {
        "false_admission": Counter(),
        "false_refusal": Counter(),
    }
    for row in rows:
        estimate = _estimate(row, model)
        peak = _nonnegative_integer(row.get("tracemalloc_peak_bytes"), "tracemalloc_peak_bytes")
        admitted = estimate <= limit
        observed_fits = peak <= limit
        if admitted and observed_fits:
            counts["correct_admission"] += 1
        elif admitted:
            counts["false_admission"] += 1
            error_groups["false_admission"][(
                row.get("case_id"), row.get("k"), row.get("representation"), row.get("schedule")
            )] += 1
        elif observed_fits:
            counts["false_refusal"] += 1
            error_groups["false_refusal"][(
                row.get("case_id"), row.get("k"), row.get("representation"), row.get("schedule")
            )] += 1
        else:
            counts["correct_refusal"] += 1
    return {
        "model": model,
        "limit_bytes": limit,
        "rows": len(rows),
        **{name: counts[name] for name in (
            "correct_admission", "false_admission", "false_refusal", "correct_refusal"
        )},
        "error_groups": {
            error: [
                {
                    "case_id": identity[0], "k": identity[1],
                    "representation": identity[2], "schedule": identity[3], "rows": count,
                }
                for identity, count in sorted(groups.items(), key=lambda item: tuple(str(v) for v in item[0]))
            ]
            for error, groups in error_groups.items()
        },
    }


def analyze(result_dir: Path) -> dict[str, Any]:
    corpus_dir = result_dir / "evidence" / "run-output" / "corpus-memory"
    raw_path = corpus_dir / "raw.jsonl"
    rss_path = corpus_dir / "rss-jobs.jsonl"
    selection_path = corpus_dir / "selection-manifest.json"
    oracle_path = corpus_dir / "oracles.json"
    rows = _read_jsonl(raw_path)
    rss_rows = _read_jsonl(rss_path)
    selection = _read_json(selection_path)
    oracles = _read_json(oracle_path)
    if not isinstance(selection, dict) or not isinstance(selection.get("cases"), list):
        raise ValueError("invalid selection manifest")
    if not isinstance(oracles, dict):
        raise ValueError("invalid oracle document")

    planned = selection.get("execution", {})
    expected_cases = len(selection["cases"])
    expected_jobs = _nonnegative_integer(planned.get("planned_jobs"), "planned_jobs")
    expected_calls = _nonnegative_integer(planned.get("planned_calls"), "planned_calls")
    identities: set[tuple[Any, ...]] = set()
    case_ids = {case.get("case_id") for case in selection["cases"]}
    for index, row in enumerate(rows):
        if row.get("status") != "ok" or row.get("exact") is not True:
            raise ValueError(f"row {index} is not exact/ok")
        identity = (
            row.get("case_id"), row.get("representation"), row.get("schedule"), row.get("repetition")
        )
        if identity in identities:
            raise ValueError(f"duplicate call identity: {identity!r}")
        identities.add(identity)
        if row.get("case_id") not in case_ids:
            raise ValueError(f"unknown case in row {index}")
        if row.get("output_sha256") != row.get("independent_oracle_sha256"):
            raise ValueError(f"oracle mismatch in row {index}")
    if len(case_ids) != expected_cases or len(rows) != expected_calls or len(rss_rows) != expected_jobs:
        raise ValueError("saved result does not match the frozen plan")

    rows_by_job: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        job_id = row.get("job_id")
        if not isinstance(job_id, str):
            raise ValueError("raw row lacks job_id")
        rows_by_job[job_id].append(row)
    rss_enriched: list[dict[str, Any]] = []
    seen_jobs: set[str] = set()
    metadata_keys = ("case_id", "corpus", "role", "k", "schedule", "representation")
    for index, rss in enumerate(rss_rows):
        job_id = rss.get("job_id")
        if not isinstance(job_id, str) or job_id in seen_jobs or job_id not in rows_by_job:
            raise ValueError(f"invalid RSS job identity at row {index}")
        seen_jobs.add(job_id)
        source_rows = rows_by_job[job_id]
        metadata: dict[str, Any] = {}
        for key in metadata_keys:
            values = {row.get(key) for row in source_rows}
            if len(values) != 1:
                raise ValueError(f"inconsistent {key} for {job_id}")
            metadata[key] = next(iter(values))
        sampled = _nonnegative_integer(rss.get("sampled_rss_peak_bytes"), "sampled RSS")
        hwm = _nonnegative_integer(rss.get("kernel_hwm_peak_bytes_observed"), "kernel HWM")
        if rss.get("returncode") != 0 or rss.get("timed_out") is not False:
            raise ValueError(f"failed RSS child job: {job_id}")
        rss_enriched.append({**rss, **metadata, "sampled_rss_peak_bytes": sampled,
                             "kernel_hwm_peak_bytes_observed": hwm})
    if seen_jobs != set(rows_by_job):
        raise ValueError("RSS/raw job coverage mismatch")

    def rss_summary(group: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "jobs": len(group),
            "sampled_rss_peak_bytes": distribution(row["sampled_rss_peak_bytes"] for row in group),
            "kernel_hwm_peak_bytes_observed": distribution(
                row["kernel_hwm_peak_bytes_observed"] for row in group
            ),
        }

    model_results: dict[str, Any] = {}
    for model in ("candidate", "legacy"):
        model_results[model] = {
            "overall": _model_group(rows, model),
            "by_corpus": _grouped(rows, ("corpus",), lambda group, m=model: _model_group(group, m)),
            "by_role": _grouped(rows, ("role",), lambda group, m=model: _model_group(group, m)),
            "by_schedule": _grouped(rows, ("schedule",), lambda group, m=model: _model_group(group, m)),
            "by_representation": _grouped(
                rows, ("representation",), lambda group, m=model: _model_group(group, m)
            ),
            "by_k": _grouped(rows, ("k",), lambda group, m=model: _model_group(group, m)),
            "by_role_schedule_representation": _grouped(
                rows, ("role", "schedule", "representation"),
                lambda group, m=model: _model_group(group, m),
            ),
        }

    dead_cases = [case for case in selection["cases"] if case.get("syntactic_k") != case.get("k")]
    dead_axis: list[dict[str, Any]] = []
    for case in dead_cases:
        case_id = case["case_id"]
        case_rows = [row for row in rows if row.get("case_id") == case_id]
        oracle = oracles.get(case_id)
        if not isinstance(oracle, dict):
            raise ValueError(f"missing oracle for {case_id}")
        output_hashes = sorted({row.get("output_sha256") for row in case_rows})
        dead_axis.append({
            "case_id": case_id,
            "corpus": case.get("corpus"),
            "semantic_k": case.get("k"),
            "syntactic_k": case.get("syntactic_k"),
            "fixed": oracle.get("fixed"),
            "rows": len(case_rows),
            "representations": sorted({row.get("representation") for row in case_rows}),
            "schedules": sorted({row.get("schedule") for row in case_rows}),
            "repetitions": sorted({row.get("repetition") for row in case_rows}),
            "all_exact": all(row.get("exact") is True for row in case_rows),
            "all_outputs_match_projected_oracle": output_hashes == [oracle.get("live_output_sha256")],
            "projected_live_output_sha256": oracle.get("live_output_sha256"),
            "full_frozen_truth_sha256": oracle.get("frozen_truth_sha256"),
            "projected_hash_differs_from_full_truth": (
                oracle.get("live_output_sha256") != oracle.get("frozen_truth_sha256")
            ),
        })

    return {
        "schema": SCHEMA,
        "inputs": {
            "raw_jsonl_sha256": _sha256(raw_path),
            "rss_jobs_jsonl_sha256": _sha256(rss_path),
            "selection_manifest_sha256": _sha256(selection_path),
            "oracles_sha256": _sha256(oracle_path),
        },
        "grid": {
            "cases": expected_cases,
            "jobs": len(rss_rows),
            "calls": len(rows),
            "unique_call_identities": len(identities),
            "statuses": dict(Counter(row["status"] for row in rows)),
            "exact_rows": sum(row.get("exact") is True for row in rows),
            "cases_by_corpus_role": _grouped(
                selection["cases"], ("corpus", "role"), lambda group: {"cases": len(group)}
            ),
        },
        "temporary_memory": {
            "measurement": "call-window tracemalloc peak",
            "models": model_results,
            "fixed_limit_counterfactuals": [
                _boundary(rows, model, limit)
                for limit in FIXED_LIMITS for model in ("candidate", "legacy")
            ],
        },
        "rss": {
            "measurement": (
                "whole isolated child lifetime, including interpreter imports, compile, evaluation, "
                "output hashing, and allocator lifetime; external 5 ms /proc polling"
            ),
            "overall": rss_summary(rss_enriched),
            "by_corpus": _grouped(rss_enriched, ("corpus",), rss_summary),
            "by_role": _grouped(rss_enriched, ("role",), rss_summary),
            "by_schedule": _grouped(rss_enriched, ("schedule",), rss_summary),
            "by_representation": _grouped(rss_enriched, ("representation",), rss_summary),
            "by_k": _grouped(rss_enriched, ("k",), rss_summary),
        },
        "dead_syntactic_axis": dead_axis,
        "conclusions": {
            "candidate_underestimates": model_results["candidate"]["overall"]
                ["relations_to_tracemalloc_peak"].get("under", 0),
            "legacy_underestimates": model_results["legacy"]["overall"]
                ["relations_to_tracemalloc_peak"].get("under", 0),
            "calibration_performed": False,
            "production_estimator_accepted": False,
            "real_workload_compatibility": (
                "not measured; BX1/B2/EPFL are frozen benchmark corpora"
            ),
            "rss_is_per_call": False,
            "rss_proves_enforcement": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error(f"refusing to overwrite: {args.output}")
    analysis = analyze(args.result_dir)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(analysis, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({
        "candidate_underestimates": analysis["conclusions"]["candidate_underestimates"],
        "legacy_underestimates": analysis["conclusions"]["legacy_underestimates"],
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
