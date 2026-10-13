#!/usr/bin/env python3
"""Run the bounded local Y02--Y05 SymPy/CM claim-cleanup study."""

from __future__ import annotations

import argparse
import base64
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cmbench.comparative.sympy_cm_claim_cleanup import (  # noqa: E402
    RESULT_SCHEMA,
    arms_for,
    build_contracts,
    canonical_bytes,
    execute_worker,
    median,
    sha256_bytes,
    sha256_json,
    summarize,
    validate_inputs,
)


DEFAULT_AUDIT = ROOT / "docs" / "audits" / "2026-09-15-cm-sympy-claim-cleanup"


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


def validate_plan(plan: dict[str, Any], plan_path: Path) -> tuple[Path, dict[str, Any]]:
    required = {
        "schema", "study_id", "local_only", "inputs", "source_bindings", "repetitions",
        "cell_timeout_seconds", "total_timeout_seconds", "max_worker_output_bytes",
        "expected_environment", "historical_evidence",
    }
    if not isinstance(plan, dict) or set(plan) != required:
        raise ValueError("plan fields")
    if plan["schema"] != "cm-sympy-claim-cleanup-plan/v1" or plan["local_only"] is not True:
        raise ValueError("plan schema/local-only gate")
    if plan_path.resolve().parent != DEFAULT_AUDIT.resolve():
        raise ValueError("plan must remain in the bounded audit directory")
    if type(plan["repetitions"]) is not int or not 1 <= plan["repetitions"] <= 5:
        raise ValueError("repetition bound")
    if not 0 < float(plan["cell_timeout_seconds"]) <= 30:
        raise ValueError("cell deadline bound")
    if not 0 < float(plan["total_timeout_seconds"]) <= 600:
        raise ValueError("study deadline bound")
    if type(plan["max_worker_output_bytes"]) is not int or not 1024 <= plan["max_worker_output_bytes"] <= (1 << 20):
        raise ValueError("worker output bound")

    historical_binding = plan["historical_evidence"]
    if not isinstance(historical_binding, dict) or set(historical_binding) != {"path", "sha256"}:
        raise ValueError("historical evidence binding")
    historical_path = resolve_workspace_path(historical_binding["path"])
    if file_sha256(historical_path) != historical_binding["sha256"]:
        raise ValueError("historical evidence hash mismatch")

    bindings = []
    for binding in plan["source_bindings"]:
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256", "role"}:
            raise ValueError("source binding fields")
        path = resolve_workspace_path(binding["path"])
        actual = file_sha256(path)
        if actual != binding["sha256"]:
            raise ValueError(f"source hash mismatch: {binding['path']}")
        bindings.append({**binding, "verified": True})

    input_record = plan["inputs"]
    if not isinstance(input_record, dict) or set(input_record) != {"path", "sha256"}:
        raise ValueError("input binding")
    inputs_path = resolve_workspace_path(input_record["path"])
    if file_sha256(inputs_path) != input_record["sha256"]:
        raise ValueError("frozen input hash mismatch")
    inputs = read_json(inputs_path)
    validate_inputs(inputs)

    expected = plan["expected_environment"]
    if not isinstance(expected, dict) or set(expected) != {"python_prefix", "distributions", "virtualenv_relative"}:
        raise ValueError("environment binding")
    expected_python = resolve_workspace_path(expected["virtualenv_relative"])
    if Path(sys.executable).resolve() != expected_python:
        raise RuntimeError(f"study must use project virtualenv: {expected_python}")
    if not platform.python_version().startswith(expected["python_prefix"]):
        raise RuntimeError("Python version does not match frozen plan")
    actual_distributions = {}
    for name, required_version in expected["distributions"].items():
        actual = importlib.metadata.version(name)
        if actual != required_version:
            raise RuntimeError(f"distribution mismatch for {name}: {actual} != {required_version}")
        actual_distributions[name] = actual
    return inputs_path, {
        "source_bindings": bindings,
        "inputs": {**input_record, "verified": True},
        "environment": {
            "python_executable": str(Path(sys.executable).resolve()),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "distributions": actual_distributions,
        },
    }


def worker_request_argument(request: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(canonical_bytes(request)).decode("ascii")


def failure_row(
    *,
    contract: dict[str, Any],
    arm: str,
    repetition: int,
    status: str,
    reason: str,
    caller_total_ns: int,
) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        "contract_sha256": sha256_json(contract),
        "family": contract["family"],
        "task": contract["task"],
        "case_id": contract["case_id"],
        "arm": arm,
        "repetition": repetition,
        "status": status,
        "reason": reason[:256],
        "timings_ns": {},
        "caller_total_ns": caller_total_ns,
        "artifact": None,
        "validation": None,
        "quality": None,
    }


