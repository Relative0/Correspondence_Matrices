"""Milestone D3: proved rule-pack caching across related DAG versions."""
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
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor

from .computation_experiment import (
    ComputationTask, Workload, prepare_task, reference_task, sha256_file,
)
from .features import structural_digest
from .rule_pack import (
    OR_RULE_ID, RULE_PRIORITY, XOR_RULE_ID, CompiledRulePack, ProvedRulePack,
    StructuralConeCache, aig_or_expr, compile_rule_pack, prove_rule_pack,
)

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA = "crse-versioned-rule-cache-experiment/v1"
ARMS = ("no_rewrite", "fresh_pack", "cached_pack")
VERSIONS = ("v1", "v2", "v3")


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
class VersionedRuleConfig:
    data_seed: int = 20260829
    cone_count: int = 32
    changed_per_transition: int = 4
    rounds: int = 3
    max_seconds: float = 120.0

    def validate(self) -> None:
        if type(self.data_seed) is not int or not 0 <= self.data_seed <= 2**32 - 1:
            raise ValueError("invalid data seed")
        if type(self.cone_count) is not int or not 4 <= self.cone_count <= 64:
            raise ValueError("cone count must be in 4..64")
        if (type(self.changed_per_transition) is not int
                or not 1 <= self.changed_per_transition <= self.cone_count // 2):
            raise ValueError("invalid changed-cone bound")
        if type(self.rounds) is not int or not 1 <= self.rounds <= 5:
            raise ValueError("invalid timing rounds")
        if type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 120:
            raise ValueError("wall budget must be in (0,120]")

    def run_spec(self, output: Path) -> dict[str, Any]:
        self.validate()
        return {"schema": "crse-versioned-rule-cache-run-spec/v1", "config": asdict(self),
            "versions": list(VERSIONS), "arms": list(ARMS), "rules": list(RULE_PRIORITY),
            "cache_contract": "exact canonical-v2 structural equality per stable cone ID; changed source or pack identity invalidates",
            "timing_contract": "per-version cache identity, matching/rewrite, fresh CSE build, and complete-vector execution",
            "audit_contract": "independent scalar complete-vector evaluation outside each timed arm",
            "resource_limits": {"variables": 8, "max_cones": 64, "max_versions": 3,
                                "max_cache_entries": 64, "cpu_threads": 1,
                                "cooperative_wall_seconds": float(self.max_seconds), "network": False},
            "output": str(output.resolve()),
            "scientific_scope": "generated related-cone mechanism smoke; not natural version-history generalization"}


@dataclass(frozen=True)
class VersionedCone:
    cone_id: str
    version_id: str
    expr: Expr
    changed_from_previous: bool


def _clone(expr: Expr) -> Expr:
    return expr_from_json(expr_to_json_dag(expr))


def _base_cone(index: int, revision: int, seed: int) -> Expr:
    shift = (index + revision + seed % 8) % 8
    a = And(Var(shift), Or(Var((shift + 1) % 8), Var((shift + 2) % 8)))
    b = Xor(Var((shift + 3) % 8), Not(Var((shift + 4) % 8)))
    c = Imp(Var((shift + 5) % 8), Var((shift + 6) % 8))
    d = Eqv(Var((shift + 7) % 8), And(Var((shift + revision + 2) % 8), Var(shift)))
    xor_site = Not(And(Not(And(a, Not(b))), Not(And(Not(_clone(a)), _clone(b)))))
    or_site = aig_or_expr(c, d)
    shared = Or(xor_site, or_site)
    tag: Expr = Var((index + seed) % 8)
    for bit in range(6):
        operand = Var((shift + bit + 1) % 8)
        tag = Or(tag, operand) if (index >> bit) & 1 else And(tag, operand)
    return And(shared, And(shared, tag))


def make_versions(config: VersionedRuleConfig) -> tuple[dict[str, list[VersionedCone]], dict[str, Any]]:
    config.validate()
    order = list(range(config.cone_count))
    random.Random(f"{config.data_seed}:versioned-change-order/v1").shuffle(order)
    changed_v2 = set(order[:config.changed_per_transition])
    changed_v3 = set(order[config.changed_per_transition:2 * config.changed_per_transition])
    revisions = {index: 0 for index in range(config.cone_count)}
    result: dict[str, list[VersionedCone]] = {}
    prior_hashes: dict[str, str] = {}
    change_manifest = {}
    for version_id, changed in zip(VERSIONS, (set(), changed_v2, changed_v3)):
        if version_id != "v1":
            for index in changed:
                revisions[index] += 1
        cones = []
        current_hashes = {}
        for index in range(config.cone_count):
            expr = _clone(_base_cone(index, revisions[index], config.data_seed))
            cone_id = f"cone-{index:03d}"
            digest = structural_digest(expr)
            is_changed = version_id != "v1" and prior_hashes[cone_id] != digest
            cones.append(VersionedCone(cone_id, version_id, expr, is_changed))
            current_hashes[cone_id] = digest
        actual_changed = sorted(cone.cone_id for cone in cones if cone.changed_from_previous)
        expected_changed = [] if version_id == "v1" else sorted(f"cone-{index:03d}" for index in changed)
        if actual_changed != expected_changed:
            raise RuntimeError("version generator change identity disagreement")
        if len(set(current_hashes.values())) != config.cone_count:
            raise RuntimeError("version generator produced duplicate structural cone groups")
        result[version_id] = cones
        change_manifest[version_id] = {"changed_cone_ids": actual_changed,
                                       "changed_count": len(actual_changed),
                                       "structural_sha256": current_hashes}
        prior_hashes = current_hashes
    manifest = {"schema": "crse-related-dag-versions/v1", "seed": config.data_seed,
                "cone_count": config.cone_count,
                "changed_per_transition": config.changed_per_transition,
                "changes": change_manifest,
                "relationship": "stable named cones; every version is re-deserialized so cache hits require structural rather than object identity"}
    return result, manifest


def versions_document(versions: dict[str, list[VersionedCone]], manifest: dict[str, Any]) -> dict[str, Any]:
    return {**manifest, "versions": {version_id: [
        {"cone_id": cone.cone_id, "changed_from_previous": cone.changed_from_previous,
         "structural_sha256": structural_digest(cone.expr),
         "expression_v2": expr_to_json_dag(cone.expr)} for cone in versions[version_id]]
        for version_id in VERSIONS}}


def source_fingerprints() -> dict[str, str]:
    paths = [Path(__file__), ROOT / "cmbench" / "recognition" / "rule_pack.py",
             ROOT / "cmbench" / "recognition" / "proved_rules.py",
             ROOT / "cmbench" / "recognition" / "computation_experiment.py",
             ROOT / "bitset_backend.py", ROOT / "scripts" / "cm_recognition_versioned_rules.py",
             ROOT / "scripts" / "crse_versioned_rule_verify.py"]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path) for path in paths}


