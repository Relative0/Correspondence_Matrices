from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from cmbench.reporting.provenance import sha256_file

from .schema import TraceValidationError, validate_trace_event


class TraceFileError(ValueError):
    pass


def iter_trace_events(paths: Sequence[str | Path]) -> Iterator[dict[str, Any]]:
    for raw_path in paths:
        path = Path(raw_path)
        with path.open("r", encoding="ascii", newline="") as stream:
            for line_no, line in enumerate(stream, 1):
                if not line.strip():
                    raise TraceFileError(f"{path}:{line_no}: blank lines are not valid trace events")
                try:
                    raw = json.loads(line)
                    event = validate_trace_event(raw)
                except (json.JSONDecodeError, TraceValidationError) as exc:
                    raise TraceFileError(f"{path}:{line_no}: {exc}") from exc
                yield event


def load_trace_events(paths: Sequence[str | Path]) -> list[dict[str, Any]]:
    events = list(iter_trace_events(paths))
    by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_session[event["session_id"]].append(event)
    ordered: list[dict[str, Any]] = []
    for session_id in sorted(by_session):
        session_events = sorted(by_session[session_id], key=lambda item: item["sequence"])
        seen: set[int] = set()
        last = -1
        for event in session_events:
            sequence = int(event["sequence"])
            if sequence in seen:
                raise TraceFileError(f"duplicate sequence {sequence} in session {session_id}")
            if sequence <= last:
                raise TraceFileError(f"non-increasing sequence in session {session_id}")
            seen.add(sequence)
            last = sequence
            ordered.append(event)
    return ordered


def summarize_trace_files(paths: Sequence[str | Path]) -> dict[str, Any]:
    normalized = [Path(path) for path in paths]
    events = load_trace_events(normalized)
    event_counts = Counter(event["event_type"] for event in events)
    sessions = sorted({event["session_id"] for event in events})
    expression_counts = Counter(
        event["payload"].get("expression_digest")
        for event in events
        if event["payload"].get("expression_digest") is not None
    )
    return {
        "schema_version": events[0]["schema_version"] if events else None,
        "content_modes": sorted({event["content_mode"] for event in events}),
        "input_files": [
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in normalized
        ],
        "event_count": len(events),
        "event_counts": dict(sorted(event_counts.items())),
        "session_count": len(sessions),
        "sessions": sessions,
        "expression_observation_count": int(sum(expression_counts.values())),
        "unique_expression_count": len(expression_counts),
        "repeated_expression_count": sum(1 for count in expression_counts.values() if count > 1),
        "max_expression_observations": max(expression_counts.values(), default=0),
        "trace_drop_count": int(event_counts.get("trace_drop", 0)),
        "logical_replay_only": True,
    }


def write_json_exclusive(path: str | Path, payload: Any) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(encoded)
    return out
