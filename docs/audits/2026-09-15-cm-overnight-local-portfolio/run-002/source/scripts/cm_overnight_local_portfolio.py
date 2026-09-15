"""Resumable, source-bound Windows test-module assurance campaign."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.biology_session_supervisor import run_worker  # noqa: E402


SCHEMA = "cm-overnight-local-portfolio-plan/v1"
ROW_SCHEMA = "cm-overnight-local-portfolio-row/v1"
GLOBAL_SECONDS = 8 * 60 * 60
ADMISSION_SECONDS = 7 * 60 * 60 + 30 * 60
TEST_SECONDS = 300
MEMORY_BYTES = 2 << 30
OUTPUT_BYTES = 1 << 20
DISK_BYTES = 2 << 30


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def write_replace(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def append_row(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(canonical(row).decode("utf-8") + "\n")
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def execution_lock(output: Path):
    """Refuse concurrent controllers; a crash leaves an inspectable stale lock."""
    path = output / "EXECUTION.lock"
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        owner = path.read_text(encoding="utf-8", errors="replace").strip()
        raise RuntimeError("campaign execution is already locked: " + owner) from error
    try:
        os.write(descriptor, canonical({"pid": os.getpid(), "created_utc": utc_now()}))
        os.fsync(descriptor)
        yield
    finally:
        os.close(descriptor)
        path.unlink(missing_ok=True)


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
    ).strip()


def portfolio_group(path: str) -> str:
    name = Path(path).stem.lower()
    groups = (
        ("biology", ("biology", "bnet")),
        ("sympy_regression", ("sympy",)),
        ("hardware", ("architecture", "epfl", "yosys", "hardware", "aiger", "logikbench")),
        ("feature_models", ("feature", "configuration")),
        ("affine", ("gf2", "affine", "native_slot", "xor")),
        ("exact_controls", ("count", "bucket", "projected", "sat", "cudd")),
        ("lifecycle", ("cache", "stream", "memory", "supervisor", "process",
                       "persistence", "session", "parallel", "concurrency")),
    )
    for group, needles in groups:
        if any(needle in name for needle in needles):
            return group
    return "core_and_synthetic"


def tracked_tests() -> list[str]:
    """Return the current top-level test modules; every byte is bound in the plan."""
    return sorted(path.relative_to(ROOT).as_posix()
                  for path in (ROOT / "tests").glob("test_*.py"))


def build_plan(paths: list[str] | None = None) -> dict:
    paths = tracked_tests() if paths is None else sorted(paths)
    controller = Path(__file__).resolve().relative_to(ROOT).as_posix()
    supervisor = "cmbench/biology_session_supervisor.py"
    sources = {name: sha(ROOT / name) for name in (controller, supervisor)}
    cells = []
    priority_groups = {
        "hardware", "feature_models", "affine", "exact_controls", "lifecycle",
        "core_and_synthetic",
    }
    for path in paths:
        source = ROOT / path
        if not source.is_file():
            raise FileNotFoundError(path)
        group = portfolio_group(path)
        identity = {
            "path": path,
            "input_sha256": sha(source),
            "group": group,
            "timeout_seconds": TEST_SECONDS,
            "memory_limit_bytes": MEMORY_BYTES,
            "output_limit_bytes": OUTPUT_BYTES,
        }
        cells.append({
            **identity,
            "cell_id": digest_bytes(canonical(identity))[:24],
            "priority": 0 if group in priority_groups else 1,
        })
    cells.sort(key=lambda row: (row["priority"], row["group"], row["path"]))
    plan = {
        "schema": SCHEMA,
        "created_utc": utc_now(),
        "git_head": git("rev-parse", "HEAD"),
        "python_executable": sys.executable,
        "global_seconds": GLOBAL_SECONDS,
        "stop_admission_seconds": ADMISSION_SECONDS,
        "disk_limit_bytes": DISK_BYTES,
        "sources": sources,
        "cells": cells,
        "coverage": dict(sorted(Counter(row["group"] for row in cells).items())),
        "interpretation": (
            "Fresh-process test-module assurance. Runtime is diagnostic and is not "
            "a method-performance comparison or heldout acceptance result."
        ),
    }
    plan["plan_sha256"] = digest_bytes(canonical(plan))
    return plan


def validate_plan(plan: dict) -> None:
    if plan.get("schema") != SCHEMA:
        raise ValueError("plan schema")
    body = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if digest_bytes(canonical(body)) != plan.get("plan_sha256"):
        raise ValueError("plan digest")
    if plan.get("git_head") != git("rev-parse", "HEAD"):
        raise ValueError("Git HEAD drift")
    for name, expected in plan.get("sources", {}).items():
        if sha(ROOT / name) != expected:
            raise ValueError("source drift: " + name)
    ids = set()
    for cell in plan.get("cells", []):
        if cell["cell_id"] in ids:
            raise ValueError("duplicate cell")
        ids.add(cell["cell_id"])
        if sha(ROOT / cell["path"]) != cell["input_sha256"]:
            raise ValueError("test input drift: " + cell["path"])


def prepare(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    plan = build_plan()
    write_new(output / "PLAN.json", plan)
    snapshot_names = set(plan["sources"])
    snapshot_names.update(cell["path"] for cell in plan["cells"])
    for name in sorted(snapshot_names):
        target = output / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write((ROOT / name).read_bytes())
    write_new(output / "ENVIRONMENT.json", {
        "created_utc": utc_now(),
        "python": sys.version,
        "executable": sys.executable,
        "platform": sys.platform,
        "git_head": git("rev-parse", "HEAD"),
        "memory_scope": "windows_job_peak_committed_bytes",
        "cpu_scope": "one_allowed_cpu_per_test_module",
    })


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def tree_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def state_for(output: Path, plan: dict, rows: list[dict], *, started_utc: str,
              status: str, reason: str | None = None) -> dict:
    counts = Counter(row["status"] for row in rows)
    return {
        "schema": "cm-overnight-local-portfolio-state/v1",
        "status": status,
        "reason": reason,
        "started_utc": started_utc,
        "updated_utc": utc_now(),
        "plan_sha256": sha(output / "PLAN.json"),
        "completed_cells": len(rows),
        "total_cells": len(plan["cells"]),
        "status_counts": dict(sorted(counts.items())),
        "ledger_sha256": sha(output / "ledger.jsonl") if (output / "ledger.jsonl").exists() else None,
        "output_bytes": tree_bytes(output),
    }


def classify(supervisor: dict) -> tuple[str, str]:
    if not supervisor["cleanup_verified"]:
        return "backend_error", "job_cleanup_unverified"
    if supervisor["status"] != "ok":
        return supervisor["status"], supervisor["reason"]
    if supervisor["returncode"] == 0:
        return "passed", "pytest_passed"
    if supervisor["returncode"] == 1:
        return "test_failure", "pytest_failed"
    return "backend_error", "pytest_exit_" + str(supervisor["returncode"])


def execute_cell(output: Path, cell: dict) -> dict:
    cell_id = cell["cell_id"]
    junit = output / "junit" / (cell_id + ".xml")
    base_temp = output / "work" / cell_id
    junit.parent.mkdir(parents=True, exist_ok=True)
    base_temp.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-B", "-m", "pytest", cell["path"], "-q",
        "--basetemp=" + os.fspath(base_temp), "--junitxml=" + os.fspath(junit),
    ]
    supervisor = run_worker(
        command,
        timeout_seconds=cell["timeout_seconds"],
        memory_limit_bytes=cell["memory_limit_bytes"],
        max_output_bytes=cell["output_limit_bytes"],
        cwd=ROOT,
    )
    status, reason = classify(supervisor)
    logs = {}
    for stream in ("stdout", "stderr"):
        data = supervisor.pop(stream).encode("utf-8", errors="replace")
        if data:
            path = output / "logs" / f"{cell_id}.{stream}.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            logs[stream] = {
                "path": path.relative_to(output).as_posix(),
                "bytes": len(data),
                "sha256": digest_bytes(data),
            }
    return {
        "schema": ROW_SCHEMA,
        "cell_id": cell_id,
        "path": cell["path"],
        "input_sha256": cell["input_sha256"],
        "group": cell["group"],
        "priority": cell["priority"],
        "status": status,
        "reason": reason,
        "completed_utc": utc_now(),
        "supervisor": supervisor,
        "logs": logs,
        "junit": ({
            "path": junit.relative_to(output).as_posix(),
            "bytes": junit.stat().st_size,
            "sha256": sha(junit),
        } if junit.exists() else None),
    }


def finalize(output: Path, plan: dict, rows: list[dict], started_utc: str,
             reason: str) -> None:
    completed = {row["cell_id"] for row in rows}
    for cell in plan["cells"]:
        if cell["cell_id"] not in completed:
            row = {
                "schema": ROW_SCHEMA,
                "cell_id": cell["cell_id"],
                "path": cell["path"],
                "input_sha256": cell["input_sha256"],
                "group": cell["group"],
                "priority": cell["priority"],
                "status": "not_run",
                "reason": reason,
                "completed_utc": utc_now(),
                "supervisor": None,
                "logs": {},
                "junit": None,
            }
            append_row(output / "ledger.jsonl", row)
            rows.append(row)
    summary = {
        "schema": "cm-overnight-local-portfolio-summary/v1",
        "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
        "group_status_counts": {
            group: dict(sorted(Counter(row["status"] for row in rows
                                       if row["group"] == group).items()))
            for group in sorted({row["group"] for row in rows})
        },
        "test_modules": len(rows),
        "cleanup_verified": all(
            row["supervisor"] is None or row["supervisor"]["cleanup_verified"]
            for row in rows
        ),
        "interpretation": plan["interpretation"],
    }
    write_new(output / "SUMMARY.json", summary)
    final_state = state_for(output, plan, rows, started_utc=started_utc,
                            status="complete", reason=reason)
    write_replace(output / "RUN.json", final_state)
    lines = [
        "# Overnight local CM portfolio assurance results",
        "",
        f"Terminal reason: `{reason}`. All {len(rows)} frozen test-module cells are recorded.",
        "",
        "| Status | Modules |",
        "| --- | ---: |",
    ]
    for status, count in sorted(summary["status_counts"].items()):
        lines.append(f"| {status} | {count} |")
    lines.extend([
        "", "These are fresh-process test and portability results, not method-performance timings.",
        "Repetitions were not used as independent evidence. See `SUMMARY.json` and `ledger.jsonl`",
        "for group-level outcomes, preserved failures and resource accounting.", "",
    ])
    (output / "REPORT.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def execute(output: Path, *, slice_seconds: float, max_cells: int | None) -> None:
    plan_path = output / "PLAN.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    validate_plan(plan)
    ledger = output / "ledger.jsonl"
    rows = load_rows(ledger)
    if (output / "RUN.json").exists():
        print(json.dumps(json.loads((output / "RUN.json").read_text(encoding="utf-8"))))
        return
    ids = [row["cell_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate ledger cell")
    plan_ids = {cell["cell_id"] for cell in plan["cells"]}
    if any(row["cell_id"] not in plan_ids for row in rows):
        raise ValueError("foreign ledger cell")
    state_path = output / "STATE.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        started_utc = state["started_utc"]
    else:
        started_utc = utc_now()
    started = datetime.fromisoformat(started_utc.replace("Z", "+00:00"))
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    if elapsed >= plan["stop_admission_seconds"]:
        finalize(output, plan, rows, started_utc, "stop_admission_deadline")
        return
    done = set(ids)
    slice_started = time.monotonic()
    run_count = 0
    for cell in plan["cells"]:
        if cell["cell_id"] in done:
            continue
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        if elapsed >= plan["stop_admission_seconds"]:
            finalize(output, plan, rows, started_utc, "stop_admission_deadline")
            return
        if time.monotonic() - slice_started >= slice_seconds:
            break
        if max_cells is not None and run_count >= max_cells:
            break
        if tree_bytes(output) >= plan["disk_limit_bytes"]:
            finalize(output, plan, rows, started_utc, "disk_limit")
            return
        row = execute_cell(output, cell)
        append_row(ledger, row)
        rows.append(row)
        run_count += 1
        write_replace(state_path, state_for(
            output, plan, rows, started_utc=started_utc, status="running"
        ))
        if not row["supervisor"]["cleanup_verified"]:
            finalize(output, plan, rows, started_utc, "job_cleanup_unverified")
            return
    if len(rows) == len(plan["cells"]):
        finalize(output, plan, rows, started_utc, "schedule_complete")
        return
    write_replace(state_path, state_for(
        output, plan, rows, started_utc=started_utc, status="running",
        reason="slice_complete",
    ))
    print(json.dumps(json.loads(state_path.read_text(encoding="utf-8"))))


def verify(output: Path, *, require_complete: bool) -> dict:
    plan = json.loads((output / "PLAN.json").read_text(encoding="utf-8"))
    validate_plan(plan)
    rows = load_rows(output / "ledger.jsonl")
    ids = [row["cell_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate ledger cell")
    expected = {cell["cell_id"]: cell for cell in plan["cells"]}
    for name, expected_sha in plan["sources"].items():
        if sha(output / "source" / name) != expected_sha:
            raise ValueError("source snapshot identity")
    for cell in plan["cells"]:
        if sha(output / "source" / cell["path"]) != cell["input_sha256"]:
            raise ValueError("test snapshot identity")
    for row in rows:
        cell = expected.get(row["cell_id"])
        if cell is None or row["input_sha256"] != cell["input_sha256"]:
            raise ValueError("row identity")
        for record in row["logs"].values():
            path = output / record["path"]
            if path.stat().st_size != record["bytes"] or sha(path) != record["sha256"]:
                raise ValueError("log identity")
        if row["junit"]:
            record = row["junit"]
            path = output / record["path"]
            if path.stat().st_size != record["bytes"] or sha(path) != record["sha256"]:
                raise ValueError("JUnit identity")
    if require_complete:
        if len(rows) != len(plan["cells"]) or not (output / "RUN.json").exists():
            raise ValueError("campaign incomplete")
        if not (output / "SUMMARY.json").exists() or not (output / "REPORT.md").exists():
            raise ValueError("terminal outputs missing")
    result = {
        "status": "passed",
        "rows": len(rows),
        "cells": len(plan["cells"]),
        "complete": len(rows) == len(plan["cells"]),
    }
    print(json.dumps(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--output", type=Path, required=True)
    execute_parser = commands.add_parser("execute")
    execute_parser.add_argument("--output", type=Path, required=True)
    execute_parser.add_argument("--slice-seconds", type=float, default=3000)
    execute_parser.add_argument("--max-cells", type=int)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--output", type=Path, required=True)
    verify_parser.add_argument("--require-complete", action="store_true")
    status_parser = commands.add_parser("status")
    status_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.output)
    elif args.action == "execute":
        with execution_lock(args.output):
            execute(args.output, slice_seconds=args.slice_seconds, max_cells=args.max_cells)
    elif args.action == "verify":
        verify(args.output, require_complete=args.require_complete)
    else:
        state = args.output / ("RUN.json" if (args.output / "RUN.json").exists()
                               else "STATE.json")
        print(state.read_text(encoding="utf-8") if state.exists()
              else json.dumps({"status": "not_started"}))


if __name__ == "__main__":
    main()
