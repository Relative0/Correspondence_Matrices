"""Fail-closed task, artifact, lifecycle, and result contracts.

The comparative program measures methods only when they deliver the same
declared artifact.  These validators intentionally accept plain JSON objects
so frozen plans can be inspected without importing a backend.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any


CONTRACT_SCHEMA = "cm-comparative-contract/v1"
RESULT_SCHEMA = "cm-comparative-result/v1"
MAX_VARIABLES = 4096
MAX_QUERIES = 1_000_000
MAX_TIMING_STAGES = 64
MAX_TEXT = 256
SHA256 = re.compile(r"[0-9a-f]{64}")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/+-]{0,255}")

TASKS = frozenset(
    {
        "ir_preparation",
        "complete_relation",
        "exact_count",
        "sat_status",
        "witness",
        "equivalence_delta",
        "partial_context",
        "version_history",
        "structural_reload",
        "streamed_relation",
        "feasibility_frontier",
        "gf2_decomposition",
    }
)

ARTIFACT_KINDS = frozenset(
    {
        "ordered_cm_ir",
        "flat_program",
        "dense_cm",
        "packed_bigint",
        "packed_words",
        "truth_vector_u8",
        "reduced_bigint",
        "reduced_words",
        "restored_full",
        "streamed_chunks",
        "scalar_count",
        "boolean_status",
        "witness_assignment",
        "delta_count",
        "context_answers",
        "history_answers",
        "serialized_structure",
        "frontier_outcome",
        "exact_gf2_artifact",
    }
)

LIFECYCLES = frozenset(
    {
        "fresh_process",
        "fresh_engine",
        "resident_engine",
        "serialized_reload",
    }
)

RESULT_STATUSES = frozenset(
    {
        "ok",
        "refused",
        "timeout",
        "memory_limit",
        "output_limit",
        "error",
        "mismatch",
    }
)

_TASK_ARTIFACTS = {
    "ir_preparation": {"ordered_cm_ir", "flat_program"},
    "complete_relation": {
        "dense_cm",
        "packed_bigint",
        "packed_words",
        "truth_vector_u8",
        "reduced_bigint",
        "reduced_words",
        "restored_full",
    },
    "exact_count": {"scalar_count"},
    "sat_status": {"boolean_status"},
    "witness": {"witness_assignment"},
    "equivalence_delta": {"boolean_status", "delta_count"},
    "partial_context": {"context_answers"},
    "version_history": {"history_answers"},
    "structural_reload": {"serialized_structure"},
    "streamed_relation": {"streamed_chunks"},
    "feasibility_frontier": {"frontier_outcome"},
    "gf2_decomposition": {"exact_gf2_artifact"},
}

_FULL_ONLY = {"dense_cm", "packed_bigint", "packed_words", "truth_vector_u8", "restored_full", "streamed_chunks"}
_REDUCED_ONLY = {"reduced_bigint", "reduced_words"}
_ORDERED_ARTIFACTS = _FULL_ONLY | _REDUCED_ONLY | {"witness_assignment", "context_answers", "history_answers"}


class ContractError(ValueError):
    """A frozen request/result violated its declared comparison contract."""


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ContractError(message)


def canonical_bytes(value: Any) -> bytes:
    """Canonical finite JSON for identities and immutable plan records."""
    try:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ContractError("record is not canonical finite JSON") from exc
    return payload.encode("ascii")


def contract_digest(contract: Mapping[str, Any]) -> str:
    validate_contract(contract)
    return hashlib.sha256(canonical_bytes(contract)).hexdigest()


def _identifier(value: Any, field: str) -> str:
    require(isinstance(value, str) and IDENTIFIER.fullmatch(value) is not None, f"invalid {field}")
    return value


def _variables(value: Any, field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    require(isinstance(value, list), f"{field} must be a list")
    require((allow_empty or value) and len(value) <= MAX_VARIABLES, f"invalid {field} length")
    names = tuple(_identifier(name, field) for name in value)
    require(len(set(names)) == len(names), f"duplicate {field}")
    return names


def _fixed(value: Any, variables: tuple[str, ...]) -> dict[str, int]:
    require(isinstance(value, list) and len(value) <= len(variables), "fixed assignments must be a bounded list")
    output: dict[str, int] = {}
    for row in value:
        require(isinstance(row, dict) and set(row) == {"variable", "value"}, "fixed assignment fields")
        variable = _identifier(row["variable"], "fixed variable")
        bit = row["value"]
        require(variable in variables and variable not in output and type(bit) is int and bit in (0, 1),
                "invalid fixed assignment")
        output[variable] = bit
    return output


def validate_contract(record: Mapping[str, Any]) -> dict[str, Any]:
    require(isinstance(record, Mapping), "contract must be an object")
    require(
        set(record)
        == {"schema", "contract_id", "task", "artifact", "lifecycle", "queries", "validation"},
        "contract fields",
    )
    require(record["schema"] == CONTRACT_SCHEMA, "contract schema")
    contract_id = _identifier(record["contract_id"], "contract id")
    task = record["task"]
    lifecycle = record["lifecycle"]
    queries = record["queries"]
    require(task in TASKS and lifecycle in LIFECYCLES, "unknown task or lifecycle")
    require(type(queries) is int and 1 <= queries <= MAX_QUERIES, "invalid query count")

    artifact = record["artifact"]
    require(
        isinstance(artifact, Mapping)
        and set(artifact)
        == {"kind", "variable_order", "output_order", "fixed", "output_scope", "restoration", "stream"},
        "artifact fields",
    )
    kind = artifact["kind"]
    scope = artifact["output_scope"]
    restoration = artifact["restoration"]
    require(kind in ARTIFACT_KINDS and kind in _TASK_ARTIFACTS[task], "artifact does not match task")
    require(scope in {"full", "reduced", "not_applicable"}, "invalid output scope")
    require(restoration in {"none", "included"}, "invalid restoration")
    variables = _variables(artifact["variable_order"], "variable order")
    output = _variables(artifact["output_order"], "output order")
    fixed = _fixed(artifact["fixed"], variables)
    require(set(output).issubset(variables), "output order outside variable universe")

    if kind in _FULL_ONLY:
        require(scope == "full" and output == variables, "full artifact must preserve the complete declared order")
    elif kind in _REDUCED_ONLY:
        require(scope == "reduced" and output and set(output) == set(variables) - set(fixed),
                "reduced artifact must contain exactly the unfixed variables")
        require(restoration == "none", "reduced artifact cannot claim included restoration")
    elif kind in _ORDERED_ARTIFACTS:
        require(output, "ordered artifact needs output variables")
    else:
        require(scope == "not_applicable" and not output and restoration == "none",
                "scalar/structural artifact cannot declare relation axes")
    if restoration == "included":
        require(kind == "restored_full", "included restoration requires restored_full artifact")
    if kind == "restored_full":
        require(restoration == "included", "restored_full must charge included restoration")

    stream = artifact["stream"]
    if kind == "streamed_chunks":
        require(
            isinstance(stream, Mapping)
            and set(stream) == {"chunk_bits", "ordering"}
            and type(stream["chunk_bits"]) is int
            and 64 <= stream["chunk_bits"] <= (1 << 30)
            and stream["chunk_bits"] % 64 == 0
            and stream["ordering"] == "assignment_msb_first",
            "invalid stream contract",
        )
    else:
        require(stream is None, "nonstream artifact has stream settings")

    validation = record["validation"]
    require(
        isinstance(validation, Mapping)
        and set(validation) == {"oracle", "validation_in_timed_span", "required_output_sha256"},
        "validation fields",
    )
    _identifier(validation["oracle"], "oracle")
    require(type(validation["validation_in_timed_span"]) is bool, "validation timing flag")
    expected = validation["required_output_sha256"]
    require(expected is None or (isinstance(expected, str) and SHA256.fullmatch(expected)), "output SHA-256")
    require(not validation["validation_in_timed_span"], "correctness validation must remain outside comparative timing")

    return {
        "contract_id": contract_id,
        "task": task,
        "kind": kind,
        "lifecycle": lifecycle,
        "queries": queries,
        "variable_order": variables,
        "output_order": output,
        "fixed": fixed,
        "output_scope": scope,
        "restoration": restoration,
    }


def _timings(value: Any) -> dict[str, int]:
    require(isinstance(value, Mapping) and 0 < len(value) <= MAX_TIMING_STAGES, "timing fields")
    output: dict[str, int] = {}
    for key, item in value.items():
        name = _identifier(key, "timing stage")
        require(type(item) is int and 0 <= item <= (1 << 63) - 1, "invalid timing value")
        output[name] = item
    require("task_total_ns" in output, "missing task total")
    require(all(value <= output["task_total_ns"] for key, value in output.items() if key != "task_total_ns"),
            "timing stage exceeds task total")
    return output


def validate_result(record: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_contract(contract)
    require(isinstance(record, Mapping), "result must be an object")
    require(
        set(record)
        == {
            "schema",
            "contract_sha256",
            "case_id",
            "arm",
            "status",
            "reason",
            "timings_ns",
            "artifact",
            "resources",
            "identity",
        },
        "result fields",
    )
    require(record["schema"] == RESULT_SCHEMA and record["contract_sha256"] == contract_digest(contract),
            "result contract identity")
    _identifier(record["case_id"], "case id")
    _identifier(record["arm"], "arm")
    status = record["status"]
    reason = record["reason"]
    require(status in RESULT_STATUSES and isinstance(reason, str) and len(reason) <= MAX_TEXT, "result status/reason")
    timings = _timings(record["timings_ns"])
    require(isinstance(record["resources"], Mapping) and isinstance(record["identity"], Mapping),
            "resource/identity records")
    canonical_bytes(record["resources"])
    canonical_bytes(record["identity"])

    artifact = record["artifact"]
    if status == "ok":
        require(reason == "completed" and isinstance(artifact, Mapping), "successful result artifact")
        require(
            set(artifact) == {"kind", "output_scope", "output_order", "bytes", "sha256"},
            "result artifact fields",
        )
        require(artifact["kind"] == normalized["kind"] and artifact["output_scope"] == normalized["output_scope"],
                "result artifact contract mismatch")
        result_order = _variables(artifact["output_order"], "result output order")
        require(result_order == normalized["output_order"], "result output order mismatch")
        require(type(artifact["bytes"]) is int and 0 <= artifact["bytes"] <= (1 << 63) - 1,
                "result artifact byte count")
        require(isinstance(artifact["sha256"], str) and SHA256.fullmatch(artifact["sha256"]),
                "result artifact SHA-256")
        expected = contract["validation"]["required_output_sha256"]
        require(expected is None or artifact["sha256"] == expected, "independent output digest mismatch")
    else:
        require(reason and artifact is None, "failed result must retain reason and no artifact")

    return {"status": status, "task_total_ns": timings["task_total_ns"], "artifact": artifact}
