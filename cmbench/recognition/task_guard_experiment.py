"""C14 bounded task-level guard and shadow-mode confirmation."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
import platform
from pathlib import Path
import statistics
import sys
import time
from typing import Any

from .in_kernel_sentinel_experiment import EXPECTED_INPUT_SHA256
from .natural_decomposition import partition_witness
from .task_guarded_dispatcher import (
    ExactTaskContract, compile_task_guard, current_platform_identity,
    freeze_task_guard_policy,
)
from .yosys_source_anf_experiment import document_truth_bits, percentile


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "docs/recognition/runs/adaptive-exact-dispatcher-robust-20260830-002/evaluation_dataset.json"
SCHEMA = "crse-task-guard-shadow-experiment/v1"
MEASUREMENT_SCHEMA = "crse-task-guard-shadow-measurement/v1"
SPLITS = ("c6_confirmatory_dev", "c12_sealed_a", "c12_sealed_b")
MODES = (
    "advice_disabled", "throughput", "latency_sensitive", "repeated_query",
    "memory_sensitive", "throughput_shadow",
)


@dataclass(frozen=True)
class TaskGuardConfig:
    repetitions: int = 9
    cache_capacity: int = 1024
    threads: int = 1
    max_seconds: int = 120

    def validate(self) -> None:
        if (type(self.repetitions) is not int or not 5 <= self.repetitions <= 15
                or type(self.cache_capacity) is not int
                or not 1 <= self.cache_capacity <= 16_384
                or self.threads != 1 or type(self.max_seconds) is not int
                or not 1 <= self.max_seconds <= 120):
            raise ValueError("invalid C14 task-guard configuration")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def source_fingerprints() -> dict[str, str]:
    paths = (
        ROOT / "cmbench/recognition/source_interaction.py",
        ROOT / "cmbench/recognition/adaptive_exact_dispatcher.py",
        ROOT / "cmbench/recognition/task_guarded_dispatcher.py",
        ROOT / "cmbench/recognition/task_guard_experiment.py",
        ROOT / "scripts/cm_recognition_task_guard.py",
    )
    return {relative(path): sha(path) for path in paths}


def _mode(mode: str):
    if mode == "advice_disabled":
        return ExactTaskContract("latency_sensitive"), False, False
    if mode == "throughput_shadow":
        return ExactTaskContract("throughput"), True, True
    if mode == "repeated_query":
        return ExactTaskContract(mode, expected_reuses=8), True, False
    return ExactTaskContract(mode), True, False


def run_task_guard_experiment(
    config: TaskGuardConfig,
    output: Path,
    *,
    input_path: Path = DEFAULT_INPUT,
    progress=print,
) -> dict:
    config.validate()
    output, input_path = output.resolve(), input_path.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = source_fingerprints()

    # Freeze and persist the task policy before opening the evaluation input.
    identity = current_platform_identity()
    policy = freeze_task_guard_policy(identity)
    write_json(output / "frozen_task_policy.json", policy)
    frozen_policy_sha256 = sha(output / "frozen_task_policy.json")
    run_spec = {
        "schema": "crse-task-guard-shadow-run-spec/v1",
        "purpose": "C14 task-level opt-in, abstention, advice-off and shadow confirmation",
        "input": relative(input_path), "expected_input_sha256": EXPECTED_INPUT_SHA256,
        "input_opened_after_policy_freeze": True,
        "modes": list(MODES), "splits": list(SPLITS), "config": asdict(config),
        "estimated_memory_mib": 384, "network": False, "training": False,
        "production_write": False,
        "shadow_contract": "production arm returned; exact alternative timed and compared only",
        "policy_cost": "charged once per compiled split/mode/n_vars workload",
    }
    write_json(output / "run_spec.json", run_spec)
    if sha(input_path) != EXPECTED_INPUT_SHA256:
        raise ValueError("changed frozen C14 evaluation input")
    all_documents = json.loads(input_path.read_text(encoding="utf-8"))
    documents = [row for row in all_documents if row["evaluation_split"] in SPLITS]
    if Counter(row["evaluation_split"] for row in documents) != Counter({
            "c6_confirmatory_dev": 36, "c12_sealed_a": 20, "c12_sealed_b": 20}):
        raise ValueError("changed C14 split cardinality")

    measurements = []
    started = time.perf_counter()
    for split in SPLITS:
        rows = [row for row in documents if row["evaluation_split"] == split]
        progress(f"C14 {split}: {len(rows)} cases")
        for repetition in range(config.repetitions):
            order = MODES[repetition % len(MODES):] + MODES[:repetition % len(MODES)]
            for mode in order:
                task, advice_enabled, shadow = _mode(mode)
                executors = {}
                for row in rows:
                    if time.perf_counter() - started > config.max_seconds:
                        raise TimeoutError("C14 cooperative wall budget exceeded")
                    n_vars = row["n_vars"]
                    if n_vars not in executors:
                        executors[n_vars] = compile_task_guard(
                            policy, task, n_vars=n_vars,
                            cache_capacity=config.cache_capacity, identity=identity,
                            advice_enabled=advice_enabled, shadow=shadow)
                    execution = executors[n_vars].execute(row["expression_v2"])
                    check_started = time.perf_counter_ns()
                    bits = document_truth_bits(row["expression_v2"], n_vars)
                    witness = (partition_witness(bits, n_vars, execution.partition)
                               if execution.partition is not None else None)
                    exact_check_ns = time.perf_counter_ns() - check_started
                    canonical = (tuple(row["witness"]["row_variables"])
                                 if row["witness"] is not None else None)
                    accepted = execution.partition is not None and witness is not None
                    measurements.append({
                        "schema": MEASUREMENT_SCHEMA, "repetition": repetition,
                        "mode": mode, "split": split, "case_id": row["case_id"],
                        "n_vars": n_vars, "label": row["label"],
                        "selected_arm": execution.selected_arm,
                        "decision_reason": execution.decision_reason,
                        "abstained": execution.abstained,
                        "predicted": int(execution.partition is not None),
                        "accepted": accepted,
                        "row_variables": (list(execution.partition)
                                          if execution.partition is not None else None),
                        "canonical_partition_match": execution.partition == canonical,
                        "semantic_mismatch": bool(accepted and not row["label"]),
                        "policy_ns": execution.policy_ns,
                        "production_ns": execution.production_ns,
                        "shadow_ns": execution.shadow_ns,
                        "charged_execution_ns": execution.total_ns,
                        "exact_check_ns": exact_check_ns,
                        "charged_total_ns": execution.total_ns + exact_check_ns,
                        "shadow_selected_arm": execution.shadow_selected_arm,
                        "shadow_partition_match": execution.shadow_partition_match,
                    })

    grouped = defaultdict(list)
    for row in measurements:
        grouped[(row["mode"], row["split"], row["case_id"])].append(row)
    per_case = []
    semantic_fields = ("selected_arm", "decision_reason", "abstained", "predicted",
                       "accepted", "row_variables", "canonical_partition_match",
                       "semantic_mismatch", "shadow_selected_arm",
                       "shadow_partition_match")
    for (mode, split, case_id), values in sorted(grouped.items()):
        first = values[0]
        if len(values) != config.repetitions or any(
                any(value[field] != first[field] for field in semantic_fields)
                for value in values[1:]):
            raise ValueError("nondeterministic or incomplete C14 result")
        per_case.append({
            "mode": mode, "split": split, "case_id": case_id,
            "n_vars": first["n_vars"], "label": first["label"],
            **{field: first[field] for field in semantic_fields},
            "median_policy_ns": int(statistics.median(row["policy_ns"] for row in values)),
            "median_production_ns": int(statistics.median(
                row["production_ns"] for row in values)),
            "median_shadow_ns": int(statistics.median(row["shadow_ns"] for row in values)),
            "median_charged_execution_ns": int(statistics.median(
                row["charged_execution_ns"] for row in values)),
            "median_exact_check_ns": int(statistics.median(
                row["exact_check_ns"] for row in values)),
            "median_charged_total_ns": int(statistics.median(
                row["charged_total_ns"] for row in values)),
        })

    mode_summary = {}
    for mode in MODES:
        for split in SPLITS:
            values = [row for row in per_case if row["mode"] == mode and row["split"] == split]
            production = [row["median_production_ns"] for row in values]
            charged = [row["median_charged_execution_ns"] for row in values]
            shadow = [row["median_shadow_ns"] for row in values]
            mode_summary[f"{mode}/{split}"] = {
                "cases": len(values), "sequence_production_ns": sum(production),
                "sequence_charged_execution_ns": sum(charged),
                "p95_production_ns": percentile(production, .95),
                "sequence_shadow_ns": sum(shadow),
                "selection_counts": dict(sorted(Counter(
                    row["selected_arm"] for row in values).items())),
                "abstentions": sum(row["abstained"] for row in values),
            }
    split_summary = {}
    for split in SPLITS:
        disabled = mode_summary[f"advice_disabled/{split}"]
        throughput = mode_summary[f"throughput/{split}"]
        latency = mode_summary[f"latency_sensitive/{split}"]
        shadow = mode_summary[f"throughput_shadow/{split}"]
        split_summary[split] = {
            "throughput_speedup_over_advice_disabled": (
                disabled["sequence_charged_execution_ns"]
                / throughput["sequence_charged_execution_ns"]),
            "latency_speedup_over_advice_disabled": (
                disabled["sequence_charged_execution_ns"]
                / latency["sequence_charged_execution_ns"]),
            "latency_p95_speedup_over_advice_disabled": (
                disabled["p95_production_ns"] / latency["p95_production_ns"]),
            "throughput_selection_counts": throughput["selection_counts"],
            "latency_selection_counts": latency["selection_counts"],
            "shadow_sequence_ns": shadow["sequence_shadow_ns"],
        }
    exact = all(row["predicted"] == row["label"]
                and row["canonical_partition_match"]
                and not row["semantic_mismatch"] for row in measurements)
    shadow_exact = all(row["shadow_partition_match"] is True
                       for row in measurements if row["mode"] == "throughput_shadow")
    throughput_no_regret = all(
        split_summary[split]["throughput_speedup_over_advice_disabled"] >= 1 / 1.03
        for split in SPLITS)
    dense_tail = (split_summary["c6_confirmatory_dev"]
                  ["latency_p95_speedup_over_advice_disabled"] >= 2)
    criteria = {
        "exact": exact, "shadow_exact": shadow_exact,
        "policy_frozen_before_input_load": True,
        "platform_identity_bound": True,
        "global_advice_disable_exact": True,
        "throughput_no_material_regret_3pct": throughput_no_regret,
        "latency_dense_tail_guard": dense_tail,
        "local_task_guard_gate": exact and shadow_exact and throughput_no_regret and dense_tail,
        "production_promotion": False,
    }
    result = {
        "schema": SCHEMA, "status": "complete",
        "wall_seconds": time.perf_counter() - started,
        "platform": platform.platform(), "python": sys.version.split()[0],
        "config": asdict(config), "frozen_policy_sha256": frozen_policy_sha256,
        "input": relative(input_path), "input_sha256": sha(input_path),
        "evaluation_cases": len(documents), "measurement_rows": len(measurements),
        "per_case_rows": len(per_case), "mode_summary": mode_summary,
        "split_summary": split_summary, "criteria": criteria,
        "semantic_mismatches": sum(row["semantic_mismatch"] for row in measurements),
        "source_unchanged": before == source_fingerprints(),
    }
    (output / "measurements.jsonl").write_text("".join(
        json.dumps(row, sort_keys=True) + "\n" for row in measurements), encoding="utf-8")
    write_json(output / "per_case.json", per_case)
    write_json(output / "summary.json", result)
    files = ("frozen_task_policy.json", "run_spec.json", "measurements.jsonl",
             "per_case.json", "summary.json")
    write_json(output / "manifest.json", {
        "schema": "crse-task-guard-shadow-artifacts/v1", "status": "complete",
        "files_sha256": {name: sha(output / name) for name in files},
        "source_sha256": before,
    })
    return result
