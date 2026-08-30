"""Register independently verified C13 and C14 exact-dispatcher results."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/recognition"
REGISTER = DOCS / "experiment_register.json"
C13_RUN = DOCS / "runs/in-kernel-tail-sentinel-20260830-003"
C13_VERIFY = DOCS / "verification/in-kernel-tail-sentinel-20260830-003.json"
C13_REPORT = "LEARNING_MILESTONE_C13_IN_KERNEL_TAIL_SENTINEL_2026_08_30.md"
C13_MACHINE = "learning_milestone_c13_in_kernel_sentinel_results.json"
C14_RUN = DOCS / "runs/task-guard-shadow-20260830-001"
C14_VERIFY = DOCS / "verification/task-guard-shadow-20260830-001.json"
C14_REPORT = "LEARNING_MILESTONE_C14_TASK_GUARD_SHADOW_2026_08_30.md"
C14_MACHINE = "learning_milestone_c14_task_guard_results.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def write_json(path: Path, value) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                                allow_nan=False).encode("utf-8") + b"\n")


def upsert_result(container: dict, report: str, machine: str, scope: str) -> None:
    result = {"report": report, "machine_summary": machine, "scope": scope}
    existing = [row for row in container["results"] if row.get("report") == report]
    if len(existing) > 1:
        raise SystemExit(f"duplicate registration for {report}")
    if existing:
        existing[0].update(result)
    else:
        container["results"].append(result)


def main() -> None:
    c13, c13_verify = load(C13_RUN / "summary.json"), load(C13_VERIFY)
    c14, c14_verify = load(C14_RUN / "summary.json"), load(C14_VERIFY)
    if (not (DOCS / C13_REPORT).is_file() or not (DOCS / C14_REPORT).is_file()
            or c13.get("status") != "complete" or c13.get("semantic_mismatches") != 0
            or c13.get("measurement_rows") != 11280
            or c13.get("criteria", {}).get("exact") is not True
            or c13.get("criteria", {}).get("dense_tail_guard") is not True
            or c13.get("criteria", {}).get("sparse_no_material_regret") is not False
            or c13.get("criteria", {}).get("local_engineering_gate") is not False
            or c13.get("criteria", {}).get("production_promotion") is not False
            or c13_verify.get("status") != "pass"
            or c13_verify.get("timing_samples_checked") != 11280
            or c13_verify.get("semantic_mismatches") != 0
            or c14.get("status") != "complete" or c14.get("semantic_mismatches") != 0
            or c14.get("measurement_rows") != 4104
            or c14.get("criteria", {}).get("exact") is not True
            or c14.get("criteria", {}).get("shadow_exact") is not True
            or c14.get("criteria", {}).get("local_task_guard_gate") is not True
            or c14.get("criteria", {}).get("production_promotion") is not False
            or c14_verify.get("status") != "pass"
            or c14_verify.get("timing_samples_checked") != 4104
            or c14_verify.get("semantic_mismatches") != 0):
        raise SystemExit("refusing C13/C14 registration: evidence is incomplete")

    c13_machine = {
        "schema": "crse-learning-milestone-c13-in-kernel-sentinel-summary/v1",
        "date": "2026-08-30", "status": "complete",
        "report": C13_REPORT, "run": relative(C13_RUN),
        "verification": {"path": relative(C13_VERIFY), **c13_verify},
        "product_pair_budget": c13["product_pair_budget"],
        "evaluation_cases": c13["evaluation_cases"],
        "measurement_rows": c13["measurement_rows"],
        "split_summary": c13["split_summary"], "criteria": c13["criteria"],
        "semantic_mismatches": 0, "production_promotion": False,
        "runpod": {"used": False, "cost_usd": 0.0,
                   "reason": "Windows-first local engineering gate failed"},
        "interpretation": (
            "The in-kernel sentinel remained exact and improved the dense C6 tail, "
            "but sparse no-switch overhead failed the no-material-regret gate."
        ),
    }
    write_json(DOCS / C13_MACHINE, c13_machine)
    c14_machine = {
        "schema": "crse-learning-milestone-c14-task-guard-summary/v1",
        "date": "2026-08-30", "status": "complete",
        "report": C14_REPORT, "run": relative(C14_RUN),
        "verification": {"path": relative(C14_VERIFY), **c14_verify},
        "frozen_policy": relative(C14_RUN / "frozen_task_policy.json"),
        "frozen_policy_sha256": c14["frozen_policy_sha256"],
        "evaluation_cases": c14["evaluation_cases"],
        "measurement_rows": c14["measurement_rows"],
        "split_summary": c14["split_summary"], "criteria": c14["criteria"],
        "semantic_mismatches": 0, "production_promotion": False,
        "runpod": {"used": False, "cost_usd": 0.0,
                   "reason": "C14 was a bounded local task-policy and shadow study"},
        "interpretation": (
            "A frozen pre-execution task contract kept throughput inside 3% regret, "
            "retained dense-tail protection for latency tasks, and preserved exact "
            "production/shadow partitions. It remains platform-bound and disabled "
            "for production."
        ),
    }
    write_json(DOCS / C14_MACHINE, c14_machine)

    data = load(REGISTER)
    expected_ids = [f"R{index:02d}" for index in range(1, 19)]
    if ([track["id"] for track in data.get("tracks", [])] != expected_ids
            or len(data.get("applications", [])) != 8):
        raise SystemExit("refusing update: register no longer has R01-R18 and eight applications")
    by_id = {track["id"]: track for track in data["tracks"]}
    c13_scopes = {
        "R01": "The exact in-kernel sentinel improved C6 dense sequence and p95 latency by 19.309x and 28.038x, but failed sparse no-regret on C12 A/B at 0.890x/0.744x.",
        "R03": "Set-prefix reuse and exact packed continuation preserved every canonical source partition across 188 C6/C7/C11/C12 cases.",
        "R06": "All 11,280 sentinel, no-sentinel, advice-off, and measured executions retained exact independent-component partitions.",
        "R16": "A branch-free fast sentinel separated diagnostic counters from execution, but sparse guard cost remained material despite large dense-tail savings.",
        "R18": "The unswitched C7/C11/C12 slices are retained negative controls; six of seven sparse split comparisons were slower than ordinary set ANF.",
    }
    c14_scopes = {
        "R01": "A frozen task contract selected exact set or sentinel arms before execution; throughput stayed within 3% regret and latency retained 27.876x C6 p95 protection.",
        "R03": "Exact bounded shadow execution compared the alternate representation on 684 rows without changing any returned partition.",
        "R16": "Policy, production, shadow, conversion, and exact-check costs were retained separately across 4,104 timing rows.",
        "R17": "Platform mismatch, unsupported task, insufficient reuse, and out-of-range input conservatively abstain or refuse advice; the global switch returns exact set execution.",
        "R18": "Forced latency routing on sparse C12 remained a visible negative control at 0.889x/0.739x rather than being hidden by the successful task gate.",
    }
    next_steps = {
        "R01": "Keep task routing opt-in and begin the bounded task-specific BDD order/compilation comparison.",
        "R03": "Add rule-engine no-op bypass and only pursue motifs with measured downstream headroom.",
        "R06": "Implement recursive disjoint-support, cofactor, complement-block, and GF(2) decomposition with exact reconstruction.",
        "R16": "Charge BDD order search, build, query, save/load, and reuse costs under equal budgets.",
        "R17": "Retain platform-bound abstention and require new-machine calibration before enabling any non-set task arm there.",
        "R18": "Keep sparse no-switch, dense tail, advice-off, and forced-wrong-task controls in future dispatcher studies.",
    }
    for track_id in sorted(set(c13_scopes) | set(c14_scopes)):
        track = by_id[track_id]
        if track_id in c13_scopes:
            upsert_result(track, C13_REPORT, C13_MACHINE, c13_scopes[track_id])
        if track_id in c14_scopes:
            upsert_result(track, C14_REPORT, C14_MACHINE, c14_scopes[track_id])
        track["status"] = "measured"
        track["status_reason"] = (c14_scopes[track_id]
                                  if track_id in c14_scopes else c13_scopes[track_id])
        track["next_experiment"] = next_steps[track_id]
    by_id["R07"]["next_experiment"] = (
        "Run an equal-budget fixed, first-occurrence, interaction, random best-of-k, "
        "and small cost-tree BDD order study with cold and repeated-query objectives."
    )

    hardware = next(item for item in data["applications"]
                    if item["name"] == "Hardware verification/design")
    upsert_result(hardware, C13_REPORT, C13_MACHINE,
                  "An exact in-kernel ANF sentinel improved dense tails but failed sparse no-regret, so universal enablement was refused.")
    upsert_result(hardware, C14_REPORT, C14_MACHINE,
                  "A frozen task guard and exact shadow mode separated throughput from latency-tail policy while preserving all outputs.")
    data["milestones"]["C"] = (
        "C14 task guard and exact shadow complete; C13 dense-tail improvement retained, "
        "sparse sentinel overhead remains negative, production promotion stays disabled"
    )
    data["updated"] = "2026-08-30"
    write_json(REGISTER, data)
    print(json.dumps({
        "tracks": len(data["tracks"]), "applications": len(data["applications"]),
        "registered": ["C13", "C14"], "updated_tracks": sorted(
            set(c13_scopes) | set(c14_scopes)),
        "semantic_mismatches": 0, "production_promotion": False,
        "runpod_used": False, "runpod_cost_usd": 0.0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
