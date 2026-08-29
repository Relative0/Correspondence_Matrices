"""Fresh-process structural persistence controls and portable BDD control.

The build worker writes only a reconstructable representation.  A distinct
reload worker reads that artifact and computes exact bounded relations.  The
portable ``dd.autoref`` arm is deliberately labelled as a control and never as
native CUDD.  Native ZDD and d4 d-DNNF persistence remain refused until their
own reviewed serialize/reload adapters exist.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

from scripts import cm_measurement_verify as scalar
from scripts import cm_session_contracts as sessions

from . import persistence
from .arms import semantic_sha256
from .contracts import (
    CONTRACT_SCHEMA,
    RESULT_SCHEMA,
    canonical_bytes,
    contract_digest,
    validate_contract,
    validate_result,
)


REQUEST_SCHEMA = "cm-comparative-fresh-persistence-request/v1"
WORKER_SCHEMA = "cm-comparative-fresh-persistence-worker/v1"
RESULT_IDENTITY_SCHEMA = "cm-comparative-fresh-persistence-result/v1"
STANDARD_ARMS = persistence.BACKENDS
BDD_ARMS = ("autoref_bdd_control", "cudd_bdd")
REFUSED_ARMS = ("cudd_zdd", "d4_ddnnf")
ARMS = STANDARD_ARMS + BDD_ARMS + REFUSED_ARMS
MAX_ARTIFACT_BYTES = 8 << 20
MAX_REQUEST_BYTES = 1 << 20
ARTIFACT_NAME = re.compile(r"cell-[A-Za-z0-9_.+-]{1,160}\.json")
SHA256 = re.compile(r"[0-9a-f]{64}")


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def _module_identity(distribution: str, module_name: str) -> dict[str, Any]:
    try:
        version = importlib.metadata.version(distribution)
        spec = importlib.util.find_spec(module_name)
    except (importlib.metadata.PackageNotFoundError, ImportError, AttributeError, ValueError):
        return {"status": "unavailable", "reason": "module_or_distribution_unavailable"}
    if spec is None or spec.origin is None:
        return {"status": "unavailable", "reason": "module_origin_unavailable"}
    path = Path(spec.origin).resolve()
    if not path.is_file():
        return {"status": "unavailable", "reason": "module_file_unavailable"}
    return {
        "status": "identified",
        "distribution": distribution,
        "version": version,
        "module": module_name,
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "native_extension": path.suffix.lower() in {".pyd", ".so", ".dll", ".dylib"},
    }


def capability_inventory() -> dict[str, dict[str, Any]]:
    """Return executable arms and fail-closed persistence refusals."""
    available = {
        arm: {
            "status": "available",
            "reason": "reviewed_structural_bundle_adapter",
            "native_execution": False,
            "portability_control": False,
        }
        for arm in STANDARD_ARMS
    }
    autoref = _module_identity("dd", "dd.autoref")
    available["autoref_bdd_control"] = {
        "status": "available" if autoref.get("status") == "identified" else "refused",
        "reason": (
            "portable_python_bdd_control_only"
            if autoref.get("status") == "identified"
            else "dd_autoref_unavailable"
        ),
        "native_execution": False,
        "portability_control": True,
        "identity": autoref,
    }
    cudd = _module_identity("dd", "dd.cudd")
    native_cudd = cudd.get("status") == "identified" and cudd.get("native_extension") is True
    available["cudd_bdd"] = {
        "status": "available" if native_cudd else "refused",
        "reason": "native_cudd_dump_load_adapter" if native_cudd else "native_cudd_extension_unavailable",
        "native_execution": bool(native_cudd),
        "portability_control": False,
        "identity": cudd,
    }
    zdd = _module_identity("dd", "dd.cudd_zdd")
    available["cudd_zdd"] = {
        "status": "refused",
        "reason": "reviewed_zdd_serialize_reload_adapter_not_implemented",
        "native_execution": False,
        "portability_control": False,
        "identity": zdd,
    }
    available["d4_ddnnf"] = {
        "status": "refused",
        "reason": "current_d4_contract_counts_only_and_does_not_serialize_ddnnf",
        "native_execution": False,
        "portability_control": False,
        "identity": {
            "status": "not_configured",
            "required": "explicit_hash_pinned_binary_and_reviewed_ddnnf_serializer",
        },
    }
    require(tuple(available) == ARMS, "capability inventory order")
    return available


def fresh_contract(*, contract_id: str, arm: str, k: int, queries: int) -> dict[str, Any]:
    require(arm in ARMS, "unsupported fresh-persistence arm")
    require(type(k) is int and 1 <= k <= scalar.MAX_K, "fresh-persistence width must be 1..8")
    require(type(queries) is int and 1 <= queries <= persistence.MAX_VERSIONS, "invalid query count")
    contract = {
        "schema": CONTRACT_SCHEMA,
        "contract_id": contract_id,
        "task": "structural_reload",
        "artifact": {
            "kind": "serialized_structure",
            "variable_order": [f"x{i}" for i in range(k)],
            "output_order": [],
            "fixed": [],
            "output_scope": "not_applicable",
            "restoration": "none",
            "stream": None,
        },
        "lifecycle": "fresh_process",
        "queries": queries,
        "validation": {
            "oracle": "scalar_cnf_plus_fresh_reload_plus_independent_structure_replay/v1",
            "validation_in_timed_span": False,
            "required_output_sha256": None,
        },
    }
    validate_contract(contract)
    return contract


def _exclusive_write(path: Path, payload: bytes) -> None:
    require(path.is_absolute() and ARTIFACT_NAME.fullmatch(path.name) is not None, "invalid artifact path")
    require(path.parent.is_dir() and not path.parent.is_symlink() and not path.exists(), "new artifact path required")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("artifact write made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _bdd_class(arm: str) -> tuple[type[Any], dict[str, Any]]:
    require(arm in BDD_ARMS, "not a BDD arm")
    module_name = "dd.autoref" if arm == "autoref_bdd_control" else "dd.cudd"
    identity = _module_identity("dd", module_name)
    require(identity.get("status") == "identified", "BDD module unavailable")
    require(arm != "cudd_bdd" or identity.get("native_extension") is True, "native CUDD extension required")
    module = importlib.import_module(module_name)
    return module.BDD, identity


def _bdd_roots(manager: Any, scenario: Mapping[str, Any]) -> dict[str, Any]:
    k = sessions.validate_scenario(scenario)
    manager.declare(*(f"x{i}" for i in range(k)))
    roots: dict[str, Any] = {}
    for index, version in enumerate(scenario["versions"]):
        root = manager.true
        for clause in version["clauses"]:
            clause_root = manager.false
            for literal in clause:
                variable = manager.var(f"x{abs(literal) - 1}")
                clause_root |= variable if literal > 0 else ~variable
            root &= clause_root
        roots[f"v{index:03}"] = root
    return roots


def build_artifact(
    scenario: Mapping[str, Any], arm: str, artifact_path: Path, *, clock=time.perf_counter_ns
) -> dict[str, Any]:
    """Build and exclusively write one answer-cache-free artifact."""
    sessions.validate_scenario(scenario)
    require(arm in STANDARD_ARMS + BDD_ARMS, "arm has no executable persistence adapter")
    started = clock()
    if arm in STANDARD_ARMS:
        bundle, counters = persistence.build_bundle(scenario, arm)
        built = clock()
        payload = canonical_bytes(bundle)
        _exclusive_write(artifact_path, payload)
        serialized = clock()
        identity = {
            "adapter": "canonical_structural_bundle/v1",
            "backend": arm,
            "native_execution": False,
            "portability_control": False,
            "counters": counters,
        }
    else:
        bdd_type, module_identity = _bdd_class(arm)
        manager = bdd_type()
        if hasattr(manager, "configure"):
            manager.configure(reordering=False)
        roots = _bdd_roots(manager, scenario)
        built = clock()
        require(not artifact_path.exists(), "new BDD artifact path required")
        manager.dump(str(artifact_path), roots=roots, filetype="json")
        serialized = clock()
        payload = artifact_path.read_bytes()
        identity = {
            "adapter": "dd_json_dump/v1",
            "backend": arm,
            "native_execution": arm == "cudd_bdd",
            "portability_control": arm == "autoref_bdd_control",
            "module": module_identity,
            "roots": list(roots),
        }
    require(0 < len(payload) <= MAX_ARTIFACT_BYTES, "artifact size bound")
    return {
        "schema": WORKER_SCHEMA,
        "mode": "build",
        "arm": arm,
        "pid": os.getpid(),
        "artifact": {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "answer_cache_included": False,
        },
        "timings_ns": {
            "construct_ns": built - started,
            "serialize_ns": serialized - built,
            "task_total_ns": serialized - started,
        },
        "identity": identity,
    }


def _bdd_rows(manager: Any, roots: Mapping[str, Any], scenario: Mapping[str, Any]) -> list[dict[str, Any]]:
    k = sessions.validate_scenario(scenario)
    expected_names = [f"v{index:03}" for index in range(len(scenario["versions"]))]
    require(list(roots) == expected_names, "BDD root identity/order")
    rows = []
    for index, name in enumerate(expected_names):
        root = roots[name]
        relation = 0
        for assignment in range(1 << k):
            values = {f"x{variable}": bool((assignment >> variable) & 1) for variable in range(k)}
            value = manager.let(values, root)
            require(value in {manager.true, manager.false}, "BDD restriction did not reach a terminal")
            relation |= int(value == manager.true) << assignment
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


def query_artifact(
    scenario: Mapping[str, Any], arm: str, artifact_path: Path, expected_sha256: str, *, clock=time.perf_counter_ns
) -> dict[str, Any]:
    """Read, reconstruct and query an artifact in a fresh worker."""
    sessions.validate_scenario(scenario)
    require(arm in STANDARD_ARMS + BDD_ARMS, "arm has no executable persistence adapter")
    require(
        artifact_path.is_absolute()
        and artifact_path.is_file()
        and not artifact_path.is_symlink()
        and ARTIFACT_NAME.fullmatch(artifact_path.name) is not None,
        "artifact file identity",
    )
    require(isinstance(expected_sha256, str) and SHA256.fullmatch(expected_sha256), "artifact SHA-256")
    started = clock()
    payload = artifact_path.read_bytes()
    read_at = clock()
    require(0 < len(payload) <= MAX_ARTIFACT_BYTES, "artifact size bound")
    require(hashlib.sha256(payload).hexdigest() == expected_sha256, "artifact changed before reload")
    if arm in STANDARD_ARMS:
        bundle = persistence.decode_bundle(payload, scenario=scenario, expected_backend=arm)
        structures = persistence.validate_bundle(bundle, scenario=scenario, expected_backend=arm)
        reconstructed = clock()
        rows = persistence._semantic_rows_from_structures(structures, scenario, arm)
        identity = {
            "adapter": "canonical_structural_bundle/v1",
            "backend": arm,
            "native_execution": False,
            "portability_control": False,
        }
    else:
        bdd_type, module_identity = _bdd_class(arm)
        manager = bdd_type()
        loaded = manager.load(str(artifact_path))
        require(isinstance(loaded, Mapping), "BDD load did not return named roots")
        reconstructed = clock()
        rows = _bdd_rows(manager, loaded, scenario)
        identity = {
            "adapter": "dd_json_load/v1",
            "backend": arm,
            "native_execution": arm == "cudd_bdd",
            "portability_control": arm == "autoref_bdd_control",
            "module": module_identity,
        }
    queried = clock()
    return {
        "schema": WORKER_SCHEMA,
        "mode": "reload_query",
        "arm": arm,
        "pid": os.getpid(),
        "artifact": {"bytes": len(payload), "sha256": expected_sha256},
        "rows": rows,
        "timings_ns": {
            "read_ns": read_at - started,
            "reconstruct_ns": reconstructed - read_at,
            "query_ns": queried - reconstructed,
            "task_total_ns": queried - started,
        },
        "identity": identity,
    }


def _strict_json(payload: bytes) -> Any:
    require(isinstance(payload, bytes) and 0 < len(payload) <= MAX_ARTIFACT_BYTES, "JSON artifact bound")

    def pairs(items: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            require(key not in value, "duplicate JSON key")
            value[key] = item
        return value

    def constant(_value: str) -> None:
        raise ValueError("nonfinite JSON constant")

    try:
        return json.loads(payload, object_pairs_hook=pairs, parse_constant=constant)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("invalid JSON artifact") from exc


def independent_bdd_rows(payload: bytes, scenario: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Replay dd JSON without importing dd or calling the producing manager."""
    k = sessions.validate_scenario(scenario)
    data = _strict_json(payload)
    require(isinstance(data, Mapping) and isinstance(data.get("level_of_var"), Mapping), "BDD graph fields")
    roots = data.get("roots")
    expected_names = [f"v{index:03}" for index in range(len(scenario["versions"]))]
    require(isinstance(roots, Mapping) and list(roots) == expected_names, "BDD graph root identity/order")
    levels: dict[int, int] = {}
    for name, level in data["level_of_var"].items():
        require(isinstance(name, str) and re.fullmatch(r"x\d+", name) is not None, "BDD variable name")
        variable = int(name[1:])
        require(type(level) is int and level not in levels, "BDD variable level")
        levels[level] = variable
    require(set(levels) == set(range(k)) and set(levels.values()) == set(range(k)), "BDD variable universe")
    full = (1 << (1 << k)) - 1
    columns = tuple(sum(1 << assignment for assignment in range(1 << k) if (assignment >> var) & 1) for var in range(k))

    def replay(root: Any) -> int:
        cache: dict[int, int] = {}
        active: set[int] = set()

        def visit(reference: Any) -> int:
            if reference == "T":
                return full
            if reference == "F":
                return 0
            require(type(reference) is int and reference != 0, "invalid BDD reference")
            identifier = abs(reference)
            if identifier not in cache:
                require(identifier not in active, "cyclic BDD graph")
                active.add(identifier)
                row = data.get(str(identifier))
                require(isinstance(row, list) and len(row) == 3 and type(row[0]) is int, "BDD node row")
                level, low, high = row
                require(level in levels, "BDD node level")
                for child in (low, high):
                    if type(child) is int:
                        child_row = data.get(str(abs(child)))
                        require(
                            isinstance(child_row, list)
                            and len(child_row) == 3
                            and type(child_row[0]) is int
                            and child_row[0] > level,
                            "BDD order violation",
                        )
                selector = columns[levels[level]]
                cache[identifier] = ((full ^ selector) & visit(low)) | (selector & visit(high))
                active.remove(identifier)
            return cache[identifier] if reference > 0 else full ^ cache[identifier]

        return visit(root)

    rows = []
    for index, name in enumerate(expected_names):
        relation = replay(roots[name])
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


