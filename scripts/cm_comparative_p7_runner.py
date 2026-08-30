#!/usr/bin/env python3
"""Run, resume, or verify a frozen P7 Linux isolated-cell shard."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from collections.abc import Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative import linux_supervisor, p7_runner
from cmbench.comparative.contracts import canonical_bytes
from cmbench.comparative.evidence import append_record, publish_json


CODE_PATHS = (
    "bitset_backend.py",
    "cm_expr_serde.py",
    "cm_exprlib.py",
    "cm_ir.py",
    "cm_normalize.py",
    "cmbench/backends/__init__.py",
    "cmbench/backends/bitset_engine.py",
    "cmbench/comparative/arms.py",
    "cmbench/comparative/contracts.py",
    "cmbench/comparative/corpus_freeze.py",
    "cmbench/comparative/evidence.py",
    "cmbench/comparative/ir.py",
    "cmbench/comparative/linux_supervisor.py",
    "cmbench/comparative/p7.py",
    "cmbench/comparative/p7_runner.py",
    "cmbench/comparative/schedule.py",
    "cmbench/recognition/__init__.py",
    "cmbench/recognition/blif.py",
    "cmbench/recognition/features.py",
    "scripts/cm_comparative_p7_runner.py",
)


def strict_load(path: Path):
    return p7_runner.strict_json(path.read_bytes(), limit=256 << 20)


def _new_output(path: Path, project: Path) -> Path:
    output = path.absolute()
    if output.exists() or not output.parent.exists() or not output.parent.resolve().is_relative_to(project):
        raise ValueError("output must be a new path under an existing project directory")
    output.mkdir()
    return output


def _checksums(output: Path) -> dict:
    files = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name == "checksums.json":
            continue
        files.append({
            "path": path.relative_to(output).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": p7_runner.sha256(path),
        })
    return {"schema": "cm-comparative-p7-isolated-checksums/v1", "files": files}


def _execute(
    *,
    project: Path,
    freeze_path: Path,
    output: Path,
    plan: dict,
    freeze: dict,
    limits: linux_supervisor.Limits,
    resume: bool,
) -> dict:
    ledger_dir = output / "ledger"
    if resume:
        if (output / "summary.json").exists() or (output / "checksums.json").exists():
            raise ValueError("completed P7 output cannot be resumed")
        before = strict_load(output / "source-before.json")
        current = p7_runner.source_identity(project, freeze, CODE_PATHS)
        if current != before:
            raise ValueError("source identity changed before resume")
        state = p7_runner.read_segments(ledger_dir)
        segment = p7_runner.new_segment(ledger_dir)
        p7_runner.recover_interrupted(state, segment)
        state = p7_runner.read_segments(ledger_dir)
        oracle_package = strict_load(output / "oracles.json")
        oracles = p7_runner.validate_oracle_package(oracle_package, plan)
    else:
        before = p7_runner.source_identity(project, freeze, CODE_PATHS)
        if p7_runner.record_sha256(before) != plan["worker_source_manifest_sha256"]:
            raise ValueError("plan worker source identity changed")
        oracle_package = p7_runner.oracle_package(plan, freeze, project)
        oracles = p7_runner.validate_oracle_package(oracle_package, plan)
        publish_json(output / "plan.json", plan)
        publish_json(output / "source-before.json", before)
        publish_json(output / "environment.json", p7_runner.environment_identity())
        publish_json(output / "oracles.json", oracle_package)
        segment = p7_runner.new_segment(ledger_dir)
        state = p7_runner.read_segments(ledger_dir)

    cells = {cell["cell_id"]: cell for cell in plan["cells"]}
    if set(state["latest"]) - set(cells):
        raise ValueError("ledger contains an unexpected cell")
    for cell in plan["cells"]:
        prior = state["latest"].get(cell["cell_id"])
        if prior is not None and prior["status"] != "error":
            continue
        if prior is not None and prior.get("reason") != "interrupted_before_terminal_evidence":
            continue
        p7_runner.verify_cell_sources(project, cell, CODE_PATHS, before)
        attempt = 1 if prior is None else prior["attempt"] + 1
        request = p7_runner.request_for(plan, cell, oracles[cell["case_id"]])
        request_sha = hashlib.sha256(canonical_bytes(request)).hexdigest()
        append_record(segment, {
            "cell_id": cell["cell_id"], "request_sha256": request_sha,
            "attempt": attempt, "status": "running",
        })
        try:
            result, request_record = p7_runner.execute_cell(
                plan=plan,
                cell=cell,
                oracle=oracles[cell["case_id"]],
                python=Path(sys.executable),
                worker_program=Path(__file__),
                project_root=project,
                freeze_path=freeze_path,
                limits=limits,
            )
            if request_record["request_sha256"] != request_sha:
                raise ValueError("cell request identity changed")
            terminal = {
                "cell_id": cell["cell_id"], "request_sha256": request_sha,
                "attempt": attempt, "status": result["status"],
                "reason": result["reason"], "result": result,
            }
        except Exception as exc:
            terminal = {
                "cell_id": cell["cell_id"], "request_sha256": request_sha,
                "attempt": attempt, "status": "error",
                "reason": "controller_exception:" + type(exc).__name__,
            }
        append_record(segment, terminal)
        p7_runner.verify_cell_sources(project, cell, CODE_PATHS, before)
        state = p7_runner.read_segments(ledger_dir)

    after = p7_runner.source_identity(project, freeze, CODE_PATHS)
    source_unchanged = before == after
    publish_json(output / "source-after.json", after)
    state = p7_runner.read_segments(ledger_dir)
    result = p7_runner.summary(plan, state, oracle_package, source_unchanged=source_unchanged)
    publish_json(output / "summary.json", result)
    publish_json(output / "checksums.json", _checksums(output))
    return result


def run(args) -> int:
    project = args.project_root.resolve()
    freeze_path = args.freeze.resolve()
    freeze = strict_load(freeze_path)
    if not p7_runner.linux_supervisor.platform_supported():
        raise ValueError("P7 isolated runner requires Linux /proc process-group supervision")
    output = _new_output(args.output, project)
    limits = linux_supervisor.Limits(
        timeout_seconds=args.timeout_seconds,
        rss_stop_bytes=args.rss_stop_bytes,
        stdout_bytes=p7_runner.MAX_WORKER_BYTES,
        stderr_bytes=256 << 10,
        input_bytes=p7_runner.MAX_REQUEST_BYTES,
        processes=4,
    )
    source_before = p7_runner.source_identity(project, freeze, CODE_PATHS)
    plan = p7_runner.build_plan(
        freeze,
        policy_id=args.policy,
        roles=args.roles,
        blocks=args.blocks,
        worker_source_manifest_sha256=p7_runner.record_sha256(source_before),
        resource_limits=p7_runner.limits_record(limits),
        case_limit=args.case_limit,
        profile=args.profile,
    )
    result = _execute(
        project=project, freeze_path=freeze_path, output=output, plan=plan,
        freeze=freeze, limits=limits, resume=False,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


def resume(args) -> int:
    project = args.project_root.resolve()
    freeze_path = args.freeze.resolve()
    freeze = strict_load(freeze_path)
    if not p7_runner.linux_supervisor.platform_supported():
        raise ValueError("P7 isolated runner requires Linux /proc process-group supervision")
    output = args.output.resolve()
    plan = strict_load(output / "plan.json")
    p7_runner.validate_plan(plan, freeze)
    limits = linux_supervisor.Limits(
        timeout_seconds=args.timeout_seconds,
        rss_stop_bytes=args.rss_stop_bytes,
        stdout_bytes=p7_runner.MAX_WORKER_BYTES,
        stderr_bytes=256 << 10,
        input_bytes=p7_runner.MAX_REQUEST_BYTES,
        processes=4,
    )
    if p7_runner.limits_record(limits) != plan["resource_limits"]:
        raise ValueError("resume limits differ from frozen plan")
    result = _execute(
        project=project, freeze_path=freeze_path, output=output, plan=plan,
        freeze=freeze, limits=limits, resume=True,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


def worker(args) -> int:
    payload = sys.stdin.buffer.read(p7_runner.MAX_REQUEST_BYTES + 1)
    request = p7_runner.strict_json(payload, limit=p7_runner.MAX_REQUEST_BYTES)
    project = args.project_root.resolve()
    freeze_path = args.freeze.resolve()
    if not freeze_path.is_relative_to(project) or not freeze_path.is_file():
        raise ValueError("worker freeze path escapes project")
    freeze = strict_load(freeze_path)
    result = p7_runner.execute_worker(request, freeze, project)
    encoded = canonical_bytes(result)
    if len(encoded) > p7_runner.MAX_WORKER_BYTES:
        raise ValueError("worker result exceeds output bound")
    sys.stdout.buffer.write(encoded + b"\n")
    sys.stdout.buffer.flush()
    return 0


def verify(args) -> int:
    project = args.project_root.resolve()
    output = args.output.resolve()
    freeze = strict_load(args.freeze.resolve())
    plan = strict_load(output / "plan.json")
    p7_runner.validate_plan(plan, freeze)
    before = strict_load(output / "source-before.json")
    after = strict_load(output / "source-after.json")
    state = p7_runner.read_segments(output / "ledger")
    oracle_package = strict_load(output / "oracles.json")
    reproduced = p7_runner.summary(plan, state, oracle_package, source_unchanged=before == after)
    saved = strict_load(output / "summary.json")
    checksums = strict_load(output / "checksums.json")
    rows = checksums.get("files") if isinstance(checksums, Mapping) else None
    checksum_ok = (
        checksums.get("schema") == "cm-comparative-p7-isolated-checksums/v1"
        and isinstance(rows, list)
        and all(
            set(row) == {"path", "bytes", "sha256"}
            and not Path(row["path"]).is_absolute()
            and (output / row["path"]).resolve().is_relative_to(output)
            and (output / row["path"]).is_file()
            and (output / row["path"]).stat().st_size == row["bytes"]
            and p7_runner.sha256(output / row["path"]) == row["sha256"]
            for row in rows
        )
    )
    current = p7_runner.source_identity(project, freeze, CODE_PATHS)
    result = {
        "schema": "cm-comparative-p7-isolated-verification/v1",
        "summary_matches": saved == reproduced,
        "checksums_verified": checksum_ok,
        "source_before_after_match": before == after,
        "current_source_matches": current == after,
        "status": saved.get("status"),
        "performance_claim_permitted": saved.get("performance_claim_permitted"),
    }
    result["verified"] = all((
        result["summary_matches"], result["checksums_verified"],
        result["source_before_after_match"], result["current_source_matches"],
        result["status"] == "passed",
    ))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verified"] else 1


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    sub = value.add_subparsers(dest="command", required=True)
    for name, function in (("run", run), ("resume", resume)):
        command = sub.add_parser(name)
        command.add_argument("--project-root", type=Path, required=True)
        command.add_argument("--freeze", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        command.add_argument("--timeout-seconds", type=float, default=30.0)
        command.add_argument("--rss-stop-bytes", type=int, default=1 << 30)
        if name == "run":
            command.add_argument("--policy", choices=sorted(p7_runner.P7_POLICIES), required=True)
            command.add_argument("--roles", nargs="+", choices=("regression", "development", "confirmation"), required=True)
            command.add_argument("--blocks", type=int, required=True)
            command.add_argument("--case-limit", type=int)
            command.add_argument("--profile", choices=("functional", "performance"), default="functional")
        command.set_defaults(func=function)
    command = sub.add_parser("worker")
    command.add_argument("--project-root", type=Path, required=True)
    command.add_argument("--freeze", type=Path, required=True)
    command.set_defaults(func=worker)
    command = sub.add_parser("verify")
    command.add_argument("--project-root", type=Path, required=True)
    command.add_argument("--freeze", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.set_defaults(func=verify)
    return value


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
