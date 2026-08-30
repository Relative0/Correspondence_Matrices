#!/usr/bin/env python3
"""Counterfactual temporary-memory policy analysis over frozen study rows.

This tool performs no CM evaluation and fits no estimator.  It treats each
eligible row's recorded ``tracemalloc_peak_bytes`` as the observed temporary
memory value, then applies the exact inclusive policy rule
``estimate <= limit``.  RSS, output-byte, and variable-count gates are outside
this counterfactual and remain separate.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Iterable


SCHEMA = "cm-memory-boundary-analysis/v1"
MAX_INPUT_BYTES = 32 << 20
MAX_ROWS = 10_000
FIXED_LIMITS = {
    "strict-diagnostic": 4 << 20,
    "production-balanced-v1-benchmark-remote": 16 << 20,
    "permissive-diagnostic": 64 << 20,
}
MODELS = ("legacy", "candidate")


def _integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def classify(estimate: int, peak: int, limit: int) -> dict[str, Any]:
    """Apply the exact inclusive admission boundary for one observation."""
    estimate = _integer(estimate, "estimate")
    peak = _integer(peak, "peak")
    limit = _integer(limit, "limit")
    admitted = estimate <= limit
    observed_fits = peak <= limit
    return {
        "status": "admitted" if admitted else "refused",
        "observed_fits": observed_fits,
        "false_admission": admitted and not observed_fits,
        "false_refusal": not admitted and observed_fits,
    }


def load_rows(path: Path) -> tuple[list[dict[str, Any]], str]:
    size = path.stat().st_size
    if size > MAX_INPUT_BYTES:
        raise ValueError(f"input exceeds {MAX_INPUT_BYTES} bytes")
    raw = path.read_bytes()
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        if len(rows) >= MAX_ROWS:
            raise ValueError(f"input exceeds {MAX_ROWS} rows")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise ValueError(f"line {line_number}: row must be an object")
        rows.append(row)
    return rows, hashlib.sha256(raw).hexdigest()


def _eligible(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible: list[dict[str, Any]] = []
    identities: set[tuple[Any, ...]] = set()
    for index, row in enumerate(rows):
        if row.get("status") != "ok" or row.get("comparison_eligible") is not True:
            continue
        peak = _integer(row.get("tracemalloc_peak_bytes"), f"row {index} peak")
        legacy = _integer(row.get("legacy_estimate"), f"row {index} legacy estimate")
        candidate_doc = row.get("candidate")
        if not isinstance(candidate_doc, dict):
            raise ValueError(f"row {index} candidate must be an object")
        candidate = _integer(candidate_doc.get("temporary_bytes"), f"row {index} candidate estimate")
        identity = (
            row.get("case_id"), row.get("schedule"), row.get("representation"),
            row.get("repetition"), row.get("window"),
        )
        if identity in identities:
            raise ValueError(f"duplicate comparable row identity: {identity!r}")
        identities.add(identity)
        eligible.append({**row, "_peak": peak, "_legacy": legacy, "_candidate": candidate})
    if not eligible:
        raise ValueError("input contains no eligible comparable rows")
    return eligible


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def analyze(rows: Iterable[dict[str, Any]], input_sha256: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    eligible = _eligible(rows)
    row_boundaries: list[dict[str, Any]] = []
    fixed_groups: dict[tuple[Any, ...], Counter[str]] = defaultdict(Counter)

    for row in eligible:
        peak = row["_peak"]
        for model in MODELS:
            estimate = row[f"_{model}"]
            relation = "over" if estimate > peak else "under" if estimate < peak else "equal"
            lower = min(estimate, peak)
            upper = max(estimate, peak) - 1
            boundary = {
                "schema": SCHEMA,
                "case_id": row.get("case_id"),
                "role": row.get("role"),
                "family": row.get("family"),
                "schedule": row.get("schedule"),
                "representation": row.get("representation"),
                "repetition": row.get("repetition"),
                "model": model,
                "estimate_bytes": estimate,
                "tracemalloc_peak_bytes": peak,
                "estimate_relation_to_peak": relation,
                "error_limit_interval_inclusive": [lower, upper] if lower <= upper else None,
                "error_interval_bytes": abs(estimate - peak),
                "estimate_minus_peak_bytes": estimate - peak,
                "estimate_over_peak": _ratio(estimate, peak),
                "checks": {},
            }
            for offset in (-1, 0, 1):
                limit = estimate + offset
                if limit < 0:
                    continue
                boundary["checks"][f"estimate{offset:+d}"] = {
                    "limit_bytes": limit,
                    **classify(estimate, peak, limit),
                }
            for profile, limit in FIXED_LIMITS.items():
                decision = classify(estimate, peak, limit)
                key = (
                    profile, limit, model, row.get("role"), row.get("schedule"),
                    row.get("representation"),
                )
                fixed_groups[key][decision["status"]] += 1
                fixed_groups[key]["false_admissions"] += int(decision["false_admission"])
                fixed_groups[key]["false_refusals"] += int(decision["false_refusal"])
                fixed_groups[key]["rows"] += 1
            row_boundaries.append(boundary)

    fixed_rows: list[dict[str, Any]] = []
    for key, counts in sorted(fixed_groups.items(), key=lambda item: tuple(str(x) for x in item[0])):
        profile, limit, model, role, schedule, representation = key
        fixed_rows.append({
            "profile": profile,
            "limit_bytes": limit,
            "model": model,
            "role": role,
            "schedule": schedule,
            "representation": representation,
            **dict(counts),
        })

    model_summary: dict[str, Any] = {}
    for model in MODELS:
        group = [row for row in row_boundaries if row["model"] == model]
        relations = Counter(row["estimate_relation_to_peak"] for row in group)
        ratios = [row["estimate_over_peak"] for row in group if row["estimate_over_peak"] is not None]
        model_summary[model] = {
            "rows": len(group),
            "relations": dict(relations),
            "false_refusal_interval_bytes_total": sum(
                row["error_interval_bytes"] for row in group
                if row["estimate_relation_to_peak"] == "over"
            ),
            "false_admission_interval_bytes_total": sum(
                row["error_interval_bytes"] for row in group
                if row["estimate_relation_to_peak"] == "under"
            ),
            "estimate_over_peak_median": statistics.median(ratios) if ratios else None,
            "estimate_over_peak_max": max(ratios, default=None),
            "estimate_minus_one": dict(Counter(
                "false_refusal" if row["checks"]["estimate-1"]["false_refusal"] else "correct_refusal"
                for row in group
            )),
            "estimate_exact": dict(Counter(
                "false_admission" if row["checks"]["estimate+0"]["false_admission"] else "correct_admission"
                for row in group
            )),
            "estimate_plus_one": dict(Counter(
                "false_admission" if row["checks"]["estimate+1"]["false_admission"] else "correct_admission"
                for row in group
            )),
        }

    summary = {
        "schema": SCHEMA,
        "input_sha256": input_sha256,
        "input_rows": len(list(rows)) if isinstance(rows, list) else None,
        "eligible_comparable_rows": len(eligible),
        "measurement": "recorded tracemalloc comparable-window peak",
        "decision_rule": "admit iff estimate_bytes <= limit_bytes",
        "scope_limits": [
            "counterfactual only; no new CM computation",
            "temporary-memory gate only; output and variable gates excluded",
            "tracemalloc is not RSS and does not prove process-memory enforcement",
            "repetitions are retained as observations and are not independent cases",
            "candidate coefficients are not fitted or changed",
        ],
        "fixed_limits": FIXED_LIMITS,
        "models": model_summary,
        "fixed_policy_rows": fixed_rows,
        "production_estimator_accepted": False,
    }
    return summary, row_boundaries, fixed_rows


def _write_json_exclusive(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def write_outputs(output_dir: Path, summary: dict[str, Any], boundaries: list[dict[str, Any]], fixed_rows: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_json_exclusive(output_dir / "summary.json", summary)
    with (output_dir / "row-boundaries.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        for row in boundaries:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    fields = (
        "profile", "limit_bytes", "model", "role", "schedule", "representation",
        "rows", "admitted", "refused", "false_admissions", "false_refusals",
    )
    with (output_dir / "fixed-policy-matrix.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in fixed_rows:
            writer.writerow({field: row.get(field, 0) for field in fields})
    candidate = summary["models"]["candidate"]
    legacy = summary["models"]["legacy"]
    report = f"""# Temporary-memory boundary counterfactual

