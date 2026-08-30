"""Immutable corpus roles and pre-timing order policies for comparative studies."""

from __future__ import annotations

import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import IDENTIFIER, SHA256, TASKS, canonical_bytes
from .schedule import balanced_orders, case_order


FREEZE_SCHEMA = "cm-comparative-corpus-freeze/v1"
ROLES = ("regression", "development", "confirmation")
ORIGINS = frozenset({"natural", "synthetic", "adversarial"})
KINDS = frozenset({"expression_jsonl_member", "blif", "cnf", "history_json"})
LOCALITIES = frozenset({"blocked", "round_robin", "sliding_window", "zipf"})
PRIMARY_METRICS = ("task_total_wall_ns", "process_tree_peak_rss_bytes")
MAX_CASES = 10_000
MAX_POLICIES = 64
MAX_LEDGER_ROWS = 1_000_000
MAX_SOURCE_BYTES = 1 << 34
SECRET_NAMES = frozenset({".env", ".env.local", ".env.runpod", ".env.runpod.local"})
DIMACS_SEMANTIC_COMMENT_DIRECTIVES = frozenset({"ind", "max", "p-protected", "p-show", "p-weight"})


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _identifier(value: Any, field: str) -> str:
    _require(isinstance(value, str) and IDENTIFIER.fullmatch(value) is not None, f"invalid {field}")
    return value


def _sha(value: Any, field: str) -> str:
    _require(isinstance(value, str) and SHA256.fullmatch(value) is not None, f"invalid {field}")
    return value


def _safe_source_path(value: Any) -> str:
    _require(isinstance(value, str) and value and len(value) <= 512 and "\\" not in value, "invalid source path")
    path = PurePosixPath(value)
    _require(not path.is_absolute() and ".." not in path.parts, "source path escapes root")
    lowered = {part.lower() for part in path.parts}
    _require(not lowered.intersection(SECRET_NAMES) and not any(part.startswith(".env") for part in lowered),
             "secret-like source path")
    return path.as_posix()


def _iso_utc(value: Any) -> str:
    _require(isinstance(value, str) and value.endswith("Z"), "created_utc must use Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("invalid created_utc") from exc
    _require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, "created_utc must be UTC")
    return value


def _strata(value: Any) -> dict[str, Any]:
    _require(isinstance(value, Mapping) and value, "case strata must be a nonempty object")
    output: dict[str, Any] = {}
    for key, item in value.items():
        name = _identifier(key, "stratum name")
        _require(
            item is None
            or type(item) in (bool, int, str)
            or (isinstance(item, list) and len(item) <= 64 and all(type(part) in (bool, int, str) for part in item)),
            "invalid stratum value",
        )
        if type(item) is int:
            _require(-(1 << 63) <= item <= (1 << 63) - 1, "stratum integer out of range")
        if isinstance(item, str):
            _require(len(item) <= 256, "stratum text too long")
        output[name] = item
    canonical_bytes(output)
    return output


def _validate_source(source: Any, *, require_hashes: bool) -> dict[str, Any]:
    expected = {"path", "member_id", "member_sha256", "license", "provenance"}
    if require_hashes:
        expected |= {"bytes", "sha256"}
    _require(isinstance(source, Mapping) and set(source) == expected, "source fields")
    path = _safe_source_path(source["path"])
    member_id = source["member_id"]
    member_sha = source["member_sha256"]
    _require(
        (member_id is None and member_sha is None)
        or (
            isinstance(member_id, str)
            and 0 < len(member_id) <= 256
            and isinstance(member_sha, str)
            and SHA256.fullmatch(member_sha) is not None
        ),
        "member identity must be complete",
    )
    license_id = _identifier(source["license"], "source license")
    provenance = source["provenance"]
    _require(isinstance(provenance, str) and 0 < len(provenance) <= 512, "invalid source provenance")
    normalized = {
        "path": path,
        "member_id": member_id,
        "member_sha256": member_sha,
        "license": license_id,
        "provenance": provenance,
    }
    if require_hashes:
        _require(type(source["bytes"]) is int and 0 <= source["bytes"] <= MAX_SOURCE_BYTES, "source byte bound")
        normalized["bytes"] = source["bytes"]
        normalized["sha256"] = _sha(source["sha256"], "source SHA-256")
    return normalized


