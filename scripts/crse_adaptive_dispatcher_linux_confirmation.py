"""Bounded Linux timing confirmation of the frozen C12 adaptive dispatcher."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_from_json
from cmbench.recognition.adaptive_exact_dispatcher import adaptive_exact_partition
from cmbench.recognition.natural_decomposition import partition_witness
from cmbench.recognition.portfolio import reference_bits
from cmbench.recognition.source_anf_hybrid import ProductCache, source_packed_partition
from cmbench.recognition.source_interaction import source_exact_partition
from cmbench.recognition.staged_exact_dispatcher import staged_exact_partition

SCHEMA = "crse-adaptive-dispatcher-linux-confirmation/v1"
MEASUREMENT_SCHEMA = "crse-adaptive-dispatcher-linux-measurement/v1"
METHODS = ("set_source_anf", "cached_packed_source_anf", "staged_restart", "adaptive_one_pass")
SPLITS = ("sealed_a", "sealed_b")
POLICY_BUDGET = 4096
EXPECTED_DATASET_SHA256 = "f026a896955540953edcf5890c13a31b35a5f76539eb8b63f98cbd304fa297b4"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(fraction * len(ordered) + .999999) - 1))]


def solve(method: str, row: dict, cache: ProductCache | None):
    document, n_vars = row["expression_v2"], row["n_vars"]
    if method == "set_source_anf":
        partition = source_exact_partition(document, n_vars)
        selected = method
    elif method == "cached_packed_source_anf":
        partition, _stats = source_packed_partition(document, n_vars, cache=cache)
        selected = method
    elif method == "staged_restart":
        partition, selected, _set, _packed = staged_exact_partition(
            document, n_vars, product_pair_budget=POLICY_BUDGET, cache=cache)
    elif method == "adaptive_one_pass":
        partition, selected, _stats = adaptive_exact_partition(
            document, n_vars, product_pair_budget=POLICY_BUDGET, cache=cache)
    else:
        raise ValueError("unknown Linux confirmation method")
    return partition, selected


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=16)
    args = parser.parse_args(argv)
    if args.repetitions != 16:
        raise ValueError("Linux confirmation requires 16 balanced repetitions")
    if sha(args.dataset) != EXPECTED_DATASET_SHA256:
        raise ValueError("changed frozen C12 dataset")
    documents = json.loads(args.dataset.read_text(encoding="utf-8"))
    if len(documents) != 40 or Counter((row["split"], row["label"]) for row in documents) != Counter({
            (split, label): 10 for split in SPLITS for label in (0, 1)}):
        raise ValueError("invalid balanced C12 dataset")
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    measurements = []
    for split in SPLITS:
        rows = [row for row in documents if row["split"] == split]
        for repetition in range(args.repetitions):
            order = METHODS[repetition % len(METHODS):] + METHODS[:repetition % len(METHODS)]
            for method in order:
                cache = ProductCache(1024) if method != "set_source_anf" else None
                for row in rows:
                    solve_started = time.perf_counter_ns()
                    partition, selected = solve(method, row, cache)
                    solve_ns = time.perf_counter_ns() - solve_started
                    check_started = time.perf_counter_ns()
                    bits = reference_bits(expr_from_json(row["expression_v2"]), row["n_vars"])
                    witness = partition_witness(bits, row["n_vars"], partition) if partition is not None else None
                    canonical = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
                    predicted = int(partition is not None)
                    exact_check_ns = time.perf_counter_ns() - check_started
                    measurements.append({"schema": MEASUREMENT_SCHEMA, "repetition": repetition,
                        "method": method, "split": split, "case_id": row["case_id"],
                        "n_vars": row["n_vars"], "label": row["label"], "selected_arm": selected,
                        "predicted": predicted, "accepted": partition is not None and witness is not None,
                        "row_variables": list(partition) if partition is not None else None,
                        "canonical_partition_match": partition == canonical,
                        "semantic_mismatch": bool(partition is not None and witness is not None and not row["label"]),
                        "solve_ns": solve_ns, "exact_check_ns": exact_check_ns,
                        "total_ns": solve_ns + exact_check_ns})
    grouped = defaultdict(list)
    for row in measurements:
        grouped[(row["method"], row["split"], row["case_id"])].append(row)
    per_case = []
    for (method, split, case_id), values in sorted(grouped.items()):
        first = values[0]
        for field in ("selected_arm", "predicted", "accepted", "row_variables",
                      "canonical_partition_match", "semantic_mismatch"):
            if any(row[field] != first[field] for row in values[1:]):
                raise ValueError("nondeterministic Linux semantic result")
        per_case.append({"method": method, "split": split, "case_id": case_id,
            "n_vars": first["n_vars"], "label": first["label"], "selected_arm": first["selected_arm"],
            "predicted": first["predicted"], "accepted": first["accepted"],
            "row_variables": first["row_variables"],
            "canonical_partition_match": first["canonical_partition_match"],
            "semantic_mismatch": first["semantic_mismatch"],
            "median_solve_ns": int(statistics.median(row["solve_ns"] for row in values)),
            "median_exact_check_ns": int(statistics.median(row["exact_check_ns"] for row in values)),
            "median_total_ns": int(statistics.median(row["total_ns"] for row in values))})
    method_summary, split_summary = {}, {}
    for method in METHODS:
        for split in SPLITS:
            values = [row for row in per_case if row["method"] == method and row["split"] == split]
            totals = [row["median_total_ns"] for row in values]
            method_summary[f"{method}/{split}"] = {"cases": len(values),
                "sequence_total_ns": sum(totals), "median_total_ns": statistics.median(totals),
                "p95_total_ns": percentile(totals, .95), "maximum_total_ns": max(totals),
                "selection_counts": dict(sorted(Counter(row["selected_arm"] for row in values).items()))}
    for split in SPLITS:
        fixed = {method: method_summary[f"{method}/{split}"]["sequence_total_ns"]
                 for method in ("set_source_anf", "cached_packed_source_anf")}
        best = min(fixed, key=fixed.get)
        adaptive = method_summary[f"adaptive_one_pass/{split}"]
        staged = method_summary[f"staged_restart/{split}"]
        split_summary[split] = {"best_fixed_arm": best, "best_fixed_total_ns": fixed[best],
            "adaptive_total_ns": adaptive["sequence_total_ns"],
            "adaptive_speedup_over_best_fixed": fixed[best] / adaptive["sequence_total_ns"],
            "adaptive_p95_speedup_over_set": method_summary[f"set_source_anf/{split}"]["p95_total_ns"] / adaptive["p95_total_ns"],
            "adaptive_speedup_over_restart": staged["sequence_total_ns"] / adaptive["sequence_total_ns"],
            "adaptive_selection_counts": adaptive["selection_counts"]}
    exact = all(row["predicted"] == row["label"] and row["canonical_partition_match"]
                and not row["semantic_mismatch"] for row in measurements)
    no_regret = all(split_summary[split]["adaptive_speedup_over_best_fixed"] >= 1 / 1.05
                    for split in SPLITS)
    summary = {"schema": SCHEMA, "status": "complete", "scientific_scope":
        "second-machine timing of the frozen robust one-pass policy on unchanged C12",
        "input": {"dataset_sha256": EXPECTED_DATASET_SHA256, "training_use": False,
                  "source_commit": documents[0]["source_commit"]},
        "config": {"cases": 40, "repetitions": args.repetitions, "cpu_threads": 1,
                   "cache_capacity": 1024, "methods": list(METHODS),
                   "product_pair_budget": POLICY_BUDGET},
        "runtime": {"platform": platform.platform(), "python": sys.version.split()[0]},
        "wall_seconds": time.perf_counter() - started, "method_summary": method_summary,
        "split_summary": split_summary, "semantic_mismatches": sum(row["semantic_mismatch"] for row in measurements),
        "criteria": {"exact": exact, "no_material_regret": no_regret,
                     "second_machine_promotion": exact and no_regret}}
    measurements_path = args.output / "measurements.jsonl"
    measurements_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in measurements), encoding="utf-8")
    (args.output / "per_case.json").write_text(json.dumps(per_case, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = ("measurements.jsonl", "per_case.json", "summary.json")
    (args.output / "manifest.json").write_text(json.dumps({"schema": "crse-adaptive-dispatcher-linux-artifacts/v1",
        "files_sha256": {name: sha(args.output / name) for name in files}}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "criteria": summary["criteria"],
                      "split_summary": split_summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

