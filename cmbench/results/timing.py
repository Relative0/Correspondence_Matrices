from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ArtifactKind(str, Enum):
    PACKED_TRUTH_FUNCTION = "packed_truth_function"
    TRUTH_TABLE_VECTOR = "truth_table_vector"
    SYMBOLIC_BDD = "symbolic_bdd"
    COMPILED_DAG = "compiled_dag"
    FLAT_PROGRAM = "flat_program"
    QUERY_RESULT = "query_result"


class TimingKind(str, Enum):
    SERIALIZATION = "serialization"
    COMPILATION = "compilation"
    BINDING_PREPARATION = "binding_preparation"
    CACHED_EXECUTION = "cached_execution"
    PACKED_EXECUTION = "packed_execution"
    EXTRACTION = "extraction"
    CORRECTNESS = "correctness"
    ORDER_GENERATION = "order_generation"
    ORDER_SEARCH = "order_search"
    DYNAMIC_REORDERING = "dynamic_reordering"
    END_TO_END = "end_to_end"


@dataclass(frozen=True)
class TimingDescriptor:
    artifact: ArtifactKind
    interval: TimingKind
    includes_preparation: bool = False
    includes_extraction: bool = False
    includes_correctness: bool = False


def comparison_compatibility(
    left: TimingDescriptor,
    right: TimingDescriptor,
    *,
    contextual: bool = False,
) -> tuple[bool, str]:
    if left.artifact != right.artifact:
        if contextual:
            return True, "contextual_different_artifacts"
        return False, f"artifact_mismatch:{left.artifact.value}!={right.artifact.value}"
    if left.interval != right.interval:
        if contextual:
            return True, "contextual_different_intervals"
        return False, f"timing_mismatch:{left.interval.value}!={right.interval.value}"
    if (
        left.includes_preparation != right.includes_preparation
        or left.includes_extraction != right.includes_extraction
        or left.includes_correctness != right.includes_correctness
    ):
        if contextual:
            return True, "contextual_different_boundaries"
        return False, "boundary_mismatch"
    return True, "equivalent"
