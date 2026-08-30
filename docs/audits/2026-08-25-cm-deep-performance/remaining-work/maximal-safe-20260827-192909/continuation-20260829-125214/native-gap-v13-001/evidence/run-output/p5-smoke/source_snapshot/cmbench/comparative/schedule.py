"""Deterministic counterbalanced schedules and immutable benchmark shards."""

from __future__ import annotations

import hashlib
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import canonical_bytes, contract_digest, validate_contract


PLAN_SCHEMA = "cm-comparative-plan/v1"
MAX_CASES = 10_000
MAX_ARMS = 32
MAX_BLOCKS = 64
MAX_CELLS = 1_000_000


def balanced_orders(arms: Sequence[str]) -> tuple[tuple[str, ...], ...]:
    """Every arm occupies every position twice, once in each direction."""
    values = tuple(arms)
    if not values or len(values) > MAX_ARMS or len(set(values)) != len(values):
        raise ValueError("unique bounded arms required")
    forward = [values[offset:] + values[:offset] for offset in range(len(values))]
    rows = tuple(forward + [tuple(reversed(row)) for row in forward])
    for arm in values:
        positions = Counter(row.index(arm) for row in rows)
        if positions != Counter({index: 2 for index in range(len(values))}):
            raise AssertionError("counterbalance construction failed")
    return rows


def case_order(case_ids: Sequence[str], mode: str, *, seed: int, repetitions: int) -> tuple[str, ...]:
    """Freeze case locality separately from within-case arm order."""
    cases = tuple(case_ids)
    if not cases or len(cases) > MAX_CASES or len(set(cases)) != len(cases):
        raise ValueError("unique bounded case ids required")
    if type(seed) is not int or type(repetitions) is not int or not 1 <= repetitions <= 4096:
        raise ValueError("invalid case schedule parameters")
    if mode == "blocked":
        return tuple(case for case in cases for _ in range(repetitions))
    if mode == "round_robin":
        return cases * repetitions
    rng = random.Random(seed)
    if mode == "sliding_window":
        output: list[str] = []
        width = min(4, len(cases))
        base = list(cases * repetitions)
        for start in range(0, len(base), width):
            window = base[start : start + width]
            rng.shuffle(window)
            output.extend(window)
        return tuple(output)
    if mode == "zipf":
        # Weighted permutations define order, not selection/survival. Every
        # case still appears once per repetition.
        weights = {case: 1.0 / (index + 1) for index, case in enumerate(cases)}
        output: list[str] = []
        for _ in range(repetitions):
            keys = {case: rng.random() ** (1.0 / weights[case]) for case in cases}
            output.extend(sorted(cases, key=lambda case: keys[case], reverse=True))
        return tuple(output)
    raise ValueError("unknown locality mode")


def build_plan(
    *,
    campaign_id: str,
    cases: Sequence[Mapping[str, Any]],
    arms: Sequence[str],
    contracts: Mapping[str, Mapping[str, Any]],
    blocks: int,
    locality: str,
    seed: int,
    shard_cells: int,
) -> dict[str, Any]:
    """Build an immutable cell/shard ledger with no post-hoc arm selection."""
    if not isinstance(campaign_id, str) or not campaign_id or len(campaign_id) > 128:
        raise ValueError("invalid campaign id")
    if type(blocks) is not int or not 1 <= blocks <= MAX_BLOCKS:
        raise ValueError("invalid block count")
    if type(shard_cells) is not int or not 1 <= shard_cells <= 100_000:
        raise ValueError("invalid shard size")
    orders = balanced_orders(arms)
    if blocks < len(orders) or blocks % len(orders):
        raise ValueError("blocks must contain complete counterbalance cycles")
    if set(contracts) != set(arms):
        raise ValueError("one contract per arm required")
    contract_hashes = {arm: contract_digest(contracts[arm]) for arm in arms}
    tasks = {validate_contract(contracts[arm])["task"] for arm in arms}
    if len(tasks) != 1:
        raise ValueError("one task per paired plan required")
    normalized_cases: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, Mapping) or set(case) != {"case_id", "cluster_id", "input_sha256"}:
            raise ValueError("case fields")
        row = {key: str(case[key]) for key in case}
        if any(not value or len(value) > 256 for value in row.values()):
            raise ValueError("invalid case identity")
        normalized_cases.append(row)
    case_ids = [row["case_id"] for row in normalized_cases]
    if not case_ids or len(case_ids) > MAX_CASES or len(set(case_ids)) != len(case_ids):
        raise ValueError("unique bounded cases required")
    case_map = {row["case_id"]: row for row in normalized_cases}
    if len(case_ids) * blocks * len(arms) > MAX_CELLS:
        raise ValueError("planned cell bound")
    ordered_cases = case_order(case_ids, locality, seed=seed, repetitions=blocks)

    cells: list[dict[str, Any]] = []
    seen_case_block: Counter[str] = Counter()
    for case_position, case_id in enumerate(ordered_cases):
        block = seen_case_block[case_id]
        seen_case_block[case_id] += 1
        order = orders[(block + seed) % len(orders)]
        for arm_position, arm in enumerate(order):
            identity = {
                "campaign_id": campaign_id,
                "case_id": case_id,
                "cluster_id": case_map[case_id]["cluster_id"],
                "input_sha256": case_map[case_id]["input_sha256"],
                "arm": arm,
                "contract_sha256": contract_hashes[arm],
                "block": block,
                "case_position": case_position,
                "arm_position": arm_position,
                "locality": locality,
                "seed": seed,
            }
            identity["cell_id"] = hashlib.sha256(canonical_bytes(identity)).hexdigest()
            cells.append(identity)
    if len(cells) > MAX_CELLS or len({row["cell_id"] for row in cells}) != len(cells):
        raise ValueError("invalid cell cardinality")

    shards = []
    for offset in range(0, len(cells), shard_cells):
        ids = [row["cell_id"] for row in cells[offset : offset + shard_cells]]
        shard = {"index": len(shards), "cell_ids": ids}
        shard["sha256"] = hashlib.sha256(canonical_bytes(shard)).hexdigest()
        shards.append(shard)
    plan = {
        "schema": PLAN_SCHEMA,
        "campaign_id": campaign_id,
        "task": next(iter(tasks)),
        "seed": seed,
        "locality": locality,
        "blocks": blocks,
        "arms": list(arms),
        "contracts": {arm: contracts[arm] for arm in arms},
        "cases": normalized_cases,
        "cells": cells,
        "shards": shards,
    }
    validate_plan(plan)
    plan["plan_sha256"] = hashlib.sha256(canonical_bytes(plan)).hexdigest()
    return plan


