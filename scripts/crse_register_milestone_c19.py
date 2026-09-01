"""Register the verified C19 cheap exact GF(2) work-policy milestone."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
RUN = DOCS / "runs/c19-logikbench-cheap-work-policy-windows-20260831-001"
REGISTER = DOCS / "experiment_register.json"
REPORT = "LEARNING_MILESTONE_C19_CHEAP_GF2_WORK_POLICY_2026_08_31.md"
MACHINE = "learning_milestone_c19_cheap_gf2_work_policy_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def upsert(container: dict, scope: str) -> None:
    value = {"report": REPORT, "machine_summary": MACHINE, "scope": scope}
    rows = [row for row in container["results"] if row.get("report") == REPORT]
    if len(rows) > 1:
        raise SystemExit("duplicate C19 registration")
    if rows:
        rows[0].update(value)
    else:
        container["results"].append(value)


def main() -> None:
    result = load(RUN / "results.json")
    verify = load(RUN / "independent_verification.json")
    corpus = load(DOCS / "c19_logikbench_small_cone_verification.json")
    policy = load(RUN / "policy.json")
    selected = result["confirmation"]["methods"]["c19_selected"]
    direct = result["confirmation"]["methods"]["direct_screened"]
    if (
        not (DOCS / REPORT).is_file()
        or result.get("status") != "complete"
        or result.get("semantic_or_artifact_mismatches") != 0
        or result["functional"].get("all_exact") is not True
        or result["confirmation"].get("gate") is not True
        or result["claims"].get("learned_truth_values") is not False
        or result["claims"].get("exact_arm_selection_only") is not True
        or result["claims"].get("production_promotion") is not False
        or result["dataset"].get("confirmation_policy_refit") is not False
        or verify.get("status") != "verified"
        or verify.get("functional_cases_replayed") != 96
        or verify.get("confirmation_rows_checked") != 720
        or verify.get("policy_rebuilt_from_development_and_validation") is not True
        or corpus.get("status") != "verified"
        or corpus.get("cases_replayed") != 96
        or corpus.get("split_cluster_overlap") != 0
        or policy.get("selected_candidate") != "learned_stump"
        or policy.get("tree") != {"kind": "leaf", "arm": "explicit_cm_screened"}
    ):
        raise SystemExit("refusing C19 registration: evidence incomplete")

    machine = {
        "schema": "crse-learning-milestone-c19-cheap-gf2-work-policy-summary/v1",
        "date": "2026-08-31",
        "status": "phase_separated_exact_policy_confirmation_passed",
        "report": REPORT,
        "run": str(RUN.relative_to(ROOT)).replace("\\", "/"),
        "corpus": {
            "dataset": "docs/recognition/c19_logikbench_small_cone_dataset.json",
            "source_inventory": "docs/recognition/c19_logikbench_small_cone_inventory.json",
            "source_verification": "docs/recognition/c19_logikbench_small_cone_verification.json",
            "family": "LogikBench",
            "cases": 96,
            "development": 48,
            "validation": 24,
            "confirmation": 24,
            "split_cluster_overlap": 0,
            "prior_truth_overlaps": 0,
        },
        "policy": {
            "path": str((RUN / "policy.json").relative_to(ROOT)).replace("\\", "/"),
            "selected_candidate": policy["selected_candidate"],
            "tree": policy["tree"],
            "policy_sha256": policy["policy_sha256"],
            "learned_truth_values": False,
            "exact_arm_selection_only": True,
            "confirmation_policy_refit": False,
        },
        "validation": result["validation"],
        "confirmation": result["confirmation"],
        "measurement_rows": {"development": 480, "validation": 840, "confirmation": 720},
        "verification": {
            "path": str((RUN / "independent_verification.json").relative_to(ROOT)).replace("\\", "/"),
            **verify,
        },
        "semantic_or_artifact_mismatches": 0,
        "runpod": result["runpod"],
        "production_promotion": False,
        "interpretation": (
            f"A pre-confirmation fitted candidate collapsed to an always-screened exact leaf and "
            f"passed the fresh LogikBench confirmation gate at "
            f"{selected['aggregate_speedup_over_exhaustive']:.3f}x aggregate and "
            f"{selected['minimum_case_speedup_over_exhaustive']:.3f}x minimum. Direct screened "
            f"reached {direct['aggregate_speedup_over_exhaustive']:.3f}x, exposing removable "
            "generic policy overhead. One-machine scope and the prior VTR slow tail prevent promotion."
        ),
    }
    write(DOCS / MACHINE, machine)

    data = load(REGISTER)
    if (
        [row["id"] for row in data.get("tracks", [])] != [f"R{index:02d}" for index in range(1, 19)]
        or len(data.get("applications", [])) != 8
    ):
        raise SystemExit("refusing C19 update: 18-track or 8-application shape changed")
    tracks = {row["id"]: row for row in data["tracks"]}
    scope = (
        "C19 fit exact-arm cost policies on 48 LogikBench cones, selected on 24 source-cluster-"
        "disjoint validation cones, froze an always-screened leaf, and confirmed exact 2.769x "
        "aggregate / 0.972x minimum performance on 24 untouched cones. Production remains disabled."
    )
    for track_id in ("R01", "R06", "R16", "R17", "R18"):
        upsert(tracks[track_id], scope)
        tracks[track_id]["status"] = "measured"
        tracks[track_id]["status_reason"] = scope
    tracks["R01"]["next_experiment"] = (
        "Constant-fold the frozen leaf to a direct screened call and measure it without retuning on repeated VTR data."
    )
    tracks["R06"]["next_experiment"] = (
        "Run a frozen-policy second-machine confirmation with the same row and cleanup bounds."
    )
    tracks["R16"]["next_experiment"] = (
        "Compile constant policy trees so leaf decisions do not pay feature extraction or generic tree traversal."
    )
    tracks["R17"]["next_experiment"] = (
        "Treat the C19 confirmation as sealed; use separate data for any policy or compiler promotion decision."
    )
    tracks["R18"]["next_experiment"] = (
        "Retain the C18 VTR small-case tail and direct screened arm as mandatory no-regret controls."
    )
    hardware = next(item for item in data["applications"] if item["name"] == "Hardware verification/design")
    upsert(hardware, scope)
    data["milestones"]["C"] = (
        "C19 verifies a phase-separated exact screened-arm cost policy on LogikBench; compile-time "
        "constant folding, VTR tail remediation, and second-machine confirmation remain"
    )
    data["updated"] = "2026-08-31"
    write(REGISTER, data)
    print(json.dumps({
        "tracks": len(data["tracks"]),
        "applications": len(data["applications"]),
        "updated_tracks": ["R01", "R06", "R16", "R17", "R18"],
        "milestone": "C19",
        "production_promotion": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
