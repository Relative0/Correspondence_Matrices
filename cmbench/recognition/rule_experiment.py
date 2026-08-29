"""Bounded comparison of a proved metavariable rule with per-instance CM proof."""
from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import random
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

from .computation_experiment import (
    ComputationTask,
    EPFL_CORPUS,
    EPFL_PROVENANCE,
    Workload,
    load_epfl_d_cases,
    output_sha256,
    prepare_task,
    reference_task,
    sha256_file,
)
from .features import extract_features, structural_digest
from .proved_rules import (
    CompiledAigXorRule,
    ProvedRule,
    aig_xor_expr,
    compile_rule,
    prove_aig_xor_rule,
)
from .teacher import teach

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA = "crse-proved-rule-experiment/v1"
ARMS = ("no_rewrite", "compiled_warm", "compiled_cold", "instance_cm_proof")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


@dataclass(frozen=True)
class RuleExperimentConfig:
    data_seed: int = 20260829
    batch_sizes: tuple[int, ...] = (1, 8, 32, 128)
    rounds: int = 3
    epfl_limit: int = 12
    negative_controls: int = 16
    max_seconds: float = 120.0

    def validate(self) -> None:
        if type(self.data_seed) is not int or not 0 <= self.data_seed <= 2**32 - 1:
            raise ValueError("invalid data seed")
        if (type(self.batch_sizes) is not tuple or not self.batch_sizes
                or tuple(sorted(set(self.batch_sizes))) != self.batch_sizes
                or any(type(value) is not int or not 1 <= value <= 128 for value in self.batch_sizes)):
            raise ValueError("invalid repeated-application batch sizes")
        if type(self.rounds) is not int or not 1 <= self.rounds <= 5:
            raise ValueError("invalid timing rounds")
        if type(self.epfl_limit) is not int or not 1 <= self.epfl_limit <= 16:
            raise ValueError("invalid EPFL evaluation bound")
        if type(self.negative_controls) is not int or not 1 <= self.negative_controls <= 32:
            raise ValueError("invalid negative-control count")
        if type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 120:
            raise ValueError("wall budget must be in (0,120]")

    def run_spec(self, output: Path) -> dict[str, Any]:
        self.validate()
        return {
            "schema": "crse-proved-rule-run-spec/v1",
            "config": asdict(self),
            "rule": "NOT(NOT(A AND NOT B) AND NOT(NOT A AND B)) -> A XOR B",
            "proof_domain": "all four valuations of pure total Boolean metavariables A and B",
            "arms": list(ARMS),
            "timing_contract": {
                "rewrite_ns": "matching, candidate construction, and any per-instance proof",
                "total_ns": "artifact load/compile when applicable, rewrite, CSE build, and complete-vector execution",
                "audit": "independent scalar complete-vector evaluation outside every arm timer",
            },
            "resource_limits": {"variables": 8, "max_regions": 128, "max_nodes_per_region": 4096,
                                "max_applications_per_region": 256, "cpu_threads": 1,
                                "cooperative_wall_seconds": float(self.max_seconds), "network": False},
            "data_contract": "generated positive repetitions and negative controls; frozen EPFL D slice is evaluation-only",
            "output": str(output.resolve()),
        }


@dataclass(frozen=True)
class RuleRegion:
    region_id: str
    split: str
    expr: Expr
    expected_root_matches: int


def _clone(expr: Expr) -> Expr:
    return expr_from_json(expr_to_json_dag(expr))


def _terms(index: int) -> tuple[Expr, Expr, Expr]:
    a = And(Var(index % 8), Or(Var((index + 1) % 8), Var((index + 2) % 8)))
    b = Xor(Var((index + 3) % 8), Not(Var((index + 4) % 8)))
    c = Eqv(Var((index + 5) % 8), Imp(Var((index + 6) % 8), Var((index + 7) % 8)))
    return a, b, c


