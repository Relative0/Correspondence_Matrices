"""Register verified C6 evidence without dropping research tracks."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
RUN = DOCS / "runs" / "natural-source-anf-hybrid-20260830-004"
VERIFY = DOCS / "verification" / "natural-source-anf-hybrid-20260830-004.json"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C6_PACKED_SOURCE_ANF_2026_08_30.md"
MACHINE = "learning_milestone_c6_packed_source_anf_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


UPDATES = {
    "R01": (
        "Packed exact source-DAG ANF now removes the retained set-product tail while preserving proof-compatible partitions.",
        "Freeze the packed core and test an independently authored Boolean decomposition suite.",
    ),
    "R03": (
        "A validation-frozen cached hybrid preserved exact source-level decomposition on 11 fallbacks but missed confirmatory p95 by 1.4%.",
        "Advance the packed core with only its hard admission fallback; retain the product-pair gate as a negative control.",
    ),
    "R06": (
        "Exact GF(2) OR-convolution over a 1,024-bit coefficient vector matched all 188 set ANFs and scalar truth tables.",
        "Compare the frozen packed representation with a bounded BDD/AIG decomposition control on an independent family.",
    ),
    "R16": (
        "Packed source ANF achieved 1.28-1.64x held-out median speedups and 1.80-2.18x p95 speedups over truth-vector ANF.",
        "Confirm packed-core latency on another machine with cold and warm cache streams separated.",
    ),
    "R17": (
        "The deterministic packed core passed the EPFL cost boundary; neural cut fitting remains paused after C5 transfer failures.",
        "Use independent exact families to decide whether more learned recognition is justified.",
    ),
    "R18": (
        "C6 retained two failed development runs and showed that transform-mask construction and fallback overhead can erase a symbolic gain.",
        "Keep set ANF, truth-vector ANF, forced fallback, cold cache, and no-cache paths in the independent confirmation.",
    ),
}


def main():
    summary, verification = load(RUN / "summary.json"), load(VERIFY)
    required = ("exact", "packed_core", "cached_packed_core", "safety")
    if (summary.get("status") != "complete" or verification.get("status") != "pass"
            or any(summary.get("criteria", {}).get(key) is not True for key in required)
            or summary.get("semantic_mismatches") != 0 or verification.get("semantic_mismatches") != 0):
        raise SystemExit("refusing C6 registration: verified evidence differs from reviewed result")
    machine = {
        "schema": "crse-learning-milestone-c6-packed-source-anf-summary/v1",
        "date": "2026-08-30",
        "status": "complete",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "development_runs": [
            "docs/recognition/runs/natural-source-anf-hybrid-20260830-001",
            "docs/recognition/runs/natural-source-anf-hybrid-20260830-002",
            "docs/recognition/runs/natural-source-anf-hybrid-20260830-003",
        ],
        "verification": {"path": str(VERIFY.relative_to(ROOT)).replace("\\", "/"), **verification},
        "retained_c5": summary["retained_c5"],
        "dataset_rows": summary["dataset_rows"],
        "gate_selection": summary["gate_selection"],
        "method_summary": summary["method_summary"],
        "cache_telemetry": summary["cache_telemetry"],
        "criteria": summary["criteria"],
        "semantic_mismatches": 0,
        "interpretation": (
            "Packed exact OR-convolution removed the C5 symbolic tail and passed held-out median and p95 criteria. "
            "The gated hybrid missed confirmatory p95 by 1.4%, so the packed core advances and the learned gate remains unpromoted."
        ),
    }
    target = DOCS / MACHINE
    if target.exists() and load(target).get("schema") != machine["schema"]:
        raise SystemExit("refusing C6 registration: unrelated machine summary already exists")
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
            raise SystemExit(f"duplicate C6 registration for {track_id}")
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
        "scope": "Packed and cached exact source ANF removed the EPFL p95 product tail; the validation gate failed narrowly."}
    existing_hardware = [item for item in hardware["results"] if item.get("report") == REPORT]
    if len(existing_hardware) > 1:
        raise SystemExit("duplicate C6 hardware registration")
    if existing_hardware:
        existing_hardware[0].update(hardware_result)
    else:
        hardware["results"].append(hardware_result)
    data["milestones"]["C"] = (
        "C6 packed exact source ANF complete; packed core passed exact held-out median and p95 criteria, budgeted hybrid tail failed narrowly"
    )
    data["updated"] = "2026-08-30"
    REGISTER.write_bytes(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "c6_tracks": sorted(UPDATES), "packed_core": True, "source_hybrid": False,
        "production_promotion": False, "safety": True}, sort_keys=True))


if __name__ == "__main__":
    main()