def _deadline_check(started: float, maximum: float) -> None:
    if time.perf_counter() - started > maximum:
        raise TimeoutError("versioned rule experiment exceeded cooperative wall budget")


def _digest_values(values: list[int]) -> str:
    return hashlib.sha256(canonical(values)).hexdigest()


def measure_sequence(versions: dict[str, list[VersionedCone]], arm: str, round_index: int,
                     matcher: CompiledRulePack,
                     expected: dict[tuple[str, str], tuple[int, ...]]) -> list[dict[str, Any]]:
    if arm not in ARMS:
        raise ValueError("unknown versioned rule arm")
    cache = StructuralConeCache(max_entries=len(versions["v1"])) if arm == "cached_pack" else None
    task, workload = ComputationTask("complete_vector", 1), Workload()
    rows = []
    for version_id in VERSIONS:
        cones = versions[version_id]
        identity_ns = rewrite_ns = cse_build_ns = cse_kernel_ns = 0
        hits = misses = invalidations = 0
        computed_applications = reused_applications = proposals = conflicts = 0
        rule_counts = Counter()
        outputs: list[int] = []
        rewritten_exprs: list[Expr] = []
        started = time.perf_counter_ns()
        for cone in cones:
            rewritten = cone.expr
            if arm == "fresh_pack":
                rewrite_started = time.perf_counter_ns()
                rewrite = matcher.rewrite(cone.expr, 8)
                rewrite_ns += max(1, time.perf_counter_ns() - rewrite_started)
                rewritten = rewrite.result
                misses += 1
                computed_applications += rewrite.applications
                proposals += rewrite.proposals
                conflicts += rewrite.conflicts
                rule_counts.update(rewrite.applications_by_rule)
            elif arm == "cached_pack":
                cached = cache.rewrite(cone.cone_id, cone.expr, matcher, 8)
                identity_ns += cached.identity_ns
                rewrite_ns += cached.rewrite_ns
                rewritten = cached.result
                hits += int(cached.cache_hit)
                misses += int(not cached.cache_hit)
                invalidations += int(cached.invalidated)
                if cached.cache_hit:
                    reused_applications += cached.rewrite.applications
                else:
                    computed_applications += cached.rewrite.applications
                    proposals += cached.rewrite.proposals
                    conflicts += cached.rewrite.conflicts
                    rule_counts.update(cached.rewrite.applications_by_rule)
            build_ns, run = prepare_task("cse", rewritten, task, workload, 8)
            cse_build_ns += build_ns
            kernel_started = time.perf_counter_ns()
            actual = run()
            cse_kernel_ns += max(1, time.perf_counter_ns() - kernel_started)
            outputs.append(actual[0])
            rewritten_exprs.append(rewritten)
        if cache is not None:
            invalidations += cache.invalidate_missing({cone.cone_id for cone in cones})
        total_ns = max(1, time.perf_counter_ns() - started)
        mismatches = sum((value,) != expected[(version_id, cone.cone_id)]
                         for cone, value in zip(cones, outputs))
        result_digests = [structural_digest(expr) for expr in rewritten_exprs]
        rows.append({"schema": "crse-versioned-rule-measurement/v1", "version_id": version_id,
            "arm": arm, "round": round_index, "status": "ok" if not mismatches else "mismatch",
            "cone_count": len(cones), "declared_changed_cones": sum(cone.changed_from_previous for cone in cones),
            "cache_hits": hits, "cache_misses": misses, "invalidations": invalidations,
            "identity_ns": identity_ns, "rewrite_ns": rewrite_ns,
            "computed_applications": computed_applications,
            "reused_applications": reused_applications,
            "effective_applications": computed_applications + reused_applications,
            "proposals_computed": proposals, "conflicts_computed": conflicts,
            "computed_applications_by_rule": {rule_id: rule_counts[rule_id] for rule_id in RULE_PRIORITY},
            "cse_build_ns": cse_build_ns, "cse_kernel_ns": cse_kernel_ns,
            "total_ns": total_ns, "mismatches": mismatches,
            "output_sha256": _digest_values(outputs),
            "result_digests_sha256": hashlib.sha256(canonical(result_digests)).hexdigest()})
    return rows


