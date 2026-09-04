"""Source-blind freeze for a future q64 architecture-learning decision surface.

The freeze contains inputs, structural features, split assignments, and policy
only.  It never executes an exact backend, reads timing/label artifacts, or
fits a model.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
import statistics
import time
from typing import Any, Mapping, Sequence

from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Expr, Imp, Not, Or, Var, Xor
from cmbench.comparative.architecture_comparison_campaign import build_query_trace
from cmbench.recognition.features import structural_digest


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "crse-query-ladder-source-blind-learning-freeze/v1"
MANIFEST_SCHEMA = "crse-query-ladder-source-blind-learning-freeze-artifacts/v1"
VERIFICATION_SCHEMA = (
    "crse-query-ladder-source-blind-learning-freeze-independent-verification/v1"
)
SEED = 2_026_090_405
SPLIT_SALT = "crse-q64-source-blind-development-split-v1"
WIDTHS = (9, 10, 12, 13)
FAMILIES = ("andor", "xor_eqv", "mixed")
SHAPES = ("tree", "high_sharing")
REPLICATES = 3
SPLIT_COUNTS = {
    "development_fit": 40,
    "development_validation": 16,
    "development_audit": 16,
}
QUERY_COUNT = 64
REPETITIONS = 16
ABSTAIN_LABEL = "__abstain__"
EXACT_ARMS = (
    "r2_topological_liveness",
    "cm_ir_bigint",
    "cm_ir_words",
    "cse_flat_bigint",
    "cse_flat_words",
    "current_projection",
    "direct_bitset_restriction",
    "native_fused_slots",
)
FEATURE_NAMES = (
    "variable_count",
    "identity_node_count",
    "edge_count",
    "maximum_depth",
    "shared_node_count",
    "maximum_reference_count",
    "not_count",
    "and_count",
    "or_count",
    "xor_count",
    "imp_count",
    "eqv_count",
    "query_count",
)
FORBIDDEN_MODEL_FIELDS = (
    "case_id",
    "source_group_sha256",
    "family",
    "shape",
    "replicate",
    "split",
    "expression_v2",
    "query_trace",
    "structural_digest",
    "alpha_structural_digest",
    "oracle_label",
    "method_timing",
    "output_sha256",
    "physical_machine_sha256",
    "compiler_sha256",
    "block",
    "arm_order",
)
MIN_MEDIAN_RUNNER_UP_SPEEDUP = 1.03
MIN_PAIRED_BLOCK_WIN_FRACTION = 0.75
MIN_P10_PAIRED_SPEEDUP = 1.0
PRIOR_FREEZE = (
    ROOT / "docs/recognition/architecture_comparison_freeze_20260903/FREEZE.json"
)
PRIOR_C36 = ROOT / "docs/recognition/c36_wide_repeated_query_dataset.json"
SOURCE_PATHS = (
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cmbench/comparative/architecture_comparison_campaign.py",
    "cmbench/recognition/features.py",
    "cmbench/recognition/query_ladder_learning_freeze.py",
    "scripts/cm_query_ladder_learning_freeze.py",
    "scripts/crse_query_ladder_learning_freeze_verify.py",
)
SHA256 = re.compile(r"[0-9a-f]{64}")
COMMIT = re.compile(r"[0-9a-f]{40}")


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
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _file_identity(root: Path, relative: str) -> dict[str, Any]:
    path = (root / relative).resolve()
    _require(path.is_relative_to(root) and path.is_file(), f"missing source: {relative}")
    return {
        "path": relative,
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
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
    raise ValueError("unknown structural family")


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
            left, right = level[offset], level[offset + 1]
            if rng.randrange(5) == 0:
                left = Not(left)
            if rng.randrange(7) == 0:
                right = Not(right)
            following.append(rng.choice(operators)(left, right))
        level = following
    return level[0]


def _expression(
    n_vars: int,
    family: str,
    shape: str,
    replicate: int,
) -> Expr:
    rng = _rng("learning-q64", n_vars, family, shape, replicate)
    base = _balanced_tree(n_vars, family, rng)
    if shape == "tree":
        return base
    _require(shape == "high_sharing", "unknown structural shape")
    tail = _balanced_tree(n_vars, family, rng)
    operators = _operators(family)
    left = operators[(replicate + 1) % len(operators)](base, tail)
    right = operators[(replicate + 2) % len(operators)](Not(base), tail)
    return operators[replicate % len(operators)](left, right)


def extract_routing_features(
    document: Mapping[str, Any],
    *,
    n_vars: int,
    query_count: int = QUERY_COUNT,
) -> tuple[int, ...]:
    """Extract the only model-visible values without reconstructing the Expr."""
    nodes = document.get("nodes")
    _require(
        document.get("version") == 2
        and isinstance(nodes, list)
        and nodes
        and type(document.get("root")) is int,
        "expression document",
    )
    depths: list[int] = []
    references = [0] * len(nodes)
    counts = Counter()
    edges = 0
    for index, node in enumerate(nodes):
        _require(isinstance(node, Mapping) and type(node.get("op")) is str, "DAG node")
        op = node["op"]
        counts[op] += 1
        children = [node[name] for name in ("a", "b") if name in node]
        _require(
            all(type(child) is int and 0 <= child < index for child in children),
            "DAG child order",
        )
        for child in children:
            references[child] += 1
        edges += len(children)
        depths.append(1 + max((depths[child] for child in children), default=-1))
    _require(0 <= document["root"] < len(nodes), "DAG root")
    return (
        n_vars,
        len(nodes),
        edges,
        depths[document["root"]],
        sum(value > 1 for value in references),
        max(references, default=0),
        counts["not"],
        counts["and"],
        counts["or"],
        counts["xor"],
        counts["imp"],
        counts["eqv"],
        query_count,
    )


def analytical_control(features: Sequence[int]) -> str:
    """Pre-label structural control derived only from prior evidence."""
    _require(len(features) == len(FEATURE_NAMES), "routing feature vector")
    shared_nodes = features[4]
    return "cse_flat_bigint" if shared_nodes > 0 else "native_fused_slots"


def bounded_model_inference(features: Sequence[int]) -> str:
    """Fixed-shape inference timing surrogate; coefficients carry no labels."""
    _require(len(features) == len(FEATURE_NAMES), "routing feature vector")
    scores = []
    for arm_index, arm in enumerate(EXACT_ARMS):
        score = sum(
            ((feature_index + 1) * (arm_index + 3) % 7 - 3) * value
            for feature_index, value in enumerate(features)
        )
        scores.append((score, arm))
    return min(scores)[1]


def verify_exact_arm_selection(arm: str) -> bool:
    """Measured guard proving that inference can select exact arms only."""
    return arm in EXACT_ARMS


def fallback_dispatch(arm: str | None) -> str:
    """Measured dispatch component; backend fallback time is charged separately."""
    return arm if arm in EXACT_ARMS else "native_fused_slots"


def _case_record(n_vars: int, family: str, shape: str, replicate: int) -> dict[str, Any]:
    expression = _expression(n_vars, family, shape, replicate)
    document = expr_to_json_dag(expression)
    case_id = (
        f"learning-q64-{shape.replace('_', '-')}-{family.replace('_', '-')}"
        f"-k{n_vars}-r{replicate}"
    )
    trace = build_query_trace(case_id, n_vars)
    alpha_digest = structural_digest(expression, alpha_rename=True)
    features = extract_routing_features(document, n_vars=n_vars)
    return {
        "case_id": case_id,
        "source_group_sha256": alpha_digest,
        "n_vars": n_vars,
        "family": family,
        "shape": shape,
        "replicate": replicate,
        "expression_v2": document,
        "expression_v2_sha256": digest(document),
        "structural_digest": structural_digest(expression),
        "alpha_structural_digest": alpha_digest,
        "query_trace": trace,
        "query_trace_sha256": digest(trace),
        "model_features": list(features),
        "model_features_sha256": digest(list(features)),
        "analytical_control_arm": analytical_control(features),
    }


def generate_cases() -> list[dict[str, Any]]:
    cases = [
        _case_record(n_vars, family, shape, replicate)
        for n_vars in WIDTHS
        for family in FAMILIES
        for shape in SHAPES
        for replicate in range(REPLICATES)
    ]
    _require(len(cases) == 72, "learning cohort cardinality")
    _require(len({row["case_id"] for row in cases}) == len(cases), "case identities")
    _require(
        len({row["source_group_sha256"] for row in cases}) == len(cases),
        "source-group identities",
    )
    return cases


def _prior_identities(root: Path) -> tuple[set[str], dict[str, Any]]:
    freeze_path = root / PRIOR_FREEZE.relative_to(ROOT)
    c36_path = root / PRIOR_C36.relative_to(ROOT)
    prior_freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    c36 = json.loads(c36_path.read_text(encoding="utf-8"))
    identities = {
        row["alpha_structural_digest"]
        for row in prior_freeze["fresh_corpus"]["single_root_cases"]
    }
    identities.update(
        structural_digest(expr_from_json(row["expression_v2"]), alpha_rename=True)
        for row in c36["cases"]
    )
    return identities, {
        "architecture_comparison_freeze": {
            **_file_identity(root, PRIOR_FREEZE.relative_to(ROOT).as_posix()),
            "role": "identity_exclusion_only",
        },
        "c36_repeated_query_dataset": {
            **_file_identity(root, PRIOR_C36.relative_to(ROOT).as_posix()),
            "role": "identity_exclusion_only",
        },
        "prior_alpha_structural_identities_sha256": digest(sorted(identities)),
        "timing_or_label_artifacts_read": False,
    }


def assign_splits(cases: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    ranked = sorted(
        cases,
        key=lambda row: hashlib.sha256(
            f"{SPLIT_SALT}:{row['source_group_sha256']}".encode("ascii")
        ).hexdigest(),
    )
    assignment: dict[str, str] = {}
    offset = 0
    for split, count in SPLIT_COUNTS.items():
        for row in ranked[offset:offset + count]:
            assignment[row["case_id"]] = split
        offset += count
    _require(offset == len(ranked) and len(assignment) == len(ranked), "split allocation")
    return assignment


def label_from_cross_host_blocks(
    host_block_timings: Mapping[str, Mapping[str, Sequence[int]]],
) -> str:
    """Apply the frozen near-tie rule to two or more verified host results."""
    _require(len(host_block_timings) >= 2, "cross-host label inputs")
    winners: list[str] = []
    all_hosts_qualified = True
    for host, by_arm in host_block_timings.items():
        _require(set(by_arm) == set(EXACT_ARMS), f"label arms: {host}")
        _require(
            all(
                len(values) == REPETITIONS
                and all(type(value) in (int, float) and value > 0 for value in values)
                for values in by_arm.values()
            ),
            f"label blocks: {host}",
        )
        medians = {arm: statistics.median(values) for arm, values in by_arm.items()}
        ordered = sorted(EXACT_ARMS, key=lambda arm: (medians[arm], arm))
        winner, runner = ordered[:2]
        paired = [
            runner_ns / winner_ns
            for winner_ns, runner_ns in zip(
                by_arm[winner], by_arm[runner], strict=True
            )
        ]
        paired_sorted = sorted(paired)
        p10 = paired_sorted[int(0.10 * (len(paired_sorted) - 1))]
        win_fraction = sum(value > 1.0 for value in paired) / len(paired)
        median_speedup = medians[runner] / medians[winner]
        if (
            median_speedup < MIN_MEDIAN_RUNNER_UP_SPEEDUP
            or win_fraction < MIN_PAIRED_BLOCK_WIN_FRACTION
            or p10 < MIN_P10_PAIRED_SPEEDUP
        ):
            all_hosts_qualified = False
        winners.append(winner)
    return (
        winners[0]
        if all_hosts_qualified and len(set(winners)) == 1
        else ABSTAIN_LABEL
    )


def _p95(values: Sequence[float]) -> float:
    _require(values, "p95 samples")
    ordered = sorted(values)
    return float(ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)])


def measure_charged_cost_components(
    cases: Sequence[Mapping[str, Any]],
    *,
    batches: int = 21,
    repetitions: int = 1_000,
) -> dict[str, Any]:
    """Measure label-free routing components on an exact-timing host.

    The fallback backend regret depends on future exact rows and is computed by
    ``expected_fallback_cost_ns_per_case``.  This function times dispatch only.
    """
    _require(batches >= 5 and repetitions >= 1, "charged timing configuration")
    _require(cases, "charged timing cases")
    features = [tuple(row["model_features"]) for row in cases]
    feature_control_samples = []
    inference_samples = []
    verification_samples = []
    fallback_dispatch_samples = []
    calls = len(cases) * repetitions
    for _ in range(batches):
        started = time.perf_counter_ns()
        for _repeat in range(repetitions):
            for row in cases:
                analytical_control(
                    extract_routing_features(
                        row["expression_v2"], n_vars=row["n_vars"]
                    )
                )
        feature_control_samples.append((time.perf_counter_ns() - started) / calls)

        started = time.perf_counter_ns()
        for _repeat in range(repetitions):
            for values in features:
                bounded_model_inference(values)
        inference_samples.append((time.perf_counter_ns() - started) / calls)

        selected = bounded_model_inference(features[0])
        started = time.perf_counter_ns()
        for _repeat in range(calls):
            verify_exact_arm_selection(selected)
        verification_samples.append((time.perf_counter_ns() - started) / calls)

        started = time.perf_counter_ns()
        for _repeat in range(calls):
            fallback_dispatch(None)
        fallback_dispatch_samples.append((time.perf_counter_ns() - started) / calls)
    return {
        "schema": "crse-query-ladder-charged-cost-components/v1",
        "batches": batches,
        "repetitions_per_case_per_batch": repetitions,
        "cases": len(cases),
        "p95_ns_per_case": {
            "feature_extraction_and_control": _p95(feature_control_samples),
            "model_inference": _p95(inference_samples),
            "exact_verification": _p95(verification_samples),
            "fallback_dispatch": _p95(fallback_dispatch_samples),
        },
        "samples_ns_per_case": {
            "feature_extraction_and_control": feature_control_samples,
            "model_inference": inference_samples,
            "exact_verification": verification_samples,
            "fallback_dispatch": fallback_dispatch_samples,
        },
        "exact_backend_executions": 0,
        "labels_consumed": 0,
    }


def expected_fallback_cost_ns_per_case(
    *,
    labels: Mapping[str, str],
    per_case_arm_medians_ns: Mapping[str, Mapping[str, float]],
    best_fixed_arm: str,
    fallback_dispatch_p95_ns: float,
) -> float:
    """Charge abstention dispatch plus fixed-arm regret against the oracle."""
    _require(best_fixed_arm in EXACT_ARMS, "fallback fixed arm")
    _require(
        bool(labels)
        and set(labels) == set(per_case_arm_medians_ns)
        and type(fallback_dispatch_p95_ns) in (int, float)
        and fallback_dispatch_p95_ns >= 0,
        "fallback inputs",
    )
    total = 0.0
    for case_id, label in labels.items():
        timings = per_case_arm_medians_ns[case_id]
        _require(
            set(timings) == set(EXACT_ARMS)
            and all(
                type(value) in (int, float) and value > 0
                for value in timings.values()
            )
            and (label in EXACT_ARMS or label == ABSTAIN_LABEL),
            "fallback case",
        )
        if label == ABSTAIN_LABEL:
            oracle = min(timings.values())
            total += max(0.0, timings[best_fixed_arm] - oracle)
            total += fallback_dispatch_p95_ns
    return total / len(labels)


def build_freeze(*, project_root: str | Path, source_checkpoint: str) -> dict[str, Any]:
    root = Path(project_root).resolve()
    _require(COMMIT.fullmatch(source_checkpoint) is not None, "source checkpoint")
    cases = generate_cases()
    prior, prior_bindings = _prior_identities(root)
    overlap = sorted(prior.intersection(row["source_group_sha256"] for row in cases))
    _require(not overlap, "learning cohort overlaps prior timed cohort")
    assignments = assign_splits(cases)
    frozen_cases = [{**row, "split": assignments[row["case_id"]]} for row in cases]
    split_groups = {
        split: sorted(
            row["source_group_sha256"]
            for row in frozen_cases
            if row["split"] == split
        )
        for split in SPLIT_COUNTS
    }
    source_closure = [_file_identity(root, path) for path in SOURCE_PATHS]
    core = {
        "schema": SCHEMA,
        "status": "frozen_not_authorized_no_labels",
        "date": "2026-09-04",
        "source_checkpoint": source_checkpoint,
        "source_closure": source_closure,
        "source_closure_sha256": digest(source_closure),
        "prior_identity_bindings": prior_bindings,
        "cohort": {
            "role": "source_blind_development",
            "generator": "crse-query-ladder-source-blind-learning-freeze/v1",
            "seed": SEED,
            "widths": list(WIDTHS),
            "families": list(FAMILIES),
            "shapes": list(SHAPES),
            "replicates": REPLICATES,
            "cases": frozen_cases,
            "case_count": len(frozen_cases),
            "case_set_sha256": digest([row["case_id"] for row in frozen_cases]),
            "source_groups": len(frozen_cases),
            "source_group_set_sha256": digest(sorted(
                row["source_group_sha256"] for row in frozen_cases
            )),
            "source_groups_by_split": split_groups,
            "source_group_counts_by_split": {
                split: len(groups) for split, groups in split_groups.items()
            },
            "cross_split_source_group_intersections": 0,
            "prior_alpha_structural_overlap_count": len(overlap),
            "truth_outputs_inspected": False,
            "method_outputs_inspected": False,
            "method_timings_inspected": False,
            "labels_produced": False,
            "prospective_cases_consumed": 0,
        },
        "model_input_contract": {
            "feature_names": list(FEATURE_NAMES),
            "forbidden_fields": list(FORBIDDEN_MODEL_FIELDS),
            "feature_vectors_frozen_before_labels": True,
            "identity_or_timing_features_permitted": False,
            "analytical_control": "shared_node_count_positive_then_cse_else_native/v1",
            "bounded_inference_shape": {
                "arms": len(EXACT_ARMS),
                "features": len(FEATURE_NAMES),
                "coefficients_are_label_free_timing_surrogate": True,
            },
        },
        "exact_task_contract": {
            "query_count": QUERY_COUNT,
            "arms": list(EXACT_ARMS),
            "blocks": REPETITIONS,
            "task_identical_exact_outputs_required": True,
            "all_unfavorable_and_refused_rows_retained": True,
            "sum_of_per_case_arm_medians_required": True,
            "two_distinct_physical_machines_required": True,
            "same_case_schedule_and_oracles_required": True,
            "absolute_cross_host_timing_comparison_permitted": False,
        },
        "label_policy": {
            "label_scope": "joint_cross_host_development_label",
            "abstain_label": ABSTAIN_LABEL,
            "same_winner_required_on_every_host": True,
            "minimum_median_runner_up_speedup": MIN_MEDIAN_RUNNER_UP_SPEEDUP,
            "minimum_paired_block_win_fraction": MIN_PAIRED_BLOCK_WIN_FRACTION,
            "minimum_p10_paired_speedup": MIN_P10_PAIRED_SPEEDUP,
            "ties_or_threshold_failures_abstain": True,
            "abstentions_retained_in_economics": True,
            "abstentions_excluded_from_model_fit": True,
            "minimum_source_groups_per_non_abstain_label": 8,
            "label_rule_frozen_before_timings": True,
        },
        "charged_cost_contract": {
            "required_p95_costs_ns_per_case": [
                "feature_extraction_and_control",
                "model_inference",
                "exact_verification",
                "expected_fallback",
            ],
            "feature_control_function": "extract_routing_features+analytical_control",
            "model_inference_function": "bounded_model_inference",
            "exact_verification_function": "verify_exact_arm_selection",
            "fallback_dispatch_function": "fallback_dispatch",
            "measurement_function": "measure_charged_cost_components",
            "measurement_batches": 21,
            "measurement_repetitions_per_case_per_batch": 1_000,
            "expected_fallback_formula": (
                "mean_over_all_cases(abstain * "
                "(best_fixed_ns-oracle_ns+fallback_dispatch_p95_ns))"
            ),
            "same_host_as_exact_timing_required": True,
            "expected_fallback_includes_abstention_backend_regret": True,
            "gross_and_fully_charged_minimum_speedup": 1.10,
            "costs_may_not_be_imputed_or_cross_host_reused": True,
        },
        "claim_boundary": {
            "later_verified_handoff_may_assess_development_experiment_design": True,
            "current_development_training_eligible": False,
            "selector_or_neural_training_permitted": False,
            "prospective_consumption_permitted": False,
            "production_routing_permitted": False,
        },
        "permissions": {
            "local_freeze_generation": True,
            "local_freeze_verification": True,
            "exact_backend_execution": False,
            "timing_execution": False,
            "runpod_request": False,
            "runpod_execution": False,
            "label_generation": False,
            "model_fitting": False,
            "neural_training": False,
            "prospective_data_access": False,
            "production_write": False,
        },
        "exact_backend_executions": 0,
        "timing_rows_produced": 0,
        "labels_produced": 0,
        "models_trained": 0,
    }
    freeze = {**core, "freeze_sha256": digest(core)}
    validate_freeze(freeze)
    return freeze


def validate_freeze(freeze: Mapping[str, Any]) -> None:
    core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    _require(
        freeze.get("schema") == SCHEMA
        and freeze.get("status") == "frozen_not_authorized_no_labels"
        and COMMIT.fullmatch(freeze.get("source_checkpoint", "")) is not None
        and freeze.get("freeze_sha256") == digest(core)
        and freeze.get("source_closure_sha256")
        == digest(freeze.get("source_closure")),
        "freeze identity",
    )
    closure = freeze["source_closure"]
    _require(
        [row.get("path") for row in closure] == list(SOURCE_PATHS)
        and all(
            set(row) == {"path", "bytes", "sha256"}
            and type(row["bytes"]) is int
            and row["bytes"] > 0
            and SHA256.fullmatch(row["sha256"]) is not None
            for row in closure
        ),
        "source closure",
    )
    cohort = freeze["cohort"]
    cases = cohort["cases"]
    replay = generate_cases()
    assignments = assign_splits(replay)
    expected_cases = [{**row, "split": assignments[row["case_id"]]} for row in replay]
    _require(
        cohort.get("role") == "source_blind_development"
        and cases == expected_cases
        and cohort.get("case_count") == 72
        and cohort.get("source_groups") == 72
        and cohort.get("source_group_counts_by_split") == SPLIT_COUNTS
        and cohort.get("cross_split_source_group_intersections") == 0
        and cohort.get("prior_alpha_structural_overlap_count") == 0
        and all(
            cohort.get(field) is False
            for field in (
                "truth_outputs_inspected",
                "method_outputs_inspected",
                "method_timings_inspected",
                "labels_produced",
            )
        )
        and cohort.get("prospective_cases_consumed") == 0,
        "cohort boundary",
    )
    split_sets = {
        split: set(groups)
        for split, groups in cohort["source_groups_by_split"].items()
    }
    _require(
        set(split_sets) == set(SPLIT_COUNTS)
        and all(len(split_sets[name]) == SPLIT_COUNTS[name] for name in SPLIT_COUNTS)
        and all(
            not split_sets[left].intersection(split_sets[right])
            for left in split_sets
            for right in split_sets
            if left < right
        ),
        "split isolation",
    )
    model = freeze["model_input_contract"]
    _require(
        model.get("feature_names") == list(FEATURE_NAMES)
        and model.get("forbidden_fields") == list(FORBIDDEN_MODEL_FIELDS)
        and model.get("feature_vectors_frozen_before_labels") is True
        and model.get("identity_or_timing_features_permitted") is False
        and all(
            row["model_features"]
            == list(extract_routing_features(row["expression_v2"], n_vars=row["n_vars"]))
            for row in cases
        ),
        "model input boundary",
    )
    task = freeze["exact_task_contract"]
    label = freeze["label_policy"]
    _require(
        task.get("query_count") == QUERY_COUNT
        and task.get("arms") == list(EXACT_ARMS)
        and task.get("blocks") == REPETITIONS
        and task.get("task_identical_exact_outputs_required") is True
        and task.get("two_distinct_physical_machines_required") is True
        and label.get("same_winner_required_on_every_host") is True
        and label.get("minimum_median_runner_up_speedup")
        == MIN_MEDIAN_RUNNER_UP_SPEEDUP
        and label.get("minimum_paired_block_win_fraction")
        == MIN_PAIRED_BLOCK_WIN_FRACTION
        and label.get("minimum_p10_paired_speedup") == MIN_P10_PAIRED_SPEEDUP
        and label.get("ties_or_threshold_failures_abstain") is True
        and label.get("label_rule_frozen_before_timings") is True,
        "exact and label contract",
    )
    costs = freeze["charged_cost_contract"]
    _require(
        costs.get("same_host_as_exact_timing_required") is True
        and costs.get("expected_fallback_includes_abstention_backend_regret") is True
        and costs.get("measurement_function") == "measure_charged_cost_components"
        and costs.get("measurement_batches") == 21
        and costs.get("measurement_repetitions_per_case_per_batch") == 1_000
        and costs.get("gross_and_fully_charged_minimum_speedup") == 1.10
        and costs.get("costs_may_not_be_imputed_or_cross_host_reused") is True,
        "charged cost contract",
    )
    permissions = freeze["permissions"]
    _require(
        permissions.get("local_freeze_generation") is True
        and permissions.get("local_freeze_verification") is True
        and all(
            permissions.get(name) is False
            for name in (
                "exact_backend_execution",
                "timing_execution",
                "runpod_request",
                "runpod_execution",
                "label_generation",
                "model_fitting",
                "neural_training",
                "prospective_data_access",
                "production_write",
            )
        )
        and freeze.get("exact_backend_executions") == 0
        and freeze.get("timing_rows_produced") == 0
        and freeze.get("labels_produced") == 0
        and freeze.get("models_trained") == 0,
        "freeze permission boundary",
    )


def verify_freeze(freeze: Mapping[str, Any], project_root: str | Path) -> dict[str, Any]:
    validate_freeze(freeze)
    root = Path(project_root).resolve()
    _require(
        all(_file_identity(root, row["path"]) == row for row in freeze["source_closure"]),
        "source closure drift",
    )
    replay = build_freeze(
        project_root=root,
        source_checkpoint=freeze["source_checkpoint"],
    )
    _require(canonical_bytes(replay) == canonical_bytes(freeze), "freeze replay mismatch")
    return {
        "schema": VERIFICATION_SCHEMA,
        "status": "verified_source_blind_freeze_no_labels",
        "freeze_sha256": digest(freeze),
        "source_closure_verified": True,
        "prior_identity_exclusion_replayed": True,
        "cohort_replayed_byte_identically": True,
        "split_isolation_verified": True,
        "label_policy_frozen_before_timings": True,
        "charged_cost_contract_present": True,
        "exact_backend_executions": 0,
        "timing_rows_produced": 0,
        "labels_produced": 0,
        "models_trained": 0,
        "prospective_cases_consumed": 0,
        "runpod_resources_created": 0,
    }


def render_report(freeze: Mapping[str, Any]) -> str:
    validate_freeze(freeze)
    cohort = freeze["cohort"]
    label = freeze["label_policy"]
    return f"""# Q64 source-blind learning evidence freeze