def _validate_case(case: Any, *, require_hashes: bool) -> dict[str, Any]:
    _require(
        isinstance(case, Mapping)
        and set(case) == {"case_id", "cluster_id", "role", "origin", "family", "kind", "tasks", "source", "strata"},
        "case fields",
    )
    tasks = case["tasks"]
    _require(isinstance(tasks, list) and tasks and len(tasks) <= len(TASKS), "case tasks")
    _require(len(set(tasks)) == len(tasks) and all(task in TASKS for task in tasks), "unknown/duplicate case task")
    role = case["role"]
    origin = case["origin"]
    kind = case["kind"]
    _require(role in ROLES and origin in ORIGINS and kind in KINDS, "case role/origin/kind")
    source = _validate_source(case["source"], require_hashes=require_hashes)
    _require(
        (kind == "expression_jsonl_member" and source["member_id"] is not None)
        or (kind != "expression_jsonl_member" and source["member_id"] is None),
        "member identity does not match source kind",
    )
    return {
        "case_id": _identifier(case["case_id"], "case id"),
        "cluster_id": _identifier(case["cluster_id"], "cluster id"),
        "role": role,
        "origin": origin,
        "family": _identifier(case["family"], "case family"),
        "kind": kind,
        "tasks": list(tasks),
        "source": source,
        "strata": _strata(case["strata"]),
    }


def _validate_exclusion(row: Any) -> dict[str, Any]:
    _require(
        isinstance(row, Mapping)
        and set(row) == {"exclusion_id", "scope", "predicate", "reason", "frozen_before_timing"},
        "exclusion fields",
    )
    _require(row["scope"] in (*ROLES, "all"), "exclusion scope")
    _require(row["frozen_before_timing"] is True, "exclusion must be frozen before timing")
    _require(isinstance(row["predicate"], str) and 0 < len(row["predicate"]) <= 512, "exclusion predicate")
    _require(isinstance(row["reason"], str) and 0 < len(row["reason"]) <= 512, "exclusion reason")
    return dict(row)


def _policy_without_ledger(policy: Any) -> dict[str, Any]:
    _require(
        isinstance(policy, Mapping)
        and set(policy)
        == {
            "policy_id", "task", "eligible_roles", "arms", "minimum_blocks", "maximum_blocks",
            "locality", "seed", "shard_cells", "noise_rule",
        },
        "draft schedule policy fields",
    )
    task = policy["task"]
    roles = policy["eligible_roles"]
    arms = policy["arms"]
    _require(task in TASKS, "schedule task")
    _require(isinstance(roles, list) and roles and len(set(roles)) == len(roles) and all(role in ROLES for role in roles),
             "schedule eligible roles")
    _require(isinstance(arms, list) and 2 <= len(arms) <= 32 and len(set(arms)) == len(arms), "schedule arms")
    normalized_arms = [_identifier(arm, "schedule arm") for arm in arms]
    orders = balanced_orders(normalized_arms)
    minimum = policy["minimum_blocks"]
    maximum = policy["maximum_blocks"]
    _require(
        type(minimum) is int and type(maximum) is int
        and max(7, len(orders)) <= minimum <= maximum <= 64
        and minimum % len(orders) == 0 and maximum % len(orders) == 0,
        "schedule blocks must contain complete counterbalance cycles",
    )
    _require(policy["locality"] in LOCALITIES and type(policy["seed"]) is int, "schedule locality/seed")
    _require(type(policy["shard_cells"]) is int and 1 <= policy["shard_cells"] <= 100_000, "schedule shard size")
    noise = policy["noise_rule"]
    _require(
        isinstance(noise, Mapping)
        and set(noise) == {"metric", "threshold_ppm", "step_blocks", "independent_units_first"}
        and noise["metric"] == "mad_over_median"
        and type(noise["threshold_ppm"]) is int and 0 <= noise["threshold_ppm"] <= 1_000_000
        and type(noise["step_blocks"]) is int and noise["step_blocks"] > 0
        and noise["step_blocks"] % len(orders) == 0
        and noise["independent_units_first"] is True,
        "schedule noise rule",
    )
    return {
        "policy_id": _identifier(policy["policy_id"], "policy id"),
        "task": task,
        "eligible_roles": list(roles),
        "arms": normalized_arms,
        "minimum_blocks": minimum,
        "maximum_blocks": maximum,
        "locality": policy["locality"],
        "seed": policy["seed"],
        "shard_cells": policy["shard_cells"],
        "noise_rule": dict(noise),
    }


