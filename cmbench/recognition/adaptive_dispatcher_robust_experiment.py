"""Robust-tie policy confirmation for the one-pass adaptive ANF dispatcher."""
from __future__ import annotations

import json
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .adaptive_dispatcher_experiment import (
    AdaptiveConfig, DEFAULT_C10_RUN, DEFAULT_C6_RUN, DEFAULT_C7_RUN, benchmark,
    relative, render_report, sha, source_fingerprints as adaptive_source_fingerprints,
    summarize, write_json,
)
from .exact_dispatcher import canonical_sha256
from .exact_dispatcher_experiment import Budget, verify_retained_c7
from .yosys_composed_holdout_data import make_yosys_composed_holdout
from .yosys_composed_holdout2_data import make_yosys_composed_holdout2
from .yosys_human_decomposition_data import make_yosys_human_documents
from .yosys_source_anf_experiment import verify_retained_c6

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA = "crse-adaptive-exact-dispatcher-robust-confirmation/v1"
POLICY_SCHEMA = "crse-adaptive-exact-dispatcher-robust/v1"
SPLITS = ("c6_test_dev", "c6_confirmatory_dev", "c7_a_dev", "c7_b_dev",
          "c11_a_dev", "c11_b_dev", "c12_sealed_a", "c12_sealed_b")
ROBUST_TOLERANCE = 0.01


def source_fingerprints() -> dict[str, str]:
    result = adaptive_source_fingerprints()
    for path in (ROOT / "cmbench/recognition/adaptive_dispatcher_robust_experiment.py",
                 ROOT / "cmbench/recognition/yosys_composed_holdout2_data.py"):
        result[relative(path)] = sha(path)
    return result


def freeze_robust_policy(c10: Path) -> tuple[dict, list[dict]]:
    candidates_path = c10 / "budget_candidates.json"
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    compact = [{key: row[key] for key in ("product_pair_budget", "sequence_total_ns", "fallbacks")}
               for row in candidates]
    minimum = min(row["sequence_total_ns"] for row in compact)
    eligible = [row for row in compact if row["sequence_total_ns"] <= minimum * (1 + ROBUST_TOLERANCE)]
    chosen = max(eligible, key=lambda row: row["product_pair_budget"])
    if chosen["product_pair_budget"] != 4096:
        raise ValueError("changed robust validation tie selection")
    return {"schema": POLICY_SCHEMA, "status": "frozen",
        "product_pair_budget": chosen["product_pair_budget"],
        "selection": "largest product-pair budget within 1% of the minimum C6-validation sequence time",
        "tie_tolerance": ROBUST_TOLERANCE, "validation_minimum_sequence_total_ns": minimum,
        "chosen_validation_sequence_total_ns": chosen["sequence_total_ns"],
        "eligible_budgets": [row["product_pair_budget"] for row in eligible],
        "budget_source": relative(candidates_path), "budget_source_sha256": sha(candidates_path),
        "architecture": "optimized one-pass set-to-packed conversion",
        "training_use": {"c6_validation": True, "c6_heldout": False, "c7": False,
                         "c11": False, "c12": False},
        "frozen_before_c12_generation": True}, compact


def measured_criteria(rows: list[dict], splits: dict, provenance: dict, frozen: bool) -> dict:
    exact = all(row["predicted"] == row["label"] and row["canonical_partition_match"]
                and not row["semantic_mismatch"] for row in rows)
    fresh = provenance["audit"]["prior_semantic_overlap"] == 0 and provenance["audit"]["prior_alpha_overlap"] == 0
    sealed_no_regret = all(splits[split]["adaptive_speedup_over_best_fixed"] >= 1 / 1.05
                           for split in ("c12_sealed_a", "c12_sealed_b"))
    dev_tail = splits["c6_confirmatory_dev"]["adaptive_p95_speedup_over_set"] >= 2.0
    return {"exact": exact, "leakage_safe_freeze": frozen, "fresh_holdout_disjoint": fresh,
        "sealed_no_material_regret": sealed_no_regret, "development_tail_guard": dev_tail,
        "safety": exact and fresh,
        "production_promotion": exact and frozen and fresh and sealed_no_regret and dev_tail}


