"""Frozen Windows D10 workload for indexed proved motifs and no-op bypass."""
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

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Expr, Not, Or, Var, Xor

from .d10_rule_engine import (
    CANCEL_RULE, CARRY_RULE, COMPARATOR_RULE, MUX_RULE, RULE_PRIORITY,
    CompiledD10RulePack, D10ConeCache, compile_d10_rule_pack, prove_d10_rule_pack,
)
from .features import structural_digest
from .portfolio import prepare, reference_bits
from .proved_rules import canonical
from .teacher import teach
from .yosys_composed_holdout_data import make_yosys_composed_holdout

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "crse-d10-rule-engine-experiment/v1"
ARMS = ("no_rewrite", "indexed", "full_scan", "instance_cm_proof", "cached")
REUSES = (1, 8, 32, 128)


@dataclass(frozen=True)
class D10Config:
    run_id: str = "d10-rule-engine-windows-20260830-001"
    seed: int = 20260830
    rounds: int = 7
    max_seconds: float = 300.0

    def validate(self) -> None:
        if (type(self.run_id) is not str or not self.run_id or type(self.seed) is not int
                or type(self.rounds) is not int or not 3 <= self.rounds <= 15
                or not 30 <= self.max_seconds <= 900):
            raise ValueError("invalid D10 experiment config")


@dataclass(frozen=True)
class D10Case:
    case_id: str
    split: str
    kind: str
    motif_family: str
    n_vars: int
    expected_reuses: int
    expression: Expr
    source_case_id: str


def _wrap(rule_id: str, base: Expr) -> Expr:
    a, b, c, d = Var(0), Var(1), Var(2), Var(3)
    if rule_id == MUX_RULE:
        return Or(And(a, base), And(Not(a), b))
    if rule_id == COMPARATOR_RULE:
        return Or(And(base, And(a, Not(b))), And(base, And(c, Not(d))))
    if rule_id == CARRY_RULE:
        return Or(Or(And(base, a), And(base, b)), And(a, b))
    if rule_id == CANCEL_RULE:
        return Xor(Xor(base, a), Xor(base, b))
    raise ValueError("unknown D10 wrapper")


