"""Register independently verified C36 wider-natural repeated-query evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c36-wide-repeated-windows-20260901-003"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C36_WIDE_NATURAL_REPEATED_QUERY_2026_09_01.md"
MACHINE = "learning_milestone_c36_wide_natural_repeated_query_results.json"
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
        raise RuntimeError("duplicate C36 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    controls = load(RUN / "functional_controls.json")
    probes = load(RUN / "external_functional_probes.json")
    spec = load(RUN / "run_spec.json")
    summary = result.get("summary", {})
    at64 = summary.get("checkpoints", {}).get("64", {})
    routing = summary.get("routing_headroom", {})
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("dataset", {}).get("cases") != 18
        or result.get("dataset", {}).get("cases_per_width") != 3
        or result.get("dataset", {}).get("widths") != list(range(11, 17))
        or result.get("measurement_rows") != 576
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("functional_controls_passed") is not True
        or result.get("external_functional_probes_passed") is not True
        or summary.get("timed_queries") != 36_864
        or at64.get("best_fixed_method") != "flattened_cse_words"
        or not (0.85 < at64.get("cm_speedup_over_flattened_cse", 0) < 0.95)
        or not (5.0 < at64.get("cm_speedup_over_direct_ast", 0) < 5.7)
        or not (0.90 < at64.get("cm_speedup_over_compiled_truth_projection", 0) < 0.98)
        or at64.get("cm_case_win_fraction_vs_flattened_cse") != 0.0
        or summary.get("cm_break_even_query_count_vs_flattened_cse") is not None
        or summary.get("cm_promotion_gate") is not False
        or routing.get("exploratory_headroom_gate") is not True
        or not (1.25 < routing.get("family_rule_budget_adjusted_speedup", 0) < 1.35)
        or routing.get("selection_is_post_hoc") is not True
        or routing.get("training_performed") is not False
        or routing.get("promotion_permitted") is not False
        or result.get("decision", {}).get("training_performed") is not False
        or result.get("decision", {}).get("policy_refit") is not False
        or result.get("decision", {}).get("production_promotion") is not False
        or result.get("runpod") != {"used": False, "cost_usd": 0.0}
        or controls.get("all_passed") is not True
        or controls.get("production_write") is not False
        or controls.get("production_promotion") is not False
        or probes.get("status") != "passed"
        or verification.get("status") != "verified"
        or verification.get("dataset_cases_replayed") != 18
        or verification.get("queries_replayed") != 1_152
        or verification.get("measurement_rows_checked") != 576
        or verification.get("timed_queries_checked") != 36_864
        or any(verification.get(key) != 0 for key in
               ("trace_mismatches", "oracle_mismatches", "contract_mismatches",
                "measurement_mismatches", "summary_mismatches", "control_mismatches"))
        or verification.get("results_sha256") != sha256(RUN / "results.json")
        or verification.get("manifest_sha256") != sha256(RUN / "manifest.json")
        or spec.get("training") is not False
        or spec.get("policy_refit") is not False
        or spec.get("production_promotion") is not False
    ):
        raise RuntimeError("refusing C36 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c36-wide-natural-repeated-query-summary/v1",
        "date": "2026-09-01",
        "status": "verified_local_cm_gate_failed_exploratory_routing_headroom",
        "report": REPORT,
        "run": RUN.relative_to(ROOT).as_posix(),
        "source_milestone": "C35",
        "dataset": result["dataset"],
        "measurement_rows": 576,
        "timed_queries": 36_864,
        "semantic_or_artifact_mismatches": 0,
        "summary": summary,
        "controls": controls,
        "external_functional_probes": probes,
        "training": False,
        "policy_refit": False,
        "fresh_parameter_and_truth_identities": True,
        "source_repository_reused": True,
        "production_write": False,
        "production_promotion": False,
        "runpod": {"used": False, "cost_usd": 0.0},
        "verification": {
            "path": (RUN / "independent_verification.json").relative_to(ROOT).as_posix(),
            **verification,
        },
        "interpretation": (
            "At q64 CM IR is 0.8783x flattened CSE and 0.9376x compiled truth "
            "projection, so its fixed promotion gate fails. A post-hoc family rule is "
            "1.2841x the best fixed method after the frozen recognition charge, creating "
            "prospective C37 routing headroom but permitting no current promotion."
        ),
    }
    write(DOCS / MACHINE, machine)

    scope = (
        "C36 measures 576 resident sessions and 36,864 exact query deliveries on 18 fresh "
        "width-11..16 natural functions. CM IR is 0.8783x flattened CSE at q64, so the "
        "fixed gate fails. A post-hoc family rule is 1.2841x the best fixed method after "
        "the frozen charge; independent replay finds zero mismatches and permits only a "
        "prospective no-training routing experiment."
    )
    next_experiment = (
        "C37 should freeze the C36 family rule before loading unseen parameter/truth "
        "identities and an independent source, then compare it with a tiny development-only "
        "cost tree and all fixed exact methods under charged verification and fallback."
    )
    register = load(REGISTER)
    track_ids = [row["id"] for row in register["tracks"]]
    application_names = [row["name"] for row in register["applications"]]
    if len(track_ids) != 18 or len(set(track_ids)) != 18 or len(application_names) != 8:
        raise RuntimeError("track/application inventory changed before C36 registration")
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
        raise RuntimeError(f"expected eleven C36 registrations, observed {registrations}")
    register["milestones"]["F"] = (
        "C36 extends natural repeated restrictions to fresh width-11..16 functions. "
        "Fixed CM remains behind CSE and compiled projection, while charged post-hoc family "
        "routing exposes enough headroom for a separately frozen prospective C37 selector"
    )
    register["updated"] = "2026-09-01"
    if ([row["id"] for row in register["tracks"]] != track_ids
            or [row["name"] for row in register["applications"]] != application_names):
        raise RuntimeError("C36 registration changed track/application identity or order")
    write(REGISTER, register)
    print(json.dumps({
        "status": "registered", "tracks": len(track_ids),
        "applications": len(application_names), "c36_registrations": registrations,
        "measurement_rows": 576, "timed_queries": 36_864,
        "semantic_or_artifact_mismatches": 0, "cm_promotion_gate": False,
        "exploratory_routing_headroom_gate": True,
        "training": False, "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
