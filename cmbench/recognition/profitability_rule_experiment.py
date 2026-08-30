"""Milestone D4: gate proved-rule work by expected reuse and harden its cache."""
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

from bitset_backend import compile_expr_cse
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

from .computation_experiment import (
    ComputationTask, Workload, prepare_task, reference_task, sha256_file,
)
from .features import postorder, structural_digest
from .proved_rules import aig_xor_expr
from .rule_pack import (
    FACTOR_RULE_ID, RULE_PRIORITY_V2, CompiledRulePack, StructuralConeCache,
    aig_or_expr, compile_rule_pack, factored_or_expr, prove_rule_pack_v2,
)

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA = "crse-rule-profitability-experiment/v1"
ARMS = ("no_rewrite", "fresh_pack", "cached_pack", "gated_cached")
VERSIONS = ("v1", "v2", "v3", "v4")
REPEAT_SCHEDULE = (1, 8, 32, 128)


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
class ProfitabilityRuleConfig:
    data_seed: int = 20260829
    cone_count: int = 32
    rounds: int = 3
    min_reuses: int = 32
    min_estimated_nodes: int = 8
    max_seconds: float = 120.0

    def validate(self) -> None:
        if type(self.data_seed) is not int or not 0 <= self.data_seed <= 2**32 - 1:
            raise ValueError("invalid data seed")
        if type(self.cone_count) is not int or not 16 <= self.cone_count <= 64:
            raise ValueError("cone count must be in [16,64]")
        if type(self.rounds) is not int or not 1 <= self.rounds <= 3:
            raise ValueError("timing rounds must be in [1,3]")
        if type(self.min_reuses) is not int or not 1 <= self.min_reuses <= 128:
            raise ValueError("invalid reuse threshold")
        if type(self.min_estimated_nodes) is not int or not 1 <= self.min_estimated_nodes <= 4096:
            raise ValueError("invalid node threshold")
        if type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 120:
            raise ValueError("wall budget must be in (0,120]")

    def run_spec(self, output: Path) -> dict[str, Any]:
        self.validate()
        return {
            "schema": "crse-rule-profitability-run-spec/v1",
            "status": "planned",
            "config": asdict(self),
            "arms": list(ARMS),
            "versions": list(VERSIONS),
            "rules": list(RULE_PRIORITY_V2),
            "repeat_schedule": list(REPEAT_SCHEDULE),
            "timing_contract": "gate-plus-identity-plus-rewrite-plus-cse-build-plus-repeated-kernel/v1",
            "gate_contract": "task/reuse/upstream-node-count-only; no expression traversal and no correctness authority/v1",
            "audit_contract": "scalar complete-vector reference outside every timed arm/v1",
            "metadata_excluded_from_timing": ["estimated_nodes", "expected_reuses", "motif_family"],
            "resource_limits": {"variables": 8, "max_cones": 64, "max_versions": 4,
                                "max_kernel_repeats": 128, "max_cache_entries": 64,
                                "cpu_threads": 1, "cooperative_wall_seconds": float(self.max_seconds),
                                "network": False},
            "output": str(output.resolve()),
            "scientific_scope": "generated profitability and adversarial cache mechanism experiment; not production promotion",
        }


@dataclass(frozen=True)
class GateDecision:
    apply_rules: bool
    reason: str
    decision_ns: int


@dataclass(frozen=True)
class DeterministicProfitabilityGate:
    min_reuses: int = 32
    min_estimated_nodes: int = 8

    def decide(self, task_kind: str, expected_reuses: int, estimated_nodes: int) -> GateDecision:
        started = time.perf_counter_ns()
        if task_kind != "complete_vector":
            apply, reason = False, "unsupported_task"
        elif type(expected_reuses) is not int or not 1 <= expected_reuses <= 128:
            raise ValueError("invalid expected reuse metadata")
        elif type(estimated_nodes) is not int or not 1 <= estimated_nodes <= 4096:
            raise ValueError("invalid upstream node metadata")
        elif expected_reuses < self.min_reuses:
            apply, reason = False, "insufficient_expected_reuse"
        elif estimated_nodes < self.min_estimated_nodes:
            apply, reason = False, "cone_too_small"
        else:
            apply, reason = True, "predeclared_reuse_and_size_gate"
        return GateDecision(apply, reason, max(1, time.perf_counter_ns() - started))