Date: 2026-09-04

Status: frozen locally; no labels, timings, model fitting, or cloud execution.

## Frozen cohort

- {cohort['case_count']} new deterministic development cases
- source-group splits: 40 fit, 16 validation, 16 audit
- prior alpha-structural overlap: 0
- model-visible features: {len(FEATURE_NAMES)} structural integers
- prospective cases consumed: 0

The case generator, complete query traces, structural feature vectors, source-group
identities, and split assignments were frozen before any method output or timing for
this cohort was produced.

## Cross-host label policy

A case receives an exact-arm label only when every verified host names the same
winner, the runner-up/winner median ratio is at least
{label['minimum_median_runner_up_speedup']:.2f}x on every host, at least
{label['minimum_paired_block_win_fraction']:.0%} of paired blocks favor the winner,
and the paired p10 ratio is at least {label['minimum_p10_paired_speedup']:.2f}x.
Every disagreement, tie, or threshold failure becomes `{ABSTAIN_LABEL}` and remains
in charged economics while being excluded from model fitting.

## Charged economics

Both physical-machine replications must measure p95 feature/control, bounded model
inference, exact-arm verification, and fallback dispatch on the same host as the
exact timings. Expected fallback also includes the exact-runtime regret for abstained
cases. Cross-host timing reuse and zero-cost imputation are prohibited. Gross and
fully charged speedup must each remain at least 1.10x on every host.

## Boundary

This artifact does not authorize exact timing, a RunPod request, label generation,
model fitting, neural training, prospective access, production routing, or any other
external write. A separately authorized Benchmark task must execute and independently
verify the exact evidence before the learning handoff can be assessed.
"""
