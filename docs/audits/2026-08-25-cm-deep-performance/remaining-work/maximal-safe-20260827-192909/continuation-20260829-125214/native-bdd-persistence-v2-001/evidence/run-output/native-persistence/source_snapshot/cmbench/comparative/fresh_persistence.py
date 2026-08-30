"""Fresh-process structural persistence controls and native graph adapters.

The build worker writes only a reconstructable representation.  A distinct
reload worker reads that artifact and computes exact bounded relations.  The
portable ``dd.autoref`` arm is deliberately labelled as a control and never as
native CUDD.  Native ZDD is serialized as a bounded reachable graph because
``dd.cudd_zdd`` does not implement ``load``.  Native and portable BDDs also
use a canonical reachable graph so equivalent builds have stable bytes across
processes.  d4 output is bundled as its arc-literal d-DNNF and replayed without
invoking the producer.
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
import subprocess
import sys
import tempfile
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
ZDD_ARMS = ("cudd_zdd",)
D4_ARMS = ("d4_ddnnf",)
OPTIONAL_NATIVE_ARMS = ZDD_ARMS + D4_ARMS
ARMS = STANDARD_ARMS + BDD_ARMS + OPTIONAL_NATIVE_ARMS
MAX_ARTIFACT_BYTES = 8 << 20
MAX_REQUEST_BYTES = 1 << 20
ARTIFACT_NAME = re.compile(r"cell-[A-Za-z0-9_.+-]{1,160}\.json")
SHA256 = re.compile(r"[0-9a-f]{64}")
D4_SOURCE_RELATIVE_PATH = Path("external/d4")
D4_SOURCE_COMMIT = "333370cc1e843dd0749c1efe88516e72b5239174"
D4_BINARY_ENV = "CM_D4_DDNNF_BINARY"
D4_SHA256_ENV = "CM_D4_DDNNF_SHA256"
D4_ALLOWED_ROOT_ENV = "CM_D4_DDNNF_ALLOWED_ROOT"
BDD_SCHEMA = "cm-bdd-reachable-graph/v1"
ZDD_SCHEMA = "cm-cudd-zdd-reachable-graph/v1"
D4_SCHEMA = "cm-d4-ddnnf-bundle/v1"
MAX_NATIVE_STDOUT_BYTES = 256 << 10


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
        "reason": (
            "native_cudd_canonical_reachable_graph_adapter"
            if native_cudd
            else "native_cudd_extension_unavailable"
        ),
        "native_execution": bool(native_cudd),
        "portability_control": False,
        "identity": cudd,
    }
    zdd = _module_identity("dd", "dd.cudd_zdd")
    native_zdd = zdd.get("status") == "identified" and zdd.get("native_extension") is True
    available["cudd_zdd"] = {
        "status": "available" if native_zdd else "refused",
        "reason": "native_cudd_zdd_reachable_graph_adapter" if native_zdd else "native_cudd_zdd_extension_unavailable",
        "native_execution": bool(native_zdd),
        "portability_control": False,
        "identity": zdd,
    }
    d4 = _d4_identity()
    native_d4 = d4.get("status") == "identified"
    available["d4_ddnnf"] = {
        "status": "available" if native_d4 else "refused",
        "reason": "native_d4_arc_literal_ddnnf_adapter" if native_d4 else d4["reason"],
        "native_execution": bool(native_d4),
        "portability_control": False,
        "identity": d4,
    }
    require(tuple(available) == ARMS, "capability inventory order")
    return available


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _d4_identity() -> dict[str, Any]:
    if not sys.platform.startswith("linux"):
        return {
            "status": "unavailable",
            "reason": "d4_ddnnf_compiler_requires_linux_x86_64",
            "source_commit": D4_SOURCE_COMMIT,
        }
    configured_path = os.environ.get(D4_BINARY_ENV)
    configured_sha256 = os.environ.get(D4_SHA256_ENV)
    if not configured_path or not configured_sha256:
        return {
            "status": "unavailable",
            "reason": "d4_ddnnf_runtime_binding_unavailable",
            "source_commit": D4_SOURCE_COMMIT,
        }
    path = Path(configured_path)
    allowed_root = Path(os.environ.get(D4_ALLOWED_ROOT_ENV, str(_project_root()))).resolve()
    if (
        not path.is_absolute()
        or not path.is_file()
        or path.is_symlink()
        or not path.resolve().is_relative_to(allowed_root)
        or SHA256.fullmatch(configured_sha256) is None
    ):
        return {
            "status": "unavailable",
            "reason": "d4_ddnnf_runtime_binding_invalid",
            "source_commit": D4_SOURCE_COMMIT,
        }
    path = path.resolve()
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != configured_sha256 or not payload.startswith(b"\x7fELF\x02\x01\x01"):
        return {
            "status": "unavailable",
            "reason": "d4_ddnnf_runtime_identity_mismatch",
            "required_sha256": configured_sha256,
            "observed_sha256": digest,
            "source_commit": D4_SOURCE_COMMIT,
        }
    return {
        "status": "identified",
        "kind": "native_linux_x86_64_elf",
        "file": path.name,
        "bytes": len(payload),
        "path": str(path),
        "sha256": digest,
        "source_commit": D4_SOURCE_COMMIT,
        "cli_contract": "legacy_d4_-dDNNF_-out",
    }


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


def _bdd_graph(manager: Any, roots: Mapping[str, Any], k: int) -> dict[str, Any]:
    """Serialize a deterministic reachable BDD graph without cached answers."""
    variables = [manager.var_at_level(level) for level in range(k)]
    require(set(variables) == {f"x{index}" for index in range(k)}, "BDD variable universe")
    nodes: dict[str, list[Any]] = {}
    memo: dict[Any, Any] = {}

    def visit(node: Any) -> Any:
        if node == manager.false:
            return "F"
        if node == manager.true:
            return "T"
        if node in memo:
            return memo[node]
        if getattr(node, "negated", False):
            level, low, high = manager.succ(~node)
            low, high = ~low, ~high
        else:
            level, low, high = manager.succ(node)
        require(
            type(level) is int
            and 0 <= level < k
            and low is not None
            and high is not None,
            "invalid BDD node",
        )
        low_ref, high_ref = visit(low), visit(high)
        identifier = len(nodes) + 1
        nodes[str(identifier)] = [level, low_ref, high_ref]
        memo[node] = identifier
        return identifier

    graph_roots = {name: visit(root) for name, root in roots.items()}
    return {
        "schema": BDD_SCHEMA,
        "k": k,
        "level_of_var": {name: level for level, name in enumerate(variables)},
        "roots": graph_roots,
        "nodes": nodes,
    }


def _load_bdd_roots(payload: bytes, scenario: Mapping[str, Any], manager: Any) -> dict[str, Any]:
    independent_bdd_rows(payload, scenario)
    data = _strict_json(payload)
    k = sessions.validate_scenario(scenario)
    manager.declare(*(f"x{index}" for index in range(k)))
    if hasattr(manager, "configure"):
        manager.configure(reordering=False)
    resolved: dict[Any, Any] = {"F": manager.false, "T": manager.true}
    for identifier in range(1, len(data["nodes"]) + 1):
        level, low, high = data["nodes"][str(identifier)]
        require(low in resolved and high in resolved, "BDD graph is not postordered")
        variable = manager.var(f"x{level}")
        resolved[identifier] = manager.ite(variable, resolved[high], resolved[low])
    return {name: resolved[reference] for name, reference in data["roots"].items()}


def _zdd_class() -> tuple[type[Any], dict[str, Any]]:
    identity = _module_identity("dd", "dd.cudd_zdd")
    require(
        identity.get("status") == "identified" and identity.get("native_extension") is True,
        "native CUDD ZDD extension required",
    )
    module = importlib.import_module("dd.cudd_zdd")
    return module.ZDD, identity


def _zdd_graph(manager: Any, roots: Mapping[str, Any], k: int) -> dict[str, Any]:
    """Serialize the reachable native ZDD graph without cached answers."""
    variables = [manager.var_at_level(level) for level in range(k)]
    require(set(variables) == {f"x{index}" for index in range(k)}, "ZDD variable universe")
    nodes: dict[str, list[Any]] = {}
    memo: dict[Any, Any] = {}

    def visit(node: Any) -> Any:
        if node == manager.false:
            return "F"
        if node == manager.true_node:
            return "T"
        if node in memo:
            return memo[node]
        level, low, high = manager.succ(node)
        require(
            type(level) is int
            and 0 <= level < k
            and low is not None
            and high is not None,
            "invalid native ZDD node",
        )
        low_ref, high_ref = visit(low), visit(high)
        identifier = len(nodes) + 1
        nodes[str(identifier)] = [level, low_ref, high_ref]
        memo[node] = identifier
        return identifier

    graph_roots = {name: visit(root) for name, root in roots.items()}
    return {
        "schema": ZDD_SCHEMA,
        "k": k,
        "level_of_var": {name: level for level, name in enumerate(variables)},
        "roots": graph_roots,
        "nodes": nodes,
    }


def independent_zdd_rows(payload: bytes, scenario: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Replay a reachable ZDD graph without importing CUDD or ``dd``."""
    k = sessions.validate_scenario(scenario)
    data = _strict_json(payload)
    require(
        isinstance(data, Mapping)
        and set(data) == {"schema", "k", "level_of_var", "roots", "nodes"}
        and data.get("schema") == ZDD_SCHEMA
        and data.get("k") == k,
        "ZDD graph fields",
    )
    levels = data["level_of_var"]
    require(
        isinstance(levels, Mapping)
        and levels == {f"x{index}": index for index in range(k)},
        "ZDD variable order",
    )
    expected_names = [f"v{index:03}" for index in range(len(scenario["versions"]))]
    roots, nodes = data["roots"], data["nodes"]
    require(isinstance(roots, Mapping) and list(roots) == expected_names, "ZDD root identity/order")
    require(isinstance(nodes, Mapping) and len(nodes) <= 1 << (k + 1), "ZDD node bound")
    expected_ids = {str(index) for index in range(1, len(nodes) + 1)}
    require(set(nodes) == expected_ids, "ZDD node identifiers")
    active: set[int] = set()
    reached: set[int] = set()

    def node_row(reference: Any, parent_level: int = -1) -> tuple[int, Any, Any] | None:
        if reference in {"F", "T"}:
            return None
        require(type(reference) is int and 1 <= reference <= len(nodes), "invalid ZDD reference")
        row = nodes[str(reference)]
        require(
            isinstance(row, list)
            and len(row) == 3
            and type(row[0]) is int
            and parent_level < row[0] < k,
            "ZDD order violation",
        )
        return row[0], row[1], row[2]

    def validate(reference: Any, parent_level: int = -1) -> None:
        row = node_row(reference, parent_level)
        if row is None:
            return
        identifier = int(reference)
        require(identifier not in active, "cyclic ZDD graph")
        if identifier in reached:
            return
        active.add(identifier)
        level, low, high = row
        validate(low, level)
        validate(high, level)
        active.remove(identifier)
        reached.add(identifier)

    for reference in roots.values():
        validate(reference)
    require(reached == {int(item) for item in expected_ids}, "unreachable ZDD nodes")

    def evaluate(reference: Any, assignment: int, level: int) -> bool:
        if reference == "F":
            return False
        if reference == "T":
            return assignment >> level == 0
        row = node_row(reference, level - 1)
        require(row is not None, "ZDD node expected")
        node_level, low, high = row
        skipped_mask = ((1 << node_level) - 1) ^ ((1 << level) - 1)
        if assignment & skipped_mask:
            return False
        child = high if (assignment >> node_level) & 1 else low
        return evaluate(child, assignment, node_level + 1)

    rows = []
    for index, name in enumerate(expected_names):
        relation = sum(
            int(evaluate(roots[name], assignment, 0)) << assignment
            for assignment in range(1 << k)
        )
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


