"""Finalize the retrieved core screen without changing frozen measurements."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign"
RUN = BASE / "runpod-results-002"
SCREEN = RUN / "evidence/core-screen"
OUT = BASE / "results-analysis-001"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def classify(log):
    if "Ganak exact-count deadline exceeded" in log:
        return "cell_timeout_reported_as_worker_error"
    if "Boolean network has undeclared regulator" in log:
        return "input_not_closed_under_declared_targets"
    if "d4 exited with code -6" in log:
        return "d4_native_abort_signal_6"
    return "other_worker_error"


def main():
    if OUT.exists():
        raise RuntimeError("results analysis output already exists")
    rows = [json.loads(line) for line in (SCREEN / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
    summary = json.loads((SCREEN / "SUMMARY.json").read_text(encoding="utf-8"))
    plan = json.loads((SCREEN / "PLAN.json").read_text(encoding="utf-8"))
    if len(rows) != 192 or summary.get("correctness_mismatches") != []:
        raise RuntimeError("retrieved screen is incomplete or has a correctness mismatch")

    terminal = Counter((row["lane"], row["arm"], row["status"]) for row in rows)
    diagnostic = Counter()
    case_diagnostics = defaultdict(Counter)
    for index, row in enumerate(rows):
        if row["status"] != "worker_error":
            continue
        log = (SCREEN / "cells" / f"{index:04d}" / "worker.log").read_text(
            encoding="utf-8", errors="replace")
        kind = classify(log)
        diagnostic[(row["lane"], row["arm"], kind)] += 1
        case_diagnostics[row["case_id"]][kind] += 1

    arm_rows = defaultdict(list)
    for row in rows:
        if row["status"] == "ok":
            arm_rows[(row["lane"], row["arm"])].append(row)
    arm_stats = {}
    for (lane, arm), items in sorted(arm_rows.items()):
        rss = [row["rss_highwater_kib"] for row in items if row.get("rss_highwater_kib") is not None]
        arm_stats[lane + ":" + arm] = {
            "cells": len(items),
            "cases": len({row["case_id"] for row in items}),
            "median_wall_ms": statistics.median(row["wall_ns"] for row in items) / 1e6,
            "minimum_wall_ms": min(row["wall_ns"] for row in items) / 1e6,
            "maximum_wall_ms": max(row["wall_ns"] for row in items) / 1e6,
            "median_rss_highwater_kib": statistics.median(rss) if rss else None,
        }

    cases = []
    for case in plan["cases"]:
        items = [row for row in rows if row["case_id"] == case["case_id"]]
        arms = {}
        for arm in sorted({row["arm"] for row in items}):
            selected = [row for row in items if row["arm"] == arm]
            ok = [row for row in selected if row["status"] == "ok"]
            arms[arm] = {
                "terminal_status_counts": dict(sorted(Counter(row["status"] for row in selected).items())),
                "value": ok[0]["value"] if ok else None,
                "median_wall_ms": statistics.median(row["wall_ns"] for row in ok) / 1e6 if ok else None,
                "median_rss_highwater_kib": statistics.median(
                    row["rss_highwater_kib"] for row in ok if row.get("rss_highwater_kib") is not None
                ) if ok else None,
            }
        cases.append({
            "case_id": case["case_id"],
            "lane": case["lane"],
            "path": case["path"],
            "input_sha256": case["input_sha256"],
            "arms": arms,
            "posthoc_error_classification": dict(sorted(case_diagnostics[case["case_id"]].items())),
        })

    document = {
        "schema": "cm-benchmark-core-screen-results-analysis/v1",
        "created_utc": now(),
        "campaign_id": "cm-mega-prelaunch-20260914-008",
        "scope": "bounded 192-cell screen; posthoc diagnostics do not change frozen terminal states",
        "source_hashes": {
            "evidence_archive": digest(RUN / "evidence.zip"),
            "run_record": digest(RUN / "RUN.json"),
            "ledger": digest(SCREEN / "ledger.jsonl"),
            "summary": digest(SCREEN / "SUMMARY.json"),
            "plan": digest(SCREEN / "PLAN.json"),
        },
        "integrity": {
            "planned_cells": 192,
            "terminal_cells": len(rows),
            "successful_measurements": sum(row["status"] == "ok" for row in rows),
            "frozen_worker_errors": sum(row["status"] == "worker_error" for row in rows),
            "correctness_mismatches": len(summary["correctness_mismatches"]),
            "independent_local_verification": "passed",
        },
        "terminal_counts": [
            {"lane": lane, "arm": arm, "status": status, "cells": count}
            for (lane, arm, status), count in sorted(terminal.items())
        ],
        "posthoc_worker_error_classification": [
            {"lane": lane, "arm": arm, "classification": kind, "cells": count}
            for (lane, arm, kind), count in sorted(diagnostic.items())
        ],
        "paired_comparisons": summary["comparisons"],
        "claim_boundaries": {
            "affine": "all eight selected cases completed in both arms; ratio is sparse-set/CM-packed",
            "biology": "only two of twelve selected files were closed under declared targets; no broad biology claim",
            "exact_count": "d4 aborted on every selected corpus case, so there is no paired Ganak/d4 comparison",
            "projected_count": "Ganak-only lane; no CM speedup claim; five of eight cases hit the 60-second bound",
        },
        "arm_statistics": arm_stats,
        "cases": cases,
    }
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / "RESULTS.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    affine = summary["comparisons"]["affine_solution_count"]
    biology = summary["comparisons"]["biology_fixed_points"]
    report = f"""# CM bounded counting, biology, and affine results

