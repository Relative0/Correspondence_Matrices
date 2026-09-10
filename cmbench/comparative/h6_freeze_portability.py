"""Read-only portability audit for the historical H6 source freeze.

The H6 freeze intentionally records byte hashes.  A Windows checkout can therefore
fail its original byte-for-byte replay solely because Git materialized text files
with different line endings.  This module does not alter or replace that strict
validator.  It independently distinguishes newline-only differences from semantic
source drift while preserving exact matching for binary inputs.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

from . import h6_fresh_process_memory_gate as h6
from .contracts import canonical_bytes


AUDIT_SCHEMA = "cm-h6-freeze-portability-audit/v1"
DEFAULT_FREEZE = (
    "docs/research/verification/"
    "cm-h6-fresh-process-memory-freeze-2026-09-08/FREEZE.json"
)
TEXT_SUFFIXES = frozenset({".c", ".json", ".md", ".py"})


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _bytes_digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _record_fields(record: Mapping[str, Any]) -> tuple[str, int, str]:
    relative = record.get("path")
    byte_count = record.get("bytes")
    digest = record.get("sha256")
    _require(isinstance(relative, str) and bool(relative), "file record path")
    _require(isinstance(byte_count, int) and byte_count >= 0, "file record bytes")
    _require(
        isinstance(digest, str)
        and len(digest) == 64
        and all(character in "0123456789abcdef" for character in digest),
        "file record SHA-256",
    )
    return relative, byte_count, digest


def _resolved_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    _require(path.is_relative_to(root) and path.is_file(), f"missing bound file: {relative}")
    return path


def _newline_variants(raw: bytes) -> list[tuple[str, bytes]]:
    """Return unique raw, LF, and CRLF byte variants in preference order."""

    variants = [("byte_exact", raw)]
    lf = raw.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    for name, value in (("lf_equivalent", lf), ("crlf_equivalent", crlf)):
        if all(value != existing for _, existing in variants):
            variants.append((name, value))
    return variants


def match_file_record(
    project_root: str | Path,
    record: Mapping[str, Any],
    *,
    allow_text_line_endings: bool | None = None,
) -> dict[str, Any]:
    """Match one frozen record, allowing only line-ending changes for text files."""

    root = Path(project_root).resolve()
    relative, expected_bytes, expected_digest = _record_fields(record)
    path = _resolved_file(root, relative)
    raw = path.read_bytes()
    is_text = (
        path.suffix.lower() in TEXT_SUFFIXES
        if allow_text_line_endings is None
        else allow_text_line_endings
    )
    variants = _newline_variants(raw) if is_text else [("byte_exact", raw)]
    match_mode = next(
        (
            name
            for name, value in variants
            if len(value) == expected_bytes and _bytes_digest(value) == expected_digest
        ),
        None,
    )
    return {
        "path": relative,
        "match": match_mode is not None,
        "match_mode": match_mode or "semantic_or_binary_mismatch",
        "text_line_endings_allowed": is_text,
        "current_bytes": len(raw),
        "current_sha256": _bytes_digest(raw),
        "frozen_bytes": expected_bytes,
        "frozen_sha256": expected_digest,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_freeze_document(
    freeze: Mapping[str, Any], project_root: str | Path
) -> dict[str, Any]:
    """Audit H6 bindings without rebuilding, executing, or modifying the freeze."""

    root = Path(project_root).resolve()
    blockers: list[str] = []

    if freeze.get("schema") != h6.SCHEMA:
        blockers.append("freeze_schema_mismatch")
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    if freeze.get("freeze_sha256") != _digest(core):
        blockers.append("freeze_digest_mismatch")

    closure = freeze.get("source_closure")
    if not isinstance(closure, list):
        closure = []
        blockers.append("source_closure_missing")
    if freeze.get("source_closure_sha256") != _digest(closure):
        blockers.append("source_closure_digest_mismatch")

    closure_paths = [record.get("path") for record in closure if isinstance(record, Mapping)]
    if closure_paths != list(h6.SOURCE_CLOSURE):
        blockers.append("source_closure_path_or_order_mismatch")
    if len(closure_paths) != len(closure):
        blockers.append("source_closure_record_malformed")

    bindings: list[dict[str, Any]] = []
    for index, record in enumerate(closure):
        try:
            _require(isinstance(record, Mapping), "source closure record")
            bindings.append(match_file_record(root, record))
        except (OSError, ValueError) as exc:
            path = record.get("path") if isinstance(record, Mapping) else f"index:{index}"
            bindings.append(
                {
                    "path": path,
                    "match": False,
                    "match_mode": "invalid_or_missing_record",
                    "error": str(exc),
                }
            )

    explicit_records = (
        ("parent_freeze", freeze.get("parent_freeze"), None),
        ("parent_oracles", freeze.get("parent_oracles"), None),
        ("native_library", freeze.get("native_library"), False),
    )
    for name, record, allow_text in explicit_records:
        try:
            _require(isinstance(record, Mapping), f"{name} record")
            result = match_file_record(
                root, record, allow_text_line_endings=allow_text
            )
            result["binding"] = name
            bindings.append(result)
        except (OSError, ValueError) as exc:
            bindings.append(
                {
                    "path": name,
                    "binding": name,
                    "match": False,
                    "match_mode": "invalid_or_missing_record",
                    "error": str(exc),
                }
            )

    mismatches = [record["path"] for record in bindings if not record["match"]]
    if mismatches:
        blockers.append("semantic_or_binary_binding_mismatch")

    try:
        parent_record = freeze["parent_freeze"]
        parent = _load_json(_resolved_file(root, parent_record["path"]))
        parent_core = {key: parent[key] for key in parent if key != "freeze_sha256"}
        if parent.get("freeze_sha256") != _digest(parent_core):
            blockers.append("parent_freeze_canonical_digest_mismatch")
        if parent.get("freeze_sha256") != parent_record.get("canonical_sha256"):
            blockers.append("parent_freeze_binding_mismatch")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        blockers.append("parent_freeze_unreadable")

    try:
        oracle_record = freeze["parent_oracles"]
        oracles = _load_json(_resolved_file(root, oracle_record["path"]))
        oracle_core = {key: oracles[key] for key in oracles if key != "oracles_sha256"}
        if oracles.get("oracles_sha256") != _digest(oracle_core):
            blockers.append("parent_oracles_canonical_digest_mismatch")
        if oracles.get("parent_freeze_sha256") != freeze["parent_freeze"].get(
            "canonical_sha256"
        ):
            blockers.append("parent_oracles_freeze_binding_mismatch")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        blockers.append("parent_oracles_unreadable")

    try:
        schedule = list(h6.expected_schedule_rows(freeze))
        expected_rows = freeze.get("expected_rows")
        if len(schedule) != expected_rows or expected_rows != 708:
            blockers.append("schedule_cardinality_mismatch")
        if len({row["row_id"] for row in schedule}) != len(schedule):
            blockers.append("schedule_identity_collision")
    except (KeyError, TypeError, ValueError):
        schedule = []
        blockers.append("schedule_unreadable")

    modes = Counter(record["match_mode"] for record in bindings)
    unique_blockers = list(dict.fromkeys(blockers))
    if unique_blockers:
        status = "rejected"
    elif modes.get("lf_equivalent", 0) or modes.get("crlf_equivalent", 0):
        status = "verified_line_ending_equivalent"
    else:
        status = "verified_byte_exact"

    return {
        "schema": AUDIT_SCHEMA,
        "status": status,
        "freeze_sha256": freeze.get("freeze_sha256"),
        "source_checkpoint": freeze.get("source_checkpoint"),
        "strict_h6_validator_replaced": False,
        "frozen_artifact_modified": False,
        "benchmark_executed": False,
        "schedule_rows_verified": len(schedule),
        "binding_count": len(bindings),
        "match_modes": dict(sorted(modes.items())),
        "semantic_or_binary_mismatches": mismatches,
        "blockers": unique_blockers,
        "bindings": bindings,
    }


def audit_h6_freeze(
    project_root: str | Path,
    freeze_path: str | Path = DEFAULT_FREEZE,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    path = Path(freeze_path)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    _require(path.is_relative_to(root) and path.is_file(), "H6 freeze path")
    freeze = _load_json(path)
    _require(isinstance(freeze, Mapping), "H6 freeze document")
    return audit_freeze_document(freeze, root)