def _load_zdd_roots(payload: bytes, scenario: Mapping[str, Any], manager: Any) -> dict[str, Any]:
    independent_zdd_rows(payload, scenario)
    data = _strict_json(payload)
    k = sessions.validate_scenario(scenario)
    manager.declare(*(f"x{index}" for index in range(k)))
    if hasattr(manager, "configure"):
        manager.configure(reordering=False)
    resolved: dict[Any, Any] = {"F": manager.false, "T": manager.true_node}
    for identifier in range(1, len(data["nodes"]) + 1):
        level, low, high = data["nodes"][str(identifier)]
        require(low in resolved and high in resolved, "ZDD graph is not postordered")
        resolved[identifier] = manager.find_or_add(
            f"x{level}", resolved[low], resolved[high]
        )
    return {name: resolved[reference] for name, reference in data["roots"].items()}


def _parse_ddnnf(text: str, k: int) -> tuple[dict[int, str], dict[int, list[tuple[int, tuple[int, ...]]]]]:
    require(isinstance(text, str) and 0 < len(text.encode("ascii")) <= MAX_ARTIFACT_BYTES, "d-DNNF text bound")
    nodes: dict[int, str] = {}
    edges: dict[int, list[tuple[int, tuple[int, ...]]]] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        fields = line.split()
        require(fields and fields[-1] == "0", f"d-DNNF missing terminator line {number}")
        if fields[0] in {"a", "o", "t", "f"}:
            require(len(fields) == 3, "certified/extended d-DNNF node not admitted")
            identifier = int(fields[1])
            require(identifier > 0 and identifier not in nodes, "duplicate/invalid d-DNNF node")
            nodes[identifier] = fields[0]
        else:
            integers = [int(field) for field in fields]
            require(len(integers) >= 3 and integers[0] > 0 and integers[1] > 0, "invalid d-DNNF arc")
            literals = tuple(integers[2:-1])
            require(all(1 <= abs(literal) <= k for literal in literals), "d-DNNF literal outside universe")
            require(len({abs(literal) for literal in literals}) == len(literals), "duplicate d-DNNF guard variable")
            edges.setdefault(integers[0], []).append((integers[1], literals))
    require(1 in nodes, "missing d4 root 1")
    for parent, children in edges.items():
        require(parent in nodes and nodes[parent] in {"a", "o"}, "invalid d-DNNF arc source")
        require(all(child in nodes for child, _ in children), "dangling d-DNNF arc")
    return nodes, edges


