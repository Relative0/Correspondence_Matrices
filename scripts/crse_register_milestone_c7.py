"""Register verified C7 evidence without dropping research tracks."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
RUN = DOCS / "runs" / "yosys-source-anf-confirmation-20260830-002"
VERIFY = DOCS / "verification" / "yosys-source-anf-confirmation-20260830-002.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C7_YOSYS_SOURCE_CONFIRMATION_2026_08_30.md"
MACHINE = "learning_milestone_c7_yosys_source_confirmation_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


UPDATES = {
    "R01": (
        "The frozen exact source recognizers transferred with zero errors to 40 independent Yosys-derived cases.",
        "Freeze an exact set/packed representation dispatcher without using either sealed C7 split for tuning.",
    ),
    "R03": (
        "Packed source ANF beat both truth-vector controls, while sparse set ANF remained faster on the external low-complexity family.",
        "Use source-only interaction counters to select set or packed ANF before either expensive path runs.",
    ),
    "R06": (
        "Packed, set, NumPy, and direct-bitset paths returned identical canonical partitions across five external generator families.",
        "Confirm the exact representation ranking on a second CPU/Linux machine.",
    ),
    "R16": (
        "Cached packed ANF achieved 1.10-1.12x median and 1.89-2.04x p95 speedups over direct bitset truth-vector ANF.",
        "Run the checksum-frozen C7 timing package once on a separately provisioned CPU.",
    ),
    "R17": (
        "Independent exact transfer succeeded without training; neural cut fitting remains paused after its earlier transfer failures.",
        "Test a frozen analytic representation selector before allocating another learned-model sweep.",
    ),
    "R18": (
        "The independent family exposed a real counterexample to universal packed promotion: sparse set ANF remained 1.94-2.44x faster at median.",
        "Retain set, packed, cached, direct-bitset, and NumPy controls in second-machine timing.",
    ),
}


def main():
    summary, verification = load(RUN / "summary.json"), load(VERIFY)
    required_true = ("exact", "independent_source", "c6_baseline_cost", "strong_baseline_cost", "safety")
    if (summary.get("status") != "complete" or verification.get("status") != "pass"
            or any(summary.get("criteria", {}).get(key) is not True for key in required_true)
            or summary.get("criteria", {}).get("legacy_set_cost") is not False
            or summary.get("criteria", {}).get("production_promotion") is not False
            or summary.get("semantic_mismatches") != 0):
        raise SystemExit("refusing C7 registration: verified evidence differs from reviewed result")
    machine = {
        "schema": "crse-learning-milestone-c7-yosys-source-confirmation-summary/v1",
        "date": "2026-08-30",
        "status": "complete",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "development_runs": ["docs/recognition/runs/yosys-source-anf-confirmation-20260830-001"],
        "verification": {"path": str(VERIFY.relative_to(ROOT)).replace("\\", "/"), **verification},
        "retained_c6": summary["retained_c6"],
        "source_provenance": summary["source_provenance"],
        "dataset_audit": summary["dataset_audit"],
        "method_summary": summary["method_summary"],
        "cache_telemetry": summary["cache_telemetry"],
        "criteria": summary["criteria"],
        "semantic_mismatches": 0,
        "interpretation": (
            "Packed exact source ANF transferred beyond EPFL and beat direct bitset truth-vector ANF, but retained set ANF remained faster on this sparse family. "
            "Use an exact cost-aware representation portfolio; do not promote packed ANF universally."
        ),
    }
    target = DOCS / MACHINE
    if target.exists() and load(target).get("schema") != machine["schema"]:
        raise SystemExit("refusing C7 registration: unrelated machine summary already exists")
    target.write_bytes(json.dumps(machine, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")

    data = load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer contains exact R01-R18 and eight applications")
    by_id = {track["id"]: track for track in data["tracks"]}
    for track_id, (reason, next_experiment) in UPDATES.items():
        track = by_id[track_id]
        existing = [item for item in track["results"] if item.get("report") == REPORT]
        if len(existing) > 1:
            raise SystemExit(f"duplicate C7 registration for {track_id}")
        track["status"] = "measured"
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        result = {"report": REPORT, "machine_summary": MACHINE, "scope": reason}
        if existing:
            existing[0].update(result)
        else:
            track["results"].append(result)
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    hardware_result = {"report": REPORT, "machine_summary": MACHINE,
        "scope": "Exact source decomposition transferred to independent Yosys generator families; sparse set ANF retained the best latency."}
    existing_hardware = [item for item in hardware["results"] if item.get("report") == REPORT]
    if len(existing_hardware) > 1:
        raise SystemExit("duplicate C7 hardware registration")
    if existing_hardware:
        existing_hardware[0].update(hardware_result)
    else:
        hardware["results"].append(hardware_result)
    data["milestones"]["C"] = (
        "C7 independent Yosys source confirmation complete; packed beat both truth-vector controls but sparse set ANF retained the latency lead"
    )
    data["updated"] = "2026-08-30"
    REGISTER.write_bytes(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "c7_tracks": sorted(UPDATES), "strong_baseline_cost": True, "legacy_set_cost": False,
        "production_promotion": False, "safety": True}, sort_keys=True))


if __name__ == "__main__":
    main()
