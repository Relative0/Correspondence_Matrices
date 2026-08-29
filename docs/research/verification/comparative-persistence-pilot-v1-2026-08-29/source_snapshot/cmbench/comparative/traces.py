"""Provenance and claim controls for comparative task traces.

Generated contexts, reconstructed public events and observed user sessions are
different evidence classes.  This module makes that distinction machine-
checkable and refuses a natural-session claim unless the trace has a bounded,
content-identified, privacy-reviewed observed source with record identities.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scripts import cm_measurement_verify as scalar
from scripts import cm_session_contracts as sessions

from .contracts import canonical_bytes
from .tasks import TASKS, validate_trace


CORPUS_SCHEMA = "cm-comparative-trace-corpus/v1"
MAX_CORPUS_BYTES = 8 << 20
MAX_TRACES = 4096
MAX_SOURCE_RECORDS = 4096
SHA256 = re.compile(r"[0-9a-f]{64}")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/+-]{0,255}")
SOURCE_KINDS = frozenset({"observed_dataset", "public_event_log", "generated_control"})
PROVENANCE_KINDS = frozenset(
    {"observed_natural", "reconstructed_public_events", "generated_control", "outcome_selected_control"}
)
SELECTION_KINDS = frozenset({"predeclared", "complete_source", "generated", "outcome_selected"})
PRIVACY_KINDS = frozenset(
    {"public_nonpersonal", "approved_deidentified", "restricted_not_publishable", "synthetic_no_person_data"}
)


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _identifier(value: Any, field: str) -> str:
    require(isinstance(value, str) and IDENTIFIER.fullmatch(value) is not None, f"invalid {field}")
    return value


def _timestamp(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and len(value) <= 64, f"invalid {field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid {field}") from exc
    require(parsed.tzinfo is not None, f"{field} needs a timezone")
    return parsed


def _public_uri(value: Any) -> str:
    require(isinstance(value, str) and len(value) <= 2048, "source URI")
    parsed = urlparse(value)
    require(parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password,
            "public HTTPS source URI required")
    return value


def _validate_source(source: Any) -> dict[str, Any]:
    require(
        isinstance(source, Mapping)
        and set(source)
        == {
            "kind",
            "uri",
            "content_sha256",
            "license",
            "privacy",
            "captured_start",
            "captured_end",
        },
        "trace source fields",
    )
    kind = source["kind"]
    privacy = source["privacy"]
    digest = source["content_sha256"]
    require(kind in SOURCE_KINDS and privacy in PRIVACY_KINDS, "trace source kind/privacy")
    require(isinstance(digest, str) and SHA256.fullmatch(digest) is not None, "trace source content SHA-256")
    if kind == "generated_control":
        require(
            source["uri"] is None
            and source["license"] == "not_applicable"
            and privacy == "synthetic_no_person_data"
            and source["captured_start"] is None
            and source["captured_end"] is None,
            "generated source boundary",
        )
        return {"kind": kind, "privacy": privacy}
    _public_uri(source["uri"])
    require(isinstance(source["license"], str) and 1 <= len(source["license"]) <= 128,
            "observed source license required")
    started = _timestamp(source["captured_start"], "capture start")
    ended = _timestamp(source["captured_end"], "capture end")
    require(started <= ended and privacy != "synthetic_no_person_data", "observed source capture/privacy")
    return {"kind": kind, "privacy": privacy}


def validate_corpus(record: Any, scenarios: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Validate a complete trace corpus and return its permitted claim class."""
    require(
        isinstance(record, Mapping)
        and set(record) == {"schema", "corpus_id", "source", "scenarios", "traces"},
        "trace corpus fields",
    )
    require(record["schema"] == CORPUS_SCHEMA, "trace corpus schema")
    corpus_id = _identifier(record["corpus_id"], "corpus id")
    source = _validate_source(record["source"])
    require(isinstance(scenarios, Mapping) and scenarios, "scenario lookup required")

    declarations = record["scenarios"]
    require(isinstance(declarations, list) and declarations, "scenario declarations")
    declared: dict[str, Mapping[str, Any]] = {}
    for row in declarations:
        require(
            isinstance(row, Mapping)
            and set(row) == {"scenario_id", "scenario_sha256"},
            "scenario declaration fields",
        )
        scenario_id = _identifier(row["scenario_id"], "scenario id")
        require(scenario_id not in declared and scenario_id in scenarios, "unknown/duplicate scenario")
        scenario = scenarios[scenario_id]
        sessions.validate_scenario(scenario)
        require(
            row["scenario_sha256"] == hashlib.sha256(canonical_bytes(scenario)).hexdigest(),
            "scenario content identity",
        )
        declared[scenario_id] = scenario
    require(set(declared) == set(scenarios), "scenario declaration coverage")

    traces = record["traces"]
    require(isinstance(traces, list) and 1 <= len(traces) <= MAX_TRACES, "bounded trace list required")
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    natural = 0
    for row in traces:
        require(
            isinstance(row, Mapping)
            and set(row) == {"trace_id", "scenario_id", "task", "events", "provenance"},
            "trace row fields",
        )
        trace_id = _identifier(row["trace_id"], "trace id")
        scenario_id = _identifier(row["scenario_id"], "trace scenario id")
        task = row["task"]
        require(trace_id not in seen and scenario_id in declared and task in TASKS, "trace identity/task")
        seen.add(trace_id)
        validate_trace(declared[scenario_id], task, row["events"])
        provenance = row["provenance"]
        require(
            isinstance(provenance, Mapping)
            and set(provenance) == {"kind", "selection", "source_record_ids", "generator"},
            "trace provenance fields",
        )
        kind = provenance["kind"]
        selection = provenance["selection"]
        ids = provenance["source_record_ids"]
        generator = provenance["generator"]
        require(kind in PROVENANCE_KINDS and selection in SELECTION_KINDS, "trace provenance kind/selection")
        require(
            isinstance(ids, list)
            and len(ids) <= MAX_SOURCE_RECORDS
            and all(isinstance(item, str) and 1 <= len(item) <= 256 for item in ids)
            and len(set(ids)) == len(ids),
            "trace source record identities",
        )
        if kind == "observed_natural":
            require(
                source["kind"] == "observed_dataset"
                and selection in {"predeclared", "complete_source"}
                and ids
                and generator is None,
                "observed-natural provenance",
            )
            if source["privacy"] in {"public_nonpersonal", "approved_deidentified"}:
                natural += 1
        elif kind == "reconstructed_public_events":
            require(
                source["kind"] == "public_event_log"
                and selection in {"predeclared", "complete_source"}
                and ids
                and generator is None,
                "reconstructed-event provenance",
            )
        elif kind == "generated_control":
            require(
                source["kind"] == "generated_control"
                and selection == "generated"
                and not ids
                and isinstance(generator, str)
                and 1 <= len(generator) <= 256,
                "generated-control provenance",
            )
        else:
            require(
                selection == "outcome_selected"
                and isinstance(generator, str)
                and 1 <= len(generator) <= 256,
                "outcome-selected provenance",
            )
        counts[kind] += 1

    return {
        "corpus_id": corpus_id,
        "trace_count": len(traces),
        "scenario_count": len(declared),
        "tasks_covered": sorted({row["task"] for row in traces}),
        "provenance_counts": dict(sorted(counts.items())),
        "natural_trace_count": natural,
        "natural_claim_permitted": natural == len(traces),
        "publishable": source["privacy"] != "restricted_not_publishable",
    }


