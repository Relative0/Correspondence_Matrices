"""Register the independently verified E2/R10 SAT-guidance study."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/sat-guidance-e2-20260830-002"
VERIFY = DOCS / "verification/sat-guidance-e2-20260830-002.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_E2_SAT_EQUIVALENCE_GUIDANCE_2026_08_30.md"
MACHINE = "learning_milestone_e2_sat_guidance_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def upsert(container: dict, scope: str) -> None:
    result = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    existing = [row for row in container["results"] if row.get("report") == REPORT]
    if len(existing) > 1:
        raise SystemExit("duplicate E2 registration")
    if existing:
        existing[0].update(result)
    else:
        container["results"].append(result)


def main() -> None:
    summary, verification = load(RUN / "summary.json"), load(VERIFY)
    if (not (DOCS / REPORT).is_file() or summary.get("status") != "complete"
            or summary.get("dataset_cases") != 20
            or summary.get("task_instances") != 80
            or summary.get("training_measurement_rows") != 960
            or summary.get("evaluation_measurement_rows") != 960
            or summary.get("task_comparison_rows") != 160
            or summary.get("exact") is not True
            or summary.get("advice_off_exact") is not True
            or summary.get("count_task_measured") is not False
            or summary.get("local_second_machine_gate") is not False
            or summary.get("production_promotion") is not False
            or verification.get("status") != "passed"
            or verification.get("trusted_solver_replays") != 220
            or verification.get("exact") is not True):
        raise SystemExit("refusing E2 registration: evidence is incomplete")
    machine = {
        "schema": "crse-learning-milestone-e2-sat-guidance-summary/v1",
        "date": "2026-08-30", "status": "complete", "report": REPORT,
        "run": relative(RUN),
        "verification": {"path": relative(VERIFY), **verification},
        "solver": summary["solver"], "dataset_cases": summary["dataset_cases"],
        "task_instances": summary["task_instances"],
        "training_measurement_rows": summary["training_measurement_rows"],
        "evaluation_measurement_rows": summary["evaluation_measurement_rows"],
        "task_comparison_rows": summary["task_comparison_rows"],
        "sat_unsat_controls": summary["sat_unsat_controls"],
        "assumption_expected_statuses": summary["assumption_expected_statuses"],
        "model_fallback": summary["model_fallback"],
        "validation": summary["validation"], "sealed_test": summary["sealed_test"],
        "exact": True, "advice_off_exact": True, "count_task_measured": False,
        "local_second_machine_gate": False, "production_promotion": False,
        "runpod": {"used": False, "cost_usd": 0.0,
                   "reason": "predeclared Windows timing gate failed"},
        "interpretation": (
            "The exact SAT/session/miter infrastructure passed. The tree learned "
            "fresh-versus-resident structure but was 4.2% slower than resident "
            "default on sealed geometric mean after charging advice overhead."
        ),
    }
    write_json(DOCS / MACHINE, machine)
    data = load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])]
            != [f"R{index:02d}" for index in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing E2 update: register shape changed")
    by_id = {track["id"]: track for track in data["tracks"]}
    scopes = {
        "R01": "Task-aware routing now includes bounded single-SAT, assumption-session, and equivalence-miter lifecycles with exact advice-off fallback.",
        "R10": "A complete expression-to-CNF adapter, trusted CaDiCaL SAT/UNSAT contract, verified witnesses/cores, resident sessions, deterministic phase/order controls, and a bounded cost tree were measured on 80 tasks.",
        "R16": "CNF encoding, phase/order work, solver construction, solve calls, features, decisions, and independent witness/core checks are separated in frozen raw rows and exact artifact manifests.",
        "R18": "The learned SAT policy is retained as a negative timing result: it learned fresh-versus-resident structure but was 1.0420x the sealed best fixed action after advice overhead.",
    }
    next_steps = {
        "R01": "Retain the fixed resident SAT fallback; route only after an independently sourced larger-task study establishes headroom.",
        "R10": "Evaluate independently sourced larger CNF and hardware-miter sessions where solver work dominates adapter and policy overhead.",
        "R16": "Keep complete source hashing, trusted UNSAT replay, assumption replacement, and exact-digest invalidation in all later solver studies.",
        "R18": "Retain fresh, resident, polarity, component, and advice-off controls; do not spend second-machine compute until the local gate passes.",
    }
    for track_id, scope in scopes.items():
        track = by_id[track_id]
        upsert(track, scope)
        track["status"] = "measured"
        track["status_reason"] = scope
        track["next_experiment"] = next_steps[track_id]
    hardware = next(item for item in data["applications"]
                    if item["name"] == "Hardware verification/design")
    upsert(hardware,
           "Generated mux, carry, comparator, and component formulas now have exact SAT, incremental-assumption, and equivalence-miter adapters; the learned execution policy was not profitable on the bounded slice.")
    data["milestones"]["E"] = (
        "E1 bounded BDD order selection and E2 exact SAT/equivalence guidance "
        "measured; both exact infrastructures pass, both learned timing policies "
        "remain negative, native/large-source follow-ups pending"
    )
    data["updated"] = "2026-08-30"
    write_json(REGISTER, data)
    print(json.dumps({
        "tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "updated_tracks": sorted(scopes), "milestone": "E2",
        "exact": True, "production_promotion": False,
        "runpod_used": False, "runpod_cost_usd": 0.0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
