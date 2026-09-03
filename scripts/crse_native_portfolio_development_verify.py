"""Read-only replay verifier for a native exact-portfolio development run."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.gf2_native_portfolio_experiment import (
    MANIFEST_SCHEMA,
    METHODS,
    NON_NATIVE_METHODS,
    RAW_SCHEMA,
    SCHEMA,
    STAGES,
)
from cmbench.comparative.schedule import balanced_orders
from scripts.crse_verify_c36_wide_repeated_query_dataset import (
    independent_output,
    independent_trace,
)


VERIFICATION_SCHEMA = "crse-native-portfolio-independent-verification/v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def project_path(relative: str, project_root: Path = ROOT) -> Path:
    root = project_root.resolve()
    path = root.joinpath(*Path(relative).parts).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("verifier path escaped or is missing")
    return path


def _recompute_summary(rows: list[dict[str, Any]], cases: list[dict[str, Any]]) -> dict[str, Any]:
    performance = [row for row in rows if row["role"] == "performance"]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in performance:
        grouped[(row["case_id"], row["method"])].append(row)
    medians = {
        (case["case_id"], method): {
            stage: int(statistics.median_low(
                row["timings_ns"][stage]
                for row in grouped[(case["case_id"], method)]
            ))
            for stage in STAGES
        }
        for case in cases for method in METHODS
    }
    totals = {
        method: {
            stage: sum(medians[(case["case_id"], method)][stage] for case in cases)
            for stage in STAGES
        }
        for method in METHODS
    }
    q64 = {method: totals[method]["accounted_total_ns"] for method in METHODS}
    best = min(METHODS, key=lambda method: (q64[method], method))
    best_non_native = min(
        NON_NATIVE_METHODS, key=lambda method: (q64[method], method))
    winners = {
        case["case_id"]: min(
            METHODS,
            key=lambda method: (
                medians[(case["case_id"], method)]["accounted_total_ns"], method),
        )
        for case in cases
    }
    oracle = sum(
        medians[(case["case_id"], winners[case["case_id"]])]["accounted_total_ns"]
        for case in cases
    )
    memory = {}
    for method in METHODS:
        selected = [row for row in rows
                    if row["role"] == "memory_profile" and row["method"] == method]
        memory[method] = {
            "sessions": len(selected),
            "max_tracemalloc_peak_bytes": max(
                row["resources"].get("tracemalloc_peak_bytes", 0)
                for row in selected),
            "max_sampled_rss_delta_bytes": max(
                row["resources"].get(
                    "session_sampled_peak_rss_delta_bytes",
                    row["resources"].get("rss_end_minus_start_bytes", 0),
                ) or 0
                for row in selected),
        }
    native_speedup = q64[best_non_native] / q64["native_fused_slots"]
    headroom = q64[best] / oracle
    return {
        "cases": len(cases),
        "performance_sessions": len(performance),
        "memory_profile_sessions": sum(row["role"] == "memory_profile" for row in rows),
        "timed_queries": len(performance) * 64,
        "aggregate_case_median_stage_ns": totals,
        "q64_accounted_total_ns": q64,
        "best_fixed_method": best,
        "best_non_native_method": best_non_native,
        "native_speedup_over_best_non_native": native_speedup,
        "native_ten_percent_gate": native_speedup >= 1.10,
        "per_case_winners": dict(sorted(winners.items())),
        "per_case_winner_counts": dict(sorted(Counter(winners.values()).items())),
        "native_case_wins": sum(value == "native_fused_slots" for value in winners.values()),
        "per_case_oracle_total_ns": oracle,
        "oracle_speedup_over_best_fixed": headroom,
        "selector_development_headroom_gate": headroom >= 1.10,
        "memory_profiles": memory,
    }


def verify_run(run_dir: Path, project_root: Path = ROOT) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    project_root = project_root.resolve()
    manifest = load(run_dir / "manifest.json")
    results = load(run_dir / "results.json")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("native portfolio manifest schema")
    if results.get("schema") != SCHEMA or results.get("status") != "complete":
        raise ValueError("native portfolio result schema")

    artifact_mismatches = 0
    for name, identity in manifest.get("artifacts", {}).items():
        path = run_dir / name
        artifact_mismatches += int(
            not path.is_file()
            or path.stat().st_size != identity.get("bytes")
            or sha256(path) != identity.get("sha256")
        )
    source_mismatches = 0
    for relative, identity in manifest.get("sources", {}).items():
        try:
            path = project_path(relative, project_root)
        except ValueError:
            source_mismatches += 1
            continue
        source_mismatches += int(
            path.stat().st_size != identity.get("bytes")
            or sha256(path) != identity.get("sha256")
        )
    interpreter = manifest.get("interpreter", {})
    interpreter_path = Path(interpreter.get("path", ""))
    interpreter_mismatches = int(
        not interpreter_path.is_file()
        or interpreter_path.stat().st_size != interpreter.get("bytes")
        or sha256(interpreter_path) != interpreter.get("sha256")
    )
    native = manifest.get("native_library", {})
    try:
        native_path = project_path(native.get("path", ""), project_root)
    except ValueError:
        native_path = Path()
    native_mismatches = int(
        not native_path.is_file()
        or native_path.stat().st_size != native.get("bytes")
        or sha256(native_path) != native.get("sha256")
        or native.get("abi_version") != 1
    )

    dataset_path = project_path(results["dataset"]["path"], project_root)
    dataset = load(dataset_path)
    dataset_verification = load(project_root / "docs/recognition/c36_wide_repeated_query_dataset_verification.json")
    dataset_mismatches = int(
        sha256(dataset_path) != results["dataset"]["sha256"]
        or dataset_verification.get("status") != "verified"
        or dataset_verification.get("dataset_sha256") != sha256(dataset_path)
        or results["dataset"].get("classification")
        != "development_exposed_c36_not_confirmation"
    )
    cases = list(dataset["cases"])
    expected = {
        case["case_id"]: digest(independent_output(
            case, independent_trace(case["case_id"], case["n_vars"])))
        for case in cases
    }

    raw = [
        json.loads(line)
        for line in (run_dir / "raw_measurements.jsonl").read_text(
            encoding="utf-8").splitlines()
        if line.strip()
    ]
    performance = [row for row in raw if row.get("role") == "performance"]
    memory = [row for row in raw if row.get("role") == "memory_profile"]
    orders = balanced_orders(METHODS)
    structure_mismatches = int(
        tuple(results.get("methods", ())) != METHODS
        or results.get("config", {}).get("blocks") != len(orders)
        or len(performance) != len(orders) * len(cases) * len(METHODS)
        or len(memory) != len(cases) * len(METHODS)
    )
    schedule_mismatches = 0
    offset = 0
    for block, order in enumerate(orders):
        case_order = list(cases)
        random.Random(results["config"]["seed"] + block).shuffle(case_order)
        for case_position, case in enumerate(case_order):
            for method_position, method in enumerate(order):
                row = performance[offset]
                offset += 1
                schedule_mismatches += int(
                    row.get("block") != block
                    or row.get("case_position") != case_position
                    or row.get("method_position") != method_position
                    or tuple(row.get("method_order", ())) != order
                    or row.get("case_id") != case["case_id"]
                    or row.get("method") != method
                )
    for case_position, case in enumerate(cases):
        order = orders[case_position % len(orders)]
        selected = memory[case_position * len(METHODS):(case_position + 1) * len(METHODS)]
        for method_position, (row, method) in enumerate(zip(selected, order, strict=True)):
            schedule_mismatches += int(
                row.get("block") is not None
                or row.get("case_position") != case_position
                or row.get("method_position") != method_position
                or tuple(row.get("method_order", ())) != order
                or row.get("case_id") != case["case_id"]
                or row.get("method") != method
            )

    correctness_mismatches = 0
    timing_mismatches = 0
    native_identity_mismatches = 0
    for row in raw:
        timings = row.get("timings_ns", {})
        correctness_mismatches += int(
            row.get("schema") != RAW_SCHEMA
            or row.get("status") != "ok"
            or row.get("method") not in METHODS
            or row.get("exact_check_passed") is not True
            or row.get("output_sha256") != expected.get(row.get("case_id"))
        )
        timing_mismatches += int(
            any(type(timings.get(stage)) is not int or timings.get(stage, 0) <= 0
                for stage in STAGES)
            or timings.get("query_total_ns") != (
                timings.get("restriction_setup_ns", 0)
                + timings.get("evaluation_ns", 0)
                + timings.get("delivery_ns", 0)
            )
            or timings.get("accounted_total_ns") != (
                timings.get("input_decode_ns", 0)
                + timings.get("representation_ns", 0)
                + timings.get("restriction_setup_ns", 0)
                + timings.get("evaluation_ns", 0)
                + timings.get("delivery_ns", 0)
                + timings.get("cleanup_ns", 0)
            )
        )
        if row.get("method") == "native_fused_slots":
            resources = row.get("resources", {})
            native_identity_mismatches += int(
                resources.get("native_library_sha256") != native.get("sha256")
                or resources.get("native_abi_version") != 1
            )

    recomputed = _recompute_summary(raw, cases)
    reported = results.get("summary", {})
    summary_mismatches = 0
    for key, value in recomputed.items():
        actual = reported.get(key)
        if isinstance(value, float):
            summary_mismatches += int(
                not isinstance(actual, (int, float))
                or not math.isclose(value, actual, rel_tol=1e-12, abs_tol=0.0)
            )
        else:
            summary_mismatches += int(actual != value)
    decision = results.get("decision", {})
    decision_mismatches = int(
        decision.get("native_fixed_improvement_gate")
        != recomputed["native_ten_percent_gate"]
        or decision.get("selector_development_headroom_gate")
        != recomputed["selector_development_headroom_gate"]
        or decision.get("prospective_confirmation_allowed")
        != (recomputed["native_ten_percent_gate"]
            and recomputed["selector_development_headroom_gate"])
        or any(decision.get(field) is not False for field in (
            "training_allowed", "training_performed", "prospective_data_consumed",
            "production_write", "production_promotion"))
    )
    failures = {
        "artifact_mismatches": artifact_mismatches,
        "source_mismatches": source_mismatches,
        "interpreter_mismatches": interpreter_mismatches,
        "native_mismatches": native_mismatches,
        "dataset_mismatches": dataset_mismatches,
        "structure_mismatches": structure_mismatches,
        "schedule_mismatches": schedule_mismatches,
        "correctness_mismatches": correctness_mismatches,
        "timing_mismatches": timing_mismatches,
        "native_identity_mismatches": native_identity_mismatches,
        "summary_mismatches": summary_mismatches,
        "decision_mismatches": decision_mismatches,
    }
    if any(failures.values()):
        raise RuntimeError(f"native portfolio verification failed: {failures}")
    return {
        "schema": VERIFICATION_SCHEMA,
        "status": "verified",
        "run_id": results["run_id"],
        "performance_sessions": len(performance),
        "memory_profile_sessions": len(memory),
        "queries_replayed_independently": len(cases) * 64,
        "raw_query_rows_checked": len(raw) * 64,
        "results_sha256": sha256(run_dir / "results.json"),
        "manifest_sha256": sha256(run_dir / "manifest.json"),
        "native_library_sha256": native["sha256"],
        "training_performed": False,
        "prospective_data_consumed": False,
        "production_write": False,
        "production_promotion": False,
        **failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    if not run_dir.is_relative_to(ROOT.resolve()) or not run_dir.is_dir():
        raise ValueError("run directory escaped the project")
    result = verify_run(run_dir)
    if args.write:
        path = run_dir / "independent_verification.json"
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, sort_keys=True, ensure_ascii=True,
                      allow_nan=False)
            handle.write("\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