@dataclass(frozen=True)
class ProfitabilityCone:
    cone_id: str
    version_id: str
    expr: Expr
    expected_reuses: int
    estimated_nodes: int
    motif_family: str
    change_kind: str
    n_vars: int = 8


def _clone(expr: Expr) -> Expr:
    return expr_from_json(expr_to_json_dag(expr))


def _tag(index: int, shift: int) -> Expr:
    value: Expr = Var((shift + 5) % 8)
    for bit in range(6):
        operand = Var((shift + bit + 1) % 8)
        value = Eqv(value, operand) if (index >> bit) & 1 else Imp(value, operand)
    return value


def _cone_expr(index: int, revision: int, seed: int) -> tuple[Expr, str]:
    shift = (index * 3 + revision + seed % 8) % 8
    a = And(Var(shift), Not(Var((shift + 1) % 8)))
    b = Imp(Var((shift + 2) % 8), Var((shift + 3) % 8))
    c = Eqv(Var((shift + 4) % 8), Var((shift + 6) % 8))
    family = ("aig_xor", "demorgan_or", "common_factor", "negative_control")[(index // 4) % 4]
    if family == "aig_xor":
        site = aig_xor_expr(a, b)
    elif family == "demorgan_or":
        site = aig_or_expr(a, b)
    elif family == "common_factor":
        site = factored_or_expr(a, b, c)
    else:
        site = Imp(Or(a, b), Xor(c, Var((shift + 7) % 8)))
    return And(site, _tag(index, shift)), family


def _version_states(config: ProfitabilityRuleConfig) -> dict[str, dict[int, int]]:
    states: dict[str, dict[int, int]] = {}
    current = {index: 0 for index in range(config.cone_count)}
    states["v1"] = dict(current)
    for index in (0, 1, 2, 3):
        current[index] = 1
    states["v2"] = dict(current)
    for index in (4, 5):
        del current[index]
    current[config.cone_count] = 0
    current[config.cone_count + 1] = 0
    for index in (6, 7, 8, 9):
        current[index] = 1
    states["v3"] = dict(current)
    for index in (0, 1):
        current[index] = 0
    for index in (10, 11):
        current[index] = 1
    states["v4"] = dict(current)
    return states


def make_versions(config: ProfitabilityRuleConfig) -> tuple[dict[str, list[ProfitabilityCone]], dict[str, Any]]:
    config.validate()
    states = _version_states(config)
    result: dict[str, list[ProfitabilityCone]] = {}
    manifest_versions: dict[str, Any] = {}
    prior_hashes: dict[str, str] = {}
    prior_ids: set[str] = set()
    v1_hashes: dict[str, str] = {}
    for version_id in VERSIONS:
        cones = []
        current_hashes = {}
        for index, revision in sorted(states[version_id].items()):
            expr, family = _cone_expr(index, revision, config.data_seed)
            expr = _clone(expr)
            cone_id = f"cone-{index:03d}"
            digest = structural_digest(expr)
            current_hashes[cone_id] = digest
            if version_id == "v1":
                change_kind = "initial"
            elif cone_id not in prior_hashes:
                change_kind = "added"
            elif digest == prior_hashes[cone_id]:
                change_kind = "unchanged"
            elif digest == v1_hashes.get(cone_id):
                change_kind = "reverted"
            else:
                change_kind = "modified"
            repeats = REPEAT_SCHEDULE[index % len(REPEAT_SCHEDULE)]
            cones.append(ProfitabilityCone(cone_id, version_id, expr, repeats,
                                            len(postorder(expr)), family, change_kind, 8))
        if len(cones) != config.cone_count or len(set(current_hashes.values())) != config.cone_count:
            raise RuntimeError("profitability corpus count or structural uniqueness disagreement")
        current_ids = set(current_hashes)
        changed = sorted(cone.cone_id for cone in cones
                         if cone.change_kind in ("added", "modified", "reverted"))
        manifest_versions[version_id] = {
            "changed_cone_ids": changed,
            "changed_count": len(changed),
            "added_cone_ids": sorted(current_ids - prior_ids) if version_id != "v1" else [],
            "removed_cone_ids": sorted(prior_ids - current_ids),
            "reverted_cone_ids": sorted(cone.cone_id for cone in cones if cone.change_kind == "reverted"),
            "structural_sha256": current_hashes,
        }
        result[version_id] = cones
        if version_id == "v1":
            v1_hashes = dict(current_hashes)
        prior_hashes, prior_ids = current_hashes, current_ids
    manifest = {"schema": "crse-profitability-related-dag-versions/v1",
                "seed": config.data_seed, "cone_count_per_version": config.cone_count,
                "repeat_schedule": list(REPEAT_SCHEDULE), "versions": manifest_versions,
                "relationship": "stable named cones with modifications, removals, additions, and exact reverts"}
    return result, manifest


def versions_document(versions: dict[str, list[ProfitabilityCone]], manifest: dict[str, Any]) -> dict[str, Any]:
    return {**manifest, "expressions": {version_id: [
        {"cone_id": cone.cone_id, "change_kind": cone.change_kind,
         "expected_reuses": cone.expected_reuses, "estimated_nodes": cone.estimated_nodes,
         "motif_family": cone.motif_family, "n_vars": cone.n_vars,
         "structural_sha256": structural_digest(cone.expr),
         "expression_v2": expr_to_json_dag(cone.expr)} for cone in versions[version_id]]
        for version_id in VERSIONS}}


def source_fingerprints() -> dict[str, str]:
    paths = [Path(__file__), ROOT / "cmbench" / "recognition" / "rule_pack.py",
             ROOT / "cmbench" / "recognition" / "computation_experiment.py",
             ROOT / "bitset_backend.py", ROOT / "scripts" / "cm_recognition_rule_profitability.py",
             ROOT / "scripts" / "crse_rule_profitability_verify.py"]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path) for path in paths}


