"""Finalize a bounded, hash-bound analysis of the successor screen."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
PRELAUNCH = BASE / "successor-prelaunch-002"
RUN_DIR = BASE / "runpod-successor-001"
RECONCILIATION = BASE / "successor-reconciliation-001/RUNPOD_RECONCILIATION.json"
OUT = BASE / "successor-results-analysis-001"
PLAN = PRELAUNCH / "PLAN.json"
MANIFEST = PRELAUNCH / "UPLOAD_MANIFEST.json"
RUN = RUN_DIR / "RUN.json"
SUMMARY = RUN_DIR / "evidence/core-screen/summary.json"
LEDGER = RUN_DIR / "evidence/core-screen/ledger.jsonl"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def geometric_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return math.exp(sum(math.log(value) for value in values) / len(values))


def median_seconds(rows: list[dict]) -> float | None:
    values = [row["wall_ns"] / 1e9 for row in rows if row["status"] == "ok"]
    return statistics.median(values) if values else None


def rounded(value: float | None) -> float | None:
    return round(value, 9) if value is not None else None


def main() -> None:
    if OUT.exists():
        raise RuntimeError("successor results analysis already exists")
    plan = load(PLAN)
    run = load(RUN)
    summary = load(SUMMARY)
    reconciliation = load(RECONCILIATION)
    rows = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()]
    if (
        digest(MANIFEST)
        != "580b08ec86385ebca01ed3e763def78e4c68c1c98d216a21b07a307f4061fcee"
        or run.get("status") != "complete"
        or summary.get("status") != "complete"
        or summary.get("cells") != 108
        or summary.get("status_counts") != {"ok": 105, "timeout": 3}
        or summary.get("correctness_mismatches")
        or len(rows) != 108
        or len({row["cell_id"] for row in rows}) != 108
        or {row["status"] for row in rows} - {"ok", "timeout"}
        or reconciliation.get("inventories")
        != {"v1_pod_count": 0, "v2_pod_count": 0}
    ):
        raise RuntimeError("successor evidence identity or terminal state mismatch")

    cases = {case["case_id"]: case for case in plan["cases"]}
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["case_id"], row["arm"])].append(row)

    lane_arms = {
        "exact_count": ("ganak", "d4"),
        "biology_fixed_points": ("bnet_cm_scalar", "biodivine_aeon"),
    }
    case_results = []
    paired_ratios: dict[str, list[float]] = defaultdict(list)
    for case_id, case in sorted(cases.items(), key=lambda item: (item[1]["lane"], item[0])):
        lane = case["lane"]
        first, second = lane_arms[lane]
        first_rows = grouped[(case_id, first)]
        second_rows = grouped[(case_id, second)]
        by_rep_first = {row["repetition"]: row for row in first_rows}
        by_rep_second = {row["repetition"]: row for row in second_rows}
        ratios = []
        for repetition in range(plan["repetitions"]):
            left, right = by_rep_first[repetition], by_rep_second[repetition]
            if left["status"] == right["status"] == "ok":
                if left["value_sha256"] != right["value_sha256"]:
                    raise RuntimeError("paired value mismatch absent from summary")
                ratio = right["wall_ns"] / left["wall_ns"]
                ratios.append(ratio)
                paired_ratios[lane].append(ratio)
        first_median = median_seconds(first_rows)
        second_median = median_seconds(second_rows)
        values = sorted({row["value"] for row in first_rows + second_rows if row["status"] == "ok"})
        if len(values) != 1:
            raise RuntimeError("case lacks one agreed result value")
        case_results.append(
            {
                "case_id": case_id,
                "lane": lane,
                "metadata": case["metadata"],
                "agreed_value": values[0],
                "first_arm": first,
                "second_arm": second,
                "first_arm_ok": sum(row["status"] == "ok" for row in first_rows),
                "second_arm_ok": sum(row["status"] == "ok" for row in second_rows),
                "first_arm_timeouts": sum(row["status"] == "timeout" for row in first_rows),
                "second_arm_timeouts": sum(row["status"] == "timeout" for row in second_rows),
                "first_arm_median_seconds": rounded(first_median),
                "second_arm_median_seconds": rounded(second_median),
                "second_over_first_median_ratio": rounded(
                    second_median / first_median
                    if first_median is not None and second_median is not None
                    else None
                ),
                "paired_repetitions": len(ratios),
            }
        )

    lane_results = {}
    for lane, (first, second) in lane_arms.items():
        ratios = paired_ratios[lane]
        summary_comparison = summary["comparisons"][lane]
        if (
            len(ratios) != summary_comparison["paired_cells"]
            or not math.isclose(geometric_mean(ratios), summary_comparison["geometric_mean_ratio"], rel_tol=1e-12)
            or not math.isclose(statistics.median(ratios), summary_comparison["median_ratio"], rel_tol=1e-12)
        ):
            raise RuntimeError("recomputed comparison differs from retrieved summary")
        lane_results[lane] = {
            "first_arm": first,
            "second_arm": second,
            "ratio_definition": f"{second} wall time divided by {first} wall time",
            "paired_cells": len(ratios),
            "geometric_mean_ratio": geometric_mean(ratios),
            "median_ratio": statistics.median(ratios),
            "reciprocal_geometric_mean": 1 / geometric_mean(ratios),
            "reciprocal_median": 1 / statistics.median(ratios),
        }

    timeout_rows = [
        {
            "case_id": row["case_id"],
            "lane": row["lane"],
            "arm": row["arm"],
            "repetition": row["repetition"],
            "reason": row.get("reason"),
            "parent_wall_seconds": row.get("parent_wall_ns", 0) / 1e9,
        }
        for row in rows
        if row["status"] == "timeout"
    ]
    result = {
        "schema": "cm-benchmark-successor-results-analysis/v1",
        "created_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "campaign_id": "cm-mega-successor-20260914-009",
        "status": "complete",
        "cells": len(rows),
        "successful_measurements": summary["status_counts"]["ok"],
        "timeouts": summary["status_counts"]["timeout"],
        "correctness_mismatches": [],
        "lane_results": lane_results,
        "case_results": case_results,
        "timeout_rows": timeout_rows,
        "claim_boundaries": [
            "Ratios describe only the selected bounded screen and are not corpus-wide claims.",
            "Timed-out pairs are absent from paired ratios and are reported separately.",
            "Biology models are the ten admitted closed models with at most 16 targets.",
            "Prior affine/projected-count results were reused and were not rerun.",
            "Projected counting remains an unpaired Ganak measurement lane with no CM speedup claim.",
        ],
        "bound_sha256": {
            "plan": digest(PLAN),
            "upload_manifest": digest(MANIFEST),
            "run": digest(RUN),
            "evidence_zip": digest(RUN_DIR / "evidence.zip"),
            "ledger": digest(LEDGER),
            "summary": digest(SUMMARY),
            "reconciliation": digest(RECONCILIATION),
        },
    }
    OUT.mkdir(parents=True, exist_ok=False)
    result_path = OUT / "RESULTS.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    exact = lane_results["exact_count"]
    biology = lane_results["biology_fixed_points"]
    report = (
        "# CM focused successor benchmark results\n\n"
        "The bounded 108-cell RunPod screen completed with 105 successful measurements, "
        "three adapter-deadline timeouts, and no correctness mismatches.\n\n"
        "## Exact model counting\n\n"
        f"Across {exact['paired_cells']} successful paired repetitions, d4/Ganak had a "
        f"geometric-mean wall-time ratio of {exact['geometric_mean_ratio']:.6f} and a "
        f"median ratio of {exact['median_ratio']:.6f}. Equivalently, d4 was "
        f"{exact['reciprocal_geometric_mean']:.3f}x faster by geometric mean and "
        f"{exact['reciprocal_median']:.3f}x faster by the median paired ratio. Ganak "
        "timed out in all three repetitions of the 2,701-variable/29,534-clause case; "
        "d4 completed that case in all three repetitions.\n\n"
        "## Closed biology fixed points\n\n"
        f"Across {biology['paired_cells']} paired repetitions, AEON/scalar had a "
        f"geometric-mean ratio of {biology['geometric_mean_ratio']:.6f}, while its "
        f"median paired ratio was {biology['median_ratio']:.6f}. The opposing aggregate "
        "directions indicate heterogeneous model-level performance; the per-case table "
        "in RESULTS.json should be used instead of a single winner claim. All values "
        "agreed and no biology cell timed out.\n\n"
        "## Boundaries\n\n"
        "These are results for the predeclared focused screen, not corpus-wide claims. "
        "Timed-out pairs are excluded from paired timing ratios and reported separately. "
        "Prior affine/projected-count evidence was reused rather than rerun; projected "
        "counting remains unpaired and supports no CM speedup claim.\n"
    )
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "complete",
                "results_sha256": digest(result_path),
                "cells": result["cells"],
                "successful_measurements": result["successful_measurements"],
                "timeouts": result["timeouts"],
                "correctness_mismatches": 0,
                "exact_d4_over_ganak_geomean": exact["geometric_mean_ratio"],
                "biology_aeon_over_scalar_geomean": biology["geometric_mean_ratio"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