def build_order_ledger(cases: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    normalized = _policy_without_ledger(policy)
    eligible = [
        row for row in cases
        if normalized["task"] in row["tasks"] and row["role"] in normalized["eligible_roles"]
    ]
    _require(eligible, "schedule policy has no eligible cases")
    case_ids = [row["case_id"] for row in eligible]
    case_map = {row["case_id"]: row for row in eligible}
    ordered = case_order(
        case_ids,
        normalized["locality"],
        seed=normalized["seed"],
        repetitions=normalized["maximum_blocks"],
    )
    orders = balanced_orders(normalized["arms"])
    seen: dict[str, int] = {case_id: 0 for case_id in case_ids}
    ledger = []
    for position, case_id in enumerate(ordered):
        block = seen[case_id]
        seen[case_id] += 1
        core = {
            "policy_id": normalized["policy_id"],
            "task": normalized["task"],
            "case_id": case_id,
            "cluster_id": case_map[case_id]["cluster_id"],
            "block": block,
            "case_position": position,
            "arm_order": list(orders[(block + normalized["seed"]) % len(orders)]),
            "conditional_extension": block >= normalized["minimum_blocks"],
        }
        core["order_sha256"] = hashlib.sha256(canonical_bytes(core)).hexdigest()
        ledger.append(core)
    _require(len(ledger) <= MAX_LEDGER_ROWS, "order ledger bound")
    return ledger


def _jsonl_member_sha256(path: Path, member_id: str) -> str:
    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value, "duplicate JSON key in JSONL member")
            value[key] = item
        return value

    def constant(_value):
        raise ValueError("nonfinite JSON")

    matches = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line, object_pairs_hook=pairs, parse_constant=constant)
        if isinstance(record, dict) and record.get("id") == member_id:
            matches.append(hashlib.sha256(canonical_bytes(record)).hexdigest())
    _require(len(matches) == 1, "JSONL member identity must match exactly one record")
    return matches[0]


def dimacs_metadata(path: str | Path) -> dict[str, Any]:
    """Parse strict, unweighted DIMACS CNF structure without solving it."""
    source = Path(path)
    header = None
    clauses = 0
    current_width = 0
    maximum_width = 0
    literal_occurrences = 0
    empty_clauses = 0
    directives = set()
    for line_number, raw in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        tokens = line.split()
        if tokens[0] == "c":
            if len(tokens) >= 2:
                directive = tokens[1].lower()
                if directive == "p" and len(tokens) >= 3:
                    directive += "-" + tokens[2].lower()
                if directive in DIMACS_SEMANTIC_COMMENT_DIRECTIVES:
                    directives.add(directive)
            continue
        if tokens[0] == "p":
            _require(header is None and clauses == 0 and current_width == 0, f"duplicate/late DIMACS header at line {line_number}")
            _require(len(tokens) == 4 and tokens[1] == "cnf", f"unsupported DIMACS header at line {line_number}")
            try:
                variable_count = int(tokens[2], 10)
                declared_clauses = int(tokens[3], 10)
            except ValueError as exc:
                raise ValueError(f"invalid DIMACS header integer at line {line_number}") from exc
            _require(variable_count >= 0 and declared_clauses >= 0, f"negative DIMACS header value at line {line_number}")
            header = (variable_count, declared_clauses)
            continue
        _require(header is not None, f"DIMACS clause precedes header at line {line_number}")
        for token in tokens:
            try:
                literal = int(token, 10)
            except ValueError as exc:
                raise ValueError(f"invalid DIMACS literal at line {line_number}") from exc
            if literal == 0:
                clauses += 1
                maximum_width = max(maximum_width, current_width)
                if current_width == 0:
                    empty_clauses += 1
                current_width = 0
            else:
                _require(abs(literal) <= header[0], f"DIMACS literal exceeds variable bound at line {line_number}")
                current_width += 1
                literal_occurrences += 1
    _require(header is not None, "DIMACS header missing")
    _require(current_width == 0, "unterminated DIMACS clause")
    _require(clauses == header[1], "DIMACS clause count mismatch")
    return {
        "variables": header[0],
        "clauses": clauses,
        "literal_occurrences": literal_occurrences,
        "maximum_clause_width": maximum_width,
        "empty_clauses": empty_clauses,
        "comment_directives": sorted(directives),
    }


