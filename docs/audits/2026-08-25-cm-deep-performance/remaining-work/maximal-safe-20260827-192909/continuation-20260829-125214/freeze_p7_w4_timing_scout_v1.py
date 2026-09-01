"""Freeze the static 12-case P7 W4 development timing/RSS scout."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = next(
    parent
    for parent in (HERE, *HERE.parents)
    if (parent / "cmbench").is_dir() and (parent / "docs").is_dir()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.corpus_freeze import build_order_ledger, validate_freeze, verify_sources


PARENT_PATH = (
    PROJECT_ROOT
    / "docs"
    / "research"
    / "verification"
    / "comparative-p6-candidate-v4-2026-08-30"
    / "freeze.json"
)
W3_AUDIT_PATH = HERE / "P7-W3-FINAL-INDEPENDENT-AUDIT.json"
W8_FREEZE_PATH = (
    PROJECT_ROOT
    / "docs"
    / "research"
    / "verification"
    / "comparative-w8-logikbench-confirmation-v1-2026-08-31"
    / "freeze.json"
)
DESTINATION = (
    PROJECT_ROOT
    / "docs"
    / "research"
    / "verification"
    / "comparative-p7-w4-timing-scout-v1-2026-08-31"
)
HASH = re.compile(r"[0-9a-f]{64}")
SYNTHETIC_PATTERN = re.compile(r"-k(8|12|16)-(andor_dom|impeqv_dom|mixed|xor_dom)-(shared|tree)-")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(case: dict) -> str:
    return hashlib.sha256(case["case_id"].encode("utf-8")).hexdigest()


def natural_stratum(case: dict) -> tuple[str, str]:
    support = case["strata"]["live_k"]
    nodes = case["strata"]["dag_nodes"]
    support_bin = "low-4-5" if support <= 5 else "mid-6-9" if support <= 9 else "high-10-16"
    node_bin = "small-1-16" if nodes <= 16 else "medium-17-64" if nodes <= 64 else "large-65-512"
    return support_bin, node_bin


def select_cases(parent: dict, w3_audit: dict) -> tuple[list[dict], list[dict]]:
    excluded = w3_audit.get("combined", {}).get("excluded_case")
    if (
        w3_audit.get("status") != "passed_with_one_shared_oracle_feasibility_exclusion"
        or excluded != "development-epfl-sqrt-31cdaf5d0213"
        or w3_audit.get("sqrt_exclusion", {}).get("policy_independent_oracle_generator") is not True
        or w3_audit.get("combined", {}).get("performance_measurement") is not False
        or w3_audit.get("combined", {}).get("performance_ranking_permitted") is not False
    ):
        raise RuntimeError("W3 typed exclusion evidence changed")
    development = [
        case for case in parent["cases"]
        if case["role"] == "development"
        and {"ir_preparation", "complete_relation"}.issubset(case["tasks"])
    ]
    synthetic = [case for case in development if case["kind"] == "expression_jsonl_member"]
    natural = [case for case in development if case["kind"] == "blif" and case["case_id"] != excluded]

    selected = []
    ledger = []
    for support in (8, 12, 16):
        for shape in ("shared", "tree"):
            candidates = [
                case for case in synthetic
                if case["strata"]["live_k"] == support and case["strata"]["shape"] == shape
            ]
            if len(candidates) != 4:
                raise RuntimeError(f"synthetic W4 stratum changed: {(support, shape)}")
            chosen = min(candidates, key=key)
            match = SYNTHETIC_PATTERN.search(chosen["case_id"])
            if match is None:
                raise RuntimeError("synthetic family identity unavailable")
            selected.append(chosen)
            ledger.append(
                {
                    "case_id": chosen["case_id"],
                    "cluster_id": chosen["cluster_id"],
                    "origin": "synthetic",
                    "stratum": {"live_k": support, "shape": shape},
                    "generator_family": match.group(2),
                    "selection_key": key(chosen),
                    "candidate_count": len(candidates),
                }
            )
    families = {row["generator_family"] for row in ledger}
    if families != {"andor_dom", "impeqv_dom", "mixed", "xor_dom"}:
        raise RuntimeError("selected synthetic cases do not cover all frozen generator families")

    grouped: dict[tuple[str, str], list[dict]] = {}
    for case in natural:
        grouped.setdefault(natural_stratum(case), []).append(case)
    if len(grouped) != 6:
        raise RuntimeError(f"natural W4 strata changed: {sorted(grouped)}")
    for stratum in sorted(grouped):
        candidates = grouped[stratum]
        chosen = min(candidates, key=key)
        selected.append(chosen)
        ledger.append(
            {
                "case_id": chosen["case_id"],
                "cluster_id": chosen["cluster_id"],
                "origin": "natural",
                "stratum": {"support_bin": stratum[0], "source_node_bin": stratum[1]},
                "selection_key": key(chosen),
                "candidate_count": len(candidates),
            }
        )
    if len(selected) != 12 or len({case["cluster_id"] for case in selected}) != 12:
        raise RuntimeError("W4 selection cardinality changed")
    return selected, ledger


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    if DESTINATION.exists():
        raise RuntimeError(f"W4 freeze already exists: {DESTINATION}")
    parent = load(PARENT_PATH)
    w3_audit = load(W3_AUDIT_PATH)
    w8_freeze = load(W8_FREEZE_PATH)
    validate_freeze(parent)
    if parent.get("freeze_sha256") != "54ea61a38135426975a0d1fead9b24c020dc565eb3d952356640fa38062598dd":
        raise RuntimeError("P6 parent freeze identity changed")
    if w8_freeze.get("freeze_sha256") != "427522568449d4d385ce642769b87b0703216535edb131653a0a75b2a8e39dcc":
        raise RuntimeError("W8 untouched confirmation freeze identity changed")
    selected, ledger = select_cases(parent, w3_audit)
    selected_ids = {case["case_id"] for case in selected}

    derived = copy.deepcopy(parent)
    derived["cases"] = [case for case in parent["cases"] if case["case_id"] in selected_ids]
    policies = []
    for policy in parent["schedule_policies"]:
        if policy["policy_id"] not in {"p7-ir", "p7-relation"}:
            continue
        normalized = {field: value for field, value in policy.items() if field != "order_ledger"}
        normalized["order_ledger"] = build_order_ledger(derived["cases"], normalized)
        policies.append(normalized)
    derived["schedule_policies"] = policies
    provenance = dict(derived["provenance"])
    provenance["w4_timing_scout"] = {
        "schema": "cm-comparative-p7-w4-timing-scout-selection/v1",
        "parent_freeze_sha256": parent["freeze_sha256"],
        "w3_audit_sha256": sha256(W3_AUDIT_PATH),
        "w8_confirmation_freeze_sha256": w8_freeze["freeze_sha256"],
        "case_count": len(selected),
        "selected_case_ids": [case["case_id"] for case in selected],
        "selection_ledger_sha256": hashlib.sha256(canonical_bytes(ledger)).hexdigest(),
        "selection_uses_comparative_timing": False,
        "typed_w3_exclusion": w3_audit["combined"]["excluded_case"],
    }
    derived["provenance"] = provenance
    derived["timing_results_inspected"] = False
    core = {field: value for field, value in derived.items() if field != "freeze_sha256"}
    derived["freeze_sha256"] = hashlib.sha256(canonical_bytes(core)).hexdigest()
    validate_freeze(derived)
    source_check = verify_sources(derived, PROJECT_ROOT)
    if source_check.get("verified") is not True:
        raise RuntimeError("selected W4 sources do not verify")

    policy_counts = {}
    for policy in policies:
        arms = len(policy["arms"])
        blocks = policy["minimum_blocks"]
        if blocks != 2 * arms:
            raise RuntimeError("W4 minimum block is not one complete counterbalance cycle")
        policy_counts[policy["policy_id"]] = {
            "cases": len(selected),
            "arms": arms,
            "blocks": blocks,
            "planned_cells": len(selected) * arms * blocks,
        }
    if policy_counts != {
        "p7-ir": {"cases": 12, "arms": 4, "blocks": 8, "planned_cells": 384},
        "p7-relation": {"cases": 12, "arms": 5, "blocks": 10, "planned_cells": 600},
    }:
        raise RuntimeError(f"W4 planned-cell contract changed: {policy_counts}")

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=DESTINATION.name + ".tmp-", dir=DESTINATION.parent))
    selection = {
        "schema": "cm-comparative-p7-w4-timing-scout-selection/v1",
        "parent_freeze_sha256": parent["freeze_sha256"],
        "derived_freeze_sha256": derived["freeze_sha256"],
        "w3_audit_sha256": sha256(W3_AUDIT_PATH),
        "w8_confirmation_freeze_sha256": w8_freeze["freeze_sha256"],
        "selection_rule": {
            "synthetic": "lowest SHA-256(case_id) in each frozen k={8,12,16} x shape={shared,tree} stratum",
            "natural": "after the pre-existing W3 typed sqrt exclusion, lowest SHA-256(case_id) in each occupied frozen support-bin x source-node-bin stratum",
            "comparative_timing_inspected": False,
        },
        "cases": ledger,
        "policy_counts": policy_counts,
        "planned_primary_cells": sum(row["planned_cells"] for row in policy_counts.values()),
    }
    write_json(temporary / "freeze.json", derived)
    write_json(temporary / "selection.json", selection)
    write_json(temporary / "source-check.json", source_check)
    verification = {
        "schema": "cm-comparative-p7-w4-timing-scout-freeze-verification/v1",
        "verified": True,
        "failures": [],
        "parent_freeze_sha256": parent["freeze_sha256"],
        "derived_freeze_sha256": derived["freeze_sha256"],
        "case_count": len(selected),
        "synthetic_cases": sum(case["origin"] == "synthetic" for case in selected),
        "natural_cases": sum(case["origin"] == "natural" for case in selected),
        "independent_clusters": len({case["cluster_id"] for case in selected}),
        "synthetic_k": sorted({case["strata"]["live_k"] for case in selected if case["origin"] == "synthetic"}),
        "synthetic_shapes": sorted({case["strata"]["shape"] for case in selected if case["origin"] == "synthetic"}),
        "synthetic_families": sorted({row["generator_family"] for row in ledger if row["origin"] == "synthetic"}),
        "natural_strata": sorted(
            [row["stratum"] for row in ledger if row["origin"] == "natural"],
            key=lambda item: (item["support_bin"], item["source_node_bin"]),
        ),
        "planned_primary_cells": 984,
        "complete_counterbalance_cycles": True,
        "sources_verified": True,
        "comparative_timing_inspected": False,
    }
    write_json(temporary / "verification.json", verification)
    readme = f"""# P7 W4 timing/RSS scout freeze v1

This development scout contains 12 independent units selected only from frozen
static strata: six synthetic units covering k=8,12,16, both tree/shared shapes,
and all four generator families; and six EPFL cones covering every occupied
support-bin/source-size stratum after the already retained W3 `sqrt` oracle
feasibility exclusion.

The derived logical freeze is `{derived['freeze_sha256']}`. It schedules one
complete counterbalance cycle for each policy: 384 IR cells and 600 relation
cells, 984 primary cells total. This is a resource/noise scout, not the
principal P7 result. The W8 LogikBench cohort remains untouched confirmation
and is not present here.
"""
    (temporary / "README.md").write_text(readme, encoding="utf-8")
    os.replace(temporary, DESTINATION)
    print(json.dumps(verification, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
