"""Opt-in, metrics-only CM workload tracing."""

from .replay import load_trace_events, summarize_trace_files, write_json_exclusive
from .opportunity import SCREEN_VERSION, screen_trace_events, screen_trace_files
from .schema import SCHEMA_VERSION, TraceValidationError, validate_trace_event
from .sink import JsonlTraceSink, NullTraceSink, TraceSink
from .workload_manifest import (
    MANIFEST_SCHEMA_VERSION,
    WorkloadManifestError,
    validate_workload_manifest,
)

__all__ = [
    "JsonlTraceSink",
    "MANIFEST_SCHEMA_VERSION",
    "NullTraceSink",
    "SCHEMA_VERSION",
    "SCREEN_VERSION",
    "TraceSink",
    "TraceValidationError",
    "WorkloadManifestError",
    "load_trace_events",
    "screen_trace_events",
    "screen_trace_files",
    "summarize_trace_files",
    "validate_trace_event",
    "validate_workload_manifest",
    "write_json_exclusive",
]