def make_d10_cases() -> tuple[list[D10Case], dict[str, Any]]:
    rows, provenance = make_yosys_composed_holdout()
    bases = [row for row in rows if row["source_kind"] == "unused_raw_generator_output"
             and row["n_vars"] <= 8]
    bases.sort(key=lambda row: row["selection_sha256"])
    if len(bases) < 16:
        raise ValueError("insufficient bounded independently sourced Yosys bases")
    positive_bases = bases[:16]
    matcher = compile_d10_rule_pack(prove_d10_rule_pack())
    no_op_bases = [row for row in bases if matcher.rewrite(
        expr_from_json(row["expression_v2"]), row["n_vars"]).applications == 0]
    if len(no_op_bases) < 12:
        raise ValueError("insufficient verified rule-free Yosys controls")
    cases = []
    for index, row in enumerate(positive_bases):
        expression = expr_from_json(row["expression_v2"])
        reuse = REUSES[index % len(REUSES)]
        rule_id = RULE_PRIORITY[index // 4]
        cases.append(D10Case(f"d10-motif-{index:02d}", row["split"], "motif",
                             rule_id, max(row["n_vars"], 5), reuse,
                             _wrap(rule_id, expression), row["case_id"]))
    for index, row in enumerate(no_op_bases):
        expression = expr_from_json(row["expression_v2"])
        cases.append(D10Case(f"d10-noop-{index:02d}", row["split"], "no_op",
                             "verified_rule_free_yosys_control", row["n_vars"],
                             REUSES[index % len(REUSES)], expression, row["case_id"]))
    cases.sort(key=lambda item: item.case_id)
    return cases, {
        "schema": "crse-d10-dataset-provenance/v1",
        "rows": len(cases), "motif_rows": 16, "no_op_rows": len(no_op_bases),
        "base_source": provenance,
        "scope": ("Motifs are deliberately inserted around independently authored Yosys-bench "
                  "generator expressions; this is source-backed composition, not a claim of "
                  "naturally occurring motif frequency."),
        "selection_uses_timing": False, "network_access_performed": False,
    }


def _case_document(case: D10Case) -> dict[str, Any]:
    return {"case_id": case.case_id, "split": case.split, "kind": case.kind,
            "motif_family": case.motif_family, "n_vars": case.n_vars,
            "expected_reuses": case.expected_reuses, "source_case_id": case.source_case_id,
            "structural_sha256": structural_digest(case.expression),
            "semantic_sha256": _bits_digest(reference_bits(case.expression, case.n_vars), case.n_vars),
            "expression_v2": expr_to_json_dag(case.expression)}


def _bits_digest(bits: int, n_vars: int) -> str:
    return hashlib.sha256(bits.to_bytes((1 << n_vars) // 8 or 1, "little")).hexdigest()


def _measure(case: D10Case, arm: str, round_index: int, matcher: CompiledD10RulePack,
             cache: D10ConeCache, expected: int) -> dict[str, Any]:
    proof_calls = proof_ns = rewrite_ns = cache_identity_ns = cache_rewrite_ns = 0
    applications = proposals = screen_sites = 0
    bypassed = cache_hit = False
    rewritten = case.expression

    def cm_proof(_rule_id: str, source: Expr, candidate: Expr) -> bool:
        nonlocal proof_calls, proof_ns
        started = time.perf_counter_ns()
        proof_calls += 1
        accepted = teach(source, case.n_vars).bits == teach(candidate, case.n_vars).bits
        proof_ns += max(1, time.perf_counter_ns() - started)
        return accepted

    started_total = time.perf_counter_ns()
    if arm in {"indexed", "full_scan", "instance_cm_proof"}:
        started = time.perf_counter_ns()
        rewrite = matcher.rewrite(case.expression, case.n_vars,
            index_mode="full_scan" if arm == "full_scan" else "indexed",
            verify=cm_proof if arm == "instance_cm_proof" else None)
        rewrite_ns = max(1, time.perf_counter_ns() - started)
        rewritten = rewrite.result
        applications, proposals = rewrite.applications, rewrite.proposals
        screen_sites, bypassed = rewrite.screen_candidate_sites, rewrite.bypassed
    elif arm == "cached":
        result = cache.rewrite(case.case_id, case.expression, matcher, case.n_vars)
        rewritten, cache_hit = result.result, result.cache_hit
        cache_identity_ns, cache_rewrite_ns = result.identity_ns, result.rewrite_ns
        rewrite = result.rewrite
        applications, proposals = rewrite.applications, rewrite.proposals
        screen_sites, bypassed = rewrite.screen_candidate_sites, rewrite.bypassed
    elif arm != "no_rewrite":
        raise ValueError("unknown D10 arm")
    build_started = time.perf_counter_ns()
    run = prepare("cse", rewritten, case.n_vars)
    build_ns = max(1, time.perf_counter_ns() - build_started)
    kernel_started = time.perf_counter_ns()
    values = [run() for _ in range(case.expected_reuses)]
    kernel_ns = max(1, time.perf_counter_ns() - kernel_started)
    total_ns = max(1, time.perf_counter_ns() - started_total)
    mismatches = sum(value != expected for value in values)
    return {"schema": "crse-d10-measurement/v1", "case_id": case.case_id,
            "split": case.split, "kind": case.kind, "motif_family": case.motif_family,
            "n_vars": case.n_vars, "expected_reuses": case.expected_reuses,
            "arm": arm, "round": round_index, "status": "ok" if not mismatches else "mismatch",
            "mismatches": mismatches, "total_ns": total_ns, "rewrite_ns": rewrite_ns,
            "cache_identity_ns": cache_identity_ns, "cache_rewrite_ns": cache_rewrite_ns,
            "cse_build_ns": build_ns, "cse_kernel_ns": kernel_ns,
            "proof_calls": proof_calls, "proof_ns": proof_ns, "applications": applications,
            "proposals": proposals, "screen_candidate_sites": screen_sites,
            "bypassed": bypassed, "cache_hit": cache_hit,
            "result_sha256": structural_digest(rewritten),
            "output_sha256": _bits_digest(values[0], case.n_vars)}


def _median_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in rows:
        grouped[(row["case_id"], row["arm"])].append(row["total_ns"])
    return {key: statistics.median(values) for key, values in grouped.items()}


def summarize(rows: list[dict[str, Any]], cases: list[D10Case]) -> dict[str, Any]:
    medians = _median_rows(rows)
    case_by_id = {case.case_id: case for case in cases}

    def subset(predicate) -> dict[str, Any]:
        selected = [case for case in cases if predicate(case)]
        totals = {arm: sum(medians[(case.case_id, arm)] for case in selected) for arm in ARMS}
        return {"cases": len(selected), "median_case_sum_ns": {key: int(value) for key, value in totals.items()},
                "speedup_over_no_rewrite": {arm: totals["no_rewrite"] / totals[arm]
                                             for arm in ARMS if arm != "no_rewrite"}}

    all_rows = subset(lambda case: True)
    positive = subset(lambda case: case.kind == "motif")
    noop = subset(lambda case: case.kind == "no_op")
    high = subset(lambda case: case.kind == "motif" and case.expected_reuses >= 32)
    oracle = sum(min(medians[(case.case_id, "no_rewrite")],
                     medians[(case.case_id, "indexed")]) for case in cases)
    no_total = sum(medians[(case.case_id, "no_rewrite")] for case in cases)
    by_reuse = {}
    for reuse in REUSES:
        by_reuse[str(reuse)] = subset(lambda case, value=reuse:
                                      case.kind == "motif" and case.expected_reuses == value)
    false_matches = sum(row["applications"] for row in rows
                        if row["kind"] == "no_op" and row["arm"] == "indexed")
    proof_calls = sum(row["proof_calls"] for row in rows if row["arm"] == "instance_cm_proof")
    criteria = {
        "exact_outputs": all(row["mismatches"] == 0 for row in rows),
        "no_op_false_matches_zero": false_matches == 0,
        "indexed_noop_overhead_at_most_3_percent":
            noop["speedup_over_no_rewrite"]["indexed"] >= 1 / 1.03,
        "high_reuse_motif_speedup_at_least_1_03":
            high["speedup_over_no_rewrite"]["indexed"] >= 1.03,
        "optimistic_oracle_headroom_at_least_1_05": no_total / oracle >= 1.05,
    }
    return {"all": all_rows, "motif": positive, "no_op": noop,
            "high_reuse_motif": high, "by_reuse": by_reuse,
            "optimistic_free_oracle": {"no_rewrite_ns": int(no_total), "oracle_ns": int(oracle),
                                       "speedup": no_total / oracle},
            "false_matches": false_matches, "instance_cm_proof_calls": proof_calls,
            "criteria": criteria, "local_promotion_gate": all(criteria.values()),
            "case_metadata_sha256": hashlib.sha256(canonical([
                (case_id, case_by_id[case_id].motif_family) for case_id in sorted(case_by_id)])).hexdigest(),
            "timing_is_machine_specific": True}


def _cache_version_probe(cases: list[D10Case], matcher: CompiledD10RulePack,
                         output: Path) -> dict[str, Any]:
    chosen = cases[:8]
    cache = D10ConeCache(16)
    v1 = [cache.rewrite(case.case_id, case.expression, matcher, case.n_vars) for case in chosen]
    v1_warm = [cache.rewrite(case.case_id, case.expression, matcher, case.n_vars) for case in chosen]
    modified = list(chosen)
    modified[1] = D10Case(chosen[1].case_id, chosen[1].split, "motif", MUX_RULE, 5, 32,
                          _wrap(MUX_RULE, Var(4)), "probe-modified")
    modified = modified[1:]  # remove the first cone
    modified.append(D10Case("probe-added", "sealed_b", "motif", CANCEL_RULE, 5, 32,
                            _wrap(CANCEL_RULE, Var(4)), "probe-added"))
    v2 = [cache.rewrite(case.case_id, case.expression, matcher, case.n_vars) for case in modified]
    removed = cache.invalidate_missing({case.case_id for case in modified})
    reverted = list(modified)
    reverted[0] = chosen[1]
    v3 = [cache.rewrite(case.case_id, case.expression, matcher, case.n_vars) for case in reverted]
    path = output / "changed_cone_cache.json"
    cache.save(path)
    loaded = D10ConeCache.load(path, matcher)
    replay = [loaded.rewrite(case.case_id, case.expression, matcher, case.n_vars) for case in reverted]
    return {"schema": "crse-d10-cache-version-probe/v1",
            "v1_cold_misses": sum(not row.cache_hit for row in v1),
            "v1_warm_hits": sum(row.cache_hit for row in v1_warm),
            "v2_hits": sum(row.cache_hit for row in v2),
            "v2_source_invalidations": sum(row.invalidated for row in v2),
            "v2_removed_invalidations": removed,
            "v3_revert_invalidations": sum(row.invalidated for row in v3),
            "serialized_reload_hits": sum(row.cache_hit for row in replay),
            "artifact": path.name,
            "exact": all(reference_bits(case.expression, case.n_vars)
                         == reference_bits(row.result, case.n_vars)
                         for case, row in zip(reverted, replay))}


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = ["# CRSE D10 indexed proved-rule engine", "",
             f"Status: **{result['status']}**", f"Exact mismatches: {result['semantic_mismatches']}",
             f"Local promotion gate: **{summary['local_promotion_gate']}**", "",
             "## Workload", "",
             "Four motif rules were proved once over metavariables (56 exhaustive rows total). "
             "The 16 positive expressions insert those motifs around independently authored "
             f"Yosys-bench cones; {result['dataset']['no_op_rows']} matcher-audited raw Yosys cones are no-op controls. This measures source-backed "
             "composition and does not estimate natural motif frequency.", "",
             "| Slice | Cases | Indexed speedup vs no rewrite | Full scan | Per-instance CM | Cached |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name in ("all", "motif", "no_op", "high_reuse_motif"):
        row = summary[name]
        speed = row["speedup_over_no_rewrite"]
        lines.append(f"| {name} | {row['cases']} | {speed['indexed']:.4f} | {speed['full_scan']:.4f} | "
                     f"{speed['instance_cm_proof']:.4f} | {speed['cached']:.4f} |")
    lines += ["", f"Optimistic per-case oracle headroom: **{summary['optimistic_free_oracle']['speedup']:.4f}x**.",
              f"Explicit per-instance CM proofs performed: {summary['instance_cm_proof_calls']}.", "",
              "## Gate", ""]
    lines.extend(f"- `{key}`: **{value}**" for key, value in summary["criteria"].items())
    lines += ["", "The indexed arm charges eligibility screening, matching, CSE construction, and all "
              "declared repeated evaluations. The CM arm additionally constructs and compares explicit "
              "correspondence matrices at every proposed site. Advice is never trusted for semantics.", "",
              "No second-machine run is justified unless this Windows gate is positive.", ""]
    return "\n".join(lines)


def run_d10_experiment(config: D10Config, output: Path, progress=print) -> dict[str, Any]:
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    wall_started = time.perf_counter()
    _write_json(output / "run_spec.json", {"schema": SCHEMA, "config": asdict(config),
        "output": str(output), "controls": {"thread_count": 1, "runpod": False}})
    progress("Proving and compiling four D10 motif rules")
    proof_started = time.perf_counter_ns()
    pack = prove_d10_rule_pack()
    proof_ns = max(1, time.perf_counter_ns() - proof_started)
    pack.save(output / "proved_motif_pack.json")
    compile_started = time.perf_counter_ns()
    matcher = compile_d10_rule_pack(pack)
    compile_ns = max(1, time.perf_counter_ns() - compile_started)
    cases, provenance = make_d10_cases()
    _write_json(output / "dataset.json", {"schema": "crse-d10-dataset/v1",
                "provenance": provenance, "cases": [_case_document(case) for case in cases]})
    expected = {case.case_id: reference_bits(case.expression, case.n_vars) for case in cases}
    cache = D10ConeCache(len(cases) + 4)
    for case in cases:
        cache.rewrite(case.case_id, case.expression, matcher, case.n_vars)
    rows = []
    rng = random.Random(f"{config.seed}:d10-balanced-order/v1")
    progress("Measuring no rewrite, indexed, full scan, per-instance CM, and warm cache")
    for round_index in range(config.rounds):
        order = [(case, arm) for case in cases for arm in ARMS]
        rng.shuffle(order)
        for case, arm in order:
            if time.perf_counter() - wall_started > config.max_seconds:
                raise TimeoutError("D10 experiment exceeded wall budget")
            rows.append(_measure(case, arm, round_index, matcher, cache, expected[case.case_id]))
    _write_jsonl(output / "measurements.jsonl", rows)
    version_probe = _cache_version_probe(cases, matcher, output)
    _write_json(output / "cache_version_probe.json", version_probe)
    summary = summarize(rows, cases)
    semantic_mismatches = sum(row["mismatches"] for row in rows)
    result = {"schema": SCHEMA, "status": "complete" if semantic_mismatches == 0 else "failed",
              "config": asdict(config), "wall_seconds": time.perf_counter() - wall_started,
              "environment": {"python": sys.version, "platform": platform.platform(),
                              "thread_environment": {name: os.environ.get(name) for name in
                               ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
              "proof": {"pack_sha256": pack.digest, "rule_ids": list(RULE_PRIORITY),
                        "proof_rows": 56, "proof_ns": proof_ns, "compile_ns": compile_ns,
                        "artifact_is_inert": True},
              "dataset": provenance, "semantic_mismatches": semantic_mismatches,
              "cache_version_probe": version_probe, "summary": summary,
              "runpod": {"used": False, "cost_usd": 0.0,
                         "reason": "pending_local_gate" if summary["local_promotion_gate"] else
                                   "local_promotion_gate_failed"},
              "claims": {"exact_bounded_rewrites": semantic_mismatches == 0,
                         "natural_frequency": False, "production_promotion": False}}
    _write_json(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    return result
