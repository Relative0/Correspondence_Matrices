"""Independent replay and artifact verification for C14."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.in_kernel_sentinel_experiment import EXPECTED_INPUT_SHA256
from cmbench.recognition.task_guard_experiment import MEASUREMENT_SCHEMA, MODES, SPLITS
from cmbench.recognition.task_guarded_dispatcher import validate_policy
from cmbench.recognition.yosys_source_anf_experiment import percentile


RUN = ROOT / "docs/recognition/runs/task-guard-shadow-20260830-001"
OUTPUT = ROOT / "docs/recognition/verification/task-guard-shadow-20260830-001.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    policy, spec, summary, manifest = (load(RUN / name) for name in (
        "frozen_task_policy.json", "run_spec.json", "summary.json", "manifest.json"))
    validate_policy(policy)
    per_case = load(RUN / "per_case.json")
    measurements = [json.loads(line) for line in
                    (RUN / "measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    input_path = ROOT / summary["input"]
    documents = load(input_path)
    documents = [row for row in documents if row["evaluation_split"] in SPLITS]

    require(sha(input_path) == EXPECTED_INPUT_SHA256 == summary["input_sha256"],
            "C14 input hash mismatch")
    artifact_names = ("frozen_task_policy.json", "run_spec.json", "measurements.jsonl",
                      "per_case.json", "summary.json")
    artifact_hashes = {name: sha(RUN / name) for name in artifact_names}
    require(manifest.get("status") == "complete"
            and manifest.get("files_sha256") == artifact_hashes,
            "C14 artifact hash mismatch")
    source_hashes = manifest.get("source_sha256")
    require(type(source_hashes) is dict and source_hashes
            and all(sha(ROOT / name) == digest for name, digest in source_hashes.items()),
            "C14 measured source changed")
    require(summary.get("status") == "complete"
            and summary.get("evaluation_cases") == 76
            and summary.get("measurement_rows") == 4104
            and summary.get("per_case_rows") == 456
            and summary.get("semantic_mismatches") == 0
            and summary.get("source_unchanged") is True
            and summary.get("frozen_policy_sha256") == sha(RUN / "frozen_task_policy.json"),
            "C14 summary scope mismatch")
    require(spec.get("modes") == list(MODES)
            and spec.get("splits") == list(SPLITS)
            and spec.get("input_opened_after_policy_freeze") is True
            and spec.get("network") is False
            and spec.get("training") is False
            and spec.get("production_write") is False,
            "C14 run specification changed")
    require(Counter(row["evaluation_split"] for row in documents) == Counter({
        "c6_confirmatory_dev": 36, "c12_sealed_a": 20, "c12_sealed_b": 20}),
        "C14 evaluation split changed")

    expected_keys = {(repetition, mode, split, row["case_id"])
                     for repetition in range(9) for mode in MODES for split in SPLITS
                     for row in documents if row["evaluation_split"] == split}
    observed_keys = {(row.get("repetition"), row.get("mode"), row.get("split"),
                      row.get("case_id")) for row in measurements}
    require(len(measurements) == len(observed_keys) == len(expected_keys) == 4104
            and observed_keys == expected_keys, "C14 raw rows incomplete or duplicated")
    expected_reason = {
        "advice_disabled": "advice_globally_disabled",
        "throughput": "task:throughput",
        "latency_sensitive": "task:latency_sensitive",
        "repeated_query": "task:repeated_query",
        "memory_sensitive": "task:memory_sensitive",
        "throughput_shadow": "task:throughput",
    }
    for row in measurements:
        require(row.get("schema") == MEASUREMENT_SCHEMA
                and all(type(row.get(field)) is int and row[field] >= 0 for field in (
                    "policy_ns", "production_ns", "shadow_ns", "charged_execution_ns",
                    "exact_check_ns", "charged_total_ns"))
                and row["charged_execution_ns"] == (
                    row["policy_ns"] + row["production_ns"] + row["shadow_ns"])
                and row["charged_total_ns"] == (
                    row["charged_execution_ns"] + row["exact_check_ns"])
                and row.get("predicted") == row.get("label")
                and row.get("canonical_partition_match") is True
                and row.get("semantic_mismatch") is False
                and row.get("decision_reason") == expected_reason[row["mode"]]
                and row.get("abstained") is False,
                "C14 timing, exactness, or decision row invalid")
        if row["mode"] == "throughput_shadow":
            require(row.get("shadow_partition_match") is True
                    and row.get("shadow_selected_arm") in {
                        "set_source_anf", "adaptive_set_to_packed"}
                    and row["shadow_ns"] > 0,
                    "C14 shadow row invalid")
        else:
            require(row.get("shadow_partition_match") is None
                    and row.get("shadow_selected_arm") is None
                    and row["shadow_ns"] == 0,
                    "C14 non-shadow row contains shadow execution")

    grouped = defaultdict(list)
    for row in measurements:
        grouped[(row["mode"], row["split"], row["case_id"])].append(row)
    rebuilt = []
    semantic_fields = ("selected_arm", "decision_reason", "abstained", "predicted",
                       "accepted", "row_variables", "canonical_partition_match",
                       "semantic_mismatch", "shadow_selected_arm",
                       "shadow_partition_match")
    for (mode, split, case_id), values in sorted(grouped.items()):
        require(len(values) == 9, "C14 per-case repetition count changed")
        first = values[0]
        require(all(all(value[field] == first[field] for field in semantic_fields)
                    for value in values[1:]), "C14 semantic replay changed by repetition")
        rebuilt.append({
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
    require(rebuilt == per_case, "C14 per-case rows do not reproduce")

    mode_summary = {}
    for mode in MODES:
        for split in SPLITS:
            values = [row for row in rebuilt if row["mode"] == mode and row["split"] == split]
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
    require(mode_summary == summary["mode_summary"],
            "C14 mode summaries do not reproduce")
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
    require(split_summary == summary["split_summary"],
            "C14 split summaries do not reproduce")

    exact = all(row["predicted"] == row["label"]
                and row["canonical_partition_match"]
                and not row["semantic_mismatch"] for row in measurements)
    shadow_exact = all(row["shadow_partition_match"] is True
                       for row in measurements if row["mode"] == "throughput_shadow")
    no_regret = all(split_summary[split]["throughput_speedup_over_advice_disabled"]
                    >= 1 / 1.03 for split in SPLITS)
    dense_tail = (split_summary["c6_confirmatory_dev"]
                  ["latency_p95_speedup_over_advice_disabled"] >= 2)
    require(summary["criteria"] == {
        "exact": exact, "shadow_exact": shadow_exact,
        "policy_frozen_before_input_load": True, "platform_identity_bound": True,
        "global_advice_disable_exact": True,
        "throughput_no_material_regret_3pct": no_regret,
        "latency_dense_tail_guard": dense_tail,
        "local_task_guard_gate": exact and shadow_exact and no_regret and dense_tail,
        "production_promotion": False,
    }, "C14 criteria do not reproduce")

    result = {
        "schema": "crse-task-guard-shadow-independent-verification/v1",
        "status": "pass", "run": relative(RUN),
        "manifest_sha256": sha(RUN / "manifest.json"),
        "files_verified": len(artifact_hashes), "source_files_verified": len(source_hashes),
        "evaluation_cases": 76, "semantic_rows_replayed": len(per_case),
        "timing_samples_checked": len(measurements), "semantic_mismatches": 0,
        "shadow_exact": shadow_exact, "throughput_no_material_regret_3pct": no_regret,
        "latency_dense_tail_guard": dense_tail, "local_task_guard_gate": True,
        "production_promotion": False, "split_summary": split_summary,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
