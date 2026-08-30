"""Register the independently verified E1 bounded ROBDD order study."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/bdd-order-e1-20260830-002"
VERIFY = DOCS / "verification/bdd-order-e1-20260830-002.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_E1_BDD_ORDER_SELECTION_2026_08_30.md"
MACHINE = "learning_milestone_e1_bdd_order_results.json"


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
        raise SystemExit("duplicate E1 registration")
    if existing:
        existing[0].update(result)
    else:
        container["results"].append(result)


def main() -> None:
    summary, verification = load(RUN / "summary.json"), load(VERIFY)
    if (not (DOCS / REPORT).is_file() or summary.get("status") != "complete"
            or summary.get("training_measurement_rows") != 720
            or summary.get("evaluation_measurement_rows") != 600
            or summary.get("semantic_mismatches") != 0
            or summary.get("criteria", {}).get("exact_truth_all_selected_orders") is not True
            or summary.get("criteria", {}).get("task_probes_exact") is not True
            or summary.get("criteria", {}).get("production_promotion") is not False
            or verification.get("status") != "pass"
            or verification.get("models_refit") != 3
            or verification.get("selected_orders_semantically_replayed")
            != summary.get("task_probe_rows")
            or verification.get("semantic_mismatches") != 0):
        raise SystemExit("refusing E1 registration: evidence is incomplete")
    machine = {
        "schema": "crse-learning-milestone-e1-bdd-order-summary/v1",
        "date": "2026-08-30", "status": "complete", "report": REPORT,
        "run": relative(RUN),
        "verification": {"path": relative(VERIFY), **verification},
        "backend": "dd.autoref", "dd_version": summary["dd_version"],
        "dynamic_reordering": False,
        "training_cases": summary["training_cases"],
        "evaluation_cases": summary["evaluation_cases"],
        "training_measurement_rows": summary["training_measurement_rows"],
        "evaluation_measurement_rows": summary["evaluation_measurement_rows"],
        "task_probe_rows": summary["task_probe_rows"],
        "aggregate": summary["aggregate"],
        "cost_tree_regret": summary["cost_tree_regret"],
        "criteria": summary["criteria"], "semantic_mismatches": 0,
        "production_promotion": False,
        "runpod": {"used": False, "cost_usd": 0.0,
                   "reason": "bounded Windows autoref study completed locally"},
        "interpretation": (
            "First-occurrence order was the strongest deterministic control. "
            "The learned tree selected it but did not repay feature and decision "
            "cost; random best-of-four was substantially slower when search was charged."
        ),
    }
    write_json(DOCS / MACHINE, machine)
    data = load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])]
            != [f"R{index:02d}" for index in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing E1 update: register shape changed")
    by_id = {track["id"]: track for track in data["tracks"]}
    scopes = {
        "R01": "A task-specific BDD study separated minimum nodes, cold build, and build-plus-restriction objectives; exact advice selected only variable-order strategies.",
        "R07": "Fixed, first-occurrence, interaction, random best-of-four, and a bounded cost tree were measured on 20 alpha-distinct mux/arithmetic/comparator/component formulas with exact reloadable artifacts.",
        "R16": "All order generation, searched builds, partial queries, features, decisions, and independent checks were separated; the learned arm failed to repay inference overhead.",
        "R18": "Charged random best-of-four and the learned cost tree are retained negatives: first occurrence remained faster on the sealed slice while preserving fewer or equal nodes.",
    }
    next_steps = {
        "R01": "Implement E2 exact SAT/equivalence task contracts before training any solver guidance.",
        "R07": "Add a natural held-out source and optional identified native CUDD control before any broader order claim.",
        "R16": "Measure cold and reused SAT sessions with encoding, assumptions, witness checks, and invalidation charged.",
        "R18": "Retain fixed order, no-search first occurrence, charged best-of-k, and outside-range fallback as future controls.",
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
           "Exact BDD order, reuse, and persistence were measured on bounded generated mux, carry, comparator, and hidden-component formulas; first occurrence led and learned routing was negative.")
    data["milestones"]["E"] = (
        "E1 bounded BDD order selection measured; exact artifact/reuse layer complete, "
        "first-occurrence control led, learned timing policy negative, native CUDD pending"
    )
    data["updated"] = "2026-08-30"
    write_json(REGISTER, data)
    print(json.dumps({
        "tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "updated_tracks": sorted(scopes), "milestone": "E1",
        "semantic_mismatches": 0, "production_promotion": False,
        "runpod_used": False, "runpod_cost_usd": 0.0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
