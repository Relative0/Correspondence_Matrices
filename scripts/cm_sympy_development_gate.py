#!/usr/bin/env python3
"""Review the sealed Y02--Y05 study at an instance-level development gate."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.sympy_cm_claim_cleanup import (  # noqa: E402
    arms_for,
    build_contracts,
    canonical_bytes,
    sha256_bytes,
    sha256_json,
)


SOURCE_AUDIT = ROOT / "docs" / "audits" / "2026-09-15-cm-sympy-claim-cleanup"
OUTPUT_AUDIT = ROOT / "docs" / "audits" / "2026-09-15-cm-sympy-development-gate"


LANES = {
    "complete_relation": {
        "family": "Y02",
        "candidate": "cm_packed",
        "incumbents": ("sympy_truth_table",),
    },
    "assignment_batch": {
        "family": "Y03",
        "candidate": "cm_ir_batch",
        "incumbents": ("sympy_lambdify_cse_off", "sympy_lambdify_cse_on"),
    },
    "sat_status": {
        "family": "Y04",
        "candidate": "cm_packed_sat",
        "incumbents": ("sympy_satisfiable", "pysat_tseitin"),
    },
    "equivalence_status": {
        "family": "Y04",
        "candidate": "cm_packed_equivalence",
        "incumbents": ("sympy_difference_sat", "pysat_tseitin_miter"),
    },
    "simplified_expression": {
        "family": "Y05",
        "candidate": "cm_truth_sympy_minimizer",
        "incumbents": ("sympy_simplify_default", "sympy_simplify_forced"),
    },
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n")


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def resolve_workspace_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"path escapes workspace: {value}") from exc
    return path


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def geometric_mean(values: Iterable[float]) -> float:
    values = tuple(values)
    if not values or any(value <= 0 for value in values):
        raise ValueError("geometric mean requires positive observations")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def exact_instance_bootstrap(ratios: list[float]) -> dict[str, Any]:
    """Exact n-out-of-n paired bootstrap over cases, never repetitions."""
    n = len(ratios)
    if not 1 <= n <= 8:
        raise ValueError("unsupported instance count")
    replicates = [
        geometric_mean(ratios[index] for index in indices)
        for indices in itertools.product(range(n), repeat=n)
    ]
    point = geometric_mean(ratios)
    return {
        "independent_instances": n,
        "paired_instance_ratios": ratios,
        "geometric_mean_candidate_over_incumbent": point,
        "geometric_mean_gain_fraction": 1.0 - point,
        "bootstrap_method": "exact_n_out_of_n_paired_instances/v1",
        "bootstrap_replicates": len(replicates),
        "bootstrap_95_percentile_interval": [percentile(replicates, 0.025), percentile(replicates, 0.975)],
    }


def verify_sealed_audit() -> dict[str, Any]:
    manifest = read_json(SOURCE_AUDIT / "AUDIT_MANIFEST.json")
    if manifest.get("complete") is not True:
        raise ValueError("source audit is not complete")
    for record in manifest["files"]:
        path = SOURCE_AUDIT / record["path"]
        if path.stat().st_size != record["bytes"] or file_sha256(path) != record["sha256"]:
            raise ValueError(f"sealed audit hash mismatch: {record['path']}")
    return manifest


def verify_review_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(plan, dict) or set(plan) != {"schema", "review_id", "source_bindings", "decision_rule"}:
        raise ValueError("review plan fields")
    if plan["schema"] != "cm-sympy-development-gate-plan/v1":
        raise ValueError("review plan schema")
    expected_rule = {
        "independent_unit": "frozen_case_within_output_contract",
        "repetition_treatment": "median_within_case_arm_before_comparison",
        "timing": "caller_total_ns",
        "minimum_gain_fraction": 0.05,
        "attribution_required": True,
    }
    if plan["decision_rule"] != expected_rule:
        raise ValueError("review decision rule")
    verified = []
    for record in plan["source_bindings"]:
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "role"}:
            raise ValueError("review source binding")
        path = resolve_workspace_path(record["path"])
        if file_sha256(path) != record["sha256"]:
            raise ValueError(f"review source hash mismatch: {record['path']}")
        verified.append({**record, "verified": True})
    return verified


def analyze() -> dict[str, Any]:
    source_manifest = verify_sealed_audit()
    inputs = read_json(SOURCE_AUDIT / "FROZEN_INPUTS.json")
    contracts = build_contracts(inputs)
    contract_by_digest = {sha256_json(contract): contract for contract, _ in contracts}
    rows = [json.loads(line) for line in (SOURCE_AUDIT / "LEDGER.jsonl").read_text(encoding="ascii").splitlines()]
    if len(rows) != 186:
        raise ValueError("unexpected ledger size")

    statuses = Counter(row["status"] for row in rows)
    complete_failure_accounting = sum(statuses.values()) == len(rows) and statuses == {"ok": 186}
    if not complete_failure_accounting:
        raise ValueError("sealed run did not retain the expected complete outcome set")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    positions: dict[tuple[str, str], list[int]] = defaultdict(list)
    for position, row in enumerate(rows):
        digest = row["contract_sha256"]
        if digest not in contract_by_digest:
            raise ValueError("ledger contract is not reproducible from frozen inputs")
        grouped[(digest, row["arm"])].append(row)
        positions[(digest, row["arm"])].append(position)
        if row["validation"].get("matches_oracle") is not True:
            raise ValueError("ledger contains an unverified output")

    for digest, contract in contract_by_digest.items():
        for arm in arms_for(contract):
            cell_rows = grouped[(digest, arm)]
            if len(cell_rows) != 3 or {row["repetition"] for row in cell_rows} != {0, 1, 2}:
                raise ValueError("repetition coverage mismatch")
        contract_rows = [row for arm in arms_for(contract) for row in grouped[(digest, arm)]]
        if contract["task"] == "simplified_expression":
            if any(row["artifact"]["semantic_sha256"] != contract["artifact"]["semantic_sha256"] for row in contract_rows):
                raise ValueError("simplification semantic output mismatch")
        elif len({row["artifact"]["sha256"] for row in contract_rows}) != 1:
            raise ValueError("identical-output digest mismatch")

    fixed_arm_order = True
    observed_orders = set()
    for digest, contract in contract_by_digest.items():
        observed = tuple(sorted(arms_for(contract), key=lambda arm: min(positions[(digest, arm)])))
        observed_orders.add((contract["task"], observed))
        fixed_arm_order = fixed_arm_order and observed == arms_for(contract)

    median_session: dict[tuple[str, str], float] = {}
    for key, cell_rows in grouped.items():
        median_session[key] = float(statistics.median(row["caller_total_ns"] for row in cell_rows))

    lane_results = []
    for task, lane in LANES.items():
        relevant = [
            (digest, contract)
            for digest, contract in contract_by_digest.items()
            if contract["task"] == task
        ]
        comparisons = []
        for incumbent in lane["incumbents"]:
            ratios = [
                median_session[(digest, lane["candidate"])] / median_session[(digest, incumbent)]
                for digest, _ in relevant
            ]
            comparison = exact_instance_bootstrap(ratios)
            comparison.update({
                "incumbent": incumbent,
                "candidate": lane["candidate"],
                "point_gain_at_least_5_percent": comparison["geometric_mean_candidate_over_incumbent"] <= 0.95,
            })
            comparisons.append(comparison)

        point_threshold_pass = all(item["point_gain_at_least_5_percent"] for item in comparisons)
        quality_noninferior = True
        if task == "simplified_expression":
            for digest, _ in relevant:
                candidate_rows = grouped[(digest, lane["candidate"])]
                candidate_quality = {
                    key: statistics.median(row["quality"][key] for row in candidate_rows)
                    for key in ("literal_occurrences", "boolean_operations", "srepr_bytes")
                }
                for incumbent in lane["incumbents"]:
                    incumbent_rows = grouped[(digest, incumbent)]
                    incumbent_quality = {
                        key: statistics.median(row["quality"][key] for row in incumbent_rows)
                        for key in candidate_quality
                    }
                    quality_noninferior = quality_noninferior and all(
                        candidate_quality[key] <= incumbent_quality[key] for key in candidate_quality
                    )

        attribution = {
            "isolated": False,
            "reason": (
                "The candidate changes representation and execution algorithm. No raw-AST or structural-CSE "
                "arm uses the candidate's evaluator, and no direct-versus-CM ingress ablation is present."
            ),
        }
        lane_results.append({
            "family": lane["family"],
            "task": task,
            "output_contracts": len(relevant),
            "independent_instances": len(relevant),
            "repetitions_per_instance_arm": 3,
            "candidate": lane["candidate"],
            "comparisons": comparisons,
            "quality_noninferior": quality_noninferior,
            "point_threshold_pass_against_all_incumbents": point_threshold_pass,
            "cm_contribution_attribution": attribution,
            "correctly_attributed_development_gain": bool(point_threshold_pass and quality_noninferior and attribution["isolated"]),
        })

    run = read_json(SOURCE_AUDIT / "RUN.json")
    review = {
        "schema": "cm-sympy-development-gate-review/v1",
        "source_audit_manifest_sha256": file_sha256(SOURCE_AUDIT / "AUDIT_MANIFEST.json"),
        "source_files_verified": len(source_manifest["files"]),
        "evidence": {
            "ledger_rows": len(rows),
            "status_counts": dict(sorted(statuses.items())),
            "all_declared_outputs_fully_consumed_and_exactly_verified": True,
            "preparation_and_cache_treatment": {
                "fresh_process_per_cell": True,
                "compilation_and_preparation_charged": True,
                "all_compared_runtimes_preloaded_before_worker_task_timer": True,
                "caller_total_includes_process_import_transport_and_shutdown": True,
                "cross_cell_cache_reuse": False,
                "arm_order_counterbalanced": not fixed_arm_order,
                "observed_ordering": "fixed_contract_arm_then_repetitions",
            },
            "complete_failure_accounting": complete_failure_accounting,
            "hard_limits": {
                "cell_time_seconds": run["limits"].get("cell_timeout_seconds"),
                "study_time_seconds": run["limits"].get("total_timeout_seconds"),
                "worker_output_bytes": run["limits"].get("max_worker_output_bytes"),
                "hard_memory_limit_present": any("memory" in key for key in run["limits"]),
            },
            "independence": {
                "unit": "frozen_case_within_output_contract",
                "repetitions_are_independent_units": False,
                "aggregation": "median repetition total session within case/arm, then paired case ratios",
                "uncertainty": "exact paired bootstrap over instances, kept separate by task/family",
            },
        },
        "lanes": lane_results,
        "decision": {
            "threshold": "at least 5 percent total-session gain against every matched incumbent",
            "correct_attribution_required": True,
            "qualifying_lanes": [lane["task"] for lane in lane_results if lane["correctly_attributed_development_gain"]],
            "outcome": "no_go",
            "reason": (
                "No lane has an isolated CM contribution. Apparent point gains therefore remain comparator/algorithm "
                "differences, and the fixed arm order plus missing hard memory ceiling prevent promotion to confirmation."
            ),
            "confirmation_corpus_frozen": False,
            "confirmation_run_performed": False,
            "stop": True,
        },
    }
    return review


def render_report(review: dict[str, Any], binding_sha256: str, review_plan_sha256: str) -> str:
    lines = [
        "# SymPy/CM development-gain gate: no-go",
        "",
        "No Y02--Y05 lane demonstrates a **correctly attributed** CM development gain of at least "
        "5% in caller-observed total-session time. No confirmation corpus was frozen or timed.",
        "",
        "## Instance-level results",
        "",
        "Each frozen case/output contract is one independent unit. The three repetitions are collapsed "
        "to a within-instance median before paired ratios and exact paired-instance bootstrap intervals "
        "are computed. Candidate/incumbent ratios below 0.95 pass the raw point threshold; they do not "
        "by themselves establish CM attribution.",
        "",
        "| Family/task | Candidate | Incumbent | Instances | Total-session ratio | 95% instance bootstrap | Raw 5% point gate | Attributed |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for lane in review["lanes"]:
        for comparison in lane["comparisons"]:
            interval = comparison["bootstrap_95_percentile_interval"]
            lines.append(
                f"| {lane['family']} / `{lane['task']}` | `{lane['candidate']}` | `{comparison['incumbent']}` | "
                f"{comparison['independent_instances']} | {comparison['geometric_mean_candidate_over_incumbent']:.4f} | "
                f"{interval[0]:.4f}--{interval[1]:.4f} | "
                f"{'pass' if comparison['point_gain_at_least_5_percent'] else 'fail'} | no |"
            )

    evidence = review["evidence"]
    lines.extend([
        "",
        "## Contract and fairness audit",
        "",
        f"- Output accounting: all {evidence['ledger_rows']} cells completed and matched their exact "
        "semantic oracle; Y02 fully consumed the generator, Y03 delivered every assignment answer, "
        "Y04 delivered exact Boolean statuses with validated witnesses, and Y05 delivered complete "
        "equivalent expressions with quality metrics.",
        "- Preparation/caching: every cell used a fresh process, all compared runtimes were preloaded "
        "before the worker task timer, task preparation/compilation was charged, and cross-cell caches "
        "were unavailable. Caller totals include startup, imports, transport, and shutdown.",
        "- Failure accounting: 186 ok, zero mismatch, timeout, error, or not-run results. The executor "
        "had cell/study/output limits, but the completed run had **no enforced hard memory ceiling**.",
        "- Ordering: arms and their three repetitions were run in fixed blocks, not counterbalanced. "
        "This is retained as a design limitation rather than repaired with post-hoc timing choices.",
        "- Independence: repetitions measure timing variation only. Effective sample sizes are four "
        "cases for Y02/Y03/Y04 and six case-form contracts for Y05.",
        "",
        "## Attribution decision",
        "",
        "Some raw point comparisons clear 5%, notably Y03 assignment batches and parts of Y04 SAT. "
        "They are not CM-specific gains: each candidate changes both representation and evaluator. "
        "The development study contains no raw-AST or structural-CSE input running through the same "
        "batch/packed evaluator, and no direct-versus-CM ingress ablation. Y04 additionally compares "
        "explicit enumeration with DPLL/CDCL-style solving; Y05 compares different simplification "
        "pipelines. Those are algorithm/comparator differences, not isolated CM contributions.",
        "",
        "Because no lane satisfies both the 5% total-session gate and the attribution gate, the correct "
        "decision is **no-go and stop**. Creating fresh heldout inputs would spend the confirmation reserve "
        "without a qualifying development mechanism, so no confirmation corpus, acceptance test, or new "
        "timing run was created.",
        "",
        "## Provenance",
        "",
        f"Review-plan SHA-256: `{review_plan_sha256}`. Verified source-binding SHA-256: `{binding_sha256}`. "
        "The sealed source audit and its historical evidence remain unchanged.",
        "",
    ])
    return "\n".join(lines)


def run(plan_path: Path, output_dir: Path) -> int:
    plan_path = plan_path.resolve()
    output_dir = output_dir.resolve()
    if plan_path.parent != OUTPUT_AUDIT.resolve() or output_dir != OUTPUT_AUDIT.resolve():
        raise ValueError("review paths must remain in the successor audit directory")
    plan = read_json(plan_path)
    bindings = verify_review_plan(plan)
    review = analyze()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_binding = {
        "schema": "cm-sympy-development-gate-source-binding/v1",
        "review_id": plan["review_id"],
        "review_plan": {
            "path": str(plan_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": file_sha256(plan_path),
        },
        "sources": bindings,
    }
    write_json(output_dir / "SOURCE_BINDING.json", source_binding)
    write_json(output_dir / "REVIEW.json", review)
    binding_sha256 = file_sha256(output_dir / "SOURCE_BINDING.json")
    report = render_report(review, binding_sha256, file_sha256(plan_path))
    (output_dir / "NO_GO.md").write_text(report, encoding="utf-8", newline="\n")
    names = ("REVIEW_PLAN.json", "SOURCE_BINDING.json", "REVIEW.json", "NO_GO.md")
    manifest = {
        "schema": "cm-sympy-development-gate-audit-manifest/v1",
        "review_id": plan["review_id"],
        "decision": "no_go",
        "files": [
            {"path": name, "sha256": file_sha256(output_dir / name), "bytes": (output_dir / name).stat().st_size}
            for name in names
        ],
    }
    write_json(output_dir / "AUDIT_MANIFEST.json", manifest)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=OUTPUT_AUDIT / "REVIEW_PLAN.json")
    parser.add_argument("--output", type=Path, default=OUTPUT_AUDIT)
    args = parser.parse_args()
    return run(args.plan, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
