"""C36 balanced wider-natural repeated-query lifecycle experiment."""
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

from cm_expr_serde import expr_from_json
from cmbench.backends.robdd_dd import select_dd_module
from cmbench.recognition.bdd_ordering import ExactBddArtifact
from cmbench.recognition.sat_guidance import encode_expression_cnf

from .contracts import canonical_bytes
from .gf2_wide_repeated_queries import (
    CHECKPOINTS, METHODS, execute_session, semantic_row, task_contract, validate_dataset,
)
from .schedule import balanced_orders


SCHEMA = "crse-c36-wide-natural-repeated-query-experiment/v1"


@dataclass(frozen=True)
class C36Config:
    run_id: str
    seed: int = 20260901
    blocks: int = 8
    checkpoints: tuple[int, ...] = CHECKPOINTS
    cm_speedup_gate: float = 1.05
    cm_case_fraction_gate: float = 0.75
    charged_router_budget_ns: int = 123_400
    routing_speedup_gate: float = 1.05
    max_seconds: float = 900.0

    def validate(self) -> None:
        if (not self.run_id or self.blocks != len(balanced_orders(METHODS))
                or tuple(self.checkpoints) != CHECKPOINTS or self.cm_speedup_gate != 1.05
                or self.cm_case_fraction_gate != 0.75
                or self.charged_router_budget_ns != 123_400
                or self.routing_speedup_gate != 1.05
                or type(self.max_seconds) not in (int, float)
                or not math.isfinite(self.max_seconds) or not 120 <= self.max_seconds <= 1800):
            raise ValueError("invalid frozen C36 experiment bounds")


def _write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_schedule(cases: list[dict[str, Any]], blocks: int, seed: int) -> list[dict[str, Any]]:
    orders = balanced_orders(METHODS)
    if blocks != len(orders):
        raise ValueError("C36 requires one complete counterbalance cycle")
    rows = []
    for block in range(blocks):
        ordered = list(cases)
        random.Random(f"c36:{seed}:{block}").shuffle(ordered)
        method_order = orders[(block + seed) % len(orders)]
        for position, case in enumerate(ordered):
            core = {"block": block, "case_position": position, "case_id": case["case_id"],
                    "family": case["family"], "n_vars": case["n_vars"],
                    "method_order": list(method_order)}
            core["order_sha256"] = hashlib.sha256(canonical_bytes(core)).hexdigest()
            rows.append(core)
    return rows


def validate_schedule(rows: list[dict[str, Any]], cases: list[dict[str, Any]], blocks: int) -> None:
    if len(rows) != len(cases) * blocks:
        raise ValueError("C36 schedule cardinality")
    case_ids = {case["case_id"] for case in cases}
    for row in rows:
        core = {key: row[key] for key in
                ("block", "case_position", "case_id", "family", "n_vars", "method_order")}
        if (row.get("order_sha256") != hashlib.sha256(canonical_bytes(core)).hexdigest()
                or row["case_id"] not in case_ids or set(row["method_order"]) != set(METHODS)):
            raise ValueError("C36 schedule identity/membership")
    for case_id in case_ids:
        selected = [row for row in rows if row["case_id"] == case_id]
        if Counter(row["block"] for row in selected) != Counter(range(blocks)):
            raise ValueError("C36 case/block balance")
        for method in METHODS:
            positions = Counter(row["method_order"].index(method) for row in selected)
            if positions != Counter({index: 2 for index in range(len(METHODS))}):
                raise ValueError("C36 arm-position balance")


