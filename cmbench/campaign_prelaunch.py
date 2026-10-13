"""Fail-closed preparation for the bounded September 2026 CM campaign.

This module performs local admission, capability probes, schedule accounting,
and deterministic source-bundle construction.  It never downloads inputs,
reads credentials, launches cloud resources, or executes a paid campaign.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import platform
import shutil
import stat
import subprocess
import sys
import time
from typing import Any
import zipfile

from cmbench.backends.affine_constraints import AffineConstraintPlan, parse_alist
from cmbench.backends.projected_count import parse_counting_dimacs, pysat_projected_count, scalar_projected_count
from cmbench.biology_bnet import evaluate_bnet, parse_bnet, undeclared_bnet_regulators
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.corpus_freeze import dimacs_metadata


ADMISSION_SCHEMA = "cm-benchmark-admission-ledger/v1"
READINESS_SCHEMA = "cm-benchmark-adapter-readiness/v1"
SCHEDULE_SCHEMA = "cm-benchmark-schedule-ledger/v1"
ARM_SCHEMA = "cm-benchmark-arm-manifest/v1"
UPLOAD_SCHEMA = "cm-benchmark-upload-manifest/v1"
MAX_INPUT_BYTES = 16 << 20
MAX_BUNDLE_BYTES = 64 << 20
ALLOWED_SUFFIXES = frozenset({".alist", ".blif", ".bnet", ".cnf", ".dimacs", ".json", ".jsonl", ".md", ".txt"})
EXECUTABLE_SUFFIXES = frozenset({".bat", ".cmd", ".com", ".dll", ".exe", ".msi", ".ps1", ".scr"})
ADMISSION_STATES = frozenset({"admitted", "rejected", "deferred"})
SCHEDULE_STATES = frozenset({"planned", "not_run", "blocked"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: str | Path, *, maximum: int = MAX_BUNDLE_BYTES) -> str:
    source = Path(path)
    if not source.is_file() or source.is_symlink() or source.stat().st_size > maximum:
        raise ValueError("file missing, linked, or oversized")
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def safe_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 512 or "\\" in value or "\x00" in value:
        raise ValueError("invalid relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or ":" in value:
        raise ValueError("relative path escapes source root")
    lowered = tuple(part.lower() for part in path.parts)
    if any(part.startswith(".env") for part in lowered) or any(
        word in part for part in lowered for word in ("credential", "private-key", "secret", "token-cache")
    ):
        raise ValueError("secret-like path is forbidden")
    return path.as_posix()


def _inside_unlinked(root: Path, relative: str) -> Path:
    base = root.resolve()
    source = (base / PurePosixPath(safe_relative_path(relative))).resolve()
    try:
        source.relative_to(base)
    except ValueError as exc:
        raise ValueError("resolved source escapes root") from exc
    current = source
    while current != base:
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise ValueError("linked source path is forbidden")
        current = current.parent
    return source


def _reject_executable(path: Path) -> None:
    if path.suffix.lower() in EXECUTABLE_SUFFIXES:
        raise ValueError("executable suffix is forbidden")
    with path.open("rb") as stream:
        prefix = stream.read(8)
    if prefix.startswith((b"MZ", b"\x7fELF", b"#!")):
        raise ValueError("executable payload is forbidden")
    if path.stat().st_mode & stat.S_IXUSR:
        raise ValueError("executable file mode is forbidden")


@dataclass(frozen=True)
class Candidate:
    case_id: str
    group: str
    family_id: str
    cluster_id: str
    role: str
    path: str
    kind: str
    source_url: str
    source_revision: str
    expected_sha256: str
    license_spdx: str
    license_path: str | None
    redistribution: str
    transformations: tuple[str, ...] = ()
    selector: str | None = None


def admit_candidate(root: str | Path, candidate: Candidate) -> dict[str, Any]:
    """Admit one already-acquired public input without executing its contents."""
    base = Path(root)
    row: dict[str, Any] = {
        "case_id": candidate.case_id,
        "group": candidate.group,
        "family_id": candidate.family_id,
        "cluster_id": candidate.cluster_id,
        "role": candidate.role,
        "path": safe_relative_path(candidate.path),
        "kind": candidate.kind,
        "source_url": candidate.source_url,
        "source_revision": candidate.source_revision,
        "expected_sha256": candidate.expected_sha256,
        "license_spdx": candidate.license_spdx,
        "license_path": safe_relative_path(candidate.license_path) if candidate.license_path else None,
        "redistribution": candidate.redistribution,
        "transformations": list(candidate.transformations),
        "selector": candidate.selector,
        "state": "rejected",
        "reason": None,
        "bytes": None,
        "sha256": None,
        "metadata": None,
    }
    try:
        if candidate.role not in {"regression", "development", "confirmation"}:
            raise ValueError("invalid split role")
        if candidate.redistribution != "permitted_with_license_notice":
            raise ValueError("redistribution not established")
        git_revision = len(candidate.source_revision) == 40 and all(c in "0123456789abcdef" for c in candidate.source_revision)
        zenodo_revision = candidate.source_revision.startswith("zenodo:") and candidate.source_revision[7:].isdigit()
        if not (git_revision or zenodo_revision):
            raise ValueError("source revision must be a pinned Git commit or Zenodo record")
        if len(candidate.expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in candidate.expected_sha256):
            raise ValueError("invalid expected SHA-256")
        source = _inside_unlinked(base, candidate.path)
        if not source.is_file():
            raise ValueError("source file missing")
        if source.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError("source suffix is not admitted")
        if not 0 < source.stat().st_size <= MAX_INPUT_BYTES:
            raise ValueError("source byte limit exceeded")
        _reject_executable(source)
        actual = sha256_file(source, maximum=MAX_INPUT_BYTES)
        if actual != candidate.expected_sha256:
            raise ValueError("source SHA-256 mismatch")
        if candidate.license_path:
            license_file = _inside_unlinked(base, candidate.license_path)
            if not license_file.is_file() or not 0 < license_file.stat().st_size <= (1 << 20):
                raise ValueError("license evidence missing or oversized")
        if candidate.kind == "cnf":
            metadata = dimacs_metadata(source)
            if metadata["comment_directives"]:
                raise ValueError("DIMACS semantic directives require a separate declared contract")
        elif candidate.kind == "blif":
            from cmbench.recognition.blif import parse_blif

            netlist = parse_blif(source)
            metadata = {
                "inputs": len(netlist.inputs),
                "outputs": len(netlist.outputs),
                "nodes": len(netlist.nodes),
            }
        elif candidate.kind == "alist":
            width, rows = parse_alist(source.read_text(encoding="utf-8"), max_width=4096, max_rows=16384)
            metadata = {"columns": width, "rows": len(rows), "nonzero_rows": sum(bool(item) for item in rows)}
        elif candidate.kind == "bnet":
            functions = parse_bnet(source.read_text(encoding="utf-8"))
            selected = next((item for item in functions if item.target == candidate.selector), None)
            if selected is None:
                raise ValueError("BNet selector does not name an update function")
            external = undeclared_bnet_regulators(functions)
            if external:
                raise ValueError("BNet fixed-point model is not closed under declared targets")
            metadata = {"functions": len(functions), "target": selected.target,
                        "regulators": list(selected.regulators), "local_width": len(selected.regulators),
                        "closed_under_declared_targets": True, "undeclared_regulators": []}
        elif candidate.kind in {"mc", "pmc"}:
            instance = parse_counting_dimacs(
                source.read_text(encoding="utf-8"), mode="exact" if candidate.kind == "mc" else "projected",
            )
            metadata = {"variables": instance.variables, "clauses": len(instance.clauses),
                        "projection_variables": len(instance.projection),
                        "declared_support_variables": len(instance.declared_support), "mode": instance.mode}
        else:
            raise ValueError("unimplemented input kind")
        row.update(state="admitted", reason="validated", bytes=source.stat().st_size, sha256=actual, metadata=metadata)
    except (OSError, UnicodeError, ValueError) as exc:
        row["reason"] = str(exc)[:256]
    return row


def validate_admission_ledger(record: Mapping[str, Any]) -> None:
    if set(record) != {"schema", "campaign_id", "created_utc", "limits", "rows", "summary", "ledger_sha256"}:
        raise ValueError("admission ledger fields")
    if record["schema"] != ADMISSION_SCHEMA or not isinstance(record["rows"], list):
        raise ValueError("admission ledger schema")
    core = {key: record[key] for key in record if key != "ledger_sha256"}
    if record["ledger_sha256"] != canonical_digest(core):
        raise ValueError("admission ledger digest")
    ids = set()
    counts = Counter()
    for row in record["rows"]:
        if row.get("state") not in ADMISSION_STATES or row.get("case_id") in ids:
            raise ValueError("admission row state or identity")
        ids.add(row["case_id"])
        counts[row["state"]] += 1
        if row["state"] == "admitted" and (row.get("reason") != "validated" or row.get("sha256") != row.get("expected_sha256")):
            raise ValueError("admitted row identity")
    if dict(sorted(counts.items())) != record["summary"]["states"]:
        raise ValueError("admission summary")


def build_admission_ledger(root: str | Path, campaign_id: str, candidates: Sequence[Candidate], *,
                           created_utc: str, prior_rows: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    rows = [admit_candidate(root, candidate) for candidate in candidates]
    rows.extend(dict(row) for row in prior_rows)
    counts = Counter(row["state"] for row in rows)
    groups = {
        group: dict(sorted(Counter(row["state"] for row in rows if row["group"] == group).items()))
        for group in sorted({row["group"] for row in rows})
    }
    record = {
        "schema": ADMISSION_SCHEMA,
        "campaign_id": campaign_id,
        "created_utc": created_utc,
        "limits": {"input_bytes": MAX_INPUT_BYTES, "archive_expansion_bytes": 0, "executables_allowed": False},
        "rows": rows,
        "summary": {"states": dict(sorted(counts.items())), "groups": groups},
    }
    record["ledger_sha256"] = canonical_digest(record)
    validate_admission_ledger(record)
    return record


def _probe(name: str, function: Any, *, missing_reason: str = "capability probe failed") -> dict[str, Any]:
    started = time.perf_counter_ns()
    try:
        detail = function()
    except Exception as exc:  # Capability failures belong in readiness evidence.
        return {"adapter": name, "state": "present_unverified", "reason": f"{missing_reason}:{type(exc).__name__}",
                "probe_ns": time.perf_counter_ns() - started, "detail": None}
    return {"adapter": name, "state": "present_verified", "reason": "bounded_local_probe_passed",
            "probe_ns": time.perf_counter_ns() - started, "detail": detail}


def adapter_readiness(root: str | Path, campaign_id: str, *, created_utc: str) -> dict[str, Any]:
    """Run bounded functional probes; timing values are diagnostics, not rankings."""
    project = Path(root)

    def complete_relation() -> dict[str, Any]:
        from cm_exprlib import And, Not, Or, Var, Xor
        from cmbench.comparative.arms import execute_arm, scalar_relation, semantic_sha256
        from cmbench.comparative.contracts import CONTRACT_SCHEMA

        expr = Or(And(Var(0), Not(Var(1))), Xor(Var(2), Var(3)))
        variables = tuple(f"x{i}" for i in range(4))
        expected = semantic_sha256(scalar_relation(expr, variables, {}), 4)
        hashes = set()
        arms = {"cm_flat_bigint": "packed_bigint", "cse_flat": "packed_bigint",
                "direct_expr_bitset": "packed_bigint", "cm_flat_words": "packed_words"}
        for arm, kind in arms.items():
            contract = {
                "schema": CONTRACT_SCHEMA, "contract_id": "prelaunch-" + arm,
                "task": "complete_relation",
                "artifact": {"kind": kind, "variable_order": list(variables), "output_order": list(variables),
                             "fixed": [], "output_scope": "full", "restoration": "none", "stream": None},
                "lifecycle": "fresh_engine", "queries": 1,
                "validation": {"oracle": "independent_scalar_assignment/v1", "validation_in_timed_span": False,
                               "required_output_sha256": expected},
            }
            hashes.add(execute_arm(expr=expr, contract=contract, case_id="prelaunch-k4", arm=arm, smoke_bound=4)["artifact"]["sha256"])
        if hashes != {expected}:
            raise ValueError("relation arms disagree")
        return {"arms": list(arms), "oracle_sha256": expected}

    def cudd_count() -> dict[str, Any]:
        from dd import cudd
        from cmbench.comparative.exact_cudd_count import exact_cudd_count

        manager = cudd.BDD()
        manager.declare("x", "y", "unused")
        root_node = manager.var("x") | manager.var("y")
        count = exact_cudd_count(manager, root_node)
        if count != 6:
            raise ValueError("arbitrary-precision CUDD traversal mismatch")
        return {"distribution": importlib.metadata.version("dd"), "count": count, "declared_variables": 3}

    def sat() -> dict[str, Any]:
        from pysat.solvers import Cadical195

        with Cadical195(bootstrap_with=[[1, 2], [-1, 2]]) as solver:
            if solver.solve(assumptions=[-2]) is not False or solver.solve(assumptions=[2]) is not True:
                raise ValueError("CaDiCaL assumptions mismatch")
            model = solver.get_model()
        return {"distribution": importlib.metadata.version("python-sat"), "binding": "pysat.Cadical195",
                "witness_returned": isinstance(model, list)}

    def affine() -> dict[str, Any]:
        plan = AffineConstraintPlan((0b11, 0b110), (1, 0), ("x0", "x1", "x2"))
        values = {"all": plan.count(), "x0=0": plan.count({"x0": 0}), "contradiction": plan.count({"x0": 0, "x1": 0})}
        if values != {"all": 2, "x0=0": 1, "contradiction": 0}:
            raise ValueError("GF(2) count mismatch")
        return values

    def streaming() -> dict[str, Any]:
        from cm_exprlib import Xor, Var
        from cmbench.backends.packed_mask_cache import PackedMaskCache
        from cmbench.backends.packed_stream_io import PackedStreamPlan, write_packed_stream

        sink = io.BytesIO()
        plan = PackedStreamPlan.from_expr(
            Xor(Var(0), Var(1)), ("x0", "x1", "x2"),
            cache=PackedMaskCache(max_bytes=1024, max_width=3),
        )
        result = write_packed_stream(plan, sink, chunk_vars=3, max_total_bits=64)
        if not result.completed or result.written_bits != 8 or len(sink.getvalue()) != result.written_bytes:
            raise ValueError("stream consumption mismatch")
        return {"written_bits": result.written_bits, "written_bytes": result.written_bytes, "sha256": result.sha256}

    def tracing() -> dict[str, Any]:
        from cmbench.tracing.schema import CONTENT_MODE, SCHEMA_VERSION, validate_trace_event

        session = "0" * 32
        event = {"schema_version": SCHEMA_VERSION, "content_mode": CONTENT_MODE, "session_id": session,
                 "sequence": 0, "event_id": session + ":0", "event_type": "session_start",
                 "utc_ns": 1, "monotonic_ns": 1, "payload": {"phase": "prelaunch"}}
        validate_trace_event(event)
        return {"metrics_only": True, "payload_fields": sorted(event["payload"])}

    def sympy_control() -> dict[str, Any]:
        import sympy
        from sympy import lambdify, symbols

        x, y = symbols("x y")
        fn = lambdify((x, y), x ^ y, modules="numpy", cse=True)
        if bool(fn(True, False)) is not True or bool(fn(True, True)) is not False:
            raise ValueError("SymPy callable mismatch")
        return {"distribution": sympy.__version__, "lambdify_cse": True}

    def biology() -> dict[str, Any]:
        function = parse_bnet("targets,factors\nout, a | b & !c\n")[0]
        if function.regulators != ("a", "b", "c") or not evaluate_bnet(
            function.expression, {"a": 0, "b": 1, "c": 0},
        ):
            raise ValueError("BNet semantics mismatch")
        return {"format": "BNet", "parser": "bounded_iterative", "local_width": 3}

    def projected_count() -> dict[str, Any]:
        instance = parse_counting_dimacs("p cnf 3 1\nc ind 1 0\n2 3 0\n", mode="projected")
        scalar = scalar_projected_count(instance)
        pysat = pysat_projected_count(instance)
        if scalar != 2 or pysat != scalar:
            raise ValueError("distinct-visible-solution semantics mismatch")
        return {"mode": "exact_projected", "count": scalar, "oracles": ["scalar", "pysat.Cadical195"]}

    def linux_native(expected: str) -> dict[str, Any]:
        smoke_path = project / "docs/audits/2026-09-13-cm-benchmark-campaign/linux-smoke-002/LINUX_SMOKE.json"
        smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
        native = smoke["native_results"]
        if smoke.get("status") != "passed" or smoke.get("secret_access") is not False:
            raise ValueError("Linux smoke did not pass safely")
        checks = {
            "ganak": native.get("ordinary_exact_count") == 4 and native.get("ganak_probabilistic_mode") is False
                     and native.get("ganak_approximate_fallback") is False,
            "projected": native.get("projected_exact_count") == 2,
            "kissat": native.get("kissat_sat_exit") == 10 and native.get("kissat_unsat_exit") == 20,
            "d4": native.get("d4_exact_count") == 4 and bool(native.get("d4_binary_sha256")),
            "cryptominisat": native.get("cryptominisat_xor_sat_exit") == 10
                             and native.get("cryptominisat_xor_unsat_exit") == 20
                             and native.get("cryptominisat_xor_witness_validated") is True,
            "aeon": native.get("biodivine_aeon_fixed_points") == 2
                    and native.get("biodivine_aeon_version") == "1.4.2",
        }
        if not checks[expected]:
            raise ValueError("native Linux smoke contract mismatch")
        revisions = {
            "ganak": native.get("ganak_revision"), "projected": native.get("ganak_revision"),
            "kissat": native.get("kissat_version"), "d4": native.get("d4_revision"),
            "cryptominisat": native.get("cryptominisat_revision"),
            "aeon": native.get("biodivine_aeon_revision"),
        }
        return {"image_id": smoke["image"]["id"], "linux_amd64": True,
                "revision": revisions[expected]}

    rows = [
        _probe("complete_relation.cm_cse_bitset", complete_relation),
        _probe("exact_count.cudd_arbitrary_precision", cudd_count),
        _probe("sat_witness.pysat_cadical", sat),
        _probe("gf2.python_packed_elimination", affine),
        _probe("streaming.packed_backpressure", streaming),
        _probe("tracing.metrics_replay_contract", tracing),
        _probe("sympy.matched_callable", sympy_control),
        _probe("biology.bnet_cm", biology),
        _probe("projected_count.cm", projected_count),
        _probe("exact_count.ganak", lambda: linux_native("ganak")),
        _probe("projected_count.native_ganak", lambda: linux_native("projected")),
        _probe("sat.kissat_one_shot", lambda: linux_native("kissat")),
        _probe("exact_count.d4", lambda: linux_native("d4")),
        _probe("sat.cryptominisat_xor", lambda: linux_native("cryptominisat")),
        _probe("biology.biodivine_native", lambda: linux_native("aeon")),
    ]
    commands = {name: shutil.which(name) for name in ("abc", "cryptominisat", "cryptominisat5", "d4", "ganak", "kissat", "yosys")}
    missing = {
        "hardware.abc_equivalence": "pinned ABC executable unavailable",
        "hardware.yosys_transform": "pinned Yosys executable unavailable",
        "policies.native_services": "Cedar/OPA semantic adapters deferred",
        "bitmaps.croaring": "record-set semantic adapter deferred",
        "weighted_inference": "weighted Boolean/probability contract deferred",
    }
    for adapter, reason in missing.items():
        executable = next((commands[name] for name in commands if name in adapter and commands[name]), None)
        rows.append({"adapter": adapter, "state": "present_unverified" if executable else "missing",
                     "reason": reason, "probe_ns": 0, "detail": {"path": executable} if executable else None})
    m4ri_source = project / "native" / "cm_scalar_m4ri"
    rows.append({"adapter": "gf2.m4ri", "state": "present_unverified" if m4ri_source.is_dir() else "missing",
                 "reason": "local source present; no pinned locally executed library binding" if m4ri_source.is_dir() else "source absent",
                 "probe_ns": 0, "detail": {"source_path": "native/cm_scalar_m4ri"} if m4ri_source.is_dir() else None})
    record = {
        "schema": READINESS_SCHEMA,
        "campaign_id": campaign_id,
        "created_utc": created_utc,
        "performance_ranking_permitted": False,
        "rows": sorted(rows, key=lambda row: row["adapter"]),
    }
    record["summary"] = dict(sorted(Counter(row["state"] for row in record["rows"]).items()))
    record["readiness_sha256"] = canonical_digest(record)
    return record


def synthetic_specs(*, count: int = 600, seed: int = 20260913) -> list[dict[str, Any]]:
    """Freeze a mechanism-balanced synthetic specification without materializing tables."""
    families = (
        "S01_constants_unused", "S02_balanced_deep", "S03_shared_duplicated", "S04_parity_equivalence",
        "S05_cardinality", "S06_multiplexers", "S07_arithmetic", "S08_random_3cnf",
        "S09_horn_2cnf", "S10_independent_components", "S11_overlap_width", "S12_projection_traps",
        "S13_rewrite_adversaries", "S14_bdd_order", "S15_output_density", "S16_frontier",
    )
    widths = (4, 8, 12, 16, 20, 24, 28, 32)
    rows = []
    for index in range(count):
        family = families[index % len(families)]
        width = widths[(index // len(families)) % len(widths)]
        identity = {"family": family, "width": width, "seed": seed + index, "index": index}
        digest = canonical_digest(identity)
        role_bucket = int(digest[:8], 16) % 10
        role = "development" if role_bucket < 4 else "confirmation" if role_bucket < 8 else "regression"
        rows.append({"case_id": f"synthetic-{index:04d}-{digest[:12]}", "cluster_id": f"{family}-{digest[12:24]}",
                     "group": "synthetic_mechanisms", "family_id": family[:3], "role": role,
                     "kind": "synthetic_spec", "spec": identity, "sha256": digest,
                     "provenance": "deterministic synthetic control; never real-world"})
    return rows


def build_schedule_ledger(campaign_id: str, admission: Mapping[str, Any], synthetic: Sequence[Mapping[str, Any]], *, created_utc: str) -> dict[str, Any]:
    targets = {"hardware": 600, "feature_models": 400, "biological_functions": 300,
               "sat_and_counting": 300, "affine": 200, "synthetic_mechanisms": 600}
    admitted = [row for row in admission["rows"] if row["state"] == "admitted"]
    by_group: dict[str, list[Mapping[str, Any]]] = {group: [] for group in targets}
    for row in admitted:
        by_group.setdefault(row["group"], []).append(row)
    by_group["synthetic_mechanisms"] = list(synthetic)
    rows = []
    for group, target in targets.items():
        cases = sorted(by_group.get(group, []), key=lambda item: item["case_id"])
        for index in range(target):
            if index < len(cases):
                case = cases[index]
                state, reason, case_id = "planned", "admitted_input", case["case_id"]
            else:
                state, reason, case_id = "not_run", "corpus_quota_shortfall", None
            core = {"campaign_id": campaign_id, "group": group, "quota_index": index,
                    "state": state, "reason": reason, "case_id": case_id}
            core["slot_id"] = canonical_digest(core)
            rows.append(core)
    counts = {group: dict(sorted(Counter(row["state"] for row in rows if row["group"] == group).items())) for group in targets}
    record = {
        "schema": SCHEDULE_SCHEMA,
        "campaign_id": campaign_id,
        "created_utc": created_utc,
        "base_case_target": sum(targets.values()),
        "allocations": targets,
        "query_counts": [1, 2, 4, 8, 16, 64, 256, 1024],
        "explicit_widths": [4, 8, 12, 16, 20, 24, 28, 32],
        "arm_order_policy": "paired balanced Latin/reverse cycles within task after pilot; no all-task Cartesian product",
        "repetitions": {"screen": 3, "confirmation": "frozen only after screen; no outcome-responsive extension"},
        "not_run_policy": "When estimated remaining time plus one-hour cleanup reserve exceeds the lesser hard cap, stop admitting whole strata by descending predetermined cost: frontier, Q1024, Q256, optional arms, then proportional hash-ranked cases within every group.",
        "rows": rows,
        "summary": counts,
    }
    record["schedule_sha256"] = canonical_digest(record)
    return record


def build_arm_manifest(campaign_id: str, readiness: Mapping[str, Any], *, created_utc: str) -> dict[str, Any]:
    """Freeze a reduced, outcome-independent scope from verified adapters only."""
    task_map = {
        "complete_relation": "complete_relations",
        "exact_count": "ordinary_exact_counts",
        "projected_count": "projected_exact_counts",
        "sat": "sat_status_and_witnesses",
        "sat_witness": "sat_status_and_witnesses",
        "gf2": "affine_outputs",
        "biology": "biological_functions",
        "sympy": "complete_relation_control",
        "streaming": "stream_delivery",
        "tracing": "metrics_and_replay_contract",
        "hardware": "hardware_translation_or_equivalence",
        "policies": "native_policy_services",
        "bitmaps": "native_record_sets",
        "weighted_inference": "weighted_inference",
    }
    rows = []
    for source in sorted(readiness["rows"], key=lambda row: row["adapter"]):
        prefix = source["adapter"].split(".", 1)[0]
        state = "planned" if source["state"] == "present_verified" else "not_run"
        rows.append({
            "adapter": source["adapter"],
            "task": task_map.get(prefix, prefix),
            "state": state,
            "reason": "verified_before_scope_freeze" if state == "planned"
                      else "excluded_before_screen:" + source["state"],
            "readiness_state": source["state"],
        })
    record = {
        "schema": ARM_SCHEMA,
        "campaign_id": campaign_id,
        "created_utc": created_utc,
        "scope": "reduced_verified_core",
        "selection_policy": "Only adapters functionally verified before this freeze are planned; excluded lanes remain explicit not-run and cannot be restored in response to benchmark outcomes.",
        "outcome_responsive_changes_permitted": False,
        "rows": rows,
        "summary": dict(sorted(Counter(row["state"] for row in rows).items())),
    }
    record["arm_manifest_sha256"] = canonical_digest(record)
    return record


def source_identity(root: str | Path, paths: Iterable[str]) -> dict[str, Any]:
    project = Path(root)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project, check=True, capture_output=True, text=True).stdout.strip()
    files = []
    for relative in sorted(set(safe_relative_path(path) for path in paths)):
        source = _inside_unlinked(project, relative)
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative], cwd=project,
            capture_output=True, text=True,
        ).returncode == 0
        unstaged = tracked and subprocess.run(
            ["git", "diff", "--quiet", "--", relative], cwd=project,
        ).returncode != 0
        staged = tracked and subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--", relative], cwd=project,
        ).returncode != 0
        state = "untracked" if not tracked else (
            "tracked_staged_and_modified" if staged and unstaged else
            "tracked_staged" if staged else "tracked_modified" if unstaged else "tracked_clean"
        )
        files.append({"path": relative, "bytes": source.stat().st_size,
                      "sha256": sha256_file(source), "git_state": state})
    return {"schema": "cm-benchmark-source-identity/v1", "git_head": head,
            "workspace_dirty_in_scope": any(row["git_state"] != "tracked_clean" for row in files),
            "files": files, "tree_sha256": canonical_digest(files)}


def environment_lock() -> dict[str, Any]:
    """Describe the tested host and immutable Linux/native environment."""
    installed = {}
    for name in ("dd", "numpy", "python-sat", "pytest", "sympy"):
        try:
            installed[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            installed[name] = None
    return {
        "schema": "cm-benchmark-environment-lock/v1",
        "local_test_host": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "packages": installed,
        },
        "proposed_linux_base": {
            "image": "python:3.13.15-bookworm",
            "amd64_digest": "sha256:a53008522631dbcb063c4d5982aa91a00e86e51d90bbcf3513313f1a5c163af8",
            "status": "pinned_built_and_smoke_tested",
            "local_image_id": "sha256:fabb3956b9129b32c179aec8e4f539d9d2bad3d247af61789e66a58655d14052",
        },
        "native_requirements": {
            "exercised": {
                "Ganak": {"revision": "7f03233c699e2a5bfa1534ca986c83bdc19ec3df", "mode": "--prob 0 --appmct -1"},
                "Kissat": {"revision": "8af8e56f174b778aef3aa45af9f739b2a5f492c2", "version": "4.0.4"},
                "CryptoMiniSat": {"revision": "e34a5147e578d3e1b8ca3d584d99253bcd9b566f", "version": "5.15.0", "xor_witness_checked": True},
                "d4v2": {"revision": "15eff31962466804a48374826b9e5a746fc2766e", "exact_count_checked": True,
                          "patoh_pr_revision": "7786dacbe75dfc3b90db7de30863578c93827bb7"},
                "Biodivine AEON.py": {"revision": "cd514aa3c5d6079fca8270091ca8fd8ed76af24c", "version": "1.4.2"},
            },
            "required_before_affected_cells": [
                "ABC", "Yosys", "M4RI",
            ],
            "source_only_pins": {},
            "unexercised_affected_cells_remain_blocked": True,
        },
        "network_used_for_public_image_and_release_assets": True,
        "cloud_used": False,
        "secret_access": False,
    }


def build_upload_bundle(root: str | Path, output_dir: str | Path, campaign_id: str,
                        entries: Sequence[Mapping[str, str]], generated: Mapping[str, bytes]) -> dict[str, Any]:
    """Create one deterministic, inspectable bundle; no network operation occurs."""
    project, destination = Path(root).resolve(), Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    normalized: list[dict[str, Any]] = []
    payloads: dict[str, bytes] = {}
    for entry in entries:
        if set(entry) != {"source", "archive"}:
            raise ValueError("upload entry fields")
        source = _inside_unlinked(project, entry["source"])
        archive = safe_relative_path(entry["archive"])
        if archive in payloads:
            raise ValueError("duplicate upload archive path")
        data = source.read_bytes()
        if len(data) > MAX_BUNDLE_BYTES:
            raise ValueError("upload member too large")
        payloads[archive] = data
        normalized.append({"source": safe_relative_path(entry["source"]), "archive": archive,
                           "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    for archive, data in generated.items():
        archive = safe_relative_path(archive)
        if archive in payloads or not isinstance(data, bytes) or len(data) > MAX_BUNDLE_BYTES:
            raise ValueError("invalid generated upload member")
        payloads[archive] = data
        normalized.append({"source": None, "archive": archive, "bytes": len(data),
                           "sha256": hashlib.sha256(data).hexdigest()})
    normalized.sort(key=lambda row: row["archive"])
    contents = {"schema": "cm-benchmark-bundle-contents/v1", "campaign_id": campaign_id, "files": normalized}
    contents_bytes = json.dumps(contents, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    payloads["BUNDLE_CONTENTS.json"] = contents_bytes
    normalized.append({"source": None, "archive": "BUNDLE_CONTENTS.json", "bytes": len(contents_bytes),
                       "sha256": hashlib.sha256(contents_bytes).hexdigest()})
    normalized.sort(key=lambda row: row["archive"])
    bundle = destination / "SOURCE_BUNDLE.zip"
    if bundle.exists():
        bundle.unlink()
    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payloads[name])
    manifest = {
        "schema": UPLOAD_SCHEMA,
        "campaign_id": campaign_id,
        "upload_authorized": False,
        "upload_scope": ["SOURCE_BUNDLE.zip"],
        "bundle": {"path": "SOURCE_BUNDLE.zip", "bytes": bundle.stat().st_size, "sha256": sha256_file(bundle)},
        "contents": normalized,
        "excluded": [".env*", ".git", "build", "local databases", "credential stores", "unrelated user files", "prior result archives"],
    }
    manifest["manifest_sha256"] = canonical_digest(manifest)
    return manifest


def build_upload_bundles(root: str | Path, output_dir: str | Path, campaign_id: str,
                         entries: Sequence[Mapping[str, str]], generated: Mapping[str, bytes], *,
                         maximum_expanded: int = MAX_BUNDLE_BYTES) -> dict[str, Any]:
    """Create deterministic upload shards with a 64 MiB expanded limit each."""
    project, destination = Path(root).resolve(), Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    assets: dict[str, tuple[str | None, Path | bytes]] = {}
    rows: list[dict[str, Any]] = []
    for entry in entries:
        if set(entry) != {"source", "archive"}:
            raise ValueError("upload entry fields")
        source_relative = safe_relative_path(entry["source"])
        source = _inside_unlinked(project, source_relative)
        archive = safe_relative_path(entry["archive"])
        if archive in assets:
            if assets[archive][0] == source_relative:
                continue
            raise ValueError("duplicate upload archive path")
        size = source.stat().st_size
        if not 0 <= size <= MAX_BUNDLE_BYTES:
            raise ValueError(f"upload member outside byte limit: {source_relative} ({size} bytes)")
        assets[archive] = (source_relative, source)
        rows.append({"source": source_relative, "archive": archive, "bytes": size,
                     "sha256": sha256_file(source), "bundle": None})
    for archive_value, data in generated.items():
        archive = safe_relative_path(archive_value)
        if archive in assets or not isinstance(data, bytes) or not 0 < len(data) <= MAX_BUNDLE_BYTES:
            raise ValueError("invalid generated upload member")
        assets[archive] = (None, data)
        rows.append({"source": None, "archive": archive, "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest(), "bundle": None})
    rows.sort(key=lambda row: row["archive"])
    if not 4096 <= maximum_expanded <= MAX_BUNDLE_BYTES:
        raise ValueError("invalid upload shard limit")
    manifest_reserve = min(4 << 20, max(1024, maximum_expanded // 4))
    shard_limit = maximum_expanded - manifest_reserve
    shards: list[list[dict[str, Any]]] = [[]]
    shard_bytes = 0
    for row in rows:
        if shards[-1] and shard_bytes + row["bytes"] > shard_limit:
            shards.append([])
            shard_bytes = 0
        shards[-1].append(row)
        shard_bytes += row["bytes"]
    names = [f"SOURCE_BUNDLE-{index:03d}.zip" for index in range(1, len(shards) + 1)]
    for name, shard in zip(names, shards):
        for row in shard:
            row["bundle"] = name
    contents = {"schema": "cm-benchmark-bundle-contents/v2", "campaign_id": campaign_id, "files": rows}
    contents_bytes = json.dumps(contents, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    if len(contents_bytes) > manifest_reserve:
        raise ValueError("bundle contents manifest exceeds reserved shard space")
    content_row = {"source": None, "archive": "BUNDLE_CONTENTS.json", "bytes": len(contents_bytes),
                   "sha256": hashlib.sha256(contents_bytes).hexdigest(), "bundle": names[0]}
    rows_with_contents = sorted([*rows, content_row], key=lambda row: row["archive"])
    assets["BUNDLE_CONTENTS.json"] = (None, contents_bytes)
    bundle_records = []
    for name, shard in zip(names, shards):
        assigned = [*shard]
        if name == names[0]:
            assigned.append(content_row)
        bundle = destination / name
        if bundle.exists():
            bundle.unlink()
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive_file:
            for row in sorted(assigned, key=lambda item: item["archive"]):
                info = zipfile.ZipInfo(row["archive"], (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                _source_relative, payload = assets[row["archive"]]
                with archive_file.open(info, "w") as sink:
                    if isinstance(payload, bytes):
                        sink.write(payload)
                    else:
                        with payload.open("rb") as source_stream:
                            shutil.copyfileobj(source_stream, sink, length=1 << 20)
        bundle_records.append({"path": name, "bytes": bundle.stat().st_size,
                               "sha256": sha256_file(bundle),
                               "expanded_bytes": sum(row["bytes"] for row in assigned),
                               "expanded_limit": maximum_expanded,
                               "files": len(assigned)})
    manifest = {
        "schema": "cm-benchmark-upload-manifest/v2", "campaign_id": campaign_id,
        "upload_authorized": False, "upload_scope": names, "bundles": bundle_records,
        "contents": rows_with_contents,
        "excluded": [".env*", ".git", "build", "local databases", "credential stores",
                     "unrelated user files", "prior result archives"],
    }
    manifest["manifest_sha256"] = canonical_digest(manifest)
    return manifest


def verify_upload_bundles(directory: str | Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    base = Path(directory)
    expected_all = {row["archive"]: row for row in manifest["contents"]}
    seen: set[str] = set()
    expanded = 0
    for bundle_row in manifest["bundles"]:
        bundle = base / bundle_row["path"]
        if sha256_file(bundle) != bundle_row["sha256"] or bundle.stat().st_size != bundle_row["bytes"]:
            raise ValueError("bundle identity mismatch")
        expected = {name: row for name, row in expected_all.items() if row["bundle"] == bundle_row["path"]}
        with zipfile.ZipFile(bundle) as archive_file:
            names = archive_file.namelist()
            if len(names) != len(set(names)) or set(names) != set(expected) or seen.intersection(names):
                raise ValueError("bundle member coverage mismatch")
            shard_expanded = 0
            for info in archive_file.infolist():
                path = PurePosixPath(info.filename)
                if path.is_absolute() or ".." in path.parts or info.is_dir() or info.file_size > MAX_BUNDLE_BYTES:
                    raise ValueError("unsafe bundle member")
                digest = hashlib.sha256()
                with archive_file.open(info) as stream:
                    size = 0
                    while chunk := stream.read(1 << 20):
                        size += len(chunk)
                        digest.update(chunk)
                row = expected[info.filename]
                if size != row["bytes"] or digest.hexdigest() != row["sha256"]:
                    raise ValueError("bundle member identity mismatch")
                shard_expanded += size
            if shard_expanded > bundle_row["expanded_limit"] or shard_expanded != bundle_row["expanded_bytes"]:
                raise ValueError("bundle expanded byte limit")
        seen.update(names)
        expanded += shard_expanded
    if seen != set(expected_all):
        raise ValueError("upload shards do not cover manifest")
    return {"verified": True, "files": len(expected_all), "bundles": len(manifest["bundles"]),
            "expanded_bytes": expanded,
            "bundle_sha256": [row["sha256"] for row in manifest["bundles"]]}


def verify_upload_bundle(directory: str | Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    base = Path(directory)
    bundle = base / manifest["bundle"]["path"]
    if sha256_file(bundle) != manifest["bundle"]["sha256"] or bundle.stat().st_size != manifest["bundle"]["bytes"]:
        raise ValueError("bundle identity mismatch")
    expected = {row["archive"]: row for row in manifest["contents"]}
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(expected):
            raise ValueError("bundle member coverage mismatch")
        total = 0
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or info.is_dir() or info.file_size > MAX_BUNDLE_BYTES:
                raise ValueError("unsafe bundle member")
            data = archive.read(info)
            total += len(data)
            row = expected[info.filename]
            if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("bundle member identity mismatch")
        if total > MAX_BUNDLE_BYTES:
            raise ValueError("bundle expanded byte limit")
    return {"verified": True, "files": len(expected), "expanded_bytes": total,
            "bundle_sha256": manifest["bundle"]["sha256"]}