def validate_artifact_semantics(
    artifact_path: Path, *, arm: str, scenario: Mapping[str, Any], expected_sha256: str
) -> list[dict[str, Any]]:
    require(artifact_path.is_file() and not artifact_path.is_symlink(), "artifact unavailable")
    payload = artifact_path.read_bytes()
    require(0 < len(payload) <= MAX_ARTIFACT_BYTES, "artifact size bound")
    require(hashlib.sha256(payload).hexdigest() == expected_sha256, "artifact hash mismatch")
    if arm in STANDARD_ARMS:
        bundle = persistence.decode_bundle(payload, scenario=scenario, expected_backend=arm)
        structures = persistence.validate_bundle(bundle, scenario=scenario, expected_backend=arm)
        return persistence._semantic_rows_from_structures(structures, scenario, arm)
    require(arm in BDD_ARMS, "unreviewed artifact replay arm")
    return independent_bdd_rows(payload, scenario)


def worker_request(payload: bytes) -> dict[str, Any]:
    require(isinstance(payload, bytes) and 0 < len(payload) <= MAX_REQUEST_BYTES, "worker request bound")
    request = _strict_json(payload)
    require(isinstance(request, Mapping), "worker request object")
    fields = {"schema", "mode", "arm", "scenario", "artifact_path"}
    if request.get("mode") == "reload_query":
        fields.add("artifact_sha256")
    require(set(request) == fields and request.get("schema") == REQUEST_SCHEMA, "worker request fields")
    require(request.get("mode") in {"build", "reload_query"}, "worker mode")
    require(request.get("arm") in STANDARD_ARMS + BDD_ARMS, "worker arm")
    sessions.validate_scenario(request["scenario"])
    path = Path(request["artifact_path"])
    require(path.is_absolute() and ARTIFACT_NAME.fullmatch(path.name) is not None, "worker artifact path")
    if request["mode"] == "reload_query":
        require(isinstance(request["artifact_sha256"], str) and SHA256.fullmatch(request["artifact_sha256"]),
                "worker artifact hash")
    return dict(request)