def _median_maps(rows: list[dict[str, Any]]):
    checkpoint_values: dict[tuple[str, str, int], list[int]] = {}
    setup_values: dict[tuple[str, str], list[int]] = {}
    warm_values: dict[tuple[str, str], list[int]] = {}
    for row in rows:
        key = (row["case_id"], row["method"])
        identity = row["identity"]
        setup_values.setdefault(key, []).append(identity["setup_total_ns"])
        cumulative = identity["checkpoint_query_ns"]
        warm_values.setdefault(key, []).append((cumulative["64"] - cumulative["16"]) // 48)
        for checkpoint in CHECKPOINTS:
            checkpoint_values.setdefault((*key, checkpoint), []).append(
                identity["checkpoint_total_ns"][str(checkpoint)])
    return (
        {key: int(statistics.median(values)) for key, values in checkpoint_values.items()},
        {key: int(statistics.median(values)) for key, values in setup_values.items()},
        {key: int(statistics.median(values)) for key, values in warm_values.items()},
    )


def summarize(rows: list[dict[str, Any]], *, speedup_gate: float,
              case_fraction_gate: float, router_budget_ns: int = 123_400,
              routing_speedup_gate: float = 1.05) -> dict[str, Any]:
    medians, setup, warm = _median_maps(rows)
    cases = sorted({row["case_id"] for row in rows})
    widths = {row["case_id"]: row["n_vars"] for row in rows}
    families = {row["case_id"]: row["family"] for row in rows}
    if len(medians) != len(cases) * len(METHODS) * len(CHECKPOINTS):
        raise ValueError("C36 incomplete checkpoint medians")
    checkpoints = {}
    versus_cse = versus_direct = versus_projection = None
    for checkpoint in CHECKPOINTS:
        totals = {method: sum(medians[(case, method, checkpoint)] for case in cases)
                  for method in METHODS}
        fixed = min(METHODS, key=lambda method: (totals[method], method))
        winners = {case: min(METHODS, key=lambda method:
                             (medians[(case, method, checkpoint)], method)) for case in cases}
        oracle_total = sum(medians[(case, winners[case], checkpoint)] for case in cases)
        cm = totals["cm_ir_words"]
        comparisons = {
            "flattened_cse_words": totals["flattened_cse_words"] / cm,
            "direct_ast_restrict": totals["direct_ast_restrict"] / cm,
            "compiled_truth_projection": totals["compiled_truth_projection"] / cm,
        }
        if versus_cse is None and comparisons["flattened_cse_words"] >= 1:
            versus_cse = checkpoint
        if versus_direct is None and comparisons["direct_ast_restrict"] >= 1:
            versus_direct = checkpoint
        if versus_projection is None and comparisons["compiled_truth_projection"] >= 1:
            versus_projection = checkpoint
        checkpoints[str(checkpoint)] = {
            "best_fixed_method": fixed, "method_total_ns": totals,
            "cm_speedup_over_flattened_cse": comparisons["flattened_cse_words"],
            "cm_speedup_over_direct_ast": comparisons["direct_ast_restrict"],
            "cm_speedup_over_compiled_truth_projection": comparisons["compiled_truth_projection"],
            "cm_case_win_fraction_vs_flattened_cse": sum(
                medians[(case, "cm_ir_words", checkpoint)]
                < medians[(case, "flattened_cse_words", checkpoint)] for case in cases) / len(cases),
            "per_case_winners": winners,
            "per_case_oracle_total_ns": oracle_total,
            "per_case_oracle_speedup_over_best_fixed": totals[fixed] / oracle_total,
        }
    final = checkpoints["64"]
    promotion = (final["cm_speedup_over_flattened_cse"] >= speedup_gate
                 and final["cm_speedup_over_compiled_truth_projection"] >= 1.0
                 and final["cm_case_win_fraction_vs_flattened_cse"] >= case_fraction_gate)
    methods = {method: {
        "aggregate_setup_median_ns": sum(setup[(case, method)] for case in cases),
        "aggregate_warm_query_median_ns": sum(warm[(case, method)] for case in cases),
        "median_case_setup_ns": int(statistics.median(setup[(case, method)] for case in cases)),
        "median_case_warm_query_ns": int(statistics.median(warm[(case, method)] for case in cases)),
    } for method in METHODS}
    by_width = {}
    for n_vars in sorted(set(widths.values())):
        selected = [case for case in cases if widths[case] == n_vars]
        totals = {method: sum(medians[(case, method, 64)] for case in selected)
                  for method in METHODS}
        by_width[str(n_vars)] = {
            "cases": len(selected),
            "best_at_64": min(METHODS, key=lambda method: (totals[method], method)),
            "method_total_ns_at_64": totals,
            "cm_speedup_over_flattened_cse_at_64": totals["flattened_cse_words"] / totals["cm_ir_words"],
        }
    by_family = {}
    family_rule_total = 0
    family_rule_methods = {}
    for family in sorted(set(families.values())):
        selected = [case for case in cases if families[case] == family]
        totals = {method: sum(medians[(case, method, 64)] for case in selected)
                  for method in METHODS}
        best = min(METHODS, key=lambda method: (totals[method], method))
        family_rule_methods[family] = best
        family_rule_total += totals[best]
        by_family[family] = {"cases": len(selected), "best_at_64": best,
                             "method_total_ns_at_64": totals}
    fixed_total = final["method_total_ns"][final["best_fixed_method"]]
    adjusted_family_total = family_rule_total + router_budget_ns * len(cases)
    family_speedup = fixed_total / family_rule_total
    adjusted_family_speedup = fixed_total / adjusted_family_total
    return {
        "cases": len(cases), "measurement_rows": len(rows), "timed_sessions": len(rows),
        "timed_queries": len(rows) * 64, "checkpoints": checkpoints, "methods": methods,
        "cm_break_even_query_count_vs_flattened_cse": versus_cse,
        "cm_break_even_query_count_vs_direct_ast": versus_direct,
        "cm_break_even_query_count_vs_compiled_truth_projection": versus_projection,
        "cm_promotion_gate": promotion,
        "cm_promotion_gate_contract": {"checkpoint": 64,
            "speedup_over_flattened_cse_minimum": speedup_gate,
            "speedup_over_compiled_truth_projection_minimum": 1.0,
            "case_win_fraction_vs_flattened_cse_minimum": case_fraction_gate},
        "routing_headroom": {
            "checkpoint": 64,
            "best_fixed_method": final["best_fixed_method"],
            "best_fixed_total_ns": fixed_total,
            "per_case_oracle_total_ns": final["per_case_oracle_total_ns"],
            "per_case_oracle_raw_speedup": final["per_case_oracle_speedup_over_best_fixed"],
            "family_rule_methods": family_rule_methods,
            "family_rule_total_ns": family_rule_total,
            "family_rule_raw_speedup": family_speedup,
            "charged_router_budget_ns_per_case": router_budget_ns,
            "family_rule_budget_adjusted_total_ns": adjusted_family_total,
            "family_rule_budget_adjusted_speedup": adjusted_family_speedup,
            "exploratory_headroom_gate": adjusted_family_speedup >= routing_speedup_gate,
            "selection_is_post_hoc": True,
            "training_performed": False,
            "promotion_permitted": False,
        },
        "by_width": by_width, "by_family": by_family,
        "timing_is_local_and_machine_specific": True,
    }


def _measurement_row(planned: dict[str, Any], method: str, result: dict[str, Any]):
    return {"block": planned["block"], "case_position": planned["case_position"],
            "method_position": planned["method_order"].index(method),
            "order_sha256": planned["order_sha256"], "case_id": planned["case_id"],
            "family": planned["family"], "n_vars": planned["n_vars"], "method": method,
            "status": result["status"], "timings_ns": result["timings_ns"],
            "artifact_sha256": result["artifact"]["sha256"],
            "artifact_bytes": result["artifact"]["bytes"],
            "resources": result["resources"], "identity": result["identity"]}


def _selected_probes(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [min((case for case in cases if case["n_vars"] == n_vars),
                key=lambda case: (case["selection_sha256"], case["case_id"]))
            for n_vars in range(11, 17)]


def functional_external_probes(cases: list[dict[str, Any]]) -> dict[str, Any]:
    selected = _selected_probes(cases)
    bdd_rows = []
    for case in selected:
        expression = expr_from_json(case["expression_v2"])
        started = time.perf_counter_ns()
        bdd = ExactBddArtifact.build(expression, case["n_vars"],
                                     [f"x{i}" for i in range(case["n_vars"])],
                                     backend="autoref")
        for query in case["c36_trace"][:4]:
            fixed = {row["variable"]: row["value"] for row in query["fixed"]}
            remaining, vector = bdd.restrict_truth_bits(fixed)
            reduced = sum(int(value) << index for index, value in enumerate(vector))
            expected = next(row for row in case["c36_oracle"]["rows"]
                            if row["query"] == query["query"])
            if remaining != tuple(query["remaining_order"]) or format(reduced, "x") != expected["truth_bits_hex"]:
                raise RuntimeError("C36 BDD probe mismatch")
        nodes = bdd.node_count
        bdd.close()
        bdd_rows.append({"case_id": case["case_id"], "n_vars": case["n_vars"],
                         "queries": 4, "node_count": nodes,
                         "diagnostic_total_ns": time.perf_counter_ns() - started,
                         "exact_check_passed": True})
    from pysat.solvers import Cadical195
    sat_rows = []
    for case in selected:
        expression = expr_from_json(case["expression_v2"])
        formula = encode_expression_cnf(expression, case["n_vars"])
        solver = Cadical195(bootstrap_with=formula.clauses)
        query = case["c36_trace"][0]
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        remaining = query["remaining_order"]
        started = time.perf_counter_ns()
        reduced = 0
        for residual in range(1 << len(remaining)):
            values = dict(fixed)
            for position, name in enumerate(remaining):
                values[name] = (residual >> (len(remaining) - 1 - position)) & 1
            assumptions = [i + 1 if values[f"x{i}"] else -(i + 1)
                           for i in range(case["n_vars"])]
            reduced |= int(bool(solver.solve(assumptions=assumptions))) << residual
        elapsed = time.perf_counter_ns() - started
        solver.delete()
        expected = case["c36_oracle"]["rows"][0]
        if semantic_row(query, reduced, case["n_vars"])["truth_sha256"] != expected["truth_sha256"]:
            raise RuntimeError("C36 SAT probe mismatch")
        sat_rows.append({"case_id": case["case_id"], "n_vars": case["n_vars"],
                         "solve_calls": 1 << len(remaining), "diagnostic_total_ns": elapsed,
                         "exact_check_passed": True})
    _module, cudd_error = select_dd_module("cudd")
    return {"schema": "crse-c36-external-functional-probes/v1", "status": "passed",
            "autoref_bdd": {"timed": False, "performance_ranking_permitted": False,
                            "rows": bdd_rows},
            "native_cudd": {"available": _module is not None, "error": cudd_error,
                            "timed": False},
            "cadical": {"timed": False, "performance_ranking_permitted": False,
                        "rows": sat_rows}}


def _controls(cases: list[dict[str, Any]], contracts: dict[str, Any]) -> dict[str, Any]:
    first = cases[0]
    def refused(function) -> bool:
        try: function()
        except (ValueError, RuntimeError): return True
        return False
    wrong = json.loads(json.dumps(contracts[first["case_id"]][METHODS[0]]))
    wrong["validation"]["required_output_sha256"] = "0" * 64
    changed = json.loads(json.dumps(first))
    changed["c36_trace"][0]["fixed"][0]["value"] ^= 1
    values = {"wrong_oracle_refused": refused(lambda: execute_session(
                  case=first, contract=wrong, method=METHODS[0])),
              "tampered_trace_refused": refused(lambda: execute_session(
                  case=changed, contract=contracts[first["case_id"]][METHODS[0]], method=METHODS[0])),
              "method_contract_mismatch_refused": refused(lambda: execute_session(
                  case=first, contract=contracts[first["case_id"]][METHODS[0]], method=METHODS[1])),
              "training": False, "policy_refit": False, "production_write": False,
              "production_promotion": False}
    values["all_passed"] = all(values[key] for key in
                                ("wrong_oracle_refused", "tampered_trace_refused",
                                 "method_contract_mismatch_refused"))
    return {"schema": "crse-c36-functional-controls/v1", **values}


def render_report(result: dict[str, Any]) -> str:
    lines = ["# C36 wider natural repeated-query adjudication", "",
             f"Status: **{result['status']}**", "",
             "Eighteen fresh parameter/truth identities from the pinned Yosys source cover",
             "widths 11-16 with three cases per width. All timed methods deliver the same",
             "reduced relation, exact count, SAT status, and canonical witness.", "",
             "| Queries | Best fixed | CM vs CSE | CM vs direct | CM vs compiled projection |",
             "|---:|---|---:|---:|---:|"]
    for checkpoint in CHECKPOINTS:
        row = result["summary"]["checkpoints"][str(checkpoint)]
        lines.append(f"| {checkpoint} | {row['best_fixed_method']} | "
                     f"{row['cm_speedup_over_flattened_cse']:.4f}x | "
                     f"{row['cm_speedup_over_direct_ast']:.4f}x | "
                     f"{row['cm_speedup_over_compiled_truth_projection']:.4f}x |")
    routing = result["summary"]["routing_headroom"]
    lines += ["", f"Frozen CM gate: **{'pass' if result['summary']['cm_promotion_gate'] else 'fail'}**.",
              f"Post-hoc family-rule speedup after frozen routing budget: "
              f"**{routing['family_rule_budget_adjusted_speedup']:.4f}x**.",
              "This is exploratory headroom only; the rule was observed on these cases.", ""]
    return "\n".join(lines)


def run(config: C36Config, output: Path, dataset_path: Path,
        dataset_verification_path: Path, root: Path, *, progress=None) -> dict[str, Any]:
    config.validate()
    wall = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    verification = json.loads(dataset_verification_path.read_text(encoding="utf-8"))
    if (verification.get("status") != "verified"
            or verification.get("dataset_sha256") != _sha256(dataset_path)):
        raise ValueError("C36 frozen dataset verification binding")
    validate_dataset(dataset)
    cases = []
    oracles = {}
    for row in dataset["cases"]:
        from .gf2_wide_repeated_queries import oracle_document
        oracle = oracle_document(row, row["c36_trace"])
        cases.append({**row, "c36_oracle": oracle})
        oracles[row["case_id"]] = oracle
    contracts = {case["case_id"]: {method: task_contract(case, method) for method in METHODS}
                 for case in cases}
    schedule = build_schedule(cases, config.blocks, config.seed)
    validate_schedule(schedule, cases, config.blocks)
    import dd.autoref  # noqa: F401
    from pysat.solvers import Cadical195  # noqa: F401
    dependencies = {"dd": importlib.metadata.version("dd"),
                    "python_sat": importlib.metadata.version("python-sat"),
                    "numpy": importlib.metadata.version("numpy")}
    probes = functional_external_probes(cases)
    if probes["status"] != "passed":
        raise RuntimeError("C36 external functional probes failed")
    _write(output / "run_spec.json", {"schema": SCHEMA,
        "config": {**asdict(config), "checkpoints": list(config.checkpoints)},
        "dataset_path": dataset_path.relative_to(root).as_posix(),
        "dataset_sha256": _sha256(dataset_path),
        "dataset_verification_path": dataset_verification_path.relative_to(root).as_posix(),
        "dataset_verification_sha256": _sha256(dataset_verification_path),
        "methods": list(METHODS), "checkpoints": list(CHECKPOINTS),
        "training": False, "policy_refit": False, "production_promotion": False})
    _write(output / "contracts.json", contracts)
    _write(output / "oracles.json", oracles)
    _write_jsonl(output / "schedule.jsonl", schedule)
    _write(output / "dependencies.json", dependencies)
    _write(output / "external_functional_probes.json", probes)
    rows = []
    case_map = {case["case_id"]: case for case in cases}
    for schedule_index, planned in enumerate(schedule):
        case = case_map[planned["case_id"]]
        for method in planned["method_order"]:
            result = execute_session(case=case,
                                     contract=contracts[case["case_id"]][method], method=method)
            rows.append(_measurement_row(planned, method, result))
        if progress is not None: progress("timing", schedule_index + 1, len(schedule), case["case_id"])
        if time.perf_counter() - wall > config.max_seconds:
            raise TimeoutError("C36 experiment exceeded wall bound")
    _write_jsonl(output / "measurements.jsonl", rows)
    summary = summarize(rows, speedup_gate=config.cm_speedup_gate,
                        case_fraction_gate=config.cm_case_fraction_gate,
                        router_budget_ns=config.charged_router_budget_ns,
                        routing_speedup_gate=config.routing_speedup_gate)
    controls = _controls(cases, contracts)
    if not controls["all_passed"]: raise RuntimeError("C36 controls failed")
    _write(output / "functional_controls.json", controls)
    result = {"schema": SCHEMA, "status": "complete", "run_id": config.run_id,
              "dataset": {"cases": 18, "cases_per_width": 3, "widths": list(range(11, 17)),
                          "fresh_parameter_and_truth_identities": True,
                          "source_repository_reused": True},
              "measurement_rows": len(rows), "semantic_or_artifact_mismatches": 0,
              "functional_controls_passed": True, "external_functional_probes_passed": True,
              "summary": summary,
              "decision": {"training_performed": False, "policy_refit": False,
                           "cm_promotion_permitted": summary["cm_promotion_gate"],
                           "production_promotion": False},
              "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                              "machine": platform.machine(), "processor": platform.processor(),
                              "cpu_count": os.cpu_count(), "dependencies": dependencies},
              "elapsed_seconds": time.perf_counter() - wall,
              "runpod": {"used": False, "cost_usd": 0.0}}
    _write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    artifacts = ["run_spec.json", "contracts.json", "oracles.json", "schedule.jsonl",
                 "dependencies.json", "external_functional_probes.json", "measurements.jsonl",
                 "functional_controls.json", "results.json", "report.md"]
    _write(output / "manifest.json", {"schema": "crse-c36-run-manifest/v1",
        "sources": {dataset_path.relative_to(root).as_posix(): _sha256(dataset_path),
                    dataset_verification_path.relative_to(root).as_posix(): _sha256(dataset_verification_path),
                    "cmbench/recognition/yosys_wide_restriction_data.py": _sha256(root / "cmbench/recognition/yosys_wide_restriction_data.py"),
                    "cmbench/comparative/gf2_wide_repeated_queries.py": _sha256(root / "cmbench/comparative/gf2_wide_repeated_queries.py"),
                    "cmbench/comparative/gf2_wide_repeated_query_experiment.py": _sha256(root / "cmbench/comparative/gf2_wide_repeated_query_experiment.py")},
        "artifacts": {name: _sha256(output / name) for name in artifacts}})
    return result
