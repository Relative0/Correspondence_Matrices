"""Milestone D5: profitability-gated proved rules on sealed natural EPFL cones."""
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

from bitset_backend import build_bitset_env, eval_expr_bitset
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_ir import expr_structural_hash

from .computation_experiment import (
    EPFL_COMMIT, EPFL_CORPUS, EPFL_CORPUS_SHA256, EPFL_PROVENANCE,
    ComputationTask, Workload, reference_task, sha256_file,
)
from .features import IneligibleExpression, postorder, structural_digest
from .portfolio import admit
from .profitability_rule_experiment import (
    ARMS, REPEAT_SCHEDULE, DeterministicProfitabilityGate, ProfitabilityCone,
    _clone, _measure_version, canonical,
)
from .rule_pack import (
    RULE_PRIORITY_V2, StructuralConeCache, compile_rule_pack, prove_rule_pack_v2,
)

ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA = "crse-natural-rule-profitability-experiment/v1"
SESSIONS = ("session-1", "session-2", "session-3")


def _write_json(path: Path, value: Any) -> None:
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


@dataclass(frozen=True)
class NaturalRuleConfig:
    case_count: int = 32
    min_support: int = 9
    max_support: int = 12
    rounds: int = 3
    min_reuses: int = 32
    min_estimated_nodes: int = 8
    max_seconds: float = 120.0

    def validate(self) -> None:
        if type(self.case_count) is not int or not 8 <= self.case_count <= 32:
            raise ValueError("natural case count must be in [8,32]")
        if (type(self.min_support) is not int or type(self.max_support) is not int
                or not 9 <= self.min_support <= self.max_support <= 12):
            raise ValueError("natural support range must stay within [9,12]")
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
        return {"schema": "crse-natural-rule-profitability-run-spec/v1", "status": "planned",
            "config": asdict(self), "arms": list(ARMS), "sessions": list(SESSIONS),
            "rules": list(RULE_PRIORITY_V2), "repeat_schedule": list(REPEAT_SCHEDULE),
            "timing_contract": "gate-plus-identity-plus-rewrite-plus-cse-build-plus-repeated-kernel/v1",
            "selection_contract": "frozen EPFL corpus; admitted equal semantic/syntactic support 9-12; corpus order with circuit-first coverage/v1",
            "training_use": False,
            "resource_limits": {"max_cases": 32, "support_range": [9, 12], "sessions": 3,
                                "max_kernel_repeats": 128, "cpu_threads": 1,
                                "cooperative_wall_seconds": float(self.max_seconds), "network": False},
            "output": str(output.resolve()),
            "scientific_scope": "sealed natural hardware evaluation and repeated-session cache reuse; not related circuit revisions"}


def _axis_order(bits: int, n_vars: int) -> int:
    result = 0
    for epfl_index in range(1 << n_vars):
        crse_index = int(f"{epfl_index:0{n_vars}b}"[::-1], 2)
        result |= ((bits >> crse_index) & 1) << epfl_index
    return result


def _select_per_circuit(items: list[tuple[dict[str, Any], Any]], limit: int):
    selected, circuits = [], set()
    for item in items:
        circuit = item[0]["circuit"]
        if circuit not in circuits:
            selected.append(item)
            circuits.add(circuit)
        if len(selected) == limit:
            return selected
    selected_ids = {item[0]["id"] for item in selected}
    selected.extend(item for item in items if item[0]["id"] not in selected_ids)
    return selected[:limit]


