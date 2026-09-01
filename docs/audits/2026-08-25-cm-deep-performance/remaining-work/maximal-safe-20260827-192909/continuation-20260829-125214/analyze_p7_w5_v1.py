"""Reconcile and analyze the four frozen P7 W5 development shards."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import statistics


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
PACKAGE = ROOT / "docs/research/verification/comparative-p7-w5-development-v1-2026-09-01"
CAMPAIGN_PATH = PACKAGE / "campaign.json"
DEFAULT_OUTPUT = HERE / "P7-W5-FINAL-ANALYSIS.json"
DEFAULT_RUNS = {
    shard: HERE / ("p7-w5-" + shard + "-v1-001")
    for shard in ("p7-ir-a", "p7-ir-b", "p7-relation-a", "p7-relation-b")
}
COMPARISONS = {
    "p7-ir": (
        ("cm-ir-current", "cm-ir-two-memo", "ordered_ir_second_memo"),
        ("cm-raw-flat", "cm-cse-flat", "flat_cse"),
    ),
    "p7-relation": tuple(
        ("cm-dense", arm, arm.removeprefix("cm-"))
        for arm in ("cm-packed-bigint", "cm-packed-words", "cm-no-reinflate", "cm-cse-flat")
    ),
}
METRICS = (
    "task_total_wall_ns",
    "fresh_process_controller_wall_ns",
    "process_tree_peak_rss_bytes",
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantile(values: list[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise ValueError("invalid quantile input")
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    fraction = position - lower
    return float(ordered[lower] * (1 - fraction) + ordered[upper] * fraction)


def absolute_summary(values: list[float]) -> dict:
    if not values or any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("invalid positive metric values")
    return {
        "n": len(values),
        "minimum": min(values),
        "p10": quantile(values, 0.10),
        "median": statistics.median(values),
        "p90": quantile(values, 0.90),
        "p95": quantile(values, 0.95),
        "maximum": max(values),
        "geometric_mean": math.exp(statistics.fmean(math.log(value) for value in values)),
    }


def cluster_bootstrap(case_log_ratios: dict[str, float], *, samples: int = 10_000, seed: int = 731_905) -> dict:
    if not case_log_ratios or samples < 1:
        raise ValueError("invalid cluster bootstrap")
    case_ids = sorted(case_log_ratios)
    values = [case_log_ratios[case_id] for case_id in case_ids]
    if any(not math.isfinite(value) for value in values):
        raise ValueError("invalid log ratio")
    rng = random.Random(seed)
    draws = []
    for _ in range(samples):
        draws.append(math.exp(statistics.fmean(values[rng.randrange(len(values))] for _ in values)))
    estimate = math.exp(statistics.fmean(values))
    return {
        "independent_clusters": len(values),
        "bootstrap_samples": samples,
        "seed": seed,
        "candidate_over_baseline_geometric_mean": estimate,
        "ci95_low": quantile(draws, 0.025),
        "ci95_high": quantile(draws, 0.975),
    }


def paired_summary(rows: list[dict], baseline: str, candidate: str, metric: str) -> dict:
    if metric not in METRICS:
        raise ValueError("unknown W5 metric")
    grouped: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
    origins = {}
    roles = {}
    for row in rows:
        if row["arm"] not in {baseline, candidate}:
            continue
        key = (row["case_id"], row["block"])
        if row["arm"] in grouped[key]:
            raise ValueError("duplicate case/block/arm metric")
        grouped[key][row["arm"]] = float(row[metric])
        origins[row["case_id"]] = row["origin"]
        roles[row["case_id"]] = row["role"]
    ratios = []
    by_case: dict[str, list[float]] = defaultdict(list)
    for (case_id, _block), values in grouped.items():
        if set(values) != {baseline, candidate}:
            raise ValueError("incomplete W5 paired metric")
        ratio = values[candidate] / values[baseline]
        if not math.isfinite(ratio) or ratio <= 0:
            raise ValueError("invalid W5 paired ratio")
        ratios.append(ratio)
        by_case[case_id].append(math.log(ratio))
    case_logs = {case_id: statistics.fmean(values) for case_id, values in by_case.items()}
    result = {
        "baseline": baseline,
        "candidate": candidate,
        "metric": metric,
        "paired_case_blocks": len(ratios),
        "independent_cases": len(case_logs),
        "candidate_over_baseline": absolute_summary(ratios),
        "candidate_lower_count": sum(value < 1 for value in ratios),
        "ties": sum(value == 1 for value in ratios),
        "candidate_higher_count": sum(value > 1 for value in ratios),
        "cluster_bootstrap": cluster_bootstrap(case_logs),
        "by_origin": {},
        "by_role": {},
    }
    for label, mapping in (("by_origin", origins), ("by_role", roles)):
        for stratum in sorted(set(mapping.values())):
            selected = {case_id: value for case_id, value in case_logs.items() if mapping[case_id] == stratum}
            stratum_ratios = [math.exp(value) for value in selected.values()]
            result[label][stratum] = {
                "case_ratio_distribution": absolute_summary(stratum_ratios),
                "cluster_bootstrap": cluster_bootstrap(
                    selected,
                    seed=731_905 + sum(stratum.encode("utf-8")),
                ),
            }
    return result


def terminal_rows(run_root: Path, name: str, campaign_cases: dict[str, dict]) -> tuple[list[dict], dict, dict]:
    evidence = run_root / "evidence/run-output"
    output = evidence / name
    plan = load(output / "plan.json")
    summary = load(output / "summary.json")
    cells = {cell["cell_id"]: cell for cell in plan["cells"]}
    terminal = {}
    for path in sorted((output / "ledger").glob("segment-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record.get("status") != "running":
                terminal[record["cell_id"]] = record
    rows = []
    for cell_id, cell in cells.items():
        record = terminal.get(cell_id)
        if record is None or record.get("status") != "ok" or record.get("result", {}).get("status") != "ok":
            raise RuntimeError("non-ok or missing W5 cell")
        result = record["result"]
        case = campaign_cases[cell["case_id"]]
        rows.append(
            {
                "cell_id": cell_id,
                "case_id": cell["case_id"],
                "cluster_id": cell["cluster_id"],
                "role": cell["role"],
                "origin": case["origin"],
                "kind": case["kind"],
                "block": cell["block"],
                "arm": cell["arm"],
                "conditional_extension": cell["conditional_extension"],
                "task_total_wall_ns": result["timings_ns"]["task_total_wall_ns"],
                "fresh_process_controller_wall_ns": result["timings_ns"]["fresh_process_controller_wall_ns"],
                "process_tree_peak_rss_bytes": result["process_tree_peak_rss_bytes"],
                "worker_pid": result["worker"]["environment"]["pid"],
            }
        )
    if set(terminal) != set(cells) or summary.get("status") != "passed":
        raise RuntimeError("W5 plan/ledger reconciliation mismatch")
    return rows, plan, summary


def analyze(run_paths: dict[str, Path]) -> dict:
    campaign = load(CAMPAIGN_PATH)
    definitions = {row["partition_id"]: row for row in campaign["definitions"]}
    parent = load(
        ROOT / "docs/research/verification/comparative-p6-candidate-v4-2026-08-30/freeze.json"
    )
    cases = {case["case_id"]: case for case in parent["cases"]}
    policies: dict[str, list[dict]] = defaultdict(list)
    diagnostics: dict[str, dict[str, list[dict]]] = defaultdict(dict)
    shards = {}
    all_worker_ids = set()
    for shard_id, run_root in run_paths.items():
        record = load(run_root / "RUN.json")
        if (
            record.get("status") != "complete"
            or record.get("cleanup", {}).get("owned_pod_absent") is not True
            or record.get("evidence", {}).get("verified") is not True
        ):
            raise RuntimeError("W5 shard or cleanup did not pass: " + shard_id)
        primary, plan, summary = terminal_rows(run_root, "primary", cases)
        anchor, anchor_plan, anchor_summary = terminal_rows(run_root, "diagnostic-anchor", cases)
        policy_id = definitions[shard_id]["policy_id"]
        policies[policy_id].extend(primary)
        diagnostics[policy_id][shard_id] = anchor
        worker_ids = {(record["pod_id"], row["worker_pid"]) for row in primary + anchor}
        if all_worker_ids.intersection(worker_ids):
            raise RuntimeError("worker identity reused across W5 shards")
        all_worker_ids.update(worker_ids)
        shards[shard_id] = {
            "pod_id": record["pod_id"],
            "estimated_compute_cost_usd": record.get("estimated_compute_cost_usd"),
            "primary_plan_sha256": plan["plan_sha256"],
            "anchor_plan_sha256": anchor_plan["plan_sha256"],
            "primary_cells": len(primary),
            "diagnostic_cells": len(anchor),
            "primary_summary_sha256": hashlib.sha256(
                json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "anchor_summary_sha256": hashlib.sha256(
                json.dumps(anchor_summary, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }

    output = {
        "schema": "cm-comparative-p7-w5-final-analysis/v1",
        "campaign_sha256": sha256(CAMPAIGN_PATH),
        "performance_measurement": True,
        "principal_p7_result": True,
        "confirmation_claim_permitted": False,
        "external_method_comparison": False,
        "parent_eligible_cases": 58,
        "principal_executable_cases": 57,
        "typed_retained_exclusions": campaign["typed_retained_exclusions"],
        "completion_frontier": {
            "parent_cases": 58,
            "completed_cases": 57,
            "typed_feasibility_exclusions": 1,
            "completed_fraction": 57 / 58,
        },
        "shards": shards,
        "fresh_worker_identities": len(all_worker_ids),
        "policies": {},
        "diagnostic_anchors": {},
    }
    for policy_id, rows in policies.items():
        specification = [row for row in campaign["definitions"] if row["policy_id"] == policy_id and row["kind"] == "primary"]
        expected = sum(row["planned_cells"] for row in specification)
        expected_cases = set().union(*(set(row["case_ids"]) for row in specification))
        if len(rows) != expected or len({row["cell_id"] for row in rows}) != expected:
            raise RuntimeError("combined W5 policy cell coverage mismatch")
        if {row["case_id"] for row in rows} != expected_cases or len(expected_cases) != 57:
            raise RuntimeError("combined W5 policy case coverage mismatch")
        arms = sorted({row["arm"] for row in rows})
        policy = {
            "cells": len(rows),
            "cases": len(expected_cases),
            "arms": arms,
            "by_arm": {},
            "comparisons": {},
        }
        for arm in arms:
            selected = [row for row in rows if row["arm"] == arm]
            policy["by_arm"][arm] = {
                metric: absolute_summary([float(row[metric]) for row in selected])
                for metric in METRICS
            }
        for baseline, candidate, label in COMPARISONS[policy_id]:
            policy["comparisons"][label] = {
                metric: paired_summary(rows, baseline, candidate, metric)
                for metric in METRICS
            }
        output["policies"][policy_id] = policy

        anchors = diagnostics[policy_id]
        if len(anchors) != 2:
            raise RuntimeError("W5 policy does not have two diagnostic allocations")
        first, second = sorted(anchors)
        first_rows = {(row["case_id"], row["block"], row["arm"]): row for row in anchors[first]}
        second_rows = {(row["case_id"], row["block"], row["arm"]): row for row in anchors[second]}
        if set(first_rows) != set(second_rows):
            raise RuntimeError("W5 diagnostic anchor grid mismatch")
        drift = {}
        for metric in METRICS:
            ratios = [second_rows[key][metric] / first_rows[key][metric] for key in first_rows]
            drift[metric] = {
                "second_over_first": absolute_summary(ratios),
                "paired_cells": len(ratios),
            }
        output["diagnostic_anchors"][policy_id] = {
            "first_shard": first,
            "second_shard": second,
            "diagnostic_only": True,
            "independent_formula_count": 0,
            "drift": drift,
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    for shard in DEFAULT_RUNS:
        parser.add_argument("--" + shard, type=Path, default=DEFAULT_RUNS[shard])
    args = parser.parse_args()
    run_paths = {shard: getattr(args, shard.replace("-", "_")) for shard in DEFAULT_RUNS}
    if args.output.exists():
        raise FileExistsError(args.output)
    result = analyze(run_paths)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
