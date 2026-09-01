"""C18 evaluation-only transfer of the frozen C17 exact GF(2) dispatcher."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import sys
import time
from typing import Any

from .blif import parse_blif
from .gf2_decomposition import analyze_exact_gf2, analyze_screened_exact_gf2
from .gf2_task_dispatcher import (
    EXHAUSTIVE, SCREENED, GF2DecompositionTask, compile_gf2_dispatcher,
    load_gf2_dispatch_policy, select_gf2_arm, verify_gf2_execution,
)
from .gf2_task_dispatcher_experiment import METHODS, summarize

SCHEMA = "crse-c18-independent-gf2-dispatch-transfer/v1"


@dataclass(frozen=True)
class C18TransferConfig:
    run_id: str
    seed: int = 20260831
    rounds: int = 1
    max_partitions: int = 64
    materialize_budget: int = 4
    max_seconds: float = 900.0

    def validate(self) -> None:
        if (not self.run_id or type(self.rounds) is not int or not 1 <= self.rounds <= 3
                or self.max_partitions != 64 or self.materialize_budget != 4
                or type(self.max_seconds) not in (int, float)
                or not 120 <= self.max_seconds <= 1800):
            raise ValueError("invalid C18 transfer bounds")


def _write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def _best(analysis):
    return analysis.best.to_dict() if analysis.best else None


def _task(n_vars: int, config: C18TransferConfig) -> GF2DecompositionTask:
    return GF2DecompositionTask(n_vars, tuple(range(n_vars)), config.max_partitions,
                                config.materialize_budget)


def _bits(case: dict[str, Any]) -> int:
    return int(case["truth_bits_hex"], 16)


def _functional(cases, policy, config):
    expected_best, decisions = {}, {}
    mismatches = 0
    for case in cases:
        bits, n_vars = _bits(case), case["n_vars"]
        exhaustive = analyze_exact_gf2(bits, n_vars, max_partitions=config.max_partitions)
        screened = analyze_screened_exact_gf2(
            bits, n_vars, max_partitions=config.max_partitions,
            materialize_budget=config.materialize_budget)
        expected_best[case["case_id"]] = _best(exhaustive)
        if (_best(screened) != _best(exhaustive)
                or any(item.reconstruct() != bits for item in exhaustive.candidates)
                or any(item.reconstruct() != bits for item in screened.candidates)):
            mismatches += 1
        selected = select_gf2_arm(policy, _task(n_vars, config), advice_enabled=True)
        advice_off = select_gf2_arm(policy, _task(n_vars, config), advice_enabled=False)
        for decision in (selected, advice_off):
            decisions[decision.reason] = decisions.get(decision.reason, 0) + 1
        expected_arm = EXHAUSTIVE if n_vars <= 3 else SCREENED
        if selected.selected_arm != expected_arm or advice_off.selected_arm != EXHAUSTIVE:
            mismatches += 1
    return {"cases": len(cases), "mismatches": mismatches, "all_exact": mismatches == 0}, expected_best, decisions


def _measure(method, case, netlist, expected_best, config, dispatcher, policy_sha, round_index):
    representation_started = time.perf_counter_ns()
    bits, support = netlist.packed_value(case["root_node"])
    representation_ns = max(1, time.perf_counter_ns() - representation_started)
    if bits != _bits(case) or len(support) != case["n_vars"]:
        raise RuntimeError("C18 timed BLIF representation mismatch")
    wrapper_ns = 0
    if method.startswith("direct_"):
        started = time.perf_counter_ns()
        if method == "direct_exhaustive":
            analysis = analyze_exact_gf2(bits, case["n_vars"], max_partitions=config.max_partitions)
            selected_arm = EXHAUSTIVE
        else:
            analysis = analyze_screened_exact_gf2(
                bits, case["n_vars"], max_partitions=config.max_partitions,
                materialize_budget=config.materialize_budget)
            selected_arm = SCREENED
        analysis_ns = max(1, time.perf_counter_ns() - started)
        checked = time.perf_counter_ns()
        best = _best(analysis)
        exact = all(item.reconstruct() == bits for item in analysis.candidates)
        exact_check_ns = max(1, time.perf_counter_ns() - checked)
        policy_ns = shadow_ns = 0
        reason = "direct_control"
        partitions, descriptors, materialized = (analysis.partitions_tested,
                                                  analysis.descriptors_screened,
                                                  analysis.artifacts_materialized)
    else:
        started = time.perf_counter_ns()
        execution = dispatcher.execute(bits)
        call_ns = max(1, time.perf_counter_ns() - started)
        verify_gf2_execution(execution.to_dict(), bits, policy_sha256=policy_sha)
        wrapper_ns = max(0, call_ns - execution.total_ns)
        analysis_ns, exact_check_ns, policy_ns, shadow_ns = (
            execution.analysis_ns, execution.exact_check_ns, execution.policy_ns, execution.shadow_ns)
        selected_arm, reason, best, exact = (execution.selected_arm, execution.decision_reason,
                                             execution.best_artifact, execution.exact_check_passed)
        partitions, descriptors, materialized = (execution.partitions_tested,
                                                  execution.descriptors_screened,
                                                  execution.artifacts_materialized)
    total_ns = representation_ns + policy_ns + analysis_ns + exact_check_ns + shadow_ns + wrapper_ns
    return {
        "case_id": case["case_id"], "source_file": case["source_file"],
        "source_kind": case["source_kind"], "split": case["split"],
        "n_vars": case["n_vars"], "method": method, "round": round_index,
        "selected_arm": selected_arm, "decision_reason": reason,
        "representation_ns": representation_ns, "policy_ns": policy_ns,
        "analysis_ns": analysis_ns, "exact_check_ns": exact_check_ns,
        "shadow_ns": shadow_ns, "wrapper_ns": wrapper_ns, "total_ns": total_ns,
        "partitions_tested": partitions, "descriptors_screened": descriptors,
        "artifacts_materialized": materialized,
        "semantic_mismatches": int(not exact),
        "artifact_mismatches": int(best != expected_best[case["case_id"]]),
        "best_artifact_sha256": best["payload_sha256"] if best else None,
        "truth_sha256": case["truth_sha256"],
    }


def run(config: C18TransferConfig, output: Path, dataset_path: Path,
        policy_path: Path, root: Path) -> dict[str, Any]:
    config.validate()
    wall = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset, policy = json.loads(dataset_path.read_text()), load_gf2_dispatch_policy(policy_path)
    cases = dataset["cases"]
    if len(cases) != 73 or dataset["provenance"]["policy_refit_allowed"] is not False:
        raise ValueError("C18 requires the verified 73-case evaluation-only freeze")
    _write(output / "run_spec.json", {
        "schema": SCHEMA, "config": asdict(config), "methods": list(METHODS),
        "policy_path": str(policy_path.relative_to(root)).replace("\\", "/"),
        "policy_sha256": policy["policy_sha256"], "policy_refit": False,
        "timing_role": "single_round_independent_transfer_scout",
        "predeclared_gates": {"aggregate_speedup": 1.25, "slow_tail": 1.20,
                              "minimum_case": 0.97}, "production_promotion": False})
    functional, expected_best, decisions = _functional(cases, policy, config)
    _write(output / "functional.json", {"summary": functional, "decisions": decisions})
    netlists = {}
    for case in cases:
        path = root / case["source_file"]
        netlists.setdefault(path, parse_blif(path))
    dispatchers = {}
    for method, advice in (("c17_dispatch", True), ("c17_advice_off", False)):
        for n_vars in sorted({case["n_vars"] for case in cases}):
            dispatchers[(method, n_vars)] = compile_gf2_dispatcher(
                policy, _task(n_vars, config), advice_enabled=advice)
    rows = []
    rng = random.Random(f"{config.seed}:c18-balanced-method-order/v1")
    for round_index in range(config.rounds):
        order = [(case, method) for case in cases for method in METHODS]
        rng.shuffle(order)
        for case, method in order:
            if time.perf_counter() - wall > config.max_seconds:
                raise TimeoutError("C18 transfer exceeded wall bound")
            dispatcher = None if method.startswith("direct_") else dispatchers[(method, case["n_vars"])]
            rows.append(_measure(method, case, netlists[root / case["source_file"]], expected_best,
                                 config, dispatcher, policy["policy_sha256"], round_index))
    with (output / "measurements.jsonl").open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    # C17's summary deliberately uses only the common charged fields. wrapper_ns is
    # already included in total_ns, so C18 also charges the dispatch call boundary.
    summary = summarize(rows, functional)
    mismatches = functional["mismatches"] + sum(row["semantic_mismatches"] + row["artifact_mismatches"] for row in rows)
    result = {
        "schema": SCHEMA, "status": "complete" if not mismatches else "failed",
        "config": asdict(config), "wall_seconds": time.perf_counter() - wall,
        "dataset": {"cases": len(cases), "source_files": len(netlists),
                    "family": "VTR BLIF", "independent_transfer": True,
                    "policy_refit": False},
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "thread_environment": {name: os.environ.get(name) for name in
                                               ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
        "functional": functional, "decision_counts": decisions,
        "measurement_rows": len(rows), "semantic_or_artifact_mismatches": mismatches,
        "summary": summary, "claims": {"exact_transfer": mismatches == 0,
                                       "learned_or_approximate_values": False,
                                       "production_promotion": False,
                                       "single_round_timing": True},
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    source_names = ("cmbench/recognition/gf2_independent_transfer_experiment.py",
                    "scripts/cm_recognition_c18_gf2_transfer.py")
    artifact_names = ("run_spec.json", "functional.json", "measurements.jsonl", "results.json")
    _write(output / "manifest.json", {
        "schema": "crse-c18-transfer-run-manifest/v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "policy_file_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "sources": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in source_names},
        "artifacts": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in artifact_names},
    })
    return result