def _deadline_check(started: float, maximum: float) -> None:
    if time.perf_counter() - started > maximum:
        raise TimeoutError("rule profitability experiment exceeded cooperative wall budget")


def _digest_values(values: list[int]) -> str:
    return hashlib.sha256(canonical(values)).hexdigest()


def _measure_version(cones: list[ProfitabilityCone], arm: str, round_index: int,
                     matcher: CompiledRulePack, cache: StructuralConeCache | None,
                     gate: DeterministicProfitabilityGate,
                     expected: dict[tuple[str, str], int]) -> dict[str, Any]:
    version_id = cones[0].version_id
    totals = Counter()
    rule_counts = Counter()
    outputs: list[int] = []
    result_digests: list[str] = []
    details = []
    started_version = time.perf_counter_ns()
    for cone in cones:
        started_cone = time.perf_counter_ns()
        rewritten = cone.expr
        gate_decision = GateDecision(True, "not_gated", 0)
        cache_hit = invalidated = False
        reason = "not_applicable"
        applications = proposals = conflicts = 0
        applications_by_rule = {rule_id: 0 for rule_id in RULE_PRIORITY_V2}
        identity_ns = rewrite_ns = 0
        if arm == "gated_cached":
            gate_decision = gate.decide("complete_vector", cone.expected_reuses, cone.estimated_nodes)
            totals["gate_ns"] += gate_decision.decision_ns
        if arm == "fresh_pack" or (arm == "gated_cached" and gate_decision.apply_rules) or arm == "cached_pack":
            if arm == "fresh_pack":
                rewrite_started = time.perf_counter_ns()
                rewrite = matcher.rewrite(cone.expr, cone.n_vars)
                rewrite_ns = max(1, time.perf_counter_ns() - rewrite_started)
                reason = "fresh_match"
            else:
                if cache is None:
                    raise RuntimeError("cache arm missing structural cache")
                cached = cache.rewrite(cone.cone_id, cone.expr, matcher, cone.n_vars)
                rewrite = cached.rewrite
                identity_ns, rewrite_ns = cached.identity_ns, cached.rewrite_ns
                cache_hit, invalidated, reason = cached.cache_hit, cached.invalidated, cached.reason
            rewritten = rewrite.result
            applications, proposals, conflicts = rewrite.applications, rewrite.proposals, rewrite.conflicts
            applications_by_rule = rewrite.applications_by_rule
        elif arm == "gated_cached":
            reason = gate_decision.reason
        build_ns, run = prepare_task("cse", rewritten, ComputationTask("complete_vector", 1),
                                     Workload(), cone.n_vars)
        kernel_started = time.perf_counter_ns()
        values = [run()[0] for _ in range(cone.expected_reuses)]
        kernel_ns = max(1, time.perf_counter_ns() - kernel_started)
        mismatch = sum(value != expected[(version_id, cone.cone_id)] for value in values)
        total_ns = max(1, time.perf_counter_ns() - started_cone)
        before_program = compile_expr_cse(cone.expr, flatten=True)
        after_program = compile_expr_cse(rewritten, flatten=True)
        outputs.append(values[0])
        result_digests.append(structural_digest(rewritten))
        totals.update({"identity_ns": identity_ns, "rewrite_ns": rewrite_ns,
                       "cse_build_ns": build_ns, "cse_kernel_ns": kernel_ns,
                       "cone_total_ns": total_ns, "mismatches": mismatch,
                       "cache_hits": int(cache_hit), "cache_misses": int(
                           arm in ("cached_pack", "gated_cached") and gate_decision.apply_rules and not cache_hit),
                       "source_invalidations": int(invalidated),
                       "computed_applications": 0 if cache_hit else applications,
                       "reused_applications": applications if cache_hit else 0,
                       "proposals_computed": 0 if cache_hit else proposals,
                       "conflicts_computed": 0 if cache_hit else conflicts,
                       "gate_applies": int(arm == "gated_cached" and gate_decision.apply_rules),
                       "gate_skips": int(arm == "gated_cached" and not gate_decision.apply_rules)})
        if not cache_hit:
            rule_counts.update(applications_by_rule)
        details.append({"cone_id": cone.cone_id, "motif_family": cone.motif_family,
            "change_kind": cone.change_kind, "expected_reuses": cone.expected_reuses,
            "estimated_nodes": cone.estimated_nodes, "n_vars": cone.n_vars,
            "gate_apply": arm == "gated_cached" and gate_decision.apply_rules,
            "gate_reason": gate_decision.reason, "cache_hit": cache_hit,
            "invalidated": invalidated, "cache_reason": reason,
            "identity_ns": identity_ns, "rewrite_ns": rewrite_ns, "cse_build_ns": build_ns,
            "cse_kernel_ns": kernel_ns, "total_ns": total_ns, "mismatches": mismatch,
            "applications": applications, "proposals": proposals, "conflicts": conflicts,
            "applications_by_rule": applications_by_rule,
            "cse_ops_before": len(before_program.ops), "cse_ops_after": len(after_program.ops),
            "output_sha256": _digest_values([values[0]]),
            "result_sha256": structural_digest(rewritten)})
    maintenance_started = time.perf_counter_ns()
    removed_invalidations = 0
    if cache is not None:
        active = {cone.cone_id for cone in cones if arm == "cached_pack" or
                  gate.decide("complete_vector", cone.expected_reuses, cone.estimated_nodes).apply_rules}
        removed_invalidations = cache.invalidate_missing(active)
    maintenance_ns = max(1, time.perf_counter_ns() - maintenance_started) if cache is not None else 0
    wall_elapsed_ns = max(1, time.perf_counter_ns() - started_version)
    total_ns = max(1, totals["cone_total_ns"] + maintenance_ns)
    totals["maintenance_ns"] = maintenance_ns
    totals["removed_invalidations"] = removed_invalidations
    totals["invalidations"] = totals["source_invalidations"] + removed_invalidations
    return {"schema": "crse-rule-profitability-measurement/v1", "version_id": version_id,
        "arm": arm, "round": round_index, "status": "ok" if not totals["mismatches"] else "mismatch",
        "cone_count": len(cones), "declared_changed_cones": sum(
            cone.change_kind in ("added", "modified", "reverted") for cone in cones),
        "gate_ns": totals["gate_ns"], "gate_applies": totals["gate_applies"],
        "gate_skips": totals["gate_skips"], "cache_hits": totals["cache_hits"],
        "cache_misses": totals["cache_misses"], "source_invalidations": totals["source_invalidations"],
        "removed_invalidations": removed_invalidations, "invalidations": totals["invalidations"],
        "identity_ns": totals["identity_ns"], "rewrite_ns": totals["rewrite_ns"],
        "computed_applications": totals["computed_applications"],
        "reused_applications": totals["reused_applications"],
        "proposals_computed": totals["proposals_computed"], "conflicts_computed": totals["conflicts_computed"],
        "computed_applications_by_rule": {rule_id: rule_counts[rule_id] for rule_id in RULE_PRIORITY_V2},
        "cse_build_ns": totals["cse_build_ns"], "cse_kernel_ns": totals["cse_kernel_ns"],
        "maintenance_ns": maintenance_ns, "total_ns": total_ns,
        "wall_elapsed_ns": wall_elapsed_ns, "mismatches": totals["mismatches"],
        "output_sha256": _digest_values(outputs),
        "result_digests_sha256": hashlib.sha256(canonical(result_digests)).hexdigest(),
        "cones": details}


