"""Freeze builder for the corrected architecture query-count follow-up."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .architecture_comparison_freeze import verify_freeze as verify_parent_freeze
from .architecture_query_ladder_followup import (
    FREEZE_SCHEMA,
    MEMORY_METHOD,
    QUERY_COUNTS,
    STAGES,
    validate_followup_freeze,
)
from .contracts import canonical_bytes


COMMIT = re.compile(r"[0-9a-f]{40}")
SOURCE_CLOSURE_PATHS = (
    "cmbench/comparative/architecture_query_ladder_followup.py",
    "cmbench/comparative/architecture_query_ladder_freeze.py",
    "scripts/cm_architecture_query_ladder_campaign.py",
    "scripts/crse_prepare_architecture_query_ladder_freeze.py",
    "scripts/crse_verify_architecture_query_ladder_freeze.py",
    "scripts/crse_verify_architecture_query_ladder_campaign.py",
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _binding(root: Path, relative: str) -> dict[str, Any]:
    path = (root / relative).resolve()
    _require(path.is_relative_to(root) and path.is_file(), f"missing follow-up input: {relative}")
    return {
        "path": relative,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def build_followup_freeze(
    *, project_root: Path, source_checkpoint: str,
    parent_freeze_path: str, parent_analysis_path: str, oracles_path: str,
) -> dict[str, Any]:
    root = project_root.resolve()
    _require(COMMIT.fullmatch(source_checkpoint) is not None, "follow-up source checkpoint")
    parent_binding = _binding(root, parent_freeze_path)
    analysis_binding = _binding(root, parent_analysis_path)
    oracle_binding = _binding(root, oracles_path)
    parent_freeze = json.loads((root / parent_freeze_path).read_text(encoding="utf-8"))
    verify_parent_freeze(parent_freeze, root)
    analysis = json.loads((root / parent_analysis_path).read_text(encoding="utf-8"))
    _require(
        analysis.get("status") == "verified_interpretation_complete"
        and analysis.get("measurement_limits", {}).get("q1_q4_q16_separately_timed") is False
        and analysis.get("measurement_limits", {}).get("per_arm_memory_interpretation_permitted") is False,
        "follow-up is not justified by the bound parent analysis",
    )
    parent_schedule = parent_freeze["schedules"]["B"]
    schedule = {
        "case_order": list(parent_schedule["case_order"]),
        "arms": list(parent_schedule["arms"]),
        "arm_orders": [list(order) for order in parent_schedule["arm_orders"]],
        "blocks": parent_schedule["blocks"],
        "query_counts": list(QUERY_COUNTS),
        "counterbalance_all_arm_positions_at_every_query_count": True,
        "selection_blind_to_followup_timings": True,
    }
    schedule["planned_cells"] = (
        len(schedule["case_order"]) * len(schedule["arms"])
        * len(schedule["arm_orders"]) * len(schedule["query_counts"])
    )
    closure = [_binding(root, relative) for relative in SOURCE_CLOSURE_PATHS]
    freeze = {
        "schema": FREEZE_SCHEMA,
        "status": "frozen_not_authorized",
        "date": "2026-09-03",
        "source_checkpoint": source_checkpoint,
        "parent_freeze": parent_binding,
        "parent_analysis": analysis_binding,
        "oracles": oracle_binding,
        "source_closure": closure,
        "source_closure_sha256": _digest(closure),
        "schedule": schedule,
        "measurement_contract": {
            "artifact": "explicit residual relation prefix with exact count, SAT flag, canonical witness, and digest",
            "timing": {
                "each_query_count_is_a_separate_cell": True,
                "stages": list(STAGES),
                "accounted_total_is_stage_sum": True,
                "fork_launch_overhead_in_timing": False,
                "reason": "fork is a measurement-isolation mechanism, not part of the backend task",
            },
            "memory": {
                "method": MEMORY_METHOD,
                "one_fresh_child_per_timed_cell": True,
                "timing_inside_child_excludes_fork": True,
                "reports_inherited_baseline_and_incremental_peak": True,
                "peak_source": "os.wait4 child rusage.ru_maxrss",
                "baseline_source": "/proc/self/statm immediately before fork",
                "interpretation": "descriptive total and incremental cell peak on the execution host",
            },
        },
        "publication_gates": {
            "zero_semantic_schedule_source_or_artifact_mismatches": True,
            "all_four_query_counts_separately_timed": True,
            "all_cells_have_isolated_memory_measurements": True,
            "native_minimum_case_speedup_floor_at_each_query_count": 0.95,
            "retain_all_unfavorable_cells": True,
            "cross_machine_claim_requires_separate_replication": True,
            "historical_windows_1_472x_retained": True,
            "no_universal_winner_headline": True,
        },
        "permissions": {
            "local_synthetic_functional_validation": True,
            "local_timing": False,
            "cloud_execution": False,
            "selector_fitting": False,
            "neural_training": False,
            "production_routing_change": False,
            "website_update": False,
            "publication": False,
        },
        "timing_evidence_produced": False,
        "memory_evidence_produced": False,
    }
    freeze["freeze_sha256"] = _digest(freeze)
    validate_followup_freeze(freeze)
    return freeze
