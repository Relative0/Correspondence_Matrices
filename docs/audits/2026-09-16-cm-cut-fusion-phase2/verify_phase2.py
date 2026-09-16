"""Recompute the frozen Phase-2 decision from preserved JSON evidence."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIXED_CONTROLS = (
    "direct",
    "r2",
    "cse",
    "cm",
    "pack_cse",
    "pack_cm",
    "d10_cse",
    "d10_cm",
    "fixpoint_cse",
    "fixpoint_cm",
    "precompute_full",
)
COMPONENTS = ("parse_ns", "compile_ns", "bind_ns", "execute_ns", "output_ns", "total_ns")


def load(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gmean(values):
    values = list(values)
    return math.exp(sum(math.log(value) for value in values) / len(values))


def medians(rows, *, families, q, arm):
    groups = defaultdict(list)
    for row in rows:
        if row["family"] in families and row["q"] == q and row["arm"] == arm:
            groups[row["case_id"]].append(row)
    return {
        case_id: {field: statistics.median(item[field] for item in items) for field in COMPONENTS}
        for case_id, items in groups.items()
    }


def best_fixed(rows, *, families, q):
    scored = {}
    for arm in FIXED_CONTROLS:
        arm_medians = medians(rows, families=families, q=q, arm=arm)
        if arm_medians:
            scored[arm] = gmean(value["total_ns"] for value in arm_medians.values())
    return min(scored, key=scored.get), scored


def family_gate(rows, family, q):
    baseline, scores = best_fixed(rows, families={family}, q=q)
    candidate = medians(rows, families={family}, q=q, arm="candidate_cse")
    control = medians(rows, families={family}, q=q, arm=baseline)
    ratios = {case_id: control[case_id]["total_ns"] / value["total_ns"] for case_id, value in candidate.items()}
    return {
        "best_fixed_control": baseline,
        "best_fixed_total_ns": scores[baseline],
        "candidate_total_ns": gmean(value["total_ns"] for value in candidate.values()),
        "geomean_speedup": gmean(ratios.values()),
        "minimum_case_speedup": min(ratios.values()),
        "cohort_floor_pass": gmean(ratios.values()) >= 0.95,
        "individual_floor_pass": min(ratios.values()) >= 0.80,
    }


def main():
    stage_a = load("stage-a-results-v4.json")
    stage_a_source = load("source-manifest-v4.json")
    development = load("stage-b-development-results.json")
    confirmation = load("stage-b-locked_confirmation-results.json")
    rows = confirmation["rows"]

    primary_families = {"F1", "F2"}
    baseline, baseline_scores = best_fixed(rows, families=primary_families, q=64)
    candidate = medians(rows, families=primary_families, q=64, arm="candidate_cse")
    control = medians(rows, families=primary_families, q=64, arm=baseline)
    component_geomeans = {
        "control": {field: gmean(value[field] for value in control.values()) for field in COMPONENTS},
        "candidate": {field: gmean(value[field] for value in candidate.values()) for field in COMPONENTS},
    }
    primary_speedup = component_geomeans["control"]["total_ns"] / component_geomeans["candidate"]["total_ns"]

    per_round = []
    for round_index in range(7):
        round_rows = [
            row for row in rows
            if row["family"] in primary_families and row["q"] == 64 and row["round"] == round_index
        ]
        control_total = gmean(row["total_ns"] for row in round_rows if row["arm"] == baseline)
        candidate_total = gmean(row["total_ns"] for row in round_rows if row["arm"] == "candidate_cse")
        per_round.append({
            "round": round_index,
            "speedup": control_total / candidate_total,
            "win": control_total / candidate_total > 1.0,
        })

    break_even = {}
    for case_id in sorted(candidate):
        base = control[case_id]
        cand = candidate[case_id]
        setup_delta = (cand["parse_ns"] + cand["compile_ns"]) - (base["parse_ns"] + base["compile_ns"])
        base_request = (base["bind_ns"] + base["execute_ns"] + base["output_ns"]) / 64
        cand_request = (cand["bind_ns"] + cand["execute_ns"] + cand["output_ns"]) / 64
        saving = base_request - cand_request
        break_even[case_id] = None if saving <= 0 else math.ceil(max(0, setup_delta) / saving)

    controls = {
        family: {str(q): family_gate(rows, family, q) for q in (1, 4, 16, 64)}
        for family in ("F3", "F4", "F5", "F6")
    }

    def verify_timing(document, expected_rows, expected_receipts):
        by_cell = defaultdict(set)
        for row in document["rows"]:
            by_cell[(row["case_id"], row["round"], row["q"])].add(tuple(row["output_sha256"]))
        return {
            "status": document["status"],
            "rows": len(document["rows"]),
            "expected_rows": expected_rows,
            "receipts": len(document["receipts"]),
            "expected_receipts": expected_receipts,
            "refusals": len(document["refusals"]),
            "all_rows_ok": all(row["status"] == "ok" for row in document["rows"]),
            "all_outputs_exact_across_arms": all(len(values) == 1 for values in by_cell.values()),
            "all_receipts_ok_and_clean": all(
                receipt["status"] == "ok" and receipt["cleanup_verified"]
                for receipt in document["receipts"]
            ),
            "max_worker_peak_committed_bytes": max(receipt["peak_memory_bytes"] for receipt in document["receipts"]),
        }

    stage_a_check = {
        "status": stage_a["status"],
        "case_count": len(stage_a["cases"]),
        "receipt_count": len(stage_a["receipts"]),
        "all_receipts_ok_and_clean": all(
            receipt["status"] == "ok" and receipt["cleanup_verified"]
            for receipt in stage_a["receipts"]
        ),
        **stage_a["gates"],
    }

    primary_gate = {
        "families": ["F1", "F2"],
        "q": 64,
        "best_fixed_control": baseline,
        "fixed_control_totals_ns": baseline_scores,
        "component_geomeans_ns": component_geomeans,
        "speedup": primary_speedup,
        "required_speedup": 1.10,
        "per_round": per_round,
        "speedup_pass": primary_speedup >= 1.10,
        "every_round_win_pass": all(item["win"] for item in per_round),
        "pass": primary_speedup >= 1.10 and all(item["win"] for item in per_round),
    }
    control_pass = all(
        result["cohort_floor_pass"] and result["individual_floor_pass"]
        for family in controls.values() for result in family.values()
    )

    result = {
        "schema": "cm-cut-fusion-phase2-verification/v1",
        "decision": "STOP",
        "stop_reason": "locked F1/F2 q64 whole-session latency gate failed",
        "head": stage_a_source["head"],
        "stage_a": stage_a_check,
        "timing_integrity": {
            "development": verify_timing(development, 8736, 168),
            "locked_confirmation": verify_timing(confirmation, 13104, 252),
            "exact_request_outputs": 464100,
        },
        "locked_f1_f2_q64": primary_gate,
        "control_family_gates": controls,
        "control_family_combined_pass": control_pass,
        "stationary_break_even_q_estimates": break_even,
        "stationary_break_even_range": [min(break_even.values()), max(break_even.values())],
        "stationary_break_even_note": "Estimate from q64 median setup and per-request costs; all crossings are outside the measured q<=64 range.",
        "unrun_after_stop": [
            "exposed 82-case natural timing panel",
            "per-arm relative peak-memory promotion sweep",
            "retained-plan replay diagnostic",
        ],
        "abc_control": confirmation["abc_control"],
    }

    source_files = [
        Path("cmbench/recognition/cut_fusion.py"),
        Path("tests/test_cut_fusion.py"),
        Path("docs/audits/2026-09-16-cm-cut-fusion-phase2/run_stage_a.py"),
        Path("docs/audits/2026-09-16-cm-cut-fusion-phase2/run_stage_a_v2.py"),
        Path("docs/audits/2026-09-16-cm-cut-fusion-phase2/run_stage_a_v3.py"),
        Path("docs/audits/2026-09-16-cm-cut-fusion-phase2/run_stage_a_v4.py"),
        Path("docs/audits/2026-09-16-cm-cut-fusion-phase2/run_stage_b.py"),
        Path("docs/audits/2026-09-16-cm-cut-fusion-phase2/verify_phase2.py"),
        Path("docs/audits/2026-09-16-cm-cut-fusion-phase2/ADJUDICATION.md"),
        Path("docs/audits/2026-09-16-cm-cut-fusion-phase2/source-manifest-v4.json"),
        Path("docs/audits/2026-09-16-cm-cut-fusion-phase2/synthetic-manifest.json"),
        Path("docs/audits/2026-09-16-cm-cut-fusion-phase2/template-table.json"),
    ]
    result["source_and_manifest_sha256"] = {path.as_posix(): sha256(ROOT / path) for path in source_files}
    verification_path = HERE / "phase2-verification.json"
    verification_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    evidence_files = (
        "ADJUDICATION.md",
        "resource-diagnosis.json",
        "source-manifest-v4.json",
        "stage-a-results-v4.json",
        "stage-b-development-results.json",
        "stage-b-locked_confirmation-results.json",
        "synthetic-manifest.json",
        "template-table.json",
        "phase2-verification.json",
    )
    evidence_index = {
        "schema": "cm-cut-fusion-phase2-evidence-index/v1",
        "head": result["head"],
        "decision": result["decision"],
        "files_sha256": {name: sha256(HERE / name) for name in evidence_files},
    }
    (HERE / "evidence-index.json").write_text(json.dumps(evidence_index, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": result["decision"],
        "primary_speedup": primary_speedup,
        "primary_gate_pass": primary_gate["pass"],
        "control_family_combined_pass": control_pass,
        "development_integrity": result["timing_integrity"]["development"],
        "confirmation_integrity": result["timing_integrity"]["locked_confirmation"],
        "break_even_range": result["stationary_break_even_range"],
    }, indent=2))


if __name__ == "__main__":
    main()
