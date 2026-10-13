"""Frozen prospective workload for scalar-versus-batched native restrictions.

Freeze and oracle construction are deliberately clock-free.  Timed execution
is available only through the separately authorized campaign entry point.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
import gc
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics
import time
from typing import Any

from bitset_backend import (
    bitset_to_bool_array,
    build_bitset_env,
    clear_bitset_env_cache,
    clear_words_env_cache,
    eval_expr_bitset,
)
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cmbench.recognition.features import structural_digest

from .gf2_native_slot_batch import (
    NativeSlotBatchExecutor,
    prepare_bindings_many,
)
from .gf2_native_slots import compile_native_slot_arena, load_native_slot_library
from .gf2_wide_repeated_queries import (
    project_truth_vector,
    projection_indices,
    restrict_full_truth,
    semantic_document,
    semantic_row,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "crse-native-slot-batch-prospective-freeze/v1"
ORACLE_SCHEMA = "crse-native-slot-batch-prospective-oracles/v1"
MANIFEST_SCHEMA = "crse-native-slot-batch-prospective-artifacts/v1"
VERIFICATION_SCHEMA = "crse-native-slot-batch-prospective-verification/v1"
AUTHORIZATION_REQUEST_SCHEMA = "crse-native-slot-batch-authorization-request/v1"
AUTHORIZATION_SCHEMA = "crse-native-slot-batch-benchmark-authorization/v1"
RAW_SCHEMA = "crse-native-slot-batch-timed-cell/v1"
SEED = 2_026_091_001
WIDTHS = (17, 18, 19)
LIVE_WIDTHS = (7, 11, 15)
FAMILIES = ("andor", "xor_eqv", "mixed")
SHAPES = ("balanced_tree", "layered_sharing")
REPLICATES = 2
QUERY_COUNTS = (8, 32, 96)
BLOCKS = 12
ARMS = ("native_scalar_v1", "native_batch_v1")
PRIMARY_QUERY_COUNT = 96
STAGES = (
    "parse_normalization_ns",
    "representation_construction_ns",
    "binding_ns",
    "evaluation_ns",
    "delivery_ns",
    "serialization_ns_when_applicable",
    "cleanup_ns",
)
MIN_PRIMARY_SUM_SPEEDUP = 1.10
MIN_PRIMARY_CASE_WIN_FRACTION = 0.75
MIN_PRIMARY_CLUSTER_CI_LOW = 1.0
MIN_Q32_SUM_SPEEDUP = 1.0
BOOTSTRAP_DRAWS = 10_000
MAX_WALL_SECONDS = 7_200
CELL_TIMEOUT_SECONDS = 30
COMMIT = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")

PRIOR_IDENTITY_PATHS = (
    "docs/recognition/runs/query-ladder-source-blind-learning-freeze-20260904-001/FREEZE.json",
    "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json",
    "docs/recognition/c36_wide_repeated_query_dataset.json",
)
SOURCE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cmbench/recognition/features.py",
    "cmbench/comparative/gf2_wide_repeated_queries.py",
    "cmbench/comparative/gf2_native_slots.py",
    "cmbench/comparative/gf2_native_slot_batch.py",
    "cmbench/comparative/gf2_native_slot_batch_workload.py",
    "native/cm_fused_slots/fused_slot_executor.c",
    "native/cm_fused_slots_batch/fused_slot_executor_batch.c",
    "native/cm_fused_slots_batch/build_msvc.cmd",
    "scripts/build_cm_fused_slots_batch.py",
    "scripts/cm_native_slot_batch_freeze.py",
    "scripts/cm_native_slot_batch_campaign.py",
    "scripts/crse_native_slot_batch_freeze_verify.py",
    "scripts/crse_native_slot_batch_campaign_verify.py",
)


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_file_identity(root: Path, relative: str) -> dict[str, Any]:
    path = (root / relative).resolve()
    _require(path.is_relative_to(root) and path.is_file(), f"missing source: {relative}")
    payload = path.read_bytes().replace(b"\r\n", b"\n")
    return {
        "path": relative,
        "bytes_lf_normalized": len(payload),
        "sha256_lf_normalized": hashlib.sha256(payload).hexdigest(),
    }


def _rng(*parts: object) -> random.Random:
    payload = ":".join(str(part) for part in (SEED, *parts)).encode("ascii")
    return random.Random(int.from_bytes(hashlib.sha256(payload).digest(), "big"))


def _operators(family: str) -> tuple[type, ...]:
    if family == "andor":
        return (And, Or)
    if family == "xor_eqv":
        return (Xor, Eqv)
    if family == "mixed":
        return (And, Or, Xor, Imp, Eqv)
    raise ValueError("unknown batch workload family")


def _balanced_tree(n_vars: int, family: str, rng: random.Random) -> Expr:
    indices = list(range(n_vars))
    rng.shuffle(indices)
    level: list[Expr] = [Var(index) for index in indices]
    operators = _operators(family)
    while len(level) > 1:
        following: list[Expr] = []
        for offset in range(0, len(level), 2):
            if offset + 1 == len(level):
                following.append(level[offset])
                continue
            left, right = level[offset:offset + 2]
            if rng.randrange(4) == 0:
                left = Not(left)
            if rng.randrange(6) == 0:
                right = Not(right)
            following.append(rng.choice(operators)(left, right))
        level = following
    return level[0]


def _expression(
    n_vars: int, family: str, shape: str, replicate: int,
) -> Expr:
    rng = _rng("native-batch-expression", n_vars, family, shape, replicate)
    first = _balanced_tree(n_vars, family, rng)
    if shape == "balanced_tree":
        return first
    _require(shape == "layered_sharing", "unknown batch workload shape")
    second = _balanced_tree(n_vars, family, rng)
    operators = _operators(family)
    shared = operators[replicate % len(operators)](first, second)
    left = operators[(replicate + 1) % len(operators)](shared, Not(first))
    right = operators[(replicate + 2) % len(operators)](shared, Not(second))
    return operators[(replicate + 3) % len(operators)](left, right)


def build_query_trace(case_id: str, n_vars: int) -> list[dict[str, Any]]:
    _require(
        isinstance(case_id, str) and case_id and n_vars in WIDTHS,
        "batch workload query identity",
    )
    rows = []
    for query in range(max(QUERY_COUNTS)):
        live_count = LIVE_WIDTHS[query % len(LIVE_WIDTHS)]
        rng = _rng("native-batch-query", case_id, query)
        remaining_indices = sorted(rng.sample(range(n_vars), live_count))
        remaining_set = set(remaining_indices)
        fixed = [
            {"variable": f"x{index}", "value": rng.randrange(2)}
            for index in range(n_vars)
            if index not in remaining_set
        ]
        core = {
            "query": query,
            "fixed": fixed,
            "remaining_order": [f"x{index}" for index in remaining_indices],
        }
        rows.append({**core, "query_sha256": digest(core)})
    return rows


def _case_record(
    n_vars: int, family: str, shape: str, replicate: int,
) -> dict[str, Any]:
    expression = _expression(n_vars, family, shape, replicate)
    document = expr_to_json_dag(expression)
    case_id = (
        f"native-batch-prospective-{shape.replace('_', '-')}-"
        f"{family.replace('_', '-')}-k{n_vars}-r{replicate}"
    )
    trace = build_query_trace(case_id, n_vars)
    alpha = structural_digest(expression, alpha_rename=True)
    return {
        "case_id": case_id,
        "source_group_sha256": alpha,
        "n_vars": n_vars,
        "family": family,
        "shape": shape,
        "replicate": replicate,
        "expression_v2": document,
        "expression_v2_sha256": digest(document),
        "structural_digest": structural_digest(expression),
        "alpha_structural_digest": alpha,
        "query_trace": trace,
        "query_trace_sha256": digest(trace),
        # JSON object keys are strings. Normalize before hashing so numeric
        # versus lexicographic key ordering cannot break a saved freeze.
        "live_width_counts": {str(width): count for width, count in sorted(Counter(
            len(row["remaining_order"]) for row in trace
        ).items())},
    }


def generate_cases() -> list[dict[str, Any]]:
    cases = [
        _case_record(n_vars, family, shape, replicate)
        for n_vars in WIDTHS
        for family in FAMILIES
        for shape in SHAPES
        for replicate in range(REPLICATES)
    ]
    expected = len(WIDTHS) * len(FAMILIES) * len(SHAPES) * REPLICATES
    _require(len(cases) == expected == 36, "batch workload case count")
    _require(len({row["case_id"] for row in cases}) == expected, "case identities")
    _require(
        len({row["source_group_sha256"] for row in cases}) == expected,
        "source group identities",
    )
    return cases


def _prior_identities(root: Path) -> tuple[set[str], list[dict[str, Any]]]:
    identities: set[str] = set()
    bindings = []
    for relative in PRIOR_IDENTITY_PATHS:
        value = json.loads((root / relative).read_text(encoding="utf-8"))
        if "query-ladder-source-blind" in relative:
            rows = value["cohort"]["cases"]
            observed = {row["alpha_structural_digest"] for row in rows}
        elif "architecture_comparison_freeze" in relative:
            rows = value["fresh_corpus"]["single_root_cases"]
            observed = {row["alpha_structural_digest"] for row in rows}
        else:
            rows = value["cases"]
            observed = {
                structural_digest(
                    expr_from_json(row["expression_v2"]), alpha_rename=True,
                )
                for row in rows
            }
        identities.update(observed)
        bindings.append({
            **normalized_file_identity(root, relative),
            "identity_count": len(observed),
            "role": "structural_identity_exclusion_only",
            "timing_or_label_fields_read": False,
        })
    return identities, bindings


def build_schedule(cases: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    case_ids = tuple(row["case_id"] for row in cases)
    schedule = []
    for block in range(BLOCKS):
        case_order = list(case_ids)
        _rng("schedule-cases", block).shuffle(case_order)
        query_order = list(QUERY_COUNTS)
        _rng("schedule-query-counts", block).shuffle(query_order)
        for query_count in query_order:
            for case_position, case_id in enumerate(case_order):
                parity = int(hashlib.sha256(
                    f"{SEED}:{case_id}:{query_count}".encode("ascii")
                ).hexdigest(), 16) & 1
                arm_order = list(ARMS)
                if parity ^ (block & 1):
                    arm_order.reverse()
                for arm_position, arm in enumerate(arm_order):
                    schedule.append({
                        "block": block,
                        "query_count": query_count,
                        "case_id": case_id,
                        "case_position": case_position,
                        "arm": arm,
                        "arm_position": arm_position,
                        "arm_order": arm_order,
                    })
    return schedule


def build_freeze(*, project_root: str | Path, source_checkpoint: str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    _require(COMMIT.fullmatch(source_checkpoint) is not None, "source checkpoint")
    cases = generate_cases()
    prior, prior_bindings = _prior_identities(root)
    overlap = sorted(prior.intersection(
        row["source_group_sha256"] for row in cases
    ))
    _require(not overlap, "prospective workload overlaps prior cohorts")
    schedule = build_schedule(cases)
    closure = [normalized_file_identity(root, path) for path in SOURCE_PATHS]
    core = {
        "schema": SCHEMA,
        "status": "frozen_awaiting_explicit_benchmark_authorization",
        "date": "2026-09-10",
        "source_checkpoint": source_checkpoint,
        "source_closure": closure,
        "source_closure_sha256": digest(closure),
        "independence": {
            "role": "prospective_exact_cost_development",
            "prior_identity_bindings": prior_bindings,
            "prior_alpha_structural_identity_count": len(prior),
            "prior_alpha_structural_overlap_count": len(overlap),
            "widths_absent_from_consumed_q64_and_c36": True,
            "query_ladder_absent_from_consumed_q64_and_prior_q1_q4_q16_q64": True,
            "case_and_schedule_selection_used_method_outputs_or_timings": False,
            "performance_rows_opened": 0,
        },
        "cohort": {
            "generator": "crse-native-slot-batch-prospective/v1",
            "seed": SEED,
            "widths": list(WIDTHS),
            "live_widths": list(LIVE_WIDTHS),
            "families": list(FAMILIES),
            "shapes": list(SHAPES),
            "replicates": REPLICATES,
            "cases": cases,
            "case_count": len(cases),
            "case_set_sha256": digest([row["case_id"] for row in cases]),
            "source_group_set_sha256": digest(sorted(
                row["source_group_sha256"] for row in cases
            )),
        },
        "oracle_contract": {
            "generated_only_after_case_and_schedule_freeze": True,
            "reference": "standard_library_full_truth_then_index_projection",
            "candidate_or_scalar_native_used_for_oracle_generation": False,
            "stored_values": [
                "full_truth_sha256",
                "canonical_output_sha256_by_query_count",
                "sampled_query_output_sha256",
            ],
            "direct_restriction_replay_samples_per_case": len(LIVE_WIDTHS),
        },
        "measurement_contract": {
            "arms": list(ARMS),
            "query_counts": list(QUERY_COUNTS),
            "primary_query_count": PRIMARY_QUERY_COUNT,
            "blocks": BLOCKS,
            "schedule": schedule,
            "schedule_sha256": digest(schedule),
            "planned_cells_per_host": len(schedule),
            "fresh_process_per_cell": True,
            "same_compiled_successor_library_for_both_arms": True,
            "scalar_arm_calls_frozen_v1_symbol": True,
            "batch_arm_calls_additive_batch_v1_symbol": True,
            "process_and_library_startup_recorded_but_outside_resident_request_cost": True,
            "accounted_stages": list(STAGES),
            "accounted_total": "sum(accounted_stages)",
            "fully_charged_exact_cost_includes_all_request_stages": True,
            "unfavorable_failures_timeouts_and_zeroes_retained": True,
            "cell_timeout_seconds": CELL_TIMEOUT_SECONDS,
            "maximum_campaign_wall_seconds": MAX_WALL_SECONDS,
            "absolute_cross_host_timing_comparison_permitted": False,
        },
        "materiality_contract": {
            "primary_sum_speedup": "sum_scalar_case_medians/sum_batch_case_medians",
            "minimum_primary_sum_speedup": MIN_PRIMARY_SUM_SPEEDUP,
            "minimum_primary_batch_case_win_fraction": MIN_PRIMARY_CASE_WIN_FRACTION,
            "paired_case_cluster_bootstrap_draws": BOOTSTRAP_DRAWS,
            "minimum_primary_cluster_ci_low": MIN_PRIMARY_CLUSTER_CI_LOW,
            "minimum_q32_sum_speedup": MIN_Q32_SUM_SPEEDUP,
            "q8_role": "diagnostic_only",
            "local_pass_disposition": "eligible_for_separate_second_host_authorization",
            "verified_material_reduction_requires_two_distinct_physical_hosts": True,
            "any_gate_failure_disposition": "exact_batch_no_go_for_this_workload",
        },
        "authorization": {
            "freeze_and_oracle_generation": True,
            "functional_fake_clock_preflight": True,
            "local_timing_benchmark": False,
            "second_host_timing_benchmark": False,
            "cloud_or_paid_execution": False,
            "model_training": False,
            "production_routing": False,
            "publish_or_deploy": False,
            "separate_hash_bound_authorization_required_for_timing": True,
        },
        "exact_backend_timing_executions": 0,
        "timing_rows_produced": 0,
        "models_trained": 0,
        "cloud_resources_created": 0,
    }
    freeze = {**core, "freeze_sha256": digest(core)}
    validate_freeze(freeze, root)
    return freeze


def validate_freeze(freeze: Mapping[str, Any], root: Path | None = None) -> None:
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(
        freeze.get("schema") == SCHEMA
        and freeze.get("status")
        == "frozen_awaiting_explicit_benchmark_authorization"
        and COMMIT.fullmatch(freeze.get("source_checkpoint", "")) is not None
        and freeze.get("freeze_sha256") == digest(core)
        and freeze.get("source_closure_sha256")
        == digest(freeze.get("source_closure")),
        "freeze identity",
    )
    cohort = freeze["cohort"]
    cases = generate_cases()
    _require(
        cohort.get("cases") == cases
        and cohort.get("case_count") == 36
        and cohort.get("widths") == list(WIDTHS)
        and cohort.get("live_widths") == list(LIVE_WIDTHS)
        and cohort.get("case_set_sha256")
        == digest([row["case_id"] for row in cases]),
        "frozen cohort",
    )
    independence = freeze["independence"]
    _require(
        independence.get("prior_alpha_structural_overlap_count") == 0
        and independence.get("widths_absent_from_consumed_q64_and_c36") is True
        and independence.get(
            "query_ladder_absent_from_consumed_q64_and_prior_q1_q4_q16_q64"
        ) is True
        and independence.get(
            "case_and_schedule_selection_used_method_outputs_or_timings"
        ) is False
        and independence.get("performance_rows_opened") == 0,
        "workload independence",
    )
    measurement = freeze["measurement_contract"]
    schedule = build_schedule(cases)
    _require(
        measurement.get("arms") == list(ARMS)
        and measurement.get("query_counts") == list(QUERY_COUNTS)
        and measurement.get("blocks") == BLOCKS
        and measurement.get("schedule") == schedule
        and measurement.get("schedule_sha256") == digest(schedule)
        and measurement.get("planned_cells_per_host")
        == BLOCKS * len(cases) * len(QUERY_COUNTS) * len(ARMS)
        and measurement.get("accounted_stages") == list(STAGES)
        and measurement.get("fully_charged_exact_cost_includes_all_request_stages")
        is True,
        "measurement contract",
    )
    for case in cases:
        for query_count in QUERY_COUNTS:
            orders = [
                tuple(row["arm_order"])
                for row in schedule
                if row["case_id"] == case["case_id"]
                and row["query_count"] == query_count
                and row["arm_position"] == 0
            ]
            _require(
                len(orders) == BLOCKS
                and Counter(orders)[ARMS] == BLOCKS // 2
                and Counter(orders)[tuple(reversed(ARMS))] == BLOCKS // 2,
                "arm-order counterbalance",
            )
    authorization = freeze["authorization"]
    _require(
        authorization.get("freeze_and_oracle_generation") is True
        and authorization.get("functional_fake_clock_preflight") is True
        and all(
            authorization.get(name) is False
            for name in (
                "local_timing_benchmark",
                "second_host_timing_benchmark",
                "cloud_or_paid_execution",
                "model_training",
                "production_routing",
                "publish_or_deploy",
            )
        )
        and freeze.get("exact_backend_timing_executions") == 0
        and freeze.get("timing_rows_produced") == 0
        and freeze.get("models_trained") == 0
        and freeze.get("cloud_resources_created") == 0,
        "authorization boundary",
    )
    if root is not None:
        _require(
            [normalized_file_identity(root, path) for path in SOURCE_PATHS]
            == freeze["source_closure"],
            "source closure drift",
        )
        prior, _ = _prior_identities(root)
        _require(
            not prior.intersection(row["source_group_sha256"] for row in cases),
            "prior identity overlap",
        )


def _case_oracle(case: Mapping[str, Any]) -> dict[str, Any]:
    expression = expr_from_json(case["expression_v2"])
    names = tuple(f"x{index}" for index in range(case["n_vars"]))
    bits = int(eval_expr_bitset(expression, build_bitset_env(names)))
    vector = bitset_to_bool_array(bits, case["n_vars"])
    rows = []
    for query in case["query_trace"]:
        fixed = {row["variable"]: row["value"] for row in query["fixed"]}
        indices = projection_indices(
            case["n_vars"], fixed, query["remaining_order"],
        )
        reduced = project_truth_vector(vector, indices)
        rows.append(semantic_row(query, reduced, case["n_vars"]))
    byte_count = max(1, ((1 << case["n_vars"]) + 7) // 8)
    sample_indexes = [
        next(
            index for index, query in enumerate(case["query_trace"])
            if len(query["remaining_order"]) == live_width
        )
        for live_width in LIVE_WIDTHS
    ]
    return {
        "full_truth_sha256": hashlib.sha256(
            bits.to_bytes(byte_count, "little")
        ).hexdigest(),
        "canonical_output_sha256_by_query_count": {
            str(query_count): digest(semantic_document(
                case["case_id"], rows[:query_count],
            ))
            for query_count in QUERY_COUNTS
        },
        "sampled_query_output_sha256": {
            str(index): digest(rows[index]) for index in sample_indexes
        },
    }


def build_oracles(freeze: Mapping[str, Any]) -> dict[str, Any]:
    validate_freeze(freeze)
    clear_bitset_env_cache()
    cases = {
        case["case_id"]: _case_oracle(case)
        for case in freeze["cohort"]["cases"]
    }
    clear_bitset_env_cache()
    return {
        "schema": ORACLE_SCHEMA,
        "status": "exact_reference_oracles_complete_no_timings",
        "freeze_sha256": digest(freeze),
        "case_set_sha256": freeze["cohort"]["case_set_sha256"],
        "cases": cases,
        "case_count": len(cases),
        "reference_full_truth_constructions": len(cases),
        "native_scalar_executions": 0,
        "native_batch_executions": 0,
        "timing_rows_produced": 0,
    }


def validate_oracles(
    oracles: Mapping[str, Any], freeze: Mapping[str, Any], *, replay: bool,
) -> None:
    _require(
        oracles.get("schema") == ORACLE_SCHEMA
        and oracles.get("status") == "exact_reference_oracles_complete_no_timings"
        and oracles.get("freeze_sha256") == digest(freeze)
        and oracles.get("case_set_sha256") == freeze["cohort"]["case_set_sha256"]
        and oracles.get("case_count") == 36
        and set(oracles.get("cases", {}))
        == {row["case_id"] for row in freeze["cohort"]["cases"]}
        and oracles.get("native_scalar_executions") == 0
        and oracles.get("native_batch_executions") == 0
        and oracles.get("timing_rows_produced") == 0,
        "oracle identity",
    )
    for value in oracles["cases"].values():
        _require(
            SHA256.fullmatch(value.get("full_truth_sha256", "")) is not None
            and set(value.get("canonical_output_sha256_by_query_count", {}))
            == {str(count) for count in QUERY_COUNTS}
            and all(
                SHA256.fullmatch(item) is not None
                for item in value["canonical_output_sha256_by_query_count"].values()
            ),
            "oracle case",
        )
        _require(
            len(value.get("sampled_query_output_sha256", {})) == len(LIVE_WIDTHS)
            and all(
                key.isdigit() and SHA256.fullmatch(item) is not None
                for key, item in value["sampled_query_output_sha256"].items()
            ),
            "oracle direct samples",
        )
    if replay:
        _require(
            canonical_bytes(oracles) == canonical_bytes(build_oracles(freeze)),
            "oracle replay mismatch",
        )


def direct_oracle_sample_check(
    freeze: Mapping[str, Any], oracles: Mapping[str, Any],
) -> int:
    checked = 0
    for case in freeze["cohort"]["cases"]:
        expression = expr_from_json(case["expression_v2"])
        names = tuple(f"x{index}" for index in range(case["n_vars"]))
        bits = int(eval_expr_bitset(expression, build_bitset_env(names)))
        byte_count = max(1, ((1 << case["n_vars"]) + 7) // 8)
        _require(
            hashlib.sha256(bits.to_bytes(byte_count, "little")).hexdigest()
            == oracles["cases"][case["case_id"]]["full_truth_sha256"],
            "direct full-truth oracle",
        )
        sampled = oracles["cases"][case["case_id"]][
            "sampled_query_output_sha256"
        ]
        for live_width in LIVE_WIDTHS:
            query_index, query = next(
                (index, row) for index, row in enumerate(case["query_trace"])
                if len(row["remaining_order"]) == live_width
            )
            fixed = {row["variable"]: row["value"] for row in query["fixed"]}
            remaining, reduced = restrict_full_truth(bits, case["n_vars"], fixed)
            _require(
                remaining == tuple(query["remaining_order"]),
                "direct oracle residual order",
            )
            direct_row = semantic_row(query, reduced, case["n_vars"])
            _require(
                digest(direct_row) == sampled[str(query_index)],
                "direct restriction oracle mismatch",
            )
            checked += 1
    clear_bitset_env_cache()
    return checked


def verify_freeze_artifacts(
    freeze: Mapping[str, Any], oracles: Mapping[str, Any], root: Path,
) -> dict[str, Any]:
    validate_freeze(freeze, root)
    validate_oracles(oracles, freeze, replay=True)
    samples = direct_oracle_sample_check(freeze, oracles)
    return {
        "schema": VERIFICATION_SCHEMA,
        "status": "verified_prospective_freeze_awaiting_benchmark_authorization",
        "freeze_sha256": digest(freeze),
        "oracles_sha256": digest(oracles),
        "source_closure_verified": True,
        "cohort_replayed_byte_identically": True,
        "schedule_replayed_byte_identically": True,
        "prior_identity_exclusion_replayed": True,
        "oracles_replayed_byte_identically": True,
        "direct_oracle_samples_checked": samples,
        "performance_rows_opened": 0,
        "timing_rows_produced": 0,
        "models_trained": 0,
        "cloud_resources_created": 0,
    }


def _stage_timer(clock: Callable[[], int], function: Callable[[], Any]) -> tuple[int, Any]:
    started = clock()
    value = function()
    return max(1, clock() - started), value


def execute_cell(
    freeze: Mapping[str, Any],
    oracles: Mapping[str, Any],
    library_path: Path,
    case_id: str,
    arm: str,
    query_count: int,
    *,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    """Execute one cell; callers must enforce the frozen authorization gate."""
    _require(arm in ARMS and query_count in QUERY_COUNTS, "timed cell identity")
    case = next(
        row for row in freeze["cohort"]["cases"] if row["case_id"] == case_id
    )
    trace = case["query_trace"][:query_count]
    expression_payload = canonical_bytes(case["expression_v2"])
    library = load_native_slot_library(library_path)
    clear_bitset_env_cache()
    clear_words_env_cache()
    timings: dict[str, int] = {}
    timings["parse_normalization_ns"], document = _stage_timer(
        clock, lambda: json.loads(expression_payload),
    )
    arena = batch = None

    def construct() -> None:
        nonlocal arena, batch
        arena = compile_native_slot_arena(
            document, library, variable_count=case["n_vars"],
        )
        if arm == "native_batch_v1":
            batch = NativeSlotBatchExecutor(arena)

    timings["representation_construction_ns"], _ = _stage_timer(clock, construct)
    queries = [
        (
            {row["variable"]: row["value"] for row in query["fixed"]},
            tuple(query["remaining_order"]),
        )
        for query in trace
    ]
    plans: Any = None

    def bind() -> None:
        nonlocal plans
        if arm == "native_scalar_v1":
            plans = tuple(
                (arena.prepare_bindings(fixed, remaining), len(remaining))
                for fixed, remaining in queries
            )
        else:
            plans = prepare_bindings_many(arena, queries)

    timings["binding_ns"], _ = _stage_timer(clock, bind)

    def evaluate() -> tuple[int, ...]:
        if arm == "native_scalar_v1":
            return tuple(arena.evaluate(binding, live) for binding, live in plans)
        bindings, live_counts = plans
        return batch.evaluate_prepared(bindings, live_counts)

    timings["evaluation_ns"], outputs = _stage_timer(clock, evaluate)

    def deliver() -> dict[str, Any]:
        rows = [
            semantic_row(query, output, case["n_vars"])
            for query, output in zip(trace, outputs, strict=True)
        ]
        return semantic_document(case_id, rows)

    timings["delivery_ns"], output_document = _stage_timer(clock, deliver)
    actual = digest(output_document)
    expected = oracles["cases"][case_id][
        "canonical_output_sha256_by_query_count"
    ][str(query_count)]
    _require(actual == expected, f"prospective oracle mismatch: {case_id}:{arm}")
    timings["serialization_ns_when_applicable"], payload = _stage_timer(
        clock, lambda: canonical_bytes(output_document),
    )

    def cleanup() -> None:
        clear_bitset_env_cache()
        clear_words_env_cache()
        gc.collect()

    timings["cleanup_ns"], _ = _stage_timer(clock, cleanup)
    values = {stage: int(timings[stage]) for stage in STAGES}
    values["accounted_total_ns"] = sum(values.values())
    return {
        "schema": RAW_SCHEMA,
        "status": "ok",
        "reason": "completed",
        "case_id": case_id,
        "arm": arm,
        "query_count": query_count,
        "timings_ns": values,
        "output_sha256": actual,
        "output_bytes": len(payload),
        "exact_check_passed": True,
        "resources": {
            "n_vars": case["n_vars"],
            "queries": query_count,
            "live_widths": sorted({len(row[1]) for row in queries}),
            "native_nodes": arena.node_count,
        },
    }


def validate_authorization(
    authorization: Mapping[str, Any], freeze_path: Path, oracles_path: Path,
) -> None:
    _require(
        authorization.get("schema") == AUTHORIZATION_SCHEMA
        and authorization.get("authorized") is True
        and authorization.get("scope") == "local_single_physical_host_development"
        and authorization.get("freeze_file_sha256") == file_sha256(freeze_path)
        and authorization.get("oracles_file_sha256") == file_sha256(oracles_path)
        and authorization.get("maximum_wall_seconds") == MAX_WALL_SECONDS
        and authorization.get("cloud_or_paid_execution") is False
        and authorization.get("models_or_training") is False,
        "benchmark authorization",
    )


def verify_rows(
    rows: Sequence[Mapping[str, Any]],
    freeze: Mapping[str, Any],
    oracles: Mapping[str, Any],
) -> dict[str, Any]:
    schedule = freeze["measurement_contract"]["schedule"]
    schedule_mismatches = semantic_mismatches = timing_mismatches = 0
    for index, expected in enumerate(schedule):
        if index >= len(rows):
            schedule_mismatches += 1
            continue
        row = rows[index]
        if any(row.get(key) != expected[key] for key in (
            "block", "query_count", "case_id", "arm",
            "case_position", "arm_position", "arm_order",
        )):
            schedule_mismatches += 1
        expected_output = oracles["cases"][expected["case_id"]][
            "canonical_output_sha256_by_query_count"
        ][str(expected["query_count"])]
        if not (
            row.get("status") == "ok"
            and row.get("exact_check_passed") is True
            and row.get("output_sha256") == expected_output
        ):
            semantic_mismatches += 1
        timings = row.get("timings_ns", {})
        if not (
            set(timings) == {*STAGES, "accounted_total_ns"}
            and all(type(timings[stage]) is int and timings[stage] > 0 for stage in STAGES)
            and timings.get("accounted_total_ns")
            == sum(timings[stage] for stage in STAGES)
        ):
            timing_mismatches += 1
    schedule_mismatches += max(0, len(rows) - len(schedule))
    return {
        "expected_rows": len(schedule),
        "observed_rows": len(rows),
        "schedule_mismatches": schedule_mismatches,
        "semantic_mismatches": semantic_mismatches,
        "timing_mismatches": timing_mismatches,
        "verified_complete": (
            len(rows) == len(schedule)
            and schedule_mismatches == semantic_mismatches == timing_mismatches == 0
        ),
    }


def _cluster_ci(values: Sequence[float]) -> tuple[float, float]:
    _require(values and all(value > 0 for value in values), "cluster values")
    rng = random.Random(f"native-batch-bootstrap:{SEED}")
    draws = []
    count = len(values)
    for _ in range(BOOTSTRAP_DRAWS):
        sample = [values[rng.randrange(count)] for _ in range(count)]
        draws.append(math.exp(statistics.fmean(math.log(value) for value in sample)))
    draws.sort()
    return draws[int(0.025 * BOOTSTRAP_DRAWS)], draws[int(0.975 * BOOTSTRAP_DRAWS)]


def summarize_rows(
    rows: Sequence[Mapping[str, Any]],
    freeze: Mapping[str, Any],
    oracles: Mapping[str, Any],
) -> dict[str, Any]:
    verification = verify_rows(rows, freeze, oracles)
    _require(verification["verified_complete"], "unverified timing rows")
    grouped: dict[tuple[int, str, str], list[int]] = defaultdict(list)
    for row in rows:
        grouped[(row["query_count"], row["case_id"], row["arm"])].append(
            row["timings_ns"]["accounted_total_ns"]
        )
    results = {}
    for query_count in QUERY_COUNTS:
        scalar = {}
        batch = {}
        for case in freeze["cohort"]["cases"]:
            case_id = case["case_id"]
            scalar[case_id] = float(statistics.median(
                grouped[(query_count, case_id, "native_scalar_v1")]
            ))
            batch[case_id] = float(statistics.median(
                grouped[(query_count, case_id, "native_batch_v1")]
            ))
        case_speedups = [scalar[name] / batch[name] for name in scalar]
        ci_low, ci_high = _cluster_ci(case_speedups)
        results[str(query_count)] = {
            "scalar_sum_of_case_medians_ns": sum(scalar.values()),
            "batch_sum_of_case_medians_ns": sum(batch.values()),
            "fully_charged_sum_speedup": sum(scalar.values()) / sum(batch.values()),
            "batch_case_win_fraction": sum(value > 1 for value in case_speedups)
            / len(case_speedups),
            "case_cluster_geomean_speedup": math.exp(statistics.fmean(
                math.log(value) for value in case_speedups
            )),
            "case_cluster_bootstrap_ci95": [ci_low, ci_high],
        }
    primary = results[str(PRIMARY_QUERY_COUNT)]
    gates = {
        "primary_sum_speedup_at_least_1_10": (
            primary["fully_charged_sum_speedup"] >= MIN_PRIMARY_SUM_SPEEDUP
        ),
        "primary_batch_case_win_fraction_at_least_0_75": (
            primary["batch_case_win_fraction"] >= MIN_PRIMARY_CASE_WIN_FRACTION
        ),
        "primary_cluster_ci_low_above_1_0": (
            primary["case_cluster_bootstrap_ci95"][0] > MIN_PRIMARY_CLUSTER_CI_LOW
        ),
        "q32_sum_speedup_at_least_1_0": (
            results["32"]["fully_charged_sum_speedup"] >= MIN_Q32_SUM_SPEEDUP
        ),
    }
    passed = all(gates.values())
    return {
        "schema": "crse-native-slot-batch-local-development-summary/v1",
        "status": "local_gate_passed" if passed else "local_gate_failed_no_go",
        "verification": verification,
        "query_counts": results,
        "gates": gates,
        "disposition": (
            "eligible_for_separate_second_host_authorization"
            if passed else "exact_batch_no_go_for_this_workload"
        ),
        "verified_material_reduction_claim_permitted": False,
    }


def render_report(freeze: Mapping[str, Any]) -> str:
    validate_freeze(freeze)
    return f"""# Prospective exact native-batch timing freeze

