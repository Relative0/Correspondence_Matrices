"""Frozen evaluation of the one-pass exact adaptive ANF representation."""
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

from .adaptive_exact_dispatcher import adaptive_exact_partition
from .exact_dispatcher import ARMS, canonical_sha256
from .exact_dispatcher_experiment import Budget, DEFAULT_C6_RUN, DEFAULT_C7_RUN, _solve, relative, verify_retained_c7
from .natural_decomposition import partition_witness
from .natural_source_anf_experiment import percentile, sha
from .source_anf_hybrid import ProductCache
from .staged_dispatcher_experiment import _staged_solve
from .yosys_composed_holdout_data import make_yosys_composed_holdout
from .yosys_human_decomposition_data import make_yosys_human_documents
from .yosys_source_anf_experiment import document_truth_bits, verify_retained_c6

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_C10_RUN = ROOT / "docs/recognition/runs/staged-exact-dispatcher-20260830-001"
RUN_SCHEMA = "crse-adaptive-exact-dispatcher-experiment/v1"
POLICY_SCHEMA = "crse-adaptive-exact-dispatcher/v1"
METHODS = (*ARMS, "staged_restart", "adaptive_one_pass")
SPLITS = ("c6_test_dev", "c6_confirmatory_dev", "c7_a_dev", "c7_b_dev",
          "c11_sealed_a", "c11_sealed_b")


@dataclass(frozen=True)
class AdaptiveConfig:
    repetitions: int = 9
    cache_capacity: int = 1024
    threads: int = 1
    max_seconds: int = 120

    def validate(self) -> None:
        if (type(self.repetitions) is not int or not 5 <= self.repetitions <= 15
                or type(self.cache_capacity) is not int or not 1 <= self.cache_capacity <= 16_384
                or self.threads != 1 or type(self.max_seconds) is not int
                or not 1 <= self.max_seconds <= 120):
            raise ValueError("invalid adaptive dispatcher configuration")


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def source_fingerprints() -> dict[str, str]:
    paths = [ROOT / "cmbench/recognition/adaptive_exact_dispatcher.py",
             ROOT / "cmbench/recognition/adaptive_dispatcher_experiment.py",
             ROOT / "cmbench/recognition/yosys_composed_holdout_data.py",
             ROOT / "cmbench/recognition/source_anf_hybrid.py",
             ROOT / "cmbench/recognition/source_interaction.py"]
    return {relative(path): sha(path) for path in paths}


def _adaptive_solve(row: dict, cache: ProductCache, budget: int) -> dict:
    document, n_vars = row["expression_v2"], row["n_vars"]
    partition, path, instrumentation = adaptive_exact_partition(
        document, n_vars, product_pair_budget=budget, cache=cache)
    witness = partition_witness(document_truth_bits(document, n_vars), n_vars, partition) if partition is not None else None
    canonical = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
    accepted = partition is not None and witness is not None
    return {"selected_arm": path, "predicted": int(partition is not None), "accepted": accepted,
        "row_variables": list(partition) if partition is not None else None,
        "canonical_partition_match": partition == canonical,
        "semantic_mismatch": bool(accepted and not row["label"]),
        "instrumentation": instrumentation.to_dict()}


def _fixed_solve(method: str, row: dict, cache: ProductCache | None) -> dict:
    _partition, result = _solve(method, row, cache)
    return {"selected_arm": method, **result}


def benchmark(rows: list[dict], policy: dict, config: AdaptiveConfig, guard: Budget,
              splits: tuple[str, ...] = SPLITS) -> list[dict]:
    samples: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for split in splits:
        split_rows = [row for row in rows if row["evaluation_split"] == split]
        for repetition in range(config.repetitions):
            order = METHODS[repetition % len(METHODS):] + METHODS[:repetition % len(METHODS)]
            for method in order:
                cache = ProductCache(config.cache_capacity) if method in {
                    "cached_packed_source_anf", "staged_restart", "adaptive_one_pass"} else None
                for row in split_rows:
                    guard.check()
                    started = time.perf_counter_ns()
                    if method == "adaptive_one_pass":
                        result = _adaptive_solve(row, cache, policy["product_pair_budget"])
                    elif method == "staged_restart":
                        staged = _staged_solve(row, cache, policy["product_pair_budget"])
                        result = {"selected_arm": staged["selected_arm"],
                            "predicted": staged["predicted"], "accepted": staged["accepted"],
                            "row_variables": staged["row_variables"],
                            "canonical_partition_match": staged["canonical_partition_match"],
                            "semantic_mismatch": staged["semantic_mismatch"],
                            "instrumentation": {"set": staged["set_instrumentation"],
                                                "packed": staged["packed_instrumentation"]}}
                    else:
                        result = _fixed_solve(method, row, cache)
                    elapsed = time.perf_counter_ns() - started
                    samples[(method, row["case_id"])].append({"total_ns": elapsed, **result})
    aggregated = []
    by_id = {row["case_id"]: row for row in rows}
    for (method, case_id), values in sorted(samples.items()):
        first = values[0]
        for field in ("selected_arm", "predicted", "accepted", "row_variables",
                      "canonical_partition_match", "semantic_mismatch", "instrumentation"):
            if any(value[field] != first[field] for value in values[1:]):
                raise ValueError(f"nondeterministic adaptive evaluation: {method}/{case_id}/{field}")
        row = by_id[case_id]
        aggregated.append({"method": method, "evaluation_split": row["evaluation_split"],
            "case_id": case_id, "source_scope": row["source_scope"],
            "family": row.get("family"), "source_kind": row.get("source_kind"),
            "n_vars": row["n_vars"], "label": row["label"], **first,
            "total_ns": int(statistics.median(value["total_ns"] for value in values)),
            "total_samples_ns": [value["total_ns"] for value in values],
            "timing_repetitions": config.repetitions})
    return aggregated


