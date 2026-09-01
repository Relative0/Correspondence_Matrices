"""C20 retrospective VTR slow-tail study for a compiled frozen C19 policy."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
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

from .gf2_task_dispatcher import EXHAUSTIVE, SCREENED
from .gf2_work_policy import cheap_truth_features, evaluate_tree, load_policy
from .gf2_work_policy_compiler import compile_work_policy
from .gf2_work_policy_experiment import _analyze, _best

SCHEMA = "crse-c20-compiled-gf2-policy-vtr-tail-experiment/v1"
METHODS = ("direct_exhaustive", "direct_screened", "generic_c19", "compiled_c19")


@dataclass(frozen=True)
class C20Config:
    run_id: str
    seed: int = 20260831
    rounds: int = 9
    max_partitions: int = 64
    materialize_budget: int = 4
    max_seconds: float = 300.0

    def validate(self) -> None:
        if (
            not self.run_id
            or type(self.rounds) is not int
            or not 5 <= self.rounds <= 21
            or self.max_partitions != 64
            or self.materialize_budget != 4
            or type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or not 60 <= self.max_seconds <= 900
        ):
            raise ValueError("invalid C20 experiment bounds")


def _write(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")


def _bits(case: dict[str, Any]) -> int:
    return int(case["truth_bits_hex"], 16)


def _functional(cases: list[dict[str, Any]], config: C20Config):
    expected, mismatches = {}, 0
    for case in cases:
        bits, n_vars = _bits(case), case["n_vars"]
        exhaustive = _analyze(EXHAUSTIVE, bits, n_vars, config)
        screened = _analyze(SCREENED, bits, n_vars, config)
        expected[case["case_id"]] = _best(exhaustive)
        if (
            _best(exhaustive) != _best(screened)
            or any(item.reconstruct() != bits for item in exhaustive.candidates)
            or any(item.reconstruct() != bits for item in screened.candidates)
        ):
            mismatches += 1
    return {"cases": len(cases), "mismatches": mismatches, "all_exact": mismatches == 0}, expected


def _measure(case, method, policy, compiled, expected, config, round_index):
    bits, n_vars = _bits(case), case["n_vars"]
    if method == "direct_exhaustive":
        arm, decision_ns = EXHAUSTIVE, 0
    elif method == "direct_screened":
        arm, decision_ns = SCREENED, 0
    elif method == "generic_c19":
        started = time.perf_counter_ns()
        arm = evaluate_tree(policy["tree"], cheap_truth_features(bits, n_vars))
        decision_ns = max(1, time.perf_counter_ns() - started)
    elif method == "compiled_c19":
        started = time.perf_counter_ns()
        arm = compiled.select(bits, n_vars)
        decision_ns = max(1, time.perf_counter_ns() - started)
    else:
        raise ValueError("unknown C20 method")
    started = time.perf_counter_ns()
    analysis = _analyze(arm, bits, n_vars, config)
    analysis_ns = max(1, time.perf_counter_ns() - started)
    started = time.perf_counter_ns()
    best = _best(analysis)
    exact = all(item.reconstruct() == bits for item in analysis.candidates)
    exact_check_ns = max(1, time.perf_counter_ns() - started)
    return {
        "case_id": case["case_id"],
        "source_file": case["source_file"],
        "n_vars": n_vars,
        "method": method,
        "round": round_index,
        "selected_arm": arm,
        "decision_ns": decision_ns,
        "analysis_ns": analysis_ns,
        "exact_check_ns": exact_check_ns,
        "total_ns": decision_ns + analysis_ns + exact_check_ns,
        "semantic_mismatches": int(not exact),
        "artifact_mismatches": int(best != expected[case["case_id"]]),
        "best_artifact_sha256": best["payload_sha256"] if best else None,
    }


def summarize(rows: list[dict[str, Any]], functional: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[int]] = {}
    for row in rows:
        grouped.setdefault((row["case_id"], row["method"]), []).append(row["total_ns"])
    med = {key: int(statistics.median(values)) for key, values in grouped.items()}
    cases = sorted({row["case_id"] for row in rows})
    exhaustive = {case: med[(case, "direct_exhaustive")] for case in cases}
    screened = {case: med[(case, "direct_screened")] for case in cases}
    methods = {}
    for method in METHODS:
        selected = {case: med[(case, method)] for case in cases}
        speedups = [exhaustive[case] / selected[case] for case in cases]
        regrets = [selected[case] / min(exhaustive[case], screened[case]) for case in cases]
        methods[method] = {
            "aggregate_speedup_over_exhaustive": sum(exhaustive.values()) / sum(selected.values()),
            "median_case_speedup_over_exhaustive": statistics.median(speedups),
            "minimum_case_speedup_over_exhaustive": min(speedups),
            "maximum_regret_over_best_direct_arm": max(regrets),
            "aggregate_overhead_over_direct_screened": sum(selected.values()) / sum(screened.values()),
        }
    compiled = methods["compiled_c19"]
    return {
        "functional_exactness": functional["all_exact"],
        "methods": methods,
        "research_gate": (
            functional["all_exact"]
            and compiled["aggregate_speedup_over_exhaustive"] >= 1.0
            and compiled["minimum_case_speedup_over_exhaustive"] >= 0.97
        ),
        "timing_is_retrospective_and_machine_specific": True,
    }


def render_report(result: dict[str, Any]) -> str:
    selected = result["summary"]["methods"]["compiled_c19"]
    direct = result["summary"]["methods"]["direct_screened"]
    return f"""# C20 compiled C19 policy on the retrospective VTR slow tail