def comparisons(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    arm_pairs = {
        "complete_relation": [
            ("sympy_truth_table", "cm_packed"),
        ],
        "assignment_batch": [
            ("sympy_lambdify_cse_off", "cm_ir_batch"),
            ("sympy_lambdify_cse_on", "cm_ir_batch"),
        ],
        "sat_status": [
            ("sympy_satisfiable", "cm_packed_sat"),
            ("pysat_tseitin", "cm_packed_sat"),
        ],
        "equivalence_status": [
            ("sympy_difference_sat", "cm_packed_equivalence"),
            ("pysat_tseitin_miter", "cm_packed_equivalence"),
        ],
    }
    medians: dict[tuple[str, str, str], float] = {}
    for row in rows:
        if row["status"] != "ok":
            continue
        key = (row["task"], row["contract_sha256"], row["arm"])
        medians.setdefault(key, [])
        medians[key].append(row["timings_ns"]["task_total_ns"])
    medians = {key: median(values) for key, values in medians.items()}

    output = []
    for task, pairs in arm_pairs.items():
        for numerator, denominator in pairs:
            contract_ids = sorted({
                contract for current_task, contract, arm in medians
                if current_task == task and arm == numerator and (task, contract, denominator) in medians
            })
            numerator_total = sum(medians[(task, contract, numerator)] for contract in contract_ids)
            denominator_total = sum(medians[(task, contract, denominator)] for contract in contract_ids)
            output.append({
                "task": task,
                "numerator_arm": numerator,
                "denominator_arm": denominator,
                "matched_contracts": len(contract_ids),
                "ratio_of_summed_contract_medians": (
                    numerator_total / denominator_total if denominator_total else None
                ),
            })
    return output


def render_report(
    *,
    plan: dict[str, Any],
    plan_sha256: str,
    input_sha256: str,
    summary: dict[str, Any],
    source_binding_sha256: str,
    historical: dict[str, Any],
) -> str:
    lines = [
        "# Bounded local SymPy/CM claim-cleanup study",
        "",
        "This study executes catalog families Y02--Y05 under task-matched output contracts. "
        "It does not overwrite or reinterpret the archived unlike-task timings. Every worker ran "
        "locally from the project virtualenv with a per-cell deadline; no cloud, download, install, "
        "push or publication operation is part of the executor.",
        "",
        "## Outcome",
        "",
        f"The run retained **{summary['rows']} cells**: **{summary['ok']} ok**, "
        f"**{summary['mismatch']} mismatches**, **{summary['timeout']} timeouts**, and "
        f"**{summary['error']} errors**. Y02 fully consumes the SymPy generator. Y03 charges "
        "SymPy callable construction and evaluates the same hashed assignment batch. Y04 proves "
        "equivalence through satisfiability of a difference miter. Y05 remains a separate "
        "runtime-and-expression-quality scoreboard.",
        "",
        "Ratios below are descriptive local task-total ratios over matched contracts; values above "
        "1 mean the numerator arm took longer. They are not population estimates or a general "
        "CM-specific performance claim.",
        "",
        "| Task | Numerator | Denominator | Contracts | Ratio |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for row in summary["comparisons"]:
        ratio = row["ratio_of_summed_contract_medians"]
        lines.append(
            f"| {row['task']} | `{row['numerator_arm']}` | `{row['denominator_arm']}` | "
            f"{row['matched_contracts']} | {ratio:.4f} |" if ratio is not None else
            f"| {row['task']} | `{row['numerator_arm']}` | `{row['denominator_arm']}` | 0 | n/a |"
        )

    lines.extend([
        "",
        "## Separate Y05 simplification scoreboard",
        "",
        "Y05 arms all return an equivalent Boolean expression in the requested DNF or CNF form. "
        "The CM-assisted arm first produces the complete CM truth relation and then invokes SymPy's "
        "corresponding SOP/POS minimizer; CM alone is not presented as a minimizer. Runtime and "
        "quality are shown without mixing them into Y02's full-table ranking.",
        "",
        "| Arm | Cells | Median task ms | Median literals | Median Boolean ops | Median srepr bytes |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in summary["scoreboards"]:
        if row["task"] != "simplified_expression":
            continue
        lines.append(
            f"| `{row['arm']}` | {row['ok']}/{row['cells']} | "
            f"{row['median_task_total_ns'] / 1e6:.4f} | {row['median_literal_occurrences']:.1f} | "
            f"{row['median_boolean_operations']:.1f} | {row['median_srepr_bytes']:.1f} |"
        )

    historical_groups = historical.get("groups", [])
    historical_n8 = next((row for row in historical_groups if row.get("n_vars") == 8), None)
    historical_text = (
        f"The preserved audit records the historical n=8 median as approximately "
        f"{historical_n8['median_of_paired_recorded_sympy_over_cm']:.3f}x, explicitly labeled "
        "an unlike-task timer ratio. It is context only and is not pooled with this run."
        if historical_n8 else
        "The historical audit is hash-bound as context only and is not pooled with this run."
    )
    lines.extend([
        "",
        "## Provenance and interpretation",
        "",
        historical_text,
        "",
        f"Plan SHA-256: `{plan_sha256}`. Frozen-input SHA-256: `{input_sha256}`. "
        f"Verified source-binding record SHA-256: `{source_binding_sha256}`. The input manifest "
        "contains exact expression trees plus a deterministic assignment generator whose emitted "
        "bytes are checked in every Y03 result.",
        "",
        "Worker `task_total_ns` includes task-specific conversion/preparation, execution and "
        "delivery to the declared artifact. Independent scalar correctness checks are outside that "
        "timer. `caller_total_ns` separately preserves fresh-process startup, imports, JSON transport "
        "and shutdown. Two/three independent algorithms agreeing here establishes the bounded cases' "
        "answers, not a broader solver ranking.",
        "",
        "## Disposition",
        "",
        "Y02--Y05 are now executed as a bounded local claim-cleanup study. The result replaces no "
        "historical file and does not alter the September 15 portfolio no-go conclusion. Broader "
        "SymPy, SAT, synthesis, hardware or cloud scaling remains deferred until a concrete consumer "
        "or distinct CM mechanism defines a new claim.",
        "",
    ])
    return "\n".join(lines)


def run(plan_path: Path, output_dir: Path) -> int:
    plan_path = plan_path.resolve()
    output_dir = output_dir.resolve()
    if output_dir != DEFAULT_AUDIT.resolve():
        raise ValueError("output must be the bounded audit directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = read_json(plan_path)
    inputs_path, verified = validate_plan(plan, plan_path)
    inputs = read_json(inputs_path)
    contracts = build_contracts(inputs)
    plan_sha256 = file_sha256(plan_path)
    input_sha256 = file_sha256(inputs_path)
    source_binding = {
        "schema": "cm-sympy-source-binding/v1",
        "study_id": plan["study_id"],
        "plan": {"path": str(plan_path.relative_to(ROOT)).replace("\\", "/"), "sha256": plan_sha256},
        **verified,
    }
    write_json(output_dir / "SOURCE_BINDING.json", source_binding)

    history_path = resolve_workspace_path(plan["historical_evidence"]["path"])
    historical = read_json(history_path)
    historical_context = {
        "schema": "cm-sympy-historical-context/v1",
        "source_path": plan["historical_evidence"]["path"],
        "source_sha256": file_sha256(history_path),
        "treatment": "preserved unlike-task context; excluded from new scoreboards",
        "evidence": historical,
    }
    write_json(output_dir / "HISTORICAL_CONTEXT.json", historical_context)

    work: list[tuple[dict[str, Any], dict[str, Any], str, int]] = []
    for contract, case in contracts:
        for arm in arms_for(contract):
            for repetition in range(plan["repetitions"]):
                work.append((contract, case, arm, repetition))

    rows: list[dict[str, Any]] = []
    study_started = time.perf_counter()
    worker_environment = dict(os.environ)
    worker_environment.update({
        "PYTHONHASHSEED": "0",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    })
    for index, (contract, case, arm, repetition) in enumerate(work):
        if time.perf_counter() - study_started >= plan["total_timeout_seconds"]:
            for remaining_contract, _, remaining_arm, remaining_repetition in work[index:]:
                rows.append(failure_row(
                    contract=remaining_contract,
                    arm=remaining_arm,
                    repetition=remaining_repetition,
                    status="not_run",
                    reason="study wall-time budget exhausted",
                    caller_total_ns=0,
                ))
            break
        request = {
            "contract": contract,
            "case": case,
            "arm": arm,
            "repetition": repetition,
            "assignment_generator": inputs["assignment_generator"],
        }
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker-request", worker_request_argument(request)]
        caller_started = time.perf_counter_ns()
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=worker_environment,
                check=False,
                capture_output=True,
                timeout=plan["cell_timeout_seconds"],
            )
            caller_total = time.perf_counter_ns() - caller_started
            if len(completed.stdout) + len(completed.stderr) > plan["max_worker_output_bytes"]:
                row = failure_row(
                    contract=contract, arm=arm, repetition=repetition, status="error",
                    reason="worker output limit exceeded", caller_total_ns=caller_total,
                )
            elif completed.returncode != 0:
                reason = completed.stderr.decode("utf-8", errors="replace").strip() or "worker failed"
                row = failure_row(
                    contract=contract, arm=arm, repetition=repetition, status="error",
                    reason=reason, caller_total_ns=caller_total,
                )
            else:
                row = json.loads(completed.stdout.decode("utf-8"))
                row["caller_total_ns"] = caller_total
        except subprocess.TimeoutExpired:
            caller_total = time.perf_counter_ns() - caller_started
            row = failure_row(
                contract=contract, arm=arm, repetition=repetition, status="timeout",
                reason="cell deadline exceeded", caller_total_ns=caller_total,
            )
        row["plan_sha256"] = plan_sha256
        row["input_sha256"] = input_sha256
        row["case_input_sha256"] = sha256_json(case)
        rows.append(row)

    ledger_path = output_dir / "LEDGER.jsonl"
    ledger_path.write_bytes(b"".join(canonical_bytes(row) + b"\n" for row in rows))
    summary = summarize(rows)
    summary["not_run"] = sum(row["status"] == "not_run" for row in rows)
    summary["comparisons"] = comparisons(rows)
    summary["plan_sha256"] = plan_sha256
    summary["input_sha256"] = input_sha256
    summary["ledger_sha256"] = file_sha256(ledger_path)
    write_json(output_dir / "SUMMARY.json", summary)

    run_record = {
        "schema": "cm-sympy-claim-cleanup-run/v1",
        "study_id": plan["study_id"],
        "status": "complete" if summary["not_run"] == 0 else "budget_exhausted",
        "local_only": True,
        "cells_planned": len(work),
        "cells_recorded": len(rows),
        "elapsed_seconds": time.perf_counter() - study_started,
        "limits": {
            "repetitions": plan["repetitions"],
            "cell_timeout_seconds": plan["cell_timeout_seconds"],
            "total_timeout_seconds": plan["total_timeout_seconds"],
            "max_worker_output_bytes": plan["max_worker_output_bytes"],
            "max_variables": 8,
            "assignment_rows": inputs["assignment_generator"]["rows"],
        },
    }
    write_json(output_dir / "RUN.json", run_record)
    source_binding_sha256 = file_sha256(output_dir / "SOURCE_BINDING.json")
    (output_dir / "REPORT.md").write_text(
        render_report(
            plan=plan,
            plan_sha256=plan_sha256,
            input_sha256=input_sha256,
            summary=summary,
            source_binding_sha256=source_binding_sha256,
            historical=historical,
        ),
        encoding="utf-8",
        newline="\n",
    )

    manifest_files = [
        "FROZEN_INPUTS.json", "PLAN.json", "SOURCE_BINDING.json", "HISTORICAL_CONTEXT.json",
        "LEDGER.jsonl", "SUMMARY.json", "RUN.json", "REPORT.md",
    ]
    manifest = {
        "schema": "cm-sympy-claim-cleanup-audit-manifest/v1",
        "study_id": plan["study_id"],
        "files": [
            {"path": name, "sha256": file_sha256(output_dir / name), "bytes": (output_dir / name).stat().st_size}
            for name in manifest_files
        ],
        "complete": all((output_dir / name).is_file() for name in manifest_files),
    }
    write_json(output_dir / "AUDIT_MANIFEST.json", manifest)
    return 0 if summary["mismatch"] == summary["timeout"] == summary["error"] == summary["not_run"] == 0 else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=DEFAULT_AUDIT / "PLAN.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--worker-request", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_request:
        request = json.loads(base64.urlsafe_b64decode(args.worker_request.encode("ascii")))
        try:
            result = execute_worker(request)
        except Exception as exc:
            print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        sys.stdout.buffer.write(canonical_bytes(result))
        return 0
    return run(args.plan, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