def summarize(rows: list[dict], splits_to_summarize: tuple[str, ...] = SPLITS) -> tuple[dict, dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
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
    for split in splits_to_summarize:
        fixed = {arm: methods[f"{arm}/{split}"]["sequence_total_ns"] for arm in ARMS}
        best = min(ARMS, key=lambda arm: fixed[arm])
        adaptive = methods[f"adaptive_one_pass/{split}"]
        staged = methods[f"staged_restart/{split}"]
        splits[split] = {"cases": adaptive["cases"], "best_fixed_arm": best,
            "best_fixed_total_ns": fixed[best], "fixed_sequence_total_ns": fixed,
            "adaptive_total_ns": adaptive["sequence_total_ns"],
            "adaptive_speedup_over_best_fixed": fixed[best] / adaptive["sequence_total_ns"],
            "adaptive_p95_speedup_over_set": methods[f"set_source_anf/{split}"]["p95_total_ns"] / adaptive["p95_total_ns"],
            "adaptive_speedup_over_restart": staged["sequence_total_ns"] / adaptive["sequence_total_ns"],
            "adaptive_selection_counts": adaptive["selection_counts"],
            "staged_total_ns": staged["sequence_total_ns"]}
    return methods, splits


def measured_criteria(rows: list[dict], splits: dict, frozen: bool, holdout_audit: dict) -> dict:
    exact = all(row["predicted"] == row["label"] and row["canonical_partition_match"]
                and not row["semantic_mismatch"] for row in rows)
    fresh = holdout_audit["c7_semantic_overlap"] == 0 and holdout_audit["c7_alpha_overlap"] == 0
    sealed_no_regret = all(splits[split]["adaptive_speedup_over_best_fixed"] >= 1 / 1.05
                           for split in ("c11_sealed_a", "c11_sealed_b"))
    dev_tail = splits["c6_confirmatory_dev"]["adaptive_p95_speedup_over_set"] >= 2.0
    restart_improved = all(splits[split]["adaptive_speedup_over_restart"] >= 1.0
                           for split in SPLITS)
    return {"exact": exact, "leakage_safe_freeze": frozen, "fresh_holdout_disjoint": fresh,
        "sealed_no_material_regret": sealed_no_regret, "development_tail_guard": dev_tail,
        "one_pass_beats_restart_all_splits": restart_improved,
        "safety": exact and fresh,
        "production_promotion": exact and frozen and fresh and sealed_no_regret and dev_tail}


def render_report(result: dict) -> str:
    lines = ["# One-pass exact adaptive dispatcher", "",
        f"Frozen product-pair budget: **{result['policy']['product_pair_budget']:,}**", "",
        "| Split | Best fixed | Adaptive speedup | vs restart | p95 vs set | Selections |",
        "| --- | --- | ---: | ---: | ---: | --- |"]
    for split, values in result["split_summary"].items():
        lines.append(f"| {split} | {values['best_fixed_arm']} | {values['adaptive_speedup_over_best_fixed']:.3f}x | {values['adaptive_speedup_over_restart']:.3f}x | {values['adaptive_p95_speedup_over_set']:.3f}x | `{json.dumps(values['adaptive_selection_counts'], sort_keys=True)}` |")
    lines += ["", f"Criteria: `{json.dumps(result['criteria'], sort_keys=True)}`", ""]
    return "\n".join(lines)


def run_adaptive_experiment(config: AdaptiveConfig, output: Path,
                            c6: Path = DEFAULT_C6_RUN, c7: Path = DEFAULT_C7_RUN,
                            c10: Path = DEFAULT_C10_RUN, progress=print) -> dict:
    config.validate()
    output, c6, c7, c10 = output.resolve(), c6.resolve(), c7.resolve(), c10.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = source_fingerprints()
    retained_c6, retained_c7 = verify_retained_c6(c6), verify_retained_c7(c7)
    upstream_policy_path = c10 / "frozen_staged_dispatcher.json"
    upstream_policy = json.loads(upstream_policy_path.read_text(encoding="utf-8"))
    if upstream_policy.get("schema") != "crse-staged-exact-dispatcher/v1" or upstream_policy.get("product_pair_budget") != 64:
        raise ValueError("unexpected C10 development policy")
    policy = {"schema": POLICY_SCHEMA, "status": "frozen", "product_pair_budget": 64,
        "architecture": "one-pass set-to-packed conversion at the first refused product",
        "budget_source": relative(upstream_policy_path), "budget_source_sha256": sha(upstream_policy_path),
        "training_use": {"c6_validation": True, "c6_test": False, "c6_confirmatory": False,
                         "c7": False, "c11": False},
        "frozen_before_c11_generation": True}
    run_spec = {"schema": "crse-adaptive-exact-dispatcher-run-spec/v1",
        "purpose": "remove staged restart by switching exact ANF representation in place",
        "methods": list(METHODS), "splits": list(SPLITS), "repetitions": config.repetitions,
        "cache_capacity": config.cache_capacity, "threads": config.threads,
        "max_seconds": config.max_seconds, "estimated_memory_mib": 256,
        "retained_c6": relative(c6), "retained_c7": relative(c7),
        "development_data": ["C6 heldout (previously inspected)", "C7 (previously inspected)"],
        "sealed_data": "C11 generated only after policy serialization",
        "network": False, "production_write": False}
    write_json(output / "run_spec.json", run_spec)
    write_json(output / "frozen_adaptive_dispatcher.json", policy)
    frozen_hash = sha(output / "frozen_adaptive_dispatcher.json")

    progress("generating and sealing the fresh C11 source holdout after policy freeze")
    c11, c11_provenance = make_yosys_composed_holdout()
    write_json(output / "c11_dataset.json", c11)
    write_json(output / "c11_provenance.json", c11_provenance)
    c11_dataset_hash = sha(output / "c11_dataset.json")

    c6_documents = json.loads((c6 / "dataset.json").read_text(encoding="utf-8"))
    c7_documents, _c7_provenance = make_yosys_human_documents()
    retained_documents = json.loads((c7 / "dataset.json").read_text(encoding="utf-8"))
    if canonical_sha256(c7_documents) != canonical_sha256(retained_documents):
        raise ValueError("retained C7 dataset did not regenerate")
    evaluation = []
    for row in c6_documents:
        if row["split"] in {"test", "confirmatory"}:
            evaluation.append({**row, "evaluation_split": f"c6_{row['split']}_dev",
                               "source_scope": "development EPFL; previously inspected"})
    for row in c7_documents:
        evaluation.append({**row, "evaluation_split": f"c7_{row['split'].removeprefix('sealed_')}_dev",
                           "source_scope": "development Yosys; previously inspected"})
    for row in c11:
        evaluation.append({**row, "evaluation_split": f"c11_{row['split']}",
                           "source_scope": "fresh C11 Yosys-derived holdout"})

    guard, started = Budget(config.max_seconds), time.perf_counter()
    progress("benchmarking fixed, restart, and one-pass exact methods")
    rows = benchmark(evaluation, policy, config, guard)
    method_summary, split_summary = summarize(rows)
    criteria = measured_criteria(rows, split_summary, True, c11_provenance["audit"])
    result = {"schema": RUN_SCHEMA, "status": "complete", "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0], "config": asdict(config),
        "retained_c6": retained_c6, "retained_c7": retained_c7,
        "policy": policy, "frozen_policy_sha256": frozen_hash,
        "c11_dataset_sha256": c11_dataset_hash, "c11_loaded_after_policy_freeze": True,
        "c11_audit": c11_provenance["audit"], "evaluation_rows": len(evaluation),
        "method_summary": method_summary, "split_summary": split_summary,
        "criteria": criteria, "semantic_mismatches": sum(row["semantic_mismatch"] for row in rows),
        "source_unchanged": before == source_fingerprints()}
    write_json(output / "evaluation_dataset.json", evaluation)
    write_json(output / "evaluation_benchmark.json", rows)
    write_json(output / "summary.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8")
    files = ("run_spec.json", "frozen_adaptive_dispatcher.json", "c11_dataset.json",
             "c11_provenance.json", "evaluation_dataset.json", "evaluation_benchmark.json",
             "summary.json", "report.md")
    write_json(output / "manifest.json", {"schema": "crse-adaptive-exact-dispatcher-artifacts/v1",
        "status": "complete", "files_sha256": {name: sha(output / name) for name in files},
        "source_sha256": before, "retained_c6_manifest_sha256": retained_c6["manifest_sha256"],
        "retained_c7_manifest_sha256": retained_c7["manifest_sha256"]})
    return result
