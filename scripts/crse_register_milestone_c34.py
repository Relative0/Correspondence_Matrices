"""Register independently verified C34 natural headroom evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c34-natural-headroom-windows-20260901-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C34_NATURAL_TASK_MATCHED_HEADROOM_2026_09_01.md"
MACHINE = "learning_milestone_c34_natural_headroom_results.json"
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
        raise RuntimeError("duplicate C34 registration")
    if matches:
        matches[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    controls = load(RUN / "functional_controls.json")
    eligibility = load(RUN / "eligibility.json")
    bdd = load(RUN / "bdd_functional_probes.json")
    spec = load(RUN / "run_spec.json")
    truth = result.get("summary", {}).get("complete_relation", {})
    decomposition = result.get("summary", {}).get("gf2_decomposition", {})
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("dataset", {}).get("cases") != 48
        or result.get("dataset", {}).get("decomposition_cases") != 15
        or result.get("dataset", {}).get("source_dataset_reused") is not True
        or result.get("dataset", {}).get("fresh_confirmation") is not False
        or result.get("truth_measurement_rows") != 3456
        or result.get("decomposition_measurement_rows") != 270
        or result.get("semantic_or_artifact_mismatches") != 0
        or result.get("functional_controls_passed") is not True
        or result.get("bdd_functional_probes_passed") is not True
        or truth.get("best_fixed_method") != "direct_ast_bitset"
        or truth.get("methods", {}).get("direct_ast_bitset", {}).get("per_case_wins") != 48
        or truth.get("oracle_headroom_gate") is not False
        or decomposition.get("best_fixed_method") != "flattened_cse_complete_screened"
        or decomposition.get("oracle_headroom_gate") is not False
        or decomposition.get("width_rule", {}).get("headroom_gate") is not False
        or result.get("decision", {}).get("training_performed") is not False
        or result.get("decision", {}).get("learning_or_router_promotion_permitted") is not False
        or result.get("decision", {}).get("production_promotion") is not False
        or result.get("runpod") != {"used": False, "cost_usd": 0.0}
        or controls.get("all_passed") is not True
        or controls.get("production_write") is not False
        or controls.get("production_promotion") is not False
        or bdd.get("status") != "passed"
        or bdd.get("performance_ranking_permitted") is not False
        or len(bdd.get("rows", [])) != 8
        or verification.get("status") != "verified"
        or verification.get("dataset_cases_replayed") != 48
        or verification.get("decomposition_oracles_recomputed") != 15
        or verification.get("truth_measurements_checked") != 3456
        or verification.get("decomposition_measurements_checked") != 270
        or any(verification.get(key) != 0 for key in
               ("semantic_mismatches", "oracle_mismatches", "measurement_mismatches", "summary_mismatches"))
        or verification.get("results_sha256") != sha256(RUN / "results.json")
        or verification.get("manifest_sha256") != sha256(RUN / "manifest.json")
        or spec.get("complete_partition_universe") is not True
        or spec.get("training") is not False
        or spec.get("production_promotion") is not False
    ):
        raise RuntimeError("refusing C34 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c34-natural-headroom-summary/v1",
        "date": "2026-09-01",
        "status": "verified_local_both_headroom_gates_failed_no_promotion",
        "report": REPORT,
        "run": RUN.relative_to(ROOT).as_posix(),
        "source_milestone": "C33",
        "dataset": result["dataset"],
        "truth_measurement_rows": 3456,
        "decomposition_measurement_rows": 270,
        "semantic_or_artifact_mismatches": 0,
        "charged_router_budget_ns": spec["charged_router_budget_ns"],
        "complete_relation": truth,
        "gf2_decomposition": decomposition,
        "eligibility": eligibility,
        "bdd_functional_probes": bdd,
        "controls": controls,
        "training": False,
        "policy_refit": False,
        "fresh_confirmation": False,
        "source_dataset_reused": True,
        "production_write": False,
        "production_promotion": False,
        "runpod": {"used": False, "cost_usd": 0.0},
        "verification": {
            "path": (RUN / "independent_verification.json").relative_to(ROOT).as_posix(),
            **verification,
        },
        "interpretation": (
            "C34 finds no profitable one-shot routing surface. Direct AST bitset wins all "
            "48 complete-relation cases. Complete exact GF(2) decomposition has only "
            "1.0035x optimistic per-case-oracle and 1.0033x budget-adjusted headroom; "
            "the post-hoc width rule is 1.0021x after budget. Both frozen gates fail."
        ),
    }
    write(DOCS / MACHINE, machine)

    scope = (
        "C34 measures 3,456 exact complete-vector and 270 complete GF(2)-decomposition "
        "executions on 48 reused natural Yosys cases at support 3-10. Direct AST wins all "
        "vector cases; complete decomposition leaves only 1.0033x budget-adjusted "
        "per-case-oracle and 1.0021x width-rule headroom. Independent replay finds zero "
        "mismatches, both gates fail, and no training or promotion occurs."
    )
    next_experiment = (
        "C35 should freeze natural repeated-query count, restriction, SAT/witness, "
        "persistence, and version traces. Compare fresh and resident direct/CSE/CM, "
        "compiled exact structures, BDD/CUDD, and CaDiCaL only under aligned output "
        "contracts; measure compile amortization and break-even query count before learning."
    )
    register = load(REGISTER)
    track_ids = [row["id"] for row in register["tracks"]]
    application_names = [row["name"] for row in register["applications"]]
    if len(track_ids) != 18 or len(set(track_ids)) != 18 or len(application_names) != 8:
        raise RuntimeError("track/application inventory changed before C34 registration")
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
        raise RuntimeError(f"expected eleven C34 registrations, observed {registrations}")
    register["milestones"]["F"] = (
        "C34 completes the one-shot natural exact-headroom adjudication: direct evaluation "
        "dominates complete vectors and complete GF(2) decomposition has no payable routing "
        "margin, so both learning gates fail and work shifts to repeated-query lifecycles"
    )
    register["updated"] = "2026-09-01"
    if ([row["id"] for row in register["tracks"]] != track_ids
            or [row["name"] for row in register["applications"]] != application_names):
        raise RuntimeError("C34 registration changed track/application identity or order")
    write(REGISTER, register)
    print(json.dumps({
        "status": "registered",
        "tracks": len(track_ids),
        "applications": len(application_names),
        "c34_registrations": registrations,
        "truth_measurements": 3456,
        "decomposition_measurements": 270,
        "semantic_or_artifact_mismatches": 0,
        "truth_headroom_gate": False,
        "decomposition_headroom_gate": False,
        "training": False,
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