def _pattern(a: Expr, b: Expr, variant: int, *, corrupt_a: Expr | None = None) -> Expr:
    left = And(a, Not(b))
    right = And(Not(_clone(a) if corrupt_a is None else corrupt_a), _clone(b))
    if variant & 1:
        left = And(left.b, left.a)
    if variant & 2:
        right = And(right.b, right.a)
    outer_a, outer_b = Not(left), Not(right)
    if variant & 4:
        outer_a, outer_b = outer_b, outer_a
    return Not(And(outer_a, outer_b))


def make_rule_regions(config: RuleExperimentConfig) -> tuple[list[RuleRegion], list[RuleRegion]]:
    config.validate()
    positives = []
    offset = config.data_seed % 8
    for index in range(max(config.batch_sizes)):
        a, b, _c = _terms(index + offset)
        positives.append(RuleRegion(f"generated-positive-{index:03d}", "generated_positive",
                                    _pattern(a, b, (index + offset) % 8), 1))
    negatives = []
    for index in range(config.negative_controls):
        a, b, c = _terms(index + 211 + offset)
        negatives.append(RuleRegion(f"generated-near-match-{index:03d}", "generated_negative",
                                    _pattern(a, b, (index + offset) % 8, corrupt_a=c), 0))
    return positives, negatives


def region_document(region: RuleRegion) -> dict[str, Any]:
    return {"region_id": region.region_id, "split": region.split,
            "expected_root_matches": region.expected_root_matches,
            "structural_sha256": structural_digest(region.expr),
            "expression_v2": expr_to_json_dag(region.expr)}


def source_fingerprints() -> dict[str, str]:
    paths = [Path(__file__), ROOT / "cmbench" / "recognition" / "proved_rules.py",
             ROOT / "cmbench" / "recognition" / "teacher.py",
             ROOT / "cmbench" / "recognition" / "computation_experiment.py",
             ROOT / "bitset_backend.py", ROOT / "scripts" / "cm_recognition_rules.py",
             ROOT / "scripts" / "crse_rule_verify.py", EPFL_CORPUS, EPFL_PROVENANCE]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path) for path in paths}


def _deadline_check(started: float, maximum: float) -> None:
    if time.perf_counter() - started > maximum:
        raise TimeoutError("proved-rule experiment exceeded cooperative wall budget")


def _output_digest(values: list[int]) -> str:
    return hashlib.sha256(canonical(values)).hexdigest()


