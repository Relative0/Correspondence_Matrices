"""Record Milestone D3 while preserving exact R01-R18 and all applications."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs" / "recognition" / "experiment_register.json"
REPORT = "VERSIONED_RULE_CACHE_MILESTONE_D3_2026_08_29.md"
MACHINE = "versioned_rule_cache_milestone_d3_results.json"

UPDATES = {
    "R03": ("measured",
        "The fixed proved macro boundary now contains two rules: the specific AIG-XOR macro and a general De Morgan OR macro. Deterministic priority resolves their intentional overlap, with eight proof rows and zero output errors.",
        "Add a nonoverlapping factoring or mux rule and test multi-step normalization and loop refusal."),
    "R04": ("measured",
        "Persistent exact structural caching was 2.08-2.11x faster than fresh rematching on sparse changed versions and 1.382x faster over the cold-plus-two-change sequence. It still lost to no rewrite, so no scheduler is promoted.",
        "Freeze a cheap skip/apply profitability rule and confirm it on unseen version histories with no-rewrite retained."),
    "R05": ("measured",
        "A strict two-rule pack now records proof rows, hashes, fixed priority and overlap accounting. It selects only built-in matchers; learned rule discovery, duplicate semantic detection and larger conflict graphs remain pending.",
        "Add bounded normalization-loop, duplicate-rule and semantic-overlap refusal tests before any proposed-rule ingestion."),
    "R09": ("measured",
        "Three related DAG versions now use stable cone IDs, exact canonical source identity and changed-cone invalidation. Each sparse transition produced 28 hits, four invalidations, 56 reused applications and zero stale results.",
        "Repeat on actual related revisions with additions, deletions, reverts and serialized cache provenance."),
    "R16": ("measured",
        "Canonical identity, cache, matching, CSE build and kernel costs are separated. Cache hits halved fresh rematching time on changed versions, but identity and rewrite overhead kept the cached sequence 3.03x slower than no rewrite.",
        "Add a pre-identity skip gate and compare full canonical bytes with a bounded incremental structural-ID scheme."),
    "R18": ("measured",
        "Cold-cache overhead and the no-rewrite arm remain explicit negative controls. Exact hashing plus byte equality prevents stale or collision-only hits; all eight declared changed cones invalidated exactly.",
        "Add adversarial pack changes, removed cones, reverts, digest collisions via injected test doubles, and cache-capacity refusal."),
}


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    if ([track["id"] for track in data.get("tracks", [])] != [f"R{i:02d}" for i in range(1, 19)]
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer contains exact R01-R18 and eight applications")
    result = {"report": REPORT, "machine_summary": MACHINE}
    for track in data["tracks"]:
        if track["id"] not in UPDATES:
            continue
        if any(item.get("report") == REPORT for item in track["results"]):
            raise SystemExit(f"Milestone D3 already registered for {track['id']}")
        status, reason, next_experiment = UPDATES[track["id"]]
        track["status"] = status
        track["status_reason"] = reason
        track["next_experiment"] = next_experiment
        track["results"].append({**result, "scope": reason})
    hardware = next(application for application in data["applications"]
                    if application["name"] == "Hardware verification/design")
    if any(item.get("report") == REPORT for item in hardware["results"]):
        raise SystemExit("Milestone D3 already registered for hardware application")
    hardware["status"] = "measured"
    hardware["results"].append({**result,
        "scope": "Generated hardware-style related DAG cones demonstrated exact two-rule overlap priority, structural cache hits and changed-cone invalidation; natural version histories remain pending."})
    data["updated"] = "2026-08-29"
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"tracks": len(data["tracks"]), "applications": len(data["applications"]),
                      "updated_tracks": sorted(UPDATES), "hardware_status": hardware["status"]}))


if __name__ == "__main__":
    main()