def measure_sequences(versions: dict[str, list[ProfitabilityCone]], config: ProfitabilityRuleConfig,
                      matcher: CompiledRulePack,
                      expected: dict[tuple[str, str], int], wall_started: float) -> list[dict[str, Any]]:
    rows = []
    gate = DeterministicProfitabilityGate(config.min_reuses, config.min_estimated_nodes)
    rng = random.Random(f"{config.data_seed}:profitability-arm-order/v1")
    for round_index in range(config.rounds):
        arms = list(ARMS)
        rng.shuffle(arms)
        for arm in arms:
            cache = StructuralConeCache(max_entries=config.cone_count + 2) if "cached" in arm else None
            for version_id in VERSIONS:
                _deadline_check(wall_started, config.max_seconds)
                rows.append(_measure_version(versions[version_id], arm, round_index,
                                             matcher, cache, gate, expected))
    return rows


def _geomean(values: list[float]) -> float:
    return math.exp(statistics.fmean(math.log(value) for value in values))


def summarize(rows: list[dict[str, Any]], rounds: int) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["version_id"], row["arm"])].append(row)
    versions = {}
    for version_id in VERSIONS:
        if not all(len(grouped[(version_id, arm)]) == rounds for arm in ARMS):
            continue
        medians = {arm: int(statistics.median(row["total_ns"] for row in grouped[(version_id, arm)]))
                   for arm in ARMS}
        sample = grouped[(version_id, "gated_cached")][0]
        versions[version_id] = {"median_total_ns": medians,
            "declared_changed_cones": sample["declared_changed_cones"],
            "gated_cache_hits": sample["cache_hits"], "gated_cache_misses": sample["cache_misses"],
            "gated_invalidations": sample["invalidations"], "gate_applies": sample["gate_applies"],
            "gate_skips": sample["gate_skips"],
            "gated_speedup_over_no_rewrite": medians["no_rewrite"] / medians["gated_cached"],
            "gated_speedup_over_fresh_pack": medians["fresh_pack"] / medians["gated_cached"]}
    sequences = {}
    for arm in ARMS:
        per_round = []
        for round_index in range(rounds):
            selected = [row["total_ns"] for row in rows if row["arm"] == arm and row["round"] == round_index]
            if len(selected) == len(VERSIONS):
                per_round.append(sum(selected))
        if len(per_round) == rounds:
            sequences[arm] = int(statistics.median(per_round))
    cone_lookup = {(row["version_id"], row["arm"], row["round"], cone["cone_id"]): cone
                   for row in rows for cone in row["cones"]}
    by_repeats = {}
    for repeats in REPEAT_SCHEDULE:
        values = {}
        for arm in ("fresh_pack", "cached_pack", "gated_cached"):
            ratios = []
            for key, baseline in cone_lookup.items():
                version_id, key_arm, round_index, cone_id = key
                if key_arm != "no_rewrite" or baseline["expected_reuses"] != repeats:
                    continue
                candidate = cone_lookup[(version_id, arm, round_index, cone_id)]
                ratios.append(baseline["total_ns"] / candidate["total_ns"])
            values[f"{arm}_speedup_over_no_rewrite_geomean"] = _geomean(ratios)
        by_repeats[str(repeats)] = values
    oracle_fresh_rounds, oracle_cached_rounds = [], []
    no_rewrite_rounds = []
    for round_index in range(rounds):
        no_total = fresh_total = cached_total = 0
        for key, baseline in cone_lookup.items():
            version_id, key_arm, key_round, cone_id = key
            if key_arm != "no_rewrite" or key_round != round_index:
                continue
            no_total += baseline["total_ns"]
            fresh_total += min(baseline["total_ns"],
                               cone_lookup[(version_id, "fresh_pack", round_index, cone_id)]["total_ns"])
            cached_total += min(baseline["total_ns"],
                                cone_lookup[(version_id, "cached_pack", round_index, cone_id)]["total_ns"])
        no_rewrite_rounds.append(no_total)
        oracle_fresh_rounds.append(fresh_total)
        oracle_cached_rounds.append(cached_total)
    no_oracle_basis = statistics.median(no_rewrite_rounds)
    oracle_fresh = statistics.median(oracle_fresh_rounds)
    oracle_cached = statistics.median(oracle_cached_rounds)
    return {"versions": versions, "median_sequence_total_ns": sequences,
        "gated_sequence_speedup_over_no_rewrite": sequences["no_rewrite"] / sequences["gated_cached"],
        "gated_sequence_speedup_over_fresh_pack": sequences["fresh_pack"] / sequences["gated_cached"],
        "gated_sequence_speedup_over_cached_pack": sequences["cached_pack"] / sequences["gated_cached"],
        "by_expected_reuses": by_repeats,
        "optimistic_free_oracle": {
            "basis": "sum of per-cone measured minima; excludes selector and cross-arm orchestration overhead",
            "no_rewrite_cone_total_ns": int(no_oracle_basis),
            "fresh_pack_oracle_ns": int(oracle_fresh),
            "cached_pack_oracle_ns": int(oracle_cached),
            "fresh_pack_oracle_speedup": no_oracle_basis / oracle_fresh,
            "cached_pack_oracle_speedup": no_oracle_basis / oracle_cached},
        "timing_is_machine_specific": True}