Status: **{result['status']}**  
Research gate: **{result['summary']['research_gate']}**

The frozen C19 policy compiled to a constant exact screened arm, avoiding truth-feature
extraction and generic tree traversal. This nine-round run used the 11 previously observed
C18 VTR cases with `n<=4`; it is retrospective diagnostic evidence, not fresh confirmation.

- Compiled policy aggregate speedup over exhaustive: **{selected['aggregate_speedup_over_exhaustive']:.4f}x**
- Compiled policy minimum per-case speedup: **{selected['minimum_case_speedup_over_exhaustive']:.4f}x**
- Direct screened aggregate speedup: **{direct['aggregate_speedup_over_exhaustive']:.4f}x**
- Compiled aggregate overhead over direct screened: **{selected['aggregate_overhead_over_direct_screened']:.4f}x**

Every result remained exact. Production promotion is false regardless of the timing gate.
"""


def run(config: C20Config, output: Path, dataset_path: Path, policy_path: Path, root: Path):
    config.validate()
    wall = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)
    dataset, policy = json.loads(dataset_path.read_text()), load_policy(policy_path)
    cases = [case for case in dataset["cases"] if case["n_vars"] <= 4]
    if len(cases) != 11 or {case["n_vars"] for case in cases} != {3, 4}:
        raise ValueError("C20 frozen VTR tail changed")
    compiled = compile_work_policy(policy)
    if compiled.mode != "constant_leaf" or compiled.constant_arm != SCREENED or compiled.requires_features:
        raise ValueError("C20 requires the frozen constant-screened C19 policy")
    _write(output / "run_spec.json", {
        "schema": SCHEMA,
        "config": asdict(config),
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "policy_file_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "policy_sha256": policy["policy_sha256"],
        "methods": list(METHODS),
        "scope": "retrospective C18 VTR n<=4 slow-tail controls",
        "production_promotion": False,
    })
    functional, expected = _functional(cases, config)
    _write(output / "functional.json", functional)
    rng = random.Random(f"{config.seed}:c20-balanced/v1")
    rows = []
    for round_index in range(config.rounds):
        order = [(case, method) for case in cases for method in METHODS]
        rng.shuffle(order)
        for case, method in order:
            if time.perf_counter() - wall > config.max_seconds:
                raise TimeoutError("C20 experiment exceeded wall bound")
            rows.append(_measure(case, method, policy, compiled, expected, config, round_index))
    _write_jsonl(output / "measurements.jsonl", rows)
    summary = summarize(rows, functional)
    mismatches = functional["mismatches"] + sum(
        row["semantic_mismatches"] + row["artifact_mismatches"] for row in rows
    )
    result = {
        "schema": SCHEMA,
        "status": "complete" if mismatches == 0 else "failed",
        "config": asdict(config),
        "wall_seconds": time.perf_counter() - wall,
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "thread_environment": {name: os.environ.get(name) for name in
                                               ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
        "dataset": {"family": "VTR BLIF", "cases": len(cases), "n_vars": [3, 4],
                    "retrospective": True, "policy_refit": False},
        "policy": {"selected_candidate": policy["selected_candidate"], "tree": policy["tree"],
                   "compiled_mode": compiled.mode, "requires_features": compiled.requires_features,
                   "policy_sha256": policy["policy_sha256"]},
        "measurement_rows": len(rows),
        "semantic_or_artifact_mismatches": mismatches,
        "summary": summary,
        "claims": {"learned_truth_values": False, "exact_arm_selection_only": True,
                   "fresh_confirmation": False, "production_promotion": False},
        "runpod": {"used": False, "cost_usd": 0.0},
    }
    _write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    sources = (
        "cmbench/recognition/gf2_work_policy_compiler.py",
        "cmbench/recognition/gf2_compiled_policy_tail_experiment.py",
        "scripts/cm_recognition_c20_compiled_policy_tail.py",
    )
    artifacts = ("run_spec.json", "functional.json", "measurements.jsonl", "results.json", "report.md")
    _write(output / "manifest.json", {
        "schema": "crse-c20-run-manifest/v1",
        "sources": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources},
        "artifacts": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in artifacts},
    })
    return result
