"""Reproducible, local-only learning versus computation pilot.

This is ordinary research code, not an OS sandbox or a controller effect. Its
time budget is cooperative between bounded calls, not hard process containment.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from bitset_backend import build_bitset_env
from cm_expr_serde import expr_to_json_dag

from .corpus import Case, FAMILIES, make_corpus
from .features import FEATURE_NAMES, IneligibleExpression, extract_features, structural_digest
from .learning import CostTree, fit_cost_tree
from .portfolio import BACKENDS, admit, prepare, reference_bits
from .routing import FeatureRouter, fit_router, query_rule, routing_features


@dataclass(frozen=True)
class Config:
    seed: int = 20260828
    train_per_family: int = 12
    validation_per_family: int = 4
    test_per_family: int = 4
    sizes: tuple[int, ...] = (6, 8, 10)
    query_counts: tuple[int, ...] = (1, 8, 64)
    held_out_family: str = "mux"
    rounds: int = 3
    max_seconds: float = 120.0
    feature_ablation: bool = False
    learned_enabled: bool = True

    def validate(self) -> None:
        if type(self.feature_ablation) is not bool or type(self.learned_enabled) is not bool:
            raise ValueError("ablation and learned-advice switches must be Boolean")
        if type(self.seed) is not int or not 0 <= self.seed <= 2**32 - 1:
            raise ValueError("seed must be an unsigned 32-bit integer")
        if type(self.rounds) is not int or not 1 <= self.rounds <= 7:
            raise ValueError("rounds must be in 1..7")
        if (type(self.max_seconds) not in (int, float) or not math.isfinite(self.max_seconds)
                or not 0 < self.max_seconds <= 600):
            raise ValueError("cooperative budget must be in (0, 600] seconds")
        if self.held_out_family not in FAMILIES:
            raise ValueError("unknown held-out family")
        for count in (self.train_per_family, self.validation_per_family, self.test_per_family):
            if type(count) is not int or not 1 <= count <= 32:
                raise ValueError("per-family counts must be in 1..32")
        if not 1 <= len(self.sizes) <= 15 or any(type(n) is not int or not 2 <= n <= 16 for n in self.sizes):
            raise ValueError("sizes must be 2..16, with at most 15 entries")
        if not 1 <= len(self.query_counts) <= 8 or any(
            type(q) is not int or not 1 <= q <= 256 for q in self.query_counts
        ):
            raise ValueError("query counts must be 1..256, with at most eight entries")


class BudgetExhausted(RuntimeError):
    pass


class Budget:
    def __init__(self, seconds: float):
        self.started = time.perf_counter()
        self.seconds = seconds

    def check(self) -> None:
        if time.perf_counter() - self.started >= self.seconds:
            raise BudgetExhausted("cooperative experiment budget exhausted")


def _canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(data: Any) -> str:
    return hashlib.sha256(_canonical(data)).hexdigest()


def source_fingerprints() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    paths = [root / name for name in ("cm_exprlib.py", "cm_expr_serde.py", "cm_ir.py",
                                      "bitset_backend.py", "cmbench/__init__.py",
                                      "scripts/cm_recognition_experiment.py")]
    paths.extend(sorted(Path(__file__).parent.rglob("*.py")))
    paths.extend(sorted((root / "scripts").glob("cm_recognition_learning*.py")))
    paths.append(root / "cmbench/output_budget.py")
    for directory in ("expr", "backends", "results", "tracing"):
        paths.extend(sorted((root / "cmbench" / directory).rglob("*.py")))
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _rule(features: tuple[float, ...]) -> str:
    # Predeclared nonlearned heuristic, unchanged after any measurements.
    _, log_queries, log_nodes, _, sharing, _, _, _, same, complement = features
    if log_queries >= 3 and same + complement >= 0.08:
        return "cm"
    if sharing >= 0.10 or log_nodes >= 6:
        return "cse"
    return "direct"


def _measure(
    case: Case, arm: str, round_index: int, expected: int,
    model: CostTree | None, cache: dict[tuple[str, int], int],
    routers: dict[str, FeatureRouter] | None = None, learned_enabled: bool = True,
) -> dict[str, Any]:
    row = {
        "case_id": case.case_id, "family": case.family, "split": case.split,
        "n_vars": case.n_vars, "queries": case.queries, "round": round_index,
        "arm": arm, "selected": arm, "reason": "fixed", "status": "ok",
        "feature_ns": 0, "decision_ns": 0, "cache_hit": False,
        "total_ns": 0, "audit_ns": 0, "mismatches": 0, "error_type": "",
        "build_ns": 0, "kernel_ns": 0,
    }
    started = time.perf_counter_ns()
    try:
        backend = arm
        cached = None
        if arm.startswith("learned") and not learned_enabled:
            if model is None:
                raise ValueError("missing training fallback")
            backend, row["reason"] = model.fallback, "learned_disabled"
        elif arm == "query_rule":
            t0 = time.perf_counter_ns()
            backend, row["reason"] = query_rule(case.queries), "predeclared_query_rule"
            row["decision_ns"] = time.perf_counter_ns() - t0
        elif routers and arm in routers:
            router = routers[arm]
            t0 = time.perf_counter_ns()
            values = routing_features(case.expr, case.n_vars, case.queries, router.feature_schema)
            t1 = time.perf_counter_ns()
            decision = router.select(values)
            backend, row["reason"] = decision.backend, decision.reason
            row["feature_ns"] = t1 - t0
            row["decision_ns"] = time.perf_counter_ns() - t1
        elif arm in ("learned", "rule"):
            t0 = time.perf_counter_ns()
            values = extract_features(case.expr, case.n_vars, case.queries).values
            t1 = time.perf_counter_ns()
            if arm == "learned":
                if model is None:
                    raise ValueError("missing model")
                decision = model.select(values)
                backend, row["reason"] = decision.backend, decision.reason
            else:
                backend, row["reason"] = _rule(values), "predeclared_rule"
            row["feature_ns"] = t1 - t0
            row["decision_ns"] = time.perf_counter_ns() - t1
        elif arm == "exact_cache":
            if model is None:
                raise ValueError("missing training fallback")
            cached = cache.get((structural_digest(case.expr), case.n_vars))
            row["cache_hit"] = cached is not None
            row["reason"] = "frozen_training_cache_hit" if cached is not None else "cache_miss"
            backend = model.fallback
        row["selected"] = backend
        if cached is not None:
            outputs = [cached for _ in range(case.queries)]
        else:
            build_started = time.perf_counter_ns()
            evaluate = prepare(backend, case.expr, case.n_vars)
            row["build_ns"] = time.perf_counter_ns() - build_started
            kernel_started = time.perf_counter_ns()
            outputs = [evaluate() for _ in range(case.queries)]
            row["kernel_ns"] = time.perf_counter_ns() - kernel_started
        row["total_ns"] = max(1, time.perf_counter_ns() - started)
        audit_started = time.perf_counter_ns()
        row["mismatches"] = sum(type(value) is not int or value != expected for value in outputs)
        row["audit_ns"] = time.perf_counter_ns() - audit_started
        if row["mismatches"]:
            row["status"] = "mismatch"
    except Exception as exc:
        row["total_ns"] = max(1, time.perf_counter_ns() - started)
        row["status"] = "memory_error" if isinstance(exc, MemoryError) else "error"
        row["error_type"] = type(exc).__name__
    return row


def _geomean(values: list[float]) -> float:
    return math.exp(statistics.fmean(math.log(v) for v in values))


def summarize(rows: list[dict[str, Any]], fallback: str, rounds: int) -> dict[str, Any]:
    """Pair within formula, aggregate medians; timing rounds are not samples."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    metadata = {}
    for row in rows:
        grouped[(row["case_id"], row["arm"])].append(row)
        metadata[row["case_id"]] = (row["split"], row["family"])
    medians = {
        key: statistics.median(r["total_ns"] for r in values)
        for key, values in grouped.items()
        if len(values) == rounds and all(r["status"] == "ok" for r in values)
    }
    summaries = {}
    scopes = [(s, None) for s in ("validation", "test", "family_test")]
    scopes += [(s, f) for s in ("validation", "test", "family_test") for f in FAMILIES]
    for split, family in scopes:
        ids = [case_id for case_id, meta in metadata.items()
               if meta[0] == split and (family is None or meta[1] == family)]
        if not ids:
            continue
        eligible = [i for i in ids if all((i, b) in medians for b in BACKENDS)]
        info: dict[str, Any] = {"observed_instances": len(ids), "complete_baseline_instances": len(eligible)}
        if eligible:
            info["optimistic_oracle_speedup_over_fixed_train"] = _geomean([
                medians[(i, fallback)] / min(medians[(i, b)] for b in BACKENDS) for i in eligible
            ])
        arms = {}
        for arm in (*BACKENDS, "rule", "learned", "exact_cache", "query_rule",
                    "learned_queries", "learned_queries_depth"):
            paired = [i for i in eligible if (i, arm) in medians]
            if not paired:
                continue
            slowdowns = [medians[(i, arm)] / medians[(i, fallback)] for i in paired]
            ordered = sorted(slowdowns)
            arms[arm] = {
                "paired_instances": len(paired),
                "geomean_speedup_over_fixed_train": 1 / _geomean(slowdowns),
                "p95_slowdown_over_fixed_train": ordered[math.ceil(0.95 * len(ordered)) - 1],
                "p99_slowdown_over_fixed_train": ordered[math.ceil(0.99 * len(ordered)) - 1],
                "max_slowdown_over_fixed_train": max(slowdowns),
                "catastrophic_ge_2x": sum(s >= 2 for s in slowdowns),
                "mean_regret_over_oracle": statistics.fmean(
                    medians[(i, arm)] / min(medians[(i, b)] for b in BACKENDS) - 1 for i in paired
                ),
                "sum_instance_median_ns": sum(medians[(i, arm)] for i in paired),
            }
        info["arms"] = arms
        summaries[split if family is None else f"{split}/{family}"] = info
    return summaries