def hardening_audit(output: Path, matcher: CompiledRulePack,
                    versions: dict[str, list[ProfitabilityCone]]) -> dict[str, Any]:
    selected = versions["v1"][:3]
    cache = StructuralConeCache(max_entries=3)
    for cone in selected:
        cache.rewrite(cone.cone_id, cone.expr, matcher, 8)
    snapshot = output / "cache_snapshot.json"
    cache.save(snapshot)
    restored = StructuralConeCache.load(snapshot, matcher)
    reload_hits = sum(restored.rewrite(cone.cone_id, _clone(cone.expr), matcher, 8).cache_hit
                      for cone in selected)
    collision = StructuralConeCache(max_entries=1, identity_hasher=lambda _value: "0" * 64)
    first = selected[0]
    collision.rewrite(first.cone_id, first.expr, matcher, 8)
    collision_result = collision.rewrite(first.cone_id, selected[1].expr, matcher, 8)
    capacity_refused = False
    bounded = StructuralConeCache(max_entries=1)
    bounded.rewrite(selected[0].cone_id, selected[0].expr, matcher, 8)
    try:
        bounded.rewrite(selected[1].cone_id, selected[1].expr, matcher, 8)
    except ValueError:
        capacity_refused = True
    changed_matcher = CompiledRulePack("f" * 64, RULE_PRIORITY_V2)
    pack_cache = StructuralConeCache(max_entries=1)
    pack_cache.rewrite(first.cone_id, first.expr, matcher, 8)
    pack_change = pack_cache.rewrite(first.cone_id, first.expr, changed_matcher, 8)
    pack = prove_rule_pack_v2().document
    def count_ops(value: Any) -> int:
        if type(value) is dict:
            return int("op" in value) + sum(count_ops(child) for child in value.values())
        if type(value) is list:
            return sum(count_ops(child) for child in value)
        return 0
    strict_decrease = all(count_ops(rule["pattern"]) > count_ops(rule["replacement"])
                          for rule in pack["rules"])
    return {"cache_reload_hits": reload_hits, "cache_reload_entries": len(selected),
            "collision_invalidated": collision_result.invalidated,
            "collision_reason": collision_result.reason,
            "capacity_refused": capacity_refused,
            "pack_change_invalidated": pack_change.invalidated,
            "pack_change_reason": pack_change.reason,
            "strict_rule_decrease": strict_decrease,
            "duplicate_rule_ids": len(set(RULE_PRIORITY_V2)) != len(RULE_PRIORITY_V2),
            "snapshot_sha256": sha256_file(snapshot)}


