"""Milestone D6: exact reuse across actual feature-model revisions."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from bitset_backend import _eval_words, get_flat_program
from cm_exprlib import And, Expr, Not, Or, Var
from cm_ir import compile_expr_to_cm_ir

from .computation_experiment import sha256_file


ROOT = Path(__file__).resolve().parents[2]
SOURCE_RUN = (ROOT / "deliverables_n22_24" / "master_explainer_2026_08_03"
              / "use_case_benchmarks_2026-08-27" / "runs"
              / "configuration-fm-version-delta-full21-2026-08-27")
RUN_SCHEMA = "crse-natural-revision-cache-experiment/v1"
ARMS = ("direct_cnf", "fresh_cm", "exact_revision_cache")
SOURCE_IDENTITY_CONTRACT = "conditioned-cnf-feature-domain/v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    with path.open("xb") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True,
                                ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical(row) + b"\n")


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _load_json(path: Path, maximum: int) -> Any:
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError(f"{path.name} exceeds size bound")
    return json.loads(raw, object_pairs_hook=_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON value")))


def _load_jsonl(path: Path, maximum: int) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError(f"{path.name} exceeds size bound")
    rows = []
    for line in raw.splitlines():
        if not line:
            continue
        value = json.loads(line, object_pairs_hook=_pairs,
            parse_constant=lambda item: (_ for _ in ()).throw(ValueError("nonfinite JSONL value")))
        if type(value) is not dict:
            raise ValueError("JSONL row must be an object")
        rows.append(value)
    return rows


def _verify_source_checksums() -> dict[str, str]:
    checksum_path = SOURCE_RUN / "CHECKSUMS.sha256"
    if not checksum_path.is_file() or checksum_path.stat().st_size > 16_384:
        raise ValueError("missing or oversized source checksum manifest")
    expected = {}
    for line in checksum_path.read_text(encoding="ascii").splitlines():
        digest, separator, name = line.partition("  ")
        if (separator != "  " or len(digest) != 64 or not name
                or Path(name).name != name or name in expected):
            raise ValueError("invalid source checksum entry")
        try:
            bytes.fromhex(digest)
        except ValueError as exc:
            raise ValueError("invalid source checksum digest") from exc
        expected[name] = digest
    required = {"admissions.csv", "cases.jsonl", "independent-audit.json",
                "inputs.jsonl", "manifest.json", "summary.json", "version-delta.csv"}
    if set(expected) != required:
        raise ValueError("source checksum file set disagreement")
    for name, digest in expected.items():
        path = SOURCE_RUN / name
        if not path.is_file() or sha256_file(path) != digest:
            raise ValueError(f"source artifact checksum mismatch: {name}")
    return expected | {"CHECKSUMS.sha256": sha256_file(checksum_path)}


def packed_sha(value: int, k: int) -> str:
    if type(value) is not int or value < 0:
        raise ValueError("packed relation must be a nonnegative integer")
    return hashlib.sha256(value.to_bytes(1 << max(0, k - 3), "little")).hexdigest()


@dataclass(frozen=True)
class NaturalRevisionCase:
    case_id: str
    transition_id: str
    history: str
    label: str
    slice_kind: str
    k: int
    feature_names: tuple[str, ...]
    earlier_residual: tuple[tuple[int, ...], ...]
    later_residual: tuple[tuple[int, ...], ...]
    earlier_packed_sha256: str
    later_packed_sha256: str

    def source_bytes(self, residual: tuple[tuple[int, ...], ...]) -> bytes:
        return canonical({"contract": SOURCE_IDENTITY_CONTRACT, "case_id": self.case_id,
            "feature_names": self.feature_names, "k": self.k, "residual": residual})


def _residual(value: Any, k: int) -> tuple[tuple[int, ...], ...]:
    if type(value) is not list or len(value) > 100_000:
        raise ValueError("invalid conditioned CNF")
    result = []
    for clause in value:
        if type(clause) is not list or not clause or len(clause) > k:
            raise ValueError("invalid conditioned clause")
        normalized = []
        for literal in clause:
            if type(literal) is not int or literal == 0 or abs(literal) > k:
                raise ValueError("invalid conditioned literal")
            normalized.append(literal)
        result.append(tuple(normalized))
    return tuple(result)


def load_natural_revision_cases(limit: int = 0) -> tuple[list[NaturalRevisionCase], dict[str, Any]]:
    if type(limit) is not int or not 0 <= limit <= 120:
        raise ValueError("case limit must be in [0,120]")
    checksums = _verify_source_checksums()
    manifest = _load_json(SOURCE_RUN / "manifest.json", 128_000)
    source_summary = _load_json(SOURCE_RUN / "summary.json", 128_000)
    audit = _load_json(SOURCE_RUN / "independent-audit.json", 128_000)
    if (manifest.get("schema_version") != "cm-fm-version-delta/v1"
            or source_summary.get("status") != "completed"
            or source_summary.get("case_count") != 120
            or source_summary.get("correctness_mismatches") != 0
            or audit.get("status") != "passed"):
        raise ValueError("source run status or audit disagreement")
    documents = _load_jsonl(SOURCE_RUN / "cases.jsonl", 8_000_000)
    with (SOURCE_RUN / "version-delta.csv").open(encoding="utf-8", newline="") as handle:
        metadata_rows = list(csv.DictReader(handle))
    if len(documents) != 120 or len(metadata_rows) != 120:
        raise ValueError("source case count disagreement")
    cases = []
    seen = set()
    for document, metadata in zip(documents, metadata_rows):
        case_id = document.get("case_id")
        k = document.get("k")
        if (type(case_id) is not str or not case_id or case_id in seen
                or type(k) is not int or k not in (8, 12, 16)
                or metadata.get("case_id") != case_id or int(metadata.get("k", 0)) != k):
            raise ValueError("source case identity disagreement")
        seen.add(case_id)
        feature_names = document.get("feature_names")
        if (type(feature_names) is not list or len(feature_names) != k
                or any(type(name) is not str or not name for name in feature_names)):
            raise ValueError("invalid feature domain")
        earlier_digest = document.get("earlier_packed_sha256")
        later_digest = document.get("later_packed_sha256")
        if (earlier_digest != metadata.get("earlier_packed_sha256")
                or later_digest != metadata.get("later_packed_sha256")):
            raise ValueError("source relation digest disagreement")
        cases.append(NaturalRevisionCase(case_id, metadata["transition_id"], metadata["history"],
            metadata["label"], document["slice_kind"], k, tuple(feature_names),
            _residual(document["earlier_residual"], k),
            _residual(document["later_residual"], k), earlier_digest, later_digest))
    if limit:
        cases = cases[:limit]
    selection = {"schema": "crse-natural-revision-selection/v1", "training_use": False,
        "source_run": str(SOURCE_RUN.relative_to(ROOT)).replace("\\", "/"),
        "source_artifacts_sha256": checksums, "source_commit": manifest["source_commit"],
        "container_image_id": manifest["container_image_id"],
        "source_case_count": len(documents), "selected_case_count": len(cases),
        "selected_case_ids": [case.case_id for case in cases],
        "histories": sorted({case.history for case in cases}),
        "transition_ids": sorted({case.transition_id for case in cases}),
        "claim_boundary": source_summary["claim_boundary"]}
    return cases, selection


@dataclass(frozen=True)
class RevisionCacheEntry:
    source_bytes: bytes
    source_sha256: str
    value: int
    k: int


@dataclass(frozen=True)
class RevisionCacheLookup:
    value: int | None
    hit: bool
    invalidated: bool
    reason: str
    source_sha256: str
    identity_ns: int


class ExactRevisionCache:
    """Stable-case cache requiring digest and exact canonical source equality."""

    def __init__(self, max_entries: int = 120,
                 identity_hasher: Callable[[bytes], str] | None = None):
        if type(max_entries) is not int or not 1 <= max_entries <= 120:
            raise ValueError("invalid revision cache bound")
        self.max_entries = max_entries
        self._hasher = identity_hasher or (lambda value: hashlib.sha256(value).hexdigest())
        self._entries: dict[str, RevisionCacheEntry] = {}

    @property
    def size(self) -> int:
        return len(self._entries)

    def lookup(self, case_id: str, source_bytes: bytes) -> RevisionCacheLookup:
        if type(case_id) is not str or not case_id or len(case_id) > 256:
            raise ValueError("invalid stable case ID")
        if type(source_bytes) is not bytes or not source_bytes or len(source_bytes) > 4_000_000:
            raise ValueError("invalid source identity bytes")
        started = time.perf_counter_ns()
        digest = self._hasher(source_bytes)
        if type(digest) is not str or not digest:
            raise ValueError("invalid source identity digest")
        prior = self._entries.get(case_id)
        if prior is None:
            result = RevisionCacheLookup(None, False, False, "cold_miss", digest, 0)
        elif prior.source_sha256 == digest and prior.source_bytes == source_bytes:
            result = RevisionCacheLookup(prior.value, True, False,
                                         "exact_source_identity", digest, 0)
        else:
            result = RevisionCacheLookup(None, False, True, "source_changed", digest, 0)
        return RevisionCacheLookup(result.value, result.hit, result.invalidated, result.reason,
            result.source_sha256, max(1, time.perf_counter_ns() - started))

    def store(self, case_id: str, source_bytes: bytes, source_sha256: str,
              value: int, k: int) -> None:
        if case_id not in self._entries and len(self._entries) == self.max_entries:
            raise ValueError("revision cache capacity exceeded")
        if (type(value) is not int or value < 0 or type(k) is not int or k not in (8, 12, 16)
                or self._hasher(source_bytes) != source_sha256):
            raise ValueError("invalid revision cache entry")
        self._entries[case_id] = RevisionCacheEntry(source_bytes, source_sha256, value, k)

    def snapshot(self) -> dict[str, Any]:
        return {"schema": "crse-exact-revision-cache-snapshot/v1",
            "identity_contract": SOURCE_IDENTITY_CONTRACT, "entry_count": self.size,
            "max_entries": self.max_entries, "entries": [{"case_id": case_id,
                "source_sha256": entry.source_sha256, "source_bytes": len(entry.source_bytes),
                "k": entry.k, "relation_sha256": packed_sha(entry.value, entry.k)}
                for case_id, entry in sorted(self._entries.items())]}


def _balanced(nodes: list[Expr], constructor: Callable[[Expr, Expr], Expr]) -> Expr:
    if not nodes:
        raise ValueError("balanced tree requires a nonempty list")
    level = list(nodes)
    while len(level) > 1:
        level = [level[index] if index + 1 == len(level)
                 else constructor(level[index], level[index + 1])
                 for index in range(0, len(level), 2)]
    return level[0]


def expression_from_residual(residual: tuple[tuple[int, ...], ...], k: int) -> Expr:
    variables = tuple(Var(index) for index in range(k))
    negatives = tuple(Not(variable) for variable in variables)
    if not residual:
        return Or(variables[0], negatives[0])
    clauses = [_balanced([variables[abs(literal) - 1] if literal > 0
                          else negatives[abs(literal) - 1] for literal in clause], Or)
               for clause in residual]
    return _balanced(clauses, And)


@lru_cache(maxsize=3)
def _patterns(k: int) -> tuple[int, ...]:
    width = 1 << k
    return tuple(sum(1 << assignment for assignment in range(width)
                     if (assignment >> index) & 1) for index in range(k))


def cnf_bitset(residual: tuple[tuple[int, ...], ...], k: int) -> int:
    mask = (1 << (1 << k)) - 1
    patterns = _patterns(k)
    value = mask
    for clause in residual:
        clause_value = 0
        for literal in clause:
            pattern = patterns[abs(literal) - 1]
            clause_value |= pattern if literal > 0 else (~pattern) & mask
        value &= clause_value
    return value


def _cm_value(residual: tuple[tuple[int, ...], ...], k: int) -> tuple[int, dict[str, int]]:
    started = time.perf_counter_ns()
    expression = expression_from_residual(residual, k)
    lower_ns = max(1, time.perf_counter_ns() - started)
    started = time.perf_counter_ns()
    node = compile_expr_to_cm_ir(expression, reuse_cache=False, persistent_cache=False)
    compile_ns = max(1, time.perf_counter_ns() - started)
    started = time.perf_counter_ns()
    value = _eval_words(get_flat_program(node), tuple(f"x{i}" for i in range(k - 1, -1, -1)), {})
    extract_ns = max(1, time.perf_counter_ns() - started)
    return value, {"lower_ns": lower_ns, "compile_ns": compile_ns, "extract_ns": extract_ns}


def expected_case_details(cases: list[NaturalRevisionCase]) -> list[dict[str, Any]]:
    details = []
    for case in cases:
        exact = case.source_bytes(case.earlier_residual) == case.source_bytes(case.later_residual)
        semantic = case.earlier_packed_sha256 == case.later_packed_sha256
        details.append({"case_id": case.case_id, "transition_id": case.transition_id,
            "history": case.history, "slice_kind": case.slice_kind, "k": case.k,
            "exact_source_equal": exact, "semantic_relation_equal": semantic,
            "unsafe_semantic_only_equal": semantic and not exact,
            "expected_later_cache_reason": "exact_source_identity" if exact else "source_changed"})
    return details


def _measure_arm(cases: list[NaturalRevisionCase], arm: str, round_index: int) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError("invalid natural revision arm")
    components = {"identity_ns": 0, "lower_ns": 0, "compile_ns": 0,
                  "extract_ns": 0, "direct_ns": 0}
    cache = ExactRevisionCache(max_entries=max(1, len(cases))) if arm == "exact_revision_cache" else None
    details = []
    wall_started = time.perf_counter_ns()
    mismatches = hits = invalidations = cold_misses = 0
    for case in cases:
        values = []
        reasons = []
        for version, residual, expected_digest in (
                ("earlier", case.earlier_residual, case.earlier_packed_sha256),
                ("later", case.later_residual, case.later_packed_sha256)):
            if arm == "direct_cnf":
                started = time.perf_counter_ns()
                value = cnf_bitset(residual, case.k)
                components["direct_ns"] += max(1, time.perf_counter_ns() - started)
                reason = "direct_exact_evaluation"
            elif arm == "fresh_cm":
                value, measured = _cm_value(residual, case.k)
                for key, amount in measured.items():
                    components[key] += amount
                reason = "fresh_cm_reconstruction"
            else:
                assert cache is not None
                source_bytes = case.source_bytes(residual)
                lookup = cache.lookup(case.case_id, source_bytes)
                components["identity_ns"] += lookup.identity_ns
                if lookup.hit:
                    value = lookup.value
                    hits += int(version == "later")
                else:
                    value, measured = _cm_value(residual, case.k)
                    for key, amount in measured.items():
                        components[key] += amount
                    cache.store(case.case_id, source_bytes, lookup.source_sha256, value, case.k)
                    cold_misses += int(version == "earlier")
                    invalidations += int(version == "later" and lookup.invalidated)
                reason = lookup.reason
            assert value is not None
            observed_digest = packed_sha(value, case.k)
            mismatches += int(observed_digest != expected_digest)
            values.append(observed_digest)
            reasons.append(reason)
        details.append({"case_id": case.case_id, "earlier_relation_sha256": values[0],
            "later_relation_sha256": values[1], "earlier_reason": reasons[0],
            "later_reason": reasons[1]})
    total_ns = sum(components.values())
    return {"schema": "crse-natural-revision-cache-measurement/v1", "status": "ok" if not mismatches else "mismatch",
        "round": round_index, "arm": arm, "case_count": len(cases), "mismatches": mismatches,
        **components, "total_ns": total_ns, "wall_ns": max(1, time.perf_counter_ns() - wall_started),
        "later_cache_hits": hits, "later_invalidations": invalidations,
        "earlier_cold_misses": cold_misses, "cases": details}


def summarize(rows: list[dict[str, Any]], cases: list[NaturalRevisionCase], rounds: int) -> dict[str, Any]:
    medians = {arm: {key: int(statistics.median(row[key] for row in rows if row["arm"] == arm))
                     for key in ("identity_ns", "lower_ns", "compile_ns", "extract_ns", "direct_ns", "total_ns")}
               for arm in ARMS if sum(row["arm"] == arm for row in rows) == rounds}
    if len(medians) != len(ARMS):
        return {}
    details = expected_case_details(cases)
    exact_hits = sum(item["exact_source_equal"] for item in details)
    semantic_equal = sum(item["semantic_relation_equal"] for item in details)
    unsafe_equal = sum(item["unsafe_semantic_only_equal"] for item in details)
    by_stratum = {}
    for kind in ("hash", "incidence"):
        for k in (8, 12, 16):
            selected = [item for item in details if item["slice_kind"] == kind and item["k"] == k]
            if selected:
                by_stratum[f"{kind}-k{k}"] = {"cases": len(selected),
                    "exact_source_hits": sum(item["exact_source_equal"] for item in selected),
                    "semantic_relation_equal": sum(item["semantic_relation_equal"] for item in selected)}
    return {"median_ns": medians,
        "exact_cache_speedup_over_fresh_cm": medians["fresh_cm"]["total_ns"] / medians["exact_revision_cache"]["total_ns"],
        "exact_cache_speedup_over_direct_cnf": medians["direct_cnf"]["total_ns"] / medians["exact_revision_cache"]["total_ns"],
        "fresh_cm_speedup_over_direct_cnf": medians["direct_cnf"]["total_ns"] / medians["fresh_cm"]["total_ns"],
        "source_identity": {"cases": len(cases), "exact_source_hits": exact_hits,
            "required_invalidations": len(cases) - exact_hits,
            "semantic_relation_equal": semantic_equal,
            "semantic_relation_changed": len(cases) - semantic_equal,
            "unsafe_semantic_only_equal": unsafe_equal},
        "by_stratum": by_stratum, "timing_is_machine_specific": True}


@dataclass(frozen=True)
class NaturalRevisionConfig:
    rounds: int = 3
    case_limit: int = 0
    max_seconds: float = 120.0

    def validate(self) -> None:
        if type(self.rounds) is not int or not 1 <= self.rounds <= 3:
            raise ValueError("rounds must be in [1,3]")
        if type(self.case_limit) is not int or not 0 <= self.case_limit <= 120:
            raise ValueError("case limit must be in [0,120]")
        if type(self.max_seconds) not in (int, float) or not 0 < self.max_seconds <= 120:
            raise ValueError("wall budget must be in (0,120]")

    def run_spec(self, output: Path) -> dict[str, Any]:
        self.validate()
        return {"schema": "crse-natural-revision-cache-run-spec/v1", "status": "planned",
            "config": asdict(self), "arms": list(ARMS),
            "source_identity_contract": SOURCE_IDENTITY_CONTRACT,
            "timing_contract": "source-identity-plus-residual-lowering-plus-cm-compile-plus-packed-extraction/v1",
            "direct_baseline": "conditioned-CNF packed exact evaluation from the same residual source/v1",
            "audit_contract": "sealed packed relation digests plus independently recomputed direct exact relations/v1",
            "resource_limits": {"max_cases": 120, "max_rounds": 3, "max_variables": 16,
                "max_cache_entries": 120, "cpu_threads": 1,
                "cooperative_wall_seconds": float(self.max_seconds), "network": False},
            "output": str(output.resolve()),
            "scientific_scope": "actual adjacent feature-model revisions under bounded conditioned relations; not whole-model equivalence or production promotion"}


def source_fingerprints() -> dict[str, str]:
    paths = [Path(__file__), ROOT / "scripts" / "cm_recognition_natural_revisions.py",
             ROOT / "scripts" / "crse_natural_revision_verify.py"]
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha256_file(path) for path in paths}


def build_cache_snapshot(cases: list[NaturalRevisionCase]) -> dict[str, Any]:
    cache = ExactRevisionCache(max_entries=max(1, len(cases)))
    for case in cases:
        source_bytes = case.source_bytes(case.later_residual)
        digest = hashlib.sha256(source_bytes).hexdigest()
        value = cnf_bitset(case.later_residual, case.k)
        cache.store(case.case_id, source_bytes, digest, value, case.k)
    return cache.snapshot()


def render_report(result: dict[str, Any]) -> str:
    summary = result.get("summaries", {})
    lines = ["# CRSE Milestone D6: exact cache on actual feature-model revisions", "",
        f"Status: **{result['status']}**", f"Wall time: {result['wall_seconds']:.3f} seconds",
        f"Exact output mismatches: {result['semantic_mismatches']}", "",
        "## Contract", "",
        "This run reuses the audited 21-transition feature-model campaign. Its 120 bounded cases compare the earlier and later conditioned CNF over the same shared named-feature domain. A cache hit requires a stable case ID, the exact canonical source bytes, and its digest; digest agreement alone is insufficient.", "",
        "Output equality is retained only as an oracle statistic. It is not a cache key and does not establish whole-model equivalence.", ""]
    if not summary:
        lines += [f"No complete timing summary is available. Error type: `{result['error_type']}`.", ""]
        return "\n".join(lines)
    identity = summary["source_identity"]
    lines += ["## Results", "",
        "| Arm | Median charged time | Speed versus direct CNF |",
        "| --- | ---: | ---: |"]
    direct = summary["median_ns"]["direct_cnf"]["total_ns"]
    for arm in ARMS:
        total = summary["median_ns"][arm]["total_ns"]
        lines.append(f"| {arm} | {total} ns | {direct / total:.3f}x |")
    lines += ["", f"The exact revision cache was **{summary['exact_cache_speedup_over_fresh_cm']:.3f}x** faster than fresh CM reconstruction and **{summary['exact_cache_speedup_over_direct_cnf']:.3f}x** versus the direct CNF baseline.", "",
        f"There were {identity['exact_source_hits']} safe hits and {identity['required_invalidations']} required invalidations. Although {identity['semantic_relation_equal']} relations were equal, {identity['unsafe_semantic_only_equal']} of those equal outputs came from changed source bytes and were correctly refused as cache hits.", "",
        "These are real adjacent configuration-model revisions, but the measured task remains a bounded relation over 8, 12, or 16 selected features under a joint satisfying context. The result does not claim whole-model semantic equivalence.", ""]
    return "\n".join(lines)


def run_natural_revision_experiment(config: NaturalRevisionConfig, output: Path,
                                    progress=print) -> dict[str, Any]:
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    wall_started = time.perf_counter()
    before = source_fingerprints()
    _write_json(output / "run_spec.json", {**config.run_spec(output), "source_sha256": before})
    rows: list[dict[str, Any]] = []
    status, error_type = "incomplete", ""
    cases: list[NaturalRevisionCase] = []
    selection: dict[str, Any] = {}
    try:
        progress("Loading and hashing the audited natural revision cases")
        cases, selection = load_natural_revision_cases(config.case_limit)
        _write_json(output / "selection.json", selection)
        expected = expected_case_details(cases)
        _write_json(output / "case_identities.json", {"schema": "crse-natural-revision-identities/v1",
            "identity_contract": SOURCE_IDENTITY_CONTRACT, "cases": expected})
        progress("Measuring direct CNF, fresh CM, and exact revision cache arms")
        rng = random.Random("crse-natural-revision-arm-order/v1")
        for round_index in range(config.rounds):
            arms = list(ARMS)
            rng.shuffle(arms)
            for arm in arms:
                if time.perf_counter() - wall_started > config.max_seconds:
                    raise TimeoutError("natural revision experiment exceeded cooperative wall budget")
                rows.append(_measure_arm(cases, arm, round_index))
        if any(row["status"] != "ok" for row in rows):
            raise RuntimeError("natural revision measurement failed exact digest audit")
        _write_json(output / "cache_snapshot.json", build_cache_snapshot(cases))
        status = "complete"
    except (KeyboardInterrupt, Exception) as exc:
        status = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        error_type = type(exc).__name__
        progress(f"Incomplete natural-revision run retained: {error_type}: {exc}")
    _write_jsonl(output / "measurements.jsonl", rows)
    summaries = summarize(rows, cases, config.rounds) if cases and rows else {}
    after = source_fingerprints()
    result = {"schema": RUN_SCHEMA, "status": status, "error_type": error_type,
        "config": asdict(config), "source_sha256": before, "source_unchanged": before == after,
        "source_selection": selection,
        "environment": {"python": sys.version, "platform": platform.platform(),
            "cpu_threads_requested": 1, "thread_environment": {name: os.environ.get(name)
            for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
        "row_count": len(rows), "summaries": summaries,
        "semantic_mismatches": sum(row["mismatches"] for row in rows),
        "failed_rows": sum(row["status"] != "ok" for row in rows),
        "criteria": {"safety_met": status == "complete" and not any(row["mismatches"] for row in rows),
            "exact_invalidation_met": status == "complete" and bool(summaries)
                and all(row["later_cache_hits"] == summaries["source_identity"]["exact_source_hits"]
                        and row["later_invalidations"] == summaries["source_identity"]["required_invalidations"]
                        for row in rows if row["arm"] == "exact_revision_cache"),
            "actual_related_revisions_met": status == "complete" and len(selection.get("transition_ids", [])) == 20,
            "production_promotion": False},
        "wall_seconds": time.perf_counter() - wall_started,
        "scientific_claim": "exact source-identity reuse and invalidation on bounded relations from actual adjacent feature-model revisions"}
    _write_json(output / "summary.json", result)
    with (output / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(render_report(result))
    files = sorted(path for path in output.iterdir() if path.is_file())
    _write_json(output / "manifest.json", {"schema": "crse-natural-revision-cache-artifacts/v1",
        "status": status, "files_sha256": {path.name: sha256_file(path) for path in files},
        "source_sha256": before})
    return result
