"""Register verified CRSE Milestones D6 and D7 without dropping any track."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "recognition"
REGISTER = DOCS / "experiment_register.json"
D6_REPORT = "NATURAL_REVISION_CACHE_MILESTONE_D6_2026_08_29.md"
D6_MACHINE = "natural_revision_cache_milestone_d6_results.json"
D7_REPORT = "NATURAL_NORMALIZATION_MILESTONE_D7_2026_08_29.md"
D7_MACHINE = "natural_normalization_milestone_d7_results.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def _summaries() -> None:
    d6 = _load(DOCS / "runs" / "natural-revision-20260829-001" / "summary.json")
    d6v = _load(DOCS / "verification" / "natural-revision-20260829-001.json")
    d7 = _load(DOCS / "runs" / "natural-normalization-20260829-001" / "summary.json")
    d7v = _load(DOCS / "verification" / "natural-normalization-20260829-001.json")
    if any(item.get("status") not in ("complete", "pass") for item in (d6, d6v, d7, d7v)):
        raise SystemExit("refusing registration: a run or verification did not complete")
    _write_new(DOCS / D6_MACHINE, {"schema": "crse-natural-revision-cache-milestone-d6-summary/v1",
        "date": "2026-08-29", "status": "complete",
        "run": "docs/recognition/runs/natural-revision-20260829-001", "report": D6_REPORT,
        "verification": {"path": "docs/recognition/verification/natural-revision-20260829-001.json", **d6v},
        "data": {"cases": d6["source_selection"]["selected_case_count"],
            "histories": len(d6["source_selection"]["histories"]),
            "transitions": len(d6["source_selection"]["transition_ids"]),
            "widths": [8, 12, 16], "source_commit": d6["source_selection"]["source_commit"],
            "claim_boundary": d6["source_selection"]["claim_boundary"]},
        "timing": d6["summaries"], "criteria": d6["criteria"],
        "semantic_mismatches": d6["semantic_mismatches"],
        "interpretation": "Exact source reuse produced 41 hits and 79 invalidations on actual adjacent feature-model revisions. It was 1.015x over fresh CM but only 0.091x versus direct conditioned-CNF evaluation."})
    _write_new(DOCS / D7_MACHINE, {"schema": "crse-natural-normalization-milestone-d7-summary/v1",
        "date": "2026-08-29", "status": "complete",
        "run": "docs/recognition/runs/natural-normalization-20260829-001", "report": D7_REPORT,
        "verification": {"path": "docs/recognition/verification/natural-normalization-20260829-001.json", **d7v},
        "pack": d7["pack"],
        "data": {"cases": d7["config"]["case_count"], "kernel_repeats": 128,
            "max_passes": d7["config"]["max_passes"], "training_use": False,
            "independent_confirmation": False},
        "timing": d7["summaries"], "criteria": d7["criteria"],
        "semantic_mismatches": d7["semantic_mismatches"],
        "interpretation": "Fixpoint exposed 18 factoring applications and was exact, but achieved only 0.805x versus no rewrite and 0.766x versus one pass. The one-pass 128-use arm achieved 1.050x on the reused D5 slice."})


D6_UPDATES = {
    "R04": ("measured", "On 120 bounded cases from actual adjacent feature-model revisions, exact source caching was 1.015x over fresh CM but only 0.091x versus direct conditioned-CNF evaluation.", "Retain direct CNF as the configuration baseline and test cache scheduling only where source identity predicts material compile cost."),
    "R09": ("measured", "Actual related configuration revisions produced 41 exact source hits and 79 required invalidations across 20 transitions and seven histories, with zero result errors.", "Add a continuous revision sequence with additions, deletions and reverts under one stable feature-domain selection policy."),
    "R16": ("measured", "Exact canonical identity cost only 3.089 ms, but the 41 safe hits were cheap cases and removed little CM compilation time.", "Predict saved compile work from safe pre-execution structure rather than hit likelihood alone."),
    "R18": ("measured", "Seventy-six equal-output cases had changed source bytes and were refused as cache hits, preventing output equality from becoming circular correctness authority.", "Retain semantic-only equality as a mandatory unsafe-oracle control in every revision-cache experiment."),
}

D7_UPDATES = {
    "R03": ("measured", "Bounded fixpoint normalization exposed 18 common-factor contractions after De Morgan lowering while preserving all exact outputs.", "Seek an independently sourced natural factoring or mux corpus before extending the proved pack."),
    "R04": ("measured", "At the frozen 128-execution policy one pass achieved 1.050x over no rewrite on the reused D5 slice, while fixpoint achieved only 0.805x.", "Confirm the one-pass high-reuse policy on Linux or a new source; do not schedule fixpoint on this evidence."),
    "R05": ("measured", "Multi-pass execution now requires strict expanded-AST decrease, exact cycle detection, finite pass/application caps, and supports overlap refusal.", "Add general semantic-overlap admission only when proposed rules extend beyond the fixed audited pack."),
    "R18": ("measured", "The exact second pass was a negative profitability result despite 18 additional reductions; partial results, cycles, pass exhaustion and refused overlap have explicit controls.", "Keep fixpoint as a negative control and report convergence-scan cost separately in future rule-pack work."),
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
    data = _load(REGISTER)
    if ([track["id"] for track in data.get("tracks", [])] != [f"R{i:02d}" for i in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer contains exact R01-R18 and eight applications")
    by_id = {track["id"]: track for track in data["tracks"]}
    for track_id, update in D6_UPDATES.items():
        _append(by_id[track_id], D6_REPORT, D6_MACHINE, update)
    for track_id, update in D7_UPDATES.items():
        _append(by_id[track_id], D7_REPORT, D7_MACHINE, update)
    configuration = next(item for item in data["applications"]
                         if item["name"] == "Configuration/product families")
    configuration["status"] = "measured"
    configuration["results"].append({"report": D6_REPORT, "machine_summary": D6_MACHINE,
        "scope": "Twenty actual adjacent feature-model transitions yielded 120 exact bounded revision cases, with 41 safe source hits, 79 invalidations and zero mismatches; direct CNF remained about 10.94x faster than cached CM."})
    hardware = next(item for item in data["applications"]
                    if item["name"] == "Hardware verification/design")
    hardware["results"].append({"report": D7_REPORT, "machine_summary": D7_MACHINE,
        "scope": "Bounded fixpoint normalization exposed 18 later factoring applications on the reused D5 EPFL slice but was slower than one pass and no rewrite; this is exploratory, not confirmation."})
    data["updated"] = "2026-08-29"
    REGISTER.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "d6_tracks": sorted(D6_UPDATES), "d7_tracks": sorted(D7_UPDATES)}))


if __name__ == "__main__":
    main()
