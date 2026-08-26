from __future__ import annotations

import atexit
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Protocol
import uuid

from .schema import CONTENT_MODE, SCHEMA_VERSION, validate_trace_event


class TraceSink(Protocol):
    @property
    def enabled(self) -> bool: ...

    def emit(self, event_type: str, **payload: Any) -> bool: ...

    def close(self) -> None: ...

    def stats(self) -> dict[str, Any]: ...


class NullTraceSink:
    enabled = False

    def emit(self, event_type: str, **payload: Any) -> bool:
        return False

    def close(self) -> None:
        return None

    def stats(self) -> dict[str, Any]:
        return {
            "enabled": False,
            "events_written": 0,
            "dropped_events": 0,
            "files": [],
            "bytes_written": 0,
            "io_error_count": 0,
        }


class JsonlTraceSink:
    """Bounded, fail-contained, metrics-only JSONL trace writer.

    Existing base or rotation files are never overwritten. Runtime I/O errors
    disable tracing and are exposed through :meth:`stats`, but do not escape
    from :meth:`emit` into the benchmark computation.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        max_bytes: int = 1 << 20,
        max_files: int = 1,
        flush_every: int = 64,
        session_id: str | None = None,
    ) -> None:
        if int(max_bytes) < 1024:
            raise ValueError("max_bytes must be >= 1024")
        if int(max_files) < 1:
            raise ValueError("max_files must be >= 1")
        if int(flush_every) < 1:
            raise ValueError("flush_every must be >= 1")
        self.base_path = Path(path)
        self.max_bytes = int(max_bytes)
        self.max_files = int(max_files)
        self.flush_every = int(flush_every)
        self.session_id = session_id or hashlib.sha256(uuid.uuid4().bytes).hexdigest()
        if len(self.session_id) < 16:
            raise ValueError("session_id is too short")
        self._sequence = 0
        self._file_index = 0
        self._stream = None
        self._current_bytes = 0
        self._events_since_flush = 0
        self._events_written = 0
        self._dropped_events = 0
        self._bytes_written = 0
        self._io_error_count = 0
        self._last_io_error_type: str | None = None
        self._closed = False
        self._disabled = False
        self._files: list[str] = []
        self._reserve_bytes = min(512, self.max_bytes // 2)
        self._open_current_file()
        atexit.register(self.close)
        self.emit("session_start", phase="trace")

    @property
    def enabled(self) -> bool:
        return not self._closed and not self._disabled and self._stream is not None

    def _path_for_index(self, index: int) -> Path:
        if index == 0:
            return self.base_path
        suffix = self.base_path.suffix or ".jsonl"
        stem = self.base_path.name[: -len(suffix)] if self.base_path.suffix else self.base_path.name
        return self.base_path.with_name(f"{stem}.{index:04d}{suffix}")

    def _open_current_file(self) -> None:
        path = self._path_for_index(self._file_index)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = path.open("xb")
        self._files.append(str(path))
        self._current_bytes = 0
        self._events_since_flush = 0

    def _new_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        sequence = self._sequence
        self._sequence += 1
        event = {
            "schema_version": SCHEMA_VERSION,
            "content_mode": CONTENT_MODE,
            "session_id": self.session_id,
            "sequence": sequence,
            "event_id": f"{self.session_id}:{sequence}",
            "event_type": event_type,
            "utc_ns": time.time_ns(),
            "monotonic_ns": time.monotonic_ns(),
            "payload": payload,
        }
        return validate_trace_event(event)

    @staticmethod
    def _encode(event: dict[str, Any]) -> bytes:
        return (json.dumps(event, sort_keys=False, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")

    def _record_io_error(self, exc: OSError) -> None:
        self._io_error_count += 1
        self._last_io_error_type = type(exc).__name__
        self._disabled = True
        try:
            if self._stream is not None:
                self._stream.close()
        except OSError:
            pass
        self._stream = None

    def _rotate(self) -> bool:
        if self._file_index + 1 >= self.max_files:
            return False
        try:
            assert self._stream is not None
            self._stream.flush()
            self._stream.close()
            self._file_index += 1
            self._open_current_file()
            return True
        except FileExistsError:
            self._disabled = True
            self._stream = None
            raise
        except OSError as exc:
            self._record_io_error(exc)
            return False

    def _write_encoded(self, encoded: bytes) -> bool:
        if not self.enabled:
            return False
        try:
            assert self._stream is not None
            self._stream.write(encoded)
            self._current_bytes += len(encoded)
            self._bytes_written += len(encoded)
            self._events_written += 1
            self._events_since_flush += 1
            if self._events_since_flush >= self.flush_every:
                self._stream.flush()
                self._events_since_flush = 0
            return True
        except OSError as exc:
            self._record_io_error(exc)
            return False

    def _write_drop_marker(self, reason: str) -> None:
        self._dropped_events += 1
        if not self.enabled:
            return
        marker = self._encode(
            self._new_event(
                "trace_drop",
                {"status": "dropped", "status_reason": reason, "event_count": self._dropped_events},
            )
        )
        if self._current_bytes + len(marker) <= self.max_bytes:
            self._write_encoded(marker)
        self._disabled = True

    def emit(self, event_type: str, **payload: Any) -> bool:
        if not self.enabled:
            self._dropped_events += 1
            return False
        event = self._new_event(event_type, dict(payload))
        encoded = self._encode(event)
        normal_limit = self.max_bytes - self._reserve_bytes
        if len(encoded) > normal_limit:
            self._write_drop_marker("event_exceeds_file_budget")
            return False
        if self._current_bytes + len(encoded) > normal_limit:
            if not self._rotate():
                self._write_drop_marker("trace_file_budget_exhausted")
                return False
        return self._write_encoded(encoded)

    def close(self) -> None:
        if self._closed:
            return
        if self.enabled:
            self.emit("session_end", phase="trace")
        try:
            if self._stream is not None:
                self._stream.flush()
                self._stream.close()
        except OSError as exc:
            self._record_io_error(exc)
        finally:
            self._stream = None
            self._closed = True

    def stats(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "closed": self._closed,
            "session_id": self.session_id,
            "events_written": self._events_written,
            "dropped_events": self._dropped_events,
            "files": list(self._files),
            "bytes_written": self._bytes_written,
            "io_error_count": self._io_error_count,
            "last_io_error_type": self._last_io_error_type,
        }

    def __enter__(self) -> "JsonlTraceSink":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
