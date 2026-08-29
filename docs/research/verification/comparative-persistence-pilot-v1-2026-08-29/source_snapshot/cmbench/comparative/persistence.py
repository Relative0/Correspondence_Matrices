"""Strict structural serialize/reload controls for bounded CM comparisons.

The artifact contains flat instructions only.  It never contains a cached
truth vector or query answer.  CM and structural CSE may serialize different
programs, so artifact byte hashes are retained rather than compared across
backends; exact reloaded semantics are compared against scalar CNF enumeration
and the separate frozen flat-program auditor.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from scripts import cm_measurement_verify as scalar
from scripts import cm_session_contracts as sessions

from .arms import semantic_sha256
from .contracts import (
    CONTRACT_SCHEMA,
    RESULT_SCHEMA,
    canonical_bytes,
    contract_digest,
    validate_contract,
    validate_result,
)


BUNDLE_SCHEMA = "cm-comparative-serialized-flat/v1"
SEMANTIC_SCHEMA = "cm-comparative-reload-semantics/v1"
BACKENDS = ("cm", "cse")
MAX_BUNDLE_BYTES = 8 << 20
MAX_VERSIONS = 64
IDENTITY_FIELDS = {
    "schema",
    "serialized_bundle",
    "reload_semantics",
    "semantic_encoding",
    "counters",
    "answer_cache_included",
    "output_cache_used",
    "performance_claim_permitted",
}


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _variables(k: int) -> tuple[str, ...]:
    return tuple(f"x{i}" for i in range(k))


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def persistence_contract(*, contract_id: str, backend: str, k: int, queries: int) -> dict[str, Any]:
    """Return the common structural-reload obligation for one backend."""
    require(backend in BACKENDS, "unsupported persistence backend")
    require(type(k) is int and 1 <= k <= scalar.MAX_K, "persistence width must be 1..8")
    require(type(queries) is int and 1 <= queries <= MAX_VERSIONS, "invalid persistence query count")
    contract = {
        "schema": CONTRACT_SCHEMA,
        "contract_id": contract_id,
        "task": "structural_reload",
        "artifact": {
            "kind": "serialized_structure",
            "variable_order": list(_variables(k)),
            "output_order": [],
            "fixed": [],
            "output_scope": "not_applicable",
            "restoration": "none",
            "stream": None,
        },
        "lifecycle": "serialized_reload",
        "queries": queries,
        "validation": {
            "oracle": "scalar_cnf_plus_independent_flat_replay/v1",
            "validation_in_timed_span": False,
            # CM and CSE structures need not have identical bytes. Exact
            # semantic rows are checked by validate_persistence_result.
            "required_output_sha256": None,
        },
    }
    validate_contract(contract)
    return contract


def _counter_record() -> dict[str, int]:
    return {
        name: 0
        for name in (
            "engine_instances",
            "solver_instances",
            "programs_built",
            "program_cache_hits",
            "ir_persistent_cache_hits",
            "ir_persistent_cache_misses",
            "flat_evaluations",
            "cnf_evaluations",
            "solve_calls",
        )
    }


def build_bundle(scenario: Mapping[str, Any], backend: str) -> tuple[dict[str, Any], dict[str, int]]:
    """Compile every version once and return an inert structural bundle."""
    k = sessions.validate_scenario(scenario)
    require(backend in BACKENDS and 1 <= k <= scalar.MAX_K, "unsupported persistence request")
    require(len(scenario["versions"]) <= MAX_VERSIONS, "too many versions for bounded bundle")
    counts = _counter_record()
    engine = sessions.Engine(scenario, backend, counts)
    versions: list[dict[str, Any]] = []
    try:
        for index, version in enumerate(scenario["versions"]):
            engine.prepare(index)
            program = scalar.export_flat(engine.programs[index], k)
            # Round-trip validation here prevents a producer from emitting an
            # object the strict loader cannot later reconstruct.
            loaded, width = scalar.import_flat(program)
            require(
                width == k and canonical_bytes(scalar.export_flat(loaded, width)) == canonical_bytes(program),
                "unstable flat export",
            )
            versions.append({"version": index, "version_id": version["id"], "program": program})
    finally:
        engine.close()
    bundle = {
        "schema": BUNDLE_SCHEMA,
        "backend": backend,
        "case_id": scenario["id"],
        "scenario_sha256": _digest(scenario),
        "k": k,
        "versions": versions,
        "producer": "cm_session_flat_export/v1",
        "answer_cache_included": False,
    }
    validate_bundle(bundle, scenario=scenario, expected_backend=backend)
    require(len(canonical_bytes(bundle)) <= MAX_BUNDLE_BYTES, "serialized bundle byte bound")
    return bundle, counts


def validate_bundle(
    bundle: Mapping[str, Any], *, scenario: Mapping[str, Any], expected_backend: str
) -> list[tuple[int, Any]]:
    """Validate all structure before returning reconstructed flat programs."""
    k = sessions.validate_scenario(scenario)
    require(expected_backend in BACKENDS and isinstance(bundle, Mapping), "bundle request")
    require(
        set(bundle)
        == {
            "schema",
            "backend",
            "case_id",
            "scenario_sha256",
            "k",
            "versions",
            "producer",
            "answer_cache_included",
        },
        "serialized bundle fields",
    )
    require(
        bundle["schema"] == BUNDLE_SCHEMA
        and bundle["backend"] == expected_backend
        and bundle["case_id"] == scenario["id"]
        and bundle["scenario_sha256"] == _digest(scenario)
        and type(bundle["k"]) is int
        and bundle["k"] == k,
        "serialized bundle identity",
    )
    require(
        bundle["producer"] == "cm_session_flat_export/v1" and bundle["answer_cache_included"] is False,
        "serialized bundle claim boundary",
    )
    rows = bundle["versions"]
    require(isinstance(rows, list) and len(rows) == len(scenario["versions"]), "version bundle cardinality")
    loaded: list[tuple[int, Any]] = []
    for index, (row, version) in enumerate(zip(rows, scenario["versions"])):
        require(
            isinstance(row, Mapping)
            and set(row) == {"version", "version_id", "program"}
            and type(row["version"]) is int
            and row["version"] == index
            and row["version_id"] == version["id"],
            "serialized version identity/order",
        )
        program, width = scalar.import_flat(row["program"])
        require(
            width == k
            and canonical_bytes(scalar.export_flat(program, width)) == canonical_bytes(row["program"]),
            "flat reconstruction mismatch",
        )
        loaded.append((index, program))
    return loaded


def decode_bundle(payload: bytes, *, scenario: Mapping[str, Any], expected_backend: str) -> dict[str, Any]:
    require(isinstance(payload, bytes) and 0 < len(payload) <= MAX_BUNDLE_BYTES, "serialized bundle bytes")
    bundle = scalar.strict_json(payload)
    validate_bundle(bundle, scenario=scenario, expected_backend=expected_backend)
    require(canonical_bytes(bundle) == payload, "serialized bundle must use canonical encoding")
    return bundle


def _semantic_rows_from_programs(programs: Sequence[tuple[int, Any]], scenario: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    k = scenario["k"]
    for index, program in programs:
        relation = scalar.execute_flat(program, k)
        rows.append(
            {
                "version": index,
                "version_id": scenario["versions"][index]["id"],
                "relation_hex": hex(relation),
                "relation_sha256": semantic_sha256(relation, k),
                "satisfying_assignments": relation.bit_count(),
            }
        )
    return rows


def scalar_oracle(scenario: Mapping[str, Any]) -> list[dict[str, Any]]:
    sessions.validate_scenario(scenario)
    rows: list[dict[str, Any]] = []
    for index, version in enumerate(scenario["versions"]):
        relation = scalar.scalar_vector({"k": scenario["k"], "clauses": version["clauses"]})
        rows.append(
            {
                "version": index,
                "version_id": version["id"],
                "relation_hex": hex(relation),
                "relation_sha256": semantic_sha256(relation, scenario["k"]),
                "satisfying_assignments": relation.bit_count(),
            }
        )
    return rows


def execute_persistence(
    *,
    scenario: Mapping[str, Any],
    backend: str,
    contract: Mapping[str, Any],
    case_id: str,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    """Build, encode, decode, reconstruct and query without timing validation."""
    normalized = validate_contract(contract)
    require(
        backend in BACKENDS
        and normalized["task"] == "structural_reload"
        and normalized["kind"] == "serialized_structure"
        and normalized["lifecycle"] == "serialized_reload"
        and normalized["queries"] == len(scenario["versions"])
        and normalized["variable_order"] == _variables(scenario["k"]),
        "persistence contract/request mismatch",
    )
    started = clock()
    bundle, counters = build_bundle(scenario, backend)
    prepared = clock()
    payload = canonical_bytes(bundle)
    serialized = clock()
    decoded = scalar.strict_json(payload)
    decoded_at = clock()
    programs = validate_bundle(decoded, scenario=scenario, expected_backend=backend)
    reconstructed = clock()
    rows = _semantic_rows_from_programs(programs, scenario)
    queried = clock()
    timings = {
        "prepare_ns": prepared - started,
        "serialize_ns": serialized - prepared,
        "decode_ns": decoded_at - serialized,
        "reconstruct_ns": reconstructed - decoded_at,
        "first_query_ns": queried - reconstructed,
        "task_total_ns": queried - started,
    }
    require(all(type(value) is int and value >= 0 for value in timings.values()), "nonmonotonic persistence clock")
    semantic = {"schema": SEMANTIC_SCHEMA, "task": "structural_reload", "rows": rows}
    result = {
        "schema": RESULT_SCHEMA,
        "contract_sha256": contract_digest(contract),
        "case_id": case_id,
        "arm": backend,
        "status": "ok",
        "reason": "completed",
        "timings_ns": timings,
        "artifact": {
            "kind": "serialized_structure",
            "output_scope": "not_applicable",
            "output_order": [],
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
        "resources": {"measurement": "in_process_functional_smoke", "rss_measured": False},
        "identity": {
            "schema": "cm-comparative-persistence-result/v1",
            "serialized_bundle": bundle,
            "reload_semantics": semantic,
            "semantic_encoding": "canonical_json_and_exact_relation_hex/v1",
            "counters": counters,
            "answer_cache_included": False,
            "output_cache_used": False,
            "performance_claim_permitted": False,
        },
    }
    validate_persistence_result(
        result,
        contract,
        scenario=scenario,
        expected_rows=scalar_oracle(scenario),
        expected_backend=backend,
        expected_case_id=case_id,
    )
    return result


def validate_persistence_result(
    result: Mapping[str, Any],
    contract: Mapping[str, Any],
    *,
    scenario: Mapping[str, Any],
    expected_rows: list[dict[str, Any]],
    expected_backend: str,
    expected_case_id: str,
    independent_auditor: Any | None = None,
) -> dict[str, Any]:
    """Validate artifact bytes and both reconstructed and independent semantics."""
    validated = validate_result(result, contract)
    require(
        expected_backend in BACKENDS
        and result.get("arm") == expected_backend
        and result.get("case_id") == expected_case_id,
        "persistence result cell identity",
    )
    require(result.get("resources") == {"measurement": "in_process_functional_smoke", "rss_measured": False},
            "persistence resource boundary")
    identity = result.get("identity")
    require(isinstance(identity, Mapping) and set(identity) == IDENTITY_FIELDS, "persistence identity fields")
    require(
        identity["schema"] == "cm-comparative-persistence-result/v1"
        and identity["semantic_encoding"] == "canonical_json_and_exact_relation_hex/v1"
        and identity["answer_cache_included"] is False
        and identity["output_cache_used"] is False
        and identity["performance_claim_permitted"] is False,
        "persistence claim boundary",
    )
    bundle = identity["serialized_bundle"]
    payload = canonical_bytes(bundle)
    require(
        result["artifact"]["bytes"] == len(payload)
        and result["artifact"]["sha256"] == hashlib.sha256(payload).hexdigest()
        and len(payload) <= MAX_BUNDLE_BYTES,
        "serialized artifact byte identity",
    )
    programs = validate_bundle(bundle, scenario=scenario, expected_backend=expected_backend)
    semantics = identity["reload_semantics"]
    require(
        isinstance(semantics, Mapping)
        and set(semantics) == {"schema", "task", "rows"}
        and semantics["schema"] == SEMANTIC_SCHEMA
        and semantics["task"] == "structural_reload"
        and semantics["rows"] == expected_rows,
        "reloaded semantic mismatch",
    )
    require(_semantic_rows_from_programs(programs, scenario) == expected_rows, "fresh reconstruction mismatch")

    auditor = independent_auditor if independent_auditor is not None else scalar.independent_auditor()
    independent_rows = []
    for row in bundle["versions"]:
        relation = auditor.replay_flat(row["program"])
        index = row["version"]
        independent_rows.append(
            {
                "version": index,
                "version_id": scenario["versions"][index]["id"],
                "relation_hex": hex(relation),
                "relation_sha256": semantic_sha256(relation, scenario["k"]),
                "satisfying_assignments": relation.bit_count(),
            }
        )
    require(independent_rows == expected_rows, "independent flat replay mismatch")
    counts = identity["counters"]
    require(
        isinstance(counts, Mapping)
        and set(counts) == set(_counter_record())
        and all(type(value) is int and 0 <= value <= 1_000_000 for value in counts.values())
        and counts["engine_instances"] == 1
        and counts["programs_built"] == len(scenario["versions"])
        and counts["solver_instances"] == counts["flat_evaluations"] == counts["cnf_evaluations"] == counts["solve_calls"] == 0,
        "persistence construction counters",
    )
    return validated