def load_corpus(path: Path, scenarios: Mapping[str, Mapping[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load a canonical bounded JSON corpus without following a linked file."""
    require(path.is_file() and not path.is_symlink() and not path.is_junction(), "trace corpus file")
    with path.open("rb") as handle:
        payload = handle.read(MAX_CORPUS_BYTES + 1)
    require(0 < len(payload) <= MAX_CORPUS_BYTES, "trace corpus byte bound")
    record = scalar.strict_json(payload)
    require(canonical_bytes(record) == payload, "trace corpus must use canonical JSON encoding")
    return record, validate_corpus(record, scenarios)


def generated_control_corpus(
    *, corpus_id: str, scenarios: Mapping[str, Mapping[str, Any]], trace_map: Mapping[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Create an explicitly non-natural corpus for existing generated controls."""
    require(set(trace_map) == set(TASKS), "generated trace map must cover all tasks")
    generator = {"name": "cm_comparative_bridge_traces/v1", "traces": trace_map}
    declarations = []
    rows = []
    for scenario_id, scenario in sorted(scenarios.items()):
        sessions.validate_scenario(scenario)
        declarations.append(
            {"scenario_id": scenario_id, "scenario_sha256": hashlib.sha256(canonical_bytes(scenario)).hexdigest()}
        )
        for task in TASKS:
            rows.append(
                {
                    "trace_id": f"{scenario_id}:{task}:generated",
                    "scenario_id": scenario_id,
                    "task": task,
                    "events": trace_map[task],
                    "provenance": {
                        "kind": "generated_control",
                        "selection": "generated",
                        "source_record_ids": [],
                        "generator": "cm_comparative_bridge_traces/v1",
                    },
                }
            )
    record = {
        "schema": CORPUS_SCHEMA,
        "corpus_id": corpus_id,
        "source": {
            "kind": "generated_control",
            "uri": None,
            "content_sha256": hashlib.sha256(canonical_bytes(generator)).hexdigest(),
            "license": "not_applicable",
            "privacy": "synthetic_no_person_data",
            "captured_start": None,
            "captured_end": None,
        },
        "scenarios": declarations,
        "traces": rows,
    }
    validate_corpus(record, scenarios)
    return record