def measure_session(regions: list[RuleRegion], arm: str, round_index: int,
                    proof_path: Path, warm_matcher: CompiledAigXorRule,
                    expected: dict[str, tuple[int, ...]]) -> dict[str, Any]:
    if arm not in ARMS or not regions:
        raise ValueError("invalid rule measurement session")
    task = ComputationTask("complete_vector", 1)
    workload = Workload()
    proof_calls = proof_ns = load_compile_ns = 0
    rewrites_ns = matcher_ns = candidate_ns = cse_build_ns = cse_kernel_ns = 0
    proposals = applications = rejected = 0
    source_features = [extract_features(region.expr, 8) for region in regions]
    visited_nodes = sum(feature.identity_nodes for feature in source_features)
    source_nodes = sum(feature.structural_nodes for feature in source_features)
    results: list[int] = []
    rewritten_exprs: list[Expr] = []
    started = time.perf_counter_ns()
    matcher = warm_matcher
    if arm == "compiled_cold":
        cold_started = time.perf_counter_ns()
        matcher = compile_rule(ProvedRule.load(proof_path))
        load_compile_ns = max(1, time.perf_counter_ns() - cold_started)

    def explicit_cm_check(source: Expr, candidate: Expr) -> bool:
        nonlocal proof_calls, proof_ns
        check_started = time.perf_counter_ns()
        proof_calls += 1
        accepted = teach(source, 8).bits == teach(candidate, 8).bits
        proof_ns += max(1, time.perf_counter_ns() - check_started)
        return accepted

    for region in regions:
        source_nodes += extract_features(region.expr, 8).structural_nodes
        rewritten = region.expr
        if arm != "no_rewrite":
            rewrite_started = time.perf_counter_ns()
            rewrite = matcher.rewrite(region.expr, 8,
                verify=explicit_cm_check if arm == "instance_cm_proof" else None)
            rewrites_ns += max(1, time.perf_counter_ns() - rewrite_started)
            rewritten = rewrite.result
            matcher_ns += rewrite.match_ns
            candidate_ns += rewrite.candidate_ns
            proposals += rewrite.proposals
            applications += rewrite.applications
            rejected += rewrite.rejected
        build_ns, run = prepare_task("cse", rewritten, task, workload, 8)
        cse_build_ns += build_ns
        kernel_started = time.perf_counter_ns()
        actual = run()
        cse_kernel_ns += max(1, time.perf_counter_ns() - kernel_started)
        results.append(actual[0])
        rewritten_exprs.append(rewritten)
    total_ns = max(1, time.perf_counter_ns() - started)
    result_nodes = sum(extract_features(expr, 8).structural_nodes for expr in rewritten_exprs)
    result_digests = [structural_digest(expr) for expr in rewritten_exprs]
    mismatches = sum((value,) != expected[region.region_id]
                     for region, value in zip(regions, results))
    return {"schema": "crse-proved-rule-measurement/v1", "split": regions[0].split,
            "batch_id": f"{regions[0].split}/q-{len(regions)}", "batch_size": len(regions),
            "arm": arm, "round": round_index, "status": "ok" if not mismatches else "mismatch",
            "mismatches": mismatches, "proof_calls": proof_calls, "proof_ns": proof_ns,
            "load_compile_ns": load_compile_ns, "rewrite_ns": rewrites_ns,
            "matcher_ns": matcher_ns, "candidate_ns": candidate_ns,
            "cse_build_ns": cse_build_ns, "cse_kernel_ns": cse_kernel_ns,
            "total_ns": total_ns, "visited_nodes": visited_nodes, "proposals": proposals,
            "applications": applications, "rejected": rejected,
            "source_structural_nodes": source_nodes, "result_structural_nodes": result_nodes,
            "output_sha256": _output_digest(results),
            "result_digests_sha256": hashlib.sha256(canonical(result_digests)).hexdigest()}


def summarize(rows: list[dict[str, Any]], rounds: int, one_time_ns: int) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["batch_id"], row["arm"])].append(row)
    medians: dict[tuple[str, str], dict[str, float]] = {}
    metrics = ("total_ns", "rewrite_ns", "proof_ns", "load_compile_ns", "cse_build_ns", "cse_kernel_ns")
    for key, selected in grouped.items():
        if len(selected) == rounds and all(row["status"] == "ok" for row in selected):
            medians[key] = {metric: float(statistics.median(row[metric] for row in selected))
                            for metric in metrics}
            medians[key]["applications"] = float(statistics.median(row["applications"] for row in selected))
    batches = {}
    for batch_id in sorted({row["batch_id"] for row in rows}):
        if not all((batch_id, arm) in medians for arm in ARMS):
            continue
        compiled = medians[(batch_id, "compiled_warm")]
        instance = medians[(batch_id, "instance_cm_proof")]
        baseline = medians[(batch_id, "no_rewrite")]
        cold = medians[(batch_id, "compiled_cold")]
        batches[batch_id] = {
            "batch_size": next(row["batch_size"] for row in rows if row["batch_id"] == batch_id),
            "applications": int(compiled["applications"]),
            "median_ns": {arm: int(medians[(batch_id, arm)]["total_ns"]) for arm in ARMS},
            "median_rewrite_ns": {arm: int(medians[(batch_id, arm)]["rewrite_ns"]) for arm in ARMS},
            "median_instance_proof_ns": int(instance["proof_ns"]),
            "compiled_speedup_over_instance_proof_rewrite": (
                instance["rewrite_ns"] / compiled["rewrite_ns"] if compiled["rewrite_ns"] else None),
            "compiled_speedup_over_instance_proof_end_to_end": instance["total_ns"] / compiled["total_ns"],
            "compiled_speedup_over_no_rewrite_end_to_end": baseline["total_ns"] / compiled["total_ns"],
            "cold_speedup_over_instance_proof_end_to_end": instance["total_ns"] / cold["total_ns"],
        }
    generated = [value for key, value in batches.items() if key.startswith("generated_positive/")
                 and value["applications"] > 0]
    per_application_savings = []
    for value in generated:
        q = value["applications"]
        instance_cost = value["median_rewrite_ns"]["instance_cm_proof"]
        compiled_cost = value["median_rewrite_ns"]["compiled_warm"]
        per_application_savings.append(max(0.0, (instance_cost - compiled_cost) / q))
    savings = statistics.median(per_application_savings) if per_application_savings else 0.0
    return {"batches": batches, "one_time_proof_and_compile_ns": one_time_ns,
            "median_saved_rewrite_ns_per_application": savings,
            "estimated_break_even_applications": math.ceil(one_time_ns / savings) if savings > 0 else None,
            "timing_is_machine_specific": True}