def _ddnnf_relation(text: str, k: int) -> tuple[int, dict[str, int]]:
    nodes, edges = _parse_ddnnf(text, k)
    full = (1 << (1 << k)) - 1
    columns = tuple(
        sum(1 << assignment for assignment in range(1 << k) if (assignment >> variable) & 1)
        for variable in range(k)
    )
    cache: dict[int, tuple[int, frozenset[int], int]] = {}
    active: set[int] = set()
    deterministic, decomposable = 0, 0

    def visit(identifier: int) -> tuple[int, frozenset[int], int]:
        nonlocal deterministic, decomposable
        if identifier in cache:
            return cache[identifier]
        require(identifier not in active, "cyclic d-DNNF")
        active.add(identifier)
        kind = nodes[identifier]
        if kind in {"t", "f"}:
            result = (full if kind == "t" else 0, frozenset(), 1 if kind == "t" else 0)
        else:
            branches = []
            for child, literals in edges.get(identifier, []):
                value, support, count = visit(child)
                guard_support = frozenset(abs(literal) - 1 for literal in literals)
                require(not support & guard_support, "d-DNNF guard/child support overlap")
                for literal in literals:
                    column = columns[abs(literal) - 1]
                    value &= column if literal > 0 else full ^ column
                branches.append((value, support | guard_support, count))
            require(branches, "d-DNNF internal node without arcs")
            support = frozenset().union(*(branch[1] for branch in branches))
            if kind == "o":
                value, count = 0, 0
                for branch_value, branch_support, branch_count in branches:
                    require(not value & branch_value, "d-DNNF OR branches are not deterministic")
                    value |= branch_value
                    count += branch_count << (len(support) - len(branch_support))
                deterministic += 1
            else:
                value, count, used = full, 1, frozenset()
                for branch_value, branch_support, branch_count in branches:
                    require(not used & branch_support, "d-DNNF AND children are not decomposable")
                    used |= branch_support
                    value &= branch_value
                    count *= branch_count
                decomposable += 1
            result = value, support, count
        active.remove(identifier)
        cache[identifier] = result
        return result

    relation, support, root_count = visit(1)
    require(set(cache) == set(nodes), "unreachable d-DNNF nodes")
    full_count = root_count << (k - len(support))
    require(relation.bit_count() == full_count, "d-DNNF structural count mismatch")
    return relation, {
        "serialized_nodes": len(nodes),
        "serialized_edges": sum(len(rows) for rows in edges.values()),
        "deterministic_or_nodes_checked": deterministic,
        "decomposable_and_nodes_checked": decomposable,
    }