def load_natural_cases(config: NaturalRuleConfig) -> tuple[list[ProfitabilityCone], dict[str, Any]]:
    config.validate()
    if sha256_file(EPFL_CORPUS) != EPFL_CORPUS_SHA256:
        raise ValueError("frozen EPFL corpus hash mismatch")
    provenance = json.loads(EPFL_PROVENANCE.read_text(encoding="utf-8"))
    if (provenance.get("clone_commit_sha") != EPFL_COMMIT
            or provenance.get("remote_url") != "https://github.com/lsils/benchmarks.git"
            or provenance.get("license_name") != "MIT License"):
        raise ValueError("EPFL provenance identity mismatch")
    file_hashes = {Path(item["relpath"]).name: item["sha256"] for item in provenance["aig_files"]}
    eligible = []
    rejected = Counter()
    for line in EPFL_CORPUS.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record.get("record_type") == "epfl_corpus_meta" or record.get("status") != "admitted":
            continue
        syntactic = record.get("synt_support_size")
        semantic = record.get("sem_support_size")
        if (syntactic != semantic or type(syntactic) is not int
                or not config.min_support <= syntactic <= config.max_support):
            rejected["support_contract"] += 1
            continue
        try:
            expr = expr_from_json(record["expression_v2"])
            admit(expr, syntactic, 128)
            bits = eval_expr_bitset(expr, build_bitset_env(tuple(f"x{i}" for i in range(syntactic))))
        except (IneligibleExpression, ValueError, TypeError, RecursionError):
            rejected["current_admission"] += 1
            continue
        byte_count = (1 << syntactic) // 8
        truth_sha = hashlib.sha256(_axis_order(bits, syntactic).to_bytes(byte_count, "little")).hexdigest()
        if (truth_sha != record["truth_sha256"]
                or expr_structural_hash(expr) != record["structural_hash"]
                or file_hashes.get(record["circuit"]) != record["circuit_sha256"]):
            raise ValueError("natural EPFL record identity disagreement")
        eligible.append((record, expr))
    selected = _select_per_circuit(eligible, config.case_count)
    if len(selected) != config.case_count:
        raise ValueError("insufficient natural EPFL cases")
    cases = []
    for index, (record, expr) in enumerate(selected):
        n_vars = record["synt_support_size"]
        cases.append(ProfitabilityCone(record["id"], SESSIONS[0], expr,
            REPEAT_SCHEDULE[index % len(REPEAT_SCHEDULE)], len(postorder(expr)),
            f"epfl_{record['category']}", "initial", n_vars))
    manifest = {"schema": "crse-natural-epfl-rule-selection/v1", "training_use": False,
        "corpus_path": str(EPFL_CORPUS.relative_to(ROOT)).replace("\\", "/"),
        "corpus_sha256": EPFL_CORPUS_SHA256, "upstream_commit": EPFL_COMMIT,
        "upstream_url": provenance["remote_url"], "license": provenance["license_name"],
        "support_range": [config.min_support, config.max_support],
        "eligible_count": len(eligible), "rejected": dict(rejected),
        "selected_ids": [case.cone_id for case in cases],
        "selected_circuits": [record["circuit"] for record, _expr in selected],
        "selection": "first record per circuit in frozen corpus order, then remaining corpus order",
        "prior_epfl_slices_overlap": False,
        "nonoverlap_basis": "Milestones C and D selected only syntactic-support-8 records; this run admits support 9-12 only"}
    return cases, manifest


def make_sessions(cases: list[ProfitabilityCone]) -> dict[str, list[ProfitabilityCone]]:
    return {session: [ProfitabilityCone(case.cone_id, session, _clone(case.expr),
        case.expected_reuses, case.estimated_nodes, case.motif_family,
        "initial" if session == SESSIONS[0] else "unchanged", case.n_vars) for case in cases]
        for session in SESSIONS}


def cases_document(cases: list[ProfitabilityCone], manifest: dict[str, Any]) -> dict[str, Any]:
    return {**manifest, "cases": [{"case_id": case.cone_id, "category": case.motif_family,
        "n_vars": case.n_vars, "expected_reuses": case.expected_reuses,
        "estimated_nodes": case.estimated_nodes, "structural_sha256": structural_digest(case.expr),
        "expression_v2": expr_to_json_dag(case.expr)} for case in cases]}


def source_fingerprints() -> dict[str, str]:
    paths = [Path(__file__), ROOT / "cmbench" / "recognition" / "rule_pack.py",
        ROOT / "cmbench" / "recognition" / "profitability_rule_experiment.py",
        ROOT / "scripts" / "crse_rule_profitability_verify.py", EPFL_CORPUS, EPFL_PROVENANCE,
        ROOT / "scripts" / "cm_recognition_natural_rules.py",
        ROOT / "scripts" / "crse_natural_rule_verify.py"]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path) for path in paths}


def _geomean(values: list[float]) -> float:
    return math.exp(statistics.fmean(math.log(value) for value in values))


