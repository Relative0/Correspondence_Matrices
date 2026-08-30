"""Leakage-safe fitting and sealed evaluation of an exact representation dispatcher."""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cm_expr_serde import expr_from_json

from .exact_dispatcher import (
    ARMS, LINEAR_FEATURES, O1_FEATURES, POLICY_SCHEMA, CompiledDispatcher, canonical_sha256,
    extract_dispatch_features, fit_greedy_tree, select_document, select_from_values,
    tree_stats, validate_policy,
)
from .natural_decomposition import analyze_decomposition, partition_witness
from .natural_source_anf_experiment import percentile, sha
from .portfolio import reference_bits
from .source_anf_hybrid import ProductCache, source_packed_partition
from .source_interaction import source_exact_partition
from .yosys_human_decomposition_data import make_yosys_human_documents
from .yosys_source_anf_experiment import (
    DEFAULT_C6_RUN, document_truth_bits, source_fingerprints as c7_source_fingerprints,
    verify_retained_c6,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_C7_RUN = ROOT / "docs" / "recognition" / "runs" / "yosys-source-anf-confirmation-20260830-002"
RUN_SCHEMA = "crse-exact-representation-dispatcher-experiment/v1"
EVALUATION_METHODS = (*ARMS, "frozen_dispatcher")
EVALUATION_SPLITS = ("c6_test", "c6_confirmatory", "c7_sealed_a", "c7_sealed_b")


@dataclass(frozen=True)
class ExactDispatcherConfig:
    repetitions: int = 9
    cache_capacity: int = 1024
    threads: int = 1
    max_seconds: int = 120

    def validate(self):
        if (type(self.repetitions) is not int or not 5 <= self.repetitions <= 15
                or type(self.cache_capacity) is not int or not 1 <= self.cache_capacity <= 16_384
                or self.threads != 1 or type(self.max_seconds) is not int
                or not 1 <= self.max_seconds <= 120):
            raise ValueError("invalid exact dispatcher experiment configuration")

    def manifest(self, output: Path, c6: Path, c7: Path):
        return {"schema": "crse-exact-representation-dispatcher-run-spec/v1",
            "purpose": "freeze a cheap exact set/packed/bitset selector on pre-C7 development data",
            "development": {"train": True, "validation": True},
            "sealed_evaluation": {"test": False, "confirmatory": False,
                                  "c7_sealed_a": False, "c7_sealed_b": False},
            "arms": list(ARMS), "evaluation_methods": list(EVALUATION_METHODS),
            "repetitions": self.repetitions, "cache_capacity": self.cache_capacity,
            "threads": self.threads, "max_seconds": self.max_seconds,
            "estimated_memory_mib": 192, "retained_c6": relative(c6),
            "retained_c7": relative(c7), "output": relative(output),
            "network": False, "production_write": False,
            "criteria": {"exact": "dispatcher and all fixed arms reproduce every sealed canonical partition",
                "leakage": "policy is serialized before C6 held-out or C7 rows are timed or loaded for evaluation",
                "no_material_regret": "dispatcher sequence time is at most 1.05x the best fixed exact arm on every sealed split",
                "profitable": "dispatcher beats the best fixed exact arm on every sealed split"}}


def relative(path: Path) -> str:
    path = path.resolve()
    return str(path.relative_to(ROOT)).replace("\\", "/") if ROOT in path.parents or path == ROOT else str(path)


def write_json(path: Path, value: Any):
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


class Budget:
    def __init__(self, seconds: int):
        self.deadline = time.perf_counter() + seconds

    def check(self):
        if time.perf_counter() >= self.deadline:
            raise RuntimeError("exact dispatcher wall budget exhausted")


def verify_retained_c7(base: Path):
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((base / "summary.json").read_text(encoding="utf-8"))
    if (manifest.get("schema") != "crse-yosys-source-anf-confirmation-artifacts/v1"
            or manifest.get("status") != "complete" or summary.get("status") != "complete"
            or summary.get("semantic_mismatches") != 0 or not summary.get("criteria", {}).get("exact")):
        raise ValueError("invalid retained C7 dependency")
    for name, expected in manifest["files_sha256"].items():
        if sha(base / name) != expected:
            raise ValueError(f"retained C7 artifact changed: {name}")
    if c7_source_fingerprints() != manifest["source_sha256"]:
        raise ValueError("retained C7 source seal changed")
    return {"path": relative(base), "manifest_sha256": sha(base / "manifest.json"),
            "dataset_sha256": sha(base / "dataset.json")}


def source_fingerprints() -> dict[str, str]:
    paths = [ROOT / "cmbench/recognition/exact_dispatcher.py",
             ROOT / "cmbench/recognition/exact_dispatcher_experiment.py",
             ROOT / "cmbench/recognition/source_anf_hybrid.py",
             ROOT / "cmbench/recognition/source_interaction.py",
             ROOT / "cmbench/recognition/natural_decomposition.py"]
    return {relative(path): sha(path) for path in paths}


def _solve(arm: str, row: dict, cache: ProductCache | None):
    document, n_vars = row["expression_v2"], row["n_vars"]
    instrumentation = None
    witness = None
    if arm == "set_source_anf":
        partition = source_exact_partition(document, n_vars)
    elif arm == "cached_packed_source_anf":
        partition, stats = source_packed_partition(document, n_vars, cache=cache)
        instrumentation = stats.to_dict()
    elif arm == "bitset_truth_vector_anf":
        analysis = analyze_decomposition(document_truth_bits(document, n_vars), n_vars)
        partition, witness = analysis.row_variables, analysis.witness
    else:
        raise ValueError("unknown exact dispatcher arm")
    if arm != "bitset_truth_vector_anf" and partition is not None:
        witness = partition_witness(document_truth_bits(document, n_vars), n_vars, partition)
    canonical = tuple(row["witness"]["row_variables"]) if row["witness"] is not None else None
    accepted = partition is not None and witness is not None
    return partition, {"predicted": int(partition is not None), "accepted": accepted,
        "row_variables": list(partition) if partition is not None else None,
        "canonical_partition_match": partition == canonical,
        "semantic_mismatch": bool(accepted and not row["label"]),
        "instrumentation": instrumentation}


def benchmark_development(rows: list[dict], config: ExactDispatcherConfig, budget: Budget):
    samples = defaultdict(list)
    for split in ("train", "validation"):
        split_rows = [row for row in rows if row["split"] == split]
        for repetition in range(config.repetitions):
            order = ARMS[repetition % len(ARMS):] + ARMS[:repetition % len(ARMS)]
            for arm in order:
                cache = ProductCache(config.cache_capacity) if arm == "cached_packed_source_anf" else None
                for row in split_rows:
                    budget.check()
                    started = time.perf_counter_ns()
                    _partition, result = _solve(arm, row, cache)
                    elapsed = time.perf_counter_ns() - started
                    samples[(arm, row["case_id"])].append({"total_ns": elapsed, **result})
    aggregated = []
    for (arm, case_id), values in sorted(samples.items()):
        first = values[0]
        for field in ("predicted", "accepted", "row_variables", "canonical_partition_match",
                      "semantic_mismatch", "instrumentation"):
            if any(value[field] != first[field] for value in values[1:]):
                raise ValueError(f"nondeterministic development result: {arm}/{case_id}/{field}")
        row = next(item for item in rows if item["case_id"] == case_id)
        aggregated.append({"method": arm, "split": row["split"], "case_id": case_id,
            "circuit": row["circuit"], "n_vars": row["n_vars"], "label": row["label"],
            **first, "total_ns": int(statistics.median(value["total_ns"] for value in values)),
            "total_samples_ns": [value["total_ns"] for value in values],
            "timing_repetitions": config.repetitions})
    return aggregated


def _policy(tree: dict, fit_config: dict, train_rows: list[dict], train_loss: int,
            validation_metrics: dict, c6_dataset_sha256: str):
    policy = {"schema": POLICY_SCHEMA, "status": "frozen", "arms": list(ARMS),
        "feature_contract": "source DAG only; no truth vector, ANF, circuit identity, label, or sealed timing",
        "fit_config": fit_config, "tree": tree, "tree_stats": tree_stats(tree),
        "training_rows": len(train_rows), "training_case_ids_sha256": canonical_sha256(
            sorted(row["case_id"] for row in train_rows)),
        "training_loss_ns": train_loss, "validation_metrics": validation_metrics,
        "source_dataset_sha256": c6_dataset_sha256,
        "training_use": {"train": True, "validation": True, "test": False,
                         "confirmatory": False, "c7_sealed_a": False, "c7_sealed_b": False},
        "frozen_before_sealed_load": True}
    validate_policy(policy)
    return policy


def _selection_overhead(tree: dict, rows: list[dict], repetitions: int):
    required = tree_stats(tree)["required_features"]
    candidate_policy = {"schema": POLICY_SCHEMA, "arms": list(ARMS), "tree": tree,
        "tree_stats": tree_stats(tree),
        "training_use": {"train": True, "validation": True, "test": False,
                         "confirmatory": False, "c7_sealed_a": False, "c7_sealed_b": False}}
    compiled = CompiledDispatcher(candidate_policy)
    result = {}
    for row in rows:
        values = []
        selected = None
        for _ in range(repetitions):
            started = time.perf_counter_ns()
            arm, observed = compiled.select(row["expression_v2"], row["n_vars"])
            values.append(time.perf_counter_ns() - started)
            if selected is None:
                selected = arm
            elif selected != arm:
                raise ValueError("nondeterministic validation selection")
            if set(observed) != set(required) and not set(required).issubset(O1_FEATURES):
                raise ValueError("dispatcher evaluated unexpected validation features")
        result[row["case_id"]] = {"arm": selected, "median_ns": int(statistics.median(values)),
                                  "samples_ns": values}
    return result


def fit_and_select_policy(documents: list[dict], measurements: list[dict], config: ExactDispatcherConfig,
                          c6_dataset_sha256: str):
    timing = defaultdict(dict)
    for row in measurements:
        timing[row["case_id"]][row["method"]] = row["total_ns"]
    fit_rows = []
    for row in documents:
        if row["split"] not in {"train", "validation"}:
            continue
        fit_rows.append({"case_id": row["case_id"], "split": row["split"],
            "features": extract_dispatch_features(row["expression_v2"], row["n_vars"]).to_dict(),
            "costs": timing[row["case_id"]], "document": row})
    train = [row for row in fit_rows if row["split"] == "train"]
    validation = [row for row in fit_rows if row["split"] == "validation"]
    configurations = [("constant", (), 0, 2)]
    for family, features in (("o1", O1_FEATURES), ("linear", LINEAR_FEATURES)):
        for depth in (1, 2):
            for minimum in (4, 8, 12):
                configurations.append((family, features, depth, minimum))
    candidates = []
    for family, features, depth, minimum in configurations:
        tree, train_loss = fit_greedy_tree(train, features=features, max_depth=depth, min_leaf=minimum)
        overhead = _selection_overhead(tree, [row["document"] for row in validation], config.repetitions)
        arm_totals = {arm: sum(row["costs"][arm] for row in validation) for arm in ARMS}
        oracle = sum(min(row["costs"].values()) for row in validation)
        selected_total = sum(row["costs"][overhead[row["case_id"]]["arm"]]
                             + overhead[row["case_id"]]["median_ns"] for row in validation)
        metrics = {"sequence_total_ns": selected_total, "best_fixed_total_ns": min(arm_totals.values()),
            "best_fixed_arm": min(ARMS, key=lambda arm: arm_totals[arm]), "oracle_total_ns": oracle,
            "ratio_to_best_fixed": selected_total / min(arm_totals.values()),
            "regret_to_oracle": selected_total / oracle,
            "selection_overhead_median_ns": statistics.median(value["median_ns"] for value in overhead.values()),
            "selection_counts": dict(sorted(Counter(value["arm"] for value in overhead.values()).items()))}
        candidates.append({"name": f"{family}-d{depth}-m{minimum}",
            "feature_family": family, "max_depth": depth, "min_leaf": minimum,
            "tree": tree, "tree_stats": tree_stats(tree), "training_loss_ns": train_loss,
            "validation": metrics})
    chosen = min(candidates, key=lambda row: (row["validation"]["sequence_total_ns"],
        row["tree_stats"]["splits"], row["name"]))
    policy = _policy(chosen["tree"], {key: chosen[key] for key in (
        "name", "feature_family", "max_depth", "min_leaf")}, train, chosen["training_loss_ns"],
        chosen["validation"], c6_dataset_sha256)
    return policy, candidates, fit_rows


def benchmark_evaluation(rows: list[dict], policy: dict, config: ExactDispatcherConfig, budget: Budget):
    samples = defaultdict(list)
    compiled = CompiledDispatcher(policy)
    for split in EVALUATION_SPLITS:
        split_rows = [row for row in rows if row["evaluation_split"] == split]
        for repetition in range(config.repetitions):
            order = (EVALUATION_METHODS[repetition % len(EVALUATION_METHODS):]
                     + EVALUATION_METHODS[:repetition % len(EVALUATION_METHODS)])
            for method in order:
                cache = ProductCache(config.cache_capacity) if method in {
                    "cached_packed_source_anf", "frozen_dispatcher"} else None
                for row in split_rows:
                    budget.check()
                    started = time.perf_counter_ns()
                    selected_arm = method
                    selection_ns = 0
                    selection_values = None
                    if method == "frozen_dispatcher":
                        selected_arm, selection_values = compiled.select(
                            row["expression_v2"], row["n_vars"])
                        selection_ns = time.perf_counter_ns() - started
                    _partition, result = _solve(selected_arm, row, cache)
                    total_ns = time.perf_counter_ns() - started
                    samples[(method, row["case_id"])].append({"total_ns": total_ns,
                        "selection_ns": selection_ns, "selected_arm": selected_arm,
                        "selection_values": selection_values, **result})
    aggregated = []
    for (method, case_id), values in sorted(samples.items()):
        first = values[0]
        for field in ("selected_arm", "selection_values", "predicted", "accepted", "row_variables",
                      "canonical_partition_match", "semantic_mismatch", "instrumentation"):
            if any(value[field] != first[field] for value in values[1:]):
                raise ValueError(f"nondeterministic sealed dispatcher result: {method}/{case_id}/{field}")
        row = next(item for item in rows if item["case_id"] == case_id)
        aggregated.append({"method": method, "evaluation_split": row["evaluation_split"],
            "case_id": case_id, "source_scope": row["source_scope"],
            "circuit": row.get("circuit"), "family": row.get("family"),
            "n_vars": row["n_vars"], "label": row["label"], **first,
            "total_ns": int(statistics.median(value["total_ns"] for value in values)),
            "selection_ns": int(statistics.median(value["selection_ns"] for value in values)),
            "total_samples_ns": [value["total_ns"] for value in values],
            "selection_samples_ns": [value["selection_ns"] for value in values],
            "timing_repetitions": config.repetitions})
    return aggregated


def summarize_evaluation(rows: list[dict]):
    by_split_method = defaultdict(list)
    for row in rows:
        by_split_method[(row["evaluation_split"], row["method"])].append(row)
    method_summary = {}
    split_summary = {}
    for (split, method), values in sorted(by_split_method.items()):
        totals = [row["total_ns"] for row in values]
        method_summary[f"{method}/{split}"] = {"cases": len(values),
            "median_total_ns": statistics.median(totals), "p95_total_ns": percentile(totals, .95),
            "maximum_total_ns": max(totals), "sequence_total_ns": sum(totals),
            "accuracy": statistics.fmean(row["predicted"] == row["label"] for row in values),
            "canonical_partition_accuracy": statistics.fmean(row["canonical_partition_match"] for row in values),
            "semantic_mismatches": sum(row["semantic_mismatch"] for row in values),
            "median_selection_ns": statistics.median(row["selection_ns"] for row in values)}
    by_case = defaultdict(dict)
    for row in rows:
        by_case[(row["evaluation_split"], row["case_id"])][row["method"]] = row
    for split in EVALUATION_SPLITS:
        cases = [value for (row_split, _case), value in by_case.items() if row_split == split]
        fixed_totals = {arm: sum(case[arm]["total_ns"] for case in cases) for arm in ARMS}
        dispatcher_total = sum(case["frozen_dispatcher"]["total_ns"] for case in cases)
        oracle_total = sum(min(case[arm]["total_ns"] for arm in ARMS) for case in cases)
        regrets = [case["frozen_dispatcher"]["total_ns"] /
                   min(case[arm]["total_ns"] for arm in ARMS) for case in cases]
        selected = Counter(case["frozen_dispatcher"]["selected_arm"] for case in cases)
        oracle_matches = sum(case["frozen_dispatcher"]["selected_arm"] ==
                             min(ARMS, key=lambda arm: case[arm]["total_ns"]) for case in cases)
        best_arm = min(ARMS, key=lambda arm: fixed_totals[arm])
        split_summary[split] = {"cases": len(cases), "fixed_sequence_total_ns": fixed_totals,
            "best_fixed_arm": best_arm, "best_fixed_total_ns": fixed_totals[best_arm],
            "dispatcher_total_ns": dispatcher_total,
            "dispatcher_speedup_over_best_fixed": fixed_totals[best_arm] / dispatcher_total,
            "oracle_total_ns": oracle_total, "dispatcher_regret_to_oracle": dispatcher_total / oracle_total,
            "median_case_regret": statistics.median(regrets), "p95_case_regret": percentile(regrets, .95),
            "oracle_arm_match_accuracy": oracle_matches / len(cases),
            "selection_counts": dict(sorted(selected.items())),
            "selection_overhead_median_ns": method_summary[f"frozen_dispatcher/{split}"]["median_selection_ns"]}
    return method_summary, split_summary


def criteria(rows: list[dict], split_summary: dict, frozen_before_sealed: bool):
    exact = all(row["predicted"] == row["label"] and row["canonical_partition_match"]
                and not row["semantic_mismatch"] for row in rows)
    no_regret = all(split_summary[split]["dispatcher_speedup_over_best_fixed"] >= 1 / 1.05
                    for split in EVALUATION_SPLITS)
    profitable = all(split_summary[split]["dispatcher_speedup_over_best_fixed"] > 1.0
                     for split in EVALUATION_SPLITS)
    return {"exact": exact, "leakage_safe_freeze": frozen_before_sealed,
        "no_material_regret": no_regret, "profitable_on_every_split": profitable,
        "safety": exact, "production_promotion": exact and frozen_before_sealed and no_regret and profitable}


def render_report(result: dict):
    lines = ["# Exact representation dispatcher experiment", "", f"Status: **{result['status']}**", "",
        f"Frozen policy: `{result['policy']['fit_config']['name']}` / `{json.dumps(result['policy']['tree'], sort_keys=True)}`", "",
        "| Split | Best fixed | Dispatcher speedup | Oracle regret | Selection counts |", "| --- | --- | ---: | ---: | --- |"]
    for split, values in result["split_summary"].items():
        lines.append(f"| {split} | {values['best_fixed_arm']} | {values['dispatcher_speedup_over_best_fixed']:.3f}x | {values['dispatcher_regret_to_oracle']:.3f}x | `{json.dumps(values['selection_counts'], sort_keys=True)}` |")
    lines += ["", f"Criteria: `{json.dumps(result['criteria'], sort_keys=True)}`", ""]
    return "\n".join(lines)


def run_exact_dispatcher_experiment(config: ExactDispatcherConfig, output: Path,
                                    c6: Path = DEFAULT_C6_RUN, c7: Path = DEFAULT_C7_RUN,
                                    progress=print):
    config.validate()
    output, c6, c7 = output.resolve(), c6.resolve(), c7.resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "run_spec.json", config.manifest(output, c6, c7))
    before = source_fingerprints()
    retained_c6, retained_c7 = verify_retained_c6(c6), verify_retained_c7(c7)
    budget, started = Budget(config.max_seconds), time.perf_counter()
    c6_documents = json.loads((c6 / "dataset.json").read_text(encoding="utf-8"))
    c6_dataset_sha256 = sha(c6 / "dataset.json")
    development = [row for row in c6_documents if row["split"] in {"train", "validation"}]
    progress("benchmarking pre-C7 train/validation exact arms")
    development_rows = benchmark_development(development, config, budget)
    policy, candidates, fitting_rows = fit_and_select_policy(
        development, development_rows, config, c6_dataset_sha256)
    write_json(output / "development_benchmark.json", development_rows)
    write_json(output / "policy_candidates.json", candidates)
    write_json(output / "frozen_dispatcher.json", policy)
    frozen_sha256 = sha(output / "frozen_dispatcher.json")
    frozen_at_ns = time.perf_counter_ns()

    progress("loading sealed C6 held-out and independent C7 cases after freeze")
    c7_documents, c7_provenance = make_yosys_human_documents()
    if canonical_sha256(c7_documents) != canonical_sha256(json.loads((c7 / "dataset.json").read_text(encoding="utf-8"))):
        raise ValueError("retained C7 dataset did not regenerate before sealed evaluation")
    evaluation = []
    for row in c6_documents:
        if row["split"] in {"test", "confirmatory"}:
            evaluation.append({**row, "evaluation_split": f"c6_{row['split']}", "source_scope": "pre-C7 EPFL held-out"})
    for row in c7_documents:
        evaluation.append({**row, "evaluation_split": f"c7_{row['split']}", "source_scope": "independent Yosys sealed"})
    progress("benchmarking frozen dispatcher and fixed exact arms")
    evaluation_rows = benchmark_evaluation(evaluation, policy, config, budget)
    method_summary, split_summary = summarize_evaluation(evaluation_rows)
    measured = criteria(evaluation_rows, split_summary, frozen_at_ns < time.perf_counter_ns())
    result = {"schema": RUN_SCHEMA, "status": "complete", "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0], "config": asdict(config),
        "retained_c6": retained_c6, "retained_c7": retained_c7,
        "development_rows": len(development), "fitting_rows": len(fitting_rows),
        "evaluation_rows": len(evaluation), "policy": policy,
        "frozen_dispatcher_sha256": frozen_sha256,
        "sealed_loaded_after_freeze": True, "c7_provenance": {key: c7_provenance[key] for key in (
            "source", "upstream_commit", "license", "network_access_performed", "source_checkout_modified")},
        "method_summary": method_summary, "split_summary": split_summary, "criteria": measured,
        "semantic_mismatches": sum(row["semantic_mismatch"] for row in evaluation_rows),
        "source_unchanged": before == source_fingerprints()}
    write_json(output / "evaluation_dataset.json", evaluation)
    write_json(output / "evaluation_benchmark.json", evaluation_rows)
    write_json(output / "summary.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8")
    files = ("run_spec.json", "development_benchmark.json", "policy_candidates.json",
             "frozen_dispatcher.json", "evaluation_dataset.json", "evaluation_benchmark.json",
             "summary.json", "report.md")
    write_json(output / "manifest.json", {"schema": "crse-exact-representation-dispatcher-artifacts/v1",
        "status": "complete", "files_sha256": {name: sha(output / name) for name in files},
        "source_sha256": before, "retained_c6_manifest_sha256": retained_c6["manifest_sha256"],
        "retained_c7_manifest_sha256": retained_c7["manifest_sha256"]})
    return result