def validate_plan(plan: Mapping[str, Any]) -> None:
    expected = {"schema", "campaign_id", "task", "seed", "locality", "blocks", "arms", "contracts", "cases", "cells", "shards"}
    if set(plan) not in (expected, expected | {"plan_sha256"}):
        raise ValueError("plan fields")
    if "plan_sha256" in plan:
        core = {key: plan[key] for key in expected}
        if plan["plan_sha256"] != hashlib.sha256(canonical_bytes(core)).hexdigest():
            raise ValueError("plan identity mismatch")
    if plan["schema"] != PLAN_SCHEMA:
        raise ValueError("plan schema")
    if not isinstance(plan["arms"], list) or not plan["arms"] or len(set(plan["arms"])) != len(plan["arms"]):
        raise ValueError("plan arms")
    if set(plan["contracts"]) != set(plan["arms"]):
        raise ValueError("plan contracts")
    if type(plan["blocks"]) is not int or type(plan["seed"]) is not int:
        raise ValueError("plan schedule types")
    orders = balanced_orders(plan["arms"])
    if plan["blocks"] < len(orders) or plan["blocks"] % len(orders):
        raise ValueError("plan counterbalance cycles")
    if not isinstance(plan["cases"], list) or not plan["cases"]:
        raise ValueError("plan cases")
    cases = {}
    for row in plan["cases"]:
        if not isinstance(row, Mapping) or set(row) != {"case_id", "cluster_id", "input_sha256"}:
            raise ValueError("plan case fields")
        if (
            row["case_id"] in cases
            or not isinstance(row["input_sha256"], str)
            or len(row["input_sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in row["input_sha256"])
        ):
            raise ValueError("plan case identity")
        cases[row["case_id"]] = row
    expected_case_order = case_order(
        tuple(cases), plan["locality"], seed=plan["seed"], repetitions=plan["blocks"]
    )
    if len(plan["cells"]) != len(cases) * plan["blocks"] * len(plan["arms"]):
        raise ValueError("plan cell cardinality")
    ids = [row.get("cell_id") for row in plan["cells"]]
    if not ids or len(ids) > MAX_CELLS or len(set(ids)) != len(ids):
        raise ValueError("plan cell identities")
    for arm in plan["arms"]:
        normalized = validate_contract(plan["contracts"][arm])
        if normalized["task"] != plan["task"]:
            raise ValueError("plan task mismatch")
    seen_blocks: Counter[str] = Counter()
    for offset, row in enumerate(plan["cells"]):
        if set(row) != {"campaign_id", "case_id", "cluster_id", "input_sha256", "arm", "contract_sha256",
                        "block", "case_position", "arm_position", "locality", "seed", "cell_id"}:
            raise ValueError("cell fields")
        core = {key: value for key, value in row.items() if key != "cell_id"}
        if row["cell_id"] != hashlib.sha256(canonical_bytes(core)).hexdigest():
            raise ValueError("cell identity mismatch")
        if row["arm"] not in plan["arms"] or row["contract_sha256"] != contract_digest(plan["contracts"][row["arm"]]):
            raise ValueError("cell arm/contract mismatch")
        case_position, arm_position = divmod(offset, len(plan["arms"]))
        case_id = expected_case_order[case_position]
        block = seen_blocks[case_id]
        expected_arm = orders[(block + plan["seed"]) % len(orders)][arm_position]
        if arm_position == len(plan["arms"]) - 1:
            seen_blocks[case_id] += 1
        source = cases[case_id]
        expected = {
            "campaign_id": plan["campaign_id"],
            "case_id": case_id,
            "cluster_id": source["cluster_id"],
            "input_sha256": source["input_sha256"],
            "arm": expected_arm,
            "contract_sha256": contract_digest(plan["contracts"][expected_arm]),
            "block": block,
            "case_position": case_position,
            "arm_position": arm_position,
            "locality": plan["locality"],
            "seed": plan["seed"],
        }
        if core != expected:
            raise ValueError("cell schedule mismatch")
    flattened = [cell for shard in plan["shards"] for cell in shard.get("cell_ids", [])]
    if flattened != ids:
        raise ValueError("shard coverage/order mismatch")
    for expected_index, shard in enumerate(plan["shards"]):
        if set(shard) != {"index", "cell_ids", "sha256"} or shard["index"] != expected_index:
            raise ValueError("shard fields")
        core = {"index": shard["index"], "cell_ids": shard["cell_ids"]}
        if shard["sha256"] != hashlib.sha256(canonical_bytes(core)).hexdigest():
            raise ValueError("shard identity mismatch")
