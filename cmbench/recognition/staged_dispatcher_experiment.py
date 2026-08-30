"""Validation-frozen evaluation of the exact set-first product-budget guard."""
from __future__ import annotations

import json
import platform
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .exact_dispatcher import ARMS, canonical_sha256
from .exact_dispatcher_experiment import (
    Budget, DEFAULT_C6_RUN, DEFAULT_C7_RUN, _solve, relative, verify_retained_c7,
)
from .natural_decomposition import partition_witness
from .natural_source_anf_experiment import percentile, sha
from .source_anf_hybrid import ProductCache
from .staged_exact_dispatcher import staged_exact_partition
from .yosys_human_decomposition_data import make_yosys_human_documents
from .yosys_source_anf_experiment import document_truth_bits, verify_retained_c6

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA = "crse-staged-exact-dispatcher-experiment/v1"
POLICY_SCHEMA = "crse-staged-exact-dispatcher/v1"
BUDGET_CANDIDATES = (0, 64, 256, 1_024, 4_096, 16_384, 65_536,
                     262_144, 1_048_576, 4_194_304, 8_000_000)
METHODS = (*ARMS, "staged_set_packed")
EVALUATION_SPLITS = ("c6_test", "c6_confirmatory", "c7_sealed_a", "c7_sealed_b")


@dataclass(frozen=True)
class StagedDispatcherConfig:
    repetitions: int = 9
    cache_capacity: int = 1024
    threads: int = 1
    max_seconds: int = 120

    def validate(self):
        if (type(self.repetitions) is not int or not 5 <= self.repetitions <= 15
                or type(self.cache_capacity) is not int or not 1 <= self.cache_capacity <= 16_384
                or self.threads != 1 or type(self.max_seconds) is not int
                or not 1 <= self.max_seconds <= 120):
            raise ValueError("invalid staged dispatcher configuration")

    def manifest(self, output: Path, c6: Path, c7: Path):
        return {"schema": "crse-staged-exact-dispatcher-run-spec/v1",
            "purpose": "integrate a validation-frozen early set-product guard with exact packed fallback",
            "budget_candidates": list(BUDGET_CANDIDATES), "budget_selection_data": ["validation"],
            "training_use": {"train": False, "validation": True, "test": False,
                             "confirmatory": False, "c7_sealed_a": False, "c7_sealed_b": False},
            "methods": list(METHODS), "repetitions": self.repetitions,
            "cache_capacity": self.cache_capacity, "threads": self.threads,
            "max_seconds": self.max_seconds, "estimated_memory_mib": 192,
            "retained_c6": relative(c6), "retained_c7": relative(c7),
            "output": relative(output), "network": False, "production_write": False,
            "criteria": {"exact": "all fixed and staged paths reproduce every sealed canonical partition",
                "no_material_regret": "staged sequence time is at most 1.05x the best fixed arm on every sealed split",
                "tail_guard": "staged confirmatory p95 is at least 2x faster than unguarded set ANF",
                "freeze": "budget is serialized before held-out and C7 evaluation"}}


def write_json(path: Path, value: Any):
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def source_fingerprints():
    paths = [ROOT / "cmbench/recognition/staged_exact_dispatcher.py",
             ROOT / "cmbench/recognition/staged_dispatcher_experiment.py",
             ROOT / "cmbench/recognition/source_anf_hybrid.py",
             ROOT / "cmbench/recognition/source_interaction.py"]
    return {relative(path): sha(path) for path in paths}


def _staged_solve(row: dict, cache: ProductCache, budget: int):
    document, n_vars = row["expression_v2"], row["n_vars"]
    partition, path, set_stats, packed_stats = staged_exact_partition(
        document, n_vars, product_pair_budget=budget, cache=cache)
    witness = partition_witness(document_truth_bits(document, n_vars), n_vars, partition) if partition is not None else None
    canonical = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
    accepted = partition is not None and witness is not None
    return {"selected_arm": path, "predicted": int(partition is not None), "accepted": accepted,
        "row_variables": list(partition) if partition is not None else None,
        "canonical_partition_match": partition == canonical,
        "semantic_mismatch": bool(accepted and not row["label"]),
        "set_instrumentation": set_stats.to_dict(),
        "packed_instrumentation": packed_stats.to_dict() if packed_stats is not None else None}


