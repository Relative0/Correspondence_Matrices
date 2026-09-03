"""C34 larger-natural-workload exact headroom experiment."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time
from typing import Any

from bitset_backend import build_bitset_env
from cm_expr_serde import expr_from_json
from cmbench.recognition.bdd_ordering import ExactBddArtifact
from cmbench.recognition.gf2_decomposition import analyze_exact_gf2

from .contracts import canonical_bytes
from .gf2_decomposition import delivered_sha256
from .gf2_natural_headroom import (
    DECOMPOSITION_METHODS,
    TRUTH_METHODS,
    bind_manifest_cases,
    complete_partition_sha256,
    complete_partitions,
    decomposition_task_contract,
    execute_decomposition_method,
    execute_truth_method,
    local_backend_eligibility,
    truth_contract,
    validate_dataset_manifest,
)
from .schedule import balanced_orders


SCHEMA = "crse-c34-natural-task-matched-headroom-experiment/v1"


@dataclass(frozen=True)
class C34Config:
    run_id: str
    seed: int = 20260901
    truth_blocks: int = 12
    decomposition_blocks: int = 6
    materialize_budget: int = 4
    bdd_probe_cases_per_width: int = 1
    prepared_dispatch_budget_ns: int = 43_100
    async_observation_p95_budget_ns: int = 80_300
    actionable_speedup_gate: float = 1.05
    actionable_case_fraction: float = 0.75
    max_seconds: float = 900.0

    @property
    def charged_router_budget_ns(self) -> int:
        return self.prepared_dispatch_budget_ns + self.async_observation_p95_budget_ns

    def validate(self) -> None:
        if (
            not self.run_id
            or self.truth_blocks != len(balanced_orders(TRUTH_METHODS))
            or self.decomposition_blocks != len(balanced_orders(DECOMPOSITION_METHODS))
            or self.materialize_budget != 4
            or self.bdd_probe_cases_per_width != 1
            or self.prepared_dispatch_budget_ns != 43_100
            or self.async_observation_p95_budget_ns != 80_300
            or self.actionable_speedup_gate != 1.05
            or self.actionable_case_fraction != 0.75
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 300 <= self.max_seconds <= 1800
        ):
            raise ValueError("invalid frozen C34 experiment bounds")


def _write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bound_path(root: Path, relative: str) -> Path:
    path = root.joinpath(*Path(relative).parts).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("C34 bound input escaped or is missing")
    return path


def build_schedule(
    cases: list[dict[str, Any]], methods: tuple[str, ...], blocks: int, seed: int, task: str,
) -> list[dict[str, Any]]:
    orders = balanced_orders(methods)
    if blocks != len(orders):
        raise ValueError("C34 requires one complete counterbalance cycle")
    rows: list[dict[str, Any]] = []
    for block in range(blocks):
        ordered = list(cases)
        random.Random(f"c34:{seed}:{task}:{block}").shuffle(ordered)
        method_order = orders[(block + seed) % len(orders)]
        for position, case in enumerate(ordered):
            core = {
                "task": task,
                "block": block,
                "case_position": position,
                "case_id": case["case_id"],
                "cluster_id": case["cluster_id"],
                "n_vars": case["n_vars"],
                "method_order": list(method_order),
            }
            core["order_sha256"] = hashlib.sha256(canonical_bytes(core)).hexdigest()
            rows.append(core)
    return rows


def validate_schedule(
    rows: list[dict[str, Any]], cases: list[dict[str, Any]], methods: tuple[str, ...], blocks: int,
) -> None:
    if len(rows) != len(cases) * blocks:
        raise ValueError("C34 schedule cardinality")
    case_ids = {case["case_id"] for case in cases}
    for row in rows:
        core = {key: row[key] for key in (
            "task", "block", "case_position", "case_id", "cluster_id", "n_vars", "method_order")}
        if row.get("order_sha256") != hashlib.sha256(canonical_bytes(core)).hexdigest():
            raise ValueError("C34 schedule identity")
        if row["case_id"] not in case_ids or set(row["method_order"]) != set(methods):
            raise ValueError("C34 schedule membership")
    for case_id in case_ids:
        selected = [row for row in rows if row["case_id"] == case_id]
        if Counter(row["block"] for row in selected) != Counter(range(blocks)):
            raise ValueError("C34 case/block balance")
        for method in methods:
            positions = Counter(row["method_order"].index(method) for row in selected)
            if positions != Counter({index: 2 for index in range(len(methods))}):
                raise ValueError("C34 arm-position balance")


def build_oracles(cases: list[dict[str, Any]], *, progress=None) -> tuple[dict[str, Any], dict[str, Any]]:
    truth = {
        case["case_id"]: {
            "n_vars": case["n_vars"],
            "truth_bits_hex": case["truth_bits_hex"],
            "truth_sha256": case["truth_sha256"],
        }
        for case in cases
    }
    decomposition: dict[str, Any] = {}
    for index, case in enumerate(cases):
        if not case.get("decomposition_role", False):
            continue
        bits = int(case["truth_bits_hex"], 16)
        partitions = complete_partitions(case["n_vars"])
        analysis = analyze_exact_gf2(bits, case["n_vars"], row_partitions=partitions)
        if not all(candidate.reconstruct() == bits for candidate in analysis.candidates):
            raise RuntimeError("C34 exhaustive oracle failed exact reconstruction")
        best = analysis.best.to_dict() if analysis.best else None
        decomposition[case["case_id"]] = {
            "best_artifact": best,
            "delivered_sha256": delivered_sha256(best),
            "partitions_tested": analysis.partitions_tested,
            "partition_sha256": complete_partition_sha256(case["n_vars"]),
            "candidates": len(analysis.candidates),
        }
        if progress is not None:
            progress("oracle", index + 1, len(cases), case["case_id"])
    return truth, decomposition


def _median_map(rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    grouped: dict[tuple[str, str], list[int]] = {}
    for row in rows:
        grouped.setdefault((row["case_id"], row["method"]), []).append(
            row["timings_ns"]["task_total_ns"])
    return {key: int(statistics.median(values)) for key, values in grouped.items()}


def summarize_task(
    rows: list[dict[str, Any]], methods: tuple[str, ...], *, router_budget_ns: int,
    actionable_speedup_gate: float, actionable_case_fraction: float,
) -> dict[str, Any]:
    medians = _median_map(rows)
    cases = sorted({row["case_id"] for row in rows})
    case_width = {row["case_id"]: row["n_vars"] for row in rows}
    expected = len(cases) * len(methods)
    if len(medians) != expected:
        raise ValueError("C34 summary missing case/method medians")
    totals = {method: sum(medians[(case, method)] for case in cases) for method in methods}
    best_fixed = min(methods, key=lambda method: (totals[method], method))
    oracle_by_case = {case: min(medians[(case, method)] for method in methods) for case in cases}
    oracle_winner = {
        case: min(methods, key=lambda method: (medians[(case, method)], method)) for case in cases
    }
    oracle_total = sum(oracle_by_case.values())
    fixed_total = totals[best_fixed]
    headroom = {case: medians[(case, best_fixed)] - oracle_by_case[case] for case in cases}
    by_width: dict[str, Any] = {}
    width_rule_total = 0
    width_rule_methods: dict[int, str] = {}
    for n_vars in sorted(set(case_width.values())):
        selected = [case for case in cases if case_width[case] == n_vars]
        width_totals = {
            method: sum(medians[(case, method)] for case in selected) for method in methods}
        width_best = min(methods, key=lambda method: (width_totals[method], method))
        width_rule_methods[n_vars] = width_best
        width_rule_total += width_totals[width_best]
        by_width[str(n_vars)] = {
            "cases": len(selected),
            "best_aggregate_method": width_best,
            "method_total_ns": width_totals,
            "best_fixed_speedup_from_width_choice": (
                width_totals[best_fixed] / width_totals[width_best]
            ),
        }
    covered = sum(value >= router_budget_ns for value in headroom.values()) / len(cases)
    budget_adjusted_oracle = oracle_total + router_budget_ns * len(cases)
    budget_adjusted_width = width_rule_total + router_budget_ns * len(cases)
    methods_summary = {}
    for method in methods:
        values = [medians[(case, method)] for case in cases]
        methods_summary[method] = {
            "aggregate_median_case_total_ns": totals[method],
            "median_case_ns": int(statistics.median(values)),
            "minimum_case_ns": min(values),
            "maximum_case_ns": max(values),
            "relative_to_best_fixed": fixed_total / totals[method],
            "per_case_wins": sum(oracle_winner[case] == method for case in cases),
        }
    budget_adjusted_oracle_speedup = fixed_total / budget_adjusted_oracle
    budget_adjusted_width_speedup = fixed_total / budget_adjusted_width
    return {
        "cases": len(cases),
        "measurement_rows": len(rows),
        "methods": methods_summary,
        "best_fixed_method": best_fixed,
        "best_fixed_total_ns": fixed_total,
        "per_case_oracle_total_ns": oracle_total,
        "per_case_oracle_speedup_over_best_fixed": fixed_total / oracle_total,
        "per_case_oracle_absolute_headroom_total_ns": fixed_total - oracle_total,
        "per_case_oracle_median_headroom_ns": int(statistics.median(headroom.values())),
        "charged_router_budget_ns_per_case": router_budget_ns,
        "budget_covered_case_fraction": covered,
        "budget_adjusted_oracle_speedup_over_best_fixed": budget_adjusted_oracle_speedup,
        "oracle_headroom_gate": (
            budget_adjusted_oracle_speedup >= actionable_speedup_gate
            and covered >= actionable_case_fraction
        ),
        "width_rule": {
            "methods": {str(key): value for key, value in sorted(width_rule_methods.items())},
            "total_ns": width_rule_total,
            "raw_speedup_over_best_fixed": fixed_total / width_rule_total,
            "budget_adjusted_speedup_over_best_fixed": budget_adjusted_width_speedup,
            "headroom_gate": budget_adjusted_width_speedup >= actionable_speedup_gate,
            "post_hoc_retrospective": True,
        },
        "by_width": by_width,
        "timing_is_local_and_machine_specific": True,
    }


def _measurement_row(task: str, schedule: dict[str, Any], method: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": task,
        "block": schedule["block"],
        "case_position": schedule["case_position"],
        "arm_position": schedule["method_order"].index(method),
        "order_sha256": schedule["order_sha256"],
        "case_id": schedule["case_id"],
        "cluster_id": schedule["cluster_id"],
        "n_vars": schedule["n_vars"],
        "method": method,
        "status": result["status"],
        "timings_ns": result["timings_ns"],
        "artifact_sha256": result["artifact"]["sha256"],
        "artifact_bytes": result["artifact"]["bytes"],
        "identity": result["identity"],
        "resources": result["resources"],
    }


def _bdd_probes(cases: list[dict[str, Any]]) -> dict[str, Any]:
    selected = []
    for n_vars in sorted({case["n_vars"] for case in cases}):
        selected.append(min(
            (case for case in cases if case["n_vars"] == n_vars),
            key=lambda case: (case["selection_sha256"], case["case_id"]),
        ))
    rows = []
    for case in selected:
        expression = expr_from_json(case["expression_v2"])
        started = time.perf_counter_ns()
        bdd = ExactBddArtifact.build(
            expression, case["n_vars"], [f"x{i}" for i in range(case["n_vars"])], backend="autoref")
        bits = sum(value << index for index, value in enumerate(bdd.truth_bits()))
        nodes = bdd.node_count
        bdd.close()
        elapsed = time.perf_counter_ns() - started
        if bits != int(case["truth_bits_hex"], 16):
            raise RuntimeError("C34 BDD functional probe mismatch")
        rows.append({
            "case_id": case["case_id"],
            "n_vars": case["n_vars"],
            "node_count": nodes,
            "diagnostic_total_ns": elapsed,
            "exact_check_passed": True,
        })
    return {
        "schema": "crse-c34-bdd-functional-probes/v1",
        "status": "passed",
        "backend": "dd.autoref",
        "cases": len(rows),
        "one_case_per_width": True,
        "performance_ranking_permitted": False,
        "rows": rows,
    }


def _controls(
    truth_cases: list[dict[str, Any]], decomposition_cases: list[dict[str, Any]],
    decomposition_oracles: dict[str, Any],
) -> dict[str, Any]:
    first = truth_cases[0]
    first_decomposition = decomposition_cases[0]

    def refused(function) -> bool:
        try:
            function()
        except (ValueError, RuntimeError):
            return True
        return False

    wrong_truth_contract = truth_contract(first, method="direct_ast_bitset")
    wrong_truth_contract["validation"]["required_output_sha256"] = "0" * 64
    oracle = decomposition_oracles[first_decomposition["case_id"]]
    good_decomposition_contract = decomposition_task_contract(
        first_decomposition,
        method=DECOMPOSITION_METHODS[0],
        required_best=oracle["best_artifact"],
    )
    controls = {
        "complete_partition_counts": {
            str(n_vars): len(complete_partitions(n_vars)) for n_vars in range(3, 11)
        },
        "wrong_truth_contract_refused": refused(lambda: execute_truth_method(
            case=first, contract=wrong_truth_contract, method="direct_ast_bitset")),
        "wrong_decomposition_best_refused": refused(lambda: execute_decomposition_method(
            case=first_decomposition,
            contract=good_decomposition_contract,
            method=DECOMPOSITION_METHODS[0],
            required_best=None,
        )),
        "task_mismatch_refused": refused(lambda: execute_truth_method(
            case=first,
            contract=good_decomposition_contract,
            method="direct_ast_bitset",
        )),
        "production_write": False,
        "production_promotion": False,
    }
    controls["all_passed"] = (
        controls["complete_partition_counts"]
        == {str(n): (1 << (n - 1)) - 1 for n in range(3, 11)}
        and controls["wrong_truth_contract_refused"]
        and controls["wrong_decomposition_best_refused"]
        and controls["task_mismatch_refused"]
    )
    return {"schema": "crse-c34-functional-controls/v1", **controls}


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# C34 natural task-matched exact headroom scout",
        "",
        f"Status: **{result['status']}**",
        "",
        "The complete-relation table delivers the same canonical packed truth vector from every",
        "timed method. The decomposition table delivers the same globally best exact CM/GF(2)",
        "artifact over the complete partition universe. This is reused natural extension evidence,",
        "not fresh confirmation, training, routing, or production promotion.",
        "",
    ]
    for task, title in (("complete_relation", "Complete relation"),
                        ("gf2_decomposition", "Complete GF(2) decomposition")):
        summary = result["summary"][task]
        lines += [
            f"## {title}",
            "",
            f"Best fixed method: **{summary['best_fixed_method']}**",
            "",
            "| Method | Aggregate median-case time | Relative to best fixed | Case wins |",
            "|---|---:|---:|---:|",
        ]
        for method, row in summary["methods"].items():
            lines.append(
                f"| {method} | {row['aggregate_median_case_total_ns'] / 1e6:.3f} ms | "
                f"{row['relative_to_best_fixed']:.4f}x | {row['per_case_wins']} |"
            )
        lines += [
            "",
            f"Budget-adjusted per-case-oracle speedup: "
            f"**{summary['budget_adjusted_oracle_speedup_over_best_fixed']:.4f}x**.",
            f"Budget-adjusted post-hoc width-rule speedup: "
            f"**{summary['width_rule']['budget_adjusted_speedup_over_best_fixed']:.4f}x**.",
            "",
        ]
    lines += [
        "No learning gate or production gate is implied. A positive exploratory headroom gate",
        "would require a new outcome-independent confirmation corpus before model fitting.",
        "",
    ]
    return "\n".join(lines)


def run(
    config: C34Config,
    output: Path,
    dataset_manifest_path: Path,
    dataset_verification_path: Path,
    root: Path,
    *,
    progress=None,
) -> dict[str, Any]:
    config.validate()
    wall = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    verification = json.loads(dataset_verification_path.read_text(encoding="utf-8"))
    source_path = _bound_path(root, manifest["source"]["path"])
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if (_sha256(source_path) != manifest["source"]["sha256"]
            or _sha256(dataset_manifest_path) != verification.get("manifest_sha256")
            or verification.get("status") != "verified"):
        raise ValueError("C34 frozen corpus binding changed")
    validate_dataset_manifest(manifest, source)
    truth_cases = bind_manifest_cases(manifest, source, role="complete_relation")
    decomposition_cases = bind_manifest_cases(manifest, source, role="decomposition")
    decomposition_ids = {case["case_id"] for case in decomposition_cases}
    oracle_input = [{**case, "decomposition_role": case["case_id"] in decomposition_ids}
                    for case in truth_cases]
    truth_oracles, decomposition_oracles = build_oracles(oracle_input, progress=progress)
    if time.perf_counter() - wall > config.max_seconds:
        raise TimeoutError("C34 oracle construction exceeded wall bound")

    truth_contracts = {
        case["case_id"]: {method: truth_contract(case, method=method) for method in TRUTH_METHODS}
        for case in truth_cases
    }
    decomposition_contracts = {
        case["case_id"]: {
            method: decomposition_task_contract(
                case,
                method=method,
                required_best=decomposition_oracles[case["case_id"]]["best_artifact"],
            )
            for method in DECOMPOSITION_METHODS
        }
        for case in decomposition_cases
    }
    truth_schedule = build_schedule(
        truth_cases, TRUTH_METHODS, config.truth_blocks, config.seed, "complete_relation")
    decomposition_schedule = build_schedule(
        decomposition_cases, DECOMPOSITION_METHODS, config.decomposition_blocks,
        config.seed, "gf2_decomposition")
    validate_schedule(truth_schedule, truth_cases, TRUTH_METHODS, config.truth_blocks)
    validate_schedule(
        decomposition_schedule, decomposition_cases, DECOMPOSITION_METHODS,
        config.decomposition_blocks)
    eligibility = local_backend_eligibility()
    bdd = _bdd_probes(truth_cases)
    controls = _controls(truth_cases, decomposition_cases, decomposition_oracles)
    if not controls["all_passed"] or bdd["status"] != "passed":
        raise RuntimeError("C34 functional controls failed")

    _write(output / "run_spec.json", {
        "schema": SCHEMA,
        "config": asdict(config),
        "charged_router_budget_ns": config.charged_router_budget_ns,
        "dataset_manifest_path": dataset_manifest_path.resolve().relative_to(root.resolve()).as_posix(),
        "dataset_manifest_sha256": _sha256(dataset_manifest_path),
        "dataset_verification_path": dataset_verification_path.resolve().relative_to(root.resolve()).as_posix(),
        "dataset_verification_sha256": _sha256(dataset_verification_path),
        "source_dataset_path": source_path.resolve().relative_to(root.resolve()).as_posix(),
        "source_dataset_sha256": _sha256(source_path),
        "truth_methods": list(TRUTH_METHODS),
        "decomposition_methods": list(DECOMPOSITION_METHODS),
        "complete_partition_universe": True,
        "internal_exact_checks_charged": True,
        "external_oracle_outside_timing": True,
        "training": False,
        "policy_refit": False,
        "fresh_confirmation": False,
        "production_write": False,
        "production_promotion": False,
    })
    _write(output / "eligibility.json", eligibility)
    _write(output / "truth_oracles.json", truth_oracles)
    _write(output / "decomposition_oracles.json", decomposition_oracles)
    _write(output / "truth_contracts.json", truth_contracts)
    _write(output / "decomposition_contracts.json", decomposition_contracts)
    _write_jsonl(output / "truth_schedule.jsonl", truth_schedule)
    _write_jsonl(output / "decomposition_schedule.jsonl", decomposition_schedule)
    _write(output / "bdd_functional_probes.json", bdd)
    _write(output / "functional_controls.json", controls)

    for n_vars in range(3, 11):
        build_bitset_env(tuple(f"x{i}" for i in range(n_vars)))
    case_map = {case["case_id"]: case for case in truth_cases}
    truth_rows = []
    for schedule_index, schedule in enumerate(truth_schedule):
        case = case_map[schedule["case_id"]]
        for method in schedule["method_order"]:
            if time.perf_counter() - wall > config.max_seconds:
                raise TimeoutError("C34 complete-relation table exceeded wall bound")
            result = execute_truth_method(
                case=case,
                contract=truth_contracts[case["case_id"]][method],
                method=method,
            )
            truth_rows.append(_measurement_row("complete_relation", schedule, method, result))
        if progress is not None:
            progress("truth", schedule_index + 1, len(truth_schedule), schedule["case_id"])
    _write_jsonl(output / "truth_measurements.jsonl", truth_rows)

    decomposition_rows = []
    for schedule_index, schedule in enumerate(decomposition_schedule):
        case = case_map[schedule["case_id"]]
        oracle = decomposition_oracles[case["case_id"]]
        for method in schedule["method_order"]:
            if time.perf_counter() - wall > config.max_seconds:
                raise TimeoutError("C34 decomposition table exceeded wall bound")
            result = execute_decomposition_method(
                case=case,
                contract=decomposition_contracts[case["case_id"]][method],
                method=method,
                required_best=oracle["best_artifact"],
                materialize_budget=config.materialize_budget,
            )
            decomposition_rows.append(_measurement_row(
                "gf2_decomposition", schedule, method, result))
        if progress is not None:
            progress("decomposition", schedule_index + 1, len(decomposition_schedule), schedule["case_id"])
    _write_jsonl(output / "decomposition_measurements.jsonl", decomposition_rows)

    summary = {
        "complete_relation": summarize_task(
            truth_rows,
            TRUTH_METHODS,
            router_budget_ns=config.charged_router_budget_ns,
            actionable_speedup_gate=config.actionable_speedup_gate,
            actionable_case_fraction=config.actionable_case_fraction,
        ),
        "gf2_decomposition": summarize_task(
            decomposition_rows,
            DECOMPOSITION_METHODS,
            router_budget_ns=config.charged_router_budget_ns,
            actionable_speedup_gate=config.actionable_speedup_gate,
            actionable_case_fraction=config.actionable_case_fraction,
        ),
    }
    mismatches = sum(not row["identity"]["exact_check_passed"]
                     for row in (*truth_rows, *decomposition_rows))
    result = {
        "schema": SCHEMA,
        "status": "complete" if mismatches == 0 else "failed",
        "config": asdict(config),
        "wall_seconds": time.perf_counter() - wall,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": importlib.metadata.version("numpy"),
            "dd": importlib.metadata.version("dd"),
            "python_sat": importlib.metadata.version("python-sat"),
            "thread_environment": {name: os.environ.get(name) for name in
                                   ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        },
        "dataset": {
            "cases": len(truth_cases),
            "decomposition_cases": len(decomposition_cases),
            "families": manifest["counts"]["families"],
            "n_vars": list(range(3, 11)),
            "source_dataset_reused": True,
            "fresh_confirmation": False,
            "training_use": False,
            "policy_refit": False,
        },
        "truth_measurement_rows": len(truth_rows),
        "decomposition_measurement_rows": len(decomposition_rows),
        "semantic_or_artifact_mismatches": mismatches,
        "functional_controls_passed": controls["all_passed"],
        "bdd_functional_probes_passed": bdd["status"] == "passed",
        "summary": summary,
        "decision": {
            "training_performed": False,
            "learning_or_router_promotion_permitted": False,
            "production_promotion": False,
            "next_step": (
                "fresh outcome-independent confirmation only if a fixed or width-rule surface "
                "retains budget-adjusted headroom; otherwise move to another exact task/track"
            ),
        },
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    sources = (
        "cmbench/comparative/gf2_natural_headroom.py",
        "cmbench/comparative/gf2_natural_headroom_experiment.py",
        "scripts/cm_comparative_c34_natural_headroom.py",
    )
    artifacts = (
        "run_spec.json", "eligibility.json", "truth_oracles.json",
        "decomposition_oracles.json", "truth_contracts.json",
        "decomposition_contracts.json", "truth_schedule.jsonl",
        "decomposition_schedule.jsonl", "bdd_functional_probes.json",
        "functional_controls.json", "truth_measurements.jsonl",
        "decomposition_measurements.jsonl", "results.json", "report.md",
    )
    _write(output / "manifest.json", {
        "schema": "crse-c34-run-manifest/v1",
        "dataset_manifest_sha256": _sha256(dataset_manifest_path),
        "dataset_verification_sha256": _sha256(dataset_verification_path),
        "source_dataset_sha256": _sha256(source_path),
        "sources": {name: _sha256(root / name) for name in sources},
        "artifacts": {name: _sha256(output / name) for name in artifacts},
    })
    return result
