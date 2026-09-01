"""Register independently verified C24 C22-boundary evidence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c24-c22-boundary-windows-20260831-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C24_C22_BOUNDARY_2026_08_31.md"
MACHINE = "learning_milestone_c24_c22_boundary_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
    ).encode("utf-8") + b"\n")


def upsert(container: dict, scope: str) -> None:
    value = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    matches = [row for row in container["results"] if row.get("report") == REPORT]
    if len(matches) > 1:
        raise SystemExit("duplicate C24 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    controls = load(RUN / "functional_controls.json")
    summary = result["summary"]
    advice = summary["methods"]["c22_advice_on"]
    comparisons = summary["wrapper_comparisons"]
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("measurement_rows") != 3456
        or result.get("memory_measurement_rows") != 64
        or result.get("fallback_controls") != 48
        or result.get("refusal_controls") != 5
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("claims", {}).get("unchanged_c22_policy") is not True
        or result.get("claims", {}).get("fallback_and_refusal_controls_passed") is not True
        or result.get("claims", {}).get("production_promotion") is not False
        or summary.get("exactness_gate") is not True
        or summary.get("functional_control_gate") is not True
        or summary.get("local_promotion_gate") is not False
        or controls.get("all_passed") is not True
        or verification.get("status") != "verified"
        or verification.get("functional_cases_replayed") != 48
        or verification.get("fallback_controls_replayed") != 48
        or verification.get("refusal_controls_checked") != 5
        or verification.get("measurement_rows_checked") != 3456
        or verification.get("memory_rows_checked") != 64
        or verification.get("summary_recomputed") is not True
        or verification.get("semantic_or_artifact_mismatches") != 0
        or verification.get("production_promotion") is not False
    ):
        raise SystemExit("refusing C24 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c24-c22-boundary-summary/v1",
        "date": "2026-08-31",
        "status": "retrospective_boundary_exact_verified_local_promotion_gate_failed",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "dataset": result["dataset"],
        "methods": list(summary["methods"]),
        "measurement_rows": result["measurement_rows"],
        "memory_measurement_rows": result["memory_measurement_rows"],
        "fallback_controls": result["fallback_controls"],
        "refusal_controls": result["refusal_controls"],
        "summary": summary,
        "verification": {
            "path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace("\\", "/"),
            **verification,
        },
        "semantic_or_artifact_mismatches": 0,
        "policy_refit": False,
        "fresh_confirmation": False,
        "linux_replication": {
            "status": "not_warranted_local_gate_failed",
            "used": False,
            "cost_usd": 0.0,
        },
        "production_promotion": False,
        "interpretation": (
            "The frozen C22 boundary remained exact and fail-closed, including 48 forced fallbacks "
            "and five refusal controls. Its advice-on path reached "
            f"{advice['aggregate_speedup_over_direct_screened']:.3f}x direct screened overall and "
            f"{advice['minimum_case_speedup_over_direct_screened']:.3f}x on the slowest case. "
            "The boundary retained only "
            f"{comparisons['c22_advice_on_speedup_over_direct_source_packed']:.3f}x of direct "
            "source-packed throughput, so fresh single-query promotion failed."
        ),
    }
    write(DOCS / MACHINE, machine)

    data = load(REGISTER)
    if (
        [row["id"] for row in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
        or len(data.get("applications", [])) != 8
    ):
        raise SystemExit("refusing C24 update: 18-track or 8-application shape changed")
    tracks = {row["id"]: row for row in data["tracks"]}
    scope = (
        "C24 charged the frozen C22 dispatcher end to end on all 48 sealed C23 cases. Exactness, "
        "48 forced fallbacks, and five fail-closed controls passed; advice-on reached 0.833x direct "
        "screened overall and the local promotion gate failed."
    )
    for track_id in ("R01", "R02", "R06", "R11", "R13", "R16", "R17", "R18"):
        upsert(tracks[track_id], scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = scope
    tracks["R01"]["next_experiment"] = (
        "Measure a resident-session C25 contract and report exact break-even query counts."
    )
    tracks["R02"]["next_experiment"] = (
        "Reuse immutable validated policy and compiled portfolio state within a bounded session."
    )
    tracks["R06"]["next_experiment"] = (
        "Compare resident boundary and direct controls over query counts 1, 2, 4, 8, 16, and 32."
    )
    tracks["R11"]["next_experiment"] = (
        "Keep source-packed exact completion but amortize policy load and compilation only."
    )
    tracks["R13"]["next_experiment"] = (
        "Do not train a new router: C24 deployable oracle headroom is only 1.017x before routing cost."
    )
    tracks["R16"]["next_experiment"] = (
        "Implement fail-closed resident sessions with per-query validation and exact delivery checks."
    )
    tracks["R17"]["next_experiment"] = (
        "Repeat malformed, unsupported-width, and policy-identity refusal controls at session entry."
    )
    tracks["R18"]["next_experiment"] = (
        "Retain resident exhaustive, screened, compiled-screened, and source-packed controls."
    )
    hardware = next(
        item for item in data["applications"] if item["name"] == "Hardware verification/design")
    upsert(hardware, scope)
    data["milestones"]["F"] = (
        "C24 verifies that the frozen C22 boundary is exact and fail-closed but not profitable for "
        "fresh single-query use; resident-session amortization is the next bounded lifecycle test"
    )
    data["updated"] = "2026-08-31"
    write(REGISTER, data)
    print(json.dumps({
        "tracks": len(data["tracks"]),
        "applications": len(data["applications"]),
        "updated_tracks": ["R01", "R02", "R06", "R11", "R13", "R16", "R17", "R18"],
        "milestone": "C24/F4",
        "local_promotion_gate": False,
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