def independent_ddnnf_rows(payload: bytes, scenario: Mapping[str, Any]) -> list[dict[str, Any]]:
    k = sessions.validate_scenario(scenario)
    data = _strict_json(payload)
    require(
        isinstance(data, Mapping)
        and set(data) == {"schema", "k", "variable_order", "versions"}
        and data.get("schema") == D4_SCHEMA
        and data.get("k") == k
        and data.get("variable_order") == [f"x{index}" for index in range(k)],
        "d4 d-DNNF bundle fields",
    )
    versions = data["versions"]
    require(isinstance(versions, list) and len(versions) == len(scenario["versions"]), "d-DNNF version count")
    rows = []
    for index, item in enumerate(versions):
        require(
            isinstance(item, Mapping)
            and set(item) == {"id", "nnf", "sha256"}
            and item.get("id") == scenario["versions"][index]["id"]
            and isinstance(item.get("nnf"), str)
            and isinstance(item.get("sha256"), str)
            and SHA256.fullmatch(item["sha256"]) is not None,
            "d-DNNF version identity",
        )
        nnf_payload = item["nnf"].encode("ascii")
        require(hashlib.sha256(nnf_payload).hexdigest() == item["sha256"], "d-DNNF payload hash")
        relation, _metrics = _ddnnf_relation(item["nnf"], k)
        rows.append(
            {
                "version": index,
                "version_id": item["id"],
                "relation_hex": hex(relation),
                "relation_sha256": semantic_sha256(relation, k),
                "satisfying_assignments": relation.bit_count(),
            }
        )
    return rows


