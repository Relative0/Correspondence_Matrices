"""Independent replay and artifact verification for C13."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cmbench.recognition.in_kernel_sentinel_experiment import (
    EXPECTED_INPUT_SHA256, FROZEN_PRODUCT_PAIR_BUDGET, MEASUREMENT_SCHEMA,
    METHODS, SPLITS,
)
from cmbench.recognition.yosys_source_anf_experiment import percentile


RUN = ROOT / "docs/recognition/runs/in-kernel-tail-sentinel-20260830-003"
OUTPUT = ROOT / "docs/recognition/verification/in-kernel-tail-sentinel-20260830-003.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    spec, summary, manifest = (load(RUN / name) for name in
                               ("run_spec.json", "summary.json", "manifest.json"))
    per_case = load(RUN / "per_case.json")
    measurements = [json.loads(line) for line in
                    (RUN / "measurements.jsonl").read_text(encoding="utf-8").splitlines()]
    input_path = ROOT / summary["input"]
    documents = load(input_path)
    require(sha(input_path) == EXPECTED_INPUT_SHA256 == summary["input_sha256"],
            "C13 input hash mismatch")
    artifact_hashes = {name: sha(RUN / name) for name in
                       ("run_spec.json", "measurements.jsonl", "per_case.json", "summary.json")}
    require(manifest.get("status") == "complete"
            and manifest.get("files_sha256") == artifact_hashes,
            "C13 artifact hash mismatch")
    require(summary.get("status") == "complete"
            and summary.get("product_pair_budget") == FROZEN_PRODUCT_PAIR_BUDGET
            and summary.get("evaluation_cases") == 188
            and summary.get("measurement_rows") == 11280
            and summary.get("per_case_rows") == 752
            and summary.get("semantic_mismatches") == 0
            and summary.get("source_unchanged") is True,
            "C13 summary scope mismatch")
    require(spec.get("methods") == list(METHODS)
            and spec.get("splits") == list(SPLITS)
            and spec.get("network") is False
            and spec.get("training") is False
            and spec.get("production_write") is False,
            "C13 run specification changed")

    expected_keys = {(repetition, method, split, row["case_id"])
                     for repetition in range(15) for method in METHODS for split in SPLITS
                     for row in documents if row["evaluation_split"] == split}
    observed_keys = {(row.get("repetition"), row.get("method"), row.get("split"),
                      row.get("case_id")) for row in measurements}
    require(len(measurements) == len(observed_keys) == len(expected_keys) == 11280
            and observed_keys == expected_keys, "C13 raw rows incomplete or duplicated")
    for row in measurements:
        require(row.get("schema") == MEASUREMENT_SCHEMA
                and type(row.get("solve_ns")) is int and row["solve_ns"] >= 0
                and type(row.get("exact_check_ns")) is int and row["exact_check_ns"] >= 0
                and row.get("total_ns") == row["solve_ns"] + row["exact_check_ns"]
                and row.get("predicted") == row.get("label")
                and row.get("canonical_partition_match") is True
                and row.get("semantic_mismatch") is False,
                "C13 timing or exactness row invalid")
        instrumentation = row.get("instrumentation")
        if row["method"] == "sentinel_measured":
            require(type(instrumentation) is dict
                    and instrumentation.get("product_pair_budget") == 4096
                    and 0 <= instrumentation.get("set_executed_product_pairs", -1) <= 4096,
                    "C13 measured instrumentation invalid")
        else:
            require(instrumentation is None,
                    "C13 non-measured arm unexpectedly exposed counters")

    grouped = defaultdict(list)
    for row in measurements:
        grouped[(row["method"], row["split"], row["case_id"])].append(row)
    rebuilt = []
    semantic_fields = ("selected_arm", "predicted", "accepted", "row_variables",
                       "canonical_partition_match", "semantic_mismatch")
    for (method, split, case_id), values in sorted(grouped.items()):
        require(len(values) == 15, "C13 per-case repetition count changed")
        first = values[0]
        require(all(all(value[field] == first[field] for field in semantic_fields)
                    for value in values[1:]), "C13 semantic replay changed by repetition")
        source = next(row for row in documents if row["case_id"] == case_id)
        rebuilt.append({
            "method": method, "split": split, "case_id": case_id,
            "n_vars": first["n_vars"], "label": first["label"],
            **{field: first[field] for field in semantic_fields},
            "median_solve_ns": int(statistics.median(row["solve_ns"] for row in values)),
            "median_exact_check_ns": int(statistics.median(
                row["exact_check_ns"] for row in values)),
            "median_total_ns": int(statistics.median(row["total_ns"] for row in values)),
            "timing_repetitions": 15, "source_scope": source["source_scope"],
        })
    require(rebuilt == per_case, "C13 per-case rows do not reproduce")

    method_summary = {}
    for method in METHODS:
        for split in SPLITS:
            values = [row for row in rebuilt
                      if row["method"] == method and row["split"] == split]
            solve = [row["median_solve_ns"] for row in values]
            total = [row["median_total_ns"] for row in values]
            method_summary[f"{method}/{split}"] = {
                "cases": len(values), "sequence_solve_ns": sum(solve),
                "median_solve_ns": statistics.median(solve),
                "p95_solve_ns": percentile(solve, .95), "maximum_solve_ns": max(solve),
                "sequence_total_ns": sum(total),
                "selection_counts": dict(sorted(Counter(
                    row["selected_arm"] for row in values).items())),
            }
    require(method_summary == summary["method_summary"],
            "C13 method summaries do not reproduce")
    split_summary = {}
    for split in SPLITS:
        base = method_summary[f"set_no_sentinel/{split}"]
        off = method_summary[f"advice_disabled/{split}"]
        fast = method_summary[f"sentinel_fast/{split}"]
        measured = method_summary[f"sentinel_measured/{split}"]
        split_summary[split] = {
            "sentinel_fast_speedup_over_set": base["sequence_solve_ns"] / fast["sequence_solve_ns"],
            "sentinel_fast_p95_speedup_over_set": base["p95_solve_ns"] / fast["p95_solve_ns"],
            "sentinel_measured_speedup_over_fast": fast["sequence_solve_ns"] / measured["sequence_solve_ns"],
            "advice_disabled_speedup_over_set": base["sequence_solve_ns"] / off["sequence_solve_ns"],
            "sentinel_fast_selection_counts": fast["selection_counts"],
            "set_sequence_solve_ns": base["sequence_solve_ns"],
            "sentinel_fast_sequence_solve_ns": fast["sequence_solve_ns"],
        }
    require(split_summary == summary["split_summary"],
            "C13 split summaries do not reproduce")
    for split in SPLITS:
        set_rows = {row["case_id"]: row for row in rebuilt
                    if row["split"] == split and row["method"] == "set_no_sentinel"}
        off_rows = {row["case_id"]: row for row in rebuilt
                    if row["split"] == split and row["method"] == "advice_disabled"}
        require({key: tuple(row[field] for field in semantic_fields) for key, row in set_rows.items()}
                == {key: tuple(row[field] for field in semantic_fields) for key, row in off_rows.items()},
                "C13 advice-off result differs from no-sentinel execution")

    criteria = summary["criteria"]
    require(criteria.get("exact") is True
            and criteria.get("advice_disabled_exact") is True
            and criteria.get("dense_tail_guard") is True
            and criteria.get("sparse_no_material_regret") is False
            and criteria.get("local_engineering_gate") is False
            and criteria.get("production_promotion") is False,
            "C13 retained negative decision changed")
    result = {
        "schema": "crse-in-kernel-tail-sentinel-independent-verification/v1",
        "status": "pass", "run": relative(RUN),
        "manifest_sha256": sha(RUN / "manifest.json"),
        "files_verified": len(artifact_hashes), "evaluation_cases": 188,
        "semantic_rows_replayed": len(per_case),
        "timing_samples_checked": len(measurements),
        "semantic_mismatches": 0, "advice_disabled_exact": True,
        "dense_tail_guard": True, "sparse_no_material_regret": False,
        "local_engineering_gate": False, "production_promotion": False,
        "split_summary": split_summary,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps(result, sort_keys=True))


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


if __name__ == "__main__":
    main()
