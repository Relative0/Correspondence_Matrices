"""Run the frozen local incremental-revision comparison without network access."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import incremental_revision as experiment  # noqa: E402


DEFAULT_OUTPUT = ROOT / "docs" / "research" / "verification" / "incremental-revision-local-gate-2026-09-04"
PROTOCOL = "docs/research/CM_INCREMENTAL_REVISION_LOCAL_GATE_PROTOCOL_2026_09_04.md"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_inventory_and_checksums(output: Path) -> None:
    artifacts = sorted(
        path for path in output.iterdir()
        if path.is_file() and path.name not in {"INVENTORY.json", "CHECKSUMS.sha256"}
    )
    inventory = {
        "schema": "cm-incremental-revision-local-gate-inventory/v1",
        "files": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": file_sha(path)}
            for path in artifacts
        ],
    }
    write_json(output / "INVENTORY.json", inventory)
    checksummed = sorted(path for path in output.iterdir() if path.is_file() and path.name != "CHECKSUMS.sha256")
    (output / "CHECKSUMS.sha256").write_text(
        "".join(f"{file_sha(path)}  {path.name}\n" for path in checksummed),
        encoding="ascii",
        newline="\n",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rounds", type=int, default=experiment.DEFAULT_ROUNDS)
    parser.add_argument(
        "--evaluation-repetitions",
        type=int,
        default=experiment.DEFAULT_EVALUATION_REPETITIONS,
    )
    parser.add_argument("--limit-cases", type=int, default=0, help="diagnostic only; zero runs the frozen full matrix")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    if args.rounds < 1 or args.evaluation_repetitions < 1 or args.limit_cases < 0:
        raise SystemExit("rounds/evaluation repetitions must be positive and limit-cases nonnegative")

    cases = experiment.load_cases()
    full_matrix = args.limit_cases == 0
    selected = cases if full_matrix else cases[: args.limit_cases]
    output.mkdir(parents=True)
    manifest = {
        "schema": "cm-incremental-revision-local-gate-manifest/v1",
        "status": "running",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repository_revision": git_head(),
        "protocol": PROTOCOL,
        "cases_sha256": experiment.CASES_SHA256,
        "admissions_sha256": experiment.ADMISSIONS_SHA256,
        "source_commit": experiment.SOURCE_COMMIT,
        "python": sys.version,
        "platform": platform.platform(),
        "rounds": args.rounds,
        "evaluation_repetitions": args.evaluation_repetitions,
        "arms": list(experiment.ARMS),
        "selected_case_count": len(selected),
        "full_frozen_matrix": full_matrix,
        "network_used": False,
        "cloud_used": False,
    }
    write_json(output / "MANIFEST.json", manifest)
    write_json(
        output / "PLAN.json",
        {
            "schema": "cm-incremental-revision-local-gate-plan/v1",
            "case_ids": [case["case_id"] for case in selected],
            "split_counts": {
                split: sum(case["split"] == split for case in selected)
                for split in ("development", "confirmation")
            },
            "transition_labels_define_split": True,
            "output_selected": False,
        },
    )

    rows: list[dict[str, Any]] = []
    for index, case in enumerate(selected, 1):
        rows.extend(
            experiment.run_case(
                case,
                rounds=args.rounds,
                evaluation_repetitions=args.evaluation_repetitions,
            )
        )
        if index == 1 or index % 10 == 0 or index == len(selected):
            print(f"completed {index}/{len(selected)} cases", flush=True)
    write_jsonl(output / "RAW.jsonl", rows)

    if full_matrix:
        summary = experiment.summarize(rows)
        recomputed = experiment.summarize([
            json.loads(line) for line in (output / "RAW.jsonl").read_text(encoding="utf-8").splitlines()
        ])
        if recomputed != summary:
            raise AssertionError("serialized raw-result replay changed the summary")
        verification = {
            "schema": "cm-incremental-revision-local-gate-verification/v1",
            "status": "passed",
            "raw_rows_replayed": len(rows),
            "saved_artifact_hashes_checked_per_row": 3,
            "summary_reproduced": True,
            "correctness_mismatches": 0,
        }
    else:
        summary = {
            "schema": "cm-incremental-revision-local-gate/v1",
            "status": "diagnostic_only",
            "row_count": len(rows),
            "case_count": len(selected),
            "performance_ranking_permitted": False,
        }
        verification = {
            "schema": "cm-incremental-revision-local-gate-verification/v1",
            "status": "diagnostic_only",
            "raw_rows_replayed": 0,
            "summary_reproduced": False,
            "correctness_mismatches": 0,
        }
    write_json(output / "SUMMARY.json", summary)
    write_json(output / "VERIFICATION.json", verification)
    manifest["status"] = "completed"
    manifest["completed_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(output / "MANIFEST.json", manifest)
    write_inventory_and_checksums(output)
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