def select_budget(validation: list[dict], config: StagedDispatcherConfig, budget_guard: Budget):
    candidates = []
    for candidate in BUDGET_CANDIDATES:
        samples = defaultdict(list)
        fallback_streams = []
        for repetition in range(config.repetitions):
            cache = ProductCache(config.cache_capacity)
            fallbacks = 0
            for row in validation:
                budget_guard.check()
                started = time.perf_counter_ns()
                result = _staged_solve(row, cache, candidate)
                elapsed = time.perf_counter_ns() - started
                fallbacks += result["selected_arm"] == "cached_packed_source_anf"
                samples[row["case_id"]].append({"total_ns": elapsed, **result})
            fallback_streams.append(fallbacks)
        cases = []
        for row in validation:
            values = samples[row["case_id"]]
            first = values[0]
            for field in ("selected_arm", "predicted", "accepted", "row_variables",
                          "canonical_partition_match", "semantic_mismatch",
                          "set_instrumentation", "packed_instrumentation"):
                if any(value[field] != first[field] for value in values[1:]):
                    raise ValueError(f"nondeterministic staged validation result: {candidate}/{row['case_id']}/{field}")
            cases.append({"case_id": row["case_id"], **first,
                "total_ns": int(statistics.median(value["total_ns"] for value in values)),
                "total_samples_ns": [value["total_ns"] for value in values]})
        candidates.append({"product_pair_budget": candidate,
            "sequence_total_ns": sum(row["total_ns"] for row in cases),
            "median_total_ns": statistics.median(row["total_ns"] for row in cases),
            "p95_total_ns": percentile([row["total_ns"] for row in cases], .95),
            "fallbacks": sum(row["selected_arm"] == "cached_packed_source_anf" for row in cases),
            "fallback_streams": fallback_streams, "cases": cases})
    chosen = min(candidates, key=lambda row: (row["sequence_total_ns"], row["product_pair_budget"]))
    policy = {"schema": POLICY_SCHEMA, "status": "frozen",
        "product_pair_budget": chosen["product_pair_budget"],
        "selection": "minimum validation sum of per-case median charged total latency",
        "budget_candidates": list(BUDGET_CANDIDATES),
        "validation_sequence_total_ns": chosen["sequence_total_ns"],
        "validation_fallbacks": chosen["fallbacks"],
        "training_use": {"train": False, "validation": True, "test": False,
                         "confirmatory": False, "c7_sealed_a": False, "c7_sealed_b": False},
        "frozen_before_sealed_load": True}
    return policy, candidates