def summarize_natural(rows: list[dict[str, Any]], rounds: int) -> dict[str, Any]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["version_id"], row["arm"])].append(row)
    sessions = {}
    for session in SESSIONS:
        medians = {arm: int(statistics.median(row["total_ns"] for row in grouped[(session, arm)]))
                   for arm in ARMS}
        sample = grouped[(session, "gated_cached")][0]
        sessions[session] = {"median_total_ns": medians,
            "gated_cache_hits": sample["cache_hits"], "gated_cache_misses": sample["cache_misses"],
            "gate_applies": sample["gate_applies"], "gate_skips": sample["gate_skips"],
            "gated_speedup_over_no_rewrite": medians["no_rewrite"] / medians["gated_cached"],
            "gated_speedup_over_fresh_pack": medians["fresh_pack"] / medians["gated_cached"]}
    sequences = {}
    for arm in ARMS:
        totals = [sum(row["total_ns"] for row in rows if row["arm"] == arm and row["round"] == round_index)
                  for round_index in range(rounds)]
        sequences[arm] = int(statistics.median(totals))
    lookup = {(row["version_id"], row["arm"], row["round"], cone["cone_id"]): cone
              for row in rows for cone in row["cones"]}
    by_repeats = {}
    for repeats in REPEAT_SCHEDULE:
        by_repeats[str(repeats)] = {}
        for arm in ("fresh_pack", "cached_pack", "gated_cached"):
            ratios = []
            for (session, key_arm, round_index, cone_id), baseline in lookup.items():
                if key_arm == "no_rewrite" and baseline["expected_reuses"] == repeats:
                    ratios.append(baseline["total_ns"] /
                                  lookup[(session, arm, round_index, cone_id)]["total_ns"])
            by_repeats[str(repeats)][f"{arm}_speedup_over_no_rewrite_geomean"] = _geomean(ratios)
    incidence = Counter()
    cases_with_rules = Counter()
    selected = next(row for row in rows if row["version_id"] == SESSIONS[0]
                    and row["arm"] == "fresh_pack" and row["round"] == 0)
    for cone in selected["cones"]:
        for rule_id, count in cone["applications_by_rule"].items():
            incidence[rule_id] += count
            cases_with_rules[rule_id] += int(count > 0)
    no_cone_total = fresh_oracle = cached_oracle = 0
    for key, baseline in lookup.items():
        session, arm, round_index, cone_id = key
        if arm != "no_rewrite" or round_index != 0:
            continue
        no_cone_total += baseline["total_ns"]
        fresh_oracle += min(baseline["total_ns"], lookup[(session, "fresh_pack", 0, cone_id)]["total_ns"])
        cached_oracle += min(baseline["total_ns"], lookup[(session, "cached_pack", 0, cone_id)]["total_ns"])
    return {"sessions": sessions, "median_sequence_total_ns": sequences,
        "gated_sequence_speedup_over_no_rewrite": sequences["no_rewrite"] / sequences["gated_cached"],
        "gated_sequence_speedup_over_fresh_pack": sequences["fresh_pack"] / sequences["gated_cached"],
        "by_expected_reuses": by_repeats,
        "natural_rule_incidence": {rule_id: {"applications": incidence[rule_id],
            "cases_with_rule": cases_with_rules[rule_id]} for rule_id in RULE_PRIORITY_V2},
        "optimistic_free_oracle": {"no_rewrite_cone_total_ns": no_cone_total,
            "fresh_pack_oracle_speedup": no_cone_total / fresh_oracle,
            "cached_pack_oracle_speedup": no_cone_total / cached_oracle},
        "timing_is_machine_specific": True}


def render_report(result: dict[str, Any]) -> str:
    summary = result.get("summaries", {})
    sequence = summary.get("median_sequence_total_ns")
    lines = ["# CRSE Milestone D5: proved-rule profitability on natural EPFL cones", "",
        f"Status: **{result['status']}**", f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Exact output mismatches: {result['semantic_mismatches']}", "",
        "## Contract", "",
        "This sealed evaluation uses frozen EPFL AND/INV circuit cones with equal semantic and syntactic support from 9 through 12 variables. Earlier Milestones C and D used support-8 slices, so no case overlaps. The three sessions are exact repeated uses of the same natural cones; they are not claimed to be circuit revisions.", "",
        "Each arm pays for gating where applicable, structural identity or matching, rewriting, flattened-CSE construction, and 1, 8, 32, or 128 exact packed executions. The original frozen truth digest is checked before timing.", ""]
    if sequence:
        lines += ["## Three-session result", "", "| Arm | Median total (ns) | Speed versus no rewrite |",
            "| --- | ---: | ---: |"]
        for arm in ARMS:
            lines.append(f"| {arm} | {sequence[arm]} | {sequence['no_rewrite'] / sequence[arm]:.3f}x |")
        lines += ["", "## Natural rule incidence", "",
            "| Rule | Applications | Cases containing rule |", "| --- | ---: | ---: |"]
        for rule_id, value in summary["natural_rule_incidence"].items():
            lines.append(f"| {rule_id} | {value['applications']} | {value['cases_with_rule']} |")
        lines += ["", "## Reuse strata", "", "| Executions | Fresh pack | Cached pack | Gated cache |",
            "| ---: | ---: | ---: | ---: |"]
        for repeats, value in summary["by_expected_reuses"].items():
            lines.append(f"| {repeats} | {value['fresh_pack_speedup_over_no_rewrite_geomean']:.3f}x | "
                         f"{value['cached_pack_speedup_over_no_rewrite_geomean']:.3f}x | "
                         f"{value['gated_cached_speedup_over_no_rewrite_geomean']:.3f}x |")
        oracle = summary["optimistic_free_oracle"]
        lines += ["", f"The zero-cost per-cone oracle is {oracle['fresh_pack_oracle_speedup']:.3f}x for fresh matching and {oracle['cached_pack_oracle_speedup']:.3f}x for caching. It diagnoses opportunity; it is not an achieved selector.", ""]
    lines += ["This natural-source result can confirm or reject generated-workload behavior, but one local machine and repeated identical sessions do not establish cross-machine performance or changed-revision invalidation.", ""]
    return "\n".join(lines)


