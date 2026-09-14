"""Read frozen timing evidence; write only this successor audit's derived JSON.

Python standard library only. Never runs a benchmark or changes old evidence.
Retained-root fallbacks are explicit because several original raw files/reports
were not included in the consolidated checkout.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import re
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_RETAINED = Path("C:/Users/brian/Documents/CM_Computation")


def geomean(values):
    return math.exp(statistics.mean(math.log(x) for x in values)) if values else None


def percentile(values, q):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = int(pos)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (pos - low)


def aggregate(cases):
    complete = [x for x in cases if x["paired_ratios"]]
    groups = defaultdict(list)
    for case in complete:
        groups[case["cluster"]].append(case["geometric_mean_ratio"])
    cluster_values = [geomean(v) for _, v in sorted(groups.items())]
    rng = random.Random(20260914)
    draws = [geomean(rng.choices(cluster_values, k=len(cluster_values))) for _ in range(10000)] if len(groups) >= 2 else []
    vals = [x["geometric_mean_ratio"] for x in complete]
    return {
        "instances": len(cases), "paired_instances": len(complete),
        "measurement_pairs": sum(len(x["paired_ratios"]) for x in complete),
        "clusters": {k: {"instances": len(v), "geometric_mean_ratio": geomean(v)} for k, v in sorted(groups.items())},
        "equal_instance_geometric_mean": geomean(vals),
        "geometric_mean_instance_ratio_medians": geomean([x["ratio_medians"] for x in complete]),
        "median_instance_geometric_ratio": statistics.median(vals) if vals else None,
        "ratio_sum_instance_median_times": sum(x["candidate_median"] for x in complete) / sum(x["baseline_median"] for x in complete) if complete else None,
        "equal_cluster_geometric_mean": geomean(cluster_values),
        "cluster_percentile_bootstrap_95": [percentile(draws, .025), percentile(draws, .975)] if draws else None,
        "interval_status": "descriptive resampling of exposed clusters; not population coverage or held-out acceptance" if draws else "not estimable: fewer than two clusters",
        "few_cluster_warning": len(groups) < 5,
        "leave_one_cluster_out_range": [min(geomean(cluster_values[:i] + cluster_values[i+1:]) for i in range(len(cluster_values))), max(geomean(cluster_values[:i] + cluster_values[i+1:]) for i in range(len(cluster_values)))] if len(groups) > 1 else None,
        "heldout_gate": {"applicable": False, "reason": "Previously exposed inputs; no matched CM attribution treatment or independently frozen family holdout in this reanalysis."},
    }


class Audit:
    def __init__(self, retained):
        self.retained = retained
        self.sources = {}

    def locate(self, relative):
        path = ROOT / relative
        if not path.is_file():
            path = self.retained / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        key = relative if path.is_relative_to(ROOT) else str(path).replace("\\", "/")
        self.sources[key] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size,
                             "custody": "consolidated checkout" if path.is_relative_to(ROOT) else "retained original checkout; read-only fallback"}
        return path

    def read(self, relative):
        return json.loads(self.locate(relative).read_text(encoding="utf-8-sig"))

    def rows(self, relative):
        return [json.loads(x) for x in self.locate(relative).read_text(encoding="utf-8-sig").splitlines() if x.strip()]


def compare(rows, baseline, candidate, cluster, metric="total_ns"):
    grouped = defaultdict(dict)
    for row in rows:
        method = row.get("method", row.get("arm"))
        if method in (baseline, candidate):
            key = (row["case"], row.get("q", 1), row.get("repeat", 0))
            if method in grouped[key]:
                raise ValueError(f"duplicate measurement {key} {method}")
            grouped[key][method] = row
    cases = defaultdict(list)
    for (name, q, repeat), methods in sorted(grouped.items()):
        cases[(name, q)].append((repeat, methods))
    records = []
    for (name, q), runs in sorted(cases.items()):
        ratios, bt, ct, failures = [], [], [], []
        for repeat, methods in runs:
            b, c = methods.get(baseline), methods.get(candidate)
            valid = b and c and b.get("status", "complete") in ("ok", "complete") and c.get("status", "complete") in ("ok", "complete") and b.get(metric, 0) > 0 and c.get(metric, 0) > 0
            if valid:
                ratios.append(c[metric] / b[metric]); bt.append(b[metric]); ct.append(c[metric])
            else:
                failures.append({"repeat": repeat, "baseline": None if b is None else b.get("status", "metric_missing"), "candidate": None if c is None else c.get("status", "metric_missing")})
        records.append({"case": name, "q": q, "cluster": cluster(name), "paired_ratios": ratios,
                        "geometric_mean_ratio": geomean(ratios), "baseline_median": statistics.median(bt) if bt else None,
                        "candidate_median": statistics.median(ct) if ct else None,
                        "ratio_medians": statistics.median(ct) / statistics.median(bt) if bt else None,
                        "paired_range": [min(ratios), max(ratios)] if ratios else None, "unpaired_or_failed": failures})
    by_q = {str(q): aggregate([r for r in records if r["q"] == q]) for q in sorted({r["q"] for r in records})}
    return {"baseline": baseline, "candidate": candidate, "metric": metric, "ratio_definition": "candidate / baseline; below one favors candidate", "cases": records, "by_q": by_q}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retained-root", type=Path, default=DEFAULT_RETAINED)
    args = parser.parse_args()
    audit = Audit(args.retained_root)
    campaign = "docs/audits/2026-09-13-cm-benchmark-campaign/"
    successor = campaign + "runpod-successor-001/evidence/core-screen/"
    raw = audit.rows(successor + "ledger.jsonl")
    plan = audit.read(successor + "PLAN.json")
    published = audit.read(campaign + "successor-results-analysis-001/RESULTS.json")
    assert len(raw) == 108 and Counter(r["status"] for r in raw) == {"ok": 105, "timeout": 3}
    assert len({r["cell_id"] for r in raw}) == 108
    family = {}
    corpus_path = HERE / "BIOLOGY_CORPUS_AUDIT.json"
    if corpus_path.exists():
        corpus = audit.read(str(corpus_path.relative_to(ROOT)).replace("\\", "/"))
        # Explicit stable mapping supplied by the corpus audit; absent mappings
        # conservatively collapse to one source-corpus cluster.
        for model in corpus.get("models", []):
            family[model.get("sha256", model.get("input_sha256"))] = model.get("independence_cluster", model.get("family_cluster", model.get("cluster_id", "biodivine-source-corpus")))
    case_meta = {x["case_id"]: x for x in plan["cases"]}
    input_freeze = audit.read(campaign + "input-freeze-009/INPUT_FREEZE.json")
    count_provenance = {x["sha256"]: x for x in input_freeze["counting"]["rows"]}
    converted = [dict(r, case=r["case_id"], repeat=r["repetition"], total_ns=r.get("wall_ns"), parent_ns=r["parent_wall_ns"]) for r in raw]
    successor_results = {}
    for lane, b, c in [("biology_fixed_points", "bnet_cm_scalar", "biodivine_aeon"), ("exact_count", "ganak", "d4")]:
        selected = [r for r in converted if r["lane"] == lane]
        def cluster(name):
            return family.get(case_meta[name]["input_sha256"], "biodivine-source-corpus") if lane == "biology_fixed_points" else "cachet-plan-recognition"
        result = compare(selected, b, c, cluster)
        result["parent_lifecycle_sensitivity"] = compare(selected, b, c, cluster, "parent_ns")
        result["instance_as_cluster_sensitivity"] = aggregate([dict(x, cluster=x["case"]) for x in result["cases"]])
        result["instance_as_cluster_sensitivity"]["assumption"] = "Optimistic sensitivity only; treating related instances as independent is not justified."
        for item in result["cases"]:
            item["input_sha256"] = case_meta[item["case"]]["input_sha256"]
            item["input_path_in_frozen_plan"] = case_meta[item["case"]]["path"]
            if lane == "exact_count":
                provenance = count_provenance[item["input_sha256"]]
                assert "/cachet-plan-recognition/" in provenance["source_path"]
                item["source_provenance"] = provenance
                name = Path(provenance["source_path"]).name
                item["named_subfamily"] = "step" if "step" in name else name.split("-")[0]
        if lane == "exact_count":
            result["named_subfamily_sensitivity"] = aggregate([dict(x, cluster=x["named_subfamily"]) for x in result["cases"]])
            result["named_subfamily_sensitivity"]["assumption"] = "Three filename/provenance subfamilies: step, tire, log. Their independent generation is not established; primary analysis clusters all under cachet-plan-recognition."
        result["censoring"] = [{"case": r["case"], "repeat": r["repeat"], "arm": r["arm"], "status": r["status"], "observed_parent_seconds": r["parent_ns"] / 1e9, "reason": r.get("reason")} for r in selected if r["status"] != "ok"]
        # All comparator values present in a case must agree. The d4-only case
        # is repeated-output consistency, not a second-counter agreement.
        for name in {r["case"] for r in selected}:
            assert len({r["value"] for r in selected if r["case"] == name and r["status"] == "ok"}) == 1
        actual = geomean([v for x in result["cases"] for v in x["paired_ratios"]])
        assert math.isclose(actual, published["lane_results"][lane]["geometric_mean_ratio"], rel_tol=1e-12)
        if lane == "exact_count":
            censored = next(x for x in result["cases"] if not x["paired_ratios"])
            times = [r["wall_ns"] / 1e9 for r in selected if r["case"] == censored["case"] and r["status"] == "ok"]
            result["timeout_sensitivity"] = {"deadline_seconds": 60, "case": censored["case"],
                "d4_seconds": times, "d4_over_60_second_budget": [x / 60 for x in times],
                "interpretation": "Runtime-threshold sensitivity only. Ganak completion time is right-censored; 60 seconds is not an observed completed time. No finite ratio is imputed in summaries.",
                "unconditional_population_ratio": None}
        successor_results[lane] = result
    history = {}
    prior = audit.rows(campaign + "runpod-results-002/evidence/core-screen/ledger.jsonl")
    prior = [dict(r, case=r["case_id"], repeat=r["repetition"], total_ns=r.get("wall_ns")) for r in prior]
    affine = [r for r in prior if r["lane"] == "affine_solution_count"]
    affine_arms = sorted({r["arm"] for r in affine})
    assert len(affine_arms) == 2
    history["prior_affine_screen"] = compare(affine, affine_arms[0], affine_arms[1], lambda n: "affine-screen-source-family-unresolved")
    history["prior_screen_statuses"] = {lane: dict(Counter(r["status"] for r in prior if r["lane"] == lane)) for lane in sorted({r["lane"] for r in prior})}
    base = "docs/audits/2026-09-11-cm-"
    rows = audit.rows(base + "performance/confirmation_raw.jsonl")
    history["periodic_mask"] = {}
    for backend in sorted({r["backend"] for r in rows}):
        for restricted in (False, True):
            selected = [r for r in rows if r["backend"] == backend and r["restricted"] == restricted]
            if selected:
                history["periodic_mask"][f"{backend}:restricted={restricted}"] = compare(selected, "baseline", "candidate", lambda n: "synthetic-mask-generator")
    panels = audit.rows(base + "continuation/packed-panels/confirmation-RAW.jsonl")
    history["packed_continuation"] = [compare(panels, b, c, lambda n: "synthetic-count" if "count" in n else "synthetic-stream" if "stream" in n else "synthetic-cache") for b, c in [("named_lru", "positional"), ("cse_flat", "independent_expr"), ("cse_flat", "independent_cm"), ("complete", "stream_16"), ("complete", "stream_12"), ("complete", "stream_8")]]
    scalar = audit.rows(base + "scalar-research/attempt-001/evidence/scalar/RAW.jsonl")
    history["factorized_affine"] = [compare(scalar, b, c, lambda n: "GNU-Radio-LDPC" if n.startswith("n_") else "synthetic-factor-generator") for b, c in [("cse", "factor_expr"), ("cse", "factor_cm"), ("factor_expr", "factor_cm"), ("cudd_natural", "factor_expr"), ("flint", "affine_rows"), ("affine_rows", "affine_cm")]]
    binding = audit.rows(base + "scalar-research/attempt-003/evidence/binding/RAW.jsonl")
    history["affine_binding"] = [compare(binding, b, c, lambda n: "GNU-Radio-LDPC" if n.startswith("n_") else "synthetic-binding-generator") for b, c in [("rows_legacy", "rows_indexed"), ("m4ri_legacy", "m4ri_indexed"), ("m4ri_indexed", "rows_indexed")]]
    m4ri = audit.rows(base + "scalar-research/attempt-002/evidence/m4ri/RAW.jsonl")
    history["affine_m4ri"] = {"raw_methods": sorted({r["method"] for r in m4ri}), "comparisons": [compare(m4ri, b, c, lambda n: "GNU-Radio-LDPC") for b, c in itertools.combinations(sorted({r["method"] for r in m4ri}), 2)]}
    native = audit.rows(base + "continuation/native-run/RAW.jsonl")
    native = [dict(r, case=r["case_id"], q=r["query_count"], repeat=r["block"], total_ns=r["timings_ns"]["accounted_total_ns"]) for r in native]
    history["native_batch"] = compare(native, "native_scalar_v1", "native_batch_v1", lambda n: "native-balanced-tree-generator" if "balanced-tree" in n else "native-layered-sharing-generator")
    # Every array fixture is retained, including the entire-refusal fixtures.
    bucket_dir = "docs/audits/2026-09-11-cm-bucket-counts/attempt-002/evidence/bucket-numpy"
    location = ROOT / bucket_dir
    if not location.exists():
        location = args.retained_root / bucket_dir
    bucket = []
    for path in sorted(location.glob("*/RAW.jsonl")):
        bucket.extend(audit.rows(bucket_dir + "/" + path.parent.name + "/RAW.jsonl"))
    assert bucket, "No array raw evidence found"
    def bucket_cluster(name):
        return name if name.startswith("model-") else "synthetic-bucket-generator"
    history["bucket_arrays"] = [compare(bucket, b, c, bucket_cluster) for b, c in [("bucket_min_fill", "numpy_min_fill"), ("numpy_min_fill", "numpy_cm"), ("cudd_natural", "numpy_min_fill"), ("cudd_dynamic", "numpy_min_fill")]]
    result = {"schema": "cm-attribution-statistical-reanalysis/v1", "seed": 20260914, "bootstrap_draws": 10000,
              "ratio_convention": "candidate / baseline; lower is better", "sources": audit.sources,
              "successor": successor_results, "historical": history,
              "historical_status_counts": {"array_raw": dict(Counter(r.get("status", "complete") for r in bucket)), "native_batch": dict(Counter(r["status"] for r in native))},
              "limitations": ["Finite exposed convenience cohorts; no population sampling design.", "Clusters are conservative ancestry assumptions, not verified independent random draws.", "Repetitions estimate repeatability only. No bootstrap over pooled repetition rows is presented as dataset uncertainty.", "Historical original-path fallbacks are hash-bound here but require the retained checkout to reproduce.", "Runtime, parent lifecycle, warm batches, traced allocations and OS high-water memory are distinct estimands.", "No timing result here qualifies as an attribution-isolated CM effect or a prospective held-out biology gate."]}
    (HERE / "STATISTICAL_REANALYSIS.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(audit.sources), "successor": {k: v["by_q"] for k, v in successor_results.items()}, "historical_panels": list(history)}, indent=2))


if __name__ == "__main__":
    main()