Date: 2026-09-10

Status: **frozen and independently verifiable; benchmark authorization absent**

## New workload

- {freeze['cohort']['case_count']} source-distinct cases at widths 17, 18, and 19
- balanced-tree and layered-sharing shapes across three operator families
- 96 frozen restrictions per case with residual widths 7, 11, and 15
- independently scheduled q8, q32, and q96 cells
- zero alpha-structural overlap with the consumed q64, prior architecture, or C36 cohorts

The case identities, query traces, scalar/batch arms, {BLOCKS}-block counterbalanced
schedule, accounted stages, and materiality gates were selected without reading any
performance output for this workload.

## Primary decision

At q96, the sum of scalar case medians divided by the sum of batched case medians
must be at least {MIN_PRIMARY_SUM_SPEEDUP:.2f}x. Batch must also win at least
{MIN_PRIMARY_CASE_WIN_FRACTION:.0%} of cases, the paired case-cluster bootstrap lower
bound must exceed {MIN_PRIMARY_CLUSTER_CI_LOW:.1f}, and q32 sum speedup must not be
below {MIN_Q32_SUM_SPEEDUP:.1f}x. All parse, construction, binding, evaluation,
delivery, serialization, and cleanup stages are charged.

A local pass permits only a request for a separately authorized second physical
host. A verified material-reduction claim requires both physical hosts to pass.

