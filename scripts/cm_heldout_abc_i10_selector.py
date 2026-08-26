#!/usr/bin/env python3
"""Preregistered Berkeley ABC i10 held-out engine-selector study.

Stages are intentionally separate so source/cone screening and model fitting
are frozen before any held-out timing is observed. Every artifact refuses
overwrite. See the dated preregistration beside the downloaded source.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import platform
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cm_expr_serde import expr_to_json_dag  # noqa: E402
from cm_ir import expr_structural_hash  # noqa: E402
from scripts import cm_deep_performance_audit as audit  # noqa: E402
from scripts.cm_benchmark_provenance import capture_source_snapshot  # noqa: E402


BASE = ROOT / "deliverables_n22_24" / "heldout_abc_i10_2026_08_26"
SOURCE = BASE / "source" / "i10.aig"
SOURCE_NOTICE = BASE / "source" / "copyright.txt"
SOURCE_MANIFEST = BASE / "source_manifest.json"
PREREGISTRATION = BASE / "CM_ABC_I10_HELDOUT_SELECTOR_PREREGISTRATION_2026-08-26.md"
CORPUS = BASE / "abc_i10_heldout_corpus.jsonl"
SCREENING = BASE / "abc_i10_screening.json"
MODEL = BASE / "abc_i10_selector_model_frozen.json"
RAW = BASE / "abc_i10_heldout_raw.csv"
ENVIRONMENT = BASE / "abc_i10_heldout_environment.json"
DECISIONS = BASE / "abc_i10_selector_decisions.csv"
SUMMARY = BASE / "abc_i10_selector_summary.csv"
AUDIT = BASE / "abc_i10_selector_audit.json"
SNAPSHOT = BASE / "abc_i10_measure_source_snapshot"
TRAINING = (
    ROOT
    / "docs"
    / "audits"
    / "2026-08-25-cm-deep-performance"
    / "reruns"
    / "campaign-20260826-132038"
    / "deep_representative_raw.csv"
)
EXTRACTOR_PATH = ROOT / "deliverables_n22_24" / "cm_gap_epfl_extract_2026_08_03.py"
SOURCE_PATHS = audit.SOURCE_PATHS + (
    "deliverables_n22_24/cm_gap_epfl_extract_2026_08_03.py",
    "scripts/cm_heldout_abc_i10_selector.py",
)

EXPECTED_SOURCE_SHA256 = "b551b0932703d7d3c5e3b3cd0fc742b484d0f5d8332b1bf3dd7567679d1559d7"
EXPECTED_NOTICE_SHA256 = "819151b8f059a48f806c75732ef62b1f873b49b6a04fb128aed28bf87d3dcd6c"
UPSTREAM_COMMIT = "c6e8823c0b9f0c7c469a7538dc2a75b39da17cc4"
SEMANTIC_K = tuple(range(8, 17))
PER_K_CAP = 16
MIN_ROWS = 32
MIN_K_STRATA = 3
AND_CAP = 5_000
RIDGE_LAMBDAS = (0.01, 0.1, 1.0, 10.0, 100.0)
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20260826


def _load_extractor():
    spec = importlib.util.spec_from_file_location("cm_gap_epfl_extract", EXTRACTOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load extractor: {EXTRACTOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refuse(paths: Sequence[Path]) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise FileExistsError("refusing to overwrite: " + ", ".join(existing))


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _select_evenly(rows: Sequence[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if count <= 0 or not rows:
        return []
    if len(rows) <= count:
        return list(rows)
    if count == 1:
        return [rows[0]]
    indices = [(index * (len(rows) - 1)) // (count - 1) for index in range(count)]
    return [rows[index] for index in indices]


def _source_gate() -> dict[str, Any]:
    if not SOURCE.is_file() or not SOURCE_NOTICE.is_file():
        raise FileNotFoundError("approved ABC source files are missing")
    source_sha = _sha(SOURCE)
    notice_sha = _sha(SOURCE_NOTICE)
    if source_sha != EXPECTED_SOURCE_SHA256 or notice_sha != EXPECTED_NOTICE_SHA256:
        raise RuntimeError("frozen ABC source hash mismatch")
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("commit") != UPSTREAM_COMMIT:
        raise RuntimeError("source manifest commit mismatch")
    return {
        "upstream_commit": UPSTREAM_COMMIT,
        "source_sha256": source_sha,
        "notice_sha256": notice_sha,
        "source_bytes": SOURCE.stat().st_size,
        "notice_bytes": SOURCE_NOTICE.stat().st_size,
        "source_manifest_sha256": _sha(SOURCE_MANIFEST),
        "preregistration_sha256": _sha(PREREGISTRATION),
    }


def extract() -> dict[str, Any]:
    _refuse((CORPUS, SCREENING))
    BASE.mkdir(parents=True, exist_ok=True)
    source = _source_gate()
    ext = _load_extractor()
    aig = ext.parse_aig(SOURCE)
    child, supports = ext.build_tables(aig)
    rejects: Counter[str] = Counter()
    duplicates: Counter[str] = Counter()
    qualified: dict[str, list[dict[str, Any]]] = {"po": [], "internal": []}
    seen: dict[tuple[str, str], str] = {}

    def qualify(root_lit: int, kind: str, index: int) -> None:
        node_index = root_lit >> 1
        if node_index == 0:
            rejects[f"{kind}:constant_root"] += 1
            return
        if child[node_index] is None:
            rejects[f"{kind}:input_or_invalid_root"] += 1
            return
        syntactic_support = supports[node_index]
        if syntactic_support is None:
            rejects[f"{kind}:syntactic_support_gt16"] += 1
            return
        n_ands, uses_constant, _seen_nodes = ext.cone_stats(node_index, child)
        if uses_constant:
            rejects[f"{kind}:constant_literal"] += 1
            return
        if n_ands > AND_CAP:
            rejects[f"{kind}:and_cap"] += 1
            return
        syntactic_inputs = sorted(syntactic_support)
        bits, full = ext.cone_truth_bigint(root_lit, child, syntactic_inputs)
        if bits in (0, full):
            rejects[f"{kind}:constant_function"] += 1
            return
        semantic_inputs = ext.semantic_support(bits, syntactic_inputs)
        semantic_k = len(semantic_inputs)
        if semantic_k not in SEMANTIC_K:
            rejects[f"{kind}:semantic_support_out_of_range"] += 1
            return
        var_index = {input_index: position for position, input_index in enumerate(syntactic_inputs)}
        expr = ext.cone_to_expr(root_lit, child, var_index)
        structural_hash = expr_structural_hash(expr)
        truth_bytes = int(bits).to_bytes(max(1, (1 << len(syntactic_inputs)) // 8), "little")
        truth_sha = hashlib.sha256(truth_bytes).hexdigest()
        key = (structural_hash, truth_sha)
        identifier = f"abc-i10-{kind}{index}-k{semantic_k}-{structural_hash[:10]}"
        if key in seen:
            duplicates[kind] += 1
            return
        seen[key] = identifier
        unfolded = ext._tree_unfolded(expr)
        qualified[kind].append(
            {
                "id": identifier,
                "status": "admitted",
                "category": "berkeley_abc_demo",
                "circuit": "i10.aig",
                "circuit_sha256": source["source_sha256"],
                "upstream_commit": UPSTREAM_COMMIT,
                "root_kind": kind,
                "root_index": index,
                "root_literal": root_lit,
                "n_aig_ands": n_ands,
                "synt_support_inputs": syntactic_inputs,
                "synt_support_size": len(syntactic_inputs),
                "sem_support_inputs": semantic_inputs,
                "sem_support_size": semantic_k,
                "structural_hash": structural_hash,
                "truth_sha256": truth_sha,
                "unfolded_occurrences": unfolded,
                "raw_arm": (
                    "ok" if unfolded <= ext.RAW_UNFOLDED_CAP
                    else "raw_arm_skipped_unfolded_cap"
                ),
                "expression_v2": expr_to_json_dag(expr),
            }
        )

    for output_index, literal in enumerate(aig["outputs"]):
        qualify(literal, "po", output_index)
    for and_index, (lhs, _rhs0, _rhs1) in enumerate(aig["ands"]):
        qualify(lhs, "internal", and_index)

    selected: list[dict[str, Any]] = []
    selected_counts: dict[str, dict[str, int]] = {}
    qualified_counts: dict[str, dict[str, int]] = {}
    for live_k in SEMANTIC_K:
        po_rows = [row for row in qualified["po"] if row["sem_support_size"] == live_k]
        internal_rows = [
            row for row in qualified["internal"] if row["sem_support_size"] == live_k
        ]
        chosen_po = _select_evenly(po_rows, min(PER_K_CAP, len(po_rows)))
        remaining = PER_K_CAP - len(chosen_po)
        chosen_internal = _select_evenly(internal_rows, min(remaining, len(internal_rows)))
        selected.extend(chosen_po)
        selected.extend(chosen_internal)
        qualified_counts[str(live_k)] = {"po": len(po_rows), "internal": len(internal_rows)}
        selected_counts[str(live_k)] = {
            "po": len(chosen_po),
            "internal": len(chosen_internal),
        }

    selected.sort(
        key=lambda row: (
            int(row["sem_support_size"]),
            row["root_kind"] != "po",
            int(row["root_index"]),
        )
    )
    represented_k = sorted({int(row["sem_support_size"]) for row in selected})
    screening_pass = len(selected) >= MIN_ROWS and len(represented_k) >= MIN_K_STRATA
    metadata = {
        "record_type": "abc_i10_heldout_corpus_meta",
        "protocol": "CM_ABC_I10_HELDOUT_SELECTOR_PREREGISTRATION_2026-08-26.md",
        "source": source,
        "aiger": {key: aig[key] for key in ("format", "M", "I", "L", "O", "A")},
        "selection": {
            "semantic_k": SEMANTIC_K,
            "per_k_cap": PER_K_CAP,
            "minimum_rows": MIN_ROWS,
            "minimum_k_strata": MIN_K_STRATA,
        },
    }
    with CORPUS.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n")
        for row in selected:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    screening = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "aiger": metadata["aiger"],
        "qualified_counts_by_k": qualified_counts,
        "selected_counts_by_k": selected_counts,
        "selected_rows": len(selected),
        "represented_k": represented_k,
        "rejection_histogram": dict(sorted(rejects.items())),
        "duplicate_histogram": dict(sorted(duplicates.items())),
        "corpus_sha256": _sha(CORPUS),
        "screening_gate": {
            "minimum_rows": MIN_ROWS,
            "minimum_k_strata": MIN_K_STRATA,
            "pass": screening_pass,
        },
    }
    _write_json(SCREENING, screening)
    print(json.dumps(screening, indent=2, sort_keys=True))
    return screening


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_corpus() -> list[dict[str, Any]]:
    return [
        document
        for document in (
            json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines()
        )
        if "expression_v2" in document
    ]


def _timing_keys(arm: str) -> tuple[str, str]:
    return f"{arm}_flat_ns_median", f"{arm}_words_ns_median"


def _feature_vector(row: Mapping[str, Any], arm: str) -> list[float]:
    prefix = "cm" if arm == "cm" else "raw"
    peak = float(row.get("cm_peak_live_word_buffers") or 0.0) if arm == "cm" else 0.0
    return [
        float(row["live_k"]),
        math.log1p(float(row[f"{prefix}_instructions"])),
        math.log1p(float(row[f"{prefix}_executed_bigint_ops"])),
        math.log1p(float(row[f"{prefix}_executed_word_ops"])),
        math.log1p(peak),
        math.log1p(float(row["structural_dag_nodes_source"])),
        math.log1p(float(row["unfolded_tree_nodes"])),
    ]


def _eligible_training(rows: Sequence[Mapping[str, Any]], arm: str) -> list[Mapping[str, Any]]:
    flat_key, words_key = _timing_keys(arm)
    return [
        row
        for row in rows
        if row.get("corpus") == "bx1"
        and row.get(flat_key) not in (None, "")
        and row.get(words_key) not in (None, "")
    ]


def _fit_ridge(rows: Sequence[Mapping[str, Any]], arm: str, ridge_lambda: float) -> dict[str, Any]:
    x = np.asarray([_feature_vector(row, arm) for row in rows], dtype=np.float64)
    flat_key, words_key = _timing_keys(arm)
    y = np.asarray(
        [math.log(float(row[words_key]) / float(row[flat_key])) for row in rows],
        dtype=np.float64,
    )
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale == 0.0] = 1.0
    z = (x - mean) / scale
    y_mean = float(y.mean())
    identity = np.eye(z.shape[1], dtype=np.float64)
    coefficient = np.linalg.solve(
        z.T @ z + ridge_lambda * identity,
        z.T @ (y - y_mean),
    )
    return {
        "arm": arm,
        "ridge_lambda": ridge_lambda,
        "feature_names": [
            "live_k",
            "log1p_instructions",
            "log1p_executed_bigint_ops",
            "log1p_executed_word_ops",
            "log1p_peak_live_word_buffers",
            "log1p_structural_dag_nodes_source",
            "log1p_unfolded_tree_nodes",
        ],
        "feature_mean": mean.tolist(),
        "feature_scale": scale.tolist(),
        "intercept": y_mean,
        "coefficient": coefficient.tolist(),
        "training_rows": len(rows),
    }


def _predict(model: Mapping[str, Any], row: Mapping[str, Any]) -> float:
    x = np.asarray(_feature_vector(row, str(model["arm"])), dtype=np.float64)
    mean = np.asarray(model["feature_mean"], dtype=np.float64)
    scale = np.asarray(model["feature_scale"], dtype=np.float64)
    coefficient = np.asarray(model["coefficient"], dtype=np.float64)
    return float(model["intercept"] + ((x - mean) / scale) @ coefficient)


def _geomean(values: Sequence[float]) -> float:
    return math.exp(statistics.fmean(math.log(value) for value in values))


def _choose_lambda(rows: Sequence[Mapping[str, Any]], arm: str) -> tuple[float, list[dict[str, Any]]]:
    live_k_values = sorted({int(row["live_k"]) for row in rows})
    flat_key, words_key = _timing_keys(arm)
    diagnostics: list[dict[str, Any]] = []
    for ridge_lambda in RIDGE_LAMBDAS:
        regrets: list[float] = []
        absolute_log_errors: list[float] = []
        for heldout_k in live_k_values:
            training = [row for row in rows if int(row["live_k"]) != heldout_k]
            validation = [row for row in rows if int(row["live_k"]) == heldout_k]
            model = _fit_ridge(training, arm, ridge_lambda)
            for row in validation:
                predicted = _predict(model, row)
                actual_log_ratio = math.log(float(row[words_key]) / float(row[flat_key]))
                use_words = int(row["live_k"]) >= 6 and predicted < 0.0
                selected = float(row[words_key] if use_words else row[flat_key])
                best = min(float(row[flat_key]), float(row[words_key]))
                regrets.append(selected / best)
                absolute_log_errors.append(abs(predicted - actual_log_ratio))
        diagnostics.append(
            {
                "ridge_lambda": ridge_lambda,
                "catastrophic_ge_2_count": sum(regret >= 2.0 for regret in regrets),
                "regret_geomean": _geomean(regrets),
                "mean_absolute_log_error": statistics.fmean(absolute_log_errors),
                "fold_count": len(live_k_values),
                "row_count": len(regrets),
            }
        )
    best = min(
        diagnostics,
        key=lambda row: (
            row["catastrophic_ge_2_count"],
            row["regret_geomean"],
            row["mean_absolute_log_error"],
            row["ridge_lambda"],
        ),
    )
    return float(best["ridge_lambda"]), diagnostics


def freeze_model() -> dict[str, Any]:
    _refuse((MODEL,))
    screening = json.loads(SCREENING.read_text(encoding="utf-8"))
    if not screening["screening_gate"]["pass"]:
        raise RuntimeError("screening gate failed; model/timing prohibited")
    training_rows = _read_csv(TRAINING)
    models: dict[str, Any] = {}
    for arm in ("raw", "cm"):
        eligible = _eligible_training(training_rows, arm)
        ridge_lambda, diagnostics = _choose_lambda(eligible, arm)
        model = _fit_ridge(eligible, arm, ridge_lambda)
        model["cross_validation"] = diagnostics
        models[arm] = model
    document = {
        "frozen_before_heldout_timing": True,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "CM_ABC_I10_HELDOUT_SELECTOR_PREREGISTRATION_2026-08-26.md",
        "training_role": "BX1 tuning only",
        "training_path": TRAINING.relative_to(ROOT).as_posix(),
        "training_sha256": _sha(TRAINING),
        "heldout_corpus_sha256": screening["corpus_sha256"],
        "route": "flat below k=6; otherwise words iff predicted log(words/flat) < 0",
        "models": models,
    }
    _write_json(MODEL, document)
    print(json.dumps(document, indent=2, sort_keys=True))
    return document


def measure(prep_repetitions: int, kernel_rounds: int, temporary_cap: int) -> None:
    _refuse((RAW, ENVIRONMENT, SNAPSHOT))
    screening = json.loads(SCREENING.read_text(encoding="utf-8"))
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    if not screening["screening_gate"]["pass"]:
        raise RuntimeError("screening gate failed")
    if model["heldout_corpus_sha256"] != _sha(CORPUS):
        raise RuntimeError("held-out corpus changed after model freeze")
    records = _read_corpus()
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(records, 1):
        row = audit._measure_record(
            "epfl", record, prep_repetitions, kernel_rounds, temporary_cap
        )
        row["corpus"] = "abc_i10"
        row["role"] = "validation_heldout"
        if row["structural_hash"] != record["structural_hash"]:
            raise AssertionError(f"{row['id']}: frozen structural hash mismatch")
        rows.append(row)
        print(
            f"heldout {index}/{len(records)} {row['id']} "
            f"raw={row['raw_words_over_flat']} cm={row['cm_words_over_flat']:.3f}",
            flush=True,
        )
    environment = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpu_count": audit.os.cpu_count(),
        "process_affinity": audit._process_affinity(),
        "prep_repetitions": prep_repetitions,
        "kernel_rounds": kernel_rounds,
        "max_kernel_temporary_bytes": temporary_cap,
        "source": _source_gate(),
        "corpus_sha256": _sha(CORPUS),
        "screening_sha256": _sha(SCREENING),
        "model_sha256": _sha(MODEL),
        "training_sha256": _sha(TRAINING),
        "source_sha256": audit.source_hashes(ROOT, SOURCE_PATHS),
    }
    environment["source_snapshot"] = capture_source_snapshot(ROOT, SNAPSHOT, SOURCE_PATHS)
    _write_csv(RAW, rows)
    _write_json(ENVIRONMENT, environment)


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    index = fraction * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _bootstrap_geomean(regrets: Sequence[float], seed_offset: int) -> tuple[float, float]:
    rng = random.Random(BOOTSTRAP_SEED + seed_offset)
    estimates = [
        _geomean([rng.choice(regrets) for _ in regrets]) for _ in range(BOOTSTRAP_DRAWS)
    ]
    return _percentile(estimates, 0.025), _percentile(estimates, 0.975)


def analyze() -> dict[str, Any]:
    _refuse((DECISIONS, SUMMARY, AUDIT))
    rows = _read_csv(RAW)
    model_document = json.loads(MODEL.read_text(encoding="utf-8"))
    decision_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    summary_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    seed_offset = 0
    for arm in ("raw", "cm"):
        flat_key, words_key = _timing_keys(arm)
        eligible = [
            row
            for row in rows
            if row.get(flat_key) not in (None, "") and row.get(words_key) not in (None, "")
        ]
        model = model_document["models"][arm]
        for policy in ("current_k16", "feature_ridge"):
            regrets: list[float] = []
            word_routes = 0
            prediction_samples: list[float] = []
            for row in eligible:
                live_k = int(row["live_k"])
                predicted = _predict(model, row)
                if policy == "current_k16":
                    use_words = live_k >= 16
                else:
                    start = time.perf_counter_ns()
                    for _ in range(100):
                        _predict(model, row)
                    prediction_samples.append((time.perf_counter_ns() - start) / 100)
                    use_words = live_k >= 6 and predicted < 0.0
                flat = float(row[flat_key])
                words = float(row[words_key])
                selected = words if use_words else flat
                best = min(flat, words)
                regret = selected / best
                regrets.append(regret)
                word_routes += int(use_words)
                decision_rows.append(
                    {
                        "id": row["id"],
                        "arm": arm,
                        "policy": policy,
                        "live_k": live_k,
                        "predicted_log_words_over_flat": predicted,
                        "actual_words_over_flat": words / flat,
                        "selected_engine": "words" if use_words else "flat",
                        "best_engine": "words" if words < flat else "flat",
                        "regret": regret,
                    }
                )
            ci_low, ci_high = _bootstrap_geomean(regrets, seed_offset)
            seed_offset += 1
            summary = {
                "arm": arm,
                "policy": policy,
                "n": len(eligible),
                "refused_or_ineligible_count": len(rows) - len(eligible),
                "word_routes": word_routes,
                "regret_geomean": _geomean(regrets),
                "regret_row_bootstrap_ci95_low": ci_low,
                "regret_row_bootstrap_ci95_high": ci_high,
                "regret_median": statistics.median(regrets),
                "regret_p90": _percentile(regrets, 0.9),
                "regret_max": max(regrets),
                "catastrophic_ge_2_count": sum(regret >= 2.0 for regret in regrets),
                "selector_decision_ns_median": (
                    statistics.median(prediction_samples) if prediction_samples else 0.0
                ),
                "uncertainty_scope": "row bootstrap conditional on the single i10 circuit",
            }
            summaries.append(summary)
            summary_by_key[(arm, policy)] = summary

    checks = []
    for arm in ("raw", "cm"):
        candidate = summary_by_key[(arm, "feature_ridge")]
        control = summary_by_key[(arm, "current_k16")]
        check = {
            "arm": arm,
            "candidate_regret_geomean": candidate["regret_geomean"],
            "control_regret_geomean": control["regret_geomean"],
            "candidate_over_control_regret": (
                candidate["regret_geomean"] / control["regret_geomean"]
            ),
            "regret_geomean_at_most_1_05": candidate["regret_geomean"] <= 1.05,
            "no_catastrophic_routes": candidate["catastrophic_ge_2_count"] == 0,
            "max_regret_below_2": candidate["regret_max"] < 2.0,
            "not_more_than_1pct_worse_than_control": (
                candidate["regret_geomean"] <= 1.01 * control["regret_geomean"]
            ),
        }
        check["pass"] = all(
            check[key]
            for key in (
                "regret_geomean_at_most_1_05",
                "no_catastrophic_routes",
                "max_regret_below_2",
                "not_more_than_1pct_worse_than_control",
            )
        )
        checks.append(check)
    exact_failures = [row["id"] for row in rows if row.get("packed_equal") != "True"]
    acceptance = {
        "screening": json.loads(SCREENING.read_text(encoding="utf-8"))["screening_gate"],
        "exact_failure_ids": exact_failures,
        "arm_checks": checks,
        "feature_selector_validation_pass": not exact_failures and all(
            check["pass"] for check in checks
        ),
        "production_integration_authorized": False,
        "production_reason": (
            "Preregistration requires replication on another independently frozen "
            "circuit family even if this single-circuit validation passes."
        ),
    }
    audit_document = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "CM_ABC_I10_HELDOUT_SELECTOR_PREREGISTRATION_2026-08-26.md",
        "source": _source_gate(),
        "corpus_sha256": _sha(CORPUS),
        "raw_sha256": _sha(RAW),
        "model_sha256": _sha(MODEL),
        "summaries": summaries,
        "acceptance": acceptance,
    }
    _write_csv(DECISIONS, decision_rows)
    _write_csv(SUMMARY, summaries)
    _write_json(AUDIT, audit_document)
    print(json.dumps(audit_document, indent=2, sort_keys=True))
    return audit_document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage", choices=("extract", "freeze-model", "measure", "analyze"), required=True
    )
    parser.add_argument("--prep-repetitions", type=int, default=5)
    parser.add_argument("--kernel-rounds", type=int, default=9)
    parser.add_argument("--max-kernel-temporary-bytes", type=int, default=1 << 24)
    args = parser.parse_args()
    if args.prep_repetitions < 3 or args.kernel_rounds < 3:
        parser.error("repetition counts must be at least 3")
    if args.stage == "extract":
        result = extract()
        return 0 if result["screening_gate"]["pass"] else 2
    if args.stage == "freeze-model":
        freeze_model()
        return 0
    if args.stage == "measure":
        measure(args.prep_repetitions, args.kernel_rounds, args.max_kernel_temporary_bytes)
        return 0
    analyze()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
