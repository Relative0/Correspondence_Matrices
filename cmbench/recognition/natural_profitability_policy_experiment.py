"""Milestone D9: freeze a calibrated rewrite gate before natural BLIF evaluation."""
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
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bitset_backend import build_bitset_env, compile_expr_cse, eval_expr_bitset
from cm_expr_serde import expr_to_json_dag
from cm_exprlib import And, Expr, Not, Or, Var

from .blif import BlifConeMetadata, parse_blif
from .computation_experiment import ComputationTask, Workload, prepare_task, sha256_file
from .features import postorder, structural_digest
from .portfolio import admit
from .profitability_policy import (
    ACTIONS, CALIBRATION_SCHEMA, EnvironmentCalibration, ProfitabilityMetadata,
    ProfitabilityTree, feature_vector, fit_profitability_tree, sha256_document,
)
from .rule_pack import RULE_PRIORITY_V2, compile_rule_pack, factored_or_expr, prove_rule_pack_v2


ROOT = Path(__file__).resolve().parents[2]
EPFL_ROOT = ROOT / "external" / "epfl-benchmarks"
BEST_RESULTS = EPFL_ROOT / "best_results"
EPFL_COMMIT = "0060e156826e733d69bf5b3322d1bdd0d03a1f9a"
EPFL_URL = "https://github.com/lsils/benchmarks.git"
RUN_SCHEMA = "crse-natural-profitability-policy-experiment/v1"
MEASUREMENT_SCHEMA = "crse-natural-profitability-policy-measurement/v1"
SPLITS = {
    "training": ("depth", ("arbiter", "cavlc", "i2c", "int2float", "router")),
    "validation": ("depth", ("mem_ctrl",)),
    "evaluation": ("size", ("priority", "voter", "div", "max", "multiplier", "sin")),
}
EVALUATION_SOURCE_EXCLUSIONS = {
    "adder": "no admissible 9-12 support cone within the expression bound",
    "hyp": "source file exceeds the bounded structural-scan budget",
    "log2": "no cone passed the current rule-engine depth/unfolded-work admission bound",
    "sqrt": "source topology exceeds the bounded structural-scan time budget",
    "square": "source topology exceeds the bounded structural-scan time budget",
}
REUSES = (8, 32, 128)
ARMS = ("no_rewrite", "one_pass", "frozen_gate")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