def run_natural_rule_experiment(config: NaturalRuleConfig, output: Path, progress=print) -> dict[str, Any]:
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    wall_started = time.perf_counter()
    before = source_fingerprints()
    _write_json(output / "run_spec.json", {**config.run_spec(output), "source_sha256": before})
    rows = []
    status, error_type = "incomplete", ""
    selection = {}
    pack = None
    try:
        progress("Loading and independently checking the sealed natural EPFL slice")
        cases, selection = load_natural_cases(config)
        _write_json(output / "natural_cases.json", cases_document(cases, selection))
        pack = prove_rule_pack_v2()
        pack.save(output / "proved_rule_pack.json")
        pack = type(pack).load(output / "proved_rule_pack.json")
        matcher = compile_rule_pack(pack)
        sessions = make_sessions(cases)
        expected = {(session, cone.cone_id): eval_expr_bitset(
            cone.expr, build_bitset_env(tuple(f"x{i}" for i in range(cone.n_vars))))
            for session in SESSIONS for cone in sessions[session]}
        gate = DeterministicProfitabilityGate(config.min_reuses, config.min_estimated_nodes)
        rng = random.Random("natural-rule-profitability-arm-order/v1")
        progress("Measuring natural cones across three repeated sessions")
        for round_index in range(config.rounds):
            arms = list(ARMS)
            rng.shuffle(arms)
            for arm in arms:
                cache = StructuralConeCache(max_entries=config.case_count) if "cached" in arm else None
                for session in SESSIONS:
                    if time.perf_counter() - wall_started > config.max_seconds:
                        raise TimeoutError("natural rule experiment exceeded cooperative wall budget")
                    rows.append(_measure_version(sessions[session], arm, round_index,
                                                 matcher, cache, gate, expected))
        if any(row["status"] != "ok" for row in rows):
            raise RuntimeError("natural rule measurement failed exact audit")
        status = "complete"
    except (KeyboardInterrupt, Exception) as exc:
        status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        error_type = type(exc).__name__
        progress(f"Incomplete natural rule run retained: {error_type}: {exc}")
    _write_jsonl(output / "measurements.jsonl", rows)
    summaries = summarize_natural(rows, config.rounds) if rows else {}
    after = source_fingerprints()
    result = {"schema": RUN_SCHEMA, "status": status, "error_type": error_type,
        "config": asdict(config), "source_sha256": before, "source_unchanged": before == after,
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "cpu_threads_requested": 1, "thread_environment": {name: os.environ.get(name)
                        for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
        "pack": {"pack_id": pack.document["pack_id"] if pack else None,
                 "artifact_sha256": pack.digest if pack else None,
                 "rule_ids": list(RULE_PRIORITY_V2), "proof_rows": 16, "artifact_is_inert": True},
        "selection": selection, "row_count": len(rows), "summaries": summaries,
        "semantic_mismatches": sum(row["mismatches"] for row in rows),
        "failed_rows": sum(row["status"] != "ok" for row in rows),
        "criteria": {"safety_met": status == "complete" and not any(row["mismatches"] for row in rows),
            "sealed_natural_source_met": status == "complete" and selection.get("prior_epfl_slices_overlap") is False,
            "gated_beats_fresh_pack": bool(summaries) and
                summaries["gated_sequence_speedup_over_fresh_pack"] > 1.0,
            "gated_beats_no_rewrite": bool(summaries) and
                summaries["gated_sequence_speedup_over_no_rewrite"] > 1.0,
            "production_promotion": False},
        "wall_seconds": time.perf_counter() - wall_started,
        "scientific_claim": "sealed natural EPFL repeated-session proved-rule profitability measurement"}
    _write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-natural-rule-profitability-artifacts/v1",
        "status": status, "files_sha256": {path.name: sha256_file(path) for path in files},
        "source_sha256": before})
    return result