## Authorization boundary

Freeze generation, exact reference-oracle construction, and fake-clock functional
preflight are allowed. Local timing, second-host timing, cloud or paid work, model
training, production routing, publishing, and deployment are not authorized by this
artifact. Timed execution requires a separate hash-bound authorization record.
"""


def authorization_request(
    freeze_path: Path, oracles_path: Path,
) -> dict[str, Any]:
    return {
        "schema": AUTHORIZATION_REQUEST_SCHEMA,
        "status": "awaiting_explicit_user_authorization",
        "authorization_granted": False,
        "requested_scope": "local_single_physical_host_development",
        "effect": (
            "build the separate successor DLL, execute 2592 fresh-process timed "
            "cells locally, and write a new append-only run directory"
        ),
        "freeze_file": freeze_path.as_posix(),
        "freeze_file_sha256": file_sha256(freeze_path),
        "oracles_file": oracles_path.as_posix(),
        "oracles_file_sha256": file_sha256(oracles_path),
        "maximum_wall_seconds": MAX_WALL_SECONDS,
        "cell_timeout_seconds": CELL_TIMEOUT_SECONDS,
        "cloud_or_paid_execution": False,
        "models_or_training": False,
        "production_change": False,
        "publish_or_deploy": False,
        "second_host_execution": False,
    }