def render_report(result: dict[str, Any]) -> str:
    lines = ["# CRSE proved metavariable rule experiment", "",
        f"Status: **{result['status']}**", f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Exact output mismatches: {result['semantic_mismatches']}", "",
        "## Rule and proof", "",
        "`NOT(NOT(A AND NOT B) AND NOT(NOT A AND B)) -> A XOR B`",
        "",
        "The rule was proved once by exhausting all four Boolean valuations of A and B. The fixed matcher enforces structural equality at repeated metavariable occurrences; the proof artifact is inert JSON and selects only a built-in matcher implementation.", "",
        f"One-time proof plus compile: {result['proof']['one_time_proof_and_compile_ns']} ns. Estimated break-even: {result['summaries']['estimated_break_even_applications']} applications.", "",
        "## Repeated applications", "",
        "| Batch | Applications | Warm compiled ns | Per-instance CM ns | Rewrite speedup | End-to-end speedup | Cold end-to-end speedup |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for key, value in result["summaries"]["batches"].items():
        lines.append(f"| {key} | {value['applications']} | {value['median_ns']['compiled_warm']} | "
                     f"{value['median_ns']['instance_cm_proof']} | "
                     f"{value['compiled_speedup_over_instance_proof_rewrite']:.3f} | "
                     f"{value['compiled_speedup_over_instance_proof_end_to_end']:.3f} | "
                     f"{value['cold_speedup_over_instance_proof_end_to_end']:.3f} |")
    lines += ["", "Every timed arm builds and executes the rewritten expression through the CSE backend. `instance_cm_proof` constructs and compares two explicit 8-variable correspondence matrices at every proposed site. Independent scalar enumeration audits outputs outside the timer.", "",
        f"Negative near-match controls: {result['negative_controls']['cases']}; false matches: {result['negative_controls']['false_matches']}.",
        f"EPFL evaluation cases: {result['epfl']['cases']}; matched motif applications per compiled session: {result['epfl']['applications']}.", "",
        "This establishes bounded exact reuse and local timing behavior. It does not yet establish a general rule language, cross-machine performance, or promotion of the rewrite into production routing.", ""]
    return "\n".join(lines)


def run_rule_experiment(config: RuleExperimentConfig, output: Path, progress=print) -> dict[str, Any]:
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    wall_started = time.perf_counter()
    before = source_fingerprints()
    _write_json(output / "run_spec.json", {**config.run_spec(output), "source_sha256": before})
    status, error_type = "incomplete", ""
    rows: list[dict[str, Any]] = []
    epfl_manifest: dict[str, Any] = {}
    negative_false_matches = 0
    epfl_applications = 0
    proof: ProvedRule | None = None
    proof_ns = compile_ns = 0
    try:
        progress("Proving the XOR AIG motif once over Boolean metavariables")
        started = time.perf_counter_ns()
        proof = prove_aig_xor_rule()
        proof_ns = max(1, time.perf_counter_ns() - started)
        proof_path = output / "proved_rule.json"
        proof.save(proof_path)
        proof = ProvedRule.load(proof_path)
        started = time.perf_counter_ns()
        matcher = compile_rule(proof)
        compile_ns = max(1, time.perf_counter_ns() - started)
        positives, negatives = make_rule_regions(config)
        _write_json(output / "generated_regions.json", {
            "schema": "crse-proved-rule-regions/v1", "seed": config.data_seed,
            "positive": [region_document(region) for region in positives],
            "negative": [region_document(region) for region in negatives]})
        for region in negatives:
            negative_false_matches += matcher.rewrite(region.expr, 8).applications
        if negative_false_matches:
            raise RuntimeError("compiled matcher accepted a negative near-match control")
        epfl_cases, epfl_manifest = load_epfl_d_cases(config.epfl_limit)
        epfl_regions = [RuleRegion(case.case_id, "epfl_d", case.expr, -1) for case in epfl_cases]
        _write_json(output / "epfl_evaluation_manifest.json", epfl_manifest)
        all_regions = positives + negatives + epfl_regions
        expected = {region.region_id: reference_task(region.expr,
                    ComputationTask("complete_vector", 1), Workload(), 8) for region in all_regions}
        progress("Comparing warm/cold compiled matching with explicit CM proof at each site")
        rng = random.Random(f"{config.data_seed}:proved-rule-arm-order/v1")
        batches = [(positives[:size], size) for size in config.batch_sizes]
        batches.append((epfl_regions, len(epfl_regions)))
        for round_index in range(config.rounds):
            for regions, _size in batches:
                _deadline_check(wall_started, config.max_seconds)
                arms = list(ARMS)
                rng.shuffle(arms)
                for arm in arms:
                    _deadline_check(wall_started, config.max_seconds)
                    rows.append(measure_session(regions, arm, round_index, proof_path, matcher, expected))
        epfl_rows = [row for row in rows if row["split"] == "epfl_d"
                     and row["arm"] == "compiled_warm" and row["round"] == 0]
        epfl_applications = sum(row["applications"] for row in epfl_rows)
        if any(row["status"] != "ok" for row in rows):
            raise RuntimeError("proved-rule computation cell failed exact audit")
        status = "complete"
    except (KeyboardInterrupt, Exception) as exc:
        status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        error_type = type(exc).__name__
        progress(f"Incomplete proved-rule run retained: {error_type}: {exc}")
    _write_jsonl(output / "measurements.jsonl", rows)
    one_time_ns = proof_ns + compile_ns
    summaries = summarize(rows, config.rounds, one_time_ns)
    after = source_fingerprints()
    result = {"schema": RUN_SCHEMA, "status": status, "error_type": error_type,
        "config": asdict(config), "source_sha256": before, "source_unchanged": before == after,
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "cpu_threads_requested": 1, "thread_environment": {name: os.environ.get(name)
                        for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
        "proof": {"rule_id": proof.document["rule_id"] if proof else None,
                  "artifact_sha256": proof.digest if proof else None, "proof_rows": 4,
                  "proof_ns": proof_ns, "compile_ns": compile_ns,
                  "one_time_proof_and_compile_ns": one_time_ns,
                  "universality_scope": "pure total Boolean expressions satisfying structural bindings"},
        "negative_controls": {"cases": config.negative_controls,
                              "false_matches": negative_false_matches},
        "epfl": {"cases": config.epfl_limit, "training_use": False,
                 "applications": epfl_applications, "selection": epfl_manifest},
        "row_count": len(rows), "summaries": summaries,
        "semantic_mismatches": sum(row["mismatches"] for row in rows),
        "failed_rows": sum(row["status"] != "ok" for row in rows),
        "criteria": {"safety_met": status == "complete" and negative_false_matches == 0
                                   and not any(row["mismatches"] for row in rows),
                     "bounded_reuse_demonstrated": status == "complete"
                         and any(row["applications"] >= max(config.batch_sizes) for row in rows),
                     "production_promotion": False},
        "wall_seconds": time.perf_counter() - wall_started,
        "scientific_claim": "one Boolean motif proof reused by a fixed structural matcher in a bounded local exact computation smoke"}
    _write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-proved-rule-artifacts/v1",
        "status": status, "files_sha256": {path.name: sha256_file(path) for path in files},
        "source_sha256": before})
    return result
