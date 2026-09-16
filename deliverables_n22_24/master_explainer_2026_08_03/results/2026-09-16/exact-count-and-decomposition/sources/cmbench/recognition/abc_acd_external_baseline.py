"""Run a pinned public ABC Ashenhurst-Curtis baseline on a frozen truth corpus."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
from typing import Any, Mapping

from .gf2_phase_benchmark import ROOT, verify_freeze


SCHEMA = "crse-c39-abc-acd-external-baseline/v1"


@dataclass(frozen=True)
class AbcAcdConfig:
    lut_size: int = 4
    rounds: int = 3
    seed: int = 20260916
    timeout_seconds: float = 30.0

    def validate(self) -> None:
        if (
            type(self.lut_size) is not int or not 2 <= self.lut_size <= 8
            or type(self.rounds) is not int or not 3 <= self.rounds <= 9
            or type(self.seed) is not int
            or type(self.timeout_seconds) not in (int, float) or not 1 <= self.timeout_seconds <= 120
        ):
            raise ValueError("invalid C39 ABC ACD baseline config")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_x(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl_x(path: Path, rows: list[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, allow_nan=False) + "\n")


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _git_revision(path: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True, encoding="utf-8"
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _schedule(cases: list[Mapping[str, Any]], config: AbcAcdConfig) -> list[tuple[int, str]]:
    result = []
    for round_index in range(config.rounds):
        order = [row["case_id"] for row in cases]
        random.Random(f"{config.seed}:abc-acd:{round_index}").shuffle(order)
        result.extend((round_index, case_id) for case_id in order)
    return result


def run_abc_acd_baseline(*, project_root: str | Path, freeze_path: str | Path,
                         runner_path: str | Path, output: str | Path,
                         config: AbcAcdConfig = AbcAcdConfig()) -> dict[str, Any]:
    """Evaluate ABC ACD with the same frozen truth vectors as C39.

    ABC's output is a k-LUT ACD feasibility/cost result.  It deliberately is
    not compared numerically with C16: C16 selects a canonical CM artifact,
    while ABC optimizes a distinct LUT-mapping objective.
    """
    config.validate()
    root = Path(project_root).resolve()
    freeze_file = Path(freeze_path)
    if not freeze_file.is_absolute():
        freeze_file = root / freeze_file
    runner = Path(runner_path)
    if not runner.is_absolute():
        runner = root / runner
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root / output_path
    if not runner.is_file():
        raise ValueError("ABC ACD runner is missing")
    freeze = json.loads(freeze_file.read_text(encoding="utf-8"))
    freeze_verification = verify_freeze(freeze, root)
    if not freeze_verification["verified"]:
        raise ValueError("C39 freeze verification failed before external baseline")
    output_path.mkdir(parents=True, exist_ok=False)

    rows = []
    by_id = {row["case_id"]: row for row in freeze["cases"]}
    for round_index, case_id in _schedule(freeze["cases"], config):
        case = by_id[case_id]
        started = time.perf_counter_ns()
        completed = subprocess.run(
            [str(runner), str(case["n_vars"]), str(config.lut_size), case["truth_bits_hex"]],
            capture_output=True, text=True, encoding="utf-8", timeout=config.timeout_seconds, check=False,
        )
        process_ns = max(1, time.perf_counter_ns() - started)
        result = None
        detail = None
        try:
            result = json.loads(completed.stdout)
            valid = (
                completed.returncode == 0
                and result["n_vars"] == case["n_vars"]
                and result["lut_size"] == config.lut_size
                and result["status"] in {"decomposed", "no_decomposition"}
                and type(result["algorithm_ns"]) is int and result["algorithm_ns"] > 0
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            valid = False
            detail = f"{type(exc).__name__}: {exc}"
        rows.append({
            "schema": "crse-c39-abc-acd-measurement/v1",
            "round": round_index,
            "case_id": case_id,
            "n_vars": case["n_vars"],
            "truth_sha256": case["truth_sha256"],
            "process_ns": process_ns,
            "returncode": completed.returncode,
            "stdout_sha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
            "valid": valid,
            "detail": detail,
            "acd": result,
        })

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["case_id"]].append(row)
    algorithm_medians = {
        case_id: statistics.median(row["acd"]["algorithm_ns"] for row in values if row["valid"])
        for case_id, values in grouped.items() if all(row["valid"] for row in values)
    }
    semantic_keys = ("status", "return_value", "delay_profile", "lut_cost")
    case_outcomes = {
        case_id: {key: values[0]["acd"][key] for key in semantic_keys}
        for case_id, values in sorted(grouped.items()) if values[0]["valid"]
    }
    case_outcomes_consistent = all(
        all(row["valid"] and {key: row["acd"][key] for key in semantic_keys} == case_outcomes[case_id]
            for row in values)
        for case_id, values in grouped.items()
    )
    status_counts = Counter(row["status"] for row in case_outcomes.values())
    source_root = runner.parent.parent / "c39_abc_source"
    functional_valid = all(row["valid"] for row in rows)
    result = {
        "schema": SCHEMA,
        "status": "complete" if functional_valid else "failed",
        "config": asdict(config),
        "freeze_path": _relative(root, freeze_file),
        "freeze_sha256": freeze["freeze_sha256"],
        "runner": {
            "path": _relative(root, runner),
            "sha256": _sha256(runner),
            "abc_source_revision": _git_revision(source_root),
            "upstream_repository": "https://github.com/berkeley-abc/abc",
        },
        "environment": {"python": sys.version, "platform": platform.platform()},
        "summary": {
            "valid_external_calls": functional_valid,
            "case_count": len(grouped),
            "case_outcomes": case_outcomes,
            "case_outcomes_consistent_across_rounds": case_outcomes_consistent,
            "case_decomposition_status_counts": dict(sorted(status_counts.items())),
            "sum_case_median_algorithm_ns": int(sum(algorithm_medians.values())),
            "objective_alignment": {
                "same_frozen_truth_vectors": True,
                "same_general_task": "Exact Boolean functional decomposition",
                "same_artifact_contract": False,
                "same_optimization_objective": False,
                "timing_comparable_to_c16": False,
                "reason": "ABC reports 4-LUT ACD feasibility, LUT cost, and delay profile; C16 must choose a canonical artifact from XOR, GF(2)-rank, cofactor-block, and Kronecker families.",
            },
        },
    }
    _write_json_x(output_path / "freeze_verification.json", freeze_verification)
    _write_jsonl_x(output_path / "measurements.jsonl", rows)
    _write_json_x(output_path / "results.json", result)
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run_abc_acd_baseline(
        project_root=args.project_root, freeze_path=args.freeze, runner_path=args.runner, output=args.output
    )
    print(json.dumps({"status": result["status"], "summary": result["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