def run_robust_adaptive_experiment(config: AdaptiveConfig, output: Path,
                                   c6: Path = DEFAULT_C6_RUN, c7: Path = DEFAULT_C7_RUN,
                                   c10: Path = DEFAULT_C10_RUN, progress=print) -> dict:
    config.validate()
    output, c6, c7, c10 = output.resolve(), c6.resolve(), c7.resolve(), c10.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = source_fingerprints()
    retained_c6, retained_c7 = verify_retained_c6(c6), verify_retained_c7(c7)
    policy, candidates = freeze_robust_policy(c10)
    write_json(output / "run_spec.json", {"schema": "crse-adaptive-robust-run-spec/v1",
        "purpose": "confirm the robust validation-tie policy on a new source holdout",
        "policy_rule": policy["selection"], "repetitions": config.repetitions,
        "cache_capacity": config.cache_capacity, "threads": config.threads,
        "max_seconds": config.max_seconds, "estimated_memory_mib": 320,
        "development_data": ["C6 heldout", "C7", "C11"], "sealed_data": "C12",
        "retained_c6": relative(c6), "retained_c7": relative(c7),
        "network": False, "production_write": False})
    write_json(output / "robust_budget_evidence.json", candidates)
    write_json(output / "frozen_robust_dispatcher.json", policy)
    frozen_hash = sha(output / "frozen_robust_dispatcher.json")

    progress("generating C12 only after the robust policy freeze")
    c12, c12_provenance = make_yosys_composed_holdout2()
    write_json(output / "c12_dataset.json", c12)
    write_json(output / "c12_provenance.json", c12_provenance)
    c12_hash = sha(output / "c12_dataset.json")

    c6_documents = json.loads((c6 / "dataset.json").read_text(encoding="utf-8"))
    c7_documents, _ = make_yosys_human_documents()
    retained_c7_documents = json.loads((c7 / "dataset.json").read_text(encoding="utf-8"))
    if canonical_sha256(c7_documents) != canonical_sha256(retained_c7_documents):
        raise ValueError("retained C7 dataset did not regenerate")
    c11, _ = make_yosys_composed_holdout()
    evaluation = []
    for row in c6_documents:
        if row["split"] in {"test", "confirmatory"}:
            evaluation.append({**row, "evaluation_split": f"c6_{row['split']}_dev",
                               "source_scope": "development EPFL"})
    for row in c7_documents:
        evaluation.append({**row, "evaluation_split": f"c7_{row['split'].removeprefix('sealed_')}_dev",
                           "source_scope": "development Yosys C7"})
    for row in c11:
        evaluation.append({**row, "evaluation_split": f"c11_{row['split'].removeprefix('sealed_')}_dev",
                           "source_scope": "development Yosys-derived C11"})
    for row in c12:
        evaluation.append({**row, "evaluation_split": f"c12_{row['split']}",
                           "source_scope": "fresh Yosys-derived C12"})

    guard, started = Budget(config.max_seconds), time.perf_counter()
    progress("benchmarking the frozen robust policy against exact controls")
    rows = benchmark(evaluation, policy, config, guard, SPLITS)
    method_summary, split_summary = summarize(rows, SPLITS)
    criteria = measured_criteria(rows, split_summary, c12_provenance, True)
    result = {"schema": RUN_SCHEMA, "status": "complete", "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0], "config": asdict(config),
        "retained_c6": retained_c6, "retained_c7": retained_c7,
        "policy": policy, "frozen_policy_sha256": frozen_hash,
        "c12_dataset_sha256": c12_hash, "c12_loaded_after_policy_freeze": True,
        "c12_audit": c12_provenance["audit"], "evaluation_rows": len(evaluation),
        "method_summary": method_summary, "split_summary": split_summary,
        "criteria": criteria, "semantic_mismatches": sum(row["semantic_mismatch"] for row in rows),
        "source_unchanged": before == source_fingerprints()}
    write_json(output / "evaluation_dataset.json", evaluation)
    write_json(output / "evaluation_benchmark.json", rows)
    write_json(output / "summary.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8")
    files = ("run_spec.json", "robust_budget_evidence.json", "frozen_robust_dispatcher.json",
             "c12_dataset.json", "c12_provenance.json", "evaluation_dataset.json",
             "evaluation_benchmark.json", "summary.json", "report.md")
    write_json(output / "manifest.json", {"schema": "crse-adaptive-robust-artifacts/v1",
        "status": "complete", "files_sha256": {name: sha(output / name) for name in files},
        "source_sha256": before, "retained_c6_manifest_sha256": retained_c6["manifest_sha256"],
        "retained_c7_manifest_sha256": retained_c7["manifest_sha256"]})
    return result
