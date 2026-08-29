"""Finite, local neural motif experiment reusing CRSE exact execution and trees."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import random
import statistics
import sys
import time
import tracemalloc
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from bitset_backend import build_bitset_env
from .contracts import Proposal, RequestBudget, Task, check_proposal
from .experiment import Budget, BudgetExhausted, _measure, source_fingerprints
from .features import extract_features
from .learning import fit_cost_tree, load_model
from .models.mlp import MotifMLP, canonical, read_json, train_mlp
from .motif_data import SPLITS, case_from_document, make_motif_documents, validate_documents
from .portfolio import BACKENDS, admit, prepare, reference_bits
from .teacher import INPUT_SCHEMA, affine_candidate, is_affine, teach

ARMS = (*BACKENDS, "exact_cache", "exact_detector", "tiny_tree", "mlp", "mlp_cold")


@dataclass(frozen=True)
class MotifConfig:
    data_seed: int = 20260829
    training_seeds: tuple[int, ...] = (20260829, 20260830)
    parent_counts: tuple[int, ...] = (64, 16, 16, 8)
    epochs: int = 40
    batch_size: int = 32
    hidden: int = 128
    rounds: int = 3
    max_seconds: float = 120.0
    request_seconds: float = 1.0
    learned_enabled: bool = True

    def validate(self):
        for seed in (self.data_seed, *self.training_seeds):
            if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
                raise ValueError("invalid seed")
        if not 1 <= len(self.training_seeds) <= 3 or len(set(self.training_seeds)) != len(self.training_seeds):
            raise ValueError("one to three distinct training seeds required")
        if (type(self.parent_counts) is not tuple or len(self.parent_counts) != 4
                or any(type(n) is not int or not 1 <= n <= cap for n, cap in zip(self.parent_counts, (128, 64, 48, 16)))):
            raise ValueError("invalid finite parent counts")
        for value, cap in ((self.epochs, 100), (self.batch_size, 128), (self.hidden, 256), (self.rounds, 5)):
            if type(value) is not int or not 1 <= value <= cap:
                raise ValueError("invalid finite model or timing bound")
        if type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 120:
            raise ValueError("smoke wall budget must be in (0,120]")
        Task(8, max_seconds=self.request_seconds, learned_enabled=self.learned_enabled)

    def manifest(self, output: Path, phase: str):
        self.validate()
        return {"schema": "crse-motif-run-spec/v1", "phase": phase, "config": asdict(self),
                "planned_rows": 2 * sum(self.parent_counts) if phase in ("run", "dataset") else None,
                "input_row_limit": 512, "threads_requested": 1,
                "thread_environment": {name: os.environ.get(name) for name in
                    ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
                "device": "cpu", "memory_estimate_bytes": 256 * 1024 * 1024,
                "memory_limit_is_hard": False, "wall_limit_is_cooperative": True,
                "candidate_limit_per_request": 1, "fallback_budget_fraction": 0.5,
                "output": str(output.resolve()), "network": False,
                "task": "fresh expression -> Q identical complete truth vectors; recomputation and answer-cache arms separate",
                "input_schema": INPUT_SCHEMA, "threshold": 0.5, "tuning": "none",
                "practical_criteria": {"speedup_over_strongest_control": 1.10,
                    "max_p95_slowdown": 1.10, "accepted_semantic_errors": 0,
                    "no_increase_ge_2x": True, "promotion": "never automatic"},
                "source": "generated local Boolean fixtures; no external corpus or downloaded data",
                "license": "no third-party dataset; repository source and its existing terms retained"}


def _write_json(path: Path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def measure_motif(case, label, arm, model, tree, config, model_path=None):
    if arm not in ARMS:
        raise ValueError("unavailable or unknown motif backend")
    task = Task(case.n_vars, case.queries, config.request_seconds, config.learned_enabled)
    # Common admission/audit is outside ALL arm timers. Required acceptance proof is inside.
    admit(case.expr, case.n_vars, case.queries)
    expected = reference_bits(case.expr, case.n_vars)
    row = {"case_id": case.case_id, "family": case.family, "split": case.split,
           "group": case.group_digest, "queries": case.queries, "label": label, "arm": arm,
           "status": "ok", "selected": "cse", "reason": "fixed", "score": None,
           "feature_ns": 0, "inference_ns": 0, "candidate_ns": 0, "verification_ns": 0,
           "build_ns": 0, "kernel_ns": 0, "conversion_ns": 0, "model_load_ns": 0,
           "total_ns": 0, "audit_ns": 0, "mismatches": 0, "proposed": False,
           "accepted": False, "trace_json": "", "error_type": ""}
    started = time.perf_counter_ns()
    budget = RequestBudget(task)
    expr = case.expr
    backend = arm if arm in BACKENDS else "cse"
    try:
        if arm in ("mlp", "mlp_cold", "tiny_tree") and not config.learned_enabled:
            row["reason"] = "learned_disabled"
        elif arm == "tiny_tree":
            t = time.perf_counter_ns()
            features = extract_features(expr, case.n_vars, case.queries).values
            row["feature_ns"] = time.perf_counter_ns() - t
            t = time.perf_counter_ns()
            decision = tree.select(features)
            backend, row["reason"] = decision.backend, decision.reason
            row["inference_ns"] = time.perf_counter_ns() - t
        elif arm in ("mlp", "mlp_cold", "exact_detector"):
            try:
                budget.check(proposal=True)
                if arm == "mlp_cold":
                    t = time.perf_counter_ns()
                    model = MotifMLP.load(model_path)
                    row["model_load_ns"] = time.perf_counter_ns() - t
                t = time.perf_counter_ns()
                cm = teach(expr, case.n_vars)
                values = cm.tensor() if arm != "exact_detector" else None
                row["feature_ns"] = time.perf_counter_ns() - t
                t = time.perf_counter_ns()
                score = float(is_affine(cm)) if arm == "exact_detector" else model.score(values)
                if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
                    raise ValueError("invalid motif probability")
                row["score"] = score
                row["inference_ns"] = time.perf_counter_ns() - t
                budget.check(proposal=True)
                row["reason"] = "abstained"
                if score >= 0.5:
                    t = time.perf_counter_ns()
                    candidate = affine_candidate(cm)
                    proposal = Proposal(case.digest, candidate,
                        "handwritten" if arm == "exact_detector" else "learned",
                        "exact-affine-detector/v1" if arm == "exact_detector" else model.artifact_digest or "unsaved-test-model", score)
                    row["proposed"] = True
                    row["candidate_ns"] = time.perf_counter_ns() - t
                    checked = check_proposal(expr, proposal, task, budget)
                    row["verification_ns"] = checked.check_ns
                    row["accepted"], row["reason"] = checked.accepted, checked.reason
                    row["trace_json"] = json.dumps({**checked.to_dict(), "origin": proposal.origin,
                        "model_version": proposal.model_version, "substitution": "root boundary; original variable identities",
                        "side_conditions": ["same declared universe", "strict structural-node reduction"],
                        "candidate_budget": 1, "predicted_cost": None, "predicted_probability": score,
                        "prediction_kind": "uncalibrated motif probability, not cost or proof",
                        "proof_scope": "this instance only, not a rule over metavariables"}, sort_keys=True)
                    if checked.accepted:
                        expr = candidate
            except TimeoutError:
                row["reason"] = "proposal_timeout_fallback"
            except (ValueError, OSError, TypeError, AttributeError):
                row["reason"] = "invalid_model_or_proposal_fallback"
        budget.check()
        row["selected"] = backend
        t = time.perf_counter_ns()
        evaluate = prepare(backend, expr, case.n_vars)
        row["build_ns"] = time.perf_counter_ns() - t
        t = time.perf_counter_ns()
        if arm == "exact_cache":
            answer = evaluate()
            outputs = [answer] * case.queries
        else:
            outputs = [evaluate() for _ in range(case.queries)]
        row["kernel_ns"] = time.perf_counter_ns() - t
        budget.check()
        row["total_ns"] = max(1, time.perf_counter_ns() - started)
        t = time.perf_counter_ns()
        row["mismatches"] = sum(type(answer) is not int or answer != expected for answer in outputs)
        row["audit_ns"] = time.perf_counter_ns() - t
        if row["mismatches"]:
            row["status"] = "mismatch"
    except Exception as exc:
        row["total_ns"] = max(1, time.perf_counter_ns() - started)
        row["error_type"] = type(exc).__name__
        row["status"] = "timeout" if isinstance(exc, TimeoutError) else "oom" if isinstance(exc, MemoryError) else "error"
    return row


def summarize_motifs(rows, rounds):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["seed"], row["split"], row["case_id"], row["arm"])].append(row)
    medians = {key: statistics.median(r["total_ns"] for r in values) for key, values in grouped.items()
               if len(values) == rounds and all(r["status"] == "ok" for r in values)}
    summaries = {}
    for seed in sorted({r["seed"] for r in rows}):
        for split in SPLITS[1:]:
            ids = sorted({r["case_id"] for r in rows if r["seed"] == seed and r["split"] == split})
            for arm in ARMS:
                selected = [i for i in ids if all((seed, split, i, a) in medians for a in (arm, "cse", "exact_cache", "direct", "cm", "exact_detector"))]
                if not selected:
                    continue
                ratios, strongest, ns = [], [], []
                for case_id in selected:
                    cost = medians[(seed, split, case_id, arm)]
                    ratios.append(cost / medians[(seed, split, case_id, "cse")])
                    best = min(medians[(seed, split, case_id, a)] for a in ("direct", "cse", "cm", "exact_cache", "exact_detector"))
                    strongest.append(cost / best)
                    ns.append(cost)
                ordered = sorted(ratios)
                summaries[f"{seed}/{split}/{arm}"] = {
                    "instances": len(selected), "geomean_speedup_over_cse": math.exp(-statistics.fmean(map(math.log, ratios))),
                    "geomean_speedup_over_virtual_best_nonlearned": math.exp(-statistics.fmean(map(math.log, strongest))),
                    "virtual_best_is_oracle_not_deployable": True,
                    "p95_slowdown_over_cse": ordered[math.ceil(.95 * len(ordered)) - 1],
                    "p99_slowdown_over_cse": ordered[math.ceil(.99 * len(ordered)) - 1],
                    "max_slowdown_over_cse": max(ratios), "ge_2x": sum(r >= 2 for r in ratios),
                    "mean_regret_over_nonlearned_oracle": statistics.fmean(strongest) - 1,
                    "sum_instance_median_ns": sum(ns),
                    "clustered_ci95": None, "ci_limitation": "Only one held-out generating template/support group per split; no independent-cluster interval justified."}
    return summaries


def classification_summary(rows):
    """One observation per case/seed/arm, not one independent sample per round."""
    groups = defaultdict(list)
    for row in rows:
        if row["round"] == 0 and row["score"] is not None:
            groups[f"{row['seed']}/{row['split']}/{row['arm']}"].append(row)
    result = {}
    for key, values in groups.items():
        tp = sum(r["score"] >= .5 and r["label"] == 1 for r in values)
        fp = sum(r["score"] >= .5 and r["label"] == 0 for r in values)
        fn = sum(r["score"] < .5 and r["label"] == 1 for r in values)
        result[key] = {"cases": len(values), "true_positive": tp, "false_positive": fp, "false_negative": fn,
            "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
            "proposal_coverage": sum(r["proposed"] for r in values) / len(values),
            "accepted_coverage": sum(r["accepted"] for r in values) / len(values),
            "abstention_rate": sum(not r["proposed"] for r in values) / len(values),
            "rejection_count": sum(r["proposed"] and not r["accepted"] for r in values),
            "accepted_false_positives": sum(r["accepted"] and not r["label"] for r in values),
            "brier_score": statistics.fmean((r["score"] - r["label"]) ** 2 for r in values),
            "calibration": "descriptive Brier score only; no fitted calibration or confidence guarantee"}
    return result


def run_motif_experiment(config: MotifConfig, output: Path, *, phase="run", input_dir=None, progress=print):
    config.validate()
    if phase not in ("run", "dataset", "train", "evaluate"):
        raise ValueError("unknown experiment phase")
    if phase in ("train", "evaluate") and input_dir is None:
        raise ValueError("phase requires an input artifact directory")
    output.mkdir(parents=True, exist_ok=False)
    spec = config.manifest(output, phase)
    before = source_fingerprints()
    _write_json(output / "run_spec.json", {**spec, "source_sha256": before, "status": "planned"})
    budget = Budget(config.max_seconds)
    rows, training_rows, model_cards = [], [], []
    documents = []
    models = []
    tree = None
    status = "incomplete"
    error_type = ""
    timings = {}
    leakage = {}
    memory = {}
    try:
        t = time.perf_counter_ns()
        progress("Dataset: exact labels and grouped split checks")
        if phase in ("run", "dataset"):
            documents = make_motif_documents(config.data_seed, config.parent_counts, budget.check)
        else:
            documents = read_json(Path(input_dir) / "corpus.json", 16 * 1024 * 1024)
        leakage = validate_documents(documents, budget.check)
        _write_json(output / "corpus.json", documents)
        data_hash = hashlib.sha256(canonical(documents)).hexdigest()
        timings["dataset_and_check_ns"] = time.perf_counter_ns() - t
        cases = [case_from_document(d) for d in documents]
        labels = {d["case_id"]: d["label"] for d in documents}
        for n in {c.n_vars for c in cases}:
            build_bitset_env(tuple(f"x{i}" for i in range(n)))
        if phase in ("run", "train"):
            progress("Training: measure exact controls, freeze cost tree, train bounded MLP seeds")
            training = [c for c in cases if c.split == "train"]
            xs, costs = [], []
            order_rng = random.Random(config.data_seed)
            t = time.perf_counter_ns()
            for case in training:
                budget.check()
                expected = reference_bits(case.expr, 8)
                current = []
                for round_index in range(config.rounds):
                    arms = list(BACKENDS)
                    order_rng.shuffle(arms)
                    for arm in arms:
                        budget.check()
                        row = _measure(case, arm, round_index, expected, None, {})
                        row["execution_index"] = len(training_rows)
                        training_rows.append(row)
                        current.append(row)
                        if row["status"] != "ok":
                            raise RuntimeError("training backend failure retained")
                xs.append(extract_features(case.expr, 8, case.queries).values)
                costs.append([statistics.median(r["total_ns"] for r in current if r["arm"] == b) for b in BACKENDS])
            tree = fit_cost_tree(xs, costs)
            _write_json(output / "router.json", tree.to_dict())
            timings["training_cost_table_and_tree_ns"] = time.perf_counter_ns() - t
            x = np.stack([teach(c.expr, 8).tensor() for c in training])
            y = np.array([labels[c.case_id] for c in training], dtype=np.float32)
            for seed in config.training_seeds:
                budget.check()
                t = time.perf_counter_ns()
                model = train_mlp(x, y, seed=seed, epochs=config.epochs, batch_size=config.batch_size,
                                  hidden=config.hidden, check=budget.check)
                fit_ns = time.perf_counter_ns() - t
                model.training.update({"dataset_sha256": data_hash,
                    "training_ids_sha256": hashlib.sha256(canonical([c.case_id for c in training])).hexdigest()})
                model_path = output / f"model-{seed}.json"
                model.save(model_path)
                t = time.perf_counter_ns()
                loaded = MotifMLP.load(model_path)
                load_ns = time.perf_counter_ns() - t
                if not model.training["parameters_updated"] or not np.array_equal(model.predict(x), loaded.predict(x)):
                    raise RuntimeError("actual learning or reload agreement failed")
                models.append((seed, loaded, model_path))
                model_cards.append({"seed": seed, "file": model_path.name, "parameters": model.parameter_count,
                    "layers": [512, config.hidden, 1], "activations": ["relu", "sigmoid"],
                    "weights_dtype": "float32", "parameter_bytes": model.parameter_count * 4,
                    "graph_memory_bytes": None, "graph_memory_reason": "matrix MLP, no graph model",
                    "fit_ns": fit_ns, "reload_ns": load_ns, "reload_predictions_identical": True,
                    "serialized_bytes": model_path.stat().st_size,
                    "training": model.training})
            _write_json(output / "model_index.json", {"schema": "crse-motif-model-index/v1", "dataset_sha256": data_hash,
                "model_files": [p.name for _, _, p in models], "router_sha256": hashlib.sha256((output / "router.json").read_bytes()).hexdigest()})
        elif phase == "evaluate":
            index = read_json(Path(input_dir) / "model_index.json")
            if index.get("schema") != "crse-motif-model-index/v1" or index.get("dataset_sha256") != data_hash:
                raise ValueError("model/dataset identity mismatch")
            filenames = index.get("model_files")
            import re
            if (type(filenames) is not list or not 1 <= len(filenames) <= 3 or len(set(filenames)) != len(filenames)
                    or any(type(name) is not str or re.fullmatch(r"model-[0-9]{1,10}\.json", name) is None for name in filenames)):
                raise ValueError("invalid model file index")
            tree_path = Path(input_dir) / "router.json"
            tree = load_model(tree_path)
            if hashlib.sha256(tree_path.read_bytes()).hexdigest() != index["router_sha256"]:
                raise ValueError("router hash mismatch")
            _write_json(output / "router.json", tree.to_dict())
            for name in filenames:
                model = MotifMLP.load(Path(input_dir) / name)
                if model.training.get("dataset_sha256") != data_hash:
                    raise ValueError("stale model training dataset")
                path = output / name
                model.save(path)
                models.append((model.training["seed"], model, path))
                model_cards.append({"seed": model.training["seed"], "file": name,
                                    "parameters": model.parameter_count, "training": model.training})
        if phase in ("run", "evaluate"):
            frozen = {seed: hashlib.sha256(canonical(model.to_dict())).hexdigest() for seed, model, _ in models}
            progress("Evaluation: models frozen; validation, exploratory test, then sealed confirmation")
            t = time.perf_counter_ns()
            for seed, model, path in models:
                order_rng = random.Random(seed ^ config.data_seed)
                for split in SPLITS[1:]:
                    for case in (c for c in cases if c.split == split):
                        arms = list(ARMS)
                        order_rng.shuffle(arms)
                        for round_index in range(config.rounds):
                            # Rotate the first order to counterbalance position across rounds.
                            ordered = arms[round_index:] + arms[:round_index]
                            for arm in ordered:
                                budget.check()
                                row = measure_motif(case, labels[case.case_id], arm, model, tree, config, path)
                                row.update({"seed": seed, "round": round_index, "execution_index": len(rows)})
                                rows.append(row)
                                if row["status"] != "ok":
                                    raise RuntimeError("evaluation failure retained; run not accepted")
            timings["evaluation_ns"] = time.perf_counter_ns() - t
            if any(hashlib.sha256(canonical(model.to_dict())).hexdigest() != frozen[seed] for seed, model, _ in models):
                raise RuntimeError("model changed during evaluation")
            # Separate allocation probe: never turn tracing overhead into benchmark latency.
            budget.check()
            probe_case = next(c for c in cases if c.split == "train")
            seed, model, path = models[0]
            tracemalloc.start()
            try:
                probe = measure_motif(probe_case, labels[probe_case.case_id], "mlp", model, tree, config, path)
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            memory = {"separate_mlp_allocation_probe_peak_bytes": peak, "probe_status": probe["status"],
                      "scope": "tracemalloc-visible allocations in one training-case request; not process RSS or a hard limit"}
        budget.check()
        status = "complete"
    except (KeyboardInterrupt, Exception) as exc:
        status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "budget_exhausted" if isinstance(exc, BudgetExhausted) else "failed"
        error_type = type(exc).__name__
        progress(f"Incomplete run retained: {error_type}: {exc}")
    after = source_fingerprints()
    if before != after:
        status = "source_changed_during_run"
    result = {"schema": "crse-motif-experiment/v1", "status": status, "phase": phase, "error_type": error_type,
        "config": asdict(config), "source_sha256": before, "source_unchanged": before == after,
        "dataset_sha256": hashlib.sha256(canonical(documents)).hexdigest(), "leakage_checks": leakage,
        "environment": {"python": sys.version, "numpy": np.__version__, "platform": platform.platform(),
                        "processor": platform.processor()}, "model_cards": model_cards, "timings": timings,
        "wall_seconds": time.perf_counter() - budget.started, "memory": memory,
        "rows": rows, "training_rows": training_rows,
        "summary": summarize_motifs(rows, config.rounds),
        "classification": classification_summary(rows),
        "timer_resolution_seconds": time.get_clock_info("perf_counter").resolution,
        "timing_noise_control": "paired case medians, randomized initial arm order, rotated rounds; no speed assertions",
        "failure_rates": {kind: sum(r["status"] == kind for r in rows) / len(rows) if rows else None
                          for kind in ("timeout", "oom", "error", "mismatch")},
        "row_status_counts": dict(Counter(r["status"] for r in rows)),
        "semantic_mismatches": sum(r["mismatches"] for r in rows),
        "proposal_reasons": dict(Counter(r["reason"] for r in rows)),
        "scientific_claim": "bounded generated mechanism smoke only; no natural-source or cross-machine replication"}
    _write_json(output / "summary.json", {k: v for k, v in result.items() if k not in ("rows", "training_rows")})
    for name, records in (("raw.csv", rows), ("training_raw.csv", training_rows)):
        with (output / name).open("x", encoding="utf-8", newline="") as handle:
            if records:
                writer = csv.DictWriter(handle, fieldnames=list(records[0]))
                writer.writeheader()
                writer.writerows(records)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_motif_report(result))
    names = sorted(p.name for p in output.iterdir() if p.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-motif-artifacts/v1", "status": status,
        "files_sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in names},
        "source_sha256": before})
    return result


def render_motif_report(result):
    lines = ["# CRSE exact-checked neural motif smoke", "", f"Status: {result['status']}; phase: {result['phase']}",
        f"Dataset SHA-256: {result['dataset_sha256']}", f"Semantic output mismatches: {result['semantic_mismatches']}", "",
        "| Seed / split / arm | Cases | Speedup vs CSE | p95 slowdown | >=2x |", "| --- | ---: | ---: | ---: | ---: |"]
    for key, values in result["summary"].items():
        lines.append(f"| {key} | {values['instances']} | {values['geomean_speedup_over_cse']:.3f} | "
                     f"{values['p95_slowdown_over_cse']:.3f} | {values['ge_2x']} |")
    lines += ["", "## Interpretation", "",
        "The MLP is trained by minibatch SGD, saved as bounded hashed float32 tensors in JSON, reloaded, and evaluated.",
        "It predicts affine motif probability, not truth values, proof, or profitability. Every applied proposal passes independent full-reference equivalence and node-reduction checks.",
        "CM construction, feature conversion, inference, proposal generation, acceptance proof, backend build and queries are inside total time; cold cells also load the model.",
        "Common admission and output audit are outside all timers. Model preprocessing uses training rows only. No test-dependent tuning occurs.",
        "The exact-cache arm computes once per request and reuses the identical answer. Recomputed Q queries are not a natural session trace.",
        "The cm arm is the original deterministic CM-IR simplifier; tiny_tree is the existing cost router fitted to measured training costs.",
        "Only root affine motifs and one-bit near-matches at ambient eight are tested. Variable-permuted/output-complemented siblings and source templates stay within their split.",
        "Held-out template/support clusters are too few for meaningful clustered confidence intervals. Two training seeds are not independent source or machine replication.",
        "The probability is uncalibrated. Matrix construction already obtains the answer, so exact direct/cache controls are essential and may dominate.",
        "Timeout checks are cooperative, with half the request reserved for fallback; no OS containment is claimed. Interrupted/failed runs are not accepted.",
        "CNN/GNN/fused inputs, generalized rules, live LLMs, natural data and all other tracks remain separately pending. No model is promoted.", ""]
    return "\n".join(lines)
