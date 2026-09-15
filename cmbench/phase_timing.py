"""Opt-in nested wall/CPU observations; legacy benchmark timers are independent.

Only exclusive spans within one capture partition its observed boundary. Inclusive
parents, legacy timers, and separately observed API return time must not be summed.
Recorder overhead remains in the enclosing exclusive span. Never use a captured
run as an uninstrumented performance sample.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import time


SCHEMA = "cm-family-phases-v1"
_ACTIVE: ContextVar["PhaseRecorder | None"] = ContextVar("cm_family_timing", default=None)


def active_recorder():
    """Internal opt-in hook; callers should enter ``PhaseRecorder.activate``."""
    return _ACTIVE.get()


class PhaseRecorder:
    def __init__(self, *, wall_clock=time.perf_counter_ns, cpu_clock=time.process_time_ns):
        self.wall_clock = wall_clock
        self.cpu_clock = cpu_clock
        self.records: list[dict] = []
        self._stack: list[dict] = []

    @contextmanager
    def activate(self):
        from cm_ir import _IR_PHASE_OBSERVER

        token = _ACTIVE.set(self)
        ir_token = _IR_PHASE_OBSERVER.set(self)
        try:
            yield self
        finally:
            _IR_PHASE_OBSERVER.reset(ir_token)
            _ACTIVE.reset(token)

    def wrap(self, name, function):
        @wraps(function)
        def observed(*args, **kwargs):
            with self.span(name):
                return function(*args, **kwargs)
        return observed

    @contextmanager
    def span(self, name: str, boundary: str = "function_entry_to_return"):
        record = {
            "id": len(self.records), "parent": self._stack[-1]["id"] if self._stack else None,
            "phase": name, "boundary": boundary, "status": "running",
        }
        self.records.append(record)
        self._stack.append(record)
        wall0, cpu0 = self.wall_clock(), self.cpu_clock()
        try:
            yield record
        except BaseException as exc:
            record.update(status="error", exception_type=type(exc).__name__)
            raise
        else:
            record["status"] = "ok"
        finally:
            cpu1, wall1 = self.cpu_clock(), self.wall_clock()
            self._stack.pop()
            wall, cpu = wall1 - wall0, cpu1 - cpu0
            record.update(
                wall_ns=wall, cpu_ns=cpu,
                exclusive_wall_ns=wall - record.pop("_children_wall_ns", 0),
                exclusive_cpu_ns=cpu - record.pop("_children_cpu_ns", 0),
                span_kind="inclusive_with_exclusive_partition",
            )
            if self._stack:
                parent = self._stack[-1]
                parent["_children_wall_ns"] = parent.get("_children_wall_ns", 0) + wall
                parent["_children_cpu_ns"] = parent.get("_children_cpu_ns", 0) + cpu

    def snapshot(self):
        if self._stack:
            raise RuntimeError("cannot serialize an active timing capture")
        return {"schema": SCHEMA, "instrumented": True, "records": [dict(r) for r in self.records]}


def phase_call(name, function, /, *args, **kwargs):
    recorder = _ACTIVE.get()
    if recorder is None:
        return function(*args, **kwargs)
    with recorder.span(name):
        return function(*args, **kwargs)


def timed_phase(name):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            return phase_call(name, function, *args, **kwargs)
        return wrapped
    return decorate