def summarize(rows: list[dict[str, Any]], rounds: int) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["version_id"], row["arm"])].append(row)
    medians = {}
    metrics = ("total_ns", "identity_ns", "rewrite_ns", "cse_build_ns", "cse_kernel_ns")
    for key, selected in grouped.items():
        if len(selected) == rounds and all(row["status"] == "ok" for row in selected):
            medians[key] = {metric: float(statistics.median(row[metric] for row in selected))
                            for metric in metrics}
    versions_summary = {}
    for version_id in VERSIONS:
        if not all((version_id, arm) in medians for arm in ARMS):
            continue
        fresh = medians[(version_id, "fresh_pack")]["total_ns"]
        cached = medians[(version_id, "cached_pack")]["total_ns"]
        baseline = medians[(version_id, "no_rewrite")]["total_ns"]
        sample = next(row for row in rows if row["version_id"] == version_id
                      and row["arm"] == "cached_pack" and row["round"] == 0)
        versions_summary[version_id] = {"declared_changed_cones": sample["declared_changed_cones"],
            "cache_hits": sample["cache_hits"], "cache_misses": sample["cache_misses"],
            "invalidations": sample["invalidations"],
            "computed_applications": sample["computed_applications"],
            "reused_applications": sample["reused_applications"],
            "median_total_ns": {arm: int(medians[(version_id, arm)]["total_ns"]) for arm in ARMS},
            "cached_speedup_over_fresh_pack": fresh / cached,
            "cached_speedup_over_no_rewrite": baseline / cached,
            "fresh_speedup_over_no_rewrite": baseline / fresh}
    sequence_costs = {}
    for arm in ARMS:
        totals = []
        for round_index in range(rounds):
            selected = [row["total_ns"] for row in rows
                        if row["arm"] == arm and row["round"] == round_index]
            if len(selected) == len(VERSIONS):
                totals.append(sum(selected))
        if len(totals) == rounds:
            sequence_costs[arm] = int(statistics.median(totals))
    return {"versions": versions_summary, "median_sequence_total_ns": sequence_costs,
            "cached_sequence_speedup_over_fresh_pack": (
                sequence_costs["fresh_pack"] / sequence_costs["cached_pack"]),
            "cached_sequence_speedup_over_no_rewrite": (
                sequence_costs["no_rewrite"] / sequence_costs["cached_pack"]),
            "timing_is_machine_specific": True}