def _dimacs(version: Mapping[str, Any], k: int) -> bytes:
    clauses = version["clauses"]
    lines = [f"p cnf {k} {len(clauses)}"]
    lines.extend(" ".join(str(literal) for literal in clause) + (" " if clause else "") + "0" for clause in clauses)
    return ("\n".join(lines) + "\n").encode("ascii")


def _build_d4_bundle(scenario: Mapping[str, Any], identity: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    k = sessions.validate_scenario(scenario)
    binary = Path(identity.get("path", ""))
    require(
        identity.get("status") == "identified"
        and binary.is_absolute()
        and binary.resolve().is_relative_to(
            Path(os.environ.get(D4_ALLOWED_ROOT_ENV, str(_project_root()))).resolve()
        )
        and sha256_file(binary) == identity.get("sha256"),
        "d4 binary identity",
    )
    binary.chmod(0o700)
    versions = []
    executions = []
    with tempfile.TemporaryDirectory(prefix="cm-d4-ddnnf-") as directory:
        root = Path(directory)
        for index, version in enumerate(scenario["versions"]):
            source, target = root / f"v{index:03}.cnf", root / f"v{index:03}.nnf"
            source.write_bytes(_dimacs(version, k))
            command = [str(binary), "-dDNNF", str(source), f"-out={target}"]
            started = time.perf_counter_ns()
            result = subprocess.run(
                command,
                cwd=_project_root(),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
                check=False,
            )
            elapsed = time.perf_counter_ns() - started
            require(
                result.returncode == 0
                and len(result.stdout) <= MAX_NATIVE_STDOUT_BYTES
                and len(result.stderr) <= MAX_NATIVE_STDOUT_BYTES
                and target.is_file()
                and not target.is_symlink(),
                "d4 d-DNNF compilation failed",
            )
            nnf_payload = target.read_bytes()
            require(0 < len(nnf_payload) <= MAX_ARTIFACT_BYTES, "d4 d-DNNF output bound")
            nnf = nnf_payload.decode("ascii")
            _parse_ddnnf(nnf, k)
            versions.append({"id": version["id"], "nnf": nnf, "sha256": hashlib.sha256(nnf_payload).hexdigest()})
            executions.append({"version": index, "wall_ns": elapsed, "returncode": result.returncode})
    return {
        "schema": D4_SCHEMA,
        "k": k,
        "variable_order": [f"x{index}" for index in range(k)],
        "versions": versions,
    }, executions


def build_artifact(
    scenario: Mapping[str, Any], arm: str, artifact_path: Path, *, clock=time.perf_counter_ns
) -> dict[str, Any]:
    """Build and exclusively write one answer-cache-free artifact."""
    sessions.validate_scenario(scenario)
    require(arm in STANDARD_ARMS + BDD_ARMS + OPTIONAL_NATIVE_ARMS, "arm has no executable persistence adapter")
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
    elif arm in BDD_ARMS:
        bdd_type, module_identity = _bdd_class(arm)
        manager = bdd_type()
        if hasattr(manager, "configure"):
            manager.configure(reordering=False)
        roots = _bdd_roots(manager, scenario)
        built = clock()
        graph = _bdd_graph(manager, roots, sessions.validate_scenario(scenario))
        payload = canonical_bytes(graph)
        _exclusive_write(artifact_path, payload)
        serialized = clock()
        identity = {
            "adapter": "canonical_bdd_reachable_graph/v1",
            "backend": arm,
            "native_execution": arm == "cudd_bdd",
            "portability_control": arm == "autoref_bdd_control",
            "module": module_identity,
            "roots": list(roots),
            "serialized_nodes": len(graph["nodes"]),
        }
    elif arm in ZDD_ARMS:
        zdd_type, module_identity = _zdd_class()
        manager = zdd_type()
        if hasattr(manager, "configure"):
            manager.configure(reordering=False)
        roots = _bdd_roots(manager, scenario)
        built = clock()
        graph = _zdd_graph(manager, roots, sessions.validate_scenario(scenario))
        payload = canonical_bytes(graph)
        _exclusive_write(artifact_path, payload)
        serialized = clock()
        identity = {
            "adapter": "cudd_zdd_reachable_graph/v1",
            "backend": arm,
            "native_execution": True,
            "portability_control": False,
            "module": module_identity,
            "roots": list(roots),
            "serialized_nodes": len(graph["nodes"]),
        }
    else:
        module_identity = _d4_identity()
        require(module_identity.get("status") == "identified", "pinned native d4 required")
        bundle, executions = _build_d4_bundle(scenario, module_identity)
        built = clock()
        payload = canonical_bytes(bundle)
        _exclusive_write(artifact_path, payload)
        serialized = clock()
        identity = {
            "adapter": "d4_arc_literal_ddnnf_bundle/v1",
            "backend": arm,
            "native_execution": True,
            "portability_control": False,
            "binary": module_identity,
            "executions": executions,
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
    require(arm in STANDARD_ARMS + BDD_ARMS + OPTIONAL_NATIVE_ARMS, "arm has no executable persistence adapter")
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
    elif arm in BDD_ARMS:
        bdd_type, module_identity = _bdd_class(arm)
        manager = bdd_type()
        loaded = _load_bdd_roots(payload, scenario, manager)
        reconstructed = clock()
        rows = _bdd_rows(manager, loaded, scenario)
        identity = {
            "adapter": "canonical_bdd_reachable_graph_reload/v1",
            "backend": arm,
            "native_execution": arm == "cudd_bdd",
            "portability_control": arm == "autoref_bdd_control",
            "module": module_identity,
        }
    elif arm in ZDD_ARMS:
        zdd_type, module_identity = _zdd_class()
        manager = zdd_type()
        roots = _load_zdd_roots(payload, scenario, manager)
        reconstructed = clock()
        rows = _bdd_rows(manager, roots, scenario)
        identity = {
            "adapter": "cudd_zdd_reachable_graph_reload/v1",
            "backend": arm,
            "native_execution": True,
            "portability_control": False,
            "module": module_identity,
        }
    else:
        rows = independent_ddnnf_rows(payload, scenario)
        reconstructed = clock()
        identity = {
            "adapter": "bounded_arc_literal_ddnnf_reload/v1",
            "backend": arm,
            "native_execution": False,
            "native_build_required": True,
            "portability_control": False,
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
    """Replay a canonical reachable BDD graph without importing ``dd``."""
    k = sessions.validate_scenario(scenario)
    data = _strict_json(payload)
    require(
        isinstance(data, Mapping)
        and set(data) == {"schema", "k", "level_of_var", "roots", "nodes"}
        and data.get("schema") == BDD_SCHEMA
        and data.get("k") == k,
        "BDD graph fields",
    )
    expected_names = [f"v{index:03}" for index in range(len(scenario["versions"]))]
    levels = data["level_of_var"]
    require(
        isinstance(levels, Mapping)
        and levels == {f"x{index}": index for index in range(k)},
        "BDD variable order",
    )
    roots, nodes = data["roots"], data["nodes"]
    require(isinstance(roots, Mapping) and list(roots) == expected_names, "BDD graph root identity/order")
    require(isinstance(nodes, Mapping) and len(nodes) <= 1 << (k + 1), "BDD node bound")
    expected_ids = {str(index) for index in range(1, len(nodes) + 1)}
    require(set(nodes) == expected_ids, "BDD node identifiers")
    active: set[int] = set()
    reached: set[int] = set()

    def node_row(reference: Any, parent_level: int = -1) -> tuple[int, Any, Any] | None:
        if reference in {"F", "T"}:
            return None
        require(type(reference) is int and 1 <= reference <= len(nodes), "invalid BDD reference")
        row = nodes[str(reference)]
        require(
            isinstance(row, list)
            and len(row) == 3
            and type(row[0]) is int
            and parent_level < row[0] < k,
            "BDD order violation",
        )
        return row[0], row[1], row[2]

    def validate(reference: Any, parent_level: int = -1) -> None:
        row = node_row(reference, parent_level)
        if row is None:
            return
        identifier = int(reference)
        require(identifier not in active, "cyclic BDD graph")
        if identifier in reached:
            return
        active.add(identifier)
        level, low, high = row
        validate(low, level)
        validate(high, level)
        active.remove(identifier)
        reached.add(identifier)

    for reference in roots.values():
        validate(reference)
    require(reached == {int(item) for item in expected_ids}, "unreachable BDD nodes")

    def evaluate(reference: Any, assignment: int) -> bool:
        if reference == "F":
            return False
        if reference == "T":
            return True
        row = node_row(reference)
        require(row is not None, "BDD node expected")
        level, low, high = row
        return evaluate(high if (assignment >> level) & 1 else low, assignment)

    rows = []
    for index, name in enumerate(expected_names):
        relation = sum(
            int(evaluate(roots[name], assignment)) << assignment
            for assignment in range(1 << k)
        )
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
    if arm in BDD_ARMS:
        return independent_bdd_rows(payload, scenario)
    if arm in ZDD_ARMS:
        return independent_zdd_rows(payload, scenario)
    require(arm in D4_ARMS, "unreviewed artifact replay arm")
    return independent_ddnnf_rows(payload, scenario)


def worker_request(payload: bytes) -> dict[str, Any]:
    require(isinstance(payload, bytes) and 0 < len(payload) <= MAX_REQUEST_BYTES, "worker request bound")
    request = _strict_json(payload)
    require(isinstance(request, Mapping), "worker request object")
    fields = {"schema", "mode", "arm", "scenario", "artifact_path"}
    if request.get("mode") == "reload_query":
        fields.add("artifact_sha256")
    require(set(request) == fields and request.get("schema") == REQUEST_SCHEMA, "worker request fields")
    require(request.get("mode") in {"build", "reload_query"}, "worker mode")
    require(request.get("arm") in STANDARD_ARMS + BDD_ARMS + OPTIONAL_NATIVE_ARMS, "worker arm")
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
