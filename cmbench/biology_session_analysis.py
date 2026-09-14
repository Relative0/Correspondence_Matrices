"""Descriptive, ancestry-aware analysis of local biology session measurements.

This module does not infer a held-out experiment from row labels, or turn
repeated measurements into independent models. It never modifies input rows.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math
import re
import statistics

from cmbench.benchmark_contracts import validate_result


SCHEMA = "cm-biology-session-analysis/v1"
_PHASES = ("cold_construction", "preparation", "warm_queries", "total_session")
_BASELINE = "raw_factorized"
_CANDIDATE = "prepared_cm_factorized"
_IDENTITY = ("input_sha256", "query_schedule_sha256", "perturbation_semantics",
             "environment_id", "source_manifest_sha256", "partition", "cluster_id")


def _geomean(values):
    return math.exp(statistics.mean(math.log(x) for x in values)) if values else None


def _key(row):
    return (row["instance_id"], row["queries"], row["repetition"], row["arm"],
            row.get("reuse_mode", "retained"), row.get("representation_mode", "matched"))


def _reference(row):
    return dict(zip(("instance_id", "queries", "repetition", "arm", "reuse_mode",
                     "representation_mode"), _key(row)))


def _output_disagreements(left, right):
    differences = []
    for index, (a, b) in enumerate(zip(left["outputs"], right["outputs"])):
        if a["satisfiable"] != b["satisfiable"]:
            differences.append({"query_index": index, "field": "satisfiable",
                                "left": a["satisfiable"], "right": b["satisfiable"]})
        # A SAT-only control has no count; its decision still participates.
        if a.get("count") is not None and b.get("count") is not None and a["count"] != b["count"]:
            differences.append({"query_index": index, "field": "count",
                                "left": a["count"], "right": b["count"]})
    return differences


def _plan_comparison(baseline, candidate):
    before, after = baseline.get("query_plan_sha256"), candidate.get("query_plan_sha256")
    if before is None or after is None:
        return "unresolved_missing_plan_identity"
    if before != after:
        return "preprocessing_topology_confounded"
    return "identical_normalized_plans_same_declared_evaluator"


def _summarize(instances):
    clusters = defaultdict(list)
    for instance in instances:
        clusters[instance["cluster_id"]].append(instance["geometric_mean_ratio"])
    family_ratios = {name: _geomean(values) for name, values in sorted(clusters.items())}
    values = list(family_ratios.values())
    leave_one_out = {name: _geomean([v for k, v in family_ratios.items() if k != name])
                     for name in family_ratios} if len(values) > 1 else {}
    baseline_total = sum(x["mean_timing_seconds"]["baseline"]["total_session"] for x in instances)
    return {
        "paired_instances": len(instances),
        "measurement_pairs": sum(x["paired_repetitions"] for x in instances),
        "independent_cluster_count_assumption": len(clusters),
        "equal_instance_geometric_mean_ratio": _geomean([x["geometric_mean_ratio"] for x in instances]),
        "equal_family_geometric_mean_ratio": _geomean(values),
        "median_instance_ratio": statistics.median(x["geometric_mean_ratio"] for x in instances) if instances else None,
        "ratio_sum_instance_mean_total_cost": sum(x["mean_timing_seconds"]["candidate"]["total_session"] for x in instances) / baseline_total if baseline_total else None,
        "family_ratios": family_ratios,
        "leave_one_family_out": leave_one_out,
        "leave_one_family_out_range": [min(leave_one_out.values()), max(leave_one_out.values())] if leave_one_out else None,
        "phase_totals_seconds": {arm: {phase: sum(x["mean_timing_seconds"][arm][phase] for x in instances)
                                       for phase in _PHASES} for arm in ("baseline", "candidate")},
        "confidence_interval_95": None,
        "uncertainty_status": "descriptive pilot; no sampling-based confidence claim; repeats are measurements, not independent models",
        "single_repeat_instances": sum(x["paired_repetitions"] == 1 for x in instances),
    }


def analyze_sessions(rows: list[dict]) -> dict:
    """Validate full future-result rows and compare matched factorized sessions.

    The returned ``comparisons`` list separates q, partition, reuse mode and
    candidate representation mode. Canonical CM is compared with the matched
    raw baseline, retaining any plan/topology confound. ``failures`` preserves
    unsuccessful rows; ``unpaired_or_failed`` explains exclusions from paired
    timing. Witness values may differ; their validation remains the producer's
    responsibility. ``correctness_mismatches`` compares exact counts and SAT
    decisions across all successful controls with identical semantic identity.
    """
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    indexed, identity = {}, {}
    semantic_groups = defaultdict(list)
    for row in rows:
        validate_result(row)
        if row.get("reuse_mode", "retained") not in {"retained", "rebuild"}:
            raise ValueError("unknown reuse_mode")
        if row.get("representation_mode", "matched") not in {"matched", "cm_canonical"}:
            raise ValueError("unknown representation_mode")
        plans = row.get("query_plan_sha256")
        if plans is not None and (not isinstance(plans, list) or len(plans) != row["queries"] or
                                  any(not isinstance(x, str) or not re.fullmatch(r"[0-9a-f]{64}", x) for x in plans)):
            raise ValueError("query_plan_sha256 must contain one ordered SHA-256 per query")
        key = _key(row)
        if key in indexed:
            raise ValueError(f"duplicate session row: {key}")
        indexed[key] = row
        known = (row["cluster_id"], row["partition"], row["input_sha256"])
        if row["instance_id"] in identity and identity[row["instance_id"]] != known:
            raise ValueError("instance has conflicting cluster, partition or input identity")
        identity[row["instance_id"]] = known
        if row["status"] == "ok":
            semantic = (row["instance_id"], row["queries"], row["repetition"],
                        row["query_schedule_sha256"], row["perturbation_semantics"])
            semantic_groups[semantic].append(row)

    mismatches, invalid_keys = [], set()
    for _, group in sorted(semantic_groups.items()):
        # Compare every successful row against a count-bearing reference where
        # possible, so a SAT-only reference cannot mask count disagreements.
        group = sorted(group, key=lambda r: (r["outputs"][0].get("count") is None, _key(r)))
        reference = group[0]
        for other in group[1:]:
            differences = _output_disagreements(reference, other)
            if differences:
                mismatches.append({"left": _reference(reference), "right": _reference(other),
                                   "differences": differences})
                invalid_keys.update(_key(r) for r in group)

    failures = [{**_reference(row), "status": row["status"], "failure_reason": row["failure_reason"],
                 "timing_seconds": dict(row["timing_seconds"])} for _, row in sorted(indexed.items()) if row["status"] != "ok"]
    groups, excluded, used_baselines = defaultdict(list), [], set()
    for _, row in sorted(indexed.items()):
        if row["arm"] != _CANDIDATE:
            continue
        key = _key(row)
        baseline_key = (key[0], key[1], key[2], _BASELINE, key[4], "matched")
        baseline = indexed.get(baseline_key)
        group_key = (row["queries"], row["partition"], key[4], key[5])
        groups[group_key]  # Preserve a comparison even when every pair fails.
        reason = None
        if baseline is None:
            reason = "missing_raw_factorized_baseline"
        else:
            used_baselines.add(baseline_key)
            if row["status"] != "ok" or baseline["status"] != "ok":
                reason = "non_successful_arm"
            elif any(row[field] != baseline[field] for field in _IDENTITY):
                reason = "unmatched_semantic_or_environment_identity"
            elif key in invalid_keys or baseline_key in invalid_keys:
                reason = "correctness_mismatch"
            elif min(row["timing_seconds"]["total_session"], baseline["timing_seconds"]["total_session"]) <= 0:
                reason = "nonpositive_total_session"
        if reason:
            excluded.append({"candidate": _reference(row), "baseline": _reference(baseline) if baseline else None,
                             "reason": reason, "candidate_status": row["status"],
                             "baseline_status": baseline["status"] if baseline else None})
            continue
        groups[group_key].append({"instance_id": row["instance_id"], "cluster_id": row["cluster_id"],
                                  "repetition": row["repetition"],
                                  "ratio": row["timing_seconds"]["total_session"] / baseline["timing_seconds"]["total_session"],
                                  "baseline": baseline, "candidate": row,
                                  "attribution": _plan_comparison(baseline, row)})
    for key, row in sorted(indexed.items()):
        if row["arm"] == _BASELINE and key not in used_baselines:
            excluded.append({"baseline": _reference(row), "candidate": None,
                             "reason": "missing_prepared_cm_candidate", "baseline_status": row["status"], "candidate_status": None})

    comparisons = []
    for (q, partition, reuse, representation), pairs in sorted(groups.items()):
        by_instance = defaultdict(list)
        for pair in pairs:
            by_instance[pair["instance_id"]].append(pair)
        instances = []
        for name, measurements in sorted(by_instance.items()):
            measurements.sort(key=lambda x: x["repetition"])
            ratios = [x["ratio"] for x in measurements]
            times = {arm: {phase: statistics.mean(x[arm]["timing_seconds"][phase] for x in measurements)
                           for phase in _PHASES} for arm in ("baseline", "candidate")}
            instances.append({"instance_id": name, "cluster_id": measurements[0]["cluster_id"],
                              "paired_repetitions": len(measurements),
                              "repetition_ratios": [{"repetition": x["repetition"], "ratio": x["ratio"], "attribution": x["attribution"]} for x in measurements],
                              "geometric_mean_ratio": _geomean(ratios), "ratio_range": [min(ratios), max(ratios)],
                              "ratio_mean_total_cost": times["candidate"]["total_session"] / times["baseline"]["total_session"],
                              "mean_timing_seconds": times,
                              "plan_attribution_counts": dict(sorted(Counter(x["attribution"] for x in measurements).items()))})
        comparisons.append({"queries": q, "partition": partition, "reuse_mode": reuse,
                            "representation_mode": representation, "baseline_arm": _BASELINE,
                            "candidate_arm": _CANDIDATE, "instances": instances,
                            "plan_attribution_counts": dict(sorted(Counter(x["attribution"] for x in pairs).items())),
                            "summary": _summarize(instances)})
    return {"schema": SCHEMA, "row_count": len(rows), "instance_count": len(identity),
            "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
            "ratio_definition": "prepared CM / raw factorized total session time; below one favors prepared CM",
            "correctness_mismatches": mismatches, "failures": failures,
            "unpaired_or_failed": excluded, "comparisons": comparisons,
            "heldout_acceptance": {"eligible": False, "passed": None,
                "reason": "Descriptive local session analysis; exposed/pilot inputs and row partition labels do not establish an independently frozen held-out study."},
            "attribution_limit": "Identical normalized plans identify a matched declared evaluator comparison, not a demonstrated CM-specific effect. Different plans confound preprocessing/topology. No performance gate or confidence claim is made."}
