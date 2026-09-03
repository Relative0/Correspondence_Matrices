"""Register independently verified C35 natural repeated-query evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c35-natural-repeated-windows-20260901-002"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C35_NATURAL_REPEATED_QUERY_2026_09_01.md"
MACHINE = "learning_milestone_c35_natural_repeated_query_results.json"
TRACK_IDS = frozenset({"R01", "R02", "R06", "R07", "R10", "R11", "R13", "R16", "R17", "R18"})
APPLICATION = "Hardware verification/design"


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
        raise RuntimeError("duplicate C35 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    controls = load(RUN / "functional_controls.json")
    spec = load(RUN / "run_spec.json")
    summary = result.get("summary", {})
    at64 = summary.get("checkpoints", {}).get("64", {})
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("dataset", {}).get("cases") != 8
        or result.get("dataset", {}).get("queries_per_case") != 64
        or result.get("dataset", {}).get("fresh_confirmation") is not False
        or result.get("measurement_rows") != 576
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("functional_controls_passed") is not True
        or summary.get("timed_queries") != 36_864
        or at64.get("best_fixed_method") != "flattened_cse_restrict"
        or not (1.20 < at64.get("cm_speedup_over_direct_ast", 0) < 1.25)
        or not (0.90 < at64.get("cm_speedup_over_flattened_cse", 0) < 0.95)
        or at64.get("cm_case_win_fraction_vs_flattened_cse") != 0.25
        or summary.get("cm_break_even_query_count_vs_direct_ast") != 64
        or summary.get("cm_break_even_query_count_vs_flattened_cse") is not None
        or summary.get("cm_promotion_gate") is not False
        or result.get("decision", {}).get("training_performed") is not False
        or result.get("decision", {}).get("policy_refit") is not False
        or result.get("decision", {}).get("production_promotion") is not False
        or result.get("runpod") != {"used": False, "cost_usd": 0.0}
        or controls.get("all_passed") is not True
        or controls.get("production_write") is not False
        or controls.get("production_promotion") is not False
        or verification.get("status") != "verified"
        or verification.get("dataset_cases_replayed") != 8
        or verification.get("queries_replayed") != 512
        or verification.get("measurement_rows_checked") != 576
        or verification.get("timed_queries_checked") != 36_864
        or any(verification.get(key) != 0 for key in
               ("semantic_mismatches", "trace_mismatches", "oracle_mismatches",
                "measurement_mismatches", "summary_mismatches"))
        or verification.get("results_sha256") != sha256(RUN / "results.json")
        or verification.get("manifest_sha256") != sha256(RUN / "manifest.json")
        or spec.get("training") is not False
        or spec.get("policy_refit") is not False
        or spec.get("production_promotion") is not False
    ):
        raise RuntimeError("refusing C35 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c35-natural-repeated-query-summary/v1",
        "date": "2026-09-01", "status": "verified_local_cm_gate_failed_no_promotion",
        "report": REPORT, "run": RUN.relative_to(ROOT).as_posix(), "source_milestone": "C34",
        "dataset": result["dataset"], "measurement_rows": 576, "timed_queries": 36_864,
        "semantic_or_artifact_mismatches": 0, "summary": summary,
        "controls": controls, "training": False, "policy_refit": False,
        "fresh_confirmation": False, "source_dataset_reused": True,
        "production_write": False, "production_promotion": False,
        "runpod": {"used": False, "cost_usd": 0.0},
        "verification": {
            "path": (RUN / "independent_verification.json").relative_to(ROOT).as_posix(),
            **verification,
        },
        "interpretation": (
            "At 64 exact partial-context queries CM IR is 1.2245x faster than direct AST "
            "but only 0.9303x flattened structural CSE and wins that pair on 2/8 cases. "
            "The exact lifecycle gate fails; no second-machine or production promotion follows."
        ),
    }
    write(DOCS / MACHINE, machine)

    scope = (
        "C35 measures 576 resident sessions and 36,864 exact partial-context query deliveries "
        "on eight reused natural Yosys expressions at support 3-10. CM IR reaches 1.2245x over "
        "direct AST at q64 but remains 0.9303x flattened CSE and wins that pair on only 2/8 "
        "cases. Independent replay finds zero mismatches; the CM gate fails with no training."
    )
    next_experiment = (
        "C36 should separate wider fresh natural restriction/count/SAT/witness workloads from "
        "persistence/reload and related-version traces. Add efficient packed projection, native "
        "CUDD when available, and changed-cone accounting before any learned selection."
    )
    register = load(REGISTER)
    track_ids = [row["id"] for row in register["tracks"]]
    application_names = [row["name"] for row in register["applications"]]
    if len(track_ids) != 18 or len(set(track_ids)) != 18 or len(application_names) != 8:
        raise RuntimeError("track/application inventory changed before C35 registration")
    registrations = 0
    for row in register["tracks"]:
        if row["id"] not in TRACK_IDS:
            continue
        upsert(row, scope)
        registrations += 1
        row["status_reason"] = scope
        row["next_experiment"] = next_experiment
    for row in register["applications"]:
        if row["name"] != APPLICATION:
            continue
        upsert(row, scope)
        registrations += 1
    if registrations != 11:
        raise RuntimeError(f"expected eleven C35 registrations, observed {registrations}")
    register["milestones"]["F"] = (
        "C35 completes the first natural repeated-query lifecycle adjudication: CM IR "
        "amortizes past direct AST at q64 but remains behind flattened CSE, so the frozen CM "
        "promotion gate fails and work moves to wider fresh and persistence/version lifecycles"
    )
    register["updated"] = "2026-09-01"
    if ([row["id"] for row in register["tracks"]] != track_ids
            or [row["name"] for row in register["applications"]] != application_names):
        raise RuntimeError("C35 registration changed track/application identity or order")
    write(REGISTER, register)
    print(json.dumps({
        "status": "registered", "tracks": len(track_ids),
        "applications": len(application_names), "c35_registrations": registrations,
        "measurement_rows": 576, "timed_queries": 36_864,
        "semantic_or_artifact_mismatches": 0, "cm_promotion_gate": False,
        "training": False, "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
