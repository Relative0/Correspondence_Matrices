"""Register verified native-portfolio closure and the resulting no-training decision."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/native-portfolio-development-20260903-001"
REASSESSMENT = DOCS / "runs/neural-native-portfolio-reassessment-development-20260903-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "../research/CM_NATIVE_PORTFOLIO_BASELINE_CLOSURE_2026_09_03.md"
MACHINE = "native_portfolio_baseline_closure_results.json"
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
        raise RuntimeError("duplicate native portfolio registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    assessment = load(REASSESSMENT / "assessment.json")
    assessment_verification = load(REASSESSMENT / "independent_verification.json")
    summary = result.get("summary", {})
    if (
        result.get("status") != "complete"
        or result.get("dataset", {}).get("classification")
        != "development_exposed_c36_not_confirmation"
        or summary.get("best_fixed_method") != "native_fused_slots"
        or summary.get("per_case_winner_counts") != {"native_fused_slots": 18}
        or summary.get("per_case_oracle_total_ns")
        != summary.get("q64_accounted_total_ns", {}).get("native_fused_slots")
        or summary.get("oracle_speedup_over_best_fixed") != 1.0
        or summary.get("selector_development_headroom_gate") is not False
        or result.get("decision", {}).get("prospective_confirmation_allowed") is not False
        or verification.get("status") != "verified"
        or verification.get("results_sha256") != sha256(RUN / "results.json")
        or verification.get("manifest_sha256") != sha256(RUN / "manifest.json")
        or any(verification.get(name) != 0 for name in (
            "artifact_mismatches", "source_mismatches", "interpreter_mismatches",
            "native_mismatches", "dataset_mismatches", "structure_mismatches",
            "schedule_mismatches", "correctness_mismatches", "timing_mismatches",
            "native_identity_mismatches", "summary_mismatches", "decision_mismatches"))
        or assessment.get("decision", {}).get("training_allowed") is not False
        or assessment.get("decision", {}).get("prospective_confirmation_allowed") is not False
        or assessment.get("economics", {}).get("gross_headroom_speedup") != 1.0
        or assessment_verification.get("status") != "verified"
        or assessment_verification.get("assessment_sha256")
        != sha256(REASSESSMENT / "assessment.json")
    ):
        raise RuntimeError("refusing native portfolio registration: evidence incomplete")

    scope = (
        "A cache-isolated seven-arm q64 run closes native slots against R2, optimized "
        "projection, and CSE/CM bigint/word controls on the 18 exposed C36 cases. "
        "Native is 1.2727x the best non-native fixed method and wins all 18 cases, "
        "leaving exactly 1.0000x selector headroom. Independent replay found zero "
        "mismatches; training, prospective-data use, and production promotion remain off."
    )
    next_experiment = (
        "Do not run C37 or consume a prospective corpus on this surface. Resume learned "
        "or prospective selection only after a genuinely new exact task leaves about "
        "1.10x development oracle headroom after optimized exact baselines."
    )
    machine = {
        "schema": "crse-native-portfolio-baseline-closure-summary/v1",
        "date": "2026-09-03",
        "status": "verified_fixed_native_gain_zero_selector_headroom",
        "report": REPORT,
        "run": RUN.relative_to(ROOT).as_posix(),
        "reassessment": REASSESSMENT.relative_to(ROOT).as_posix(),
        "dataset": result["dataset"],
        "methods": result["methods"],
        "summary": summary,
        "decision": result["decision"],
        "training": False,
        "prospective_data_consumed": False,
        "production_write": False,
        "production_promotion": False,
        "verification": verification,
        "reassessment_verification": assessment_verification,
    }
    write(DOCS / MACHINE, machine)

    register = load(REGISTER)
    track_ids = [row["id"] for row in register["tracks"]]
    application_names = [row["name"] for row in register["applications"]]
    if len(track_ids) != 18 or len(set(track_ids)) != 18 or len(application_names) != 8:
        raise RuntimeError("track/application inventory changed before native registration")
    registrations = 0
    for row in register["tracks"]:
        if row["id"] not in TRACK_IDS:
            continue
        upsert(row, scope)
        row["status"] = "measured"
        row["status_reason"] = scope
        row["next_experiment"] = next_experiment
        registrations += 1
    for row in register["applications"]:
        if row["name"] == APPLICATION:
            upsert(row, scope)
            row["status"] = "measured"
            registrations += 1
    if registrations != 11:
        raise RuntimeError(f"expected eleven native registrations, observed {registrations}")
    register["milestones"]["F"] = (
        "The September 3 native exact-portfolio closure supersedes C36's proposed C37 "
        "route: fused native slots beat the best non-native fixed backend by 1.2727x "
        "but win all 18 exposed cases, leaving exactly 1.0000x selector headroom. "
        "Prospective-data use and training remain stopped."
    )
    register["updated"] = "2026-09-03"
    if (
        [row["id"] for row in register["tracks"]] != track_ids
        or [row["name"] for row in register["applications"]] != application_names
    ):
        raise RuntimeError("native registration changed track/application identity or order")
    write(REGISTER, register)
    print(json.dumps({
        "status": "registered",
        "registrations": registrations,
        "best_fixed_method": summary["best_fixed_method"],
        "native_speedup_over_best_non_native": summary["native_speedup_over_best_non_native"],
        "oracle_headroom": summary["oracle_speedup_over_best_fixed"],
        "training": False,
        "prospective_data_consumed": False,
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
