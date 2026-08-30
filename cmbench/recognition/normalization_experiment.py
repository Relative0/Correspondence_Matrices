"""Milestone D7: bounded multi-pass normalization on sealed natural cones."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import statistics
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from bitset_backend import _eval_words, build_bitset_env, compile_expr_cse, eval_expr_bitset

from .computation_experiment import sha256_file
from .features import structural_digest
from .natural_rule_experiment import NaturalRuleConfig, cases_document, load_natural_cases
from .normalization import normalize_to_fixpoint
from .rule_pack import (
    RULE_PRIORITY_V2, CompiledRulePack, ProvedRulePack, compile_rule_pack, prove_rule_pack_v2,
)


ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA = "crse-natural-normalization-experiment/v1"
ARMS = ("no_rewrite", "one_pass", "fixpoint")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True,
                                allow_nan=False).encode("utf-8") + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


def packed_sha(value: int, n_vars: int) -> str:
    return hashlib.sha256(value.to_bytes(1 << max(0, n_vars - 3), "little")).hexdigest()


@dataclass(frozen=True)
class NormalizationConfig:
    case_count: int = 32
    rounds: int = 3
    kernel_repeats: int = 128
    max_passes: int = 8
    max_seconds: float = 120.0

    def validate(self) -> None:
        if type(self.case_count) is not int or not 8 <= self.case_count <= 32:
            raise ValueError("case count must be in [8,32]")
        if type(self.rounds) is not int or not 1 <= self.rounds <= 3:
            raise ValueError("rounds must be in [1,3]")
        if self.kernel_repeats != 128:
            raise ValueError("the frozen high-reuse policy requires exactly 128 executions")
        if type(self.max_passes) is not int or not 1 <= self.max_passes <= 8:
            raise ValueError("max passes must be in [1,8]")
        if type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 120:
            raise ValueError("wall budget must be in (0,120]")

    def run_spec(self, output: Path) -> dict[str, Any]:
        self.validate()
        return {"schema": "crse-natural-normalization-run-spec/v1", "status": "planned",
            "config": asdict(self), "arms": list(ARMS), "rules": list(RULE_PRIORITY_V2),
            "timing_contract": "normalization-plus-flattened-cse-build-plus-128-packed-executions/v1",
            "termination_contract": "strict-expanded-ast-operator-decrease-plus-exact-cycle-detection-plus-final-no-op-pass/v1",
            "overlap_contract": "only the fixed pack's declared deterministic priority; refuse mode tested separately/v1",
            "audit_contract": "original-expression packed exact evaluation outside every timed arm/v1",
            "resource_limits": {"max_cases": 32, "max_rounds": 3, "max_variables": 12,
                "kernel_repeats": 128, "max_passes": 8, "max_total_applications_per_case": 1024,
                "cpu_threads": 1, "cooperative_wall_seconds": float(self.max_seconds), "network": False},
            "output": str(output.resolve()),
            "scientific_scope": "exploratory reuse of the D5 EPFL slice to test multi-pass mechanics; not independent confirmation or production promotion"}


def load_cases(config: NormalizationConfig):
    config.validate()
    natural_config = NaturalRuleConfig(case_count=config.case_count, rounds=1)
    cases, selection = load_natural_cases(natural_config)
    return cases, selection, cases_document(cases, selection)


def _measure_arm(cases, arm: str, round_index: int, matcher: CompiledRulePack,
                 repeats: int, max_passes: int, expected: dict[str, int]) -> dict[str, Any]:
    normalization_ns = cse_build_ns = kernel_ns = 0
    mismatches = 0
    details = []
    wall_started = time.perf_counter_ns()
    for case in cases:
        applications = proposals = conflicts = productive_passes = convergence_passes = 0
        by_rule = {rule_id: 0 for rule_id in RULE_PRIORITY_V2}
        if arm == "no_rewrite":
            result = case.expr
        elif arm == "one_pass":
            started = time.perf_counter_ns()
            rewrite = matcher.rewrite(case.expr, case.n_vars)
            normalization_ns += max(1, time.perf_counter_ns() - started)
            result = rewrite.result
            applications, proposals, conflicts = rewrite.applications, rewrite.proposals, rewrite.conflicts
            productive_passes = int(rewrite.applications > 0)
            convergence_passes = 1
            by_rule = dict(rewrite.applications_by_rule)
        elif arm == "fixpoint":
            started = time.perf_counter_ns()
            normalized = normalize_to_fixpoint(matcher, case.expr, case.n_vars,
                                                max_passes=max_passes)
            normalization_ns += max(1, time.perf_counter_ns() - started)
            result = normalized.result
            applications, proposals, conflicts = (normalized.total_applications,
                normalized.total_proposals, normalized.total_conflicts)
            productive_passes = normalized.productive_passes
            convergence_passes = normalized.convergence_passes
            by_rule = dict(normalized.applications_by_rule)
        else:
            raise ValueError("invalid normalization arm")
        variables = tuple(f"x{i}" for i in range(case.n_vars))
        started = time.perf_counter_ns()
        program = compile_expr_cse(result, flatten=True)
        cse_build_ns += max(1, time.perf_counter_ns() - started)
        started = time.perf_counter_ns()
        value = 0
        for _ in range(repeats):
            value = _eval_words(program, variables, {})
        kernel_ns += max(1, time.perf_counter_ns() - started)
        digest = packed_sha(value, case.n_vars)
        mismatches += int(value != expected[case.cone_id])
        details.append({"case_id": case.cone_id, "n_vars": case.n_vars,
            "source_sha256": structural_digest(case.expr),
            "result_sha256": structural_digest(result), "value_sha256": digest,
            "applications": applications, "proposals": proposals, "conflicts": conflicts,
            "productive_passes": productive_passes, "convergence_passes": convergence_passes,
            "applications_by_rule": by_rule})
    total_ns = normalization_ns + cse_build_ns + kernel_ns
    return {"schema": "crse-natural-normalization-measurement/v1",
        "status": "ok" if not mismatches else "mismatch", "round": round_index,
        "arm": arm, "case_count": len(cases), "kernel_repeats": repeats,
        "normalization_ns": normalization_ns, "cse_build_ns": cse_build_ns,
        "kernel_ns": kernel_ns, "total_ns": total_ns,
        "wall_ns": max(1, time.perf_counter_ns() - wall_started),
        "mismatches": mismatches, "cases": details}


def summarize(rows: list[dict[str, Any]], rounds: int) -> dict[str, Any]:
    medians = {arm: {metric: int(statistics.median(row[metric] for row in rows if row["arm"] == arm))
                     for metric in ("normalization_ns", "cse_build_ns", "kernel_ns", "total_ns")}
               for arm in ARMS if sum(row["arm"] == arm for row in rows) == rounds}
    if len(medians) != len(ARMS):
        return {}
    incidence = {}
    pass_distribution = {}
    for arm in ("one_pass", "fixpoint"):
        sample = next(row for row in rows if row["arm"] == arm and row["round"] == 0)
        counts = Counter()
        passes = Counter()
        conflicts = 0
        for case in sample["cases"]:
            counts.update(case["applications_by_rule"])
            passes[case["productive_passes"]] += 1
            conflicts += case["conflicts"]
        incidence[arm] = {"applications_by_rule": {rule_id: counts[rule_id]
            for rule_id in RULE_PRIORITY_V2}, "total_conflicts": conflicts}
        pass_distribution[arm] = {str(key): value for key, value in sorted(passes.items())}
    baseline = medians["no_rewrite"]["total_ns"]
    return {"median_ns": medians,
        "one_pass_speedup_over_no_rewrite": baseline / medians["one_pass"]["total_ns"],
        "fixpoint_speedup_over_no_rewrite": baseline / medians["fixpoint"]["total_ns"],
        "fixpoint_speedup_over_one_pass": medians["one_pass"]["total_ns"] / medians["fixpoint"]["total_ns"],
        "incidence": incidence, "productive_pass_distribution": pass_distribution,
        "timing_is_machine_specific": True}


def source_fingerprints() -> dict[str, str]:
    from .natural_rule_experiment import EPFL_CORPUS, EPFL_PROVENANCE
    paths = [Path(__file__), ROOT / "cmbench" / "recognition" / "normalization.py",
        ROOT / "cmbench" / "recognition" / "rule_pack.py",
        ROOT / "cmbench" / "recognition" / "natural_rule_experiment.py",
        ROOT / "scripts" / "cm_recognition_normalization.py",
        ROOT / "scripts" / "crse_normalization_verify.py", EPFL_CORPUS, EPFL_PROVENANCE]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path) for path in paths}


def render_report(result: dict[str, Any]) -> str:
    summary = result.get("summaries", {})
    lines = ["# CRSE Milestone D7: bounded multi-pass normalization", "",
        f"Status: **{result['status']}**", f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Exact output mismatches: {result['semantic_mismatches']}", "",
        "## Contract", "",
        "The three-rule proved pack is applied to the sealed D5 EPFL cones with a frozen 128-execution workload. One pass, bounded fixpoint normalization, and no rewrite all pay flattened CSE construction and packed execution. Fixpoint timing includes its final no-op convergence pass.", "",
        "Every productive pass must strictly decrease expanded AST operator occurrences. Exact repeated-state detection, an eight-pass cap, a 1,024-application cap, and a tested overlap-refusal mode prevent partial or cyclic promotion.", ""]
    if not summary:
        lines += [f"No complete timing summary is available. Error type: `{result['error_type']}`.", ""]
        return "\n".join(lines)
    base = summary["median_ns"]["no_rewrite"]["total_ns"]
    lines += ["## Results", "", "| Arm | Median charged time | Speed versus no rewrite |",
        "| --- | ---: | ---: |"]
    for arm in ARMS:
        total = summary["median_ns"][arm]["total_ns"]
        lines.append(f"| {arm} | {total} ns | {base / total:.3f}x |")
    factor = summary["incidence"]["fixpoint"]["applications_by_rule"]["boolean-common-factor/v1"]
    lines += ["", f"Fixpoint normalization exposed {factor} factoring applications that were unavailable to the single bottom-up pass. It was **{summary['fixpoint_speedup_over_one_pass']:.3f}x** versus one pass and **{summary['fixpoint_speedup_over_no_rewrite']:.3f}x** versus no rewrite.", "",
        "This reuses the D5 cases to test mechanics, so it is exploratory rather than an independent confirmation. Linux or a different natural source remains required before promotion.", ""]
    return "\n".join(lines)


def run_normalization_experiment(config: NormalizationConfig, output: Path,
                                 progress=print) -> dict[str, Any]:
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    wall_started = time.perf_counter()
    before = source_fingerprints()
    _write_json(output / "run_spec.json", {**config.run_spec(output), "source_sha256": before})
    rows = []
    status, error_type = "incomplete", ""
    selection = {}
    pack: ProvedRulePack | None = None
    try:
        progress("Loading the sealed natural cones and proved rule pack")
        cases, selection, case_document = load_cases(config)
        _write_json(output / "natural_cases.json", case_document)
        pack = prove_rule_pack_v2()
        pack.save(output / "proved_rule_pack.json")
        matcher = compile_rule_pack(ProvedRulePack.load(output / "proved_rule_pack.json"))
        expected = {case.cone_id: eval_expr_bitset(case.expr,
            build_bitset_env(tuple(f"x{i}" for i in range(case.n_vars)))) for case in cases}
        progress("Measuring no rewrite, one pass, and bounded fixpoint normalization")
        rng = random.Random("crse-natural-normalization-arm-order/v1")
        for round_index in range(config.rounds):
            arms = list(ARMS)
            rng.shuffle(arms)
            for arm in arms:
                if time.perf_counter() - wall_started > config.max_seconds:
                    raise TimeoutError("normalization experiment exceeded cooperative wall budget")
                rows.append(_measure_arm(cases, arm, round_index, matcher,
                                         config.kernel_repeats, config.max_passes, expected))
        if any(row["status"] != "ok" for row in rows):
            raise RuntimeError("normalization measurement failed exact audit")
        status = "complete"
    except (KeyboardInterrupt, Exception) as exc:
        status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        error_type = type(exc).__name__
        progress(f"Incomplete normalization run retained: {error_type}: {exc}")
    _write_jsonl(output / "measurements.jsonl", rows)
    summaries = summarize(rows, config.rounds) if rows else {}
    after = source_fingerprints()
    result = {"schema": RUN_SCHEMA, "status": status, "error_type": error_type,
        "config": asdict(config), "source_sha256": before, "source_unchanged": before == after,
        "environment": {"python": sys.version, "platform": platform.platform(),
            "cpu_threads_requested": 1, "thread_environment": {name: os.environ.get(name)
            for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
        "selection": selection, "pack": {"pack_id": pack.document["pack_id"] if pack else None,
            "pack_sha256": pack.digest if pack else None, "rules": list(RULE_PRIORITY_V2),
            "proof_rows": 16, "artifact_is_inert": True},
        "row_count": len(rows), "summaries": summaries,
        "semantic_mismatches": sum(row["mismatches"] for row in rows),
        "failed_rows": sum(row["status"] != "ok" for row in rows),
        "criteria": {"safety_met": status == "complete" and not any(row["mismatches"] for row in rows),
            "fixpoint_met": status == "complete" and bool(summaries)
                and summaries["incidence"]["fixpoint"]["applications_by_rule"]["boolean-common-factor/v1"] > 0,
            "independent_confirmation": False, "production_promotion": False},
        "wall_seconds": time.perf_counter() - wall_started,
        "scientific_claim": "bounded multi-pass proved-rule normalization mechanics on a reused natural EPFL slice"}
    _write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-natural-normalization-artifacts/v1",
        "status": status, "files_sha256": {path.name: sha256_file(path) for path in files},
        "source_sha256": before})
    return result