def build_freeze(draft: Mapping[str, Any], root: str | Path) -> dict[str, Any]:
    """Materialize source hashes and realized order ledgers from a review draft."""
    expected = {
        "schema", "freeze_id", "created_utc", "timing_results_inspected", "cases", "exclusions",
        "schedule_policies", "primary_metrics", "secondary_metrics", "confirmation", "gate_requirements",
        "provenance",
    }
    _require(isinstance(draft, Mapping) and set(draft) == expected, "draft fields")
    _require(draft["schema"] == FREEZE_SCHEMA, "draft schema")
    project = Path(root).resolve()
    cases = [_validate_case(row, require_hashes=False) for row in draft["cases"]]
    _require(0 < len(cases) <= MAX_CASES, "case count")
    for case in cases:
        source_path = (project / PurePosixPath(case["source"]["path"])).resolve()
        try:
            source_path.relative_to(project)
        except ValueError as exc:
            raise ValueError("resolved source escapes root") from exc
        _require(source_path.is_file(), "source file missing")
        size = source_path.stat().st_size
        _require(size <= MAX_SOURCE_BYTES, "source file too large")
        case["source"]["bytes"] = size
        case["source"]["sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if case["kind"] == "expression_jsonl_member":
            _require(
                _jsonl_member_sha256(source_path, case["source"]["member_id"])
                == case["source"]["member_sha256"],
                "JSONL member SHA-256 mismatch",
            )
    policies = []
    for policy in draft["schedule_policies"]:
        normalized = _policy_without_ledger(policy)
        normalized["order_ledger"] = build_order_ledger(cases, normalized)
        policies.append(normalized)
    freeze = copy.deepcopy(dict(draft))
    freeze["cases"] = cases
    freeze["schedule_policies"] = policies
    freeze["freeze_sha256"] = hashlib.sha256(canonical_bytes(freeze)).hexdigest()
    validate_freeze(freeze)
    return freeze


def validate_freeze(freeze: Mapping[str, Any]) -> None:
    expected = {
        "schema", "freeze_id", "created_utc", "timing_results_inspected", "cases", "exclusions",
        "schedule_policies", "primary_metrics", "secondary_metrics", "confirmation", "gate_requirements",
        "provenance", "freeze_sha256",
    }
    _require(isinstance(freeze, Mapping) and set(freeze) == expected, "freeze fields")
    _require(freeze["schema"] == FREEZE_SCHEMA, "freeze schema")
    _identifier(freeze["freeze_id"], "freeze id")
    _iso_utc(freeze["created_utc"])
    _require(freeze["timing_results_inspected"] is False, "freeze must precede timing inspection")
    core = {key: freeze[key] for key in expected if key != "freeze_sha256"}
    _require(freeze["freeze_sha256"] == hashlib.sha256(canonical_bytes(core)).hexdigest(), "freeze identity mismatch")
    cases = [_validate_case(row, require_hashes=True) for row in freeze["cases"]]
    _require(0 < len(cases) <= MAX_CASES, "case count")
    case_ids = [row["case_id"] for row in cases]
    _require(len(set(case_ids)) == len(case_ids), "duplicate case id")
    cluster_roles: dict[str, str] = {}
    for case in cases:
        prior_role = cluster_roles.setdefault(case["cluster_id"], case["role"])
        _require(prior_role == case["role"], "cluster spans corpus roles")
    _require(isinstance(freeze["exclusions"], list), "exclusions list")
    exclusions = [_validate_exclusion(row) for row in freeze["exclusions"]]
    _require(len({row["exclusion_id"] for row in exclusions}) == len(exclusions), "duplicate exclusion id")
    _require(isinstance(freeze["schedule_policies"], list) and 0 < len(freeze["schedule_policies"]) <= MAX_POLICIES,
             "schedule policies")
    policy_ids = set()
    for policy in freeze["schedule_policies"]:
        _require(isinstance(policy, Mapping) and "order_ledger" in policy, "schedule order ledger missing")
        normalized = _policy_without_ledger({key: value for key, value in policy.items() if key != "order_ledger"})
        _require(normalized["policy_id"] not in policy_ids, "duplicate policy id")
        policy_ids.add(normalized["policy_id"])
        expected_ledger = build_order_ledger(cases, normalized)
        _require(policy["order_ledger"] == expected_ledger, "realized order ledger mismatch")
    _require(tuple(freeze["primary_metrics"]) == PRIMARY_METRICS, "primary metrics changed")
    secondary = freeze["secondary_metrics"]
    _require(isinstance(secondary, list) and secondary and len(secondary) <= 64, "secondary metrics")
    _require(len(set(secondary)) == len(secondary)
             and all(isinstance(item, str) and IDENTIFIER.fullmatch(item) for item in secondary),
             "secondary metrics invalid")
    confirmation = freeze["confirmation"]
    _require(
        isinstance(confirmation, Mapping)
        and set(confirmation) == {"required", "selection_locked", "timing_results_inspected", "minimum_independent_clusters"}
        and confirmation["required"] is True
        and confirmation["selection_locked"] is True
        and confirmation["timing_results_inspected"] is False
        and type(confirmation["minimum_independent_clusters"]) is int
        and 1 <= confirmation["minimum_independent_clusters"] <= MAX_CASES,
        "confirmation policy",
    )
    requirements = freeze["gate_requirements"]
    _require(
        isinstance(requirements, Mapping)
        and set(requirements) == {"minimum_independent_clusters", "required_tasks", "development_origins"},
        "gate requirements",
    )
    minima = requirements["minimum_independent_clusters"]
    _require(isinstance(minima, Mapping) and set(minima) == set(ROLES), "role minima")
    _require(all(type(value) is int and 0 <= value <= MAX_CASES for value in minima.values()), "role minimum values")
    required_tasks = requirements["required_tasks"]
    _require(isinstance(required_tasks, list) and required_tasks and len(set(required_tasks)) == len(required_tasks)
             and all(task in TASKS for task in required_tasks), "required tasks")
    origins = requirements["development_origins"]
    _require(isinstance(origins, list) and origins and len(set(origins)) == len(origins)
             and all(origin in ORIGINS for origin in origins), "development origins")
    _require(isinstance(freeze["provenance"], Mapping), "freeze provenance")
    canonical_bytes(freeze["provenance"])


def verify_sources(freeze: Mapping[str, Any], root: str | Path) -> dict[str, Any]:
    validate_freeze(freeze)
    project = Path(root).resolve()
    rows = []
    file_identities: dict[Path, tuple[int, str]] = {}
    for case in freeze["cases"]:
        source = case["source"]
        path = (project / PurePosixPath(source["path"])).resolve()
        inside = True
        try:
            path.relative_to(project)
        except ValueError:
            inside = False
        present = inside and path.is_file()
        if present and path not in file_identities:
            size = path.stat().st_size
            digest = hashlib.sha256(path.read_bytes()).hexdigest() if size <= MAX_SOURCE_BYTES else None
            file_identities[path] = (size, digest)
        size, digest = file_identities.get(path, (None, None))
        member_match = True
        if present and case["kind"] == "expression_jsonl_member":
            try:
                member_match = (
                    _jsonl_member_sha256(path, source["member_id"]) == source["member_sha256"]
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                member_match = False
        rows.append({
            "case_id": case["case_id"], "path": source["path"], "inside_root": inside,
            "present": present, "bytes_match": size == source["bytes"], "sha256_match": digest == source["sha256"],
            "member_sha256_match": member_match,
        })
    return {
        "cases": rows,
        "verified": all(
            row["inside_root"] and row["present"] and row["bytes_match"]
            and row["sha256_match"] and row["member_sha256_match"]
            for row in rows
        ),
    }


def evaluate_gate(freeze: Mapping[str, Any], source_check: Mapping[str, Any]) -> dict[str, Any]:
    validate_freeze(freeze)
    reasons = []
    if source_check.get("verified") is not True:
        reasons.append("source_identity_verification_failed")
    clusters = {
        role: {case["cluster_id"] for case in freeze["cases"] if case["role"] == role}
        for role in ROLES
    }
    minima = freeze["gate_requirements"]["minimum_independent_clusters"]
    for role in ROLES:
        if len(clusters[role]) < minima[role]:
            reasons.append(f"{role}_independent_clusters_below_minimum")
    tasks = {task for case in freeze["cases"] for task in case["tasks"]}
    for task in freeze["gate_requirements"]["required_tasks"]:
        if task not in tasks:
            reasons.append("required_task_missing:" + task)
    development_origins = {case["origin"] for case in freeze["cases"] if case["role"] == "development"}
    for origin in freeze["gate_requirements"]["development_origins"]:
        if origin not in development_origins:
            reasons.append("development_origin_missing:" + origin)
    confirmation_clusters = len(clusters["confirmation"])
    if confirmation_clusters < freeze["confirmation"]["minimum_independent_clusters"]:
        reasons.append("confirmation_policy_minimum_not_met")
    return {
        "schema": "cm-comparative-p6-gate/v1",
        "freeze_sha256": freeze["freeze_sha256"],
        "source_verified": source_check.get("verified") is True,
        "independent_clusters": {role: len(clusters[role]) for role in ROLES},
        "case_counts": {role: sum(case["role"] == role for case in freeze["cases"]) for role in ROLES},
        "reasons": sorted(set(reasons)),
        "ready_for_paid_measurement": not reasons,
    }
