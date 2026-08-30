"""Register the independently verified local C16 exact-screened GF(2) study."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
REGISTER = DOCS / "experiment_register.json"
RUN = DOCS / "runs/c16-gf2-screened-tail-windows-20260830-001"
LINUX = DOCS / "c16_linux_confirmation"
REPORT = "LEARNING_MILESTONE_C16_EXACT_SCREENED_GF2_2026_08_30.md"
MACHINE = "learning_milestone_c16_exact_screened_gf2_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def upsert(container: dict, scope: str) -> None:
    value = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    existing = [row for row in container["results"] if row.get("report") == REPORT]
    if len(existing) > 1:
        raise SystemExit("duplicate C16 registration")
    if existing:
        existing[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verification = load(RUN / "independent_verification.json")
    validation = load(LINUX / "C16_PACKAGE_LOCAL_VALIDATION_20260830.json")
    manifest = load(LINUX / "c16_linux_upload_manifest.json")
    if (not (DOCS / REPORT).is_file() or result.get("status") != "complete"
            or result.get("semantic_or_artifact_mismatches") != 0
            or result["summary"].get("functional_gate") is not True
            or result["summary"].get("local_timing_gate") is not True
            or verification.get("status") != "verified"
            or verification.get("source_cases_replayed") != 40
            or verification.get("controls_replayed") != 12
            or validation.get("status") != "pass" or validation.get("measurement_rows") != 360
            or manifest.get("file_count") != 18 or manifest.get("bytes") != 423661):
        raise SystemExit("refusing C16 registration: evidence incomplete")
    machine = {
        "schema": "crse-learning-milestone-c16-exact-screened-gf2-summary/v1",
        "date": "2026-08-30",
        "status": "local_complete_second_machine_pending_exact_payload_approval",
        "report": REPORT,
        "run": rel(RUN),
        "verification": {"path": rel(RUN / "independent_verification.json"), **verification},
        "dataset": result["dataset"],
        "artifact_rows": result["artifact_rows"],
        "summary": result["summary"],
        "package_validation": {"path": rel(LINUX / "C16_PACKAGE_LOCAL_VALIDATION_20260830.json"),
                               **validation},
        "linux_package": {"manifest": rel(LINUX / "c16_linux_upload_manifest.json"),
                          "protocol": rel(LINUX / "C16_SECOND_MACHINE_TIMING_PROTOCOL_2026_08_30.md"),
                          "files": manifest["file_count"], "bytes": manifest["bytes"]},
        "runpod": {"used": False, "pod_created": False, "uploaded": False,
                   "cost_usd": 0.0, "exact_payload_approval_required": True,
                   "reason": "host approval review rejected broad authorization before process creation"},
        "semantic_or_artifact_mismatches": 0,
        "production_promotion": False,
        "interpretation": (
            "Exact descriptor screening preserved the exhaustive best artifact while reducing "
            "whole-path time by 3.545x locally; one small case regressed and Linux execution "
            "awaits exact payload approval, so production remains disabled."
        ),
    }
    write(DOCS / MACHINE, machine)

    data = load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])]
            != [f"R{index:02d}" for index in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing C16 register update: 18-track or 8-application shape changed")
    tracks = {track["id"]: track for track in data["tracks"]}
    scope = (
        "All 64 bounded partitions now share one exact matrix layout and only the best four "
        "inert descriptors are materialized. The best artifact matched exhaustive identity on "
        "40 Yosys cases and 12 controls; local whole-path speedup was 3.545x."
    )
    for track_id in ("R06", "R16", "R18"):
        upsert(tracks[track_id], scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = scope
    tracks["R06"]["next_experiment"] = (
        "Confirm the frozen exact-screened tail on Linux, then test a fresh non-XOR-heavy family "
        "before considering any learned partition ranker."
    )
    tracks["R16"]["next_experiment"] = (
        "Add a charged tiny-case bypass for the observed 0.893x worst case and retain advice-off "
        "exhaustive materialization."
    )
    tracks["R18"]["next_experiment"] = (
        "Retain dense incompressible controls, byte-identical exhaustive-best checks, per-case "
        "slowdown reporting, and second-machine timing."
    )
    hardware = next(item for item in data["applications"]
                    if item["name"] == "Hardware verification/design")
    upsert(hardware, scope)
    data["milestones"]["C"] = (
        "C16 exact-screened CM/GF(2) tail preserves the exhaustive best on all retained cases "
        "and passes local timing; exact-payload Linux approval and a tiny-case bypass remain"
    )
    data["updated"] = "2026-08-30"
    write(REGISTER, data)
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "updated_tracks": ["R06", "R16", "R18"], "milestone": "C16",
                      "runpod_used": False, "runpod_cost_usd": 0.0}, sort_keys=True))


if __name__ == "__main__":
    main()
