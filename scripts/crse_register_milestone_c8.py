"""Register the independently verified C8 Linux source-ANF confirmation."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
HERE = DOCS / "c7_linux_confirmation"
LIFECYCLE = HERE / "RUNPOD_C7_LINUX_SINGLE_PORT_FINAL_VERIFICATION_20260830-045932-420152.json"
SEMANTIC = DOCS / "verification" / "yosys-source-anf-linux-confirmation-20260830-001.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C8_LINUX_SOURCE_ANF_CONFIRMATION_2026_08_30.md"
MACHINE = "learning_milestone_c8_linux_source_anf_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


UPDATES = {
    "R01": (
        "All six exact representations reproduced every canonical partition across Windows and a separately provisioned Linux CPU.",
        "Freeze a source-only analytic representation dispatcher on pre-C7 development data.",
    ),
    "R03": (
        "Cross-machine results support a set/packed/bitset portfolio: set led sparse medians, packed controlled tails, and bitset remained competitive.",
        "Measure dispatcher selection regret against all three exact paths without tuning on C7/C8.",
    ),
    "R06": (
        "Independent Linux replay verified 2,160 method/case/repetition outputs with zero semantic mismatches.",
        "Retain exact truth confirmation behind every selected representation.",
    ),
    "R16": (
        "Second-machine timing completed: packed retained a 2.10-2.23x median advantage over NumPy and a 1.85-2.09x p95 advantage over direct bitset.",
        "Test a frozen analytic dispatcher on both sealed machines and report latency regret.",
    ),
    "R17": (
        "The strongest transfer result remains deterministic and exact; no additional neural fitting was needed.",
        "Use learned selection only if a frozen analytic dispatcher cannot transfer across families and machines.",
    ),
    "R18": (
        "Linux reversed the small packed-versus-bitset median lead while preserving packed tail wins, exposing the required machine-sensitivity control.",
        "Keep set, packed, direct-bitset, cold-cache, warm-cache, and NumPy arms in dispatcher evaluation.",
    ),
}


def main():
    lifecycle, semantic = load(LIFECYCLE), load(SEMANTIC)
    if (lifecycle.get("status") != "pass" or lifecycle.get("complete") is not True
            or lifecycle.get("scientific_confirmation_complete") is not True
            or lifecycle.get("owned_pod_absent_verified") is not True
            or lifecycle.get("semantic_mismatches") != 0
            or semantic.get("status") != "pass" or semantic.get("measurement_rows_replayed") != 2160
            or semantic.get("semantic_mismatches") != 0 or semantic.get("criteria", {}).get("exact") is not True):
        raise SystemExit("refusing C8 registration: Linux evidence is not independently complete")
    machine = {
        "schema": "crse-learning-milestone-c8-linux-source-anf-summary/v1",
        "date": "2026-08-30", "status": "complete", "production_promotion": False,
        "report": REPORT,
        "remote_study": "docs/recognition/c7_linux_confirmation/runpod-c7-linux-single-port-execute-001/evidence/run-output/yosys-c7-linux-confirmation",
        "lifecycle_verification": {"path": str(LIFECYCLE.relative_to(ROOT)).replace("\\", "/"), **lifecycle},
        "semantic_verification": {"path": str(SEMANTIC.relative_to(ROOT)).replace("\\", "/"), **semantic},
        "local_c7_run": "docs/recognition/runs/yosys-source-anf-confirmation-20260830-002",
        "method_summary": semantic["method_summary"], "criteria": semantic["criteria"],
        "semantic_mismatches": 0,
        "interpretation": (
            "Exactness, the packed-over-NumPy advantage, and the sparse set-ANF lead transferred across machines. "
            "Packed beat direct bitset at Linux p95 but not median; use a frozen exact representation dispatcher."
        ),
    }
    (DOCS / MACHINE).write_bytes(json.dumps(machine, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    data = load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer contains exact R01-R18 and eight applications")
    by_id = {track["id"]: track for track in data["tracks"]}
    for track_id, (reason, next_experiment) in UPDATES.items():
        track = by_id[track_id]
        track["status"] = "measured"
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        result = {"report": REPORT, "machine_summary": MACHINE, "scope": reason}
        existing = [row for row in track["results"] if row.get("report") == REPORT]
        if len(existing) > 1:
            raise SystemExit(f"duplicate C8 registration for {track_id}")
        if existing:
            existing[0].update(result)
        else:
            track["results"].append(result)
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    hardware_result = {"report": REPORT, "machine_summary": MACHINE,
        "scope": "Exact Yosys-family decomposition and representation timing transferred to a separately provisioned Linux CPU."}
    existing = [row for row in hardware["results"] if row.get("report") == REPORT]
    if len(existing) > 1:
        raise SystemExit("duplicate C8 hardware registration")
    if existing:
        existing[0].update(hardware_result)
    else:
        hardware["results"].append(hardware_result)
    data["milestones"]["C"] = (
        "C8 Linux confirmation complete; exactness and packed-over-NumPy transfer, sparse set ANF remains fastest, packed-versus-bitset median is machine-sensitive"
    )
    data["updated"] = "2026-08-30"
    REGISTER.write_bytes(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "c8_tracks": sorted(UPDATES), "semantic_mismatches": 0,
        "owned_pod_absent": True, "production_promotion": False}, sort_keys=True))


if __name__ == "__main__":
    main()
