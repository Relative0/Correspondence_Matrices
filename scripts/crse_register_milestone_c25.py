"""Register independently verified C25 resident-session evidence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c25-c22-resident-windows-20260831-002"
FAILED = DOCS / "runs/c25-c22-resident-windows-20260831-001/FAILED_ATTEMPT.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C25_RESIDENT_C22_SESSION_2026_08_31.md"
MACHINE = "learning_milestone_c25_resident_c22_session_results.json"


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
        raise SystemExit("duplicate C25 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    controls = load(RUN / "functional_controls.json")
    failed = load(FAILED)
    summary = result["summary"]
    q32 = summary["by_query_count"]["32"]["methods"]["resident_c22_advice_on"]
    if (
        not (DOCS / REPORT).is_file()
        or failed.get("status") != "failed_before_timing"
        or failed.get("measurement_batches") != 0
        or failed.get("runpod_used") is not False
        or result.get("status") != "complete"
        or result.get("measurement_batches") != 720
        or result.get("timed_queries") != 7560
        or result.get("memory_measurement_batches") != 24
        or result.get("fallback_controls") != 48
        or result.get("refusal_controls") != 5
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("claims", {}).get("resident_policy_and_compiled_state_reused") is not True
        or result.get("claims", {}).get("every_query_exactly_verified") is not True
        or result.get("claims", {}).get("production_promotion") is not False
        or summary.get("exactness_gate") is not True
        or summary.get("functional_control_gate") is not True
        or summary.get("advice_on_break_even_query_count") is not None
        or summary.get("resident_promotion_gate") is not False
        or controls.get("all_passed") is not True
        or verification.get("status") != "verified"
        or verification.get("fallback_controls_replayed") != 48
        or verification.get("refusal_controls_checked") != 5
        or verification.get("measurement_batches_checked") != 720
        or verification.get("timed_query_records_checked") != 7560
        or verification.get("resident_cache_records_checked") != 2520
        or verification.get("memory_batches_checked") != 24
        or verification.get("summary_recomputed") is not True
        or verification.get("semantic_or_artifact_mismatches") != 0
        or verification.get("production_promotion") is not False
    ):
        raise SystemExit("refusing C25 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c25-resident-c22-session-summary/v1",
        "date": "2026-08-31",
        "status": "resident_exact_verified_no_break_even_through_32_queries",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "failed_attempt": {
            "path": str(FAILED.relative_to(ROOT)).replace("\\", "/"),
            **failed,
        },
        "dataset": result["dataset"],
        "methods": list(summary["by_query_count"]["1"]["methods"]),
        "measurement_batches": result["measurement_batches"],
        "timed_queries": result["timed_queries"],
        "memory_measurement_batches": result["memory_measurement_batches"],
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
            "Resident immutable-policy and compiled-state reuse passed every exactness, fallback, "
            "cache, and refusal invariant, but no break-even occurred through 32 queries. At 32 "
            f"queries advice-on reached {q32['aggregate_speedup_over_direct_screened']:.3f}x direct "
            f"screened overall and {q32['minimum_width_speedup_over_direct_screened']:.3f}x on the "
            "slowest support width. Per-query duplicated verification, not session setup, is now the "
            "strongest optimization target."
        ),
    }
    write(DOCS / MACHINE, machine)

    data = load(REGISTER)
    if (
        [row["id"] for row in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
        or len(data.get("applications", [])) != 8
    ):
        raise SystemExit("refusing C25 update: 18-track or 8-application shape changed")
    tracks = {row["id"]: row for row in data["tracks"]}
    scope = (
        "C25 executed 720 resident batches and 7,560 timed exact queries through 32 queries per "
        "session. All exactness, cache, fallback, and refusal controls passed, but C22 advice-on "
        "never reached direct screened parity and resident promotion failed."
    )
    for track_id in ("R01", "R02", "R06", "R11", "R13", "R16", "R17", "R18"):
        upsert(tracks[track_id], scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = scope
    tracks["R01"]["next_experiment"] = (
        "Implement C26 hash-bound verified request contexts and rerun the resident schedule."
    )
    tracks["R02"]["next_experiment"] = (
        "Cache only immutable decoded/truth identity state with explicit digest and lifetime bounds."
    )
    tracks["R06"]["next_experiment"] = (
        "Attribute per-query duplicated evaluation, execution verification, and delivery replay costs."
    )
    tracks["R11"]["next_experiment"] = (
        "Feed one verified packed source representation into exact screened completion without reparse."
    )
    tracks["R13"]["next_experiment"] = (
        "Keep router training disabled; repeated-query evidence still has no profitable routing margin."
    )
    tracks["R16"]["next_experiment"] = (
        "Fuse resident validation and exact delivery while retaining one independent artifact replay."
    )
    tracks["R17"]["next_experiment"] = (
        "Prove context digests fail closed for expression, width, truth, policy, and session mismatches."
    )
    tracks["R18"]["next_experiment"] = (
        "Rerun unchanged resident exhaustive, screened, compiled-screened, and source-packed controls."
    )
    hardware = next(
        item for item in data["applications"] if item["name"] == "Hardware verification/design")
    upsert(hardware, scope)
    data["milestones"]["F"] = (
        "C25 verifies exact resident reuse across 7,560 timed queries but finds no profitability "
        "break-even through 32 queries; duplicated per-query verification is the next target"
    )
    data["updated"] = "2026-08-31"
    write(REGISTER, data)
    print(json.dumps({
        "tracks": len(data["tracks"]),
        "applications": len(data["applications"]),
        "updated_tracks": ["R01", "R02", "R06", "R11", "R13", "R16", "R17", "R18"],
        "milestone": "C25/F5",
        "resident_promotion_gate": False,
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
