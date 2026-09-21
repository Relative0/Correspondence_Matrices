"""Apply the exact C16 artifact-contract adapter to ABC ACD on frozen C40 cases.

This is a capability probe, not a timing or quality contest.  It records
whether the external producer can supply a complete, reconstructing artifact
in the same contract required by C16's global selection rule.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping

from .external_gf2_artifact_adapter import adapt_abc_acd_result
from .gf2_c40_confirmation_benchmark import C40Config, ROOT, _relative, verify_freeze
from .gf2_decomposition import analyze_screened_exact_gf2, truth_sha256


SCHEMA = "crse-c40-abc-acd-contract-probe/v1"


@dataclass(frozen=True)
class ABCContractProbeConfig:
    lut_size: int = 4
    timeout_seconds: float = 60.0

    def validate(self) -> None:
        if (type(self.lut_size) is not int or not 2 <= self.lut_size <= 8
                or type(self.timeout_seconds) not in (int, float)
                or not 5 <= self.timeout_seconds <= 600):
            raise ValueError("invalid C40 ABC contract-probe config")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json_x(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl_x(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, allow_nan=False) + "\n")


def _git_revision(path: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True, encoding="utf-8"
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _expected_document(case: Mapping[str, Any], config: C40Config) -> dict[str, Any] | None:
    bits, n_vars = int(case["truth_bits_hex"], 16), case["n_vars"]
    analysis = analyze_screened_exact_gf2(
        bits, n_vars, max_partitions=config.max_partitions, materialize_budget=config.materialize_budget
    )
    return analysis.best.to_dict() if analysis.best is not None else None


def run_probe(*, project_root: str | Path, freeze_path: str | Path, runner_path: str | Path,
              output: str | Path, config: ABCContractProbeConfig = ABCContractProbeConfig()) -> dict[str, Any]:
    """Run each C40 vector through ABC, then report adapter compatibility."""
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
    c40_config = C40Config(**freeze["config"])
    verification = verify_freeze(freeze, root)
    if not verification["verified"]:
        raise ValueError("C40 freeze verification failed before ABC contract probe")
    output_path.mkdir(parents=True, exist_ok=False)

    rows = []
    for case in freeze["cases"]:
        bits, n_vars = int(case["truth_bits_hex"], 16), case["n_vars"]
        expected = _expected_document(case, c40_config)
        started = time.perf_counter_ns()
        completed = subprocess.run(
            [str(runner), str(n_vars), str(config.lut_size), case["truth_bits_hex"]],
            capture_output=True, text=True, encoding="utf-8", timeout=config.timeout_seconds, check=False,
        )
        process_ns = max(1, time.perf_counter_ns() - started)
        abc, runner_valid, detail = None, False, None
        try:
            abc = json.loads(completed.stdout)
            runner_valid = (
                completed.returncode == 0
                and abc["n_vars"] == n_vars
                and abc["lut_size"] == config.lut_size
                and abc["status"] in {"decomposed", "no_decomposition"}
                and type(abc["algorithm_ns"]) is int and abc["algorithm_ns"] > 0
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            detail = f"{type(exc).__name__}: {exc}"
        adapter = (
            adapt_abc_acd_result(
                source_bits=bits, n_vars=n_vars, abc_result=abc,
                expected_selected_document=expected,
            ) if runner_valid else None
        )
        rows.append({
            "schema": "crse-c40-abc-acd-contract-probe-row/v1",
            "case_id": case["case_id"],
            "n_vars": n_vars,
            "truth_sha256": truth_sha256(bits, n_vars),
            "process_ns": process_ns,
            "returncode": completed.returncode,
            "stdout_sha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
            "runner_valid": runner_valid,
            "detail": detail,
            "abc": abc,
            "expected_selected_artifact_document_sha256": (
                hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
                if expected is not None else None
            ),
            "adapter": adapter,
        })
    counts = Counter(row["adapter"]["status"] for row in rows if row["adapter"] is not None)
    valid = all(row["runner_valid"] and row["adapter"] is not None for row in rows)
    result = {
        "schema": SCHEMA,
        "status": "complete" if valid else "failed",
        "freeze_path": _relative(root, freeze_file),
        "freeze_sha256": freeze["freeze_sha256"],
        "config": asdict(config),
        "runner": {
            "path": _relative(root, runner),
            "sha256": _sha256(runner),
            "abc_source_revision": _git_revision(runner.parent.parent / "c39_abc_source"),
            "upstream_repository": "https://github.com/berkeley-abc/abc",
        },
        "environment": {"python": sys.version, "platform": platform.platform()},
        "summary": {
            "valid_external_calls": valid,
            "case_count": len(rows),
            "adapter_status_counts": dict(sorted(counts.items())),
            "accepted_exact_contract_cases": counts.get("accepted", 0),
            "direct_artifact_comparison_eligible": counts.get("accepted", 0) == len(rows),
            "result_interpretation": "ABC ACD runner output is adapted only when it supplies a complete C16 artifact document. The runner used here reports feasibility, LUT cost, and delay only, so incompatibility is the expected honest result; this probe is not a speed or quality comparison.",
        },
    }
    _write_json_x(output_path / "freeze_verification.json", verification)
    _write_jsonl_x(output_path / "contract_probe.jsonl", rows)
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
    result = run_probe(
        project_root=args.project_root, freeze_path=args.freeze, runner_path=args.runner, output=args.output
    )
    print(json.dumps({"status": result["status"], "summary": result["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
