"""Independent standard-library replay of the frozen H2/H3 profile summary."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
from typing import Any, Mapping, Sequence


COMPONENTS = (
    "key_creation", "hashing", "interning", "serialization", "dense_lifting",
    "allocation", "conversion", "temporary_copies",
)
H2_COMPONENTS = ("key_creation", "hashing", "interning")
H3_COMPONENTS = ("dense_lifting", "allocation", "conversion", "temporary_copies")
SHA256 = frozenset("0123456789abcdef")


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode("ascii")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def valid_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= SHA256


def materiality(rows: Sequence[Mapping[str, Any]], freeze: Mapping[str, Any], hypothesis: str, component: str) -> dict[str, Any]:
    applicable = [row for row in rows if hypothesis in row["hypothesis_scope"]]
    exact = [
        row for row in applicable
        if row["status"] == "ok"
        and row["exact_oracle_agreement"]
        and row["stable_output_order_and_hashes"]
    ]
    parts = [int(row["profile"]["exclusive_self_ns"][component]) for row in exact]
    totals = [int(row["profile"]["accounted_self_ns"]) for row in exact]
    shares = [part / total if total else 0.0 for part, total in zip(parts, totals, strict=True)]
    gate = freeze["materiality_gate"]
    cohort_shares: dict[str, float] = {}
    for cohort in ("observed", "fresh"):
        selected = [
            (part, total)
            for row, part, total in zip(exact, parts, totals, strict=True)
            if row["cohort"] == cohort
        ]
        if selected:
            cohort_shares[cohort] = sum(part for part, _ in selected) / sum(total for _, total in selected)
    peak_excess = []
    for row in exact:
        peak = max(
            int(row["memory"].get("rss_incremental_peak_bytes") or 0),
            int(row["memory"].get("tracemalloc_incremental_peak_bytes") or 0),
        )
        required = int(row["required_artifact_bytes"])
        peak_excess.append(max(0.0, (peak - required) / max(1, required)))
    conditions = {
        "minimum_exact_cells": len(exact) >= gate["minimum_exact_cells"],
        "aggregate_exclusive_share": bool(totals) and sum(parts) / sum(totals) >= gate["aggregate_exclusive_share_min"],
        "median_cell_share": bool(shares) and statistics.median(shares) >= gate["median_cell_share_min"],
        "median_component_ns": bool(parts) and statistics.median(parts) >= gate["median_component_ns_min"],
        "cell_prevalence": bool(shares) and sum(value >= gate["cell_prevalence_share_floor"] for value in shares) / len(shares) >= gate["cell_prevalence_min"],
        "observed_and_fresh_floor": all(value >= gate["observed_and_fresh_aggregate_share_min"] for value in cohort_shares.values()) and set(cohort_shares) == {"observed", "fresh"},
        "allocation_copy_peak_excess": component not in {"allocation", "temporary_copies"} or (bool(peak_excess) and statistics.median(peak_excess) >= gate["allocation_copy_peak_excess_over_output_min"]),
    }
    return {
        "hypothesis": hypothesis,
        "component": component,
        "applicable_cells": len(applicable),
        "exact_cells": len(exact),
        "aggregate_exclusive_share": (sum(parts) / sum(totals) if totals and sum(totals) else 0.0),
        "median_cell_share": (statistics.median(shares) if shares else 0.0),
        "median_component_ns": (statistics.median(parts) if parts else 0.0),
        "cell_prevalence": (sum(value >= gate["cell_prevalence_share_floor"] for value in shares) / len(shares) if shares else 0.0),
        "cohort_aggregate_shares": cohort_shares,
        "median_peak_excess_over_output": (statistics.median(peak_excess) if peak_excess else 0.0),
        "conditions": conditions,
        "passes": all(conditions.values()),
    }


def expected_oracle_sha(row: Mapping[str, Any], oracles: Mapping[str, Any]) -> str:
    lane = row["row_id"].split(":", 1)[0]
    oracle = oracles["lanes"][lane][row["case_id"]]
    if lane == "A":
        return oracle["truth"]["sha256"]
    if lane == "B":
        return oracle["checkpoints"][str(row["query_count"])]
    if lane == "C":
        return oracle["output_sha256"]
    return oracle["sublanes"][row["operation"]]["output_sha256"]


def verify(project_root: Path, freeze_path: Path, raw_path: Path, summary_path: Path) -> dict[str, Any]:
    root = project_root.resolve()
    freeze = load(freeze_path)
    raw_text = raw_path.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in raw_text.splitlines() if line]
    summary = load(summary_path)

    freeze_core = {key: freeze[key] for key in freeze if key != "freeze_sha256"}
    require(freeze["freeze_sha256"] == digest(freeze_core), "freeze canonical digest")
    require(freeze["status"] == "frozen_before_decision_bearing_execution", "freeze status")
    require(freeze["continuation"]["h9_work_authorized"] is False, "H9 boundary")
    require(freeze["continuation"]["cloud_execution_authorized"] is False, "cloud boundary")
    require(sha256(raw_path) == summary["raw_measurements_sha256"], "raw file digest")
    require(summary["freeze_sha256"] == freeze["freeze_sha256"], "summary freeze identity")

    closure_mismatches = []
    for record in freeze["source_closure"]:
        path = root / record["path"]
        if not path.is_file() or path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            closure_mismatches.append(record["path"])
    require(not closure_mismatches, f"source closure mismatches: {closure_mismatches}")
    require(digest(freeze["source_closure"]) == freeze["source_closure_sha256"], "source closure digest")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()
    require(head == freeze["source_checkpoint"], "git checkpoint")

    parent_path = root / freeze["parent_freeze"]["path"]
    oracle_path = root / freeze["parent_oracles"]["path"]
    require(sha256(parent_path) == freeze["parent_freeze"]["file_sha256"], "parent freeze file")
    require(sha256(oracle_path) == freeze["parent_oracles"]["file_sha256"], "parent oracle file")
    parent = load(parent_path)
    parent_core = {key: parent[key] for key in parent if key != "freeze_sha256"}
    require(parent["freeze_sha256"] == digest(parent_core) == freeze["parent_freeze"]["canonical_sha256"], "parent canonical freeze")
    oracles = load(oracle_path)
    oracle_core = {key: oracles[key] for key in oracles if key != "oracles_sha256"}
    require(oracles["oracles_sha256"] == digest(oracle_core), "oracle canonical digest")

    expected_rows = (
        len(freeze["workload"]["complete_relation"]["case_ids"]) * 2
        + len(freeze["workload"]["repeated_restriction"]["case_ids"]) * 4
        + len(freeze["workload"]["related_multi_root"]["case_ids"]) * 4
        + len(freeze["workload"]["smaller_query"]["case_ids"]) * 13
    )
    require(len(rows) == expected_rows == summary["rows"], "row count")
    require(len({row["row_id"] for row in rows}) == len(rows), "unique row ids")
    noncanonical_lines = []
    for index, (line, row) in enumerate(zip([line for line in raw_text.splitlines() if line], rows, strict=True)):
        if line.encode("ascii") != canonical_bytes(row):
            noncanonical_lines.append(index)
        require(row["schema"] == "cm-h2-h3-profile-row/v1", "raw schema")
        require(row["status"] == "ok" and row["exact_oracle_agreement"], f"exactness {row['row_id']}")
        require(row["stable_output_order_and_hashes"], f"stability {row['row_id']}")
        require(all(valid_sha(row[key]) for key in ("output_sha256", "ordering_sha256", "structure_sha256")), "row hashes")
        require(row["output_sha256"] == expected_oracle_sha(row, oracles), f"independent oracle digest {row['row_id']}")
        require(len(row["raw_timing_trials"]) == freeze["measurement"]["repetitions"], "timing repetitions")
        for trial in row["raw_timing_trials"]:
            require(trial["accounted_total_ns"] == sum(trial["stages_ns"].values()), "timing accounting")
        for name in COMPONENTS:
            expected_share = (
                row["profile"]["exclusive_self_ns"][name] / row["profile"]["accounted_self_ns"]
                if row["profile"]["accounted_self_ns"] else 0.0
            )
            require(row["profile"]["exclusive_share"][name] == expected_share, "profile share")
        require(
            row["profile"]["mapped_self_ns"] == sum(row["profile"]["exclusive_self_ns"].values())
            and row["profile"]["unmapped_self_ns"] == row["profile"]["accounted_self_ns"] - row["profile"]["mapped_self_ns"],
            "profile accounting",
        )
        memory = row["memory"]
        require(memory["rss_available"] and memory["rss_sampler_stopped"] and memory["rss_sample_count"] >= 1, "RSS lifecycle")
        require(memory["rss_incremental_peak_bytes"] >= 0 and memory["tracemalloc_incremental_peak_bytes"] >= 0, "peak memory")
        require(memory["rss_retained_delta_bytes"] == memory["rss_retained_bytes"] - memory["rss_baseline_bytes"], "retained RSS")
        require(memory["tracemalloc_retained_delta_bytes"] == memory["tracemalloc_retained_bytes"] - memory["tracemalloc_baseline_bytes"], "retained traced")
    require(not noncanonical_lines, f"noncanonical raw lines: {noncanonical_lines}")

    replay = [
        *[materiality(rows, freeze, "H2", component) for component in H2_COMPONENTS],
        *[materiality(rows, freeze, "H3", component) for component in H3_COMPONENTS],
    ]
    require(canonical_bytes(replay) == canonical_bytes(summary["materiality"]), "materiality replay")
    passing = sorted(
        [row for row in replay if row["passes"]],
        key=lambda row: (-row["aggregate_exclusive_share"], row["component"]),
    )
    require(not passing and summary["qualifying_components"] == [], "no qualifying component")
    require(summary["decision"] == "no_go_close_h2_h3_still_deferred", "final decision")
    require(summary["selected_candidate_component"] is None and summary["candidate_implemented"] is False, "no candidate")
    require(summary["runpod_authorization_request_permitted"] is False, "no RunPod request")
    summary_core = {key: summary[key] for key in summary if key != "summary_sha256"}
    require(summary["summary_sha256"] == digest(summary_core), "summary digest")

    result_core = {
        "schema": "cm-h2-h3-profile-independent-verification/v1",
        "status": "verified_no_go_close_h2_h3_still_deferred",
        "freeze_sha256": freeze["freeze_sha256"],
        "raw_measurements_sha256": sha256(raw_path),
        "summary_sha256": summary["summary_sha256"],
        "source_checkpoint": head,
        "source_closure_mismatches": closure_mismatches,
        "rows_replayed": len(rows),
        "oracle_digest_mismatches": 0,
        "exactness_mismatches": 0,
        "ordering_or_hash_mismatches": 0,
        "memory_accounting_mismatches": 0,
        "summary_replay_mismatches": 0,
        "qualifying_components": [],
        "candidate_permitted": False,
        "runpod_authorization_request_permitted": False,
    }
    return {**result_core, "verification_sha256": digest(result_core)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = verify(
        Path(args.project_root), Path(args.freeze).resolve(), Path(args.raw).resolve(),
        Path(args.summary).resolve(),
    )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