def render_report(result: dict[str, Any]) -> str:
    lines = ["# CRSE Milestone D3: versioned proved-rule cache", "",
        f"Status: **{result['status']}**", f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Exact output mismatches: {result['semantic_mismatches']}", "",
        "## Pack and cache", "",
        "The fixed pack contains the proved AIG-XOR and De Morgan OR rules. XOR has priority at the intentional overlap where the general OR shape also matches an XOR macro. Both rules exhaust all four Boolean metavariable valuations.", "",
        "The cache is indexed by a stable cone ID and accepts a hit only when the pack hash, canonical v2 source hash, and exact canonical source bytes all agree. A changed source invalidates only that cone entry.", "",
        "## Version results", "",
        "| Version | Changed | Hits | Invalidations | Reused applications | Cached ns | Fresh-pack ns | Cache speedup | Speed vs no rewrite |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    summaries = result.get("summaries", {})
    for version_id, value in summaries.get("versions", {}).items():
        lines.append(f"| {version_id} | {value['declared_changed_cones']} | {value['cache_hits']} | "
                     f"{value['invalidations']} | {value['reused_applications']} | "
                     f"{value['median_total_ns']['cached_pack']} | {value['median_total_ns']['fresh_pack']} | "
                     f"{value['cached_speedup_over_fresh_pack']:.3f} | "
                     f"{value['cached_speedup_over_no_rewrite']:.3f} |")
    sequence = summaries.get("median_sequence_total_ns")
    if sequence is None:
        lines += ["", f"No complete timing summary is available. Error type: `{result['error_type']}`.", ""]
        return "\n".join(lines)
    lines += ["", f"Three-version median sequence: no rewrite {sequence['no_rewrite']} ns; fresh pack {sequence['fresh_pack']} ns; cached pack {sequence['cached_pack']} ns.",
        f"Cached sequence speedup over fresh rematching: {summaries['cached_sequence_speedup_over_fresh_pack']:.3f}x. Speed versus no rewrite: {summaries['cached_sequence_speedup_over_no_rewrite']:.3f}x.", "",
        "Every arm rebuilds and executes CSE for every cone and version. Scalar enumeration audits each version outside the timer. This generated related-version smoke proves cache identity and invalidation behavior; it does not establish natural version-history profitability or production promotion.", ""]
    return "\n".join(lines)


def run_versioned_rule_experiment(config: VersionedRuleConfig, output: Path,
                                  progress=print) -> dict[str, Any]:
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    wall_started = time.perf_counter()
    before = source_fingerprints()
    _write_json(output / "run_spec.json", {**config.run_spec(output), "source_sha256": before})
    rows: list[dict[str, Any]] = []
    status, error_type = "incomplete", ""
    pack: ProvedRulePack | None = None
    pack_proof_ns = pack_compile_ns = 0
    version_manifest: dict[str, Any] = {}
    try:
        progress("Proving and compiling the two-rule Boolean pack")
        started = time.perf_counter_ns()
        pack = prove_rule_pack()
        pack_proof_ns = max(1, time.perf_counter_ns() - started)
        pack_path = output / "proved_rule_pack.json"
        pack.save(pack_path)
        pack = ProvedRulePack.load(pack_path)
        started = time.perf_counter_ns()
        matcher = compile_rule_pack(pack)
        pack_compile_ns = max(1, time.perf_counter_ns() - started)
        versions, version_manifest = make_versions(config)
        _write_json(output / "versioned_cones.json", versions_document(versions, version_manifest))
        expected = {(version_id, cone.cone_id): reference_task(
                    cone.expr, ComputationTask("complete_vector", 1), Workload(), 8)
                    for version_id in VERSIONS for cone in versions[version_id]}
        progress("Measuring no rewrite, fresh rematching, and persistent structural caching")
        rng = random.Random(f"{config.data_seed}:versioned-rule-arm-order/v1")
        for round_index in range(config.rounds):
            arms = list(ARMS)
            rng.shuffle(arms)
            for arm in arms:
                _deadline_check(wall_started, config.max_seconds)
                rows.extend(measure_sequence(versions, arm, round_index, matcher, expected))
        if any(row["status"] != "ok" for row in rows):
            raise RuntimeError("versioned rule measurement failed exact audit")
        status = "complete"
    except (KeyboardInterrupt, Exception) as exc:
        status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        error_type = type(exc).__name__
        progress(f"Incomplete versioned-rule run retained: {error_type}: {exc}")
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
                 "rule_ids": list(RULE_PRIORITY), "proof_rows": 8,
                 "proof_ns": pack_proof_ns, "compile_ns": pack_compile_ns,
                 "priority": list(RULE_PRIORITY), "artifact_is_inert": True},
        "dataset": version_manifest, "row_count": len(rows), "summaries": summaries,
        "semantic_mismatches": sum(row["mismatches"] for row in rows),
        "failed_rows": sum(row["status"] != "ok" for row in rows),
        "cache_accounting": {version_id: {"expected_hits": 0 if version_id == "v1" else
                              config.cone_count - config.changed_per_transition,
                              "expected_invalidations": 0 if version_id == "v1" else
                              config.changed_per_transition} for version_id in VERSIONS},
        "criteria": {"safety_met": status == "complete" and not any(row["mismatches"] for row in rows),
                     "exact_invalidation_met": status == "complete" and all(
                         value["cache_hits"] == (0 if version_id == "v1" else
                         config.cone_count - config.changed_per_transition)
                         and value["invalidations"] == (0 if version_id == "v1" else
                         config.changed_per_transition)
                         for version_id, value in summaries.get("versions", {}).items()),
                     "production_promotion": False},
        "wall_seconds": time.perf_counter() - wall_started,
        "scientific_claim": "bounded exact structural cache and changed-cone invalidation mechanism smoke"}
    _write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-versioned-rule-cache-artifacts/v1",
        "status": status, "files_sha256": {path.name: sha256_file(path) for path in files},
        "source_sha256": before})
    return result
