"""Successor screen for the unresolved exact-count and biology lanes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    import resource
except ImportError:  # Windows can still freeze and validate the Linux plan.
    resource = None


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import cm_benchmark_core_screen as core  # noqa: E402
from cmbench.biology_bnet import parse_bnet, require_closed_bnet  # noqa: E402


CAMPAIGN = "cm-mega-successor-20260914-009"
PLAN_SCHEMA = "cm-benchmark-core-screen-plan/v2"
EXPECTED_EXACT_CASES = 8
EXPECTED_BIOLOGY_CASES = 10
EXPECTED_CELLS = 108

# Reuse the bounded worker, execution, ledger, and summary implementation while
# making its subprocess and identity globals point at this successor runner.
core.__file__ = __file__
core.CAMPAIGN = CAMPAIGN
core.PLAN_SCHEMA = PLAN_SCHEMA
core.REPETITIONS = 3
core.CELL_SECONDS = 60
core.CAMPAIGN_SECONDS = 3600


def _case(row: dict[str, object]) -> dict[str, object]:
    return {
        "case_id": row["case_id"],
        "input_sha256": row["expected_sha256"],
        "path": "inputs/" + row["group"] + "/" + Path(row["path"]).name,
        "metadata": row["metadata"],
    }


def build_plan(admission_path: Path) -> dict[str, object]:
    admission = json.loads(Path(admission_path).read_text(encoding="utf-8"))
    admitted = [row for row in admission["rows"] if row.get("state") == "admitted"]

    exact = [
        row
        for row in admitted
        if row.get("kind") == "mc"
        and row["metadata"].get("declared_support_variables") == 0
    ]
    exact = core._quantiles(  # pylint: disable=protected-access
        exact,
        EXPECTED_EXACT_CASES,
        lambda row: (row["metadata"]["variables"], row["case_id"]),
    )

    biology_by_hash = {}
    for row in admitted:
        if row.get("kind") != "bnet" or row["metadata"].get("functions", 10**9) > 16:
            continue
        source = ROOT / row["path"]
        functions = parse_bnet(source.read_text(encoding="utf-8"))
        try:
            require_closed_bnet(functions)
        except ValueError:
            continue
        model_sha = row["expected_sha256"]
        biology_by_hash.setdefault(
            model_sha,
            {
                **row,
                "case_id": "biology-closed-" + model_sha[:16],
                "metadata": {
                    **row["metadata"],
                    "closed_under_declared_targets": True,
                    "undeclared_regulators": [],
                },
            },
        )
    biology = sorted(
        biology_by_hash.values(),
        key=lambda row: (row["metadata"]["functions"], row["expected_sha256"]),
    )

    if len(exact) != EXPECTED_EXACT_CASES or len(biology) != EXPECTED_BIOLOGY_CASES:
        raise RuntimeError(
            f"successor case cardinality changed: exact={len(exact)} biology={len(biology)}"
        )

    lanes = [
        ("exact_count", exact, ("ganak", "d4"), "paired_native_incumbents"),
        (
            "biology_fixed_points",
            biology,
            ("bnet_cm_scalar", "biodivine_aeon"),
            "paired_closed_models",
        ),
    ]
    cells = []
    cases = []
    for lane, rows, arms, assurance in lanes:
        for row in rows:
            case = _case(row)
            case.update({"lane": lane, "assurance": assurance})
            cases.append(case)
            for repetition in range(core.REPETITIONS):
                order = list(arms)
                if int(
                    core.digest_bytes(
                        f"{lane}:{case['case_id']}:{repetition}".encode()
                    )[:2],
                    16,
                ) & 1:
                    order.reverse()
                for position, arm in enumerate(order):
                    identity = {
                        "campaign_id": CAMPAIGN,
                        "lane": lane,
                        "case_id": case["case_id"],
                        "arm": arm,
                        "repetition": repetition,
                        "position": position,
                        "input_sha256": case["input_sha256"],
                    }
                    cells.append(
                        {
                            **identity,
                            "cell_id": core.digest_bytes(core.canonical(identity)),
                        }
                    )

    body = {
        "schema": PLAN_SCHEMA,
        "campaign_id": CAMPAIGN,
        "created_utc": core.utc_now(),
        "selection": (
            "pre-outcome exact-count quantiles reused from the frozen screen; "
            "all unique closed biology models of at most 16 declared targets"
        ),
        "repetitions": core.REPETITIONS,
        "cell_seconds": core.CELL_SECONDS,
        "campaign_seconds": core.CAMPAIGN_SECONDS,
        "cases": sorted(cases, key=lambda row: (row["lane"], row["case_id"])),
        "cells": cells,
        "prior_results_reused": {
            "campaign_id": "cm-mega-prelaunch-20260914-008",
            "results_sha256": (
                "78e408a50ed2836b31590e034c22ab0b06a2c0823713efe65e4ee3dde88cd345"
            ),
            "lanes_not_repeated": ["affine_solution_count", "projected_count"],
            "reason": "prior lanes were not invalidated by either successor correction",
        },
        "not_run_policy": {
            "campaign_boundary": (
                "remaining cells recorded not_run when stop-admission time binds"
            ),
            "cell_boundary": (
                "timeout, exception, wrong answer, and unavailable are distinct"
            ),
            "biology": "models not closed under declared targets are absent by rule",
        },
    }
    body["plan_sha256"] = core.digest_bytes(core.canonical(body))
    return body


def validate_plan(plan: dict[str, object]) -> None:
    if plan.get("schema") != PLAN_SCHEMA or plan.get("campaign_id") != CAMPAIGN:
        raise ValueError("successor plan schema or campaign")
    body = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if core.digest_bytes(core.canonical(body)) != plan.get("plan_sha256"):
        raise ValueError("successor plan digest")
    cases = {row["case_id"]: row for row in plan.get("cases", [])}
    if len(cases) != 18 or len(plan.get("cells", [])) != EXPECTED_CELLS:
        raise ValueError("successor plan cardinality")
    lane_counts = {
        lane: sum(row["lane"] == lane for row in cases.values())
        for lane in ("exact_count", "biology_fixed_points")
    }
    if lane_counts != {
        "exact_count": EXPECTED_EXACT_CASES,
        "biology_fixed_points": EXPECTED_BIOLOGY_CASES,
    }:
        raise ValueError("successor lane cardinality")
    for cell in plan["cells"]:
        identity = {
            key: cell[key]
            for key in (
                "campaign_id",
                "lane",
                "case_id",
                "arm",
                "repetition",
                "position",
                "input_sha256",
            )
        }
        if (
            cell["case_id"] not in cases
            or core.digest_bytes(core.canonical(identity)) != cell["cell_id"]
        ):
            raise ValueError("successor cell identity")


core.validate_plan = validate_plan


def worker(request_path: Path) -> None:
    """Map an adapter deadline to the plan's explicit timeout terminal state."""
    if resource is not None:
        resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))
        resource.setrlimit(
            resource.RLIMIT_CPU, (core.CELL_SECONDS, core.CELL_SECONDS + 2)
        )
        resource.setrlimit(resource.RLIMIT_FSIZE, (16 << 20, 16 << 20))
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    try:
        result = core.execute(request)
    except TimeoutError:
        result = {
            "schema": core.SCHEMA,
            "status": "timeout",
            "cell": request["cell"],
            "reason": "adapter_deadline",
        }
    core.write_new(request["result_path"], result)


core.worker = worker


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    freeze = commands.add_parser("freeze")
    freeze.add_argument("--admission", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    worker = commands.add_parser("worker")
    worker.add_argument("--request", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--root", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--plan", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.action == "freeze":
        core.write_new(args.output, build_plan(args.admission))
        result = {
            "status": "frozen",
            "output": str(args.output),
            "sha256": core.digest(args.output),
        }
    elif args.action == "worker":
        core.worker(args.request)
        return 0
    elif args.action == "run":
        result = core.run_campaign(args.plan, args.root, args.output)
    else:
        result = core.verify(args.plan, args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