def run_experiment(config: Config, progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    config.validate()
    before = source_fingerprints()
    budget = Budget(config.max_seconds)
    cases = make_corpus(
        seed=config.seed, train=config.train_per_family, validation=config.validation_per_family,
        test=config.test_per_family, sizes=config.sizes, query_counts=config.query_counts,
        held_out_family=config.held_out_family,
    )
    documents = [{
        "case_id": c.case_id, "split": c.split, "family": c.family, "n_vars": c.n_vars,
        "queries": c.queries, "digest": c.digest, "group_digest": c.group_digest,
        "expression": expr_to_json_dag(c.expr),
    } for c in cases]
    rows: list[dict[str, Any]] = []
    case_audits = []
    training_x, training_y = [], []
    cache: dict[tuple[str, int], int] = {}
    model = None
    model_hash = None
    routers: dict[str, FeatureRouter] = {}
    router_hashes = {}
    status = "complete"
    error_type = ""
    fit_ns = train_wall_ns = 0
    train_started = time.perf_counter_ns()
    order_rng = random.Random(config.seed ^ 0x43525345)
    try:
        for split in ("train", "validation", "test", "family_test"):
            if progress:
                progress(f"{split}: measuring generated expressions")
            for case in (c for c in cases if c.split == split):
                budget.check()
                try:
                    features = admit(case.expr, case.n_vars, case.queries)
                except IneligibleExpression:
                    case_audits.append({"case_id": case.case_id, "status": "refused_input_limits"})
                    # No complete-case selection: a refused corpus aborts this
                    # pilot instead of silently dropping the difficult examples.
                    status = "refused_input_limits"
                    raise IneligibleExpression("generated corpus exceeds configured research bounds")
                reference_started = time.perf_counter_ns()
                expected = reference_bits(case.expr, case.n_vars)
                reference_ns = time.perf_counter_ns() - reference_started
                mask_started = time.perf_counter_ns()
                build_bitset_env(tuple(f"x{i}" for i in range(case.n_vars)))
                mask_ns = time.perf_counter_ns() - mask_started
                case_audits.append({
                    "case_id": case.case_id, "status": "ok", "reference_ns": reference_ns,
                    "common_mask_setup_ns": mask_ns, "features": list(features.values),
                    "identity_nodes": features.identity_nodes, "structural_nodes": features.structural_nodes,
                    "output_bits": 1 << case.n_vars,
                    "reference_sha256": hashlib.sha256(expected.to_bytes(
                        ((1 << case.n_vars) + 7) // 8, "little")).hexdigest(),
                })
                case_rows = []
                for round_index in range(config.rounds):
                    arms = list(BACKENDS) if model is None else [*BACKENDS, "rule", "learned", "exact_cache"]
                    if model is not None and config.feature_ablation:
                        arms += ["query_rule", *routers]
                    order_rng.shuffle(arms)
                    for arm in arms:
                        budget.check()
                        row = _measure(case, arm, round_index, expected, model, cache,
                                       routers, config.learned_enabled)
                        row["execution_index"] = len(rows)
                        rows.append(row)
                        case_rows.append(row)
                        budget.check()
                if any(row["status"] != "ok" for row in case_rows):
                    status = "backend_failure"
                    raise RuntimeError("backend error or semantic mismatch; pilot not accepted")
                if split == "train":
                    training_x.append(features.values)
                    training_y.append([
                        statistics.median(r["total_ns"] for r in case_rows if r["arm"] == b)
                        for b in BACKENDS
                    ])
                    cache[(case.digest, case.n_vars)] = expected
            if split == "train":
                budget.check()
                fit_started = time.perf_counter_ns()
                model = fit_cost_tree(training_x, training_y)
                if config.feature_ablation:
                    routers = {name: fit_router(training_x, training_y, schema) for name, schema in (
                        ("learned_queries", "queries/v1"), ("learned_queries_depth", "queries-depth/v1"))}
                    router_hashes = {name: _sha(router.to_dict()) for name, router in routers.items()}
                fit_ns = time.perf_counter_ns() - fit_started
                model_hash = _sha(model.to_dict())
                train_wall_ns = time.perf_counter_ns() - train_started
                if progress:
                    progress(f"Model frozen; training-selected constant baseline: {model.fallback}")
    except BudgetExhausted as exc:
        status, error_type = "budget_exhausted", type(exc).__name__
    except KeyboardInterrupt as exc:
        status, error_type = "interrupted", type(exc).__name__
    except (IneligibleExpression, RuntimeError) as exc:
        if status == "complete":
            status = "error"
        error_type = type(exc).__name__
    after = source_fingerprints()
    if before != after:
        status = "source_changed_during_run"
    frozen_unchanged = model is not None and _sha(model.to_dict()) == model_hash
    frozen_unchanged = frozen_unchanged and all(_sha(router.to_dict()) == router_hashes[name]
                                               for name, router in routers.items())
    if model is not None and not frozen_unchanged:
        status = "model_changed_during_evaluation"
    summary = summarize(rows, model.fallback, config.rounds) if model is not None else {}
    # An observed amortization estimate, not a generalization or speedup claim.
    break_even = None
    held = summary.get("test", {}).get("arms", {})
    if model is not None and model.fallback in held and "learned" in held:
        fixed, learned = held[model.fallback], held["learned"]
        if fixed["paired_instances"] == learned["paired_instances"]:
            saving = (fixed["sum_instance_median_ns"] - learned["sum_instance_median_ns"]) / fixed["paired_instances"]
            if saving > 0:
                break_even = math.ceil(train_wall_ns / saving)
    return {
        "schema": "crse-local-research/v1", "status": status, "error_type": error_type,
        "config": asdict(config), "source_sha256": before, "source_unchanged": before == after,
        "environment": {"python": sys.version, "numpy": np.__version__,
                        "platform": platform.platform(), "processor": platform.processor()},
        "timing_contract": "fresh_program_warm_variable_masks_build_plus_queries/v1",
        "audit_outside_algorithm_timing": True, "hard_process_containment": False,
        "model_frozen_before_evaluation": frozen_unchanged,
        "training_only_fallback": model.fallback if model else None,
        "model_sha256": model_hash, "corpus_sha256": _sha(documents),
        "feature_names": list(FEATURE_NAMES), "model": model.to_dict() if model else None,
        "router_models": {name: router.to_dict() for name, router in routers.items()},
        "router_sha256": router_hashes,
        "fit_ns": fit_ns, "training_wall_ns": train_wall_ns,
        "wall_seconds": time.perf_counter() - budget.started,
        "observed_training_break_even_sessions": break_even,
        "planned_split_counts": dict(Counter(c.split for c in cases)),
        "row_status_counts": dict(Counter(r["status"] for r in rows)),
        "learned_decisions": dict(Counter(r["reason"] for r in rows if r["arm"] == "learned")),
        "cache_hits_on_evaluation": sum(r["cache_hit"] for r in rows if r["arm"] == "exact_cache"),
        "semantic_mismatches": sum(r["mismatches"] for r in rows),
        "summary": summary, "case_audits": case_audits, "rows": rows, "corpus": documents,
        "scientific_claim": "exploratory generated-corpus pilot; no established general speedup",
    }


def render_report(result: dict[str, Any]) -> str:
    lines = ["# CRSE local research pilot", "", f"Status: {result['status']}", "",
             "Windows launcher/VM work is deferred. This run uses ordinary local Python only.", "",
             f"Training-selected fixed baseline: {result['training_only_fallback']}",
             f"Semantic mismatches: {result['semantic_mismatches']}",
             f"Frozen training-cache hits on evaluation: {result['cache_hits_on_evaluation']}", "",
             "Speedup is fixed-training-baseline time / arm time; above 1 is faster.",
             "Formula medians are paired; repeated rounds are not independent samples.", "",
             "| Split | Method | Formulas | Geomean speedup | p95 slowdown | >=2x slowdowns |",
             "| --- | --- | ---: | ---: | ---: | ---: |"]
    for split in ("validation", "test", "family_test"):
        for arm, stats in result["summary"].get(split, {}).get("arms", {}).items():
            lines.append(
                f"| {split} | {arm} | {stats['paired_instances']} | "
                f"{stats['geomean_speedup_over_fixed_train']:.3f} | "
                f"{stats['p95_slowdown_over_fixed_train']:.3f} | {stats['catastrophic_ge_2x']} |"
            )
    lines += ["", "## Scope and interpretation", "",
              "The learned policy selects exact algorithms; it does not predict truth values or learn new rewrite rules.",
              "Feature extraction and inference are included in the learned/rule timing windows.",
              "All arms rebuild their programs and recompute outputs; only input masks are warm/shared.",
              "Reference construction and equality audits are recorded separately and excluded equally for all arms.",
              "The exact-cache control contains training answers only and is never populated from evaluation data.",
              "The output is a complete packed truth vector (2^n bits), not SAT, counting, or a reduced representation.",
              "The CM arm means canonical CM IR plus the bigint flat executor, not dense CM matrix construction.",
              "The virtual best is an optimistic diagnostic on measured candidates, not a deployable algorithm.",
              "Budget checks are cooperative, not an OS sandbox or proof of hard termination.",
              "These synthetic, single-machine results do not establish large-scale or cross-machine generalization.",
              "No model is promoted into production. Slower results and failures remain in the records.", ""]
    return "\n".join(lines)


def write_artifacts(output: Path, result: dict[str, Any]) -> None:
    """Write only to a caller-created empty directory; never replace a file."""
    def write_json(name: str, data: Any) -> None:
        with (output / name).open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")

    summary = {key: value for key, value in result.items() if key not in ("rows", "corpus", "model")}
    write_json("summary.json", summary)
    write_json("corpus.json", result["corpus"])
    if result["model"] is not None:
        write_json("model.json", result["model"])
    if result.get("router_models"):
        write_json("router_models.json", result["router_models"])
    with (output / "raw.csv").open("x", encoding="utf-8", newline="") as handle:
        if result["rows"]:
            writer = csv.DictWriter(handle, fieldnames=list(result["rows"][0]))
            writer.writeheader()
            writer.writerows(result["rows"])
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    names = ["summary.json", "corpus.json", "raw.csv", "report.md"]
    if result["model"] is not None:
        names.append("model.json")
    if result.get("router_models"):
        names.append("router_models.json")
    if (output / "run_spec.json").is_file():
        names.append("run_spec.json")
    write_json("manifest.json", {
        "schema": "crse-local-artifacts/v1", "status": result["status"],
        "files_sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in names},
        "model_canonical_sha256": result["model_sha256"],
        "corpus_canonical_sha256": result["corpus_sha256"],
        "source_sha256": result["source_sha256"],
    })