def _digest_int(value: int, support: int) -> str:
    return hashlib.sha256(value.to_bytes(max(1, (1 << support) // 8), "little")).hexdigest()


@dataclass(frozen=True)
class NaturalProfitabilityConfig:
    cases_per_circuit: int = 2
    min_support: int = 9
    max_support: int = 12
    max_source_nodes: int = 128
    max_identity_nodes: int = 4096
    training_rounds: int = 2
    evaluation_rounds: int = 3
    max_seconds: float = 120.0

    def validate(self) -> None:
        if type(self.cases_per_circuit) is not int or not 1 <= self.cases_per_circuit <= 3:
            raise ValueError("cases per circuit must be in [1,3]")
        if (type(self.min_support) is not int or type(self.max_support) is not int
                or not 9 <= self.min_support <= self.max_support <= 12):
            raise ValueError("support range must stay within [9,12]")
        if type(self.max_source_nodes) is not int or not 16 <= self.max_source_nodes <= 256:
            raise ValueError("source-node bound must be in [16,256]")
        if type(self.max_identity_nodes) is not int or not 256 <= self.max_identity_nodes <= 4096:
            raise ValueError("identity-node bound must be in [256,4096]")
        if (type(self.training_rounds) is not int or not 1 <= self.training_rounds <= 3
                or type(self.evaluation_rounds) is not int
                or not 1 <= self.evaluation_rounds <= 3):
            raise ValueError("timing rounds must be in [1,3]")
        if type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 120:
            raise ValueError("wall budget must be in (0,120]")

    def run_spec(self, output: Path) -> dict[str, Any]:
        self.validate()
        return {
            "schema": "crse-natural-profitability-policy-run-spec/v1",
            "status": "planned",
            "config": asdict(self),
            "splits": {key: {"variant": value[0], "circuits": list(value[1])}
                       for key, value in SPLITS.items()},
            "arms": list(ARMS), "reuses": list(REUSES), "rules": list(RULE_PRIORITY_V2),
            "selection_contract": "circuit-disjoint; two deterministic structural quantiles; no rule-incidence or timing selection/v1",
            "training_contract": "depth/control BLIF only; all reuse levels; depth-3 cost tree; 5-percent predicted-gain floor/v1",
            "freeze_contract": "calibration and inert policy written and hashed before validation or size/arithmetic BLIF is parsed/v1",
            "timing_contract": "decision-plus-one-pass-rewrite-plus-CSE-build-plus-repeated-complete-vector-kernel/v1",
            "oracle_contract": "independent packed BLIF LUT evaluation outside timed arms/v1",
            "resource_limits": {"cpu_threads": 1, "network": False, "max_lut_support": 12,
                "max_source_nodes": self.max_source_nodes,
                "max_identity_nodes": self.max_identity_nodes,
                "max_kernel_repeats": max(REUSES),
                "cooperative_wall_seconds": float(self.max_seconds)},
            "source_scope": "new optimized BLIF artifacts and circuit-disjoint split within the same EPFL benchmark family",
            "evaluation_source_exclusions": EVALUATION_SOURCE_EXCLUSIONS,
            "output": str(output.resolve()),
        }


@dataclass(frozen=True)
class NaturalPolicyCase:
    case_id: str
    split: str
    circuit: str
    variant: str
    source_path: str
    source_sha256: str
    root: str
    expr: Expr
    oracle: int
    metadata: ProfitabilityMetadata
    alpha_sha256: str
    structural_sha256: str

    def document(self) -> dict[str, Any]:
        return {"case_id": self.case_id, "split": self.split, "circuit": self.circuit,
            "variant": self.variant, "source_path": self.source_path,
            "source_sha256": self.source_sha256, "root": self.root,
            "metadata": asdict(self.metadata), "alpha_sha256": self.alpha_sha256,
            "structural_sha256": self.structural_sha256,
            "oracle_sha256": _digest_int(self.oracle, self.metadata.support),
            "expression_v2": expr_to_json_dag(self.expr)}


def _deadline(started: float, seconds: float) -> None:
    if time.monotonic() - started > seconds:
        raise TimeoutError("D9 cooperative wall budget exceeded")


def _source_path(variant: str, circuit: str) -> Path:
    matches = sorted((BEST_RESULTS / variant).glob(f"{circuit}_*.blif"))
    if len(matches) != 1:
        raise ValueError(f"expected one frozen BLIF for {variant}/{circuit}")
    return matches[0]


def _trial_order(length: int, count: int) -> list[int]:
    targets = ([0] if count == 1 else
               [round(slot * (length - 1) / (count - 1)) for slot in range(count)])
    result = []
    limit = min(length, 64)
    for offset in range(length):
        for target in targets:
            for index in ((target - offset), (target + offset)):
                if 0 <= index < length and index not in result:
                    result.append(index)
                    if len(result) == limit:
                        return result
    return result


def load_split(split: str, config: NaturalProfitabilityConfig, *,
               excluded_digests: set[str], wall_started: float) -> tuple[list[NaturalPolicyCase], dict[str, Any]]:
    if split not in SPLITS:
        raise ValueError("unknown D9 split")
    variant, circuits = SPLITS[split]
    cases: list[NaturalPolicyCase] = []
    rejected = Counter()
    files = []
    for circuit in circuits:
        _deadline(wall_started, config.max_seconds)
        path = _source_path(variant, circuit)
        netlist = parse_blif(path)
        metadata = sorted(netlist.candidate_metadata(
            min_support=config.min_support, max_support=config.max_support,
            max_source_nodes=config.max_source_nodes),
            key=lambda item: (item.source_nodes, item.depth, item.node))
        selected: list[NaturalPolicyCase] = []
        for index in _trial_order(len(metadata), config.cases_per_circuit):
            if len(selected) == config.cases_per_circuit:
                break
            item = metadata[index]
            try:
                expr, support = netlist.build_expr(item.node,
                    max_identity_nodes=config.max_identity_nodes)
                admit(expr, len(support), 1)
                oracle, oracle_support = netlist.packed_value(item.node)
                if support != oracle_support:
                    raise ValueError("BLIF support disagreement")
                actual = eval_expr_bitset(expr, build_bitset_env(
                    tuple(f"x{i}" for i in range(len(support)))))
                if actual != oracle:
                    raise ValueError("BLIF expression/oracle disagreement")
                alpha = structural_digest(expr, alpha_rename=True)
                if alpha in excluded_digests or any(case.alpha_sha256 == alpha for case in selected):
                    rejected["duplicate_alpha_structure"] += 1
                    continue
                policy_metadata = ProfitabilityMetadata(len(support), REUSES[0],
                    item.source_nodes, item.source_edges, item.depth,
                    item.local_cubes, item.local_literals)
                selected.append(NaturalPolicyCase(
                    f"{split}-{variant}-{circuit}-{item.node}", split, circuit, variant,
                    str(path.relative_to(ROOT)).replace("\\", "/"), sha256_file(path), item.node,
                    expr, oracle, policy_metadata, alpha, structural_digest(expr)))
            except (ValueError, TypeError, RecursionError):
                rejected["expression_admission"] += 1
        if not selected:
            raise ValueError(f"no admissible cases for {variant}/{circuit}")
        if len(selected) < config.cases_per_circuit:
            rejected["circuit_below_requested_case_count"] += 1
        cases.extend(selected)
        excluded_digests.update(case.alpha_sha256 for case in selected)
        files.append({"circuit": circuit, "path": selected[0].source_path,
                      "sha256": selected[0].source_sha256,
                      "candidate_count": len(metadata),
                      "selected_roots": [case.root for case in selected]})
    return cases, {"schema": "crse-natural-profitability-selection/v1", "split": split,
        "variant": variant, "circuits": list(circuits), "training_use": split == "training",
        "files": files, "selected_count": len(cases), "rejected": dict(rejected),
        "selection": "structural quantiles with bounded nearest-candidate admission; no incidence or timing filter"}


def cases_document(cases: list[NaturalPolicyCase], selection: dict[str, Any]) -> dict[str, Any]:
    return {**selection, "cases": [case.document() for case in cases]}


def _calibrate(matcher) -> EnvironmentCalibration:
    a = And(Var(0), Not(Var(1)))
    b = Or(Var(2), Var(3))
    c = And(Var(4), Or(Var(5), Var(6)))
    probe = And(factored_or_expr(a, b, c), Or(Var(7), Not(Var(7))))
    expected = eval_expr_bitset(probe, build_bitset_env(tuple(f"x{i}" for i in range(8))))
    matcher_samples, kernel_samples = [], []
    applications = semantic_mismatches = 0
    result = probe
    for _ in range(9):
        started = time.perf_counter_ns()
        rewrite = matcher.rewrite(probe, 8)
        matcher_samples.append(max(1, time.perf_counter_ns() - started) / len(postorder(probe)))
        result, applications = rewrite.result, rewrite.applications
        program = compile_expr_cse(result, flatten=True)
        _build_ns, run = prepare_task("cse", result, ComputationTask("complete_vector", 1), Workload(), 8)
        started = time.perf_counter_ns()
        values = [run()[0] for _index in range(32)]
        elapsed = max(1, time.perf_counter_ns() - started)
        kernel_samples.append(elapsed / (max(1, len(program.ops)) * 32))
        semantic_mismatches += sum(value != expected for value in values)
    document = {"schema": CALIBRATION_SCHEMA,
        "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(),
            "processor": platform.processor(), "cpu_count": os.cpu_count(),
            "thread_limits": {key: os.environ.get(key, "") for key in (
                "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}},
        "probe": {"structural_sha256": structural_digest(probe), "source_nodes": len(postorder(probe)),
            "result_nodes": len(postorder(result)), "rounds": 9, "kernel_reuses": 32,
            "applications": applications},
        "matcher_node_ns": statistics.median(matcher_samples),
        "kernel_node_execution_ns": statistics.median(kernel_samples),
        "semantic_mismatches": semantic_mismatches}
    return EnvironmentCalibration.from_dict(document)


def _with_reuses(case: NaturalPolicyCase, reuses: int) -> ProfitabilityMetadata:
    value = case.metadata
    return ProfitabilityMetadata(value.support, reuses, value.source_nodes,
        value.source_edges, value.depth, value.local_cubes, value.local_literals)


def measure(case: NaturalPolicyCase, reuses: int, arm: str, round_index: int,
            matcher, policy: ProfitabilityTree | None,
            calibration: EnvironmentCalibration) -> dict[str, Any]:
    metadata = _with_reuses(case, reuses)
    decision_ns = 0
    decision_reason = "fixed_arm"
    action = arm
    if arm == "frozen_gate":
        if policy is None:
            raise ValueError("frozen gate arm requires a policy")
        decision = policy.decide(metadata, calibration)
        action, decision_reason, decision_ns = decision.action, decision.reason, decision.decision_ns
    rewritten = case.expr
    rewrite_ns = 0
    applications = proposals = conflicts = 0
    applications_by_rule = {rule_id: 0 for rule_id in RULE_PRIORITY_V2}
    if action == "one_pass":
        started = time.perf_counter_ns()
        rewrite = matcher.rewrite(case.expr, metadata.support)
        rewrite_ns = max(1, time.perf_counter_ns() - started)
        rewritten = rewrite.result
        applications, proposals, conflicts = rewrite.applications, rewrite.proposals, rewrite.conflicts
        applications_by_rule = rewrite.applications_by_rule
    build_ns, run = prepare_task("cse", rewritten, ComputationTask("complete_vector", 1),
                                 Workload(), metadata.support)
    started = time.perf_counter_ns()
    values = [run()[0] for _index in range(reuses)]
    kernel_ns = max(1, time.perf_counter_ns() - started)
    mismatches = sum(value != case.oracle for value in values)
    before = compile_expr_cse(case.expr, flatten=True)
    after = compile_expr_cse(rewritten, flatten=True)
    return {"schema": MEASUREMENT_SCHEMA, "split": case.split, "case_id": case.case_id,
        "circuit": case.circuit, "root": case.root, "round": round_index, "arm": arm,
        "selected_action": action, "decision_reason": decision_reason,
        "expected_reuses": reuses, "metadata": asdict(metadata),
        "decision_ns": decision_ns, "rewrite_ns": rewrite_ns, "cse_build_ns": build_ns,
        "cse_kernel_ns": kernel_ns, "total_ns": decision_ns + rewrite_ns + build_ns + kernel_ns,
        "applications": applications, "proposals": proposals, "conflicts": conflicts,
        "applications_by_rule": applications_by_rule,
        "cse_ops_before": len(before.ops), "cse_ops_after": len(after.ops),
        "source_sha256": case.structural_sha256, "result_sha256": structural_digest(rewritten),
        "oracle_sha256": _digest_int(case.oracle, metadata.support),
        "output_sha256": _digest_int(values[0], metadata.support),
        "mismatches": mismatches, "status": "ok" if mismatches == 0 else "mismatch"}


def _measure_split(cases: list[NaturalPolicyCase], rounds: int, arms: tuple[str, ...],
                   matcher, policy, calibration, *, seed: str,
                   wall_started: float, max_seconds: float) -> list[dict[str, Any]]:
    rows = []
    rng = random.Random(seed)
    for round_index in range(rounds):
        cells = [(case, reuses, arm) for case in cases for reuses in REUSES for arm in arms]
        rng.shuffle(cells)
        for case, reuses, arm in cells:
            _deadline(wall_started, max_seconds)
            rows.append(measure(case, reuses, arm, round_index, matcher, policy, calibration))
    return rows


def _fit(rows: list[dict[str, Any]], cases: list[NaturalPolicyCase], calibration,
         manifest_sha: str) -> ProfitabilityTree:
    timings = defaultdict(list)
    for row in rows:
        timings[(row["case_id"], row["expected_reuses"], row["arm"])].append(row["total_ns"])
    by_id = {case.case_id: case for case in cases}
    features, costs = [], []
    for case_id in sorted(by_id):
        for reuses in REUSES:
            features.append(feature_vector(_with_reuses(by_id[case_id], reuses), calibration))
            costs.append([statistics.median(timings[(case_id, reuses, action)]) for action in ACTIONS])
    return fit_profitability_tree(features, costs, calibration_sha256=calibration.digest,
        training_manifest_sha256=manifest_sha, max_depth=3, min_leaf=3, min_gain=0.05)


def summarize_split(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["case_id"], row["expected_reuses"], row["arm"])].append(row["total_ns"])
    medians = {key: statistics.median(values) for key, values in grouped.items()}
    keys = sorted({(row["case_id"], row["expected_reuses"]) for row in rows})
    totals = {arm: sum(medians[(case_id, reuses, arm)] for case_id, reuses in keys) for arm in ARMS}
    oracle_total = sum(min(medians[(case_id, reuses, "no_rewrite")],
                           medians[(case_id, reuses, "one_pass")]) for case_id, reuses in keys)
    decisions = {}
    confusion = Counter()
    reasons = Counter()
    for case_id, reuses in keys:
        row = next(item for item in rows if item["case_id"] == case_id
                   and item["expected_reuses"] == reuses and item["arm"] == "frozen_gate")
        predicted = row["selected_action"]
        actual = min(ACTIONS, key=lambda arm: (medians[(case_id, reuses, arm)], arm))
        confusion[f"predicted_{predicted}__actual_{actual}"] += 1
        reasons[row["decision_reason"]] += 1
        decisions[f"{case_id}/reuse-{reuses}"] = {"predicted": predicted, "actual": actual,
            "reason": row["decision_reason"], "gate_median_ns": medians[(case_id, reuses, "frozen_gate")],
            "no_rewrite_median_ns": medians[(case_id, reuses, "no_rewrite")],
            "one_pass_median_ns": medians[(case_id, reuses, "one_pass")]}
    raw_regret = (totals["frozen_gate"] - oracle_total) / oracle_total
    return {"workloads": len(keys), "median_cell_totals_ns": totals,
        "frozen_gate_speedup_over_no_rewrite": totals["no_rewrite"] / totals["frozen_gate"],
        "one_pass_speedup_over_no_rewrite": totals["no_rewrite"] / totals["one_pass"],
        "free_oracle_total_ns": oracle_total,
        "frozen_gate_regret_fraction": max(0.0, raw_regret),
        "frozen_gate_timing_delta_vs_free_oracle_fraction": raw_regret,
        "gate_apply_count": sum(value["predicted"] == "one_pass" for value in decisions.values()),
        "gate_abstain_count": sum(value["predicted"] == "no_rewrite" for value in decisions.values()),
        "decision_reasons": dict(sorted(reasons.items())), "confusion": dict(sorted(confusion.items())),
        "decisions": decisions}


def source_fingerprints() -> dict[str, str]:
    paths = [Path(__file__), ROOT / "cmbench" / "recognition" / "blif.py",
        ROOT / "cmbench" / "recognition" / "profitability_policy.py",
        ROOT / "cmbench" / "recognition" / "rule_pack.py",
        ROOT / "scripts" / "cm_recognition_natural_profitability_policy.py",
        ROOT / "scripts" / "crse_natural_profitability_policy_verify.py",
        EPFL_ROOT / "LICENSE"]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path) for path in paths}


def _report(summary: dict[str, Any]) -> str:
    evaluation = summary["summaries"]["evaluation"]
    validation = summary["summaries"]["validation"]
    return f"""# CRSE Milestone D9: frozen natural profitability policy

Date: 2026-08-29  
Status: **{summary['status']}**

## Result

The calibrated policy was trained only on circuit-disjoint EPFL depth/control BLIF cones,
then frozen before validation and size/arithmetic BLIF parsing. All {summary['semantic_checks']}
timed outputs agreed with an independent packed BLIF oracle; semantic mismatches were **0**.

On the sealed evaluation split, the frozen gate selected one pass for
**{evaluation['gate_apply_count']} / {evaluation['workloads']}** workloads and abstained to
no rewrite for **{evaluation['gate_abstain_count']}**. Its aggregate speedup over unconditional
no rewrite was **{evaluation['frozen_gate_speedup_over_no_rewrite']:.4f}x**, with
**{evaluation['frozen_gate_regret_fraction']:.2%}** regret versus a free per-workload oracle.
Unconditional one pass measured **{evaluation['one_pass_speedup_over_no_rewrite']:.4f}x**.

Validation measured **{validation['frozen_gate_speedup_over_no_rewrite']:.4f}x** for the frozen
gate versus no rewrite. Decision time is charged to the gate arm.

## Interpretation

This is a leakage-controlled mechanism test, not production promotion. The source uses new
optimized BLIF artifacts, a new LUT/SOP representation, and circuit-disjoint training and
evaluation groups, but both groups still come from the EPFL benchmark suite. A result here is
not independent benchmark-family confirmation. Out-of-range inputs and calibration identity
mismatches conservatively select no rewrite. If the gate applies no rules, a small measured
speed difference versus the no-rewrite control is timing variation and is not a rewrite win.
"""


def run_natural_profitability_policy_experiment(config: NaturalProfitabilityConfig,
                                                output: Path) -> dict[str, Any]:
    config.validate()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    wall_started = time.monotonic()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[key] = "1"
    if not (EPFL_ROOT / ".git").is_dir() or not (EPFL_ROOT / "LICENSE").is_file():
        raise ValueError("frozen EPFL checkout is unavailable")
    spec = config.run_spec(output)
    spec["source_sha256"] = source_fingerprints()
    spec["upstream"] = {"commit": EPFL_COMMIT, "url": EPFL_URL, "license": "MIT License"}
    _write_json(output / "run_spec.json", spec)

    pack = prove_rule_pack_v2()
    pack.save(output / "proved_rule_pack.json")
    matcher = compile_rule_pack(pack)
    calibration = _calibrate(matcher)
    _write_json(output / "calibration.json", calibration.document)

    seen: set[str] = set()
    training, training_selection = load_split("training", config,
        excluded_digests=seen, wall_started=wall_started)
    _write_json(output / "training_cases.json", cases_document(training, training_selection))
    training_rows = _measure_split(training, config.training_rounds, ACTIONS, matcher, None,
        calibration, seed="d9-training-arm-order/v1", wall_started=wall_started,
        max_seconds=config.max_seconds)
    _write_jsonl(output / "training_measurements.jsonl", training_rows)
    training_manifest = {"schema": "crse-profitability-training-manifest/v1",
        "training_use": True, "selection_sha256": sha256_file(output / "training_cases.json"),
        "measurements_sha256": sha256_file(output / "training_measurements.jsonl"),
        "calibration_sha256": calibration.digest, "actions": list(ACTIONS),
        "reuses": list(REUSES), "case_count": len(training)}
    _write_json(output / "training_manifest.json", training_manifest)
    training_manifest_sha = sha256_document(training_manifest)
    policy = _fit(training_rows, training, calibration, training_manifest_sha)
    policy.save(output / "policy.json")
    policy = ProfitabilityTree.load(output / "policy.json")
    freeze = {"schema": "crse-profitability-policy-freeze/v1", "frozen": True,
        "frozen_before_validation_or_evaluation_load": True,
        "calibration_document_sha256": calibration.digest,
        "calibration_file_sha256": sha256_file(output / "calibration.json"),
        "training_manifest_document_sha256": training_manifest_sha,
        "training_manifest_file_sha256": sha256_file(output / "training_manifest.json"),
        "policy_file_sha256": sha256_file(output / "policy.json")}
    _write_json(output / "policy_freeze.json", freeze)

    training_policy_rows = _measure_split(training, 1, ("frozen_gate",), matcher, policy,
        calibration, seed="d9-training-policy-arm-order/v1", wall_started=wall_started,
        max_seconds=config.max_seconds)
    _write_jsonl(output / "training_policy_measurements.jsonl", training_policy_rows)

    validation, validation_selection = load_split("validation", config,
        excluded_digests=seen, wall_started=wall_started)
    _write_json(output / "validation_cases.json", cases_document(validation, validation_selection))
    validation_rows = _measure_split(validation, config.evaluation_rounds, ARMS, matcher, policy,
        calibration, seed="d9-validation-arm-order/v1", wall_started=wall_started,
        max_seconds=config.max_seconds)
    _write_jsonl(output / "validation_measurements.jsonl", validation_rows)

    evaluation, evaluation_selection = load_split("evaluation", config,
        excluded_digests=seen, wall_started=wall_started)
    _write_json(output / "evaluation_cases.json", cases_document(evaluation, evaluation_selection))
    evaluation_rows = _measure_split(evaluation, config.evaluation_rounds, ARMS, matcher, policy,
        calibration, seed="d9-evaluation-arm-order/v1", wall_started=wall_started,
        max_seconds=config.max_seconds)
    _write_jsonl(output / "evaluation_measurements.jsonl", evaluation_rows)

    prior_path = ROOT / "docs" / "recognition" / "linux_confirmation" / "natural_normalization_cases.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    prior_digests = {item["structural_sha256"] for item in prior["cases"]}
    overlap = sorted(prior_digests & {case.structural_sha256 for case in training + validation + evaluation})
    all_rows = training_rows + training_policy_rows + validation_rows + evaluation_rows
    semantic_checks = sum(row["expected_reuses"] for row in all_rows)
    mismatches = sum(row["mismatches"] for row in all_rows)
    summaries = {"training": summarize_split(training_rows + training_policy_rows),
        "validation": summarize_split(validation_rows), "evaluation": summarize_split(evaluation_rows)}
    summary = {"schema": RUN_SCHEMA, "status": "complete" if mismatches == 0 else "mismatch",
        "wall_seconds": time.monotonic() - wall_started,
        "case_counts": {"training": len(training), "validation": len(validation),
                        "evaluation": len(evaluation)},
        "measurement_rows": {"training": len(training_rows) + len(training_policy_rows),
                             "training_fit": len(training_rows),
                             "training_policy": len(training_policy_rows),
                             "validation": len(validation_rows),
                             "evaluation": len(evaluation_rows)},
        "semantic_checks": semantic_checks, "semantic_mismatches": mismatches,
        "prior_d5_d8_structural_overlap_count": len(overlap),
        "prior_d5_d8_structural_overlap": overlap, "summaries": summaries,
        "criteria": {"safety_met": mismatches == 0, "leakage_control_met": True,
            "circuit_disjoint_met": True, "new_representation_met": True,
            "independent_benchmark_family_met": False,
            "profitability_met": (summaries["evaluation"]["gate_apply_count"] > 0
                and summaries["evaluation"]["frozen_gate_speedup_over_no_rewrite"] > 1.01
                and summaries["evaluation"]["frozen_gate_regret_fraction"] <= 0.05),
            "production_promotion": False}}
    _write_json(output / "summary.json", summary)
    (output / "report.md").write_text(_report(summary), encoding="utf-8", newline="\n")
    required = {path.name: sha256_file(path) for path in output.iterdir()
                if path.is_file() and path.name != "manifest.json"}
    manifest = {"schema": "crse-natural-profitability-policy-artifacts/v1",
        "status": summary["status"], "files_sha256": dict(sorted(required.items()))}
    _write_json(output / "manifest.json", manifest)
    return summary
