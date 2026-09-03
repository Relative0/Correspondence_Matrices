"""Adjudicate the verified Windows/MSVC and Linux/GCC C37-native executions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/recognition/c38_linux_confirmation"
WINDOWS = ROOT / "docs/recognition/runs/c37-native-exact-confirmation-windows-20260903-001"
RUNPOD = HERE / "runpod-c38-linux-execute-002"
LINUX = RUNPOD / "evidence/run-output/c38-c37-native-linux-gcc-20260903-001"
FINAL = HERE / "RUNPOD_C38_FINAL_VERIFICATION_20260903.json"
CONTROLLER_SUMMARY = RUNPOD / "C38-CROSS-MACHINE-SUMMARY.json"
OUTPUT = HERE / "C38_CROSS_MACHINE_ADJUDICATION_20260903.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execution(environment: str, path: Path) -> dict[str, Any]:
    result = load(path / "results.json")
    single = result["single_root"]
    multi = result["multi_root"]
    case_speedups = single["case_median_speedups_over_python_r2"]
    slowest_case = min(case_speedups, key=case_speedups.get)
    return {
        "environment": environment,
        "results_sha256": sha256(path / "results.json"),
        "independent_verification_sha256": sha256(
            path / "independent_verification.json"
        ),
        "all_predeclared_gates_passed": result["decision"][
            "all_predeclared_gates_passed"
        ],
        "single_root": {
            "aggregate_speedup": single["native_speedup_over_python_r2"],
            "minimum_case_speedup": single["minimum_case_speedup_over_python_r2"],
            "slowest_case": slowest_case,
            "slowest_case_speedup": case_speedups[slowest_case],
            "minimum_width_speedup": single["minimum_width_speedup_over_python_r2"],
            "p95_session_speedup": single["p95_session_speedup_over_python_r2"],
            "failed_gates": [
                key for key, passed in single["gates"].items() if not passed
            ],
        },
        "multi_root": {
            "aggregate_speedup": multi["union_speedup_over_separate"],
            "minimum_workload_speedup": multi["minimum_workload_speedup"],
            "p95_session_speedup": multi["p95_session_speedup"],
            "failed_gates": [
                key for key, passed in multi["gates"].items() if not passed
            ],
        },
        "training": result["decision"]["training"],
        "policy_refit": result["decision"]["policy_refit"],
        "gate_refit": result["decision"]["gate_refit"],
        "production_promotion": result["decision"]["production_promotion"],
    }


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("refusing to overwrite C38 cross-machine adjudication")
    final = load(FINAL)
    controller_summary = load(CONTROLLER_SUMMARY)
    windows_verification = load(WINDOWS / "independent_verification.json")
    linux_verification = load(LINUX / "c38_independent_verification.json")
    if (
        final.get("status") != "pass"
        or final.get("exactness_verified") is not True
        or final.get("post_retrieval_verification_byte_identical") is not True
        or final.get("owned_pod_absent_verified") is not True
        or final.get("semantic_or_artifact_mismatches") != 0
        or windows_verification.get("status") != "verified"
        or linux_verification.get("status") != "verified"
        or controller_summary.get("exactness_verified_on_both") is not True
        or controller_summary.get("os_and_compiler_families") != 2
        or controller_summary.get("status")
        != "exact_cross_machine_replication_complete_performance_not_confirmed"
    ):
        raise RuntimeError("C38 evidence is incomplete or not admissible")

    executions = [execution("windows_msvc", WINDOWS), execution("linux_gcc", LINUX)]
    if (
        any(row["training"] is not False for row in executions)
        or any(row["policy_refit"] is not False for row in executions)
        or any(row["gate_refit"] is not False for row in executions)
        or any(row["production_promotion"] is not False for row in executions)
    ):
        raise RuntimeError("C38 execution decision boundary changed")
    floors = {
        "single_root_aggregate_speedup": min(
            row["single_root"]["aggregate_speedup"] for row in executions
        ),
        "single_root_minimum_case_speedup": min(
            row["single_root"]["minimum_case_speedup"] for row in executions
        ),
        "single_root_minimum_width_speedup": min(
            row["single_root"]["minimum_width_speedup"] for row in executions
        ),
        "single_root_p95_session_speedup": min(
            row["single_root"]["p95_session_speedup"] for row in executions
        ),
        "multi_root_aggregate_speedup": min(
            row["multi_root"]["aggregate_speedup"] for row in executions
        ),
        "multi_root_minimum_workload_speedup": min(
            row["multi_root"]["minimum_workload_speedup"] for row in executions
        ),
        "multi_root_p95_session_speedup": min(
            row["multi_root"]["p95_session_speedup"] for row in executions
        ),
    }
    performance_gate_all_executions = all(
        row["all_predeclared_gates_passed"] for row in executions
    )
    adjudication = {
        "schema": "crse-c38-c37-native-cross-machine-adjudication/v1",
        "status": "exact_replication_passed_per_case_performance_not_confirmed",
        "replication_admissible": True,
        "exactness_verified_on_both": True,
        "execution_count": 2,
        "physical_machine_count": 2,
        "os_and_compiler_families": 2,
        "executions": executions,
        "cross_machine_observed_floors": floors,
        "aggregate_single_root_speedup_at_least_1_10_on_both": (
            floors["single_root_aggregate_speedup"] >= 1.10
        ),
        "aggregate_multi_root_speedup_at_least_1_10_on_both": (
            floors["multi_root_aggregate_speedup"] >= 1.10
        ),
        "all_predeclared_performance_gates_passed_on_both": (
            performance_gate_all_executions
        ),
        "failed_cross_machine_gate": "single_root_minimum_case_speedup_at_least_0_95",
        "guarded_opt_in_backend_retained": True,
        "guarded_retention_basis": (
            "Exactness transferred to Linux/GCC and aggregate performance remained "
            "positive, but the existing fail-closed Python R2 fallback remains mandatory."
        ),
        "unqualified_per_case_performance_claim": False,
        "prospective_rerun_authorized": False,
        "selector_training_justified": False,
        "training": False,
        "policy_refit": False,
        "gate_refit": False,
        "shadow_promotion": False,
        "production_promotion": False,
        "final_verification_sha256": sha256(FINAL),
        "controller_summary_sha256": sha256(CONTROLLER_SUMMARY),
        "limitations": [
            "Two machines and compiler families establish portability evidence, not broad hardware coverage.",
            "The Linux width-11 adder-tree case is retained at 0.839984x; the frozen 0.95x individual-case gate failed.",
            "Aggregate q64 speedups do not establish q1, q4, or q16 break-even behavior.",
            "C38 does not authorize a public benchmark update or production-default change.",
        ],
    }
    with OUTPUT.open("xb") as stream:
        stream.write(
            json.dumps(adjudication, indent=2, sort_keys=True, allow_nan=False).encode(
                "utf-8"
            )
            + b"\n"
        )
    print(
        json.dumps(
            {
                "status": adjudication["status"],
                "replication_admissible": adjudication["replication_admissible"],
                "exactness_verified_on_both": adjudication[
                    "exactness_verified_on_both"
                ],
                "all_performance_gates_on_both": adjudication[
                    "all_predeclared_performance_gates_passed_on_both"
                ],
                "guarded_opt_in_backend_retained": adjudication[
                    "guarded_opt_in_backend_retained"
                ],
                "production_promotion": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
