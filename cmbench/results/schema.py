from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TimingBreakdown:
    compile_s: float | None = None
    eval_s: float | None = None
    materialize_s: float | None = None
    extract_s: float | None = None
    correctness_s: float | None = None
    reorder_s: float | None = None
    cache_setup_s: float | None = None
    remote_start_s: float | None = None
    remote_wait_s: float | None = None
    remote_request_s: float | None = None
    remote_exec_s: float | None = None
    total_wall_s: float | None = None


@dataclass
class BackendResult:
    backend: str
    status: str = "ok"
    error: str | None = None
    timing: TimingBreakdown = field(default_factory=TimingBreakdown)
    ok: bool | None = None
    correctness_mode: str | None = None
    declined: bool | None = None
    result: Any | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def skipped(cls, backend: str, reason: str = "disabled") -> "BackendResult":
        return cls(backend=backend, status="skipped", error=reason)

    @classmethod
    def unavailable(cls, backend: str, reason: str) -> "BackendResult":
        return cls(backend=backend, status="unavailable", error=reason)

    @classmethod
    def error_result(cls, backend: str, exc: BaseException | str) -> "BackendResult":
        return cls(backend=backend, status="error", error=repr(exc) if not isinstance(exc, str) else exc)

    @classmethod
    def error(cls, backend: str, exc: BaseException | str) -> "BackendResult":
        return cls.error_result(backend, exc)