def render_report(result: dict[str, Any]) -> str:
    summary = result.get("summaries", {})
    sequence = summary.get("median_sequence_total_ns")
    lines = ["# CRSE Milestone D4: profitability-gated proved rules", "",
        f"Status: **{result['status']}**", f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Exact output mismatches: {result['semantic_mismatches']}", "",
        "## Why this differs from the website kernel measurements", "",
        "The website's 0.888 CM/plain-CSE figure is a kernel-only empirical ratio on its headline synthetic cohort; the matched EPFL ratio is 0.927. Its 1.0038 CM/CSE-flat value is also kernel-only and the matched EPFL result is 0.9998. Those arms compile first and then time repeated exact packed execution.", "",
        "D3 timed structural identity, rule matching or cache lookup, rewriting, CSE construction, and one kernel execution. D4 retains that full boundary but varies expected kernel reuse over 1, 8, 32, and 128 executions. The measurements are different layers of the same preparation-versus-reuse tradeoff, not theoretical-versus-practical evidence.", "",
        "## Rule pack and gate", "",
        "The inert v2 pack contains proved AIG-XOR, De Morgan OR, and common-factor contraction rules. It has 16 exhaustive Boolean proof rows. Every rewrite strictly decreases operator count; XOR wins its declared overlap with the general De Morgan shape, while factoring has a disjoint root shape.", "",
        f"The deterministic gate applies matching only when expected reuse is at least {result['config']['min_reuses']} and upstream node count is at least {result['config']['min_estimated_nodes']}. It never inspects the expression and has no correctness authority; a skip executes the original expression exactly.", ""]
    if sequence:
        lines += ["## End-to-end generated sequence", "",
            "| Arm | Median four-version time (ns) | Speed versus no rewrite |", "| --- | ---: | ---: |"]
        for arm in ARMS:
            speed = sequence["no_rewrite"] / sequence[arm]
            lines.append(f"| {arm} | {sequence[arm]} | {speed:.3f}x |")
        lines += ["", "## Reuse strata", "",
            "| Expected executions | Fresh pack | Cached pack | Gated cache |",
            "| ---: | ---: | ---: | ---: |"]
        for repeats, values in summary["by_expected_reuses"].items():
            lines.append(f"| {repeats} | {values['fresh_pack_speedup_over_no_rewrite_geomean']:.3f}x | "
                         f"{values['cached_pack_speedup_over_no_rewrite_geomean']:.3f}x | "
                         f"{values['gated_cached_speedup_over_no_rewrite_geomean']:.3f}x |")
        oracle = summary["optimistic_free_oracle"]
        lines += ["", "## Oracle headroom", "",
            f"A zero-cost per-cone oracle would achieve {oracle['fresh_pack_oracle_speedup']:.3f}x with fresh matching and {oracle['cached_pack_oracle_speedup']:.3f}x with cached matching. This is an optimistic diagnostic, not an achieved scheduler result.", ""]
    hardening = result.get("hardening", {})
    lines += ["## Cache hardening", "",
        f"Serialized cache reload hits: {hardening.get('cache_reload_hits', 0)}/{hardening.get('cache_reload_entries', 0)}. Forced digest collision invalidated by exact canonical-byte comparison: {hardening.get('collision_invalidated')}. Capacity refusal: {hardening.get('capacity_refused')}. Pack-change invalidation: {hardening.get('pack_change_invalidated')}.", "",
        "Generated cones cover modifications, removals, additions, and exact reverts. Scalar enumeration audits every original expression outside the timer. This milestone can validate a scheduler mechanism, but generated data alone cannot justify production promotion.", ""]
    return "\n".join(lines)


