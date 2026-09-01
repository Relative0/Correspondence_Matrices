"""Record the independently verified C23 Windows/Linux comparison."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
LOCAL = DOCS / "runs/c23-yosys-fresh-gf2-table-windows-20260831-002/results.json"
LINUX = (DOCS / "c23_linux_confirmation/runpod-c23-linux-execute-002c/evidence/run-output/"
         "c23-yosys-fresh-gf2-table-linux-20260831-001/results.json")
LINUX_FINAL = (
    DOCS / "c23_linux_confirmation/RUNPOD_C23_RETRY_002C_FINAL_VERIFICATION_20260831.json")
OUTPUT = DOCS / "c23_linux_confirmation/C23_LOCAL_LINUX_COMPARISON_20260831.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    local, linux, final = load(LOCAL), load(LINUX), load(LINUX_FINAL)
    local_summary, linux_summary = local["summary"], linux["summary"]
    methods = sorted(local_summary["methods"])
    if (
        methods != sorted(linux_summary["methods"])
        or local.get("status") != "complete"
        or linux.get("status") != "complete"
        or local.get("semantic_or_artifact_mismatches") != 0
        or linux.get("semantic_or_artifact_mismatches") != 0
        or local.get("claims") != linux.get("claims")
        or local.get("measurement_rows") != 1680
        or linux.get("measurement_rows") != 1680
        or final.get("status") != "pass"
        or final.get("scientific_confirmation_complete") is not True
        or final.get("summary") != linux_summary
    ):
        raise SystemExit("refusing C23 cross-machine comparison: evidence mismatch")

    comparison = {
        method: {
            "windows_aggregate_speedup_over_exhaustive":
                local_summary["methods"][method]["aggregate_speedup_over_exhaustive"],
            "linux_aggregate_speedup_over_exhaustive":
                linux_summary["methods"][method]["aggregate_speedup_over_exhaustive"],
            "windows_aggregate_speedup_over_screened":
                local_summary["methods"][method]["aggregate_speedup_over_screened"],
            "linux_aggregate_speedup_over_screened":
                linux_summary["methods"][method]["aggregate_speedup_over_screened"],
            "windows_minimum_case_speedup_over_screened":
                local_summary["methods"][method]["minimum_case_speedup_over_screened"],
            "linux_minimum_case_speedup_over_screened":
                linux_summary["methods"][method]["minimum_case_speedup_over_screened"],
        }
        for method in methods
    }
    output = {
        "schema": "crse-c23-local-linux-comparison/v1",
        "status": "verified",
        "date": "2026-08-31",
        "corpus_or_methods_changed": False,
        "cases": 48,
        "methods": methods,
        "rounds_per_machine": 5,
        "measurement_rows_per_machine": 1680,
        "memory_rows_per_machine": 56,
        "semantic_or_artifact_mismatches": 0,
        "windows": {
            "best_fixed_method": local_summary["best_fixed_method"],
            "oracle_headroom_over_best_fixed":
                local_summary["oracle_headroom_over_best_fixed"],
            "screened_control_gate": local_summary["screened_control_gate"],
            "compiled_no_regret_gate": local_summary["compiled_no_regret_gate"],
        },
        "linux": {
            "best_fixed_method": linux_summary["best_fixed_method"],
            "oracle_headroom_over_best_fixed":
                linux_summary["oracle_headroom_over_best_fixed"],
            "screened_control_gate": linux_summary["screened_control_gate"],
            "compiled_no_regret_gate": linux_summary["compiled_no_regret_gate"],
            "estimated_compute_cost_usd": final["estimated_compute_cost_usd"],
            "owned_pod_absent_verified": final["owned_pod_absent_verified"],
            "controller_status": final["controller_status"],
        },
        "method_comparison": comparison,
        "conclusions": {
            "exact_transfer": True,
            "screened_cm_materially_beats_exhaustive_on_both_machines": (
                comparison["cm_screened"]["windows_aggregate_speedup_over_exhaustive"] >= 3.0
                and comparison["cm_screened"]["linux_aggregate_speedup_over_exhaustive"] >= 3.0
            ),
            "best_fixed_ranking_is_machine_stable":
                local_summary["best_fixed_method"] == linux_summary["best_fixed_method"],
            "packed_source_margin_over_screened_has_same_sign": (
                (comparison["source_packed_anf"]["windows_aggregate_speedup_over_screened"] >= 1)
                == (comparison["source_packed_anf"]["linux_aggregate_speedup_over_screened"] >= 1)
            ),
            "router_training_justified": False,
            "production_promotion": False,
        },
    }
    OUTPUT.write_bytes(json.dumps(output, indent=2, sort_keys=True, allow_nan=False).encode()
                       + b"\n")
    print(json.dumps({
        "status": output["status"],
        "windows_best": output["windows"]["best_fixed_method"],
        "linux_best": output["linux"]["best_fixed_method"],
        "windows_oracle_headroom": output["windows"]["oracle_headroom_over_best_fixed"],
        "linux_oracle_headroom": output["linux"]["oracle_headroom_over_best_fixed"],
        "exact_transfer": True,
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