This is a local policy analysis of a frozen Runpod measurement, not a new
benchmark. It uses the exact inclusive rule `estimate <= limit` and the
recorded comparable-window `tracemalloc` peak. It excludes output/variable
gates and cannot establish an RSS limit.

## Result

- Eligible measured calls: {summary['eligible_comparable_rows']}
- Candidate estimates above/equal/below peak: {candidate['relations'].get('over', 0)} / {candidate['relations'].get('equal', 0)} / {candidate['relations'].get('under', 0)}
- Legacy estimates above/equal/below peak: {legacy['relations'].get('over', 0)} / {legacy['relations'].get('equal', 0)} / {legacy['relations'].get('under', 0)}
- At `candidate estimate - 1`, false refusals: {candidate['estimate_minus_one'].get('false_refusal', 0)}
- At the exact candidate estimate, false admissions: {candidate['estimate_exact'].get('false_admission', 0)}
- At the exact legacy estimate, false admissions: {legacy['estimate_exact'].get('false_admission', 0)}

The row-level JSONL records `estimate-1`, `estimate`, and `estimate+1` checks
and the complete byte interval in which each estimate/measurement pair would
disagree. The CSV separates fixed 4 MiB, 16 MiB, and 64 MiB results by role,
schedule, representation, and model.

No candidate coefficient or production default changed. Repeated calls are
retained as observations; they are not claimed as independent formulas.
"""
    with (output_dir / "REPORT.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output_dir.exists():
        parser.error(f"refusing to overwrite: {args.output_dir}")
    rows, digest = load_rows(args.input)
    summary, boundaries, fixed_rows = analyze(rows, digest)
    write_outputs(args.output_dir, summary, boundaries, fixed_rows)
    print(json.dumps({
        "eligible_comparable_rows": summary["eligible_comparable_rows"],
        "input_sha256": digest,
        "output_dir": str(args.output_dir),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