def run_profitability_rule_experiment(config: ProfitabilityRuleConfig, output: Path,
                                      progress=print) -> dict[str, Any]:
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    wall_started = time.perf_counter()
    before = source_fingerprints()
    _write_json(output / "run_spec.json", {**config.run_spec(output), "source_sha256": before})
    rows: list[dict[str, Any]] = []
    status, error_type = "incomplete", ""
    pack = None
    manifest: dict[str, Any] = {}
    hardening: dict[str, Any] = {}
    proof_ns = compile_ns = 0
    try:
        progress("Proving and compiling the three-rule pack")
        started = time.perf_counter_ns()
        pack = prove_rule_pack_v2()
        proof_ns = max(1, time.perf_counter_ns() - started)
        pack.save(output / "proved_rule_pack.json")
        pack = type(pack).load(output / "proved_rule_pack.json")
        started = time.perf_counter_ns()
        matcher = compile_rule_pack(pack)
        compile_ns = max(1, time.perf_counter_ns() - started)
        versions, manifest = make_versions(config)
        _write_json(output / "versioned_cones.json", versions_document(versions, manifest))
        progress("Auditing serialized cache, collisions, capacity, and pack invalidation")
        hardening = hardening_audit(output, matcher, versions)
        expected = {(version_id, cone.cone_id): reference_task(
                    cone.expr, ComputationTask("complete_vector", 1), Workload(), cone.n_vars)[0]
                    for version_id in VERSIONS for cone in versions[version_id]}
        progress("Measuring one-shot through 128-use exact workloads")
        rows = measure_sequences(versions, config, matcher, expected, wall_started)
        if any(row["status"] != "ok" for row in rows):
            raise RuntimeError("profitability measurement failed exact audit")
        status = "complete"
    except (KeyboardInterrupt, Exception) as exc:
        status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        error_type = type(exc).__name__
        progress(f"Incomplete profitability run retained: {error_type}: {exc}")
    _write_jsonl(output / "measurements.jsonl", rows)
    summaries = summarize(rows, config.rounds) if rows else {}
    after = source_fingerprints()
    result = {"schema": RUN_SCHEMA, "status": status, "error_type": error_type,
        "config": asdict(config), "source_sha256": before, "source_unchanged": before == after,
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "cpu_threads_requested": 1, "thread_environment": {name: os.environ.get(name)
                        for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
        "pack": {"pack_id": pack.document["pack_id"] if pack else None,
                 "artifact_sha256": pack.digest if pack else None,
                 "rule_ids": list(RULE_PRIORITY_V2), "proof_rows": 16,
                 "proof_ns": proof_ns, "compile_ns": compile_ns, "artifact_is_inert": True},
        "dataset": manifest, "row_count": len(rows), "summaries": summaries,
        "hardening": hardening,
        "semantic_mismatches": sum(row["mismatches"] for row in rows),
        "failed_rows": sum(row["status"] != "ok" for row in rows),
        "criteria": {"safety_met": status == "complete" and not any(row["mismatches"] for row in rows),
            "hardening_met": status == "complete" and hardening.get("cache_reload_hits") == 3
                and hardening.get("collision_invalidated") is True
                and hardening.get("capacity_refused") is True
                and hardening.get("pack_change_invalidated") is True
                and hardening.get("strict_rule_decrease") is True,
            "gated_beats_fresh_pack": bool(summaries) and
                summaries["gated_sequence_speedup_over_fresh_pack"] > 1.0,
            "gated_beats_no_rewrite": bool(summaries) and
                summaries["gated_sequence_speedup_over_no_rewrite"] > 1.0,
            "production_promotion": False},
        "wall_seconds": time.perf_counter() - wall_started,
        "scientific_claim": "bounded exact profitability gate and adversarial structural-cache mechanism measurement"}
    _write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-rule-profitability-artifacts/v1",
        "status": status, "files_sha256": {path.name: sha256_file(path) for path in files},
        "source_sha256": before})
    return result