def execute_worker(payload: bytes) -> dict[str, Any]:
    request = worker_request(payload)
    path = Path(request["artifact_path"])
    if request["mode"] == "build":
        return build_artifact(request["scenario"], request["arm"], path)
    return query_artifact(
        request["scenario"], request["arm"], path, request["artifact_sha256"]
    )


def refused_result(
    *, arm: str, case_id: str, contract: Mapping[str, Any], capability: Mapping[str, Any]
) -> dict[str, Any]:
    require(arm in ARMS and capability.get("status") == "refused", "invalid refusal capability")
    result = {
        "schema": RESULT_SCHEMA,
        "contract_sha256": contract_digest(contract),
        "case_id": case_id,
        "arm": arm,
        "status": "refused",
        "reason": capability["reason"],
        "timings_ns": {"task_total_ns": 0},
        "artifact": None,
        "resources": {"launched": False, "memory_ranking_permitted": False},
        "identity": {
            "schema": RESULT_IDENTITY_SCHEMA,
            "capability": dict(capability),
            "performance_claim_permitted": False,
            "substitution_used": False,
        },
    }
    validate_result(result, contract)
    return result


def validate_fresh_result(
    result: Mapping[str, Any],
    contract: Mapping[str, Any],
    *,
    scenario: Mapping[str, Any],
    expected_rows: list[dict[str, Any]],
    capability: Mapping[str, Any],
    artifact_path: Path | None,
) -> dict[str, Any]:
    validated = validate_result(result, contract)
    require(result.get("arm") in ARMS, "fresh result arm")
    identity = result.get("identity")
    require(isinstance(identity, Mapping) and identity.get("schema") == RESULT_IDENTITY_SCHEMA,
            "fresh result identity schema")
    require(identity.get("performance_claim_permitted") is False, "fresh result claim boundary")
    resources = result.get("resources")
    require(isinstance(resources, Mapping) and resources.get("memory_ranking_permitted") is False,
            "fresh resource claim boundary")
    if result["status"] == "refused":
        require(
            capability.get("status") == "refused"
            and result["reason"] == capability.get("reason")
            and resources.get("launched") is False
            and artifact_path is None,
            "refusal did not match capability",
        )
        require(identity.get("substitution_used") is False, "refused arm substitution")
        return validated

    require(result["status"] == "ok" and capability.get("status") == "available", "unexpected success state")
    require(artifact_path is not None, "successful cell artifact path")
    build = identity.get("build_worker")
    reload = identity.get("reload_worker")
    require(
        isinstance(build, Mapping)
        and isinstance(reload, Mapping)
        and build.get("schema") == reload.get("schema") == WORKER_SCHEMA
        and build.get("mode") == "build"
        and reload.get("mode") == "reload_query"
        and build.get("arm") == reload.get("arm") == result["arm"],
        "worker result identity",
    )
    require(type(build.get("pid")) is int and type(reload.get("pid")) is int and build["pid"] != reload["pid"],
            "build and reload must use distinct processes")
    require(reload.get("rows") == expected_rows, "fresh reload semantic mismatch")
    artifact = result["artifact"]
    require(
        build.get("artifact", {}).get("sha256") == artifact["sha256"]
        and reload.get("artifact", {}).get("sha256") == artifact["sha256"]
        and build.get("artifact", {}).get("bytes") == artifact["bytes"]
        and reload.get("artifact", {}).get("bytes") == artifact["bytes"]
        and build.get("artifact", {}).get("answer_cache_included") is False,
        "fresh artifact identity",
    )
    require(
        validate_artifact_semantics(
            artifact_path, arm=result["arm"], scenario=scenario, expected_sha256=artifact["sha256"]
        )
        == expected_rows,
        "independent artifact replay mismatch",
    )
    require(
        identity.get("substitution_used") is False
        and identity.get("native_execution") is capability.get("native_execution")
        and identity.get("portability_control") is capability.get("portability_control"),
        "backend identity/claim mismatch",
    )
    require(resources.get("fresh_processes_verified") is True, "fresh-process verification missing")
    return validated