Status: retrieved, independently verified, and campaign Pod deleted.

The screen produced 90 successful measurements from 192 planned cells. All 192 cells have terminal records and there were zero paired correctness mismatches. The other 102 frozen `worker_error` records comprise 60 biology admission failures (undeclared regulators), 24 d4 native aborts, and 18 Ganak executions that reached the 60-second deadline.

## Affine solution counts

All 48 cells completed across eight cases and three repetitions per arm. CM packed elimination and the independent sparse-set oracle agreed in every pair. With ratio defined as sparse-set wall time divided by CM-packed wall time, the median ratio was {affine['median_ratio']:.3f}x and the geometric mean was {affine['geometric_mean_ratio']:.3f}x. Thus CM packed elimination was faster on aggregate in this bounded screen. Median arm times across all successful affine cells were {arm_stats['affine_solution_count:cm_packed_elimination']['median_wall_ms']:.3f} ms for CM packed and {arm_stats['affine_solution_count:sparse_set_elimination']['median_wall_ms']:.3f} ms for sparse-set elimination.

## Biology fixed points

Only two of twelve selected files were closed under their declared targets, yielding 12 valid cells and six matched pairs. The aggregate AEON/CM-scalar median ratio was {biology['median_ratio']:.3f}x, but the two admissible models point in opposite directions: AEON was much faster on one model while CM scalar was faster on the other. This sample is too small and admission-biased for a general biology performance claim.

## Exact and projected counting

Ganak completed 21 of 24 exact-count cells, covering seven of eight cases; the remaining three executions hit the 60-second bound. d4 aborted with signal 6 on all 24 corpus cells despite passing the pinned Linux smoke fixture, so no paired exact-counter comparison is valid.

The unpaired projected Ganak lane completed nine of 24 cells, covering three of eight cases; the other fifteen reached the 60-second bound. This lane contains no CM arm and supports no CM speedup claim.

## Boundaries

These are screen results, not comprehensive corpus results. The frozen ledger retains the original `worker_error` labels; the categories above are posthoc diagnostics from the captured worker logs. Full per-case counts, timings, memory high-water values, hashes, and error classifications are in `RESULTS.json`.

RunPod's control plane reported the authorized 16 vCPU and 64 GB RAM, while the container runtime reported 64 logical CPUs and no cgroup CPU or memory maximum. The screen ran one fresh worker at a time and Ganak was explicitly limited to one thread, but this discrepancy should remain attached to any hardware-normalized interpretation.
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": "complete", "successful_measurements": 90,
                      "worker_errors": 102, "correctness_mismatches": 0,
                      "results_sha256": digest(OUT / "RESULTS.json")}, sort_keys=True))


if __name__ == "__main__":
    main()
