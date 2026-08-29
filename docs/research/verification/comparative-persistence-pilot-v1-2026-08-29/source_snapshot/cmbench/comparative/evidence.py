"""Append-only cell evidence, fail-closed resume, and atomic publication."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .contracts import RESULT_STATUSES, canonical_bytes


TERMINAL = RESULT_STATUSES
MAX_LEDGER_BYTES = 256 << 20
MAX_RECORD_BYTES = 1 << 20


def append_record(path: Path, record: dict[str, Any]) -> None:
    payload = canonical_bytes(record) + b"\n"
    if len(payload) > MAX_RECORD_BYTES:
        raise ValueError("ledger record exceeds bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("ledger append made no progress")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read_ledger(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > MAX_LEDGER_BYTES:
        raise ValueError("missing/oversized ledger")
    raw = path.read_bytes()
    states: dict[str, dict[str, Any]] = {}
    partial_tail = False
    lines = raw.splitlines()
    for index, line in enumerate(lines):
        try:
            def pairs(items):
                value = {}
                for key, item in items:
                    if key in value:
                        raise ValueError("duplicate JSON key")
                    value[key] = item
                return value

            def constant(_value):
                raise ValueError("nonfinite JSON constant")

            row = json.loads(line, object_pairs_hook=pairs, parse_constant=constant)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            if index != len(lines) - 1 or raw.endswith(b"\n"):
                raise ValueError("corrupt complete ledger record")
            partial_tail = True
            break
        if not isinstance(row, dict) or not isinstance(row.get("cell_id"), str):
            raise ValueError("invalid ledger record")
        status = row.get("status")
        if status not in TERMINAL | {"running"}:
            raise ValueError("unknown ledger status")
        prior = states.get(row["cell_id"])
        if prior is None:
            if status != "running":
                raise ValueError("terminal record without running record")
        elif prior["status"] != "running" or status == "running":
            raise ValueError("duplicate/invalid cell transition")
        elif prior.get("request_sha256") != row.get("request_sha256"):
            raise ValueError("cell request identity changed")
        states[row["cell_id"]] = row
    return {
        "states": states,
        "partial_tail": partial_tail,
        "unfinished": sorted(cell for cell, row in states.items() if row["status"] == "running"),
    }


def resume_cells(plan: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    if state["partial_tail"] or state["unfinished"]:
        raise ValueError("ledger requires audit before resume")
    planned = {row["cell_id"]: row for row in plan["cells"]}
    unexpected = set(state["states"]) - set(planned)
    if unexpected:
        raise ValueError("ledger contains unexpected cells")
    return [row for row in plan["cells"] if row["cell_id"] not in state["states"]]


def reconcile(plan: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    planned = {row["cell_id"] for row in plan["cells"]}
    observed = set(state["states"])
    counts: dict[str, int] = {}
    for row in state["states"].values():
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {
        "planned_cells": len(planned),
        "observed_cells": len(observed),
        "missing_cells": sorted(planned - observed),
        "unexpected_cells": sorted(observed - planned),
        "unfinished_cells": state["unfinished"],
        "partial_ledger_tail": state["partial_tail"],
        "statuses": dict(sorted(counts.items())),
        "complete": planned == observed and not state["unfinished"] and not state["partial_tail"],
    }


def publish_json(path: Path, value: Any) -> None:
    """Publish complete JSON atomically without replacing an existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode("utf-8") + b"\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    else:
        temporary.unlink()
