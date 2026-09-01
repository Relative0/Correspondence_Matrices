"""Register independently verified C26 fused-context evidence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c26-fused-resident-windows-20260831-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C26_FUSED_VERIFIED_CONTEXT_2026_08_31.md"
MACHINE = "learning_milestone_c26_fused_verified_context_results.json"


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
        raise SystemExit("duplicate C26 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    controls = load(RUN / "functional_controls.json")
    summary = result["summary"]
    q2 = summary["by_query_count"]["2"]["methods"]["fused_c22_advice_on"]
    q32 = summary["by_query_count"]["32"]["methods"]["fused_c22_advice_on"]
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("measurement_batches") != 720
        or result.get("timed_queries") != 7560
        or result.get("memory_measurement_batches") != 24
        or result.get("fallback_controls") != 48
        or result.get("refusal_controls") != 9
        or result.get("context_tamper_controls") != 4
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("claims", {}).get("unchanged_c25_direct_controls") is not True
        or result.get("claims", {}).get("single_expression_evaluation_per_fused_query") is not True
        or result.get("claims", {}).get("hash_bound_verified_context") is not True
        or result.get("claims", {}).get("production_promotion") is not False
        or summary.get("exactness_gate") is not True
        or summary.get("functional_control_gate") is not True
        or summary.get("fused_advice_on_break_even_query_count") is not None
        or summary.get("fused_promotion_gate") is not False
        or controls.get("all_passed") is not True
        or verification.get("status") != "verified"
        or verification.get("fallback_controls_replayed") != 48
        or verification.get("refusal_controls_checked") != 9
        or verification.get("context_tamper_controls_checked") != 4
        or verification.get("measurement_batches_checked") != 720
        or verification.get("timed_query_records_checked") != 7560
        or verification.get("fused_contexts_semantically_replayed") != 2520
        or verification.get("fused_cache_records_checked") != 2520
        or verification.get("memory_batches_checked") != 24
        or verification.get("summary_recomputed") is not True
        or verification.get("semantic_or_artifact_mismatches") != 0
        or verification.get("production_promotion") is not False
    ):
        raise SystemExit("refusing C26 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c26-fused-verified-context-summary/v1",
        "date": "2026-08-31",
        "status": "fused_exact_verified_aggregate_wins_no_regret_floor_failed",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "dataset": result["dataset"],
        "methods": list(summary["by_query_count"]["1"]["methods"]),
        "measurement_batches": result["measurement_batches"],
        "timed_queries": result["timed_queries"],
        "memory_measurement_batches": result["memory_measurement_batches"],
        "fallback_controls": result["fallback_controls"],
        "refusal_controls": result["refusal_controls"],
        "context_tamper_controls": result["context_tamper_controls"],
        "summary": summary,
        "verification": {
            "path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace("\\", "/"),
            **verification,
        },
        "semantic_or_artifact_mismatches": 0,
        "policy_refit": False,
        "fresh_confirmation": False,
        "linux_replication": {
            "status": "not_warranted_no_regret_floor_failed",
            "used": False,
            "cost_usd": 0.0,
        },
        "production_promotion": False,
        "interpretation": (
            "Single-evaluation hash-bound fusion made C22 advice-on the fastest fixed method at 1, "
            "2, and 4 queries. At two queries it reached "
            f"{q2['aggregate_speedup_over_direct_screened']:.3f}x direct screened overall, but the "
            f"slowest support width reached only {q2['minimum_width_speedup_over_direct_screened']:.3f}x. "
            "At 32 queries the minimum improved to "
            f"{q32['minimum_width_speedup_over_direct_screened']:.3f}x, still below the frozen 0.90x "
            "no-regret floor. Tiny-support packed-context overhead is the next target."
        ),
    }
    write(DOCS / MACHINE, machine)

    data = load(REGISTER)
    if (
        [row["id"] for row in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
        or len(data.get("applications", [])) != 8
    ):
        raise SystemExit("refusing C26 update: 18-track or 8-application shape changed")
    tracks = {row["id"]: row for row in data["tracks"]}
    scope = (
        "C26 executed 7,560 timed exact queries with one evaluation and hash-bound context per fused "
        "query. Fused advice-on won aggregate timing at four query counts and was the fastest fixed "
        "method at 1, 2, and 4, but the support-width no-regret floor remained below 0.90x."
    )
    for track_id in ("R01", "R02", "R06", "R11", "R13", "R16", "R17", "R18"):
        upsert(tracks[track_id], scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = scope
    tracks["R01"]["next_experiment"] = (
        "Freeze C27 support-aware truth-only tiny-support bypass, then confirm on a new corpus."
    )
    tracks["R02"]["next_experiment"] = (
        "Retain per-width immutable plans; do not cache request contexts across changing expressions."
    )
    tracks["R06"]["next_experiment"] = (
        "Confirm the support-aware rule on previously unused generators before Linux timing."
    )
    tracks["R11"]["next_experiment"] = (
        "Use packed fused context for larger supports and truth-only screened context for tiny supports."
    )
    tracks["R13"]["next_experiment"] = (
        "Use a transparent support threshold rather than training a router on the C26 development set."
    )
    tracks["R16"]["next_experiment"] = (
        "Compile the support rule into the fused session without weakening final reconstruction."
    )
    tracks["R17"]["next_experiment"] = (
        "Repeat all expression, truth, width, context, policy, limit, and close refusal controls."
    )
    tracks["R18"]["next_experiment"] = (
        "Retain the unchanged C25 direct controls and add forced tiny/large support path controls."
    )
    hardware = next(
        item for item in data["applications"] if item["name"] == "Hardware verification/design")
    upsert(hardware, scope)
    data["milestones"]["F"] = (
        "C26 verifies single-evaluation hash-bound fusion across 7,560 exact queries and obtains "
        "aggregate wins, while tiny-support overhead still prevents a no-regret promotion"
    )
    data["updated"] = "2026-08-31"
    write(REGISTER, data)
    print(json.dumps({
        "tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "updated_tracks": ["R01", "R02", "R06", "R11", "R13", "R16", "R17", "R18"],
        "milestone": "C26/F6", "fused_promotion_gate": False,
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
