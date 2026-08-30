"""Register independently verified D10 and C15 exact studies."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
REGISTER = DOCS / "experiment_register.json"
D10_RUN = DOCS / "runs/d10-rule-engine-windows-20260830-002"
C15_RUN = DOCS / "runs/c15-exact-cm-gf2-windows-20260830-001"
D10_REPORT = "LEARNING_MILESTONE_D10_INDEXED_RULE_ENGINE_2026_08_30.md"
C15_REPORT = "LEARNING_MILESTONE_C15_EXACT_CM_GF2_2026_08_30.md"
D10_MACHINE = "learning_milestone_d10_indexed_rule_engine_results.json"
C15_MACHINE = "learning_milestone_c15_exact_cm_gf2_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def upsert(container: dict, report: str, machine: str, scope: str) -> None:
    value = {"report": report, "machine_summary": machine, "scope": scope}
    existing = [row for row in container["results"] if row.get("report") == report]
    if len(existing) > 1:
        raise SystemExit(f"duplicate registration for {report}")
    if existing:
        existing[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    d10, d10_verify = load(D10_RUN / "results.json"), load(D10_RUN / "independent_verification.json")
    c15, c15_verify = load(C15_RUN / "results.json"), load(C15_RUN / "independent_verification.json")
    if (not (DOCS / D10_REPORT).is_file() or not (DOCS / C15_REPORT).is_file()
            or d10.get("status") != "complete" or d10.get("semantic_mismatches") != 0
            or d10["summary"].get("false_matches") != 0
            or d10["summary"].get("local_promotion_gate") is not False
            or d10_verify.get("status") != "verified" or d10_verify.get("cases_replayed") != 30
            or c15.get("status") != "complete" or c15.get("semantic_mismatches") != 0
            or c15["summary"].get("functional_gate") is not True
            or c15["summary"].get("second_machine_timing_gate") is not False
            or c15_verify.get("status") != "verified" or c15_verify.get("source_cases_replayed") != 40):
        raise SystemExit("refusing D10/C15 registration: evidence incomplete")
    d10_machine = {"schema": "crse-learning-milestone-d10-indexed-rule-engine-summary/v1",
        "date": "2026-08-30", "status": "complete", "report": D10_REPORT,
        "run": rel(D10_RUN), "verification": {"path": rel(D10_RUN / "independent_verification.json"),
        **d10_verify}, "proof": d10["proof"], "dataset": d10["dataset"],
        "cache_version_probe": d10["cache_version_probe"], "summary": d10["summary"],
        "semantic_mismatches": 0, "production_promotion": False,
        "superseded_run": {"path": "docs/recognition/runs/d10-rule-engine-windows-20260830-001",
            "reason": "raw controls included naturally matched carry motifs; corrected before decision"},
        "runpod": d10["runpod"], "interpretation": (
            "Four exact rules, indexed bypass, provenance, and changed-cone persistence pass; "
            "no-rewrite CSE remained faster on every case, so runtime promotion is refused.")}
    c15_machine = {"schema": "crse-learning-milestone-c15-exact-cm-gf2-summary/v1",
        "date": "2026-08-30", "status": "complete", "report": C15_REPORT,
        "run": rel(C15_RUN), "verification": {"path": rel(C15_RUN / "independent_verification.json"),
        **c15_verify}, "dataset": c15["dataset"], "artifact_rows": c15["artifact_rows"],
        "summary": c15["summary"], "semantic_mismatches": 0,
        "production_promotion": False, "runpod": c15["runpod"],
        "interpretation": (
            "Exact XOR, rank, cofactor/complement, and Kronecker artifacts passed reconstruction "
            "on Yosys and hard controls; explicit CM was marginally fastest, so no timing replication followed.")}
    write(DOCS / D10_MACHINE, d10_machine)
    write(DOCS / C15_MACHINE, c15_machine)
    data = load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])]
            != [f"R{index:02d}" for index in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing register update: 18-track or 8-application shape changed")
    tracks = {track["id"]: track for track in data["tracks"]}
    d10_scope = ("Four exhaustively proved mux, comparator, carry, and XOR-cancellation rules now "
                 "have indexed screening, strict decrease, provenance, and exact versioned cache replay; "
                 "whole-path profitability was negative.")
    c15_scope = ("Exact bounded CM/GF(2) artifacts now cover recursive XOR components, matrix rank, "
                 "complemented cofactor blocks, and Kronecker factors with full reconstruction on a "
                 "40-case Yosys source family and dense negatives.")
    for track_id in ("R03", "R04", "R05"):
        upsert(tracks[track_id], D10_REPORT, D10_MACHINE, d10_scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = d10_scope
    tracks["R03"]["next_experiment"] = "Seek larger natural contractions with positive downstream oracle headroom before enabling the indexed runtime path."
    tracks["R04"]["next_experiment"] = "Use no-rewrite as the default; schedule only after a natural candidate beats it end to end under advice-off control."
    tracks["R05"]["next_experiment"] = "Extend the inert pack only with independently proved rules whose natural occurrences and downstream savings are measured."
    upsert(tracks["R06"], C15_REPORT, C15_MACHINE, c15_scope)
    tracks["R06"]["status"] = "measured"
    tracks["R06"]["status_reason"] = c15_scope
    tracks["R06"]["next_experiment"] = "Rank bounded candidate partitions on larger source cones, reconstruct every proposal exactly, and retain exhaustive-budget and advice-off controls."
    for track_id in ("R16", "R18"):
        upsert(tracks[track_id], D10_REPORT, D10_MACHINE, d10_scope)
        upsert(tracks[track_id], C15_REPORT, C15_MACHINE, c15_scope)
    tracks["R16"]["next_experiment"] = "Reduce or amortize common GF(2) analysis cost before fitting any partition policy; charge screening, reconstruction, and reload."
    tracks["R18"]["next_experiment"] = "Retain no-rewrite, advice-off, dense-incompressible, near-match, changed-version, and exact-reconstruction controls."
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    upsert(hardware, D10_REPORT, D10_MACHINE, d10_scope)
    upsert(hardware, C15_REPORT, C15_MACHINE, c15_scope)
    data["milestones"]["D"] = (
        "D10 indexed four-rule engine and C15 exact CM/GF(2) decomposition measured; exact "
        "infrastructure passes, both timing promotion gates fail, and production remains disabled")
    data["updated"] = "2026-08-30"
    write(REGISTER, data)
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "updated_tracks": ["R03", "R04", "R05", "R06", "R16", "R18"],
        "milestones": ["D10", "C15"], "exact": True, "runpod_used": False,
        "runpod_cost_usd": 0.0}, sort_keys=True))


if __name__ == "__main__":
    main()
