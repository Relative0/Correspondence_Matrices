"""Correctness-gated real feature-model history / local-neighborhood pilot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import platform
import random
import re
import statistics
import subprocess
import sys
import time
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Callable, Iterable


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from bitset_backend import _eval_words, compile_expr_cse, get_flat_program, program_metrics  # noqa: E402
from cm_exprlib import And, Expr, Not, Or, Var  # noqa: E402
from cm_ir import clear_cm_ir_persistent_cache, compile_expr_to_cm_ir  # noqa: E402

import numpy as np  # noqa: E402

if TYPE_CHECKING:
    from pysat.solvers import Solver


SOURCE_URL = "https://github.com/SoftVarE-Group/feature-model-benchmark.git"
SOURCE_COMMIT = "afa60ee2c836e7bdc4068e0f4f128ea31158d2ad"
DEFAULT_SOURCE = Path(os.environ.get(
    "CM_FM_BENCHMARK_SOURCE",
    Path(os.environ.get("TEMP", str(HERE))) / "codex-cm-feature-model-benchmark-20260827",
))
DEFAULT_OUTPUT = HERE / "runs" / "configuration-fm-history-pilot-2026-08-27"
SLICE_SIZE = 8
PACKED_WIDTH = 1 << SLICE_SIZE
PACKED_MASK = (1 << PACKED_WIDTH) - 1
ROUNDS = 7
PACKED_BATCH = 200
BOOTSTRAP_DRAWS = 4000
BOOTSTRAP_SEED = 2026082702
MODEL_COMMENT = re.compile(rb"^c\s+(\d+)\s+(.+?)\s*$")


@dataclass(frozen=True)
class TreeEntry:
    mode: str
    kind: str
    sha: str
    name: str


@dataclass(frozen=True)
class SelectedModel:
    history: str
    version: str
    ordinal: int
    domain: str
    origin: str
    metadata_path: str
    metadata_features: str
    metadata_clauses: str
    transition_labels: tuple[str, ...]

    @property
    def model_id(self) -> str:
        return f"{self.history}@{self.version}"


@dataclass
class ParsedCNF:
    n_vars: int
    clauses: list[tuple[int, ...]]
    feature_names: dict[int, str]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def git_run(source: Path, args: list[str], *, check: bool = True, no_lazy: bool = False) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if no_lazy:
        env["GIT_NO_LAZY_FETCH"] = "1"
    return subprocess.run(
        ["git", "-C", str(source), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        env=env,
    )


def object_present(source: Path, sha: str) -> bool:
    result = git_run(source, ["cat-file", "-e", sha], check=False, no_lazy=True)
    return result.returncode == 0


def ensure_object(source: Path, sha: str) -> None:
    if object_present(source, sha):
        return
    # GitHub does not advertise arbitrary blob IDs as fetchable revisions. In
    # a promisor partial clone, asking cat-file for the exact tree-selected
    # object is the supported lazy-fetch path; Git verifies the returned
    # object's SHA-1 before placing it in the object database.
    fetched = git_run(source, ["cat-file", "-e", sha], check=False)
    if not object_present(source, sha):
        stderr = fetched.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"could not lazy-fetch Git object {sha}: {stderr}")


def tree_entries(source: Path, tree_sha: str) -> list[TreeEntry]:
    ensure_object(source, tree_sha)
    raw = git_run(source, ["ls-tree", "-z", tree_sha], no_lazy=True).stdout
    result = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        metadata, name = item.split(b"\t", 1)
        mode, kind, sha = metadata.decode("ascii").split()
        result.append(TreeEntry(mode, kind, sha, name.decode("utf-8")))
    return result


def root_tree(source: Path) -> str:
    commit = git_run(source, ["rev-parse", "HEAD"], no_lazy=True).stdout.decode().strip()
    if commit != SOURCE_COMMIT:
        raise RuntimeError(f"source HEAD is {commit}, expected {SOURCE_COMMIT}")
    return git_run(source, ["rev-parse", f"{SOURCE_COMMIT}^{{tree}}"], no_lazy=True).stdout.decode().strip()


def resolve_tree(source: Path, root_sha: str, parts: Iterable[str]) -> str:
    current = root_sha
    for part in parts:
        matches = [entry for entry in tree_entries(source, current) if entry.name == part and entry.kind == "tree"]
        if len(matches) != 1:
            raise FileNotFoundError(f"tree component {part!r} not found below {current}")
        current = matches[0].sha
    return current


def load_metadata(source: Path) -> list[dict[str, str]]:
    path = source / "statistics" / "Complete.csv"
    if not path.is_file():
        raise FileNotFoundError(f"missing source metadata: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def select_models(rows: list[dict[str, str]]) -> tuple[list[SelectedModel], list[dict]]:
    histories: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("PartOfHistory") == "True":
            histories[row["Name"]].append(row)
    if len(histories) != 7:
        raise ValueError(f"expected seven corpus histories, found {len(histories)}")

    selected: list[SelectedModel] = []
    transitions_out = []
    for history, versions in histories.items():
        n_versions = len(versions)
        if n_versions < 2:
            raise ValueError(f"history {history!r} has fewer than two versions")
        later_ordinals = sorted({1, n_versions // 2, n_versions - 1})
        transition_labels_by_endpoint: dict[int, list[str]] = defaultdict(list)
        history_transitions = []
        for later in later_ordinals:
            label = "first" if later == 1 else "last" if later == n_versions - 1 else "middle"
            transition_labels_by_endpoint[later - 1].append(label)
            transition_labels_by_endpoint[later].append(label)
            history_transitions.append({
                "label": label,
                "earlier_ordinal": later - 1,
                "later_ordinal": later,
                "earlier_version": versions[later - 1]["Version"],
                "later_version": versions[later]["Version"],
            })
        for ordinal in sorted(transition_labels_by_endpoint):
            row = versions[ordinal]
            selected.append(SelectedModel(
                history=history,
                version=row["Version"],
                ordinal=ordinal,
                domain=row["Domain"],
                origin=row["Origin"],
                metadata_path=row["Path"],
                metadata_features=row["NumberOfFeatures"],
                metadata_clauses=row["NumberOfClauses"],
                transition_labels=tuple(transition_labels_by_endpoint[ordinal]),
            ))
        transitions_out.append({
            "history": history,
            "version_count": n_versions,
            "ordering_basis": "Complete.csv row order with explicit Version field",
            "transitions": history_transitions,
        })
    return selected, transitions_out


def payload_entry(source: Path, tree_root: str, model: SelectedModel) -> tuple[str, TreeEntry]:
    locations = [
        ("derived_dimacs", ("feature_models", "dimacs", model.domain, model.history)),
        ("source_original", ("feature_models", "original", model.domain, model.history)),
    ]
    for location, parts in locations:
        try:
            directory = resolve_tree(source, tree_root, parts)
        except FileNotFoundError:
            continue
        candidates = [
            entry for entry in tree_entries(source, directory)
            if entry.kind == "blob"
            and model.version in entry.name
            and (entry.name.endswith(".dimacs") or entry.name.endswith(".dimacs.zip"))
        ]
        if len(candidates) == 1:
            return location, candidates[0]
        if len(candidates) > 1:
            raise ValueError(f"ambiguous payload for {model.model_id}: {[item.name for item in candidates]}")
    raise FileNotFoundError(f"no DIMACS payload found for {model.model_id}")


def safe_dimacs_from_blob(source: Path, payload_dir: Path, entry: TreeEntry) -> tuple[Path, dict]:
    ensure_object(source, entry.sha)
    raw = git_run(source, ["cat-file", "blob", entry.sha], no_lazy=True).stdout
    raw_sha256 = sha256_bytes(raw)
    payload_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".dimacs.zip" if entry.name.endswith(".zip") else ".dimacs"
    stored = payload_dir / f"{entry.sha}{suffix}"
    if stored.exists():
        if sha256_file(stored) != raw_sha256:
            raise RuntimeError(f"cached payload checksum mismatch: {stored}")
    else:
        stored.write_bytes(raw)

    archive_member = None
    dimacs_bytes = raw
    dimacs_path = stored
    if entry.name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = [item for item in archive.infolist() if not item.is_dir() and item.filename.endswith(".dimacs")]
            if len(members) != 1:
                raise ValueError(f"archive {entry.name!r} has {len(members)} DIMACS members")
            member = members[0]
            pure = PurePosixPath(member.filename)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError(f"unsafe archive member: {member.filename!r}")
            archive_member = member.filename
            dimacs_bytes = archive.read(member)
        dimacs_path = payload_dir / f"{entry.sha}.extracted.dimacs"
        extracted_sha = sha256_bytes(dimacs_bytes)
        if dimacs_path.exists():
            if sha256_file(dimacs_path) != extracted_sha:
                raise RuntimeError(f"cached extracted payload checksum mismatch: {dimacs_path}")
        else:
            dimacs_path.write_bytes(dimacs_bytes)

    return dimacs_path, {
        "git_blob_sha1": entry.sha,
        "source_filename": entry.name,
        "raw_size_bytes": len(raw),
        "raw_sha256": raw_sha256,
        "archive_member": archive_member,
        "dimacs_size_bytes": len(dimacs_bytes),
        "dimacs_sha256": sha256_bytes(dimacs_bytes),
        "cache_filename": dimacs_path.name,
    }


def acquire(
    source: Path,
    output: Path,
    limit_models: int,
    diagnostic_model_ids: tuple[str, ...] = (),
) -> tuple[list[dict], dict]:
    rows = load_metadata(source)
    selected, transitions = select_models(rows)
    if diagnostic_model_ids:
        requested = set(diagnostic_model_ids)
        available = {model.model_id for model in selected}
        missing = sorted(requested - available)
        if missing:
            raise ValueError(f"diagnostic model IDs are not selected protocol endpoints: {missing}")
        selected = [model for model in selected if model.model_id in requested]
    if limit_models:
        selected = selected[:limit_models]
    root = root_tree(source)
    payload_dir = source / "selected_payloads"
    payloads = []
    for model in selected:
        location, entry = payload_entry(source, root, model)
        dimacs_path, artifact = safe_dimacs_from_blob(source, payload_dir, entry)
        payloads.append({
            "model": model,
            "location": location,
            "dimacs_path": dimacs_path,
            "artifact": artifact,
        })

    tracked_inputs = {}
    for relative in ("statistics/Complete.csv", "statistics/Overview.csv", "README.md", "LICENSE"):
        path = source / relative
        tracked_inputs[relative] = {"size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
    provenance = {
        "schema_version": "1.0",
        "source_url": SOURCE_URL,
        "source_commit": SOURCE_COMMIT,
        "source_branch": "master",
        "acquisition_policy": "read-only exact Git objects; no source scripts executed",
        "selection_policy": "first, middle, and last adjacent transition per Complete.csv history",
        "diagnostic_limit_models": limit_models,
        "diagnostic_model_ids": list(diagnostic_model_ids),
        "tracked_inputs": tracked_inputs,
        "transitions": transitions,
        "selected_payloads": [
            {
                "model_id": item["model"].model_id,
                "history": item["model"].history,
                "version": item["model"].version,
                "ordinal": item["model"].ordinal,
                "transition_labels": item["model"].transition_labels,
                "source_location": item["location"],
                **item["artifact"],
            }
            for item in payloads
        ],
    }
    json_dump(output / "SOURCE-PROVENANCE.json", provenance)
    return payloads, provenance


def parse_dimacs(path: Path) -> ParsedCNF:
    n_vars = None
    expected_clauses = None
    clauses: list[tuple[int, ...]] = []
    pending: list[int] = []
    feature_names: dict[int, str] = {}
    header_seen = False
    with path.open("rb") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith(b"c"):
                match = MODEL_COMMENT.match(stripped)
                if match:
                    variable = int(match.group(1))
                    name = match.group(2).decode("utf-8", errors="replace").strip()
                    if name:
                        previous = feature_names.get(variable)
                        if previous is not None and previous != name:
                            raise ValueError(f"conflicting feature mapping for variable {variable}")
                        feature_names[variable] = name
                continue
            if stripped.startswith(b"p"):
                if header_seen or pending or clauses:
                    raise ValueError("invalid or repeated DIMACS header")
                parts = stripped.split()
                if len(parts) != 4 or parts[:2] != [b"p", b"cnf"]:
                    raise ValueError(f"unsupported DIMACS header: {stripped[:100]!r}")
                n_vars, expected_clauses = int(parts[2]), int(parts[3])
                header_seen = True
                continue
            if not header_seen:
                raise ValueError("clause data before DIMACS header")
            for token in stripped.split():
                literal = int(token)
                if literal == 0:
                    clauses.append(tuple(pending))
                    pending.clear()
                else:
                    pending.append(literal)
    if n_vars is None or expected_clauses is None:
        raise ValueError("missing DIMACS header")
    if pending:
        raise ValueError("unterminated final DIMACS clause")
    if len(clauses) != expected_clauses:
        raise ValueError(f"header declares {expected_clauses} clauses, parsed {len(clauses)}")
    if any(abs(literal) < 1 or abs(literal) > n_vars for clause in clauses for literal in clause):
        raise ValueError("literal outside declared variable range")
    feature_names = {variable: name for variable, name in feature_names.items() if 1 <= variable <= n_vars}
    return ParsedCNF(n_vars, clauses, feature_names)


def satisfying_product(parsed: ParsedCNF) -> tuple[dict[int, bool], Solver, int]:
    try:
        from pysat.solvers import Solver
    except ImportError as exc:  # pragma: no cover - exercised by CLI environment guard
        raise SystemExit(f"required existing benchmark dependency is unavailable: {exc}") from exc
    start = time.perf_counter_ns()
    solver = Solver(name="cadical195", bootstrap_with=parsed.clauses)
    construct_ns = time.perf_counter_ns() - start
    if not solver.solve():
        solver.delete()
        raise ValueError("native CaDiCaL reports UNSAT")
    model_literals = solver.get_model() or []
    product = {variable: False for variable in range(1, parsed.n_vars + 1)}
    for literal in model_literals:
        variable = abs(literal)
        if variable <= parsed.n_vars:
            product[variable] = literal > 0
    if not scalar_cnf(parsed.clauses, product):
        solver.delete()
        raise AssertionError("CaDiCaL model does not satisfy scalar CNF evaluator")
    return product, solver, construct_ns


def scalar_cnf(clauses: Iterable[tuple[int, ...]], assignment: dict[int, bool]) -> bool:
    return all(any(assignment[abs(literal)] == (literal > 0) for literal in clause) for clause in clauses)


def choose_slices(model_id: str, parsed: ParsedCNF) -> dict[str, tuple[int, ...]]:
    mapped = sorted(parsed.feature_names)
    if len(mapped) < SLICE_SIZE:
        raise ValueError(f"only {len(mapped)} original feature mappings")
    incidence = Counter(abs(literal) for clause in parsed.clauses for literal in clause)
    incidence_slice = tuple(sorted(mapped, key=lambda variable: (-incidence[variable], variable))[:SLICE_SIZE])
    hash_slice = tuple(sorted(
        mapped,
        key=lambda variable: hashlib.sha256(f"{model_id}|{variable}".encode()).digest(),
    )[:SLICE_SIZE])
    return {"incidence": incidence_slice, "hash": hash_slice}


def condition_cnf(
    clauses: Iterable[tuple[int, ...]],
    product: dict[int, bool],
    slice_variables: tuple[int, ...],
) -> tuple[tuple[tuple[int, ...], ...], dict]:
    local = {variable: index + 1 for index, variable in enumerate(slice_variables)}
    residual = []
    dropped = 0
    removed_literals = 0
    for clause in clauses:
        local_clause = []
        satisfied = False
        for literal in clause:
            variable = abs(literal)
            local_variable = local.get(variable)
            if local_variable is not None:
                local_clause.append(local_variable if literal > 0 else -local_variable)
            elif product[variable] == (literal > 0):
                satisfied = True
                break
            else:
                removed_literals += 1
        if satisfied:
            dropped += 1
            continue
        if not local_clause:
            raise AssertionError("conditioning produced an empty clause despite satisfying witness")
        residual.append(tuple(local_clause))
    return tuple(residual), {
        "source_clauses": len(list(clauses)) if not isinstance(clauses, list) else len(clauses),
        "dropped_satisfied_clauses": dropped,
        "removed_fixed_false_literals": removed_literals,
        "residual_clauses": len(residual),
        "residual_literals": sum(len(clause) for clause in residual),
    }


def balanced(nodes: list[Expr], constructor: Callable[[Expr, Expr], Expr]) -> Expr:
    if not nodes:
        raise ValueError("balanced expression requires at least one node")
    level = list(nodes)
    while len(level) > 1:
        next_level = []
        for index in range(0, len(level), 2):
            if index + 1 == len(level):
                next_level.append(level[index])
            else:
                next_level.append(constructor(level[index], level[index + 1]))
        level = next_level
    return level[0]


def expression_from_residual(residual: tuple[tuple[int, ...], ...]) -> Expr:
    variables = tuple(Var(index) for index in range(SLICE_SIZE))
    negatives = tuple(Not(variable) for variable in variables)
    if not residual:
        return Or(variables[0], negatives[0])
    clause_nodes = []
    for clause in residual:
        literals = [variables[abs(literal) - 1] if literal > 0 else negatives[abs(literal) - 1] for literal in clause]
        clause_nodes.append(balanced(literals, Or))
    return balanced(clause_nodes, And)


PATTERNS = tuple(sum(1 << assignment for assignment in range(PACKED_WIDTH) if (assignment >> index) & 1) for index in range(SLICE_SIZE))


def cnf_bitset(residual: tuple[tuple[int, ...], ...]) -> int:
    value = PACKED_MASK
    for clause in residual:
        clause_value = 0
        for literal in clause:
            pattern = PATTERNS[abs(literal) - 1]
            clause_value |= pattern if literal > 0 else (~pattern) & PACKED_MASK
        value &= clause_value
    return value


def cadical_bitset(solver: Solver, product: dict[int, bool], slice_variables: tuple[int, ...]) -> int:
    slice_set = set(slice_variables)
    outside = [variable if value else -variable for variable, value in product.items() if variable not in slice_set]
    value = 0
    for assignment in range(PACKED_WIDTH):
        assumptions = outside + [
            variable if (assignment >> index) & 1 else -variable
            for index, variable in enumerate(slice_variables)
        ]
        if solver.solve(assumptions=assumptions):
            value |= 1 << assignment
    return value


def witness_index(product: dict[int, bool], slice_variables: tuple[int, ...]) -> int:
    return sum((1 << index) for index, variable in enumerate(slice_variables) if product[variable])


def scalar_spotcheck(
    parsed: ParsedCNF,
    product: dict[int, bool],
    slice_variables: tuple[int, ...],
    packed: int,
) -> list[int]:
    indices = sorted({0, 1, 17, 127, 128, 255, witness_index(product, slice_variables)})
    for assignment_index in indices:
        assignment = dict(product)
        for index, variable in enumerate(slice_variables):
            assignment[variable] = bool((assignment_index >> index) & 1)
        expected = scalar_cnf(parsed.clauses, assignment)
        actual = bool((packed >> assignment_index) & 1)
        if expected != actual:
            raise AssertionError(f"scalar spot-check mismatch at assignment {assignment_index}")
    return indices


def timed_ns(function: Callable[[], object], batch: int) -> float:
    start = time.perf_counter_ns()
    for _ in range(batch):
        function()
    return (time.perf_counter_ns() - start) / batch


def geomean(values: Iterable[float]) -> float:
    values = list(values)
    if not values or any(value <= 0 or not math.isfinite(value) for value in values):
        raise ValueError("geomean requires positive finite values")
    return math.exp(statistics.fmean(math.log(value) for value in values))


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def clustered_summary(rows: list[dict], ratio_key: str) -> dict:
    by_history: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_history[row["history"]].append(float(row[ratio_key]))
    per_history = {history: geomean(values) for history, values in by_history.items()}
    histories = sorted(per_history)
    observed = geomean(per_history.values())
    rng = random.Random(BOOTSTRAP_SEED)
    draws = [geomean(per_history[rng.choice(histories)] for _ in histories) for _ in range(BOOTSTRAP_DRAWS)]
    return {
        "history_count": len(histories),
        "geomean": observed,
        "ci95": [percentile(draws, 0.025), percentile(draws, 0.975)],
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "per_history_geomean": per_history,
    }


def crossover_sessions(build_a: float, eval_a: float, build_b: float, eval_b: float) -> float | None:
    if eval_a >= eval_b:
        return 0.0 if build_a <= build_b else None
    return max(0.0, (build_a - build_b) / (eval_b - eval_a))


def encode_product(product: dict[int, bool], n_vars: int) -> bytes:
    value = sum(1 << (variable - 1) for variable, selected in product.items() if selected)
    return value.to_bytes((n_vars + 7) // 8, "little")


def run_benchmark(payloads: list[dict], rounds: int, packed_batch: int) -> tuple[list[dict], list[dict], dict]:
    clear_cm_ir_persistent_cache()
    raw_rows = []
    admissions = []
    model_clause_sets: dict[str, set[tuple[int, ...]]] = {}
    model_feature_sets: dict[str, set[str]] = {}
    witnesses = []
    admitted_payloads = 0

    for model_index, item in enumerate(payloads):
        model: SelectedModel = item["model"]
        path: Path = item["dimacs_path"]
        parse_start = time.perf_counter_ns()
        try:
            parsed = parse_dimacs(path)
        except Exception as exc:
            admissions.append({"model_id": model.model_id, "admitted": False, "reason": f"DIMACS parse: {exc}"})
            continue
        parse_ns = time.perf_counter_ns() - parse_start
        if len(parsed.feature_names) < SLICE_SIZE:
            admissions.append({"model_id": model.model_id, "admitted": False, "reason": f"only {len(parsed.feature_names)} mapped original variables"})
            continue
        try:
            product, solver, solver_construct_ns = satisfying_product(parsed)
        except ValueError as exc:
            admissions.append({"model_id": model.model_id, "admitted": False, "reason": str(exc)})
            continue

        admitted_payloads += 1
        product_bytes = encode_product(product, parsed.n_vars)
        product_sha256 = sha256_bytes(product_bytes)
        witnesses.append({
            "model_id": model.model_id,
            "n_vars": parsed.n_vars,
            "encoding": "bit i is DIMACS variable i+1; little-endian bytes",
            "product_little_endian_hex": product_bytes.hex(),
            "product_sha256": product_sha256,
        })
        model_clause_sets[model.model_id] = set(parsed.clauses)
        model_feature_sets[model.model_id] = set(parsed.feature_names.values())
        slices = choose_slices(model.model_id, parsed)
        admissions.append({
            "model_id": model.model_id,
            "admitted": True,
            "n_vars": parsed.n_vars,
            "n_clauses": len(parsed.clauses),
            "mapped_original_variables": len(parsed.feature_names),
            "parse_ns": parse_ns,
            "solver_construct_ns": solver_construct_ns,
        })

        for slice_index, (slice_kind, slice_variables) in enumerate(slices.items()):
            condition_start = time.perf_counter_ns()
            residual, condition_stats = condition_cnf(parsed.clauses, product, slice_variables)
            condition_ns = time.perf_counter_ns() - condition_start
            expression_start = time.perf_counter_ns()
            expression = expression_from_residual(residual)
            expression_build_ns = time.perf_counter_ns() - expression_start

            start = time.perf_counter_ns()
            cse_program = compile_expr_cse(expression, flatten=True)
            cse_compile_ns = time.perf_counter_ns() - start

            start = time.perf_counter_ns()
            compile_expr_to_cm_ir(expression, persistent_cache=False, reuse_cache=False)
            fresh_cm_compile_ns = time.perf_counter_ns() - start

            diagnostics: dict = {}
            start = time.perf_counter_ns()
            cm_node = compile_expr_to_cm_ir(
                expression,
                diagnostics=diagnostics,
                persistent_cache=True,
                reuse_cache=False,
            )
            family_cm_compile_ns = time.perf_counter_ns() - start
            cm_program = get_flat_program(cm_node)

            evaluator_vars = tuple(f"x{index}" for index in range(SLICE_SIZE - 1, -1, -1))
            cm_call = lambda: _eval_words(cm_program, evaluator_vars, {})
            cse_call = lambda: _eval_words(cse_program, evaluator_vars, {})
            cnf_call = lambda: cnf_bitset(residual)
            cadical_call = lambda: cadical_bitset(solver, product, slice_variables)

            cm_value = cm_call()
            cse_value = cse_call()
            cnf_value = cnf_call()
            cadical_value = cadical_call()
            if len({cm_value, cse_value, cnf_value, cadical_value}) != 1:
                raise AssertionError(f"packed mismatch: {model.model_id} {slice_kind}")
            witness_bit = witness_index(product, slice_variables)
            if not ((cm_value >> witness_bit) & 1):
                raise AssertionError(f"satisfying witness absent: {model.model_id} {slice_kind}")
            spotchecks = scalar_spotcheck(parsed, product, slice_variables, cm_value)

            calls = {
                "cm": (cm_call, packed_batch),
                "cnf": (cnf_call, packed_batch),
                "cse": (cse_call, packed_batch),
                "cadical": (cadical_call, 1),
            }
            for function, _batch in calls.values():
                function()
            samples: dict[str, list[float]] = {name: [] for name in calls}
            arm_names = list(calls)
            for round_index in range(rounds):
                offset = (model_index + slice_index + round_index) % len(arm_names)
                order = arm_names[offset:] + arm_names[:offset]
                for arm in order:
                    function, batch = calls[arm]
                    samples[arm].append(timed_ns(function, batch))
            medians = {arm: statistics.median(values) for arm, values in samples.items()}
            cm_metrics = program_metrics(cm_program)
            cse_metrics = program_metrics(cse_program)

            row = {
                "model_id": model.model_id,
                "history": model.history,
                "version": model.version,
                "ordinal": model.ordinal,
                "transition_labels_json": json.dumps(model.transition_labels),
                "domain": model.domain,
                "origin": model.origin,
                "payload_sha256": item["artifact"]["dimacs_sha256"],
                "product_sha256": product_sha256,
                "declared_variables": parsed.n_vars,
                "mapped_original_variables": len(parsed.feature_names),
                "native_clauses": len(parsed.clauses),
                "metadata_features": model.metadata_features,
                "metadata_clauses": model.metadata_clauses,
                "slice_kind": slice_kind,
                "slice_variables_json": json.dumps(slice_variables),
                "slice_feature_names_json": json.dumps([parsed.feature_names[variable] for variable in slice_variables], ensure_ascii=False),
                "witness_assignment_index": witness_bit,
                "spotcheck_indices_json": json.dumps(spotchecks),
                "packed_sha256": sha256_bytes(cm_value.to_bytes(PACKED_WIDTH // 8, "little")),
                "packed_true_count": cm_value.bit_count(),
                "packed_equal_all_arms": True,
                "parse_ns": parse_ns,
                "solver_construct_ns": solver_construct_ns,
                "condition_ns": condition_ns,
                "expression_build_ns": expression_build_ns,
                **condition_stats,
                "cse_compile_ns": cse_compile_ns,
                "fresh_cm_compile_ns": fresh_cm_compile_ns,
                "family_cm_compile_ns": family_cm_compile_ns,
                "persistent_hits": int(diagnostics.get("ir_persistent_cache_hits", 0)),
                "persistent_misses": int(diagnostics.get("ir_persistent_cache_misses", 0)),
                "persistent_size": int(diagnostics.get("ir_persistent_cache_size", 0)),
                "cm_flat_instructions": cm_metrics["flat_instructions"],
                "cse_flat_instructions": cse_metrics["flat_instructions"],
                "cm_executed_word_ops": cm_metrics["executed_word_ops"],
                "cse_executed_word_ops": cse_metrics["executed_word_ops"],
                "cm_ns_median": medians["cm"],
                "cnf_bitset_ns_median": medians["cnf"],
                "cse_flat_ns_median": medians["cse"],
                "cadical195_ns_median": medians["cadical"],
                "cm_over_cnf_bitset": medians["cm"] / medians["cnf"],
                "cm_over_cse_flat": medians["cm"] / medians["cse"],
                "cm_over_cadical195": medians["cm"] / medians["cadical"],
                "family_over_fresh_cm_compile": family_cm_compile_ns / fresh_cm_compile_ns,
                "cm_cnf_end_to_end_crossover_sessions": crossover_sessions(
                    condition_ns + expression_build_ns + family_cm_compile_ns,
                    medians["cm"],
                    condition_ns,
                    medians["cnf"],
                ),
                "cm_cadical_end_to_end_crossover_sessions": crossover_sessions(
                    condition_ns + expression_build_ns + family_cm_compile_ns,
                    medians["cm"],
                    solver_construct_ns,
                    medians["cadical"],
                ),
            }
            raw_rows.append(row)
        solver.delete()

    overlap_rows = []
    selected_by_history: dict[str, list[SelectedModel]] = defaultdict(list)
    for item in payloads:
        selected_by_history[item["model"].history].append(item["model"])
    for history, models in selected_by_history.items():
        models.sort(key=lambda model: model.ordinal)
        selected_ordinals = {model.ordinal: model for model in models if model.model_id in model_clause_sets}
        for model in models:
            later = selected_ordinals.get(model.ordinal + 1)
            if later is None:
                continue
            earlier_clauses = model_clause_sets[model.model_id]
            later_clauses = model_clause_sets[later.model_id]
            earlier_features = model_feature_sets[model.model_id]
            later_features = model_feature_sets[later.model_id]
            overlap_rows.append({
                "history": history,
                "earlier_model_id": model.model_id,
                "later_model_id": later.model_id,
                "clause_intersection": len(earlier_clauses & later_clauses),
                "clause_union": len(earlier_clauses | later_clauses),
                "clause_jaccard": len(earlier_clauses & later_clauses) / max(1, len(earlier_clauses | later_clauses)),
                "feature_name_intersection": len(earlier_features & later_features),
                "feature_name_union": len(earlier_features | later_features),
                "feature_name_jaccard": len(earlier_features & later_features) / max(1, len(earlier_features | later_features)),
            })

    if not raw_rows:
        raise RuntimeError("no models were admitted")
    primary = clustered_summary(raw_rows, "cm_over_cnf_bitset")
    incumbent = clustered_summary(raw_rows, "cm_over_cadical195")
    cse = clustered_summary(raw_rows, "cm_over_cse_flat")
    family_compile_ratio = sum(row["family_cm_compile_ns"] for row in raw_rows) / sum(row["fresh_cm_compile_ns"] for row in raw_rows)
    hits_by_history = defaultdict(int)
    for row in raw_rows:
        hits_by_history[row["history"]] += int(row["persistent_hits"])
    admitted_histories = sorted({row["history"] for row in raw_rows})
    summary = {
        "schema_version": "1.0",
        "status": "completed",
        "selected_payload_count": len(payloads),
        "admitted_payload_count": admitted_payloads,
        "excluded_payload_count": len(payloads) - admitted_payloads,
        "row_count": len(raw_rows),
        "correctness_mismatches": 0,
        "primary_cm_over_cnf_bitset": primary,
        "secondary_cm_over_cse_flat": cse,
        "secondary_cm_over_cadical195": incumbent,
        "family_compile": {
            "total_family_over_fresh": family_compile_ratio,
            "persistent_hits_by_history": dict(hits_by_history),
        },
        "gates": {
            "correctness": True,
            "specialized_warm_advantage": primary["geomean"] <= 0.95 and primary["ci95"][1] < 1.0,
            "incumbent_batch_advantage": incumbent["geomean"] <= 0.80 and incumbent["ci95"][1] < 1.0,
            "family_construction_advantage": family_compile_ratio <= 0.90 and all(hits_by_history[history] > 0 for history in admitted_histories),
        },
        "claim_boundary": "exact generated eight-feature neighborhoods around satisfying products; not arbitrary partial configuration, projection, counting, explanation, or natural user sessions",
    }
    return raw_rows, admissions, {"summary": summary, "overlaps": overlap_rows, "witnesses": witnesses}


def write_csv(path: Path, rows: list[dict], *, empty_fields: tuple[str, ...] = ()) -> None:
    if not rows and not empty_fields:
        raise ValueError(f"refusing to write empty CSV without a schema: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else list(empty_fields))
        writer.writeheader()
        writer.writerows(rows)


def write_checksums(output: Path) -> None:
    files = sorted(path for path in output.iterdir() if path.is_file() and path.name != "CHECKSUMS.sha256")
    text = "".join(f"{sha256_file(path)}  {path.name}\n" for path in files)
    (output / "CHECKSUMS.sha256").write_text(text, encoding="ascii")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    try:
        import pysat
    except ImportError as exc:  # pragma: no cover - exercised by CLI environment guard
        raise SystemExit(f"required existing benchmark dependency is unavailable: {exc}") from exc
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    parser.add_argument("--packed-batch", type=int, default=PACKED_BATCH)
    parser.add_argument("--limit-models", type=int, default=0, help="diagnostic only; full pilot uses zero")
    parser.add_argument(
        "--diagnostic-model-id",
        action="append",
        default=[],
        help="diagnostic only; repeat to run named preregistered endpoints",
    )
    args = parser.parse_args()
    if args.rounds < 1 or args.packed_batch < 1 or args.limit_models < 0:
        parser.error("rounds and packed-batch must be positive; limit-models must be nonnegative")
    source = args.source.resolve()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    output.mkdir(parents=True)

    diagnostic_model_ids = tuple(args.diagnostic_model_id)
    payloads, provenance = acquire(source, output, args.limit_models, diagnostic_model_ids)
    raw_rows, admissions, result = run_benchmark(payloads, args.rounds, args.packed_batch)
    write_csv(output / "raw.csv", raw_rows)
    write_csv(
        output / "transition-overlap.csv",
        result["overlaps"],
        empty_fields=(
            "history", "earlier_model_id", "later_model_id", "clause_intersection",
            "clause_union", "clause_jaccard", "feature_name_intersection",
            "feature_name_union", "feature_name_jaccard",
        ),
    )
    json_dump(output / "admissions.json", admissions)
    write_jsonl(output / "witnesses.jsonl", result["witnesses"])
    json_dump(output / "summary.json", result["summary"])
    manifest = {
        "schema_version": "1.0",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pilot_mode": "diagnostic" if args.limit_models or diagnostic_model_ids else "full",
        "diagnostic_model_ids": diagnostic_model_ids,
        "protocol": "CONFIGURATION-FM-HISTORY-PILOT-PROTOCOL-V2.md",
        "source_commit": provenance["source_commit"],
        "rounds": args.rounds,
        "packed_batch": args.packed_batch,
        "slice_size": SLICE_SIZE,
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pysat": pysat.__version__,
        "cadical": "CaDiCaL 1.9.5 via PySAT name cadical195",
        "git_head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True
        ).stdout.strip(),
    }
    json_dump(output / "manifest.json", manifest)
    write_checksums(output)
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