def benchmark(rows: list[dict], policy: dict, config: StagedDispatcherConfig, budget_guard: Budget):
    samples = defaultdict(list)
    for split in EVALUATION_SPLITS:
        split_rows = [row for row in rows if row["evaluation_split"] == split]
        for repetition in range(config.repetitions):
            order = METHODS[repetition % len(METHODS):] + METHODS[:repetition % len(METHODS)]
            for method in order:
                cache = ProductCache(config.cache_capacity) if method in {
                    "cached_packed_source_anf", "staged_set_packed"} else None
                for row in split_rows:
                    budget_guard.check()
                    started = time.perf_counter_ns()
                    if method == "staged_set_packed":
                        result = _staged_solve(row, cache, policy["product_pair_budget"])
                    else:
                        _partition, fixed = _solve(method, row, cache)
                        result = {"selected_arm": method, **fixed,
                                  "set_instrumentation": None,
                                  "packed_instrumentation": fixed["instrumentation"]}
                    elapsed = time.perf_counter_ns() - started
                    samples[(method, row["case_id"])].append({"total_ns": elapsed, **result})
    aggregated = []
    for (method, case_id), values in sorted(samples.items()):
        first = values[0]
        for field in ("selected_arm", "predicted", "accepted", "row_variables",
                      "canonical_partition_match", "semantic_mismatch",
                      "set_instrumentation", "packed_instrumentation"):
            if any(value[field] != first[field] for value in values[1:]):
                raise ValueError(f"nondeterministic staged evaluation: {method}/{case_id}/{field}")
        row = next(row for row in rows if row["case_id"] == case_id)
        aggregated.append({"method": method, "evaluation_split": row["evaluation_split"],
            "case_id": case_id, "source_scope": row["source_scope"],
            "circuit": row.get("circuit"), "family": row.get("family"),
            "n_vars": row["n_vars"], "label": row["label"], **first,
            "total_ns": int(statistics.median(value["total_ns"] for value in values)),
            "total_samples_ns": [value["total_ns"] for value in values],
            "timing_repetitions": config.repetitions})
    return aggregated


def summarize(rows: list[dict]):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["evaluation_split"], row["method"])].append(row)
    methods, splits = {}, {}
    for (split, method), values in sorted(grouped.items()):
        totals = [row["total_ns"] for row in values]
        methods[f"{method}/{split}"] = {"cases": len(values),
            "median_total_ns": statistics.median(totals), "p95_total_ns": percentile(totals, .95),
            "maximum_total_ns": max(totals), "sequence_total_ns": sum(totals),
            "accuracy": statistics.fmean(row["predicted"] == row["label"] for row in values),
            "canonical_partition_accuracy": statistics.fmean(row["canonical_partition_match"] for row in values),
            "semantic_mismatches": sum(row["semantic_mismatch"] for row in values),
            "selection_counts": dict(sorted(Counter(row["selected_arm"] for row in values).items()))}
    for split in EVALUATION_SPLITS:
        fixed = {arm: methods[f"{arm}/{split}"]["sequence_total_ns"] for arm in ARMS}
        best = min(ARMS, key=lambda arm: fixed[arm])
        staged = methods[f"staged_set_packed/{split}"]
        splits[split] = {"cases": staged["cases"], "best_fixed_arm": best,
            "best_fixed_total_ns": fixed[best], "fixed_sequence_total_ns": fixed,
            "staged_total_ns": staged["sequence_total_ns"],
            "staged_speedup_over_best_fixed": fixed[best] / staged["sequence_total_ns"],
            "staged_speedup_over_set": fixed["set_source_anf"] / staged["sequence_total_ns"],
            "staged_p95_speedup_over_set": methods[f"set_source_anf/{split}"]["p95_total_ns"] / staged["p95_total_ns"],
            "selection_counts": staged["selection_counts"]}
    return methods, splits


def measured_criteria(rows, method_summary, split_summary, frozen):
    exact = all(row["predicted"] == row["label"] and row["canonical_partition_match"]
                and not row["semantic_mismatch"] for row in rows)
    no_regret = all(split_summary[split]["staged_speedup_over_best_fixed"] >= 1 / 1.05
                    for split in EVALUATION_SPLITS)
    tail = split_summary["c6_confirmatory"]["staged_p95_speedup_over_set"] >= 2.0
    return {"exact": exact, "leakage_safe_freeze": frozen,
        "no_material_regret": no_regret, "confirmatory_tail_guard": tail,
        "safety": exact, "production_tail_guard": exact and frozen and no_regret and tail}


def render_report(result):
    lines = ["# Staged exact representation dispatcher", "",
        f"Frozen product-pair budget: **{result['policy']['product_pair_budget']:,}**", "",
        "| Split | Best fixed | Staged speedup | p95 speedup over set | Selections |",
        "| --- | --- | ---: | ---: | --- |"]
    for split, values in result["split_summary"].items():
        lines.append(f"| {split} | {values['best_fixed_arm']} | {values['staged_speedup_over_best_fixed']:.3f}x | {values['staged_p95_speedup_over_set']:.3f}x | `{json.dumps(values['selection_counts'], sort_keys=True)}` |")
    lines += ["", f"Criteria: `{json.dumps(result['criteria'], sort_keys=True)}`", ""]
    return "\n".join(lines)


