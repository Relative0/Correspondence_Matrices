"""Apply the frozen W4 MAD/median rule to the verified timing scout."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import statistics


HERE = Path(__file__).resolve().parent
RUN = HERE / "p7-w4-timing-v2-retry-001/evidence/run-output"
AUDIT = HERE / "P7-W4-TIMING-FINAL-INDEPENDENT-AUDIT.json"
SELECTION = HERE.parents[5] / "docs/research/verification/comparative-p7-w4-timing-scout-v1-2026-08-31/selection.json"
OUTPUT = HERE / "P7-W4-TIMING-NOISE-ANALYSIS.json"
THRESHOLD_PPM = 50_000
POLICIES = {
    "p7-ir": {"blocks": 8, "baseline": "cm-ir-current", "arms": 4},
    "p7-relation": {"blocks": 10, "baseline": "cm-dense", "arms": 5},
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def median_mad_ppm(values: list[int] | list[float]) -> dict:
    if not values or any(type(value) not in (int, float) or value <= 0 for value in values):
        raise ValueError("MAD sample must be finite positive values")
    center = float(statistics.median(values))
    mad = float(statistics.median(abs(value - center) for value in values))
    return {"n": len(values), "median": center, "mad": mad, "mad_over_median_ppm": mad / center * 1_000_000}


def terminal_rows(policy: str) -> list[dict]:
    root = RUN / policy
    plan = load(root / "plan.json")
    cells = {row["cell_id"]: row for row in plan["cells"]}
    terminal = {}
    for segment in sorted((root / "ledger").glob("segment-*.jsonl")):
        for line in segment.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("status") != "running":
                terminal[row["cell_id"]] = row
    if set(terminal) != set(cells):
        raise ValueError("noise analysis ledger/plan mismatch")
    result = []
    for cell_id, cell in cells.items():
        record = terminal[cell_id]["result"]
        if record.get("status") != "ok" or record.get("performance_measurement") is not True:
            raise ValueError("noise analysis requires successful performance cells")
        result.append({
            "case_id": cell["case_id"],
            "arm": cell["arm"],
            "block": cell["block"],
            "task_total_wall_ns": record["timings_ns"]["task_total_wall_ns"],
        })
    return result


def summarize(policy: str, rows: list[dict], origins: dict[str, str]) -> dict:
    spec = POLICIES[policy]
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["case_id"], row["arm"])].append(row["task_total_wall_ns"])
    if len(grouped) != 12 * spec["arms"] or any(len(values) != spec["blocks"] for values in grouped.values()):
        raise ValueError("noise case/arm/block coverage mismatch")

    case_arms = []
    for (case_id, arm), values in sorted(grouped.items()):
        summary = median_mad_ppm(values)
        case_arms.append({
            "case_id": case_id,
            "origin": origins[case_id],
            "arm": arm,
            **summary,
            "exceeds_threshold": summary["mad_over_median_ppm"] > THRESHOLD_PPM,
        })

    by_key = {(row["case_id"], row["block"], row["arm"]): row["task_total_wall_ns"] for row in rows}
    arms = sorted({row["arm"] for row in rows})
    paired = []
    for case_id in sorted({row["case_id"] for row in rows}):
        for candidate in arms:
            if candidate == spec["baseline"]:
                continue
            ratios = [
                by_key[(case_id, block, candidate)] / by_key[(case_id, block, spec["baseline"])]
                for block in range(spec["blocks"])
            ]
            summary = median_mad_ppm(ratios)
            paired.append({
                "case_id": case_id,
                "origin": origins[case_id],
                "baseline": spec["baseline"],
                "candidate": candidate,
                **summary,
                "exceeds_threshold": summary["mad_over_median_ppm"] > THRESHOLD_PPM,
            })

    normalized_by_block = defaultdict(list)
    for (case_id, arm), values in grouped.items():
        center = statistics.median(values)
        for block, value in enumerate(values):
            normalized_by_block[block].append(value / center)
    block_drift = {
        str(block): float(statistics.median(values))
        for block, values in sorted(normalized_by_block.items())
    }
    case_arm_exceeds = [row for row in case_arms if row["exceeds_threshold"]]
    paired_exceeds = [row for row in paired if row["exceeds_threshold"]]
    return {
        "threshold_ppm": THRESHOLD_PPM,
        "blocks": spec["blocks"],
        "case_arm_units": len(case_arms),
        "case_arm_units_exceeding_threshold": len(case_arm_exceeds),
        "case_arm_units_within_threshold": len(case_arms) - len(case_arm_exceeds),
        "case_arm_exceeding_by_origin": {
            origin: sum(row["origin"] == origin for row in case_arm_exceeds)
            for origin in ("synthetic", "natural")
        },
        "max_case_arm_mad_over_median_ppm": max(row["mad_over_median_ppm"] for row in case_arms),
        "paired_ratio_units": len(paired),
        "paired_ratio_units_exceeding_threshold": len(paired_exceeds),
        "max_paired_ratio_mad_over_median_ppm": max(row["mad_over_median_ppm"] for row in paired),
        "minimum_blocks_all_case_arms_below_threshold": not case_arm_exceeds,
        "conditional_extension_indicated_by_frozen_rule": bool(case_arm_exceeds),
        "normalized_block_medians": block_drift,
        "normalized_block_median_min": min(block_drift.values()),
        "normalized_block_median_max": max(block_drift.values()),
        "case_arm_details": case_arms,
        "paired_ratio_details": paired,
    }


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    audit = load(AUDIT)
    if audit.get("verified") is not True or audit.get("combined", {}).get("verified_primary_cells") != 984:
        raise ValueError("verified W4 audit required")
    origins = {row["case_id"]: row["origin"] for row in load(SELECTION)["cases"]}
    policies = {policy: summarize(policy, terminal_rows(policy), origins) for policy in POLICIES}
    result = {
        "schema": "cm-runpod-p7-w4-timing-noise-analysis/v1",
        "audit_sha256": sha256(AUDIT),
        "metric": "task_total_wall_ns",
        "rule": "mad_over_median",
        "threshold_ppm": THRESHOLD_PPM,
        "policies": policies,
        "any_conditional_extension_indicated": any(
            row["conditional_extension_indicated_by_frozen_rule"] for row in policies.values()
        ),
        "performance_measurement": True,
        "principal_p7_result": False,
        "verified": True,
    }
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(OUTPUT)
    print(json.dumps({
        "policies": {
            policy: {
                "case_arm_units_exceeding_threshold": row["case_arm_units_exceeding_threshold"],
                "paired_ratio_units_exceeding_threshold": row["paired_ratio_units_exceeding_threshold"],
                "normalized_block_median_range": [
                    row["normalized_block_median_min"], row["normalized_block_median_max"]
                ],
            }
            for policy, row in policies.items()
        },
        "any_conditional_extension_indicated": result["any_conditional_extension_indicated"],
        "verified": True,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
