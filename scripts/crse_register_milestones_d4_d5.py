"""Record CRSE Milestones D4/D5 while preserving R01-R18 and all applications."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
REGISTER = DOCS / "experiment_register.json"

D4_REPORT = "RULE_PROFITABILITY_MILESTONE_D4_2026_08_29.md"
D4_MACHINE = "rule_profitability_milestone_d4_results.json"
D4_RUN = DOCS / "runs" / "rule-profitability-20260829-002" / "summary.json"
D4_VERIFY = DOCS / "verification" / "rule-profitability-20260829-002.json"

D5_REPORT = "NATURAL_RULE_PROFITABILITY_MILESTONE_D5_2026_08_29.md"
D5_MACHINE = "natural_rule_profitability_milestone_d5_results.json"
D5_RUN = DOCS / "runs" / "natural-rule-20260829-001" / "summary.json"
D5_VERIFY = DOCS / "verification" / "natural-rule-20260829-001.json"


def _write_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def _summaries() -> None:
    d4 = json.loads(D4_RUN.read_text(encoding="utf-8"))
    d4v = json.loads(D4_VERIFY.read_text(encoding="utf-8"))
    d4_summary = {"schema": "crse-rule-profitability-milestone-d4-summary/v1",
        "date": "2026-08-29", "status": d4["status"],
        "run": "docs/recognition/runs/rule-profitability-20260829-002",
        "report": D4_REPORT,
        "verification": {"path": "docs/recognition/verification/rule-profitability-20260829-002.json",
                         **d4v},
        "pack": d4["pack"],
        "data": {"versions": 4, "cones_per_version": d4["config"]["cone_count"],
                 "reuse_schedule": [1, 8, 32, 128],
                 "changes": {key: value["changed_count"] for key, value in d4["dataset"]["versions"].items()},
                 "source": "generated related DAGs with modifications, additions, removals, and reverts"},
        "timing": d4["summaries"], "hardening": d4["hardening"], "criteria": d4["criteria"],
        "semantic_mismatches": d4["semantic_mismatches"],
        "interpretation": "The gate removed much of fresh-matcher overhead but remained slower than no rewrite; the free cached oracle exposed only 1.7% generated headroom."}
    _write_new(DOCS / D4_MACHINE, d4_summary)

    d5 = json.loads(D5_RUN.read_text(encoding="utf-8"))
    d5v = json.loads(D5_VERIFY.read_text(encoding="utf-8"))
    d5_summary = {"schema": "crse-natural-rule-profitability-milestone-d5-summary/v1",
        "date": "2026-08-29", "status": d5["status"],
        "run": "docs/recognition/runs/natural-rule-20260829-001",
        "report": D5_REPORT,
        "verification": {"path": "docs/recognition/verification/natural-rule-20260829-001.json",
                         **d5v},
        "pack": d5["pack"],
        "data": {"cases": d5["config"]["case_count"], "eligible": d5["selection"]["eligible_count"],
                 "circuits": len(set(d5["selection"]["selected_circuits"])),
                 "support_range": d5["selection"]["support_range"], "sessions": 3,
                 "reuse_schedule": [1, 8, 32, 128], "training_use": False,
                 "prior_epfl_slices_overlap": d5["selection"]["prior_epfl_slices_overlap"]},
        "timing": d5["summaries"], "criteria": d5["criteria"],
        "semantic_mismatches": d5["semantic_mismatches"],
        "interpretation": "The gated cache achieved a small 1.030x three-session gain on sealed natural cones. Cold use lost, warm sessions gained 1.156-1.168x, and only the 128-execution stratum was clearly profitable."}
    _write_new(DOCS / D5_MACHINE, d5_summary)


D4_UPDATES = {
    "R03": ("measured", "A third common-factor contraction is proved over three metavariables. The fixed pack now has 16 exhaustive rows, exact sharing-aware matching, and strictly decreasing rewrites.", "Add multi-pass normalization with loop refusal and a natural mux or factoring source where the third rule actually occurs."),
    "R04": ("measured", "A fixed reuse-and-size gate was 1.366x faster than fresh matching and 1.145x faster than ungated caching on generated versions, but remained 0.891x versus no rewrite.", "Use the frozen gate on a sealed natural source and retain the no-rewrite boundary."),
    "R05": ("measured", "The v2 pack fixes priority, rejects malformed or duplicate identities, and requires a strict operator-count decrease. General semantic-overlap admission remains pending.", "Add bounded multi-pass cycle detection and semantic-overlap refusal before accepting any proposed rule."),
    "R09": ("measured", "Generated versions now include additions, removals, exact reverts, and serialized cache reload with exact pack/source provenance.", "Repeat the same contract on actual related revisions rather than generated version histories."),
    "R16": ("measured", "The pre-identity gate skips all canonicalization and matching for low-reuse cones. It reduces overhead substantially but cannot create savings where the generated oracle headroom is only 1.7%.", "Compare canonical bytes with a bounded incremental structural ID on actual version histories."),
    "R18": ("measured", "Forced digest collisions, pack changes, cache-capacity overflow, removed cones, reverts, and low-oracle-headroom workloads are explicit checked controls.", "Add incompressible and anti-reduction natural controls while retaining exact refusal behavior."),
}

D5_UPDATES = {
    "R01": ("measured", "A deterministic task/reuse/size gate was evaluated on a sealed natural hardware source. It produced a small 1.030x total gain across three sessions, with cold-session loss and warm-session gains.", "Freeze the observed high-reuse policy without tuning on D5, then confirm it on an independent source or machine with tail-risk reporting."),
    "R03": ("measured", "The proved pack found 18 XOR and 433 De Morgan applications in 32 natural EPFL cones; the common-factor rule had zero incidence in the raw AND/INV language.", "Add a multi-pass or post-lowering factoring experiment and a natural mux source with exact provenance."),
    "R04": ("measured", "The frozen D4 gate achieved 1.030x over no rewrite on three natural sessions. Cold session was 0.834x, warm sessions were 1.156-1.168x, and the 128-use stratum was 1.167x.", "Predeclare a 128-use/high-support gate and confirm it without tuning on a new natural source or Linux replication."),
    "R09": ("measured", "Natural repeated sessions produced exact warm cache hits for the eligible half of 32 cones. These are repeated identical sessions, not changed circuit revisions.", "Acquire or identify provenance-reviewed related hardware/configuration revisions and test additions, deletions, and reverts."),
    "R16": ("measured", "On natural cones the gate was 1.517x faster than fresh matching while preserving exact outputs; its one-shot cold cost remains visible.", "Measure incremental structural identity and serialized warm-start cost on actual revision histories."),
    "R18": ("measured", "Natural one- and eight-use strata remained overhead dominated, 32 uses also lost, and only 128 uses clearly won. No aggregate hides these negative strata.", "Retain these strata as fixed negative controls for the next confirmation run."),
}


def _append(track: dict, report: str, machine: str, update: tuple[str, str, str]) -> None:
    if any(item.get("report") == report for item in track["results"]):
        raise SystemExit(f"report already registered for {track['id']}: {report}")
    status, reason, next_experiment = update
    track["status"] = status
    track["status_reason"] = reason
    track["next_experiment"] = next_experiment
    track["results"].append({"report": report, "machine_summary": machine, "scope": reason})


def main() -> None:
    _summaries()
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    if ([track["id"] for track in data.get("tracks", [])] != [f"R{i:02d}" for i in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer contains exact R01-R18 and eight applications")
    by_id = {track["id"]: track for track in data["tracks"]}
    for track_id, update in D4_UPDATES.items():
        _append(by_id[track_id], D4_REPORT, D4_MACHINE, update)
    for track_id, update in D5_UPDATES.items():
        _append(by_id[track_id], D5_REPORT, D5_MACHINE, update)
    hardware = next(item for item in data["applications"]
                    if item["name"] == "Hardware verification/design")
    if any(item.get("report") == D5_REPORT for item in hardware["results"]):
        raise SystemExit("Milestone D5 already registered for hardware application")
    hardware["status"] = "measured"
    hardware["results"].append({"report": D5_REPORT, "machine_summary": D5_MACHINE,
        "scope": "A sealed 32-cone, 15-circuit EPFL slice at support 9-12 measured exact cold and warm proved-rule reuse. The gated three-session sequence achieved 1.030x over no rewrite; no production promotion follows from one machine."})
    data["updated"] = "2026-08-29"
    REGISTER.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "d4_tracks": sorted(D4_UPDATES), "d5_tracks": sorted(D5_UPDATES)}))


if __name__ == "__main__":
    main()