def run_staged_dispatcher_experiment(config: StagedDispatcherConfig, output: Path,
                                     c6: Path = DEFAULT_C6_RUN, c7: Path = DEFAULT_C7_RUN,
                                     progress=print):
    config.validate()
    output, c6, c7 = output.resolve(), c6.resolve(), c7.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "run_spec.json", config.manifest(output, c6, c7))
    before = source_fingerprints()
    retained_c6, retained_c7 = verify_retained_c6(c6), verify_retained_c7(c7)
    budget_guard, started = Budget(config.max_seconds), time.perf_counter()
    c6_documents = json.loads((c6 / "dataset.json").read_text(encoding="utf-8"))
    validation = [row for row in c6_documents if row["split"] == "validation"]
    progress("selecting the set-product budget on pre-C7 validation only")
    policy, candidates = select_budget(validation, config, budget_guard)
    write_json(output / "budget_candidates.json", candidates)
    write_json(output / "frozen_staged_dispatcher.json", policy)
    frozen_hash = sha(output / "frozen_staged_dispatcher.json")

    progress("loading sealed held-out and independent Yosys cases after freeze")
    c7_documents, c7_provenance = make_yosys_human_documents()
    retained_documents = json.loads((c7 / "dataset.json").read_text(encoding="utf-8"))
    if canonical_sha256(c7_documents) != canonical_sha256(retained_documents):
        raise ValueError("retained C7 dataset did not regenerate")
    evaluation = []
    for row in c6_documents:
        if row["split"] in {"test", "confirmatory"}:
            evaluation.append({**row, "evaluation_split": f"c6_{row['split']}",
                               "source_scope": "pre-C7 EPFL held-out"})
    for row in c7_documents:
        evaluation.append({**row, "evaluation_split": f"c7_{row['split']}",
                           "source_scope": "independent Yosys sealed"})
    progress("benchmarking the frozen staged guard and fixed exact controls")
    rows = benchmark(evaluation, policy, config, budget_guard)
    method_summary, split_summary = summarize(rows)
    criteria = measured_criteria(rows, method_summary, split_summary, True)
    result = {"schema": RUN_SCHEMA, "status": "complete", "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0], "config": asdict(config),
        "retained_c6": retained_c6, "retained_c7": retained_c7,
        "policy": policy, "frozen_policy_sha256": frozen_hash,
        "sealed_loaded_after_freeze": True, "evaluation_rows": len(evaluation),
        "c7_provenance": {key: c7_provenance[key] for key in (
            "source", "upstream_commit", "license", "network_access_performed", "source_checkout_modified")},
        "method_summary": method_summary, "split_summary": split_summary,
        "criteria": criteria, "semantic_mismatches": sum(row["semantic_mismatch"] for row in rows),
        "source_unchanged": before == source_fingerprints()}
    write_json(output / "evaluation_dataset.json", evaluation)
    write_json(output / "evaluation_benchmark.json", rows)
    write_json(output / "summary.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8")
    files = ("run_spec.json", "budget_candidates.json", "frozen_staged_dispatcher.json",
             "evaluation_dataset.json", "evaluation_benchmark.json", "summary.json", "report.md")
    write_json(output / "manifest.json", {"schema": "crse-staged-exact-dispatcher-artifacts/v1",
        "status": "complete", "files_sha256": {name: sha(output / name) for name in files},
        "source_sha256": before, "retained_c6_manifest_sha256": retained_c6["manifest_sha256"],
        "retained_c7_manifest_sha256": retained_c7["manifest_sha256"]})
    return result
