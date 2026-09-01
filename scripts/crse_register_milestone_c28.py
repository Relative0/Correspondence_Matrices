"""Register independently verified C28 cross-machine profitability evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c28-cross-machine-profitability-adjudication-20260901-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C28_CROSS_MACHINE_PROFITABILITY_ADJUDICATION_2026_09_01.md"
MACHINE = "learning_milestone_c28_cross_machine_profitability_adjudication_results.json"
C27_MACHINE = "learning_milestone_c27_support_aware_fresh_confirmation_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False,
    ).encode("utf-8") + b"\n")


def upsert(container: dict, scope: str) -> None:
    value = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    matches = [row for row in container["results"] if row.get("report") == REPORT]
    if len(matches) > 1:
        raise RuntimeError("duplicate C28 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    manifest = load(RUN / "input_manifest.json")
    q8 = result["by_query_count"]["8"]
    q8_point = q8["cross_execution_point_floor"]
    q8_lower = q8["cross_execution_paired_bootstrap_95_lower_floor"]
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("policy_refit") is not False
        or result.get("training") is not False
        or result.get("timings_rerun") is not False
        or result.get("fresh_c27_policy_unchanged") is not True
        or result.get("execution_count") != 5
        or result.get("physical_machine_count") != 2
        or result.get("measurement_batches_checked") != 3600
        or result.get("timed_queries_checked") != 37800
        or result.get("memory_batches_checked") != 120
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("point_admissible_query_counts") != [8]
        or result.get("uncertainty_admissible_query_counts") != []
        or result.get("point_monotonic_suffix_start") is not None
        or result.get("uncertainty_monotonic_suffix_start") is not None
        or result.get("shadow_promotion") is not False
        or result.get("production_promotion") is not False
        or result.get("decision")
        != "refuse_shadow_promotion_no_uncertainty_safe_monotonic_suffix"
        or q8.get("point_gate_all_executions") is not True
        or q8.get("uncertainty_gate_all_executions") is not False
        or verification.get("status") != "verified"
        or verification.get("input_files_checked") != 35
        or verification.get("measurement_batches_checked") != 3600
        or verification.get("timed_queries_checked") != 37800
        or verification.get("memory_batches_checked") != 120
        or verification.get("paired_resample_statistics_recomputed") != 93750
        or verification.get("semantic_or_artifact_mismatches") != 0
        or verification.get("shadow_promotion") is not False
        or verification.get("production_promotion") is not False
        or verification.get("results_sha256") != sha256(RUN / "results.json")
        or verification.get("input_manifest_sha256") != sha256(RUN / "input_manifest.json")
        or manifest.get("source_execution_count") != 5
        or manifest.get("physical_machine_count") != 2
        or manifest.get("policy_refit") is not False
        or manifest.get("training") is not False
        or manifest.get("timings_rerun") is not False
    ):
        raise RuntimeError("refusing C28 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c28-cross-machine-adjudication-summary/v1",
        "date": "2026-09-01",
        "status": "verified_negative_no_uncertainty_safe_profitability_region",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "source_milestone": "C27",
        "execution_count": 5,
        "physical_machine_count": 2,
        "measurement_batches_checked": 3600,
        "timed_queries_checked": 37800,
        "memory_batches_checked": 120,
        "paired_round_resamples_per_execution_query": 3125,
        "paired_resample_statistics_recomputed": 93750,
        "point_admissible_query_counts": [8],
        "uncertainty_admissible_query_counts": [],
        "point_monotonic_suffix_start": None,
        "uncertainty_monotonic_suffix_start": None,
        "q8_cross_execution_point_floor": q8_point,
        "q8_cross_execution_paired_bootstrap_95_lower_floor": q8_lower,
        "by_query_count": result["by_query_count"],
        "decision": result["decision"],
        "semantic_or_artifact_mismatches": 0,
        "policy_refit": False,
        "training": False,
        "timings_rerun": False,
        "shadow_promotion": False,
        "production_promotion": False,
        "verification": {
            "path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace(
                "\\", "/"),
            **verification,
        },
        "interpretation": (
            "Only q8 passed the point-estimate gate on every execution, with a 1.024x "
            "aggregate and 0.950x minimum-width cross-execution floor. Its conservative "
            "paired-round lower floors were 0.928x and 0.597x, so it did not pass the "
            "uncertainty gate. No query count was uncertainty-admissible and no measured "
            "suffix supported a q>=k shadow rule. Exact fallback remains mandatory."
        ),
    }
    write(DOCS / MACHINE, machine)

    scope = (
        "C28 evaluated five frozen C27 executions across two physical machines without "
        "training, refitting, or rerunning timings. All 37,800 queries remained exact. "
        "Only q8 passed every point gate (1.024x aggregate / 0.950x minimum-width floor), "
        "but its paired-round lower floors were 0.928x / 0.597x. No uncertainty-safe "
        "query count or monotonic suffix remained, so shadow and production promotion "
        "were refused."
    )
    next_experiment = (
        "Freeze C29 variance localization before new timing: interleave candidate and "
        "screened control order, retain component timings by width, isolate the q8 "
        "round/width instability, and repeat only an unchanged justified optimization "
        "on at least two physical machines."
    )
    register = load(REGISTER)
    track_ids = [row["id"] for row in register["tracks"]]
    application_names = [row["name"] for row in register["applications"]]
    if len(track_ids) != 18 or len(set(track_ids)) != 18 or len(application_names) != 8:
        raise RuntimeError("track/application inventory changed before C28 registration")
    registrations = 0
    for collection in (register["tracks"], register["applications"]):
        for row in collection:
            has_c27 = any(item.get("machine_summary") == C27_MACHINE
                          for item in row.get("results", []))
            if not has_c27:
                continue
            upsert(row, scope)
            registrations += 1
            if "status_reason" in row:
                row["status_reason"] = scope
            if "next_experiment" in row:
                row["next_experiment"] = next_experiment
    if registrations != 9:
        raise RuntimeError(f"expected nine C28 registrations, observed {registrations}")
    register["milestones"]["F"] = (
        "C28 evaluates five frozen C27 executions across two physical machines with no "
        "refit; q8 alone passes every point gate, no query count passes conservative "
        "paired-round uncertainty, and exact fallback remains mandatory"
    )
    register["updated"] = "2026-09-01"
    if (
        [row["id"] for row in register["tracks"]] != track_ids
        or [row["name"] for row in register["applications"]] != application_names
    ):
        raise RuntimeError("C28 registration changed track/application identity or order")
    write(REGISTER, register)
    print(json.dumps({
        "status": "registered",
        "tracks": len(track_ids),
        "applications": len(application_names),
        "c28_registrations": registrations,
        "decision": result["decision"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
