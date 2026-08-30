"""Frozen Linux confirmation for the one-pass, 128-use natural rule policy."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bitset_backend import _eval_words, compile_expr_cse
from cm_expr_serde import expr_from_json
from cmbench.expr.eval import eval_expr_assignment
from cmbench.recognition.features import structural_digest
from cmbench.recognition.rule_pack import ProvedRulePack, compile_rule_pack


SCHEMA = "crse-linux-one-pass-confirmation/v1"
ARMS = ("no_rewrite", "one_pass")
CASE_COUNT = 32
KERNEL_REPEATS = 128
ROUNDS = 5
EXPECTED_CASES_SHA256 = "ebe582d2b0e3b006dbde48e4314f7aba469e731478fdf8dbe0a5dc1aa95e9a98"
EXPECTED_PACK_FILE_SHA256 = "63393b9a7691710d4730b404bac85a9f377e5f9cd2c09047217353b9a8629915"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def packed_sha(value: int, n_vars: int) -> str:
    return hashlib.sha256(value.to_bytes(1 << max(0, n_vars - 3), "little")).hexdigest()


def scalar_reference(expr, n_vars: int) -> int:
    value = 0
    for assignment in range(1 << n_vars):
        values = {f"x{index}": (assignment >> (n_vars - 1 - index)) & 1
                  for index in range(n_vars)}
        if eval_expr_assignment(expr, values):
            value |= 1 << assignment
    return value


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = max(0, min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1))
    return ordered[position]


def load_cases(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if sha256_file(path) != EXPECTED_CASES_SHA256:
        raise ValueError("frozen Linux case artifact hash mismatch")
    raw = path.read_bytes()
    if len(raw) > 1_000_000:
        raise ValueError("frozen Linux case artifact exceeds 1 MB")
    document = json.loads(raw,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite input")))
    if (document.get("schema") != "crse-natural-epfl-rule-selection/v1"
            or document.get("training_use") is not False
            or document.get("prior_epfl_slices_overlap") is not False
            or document.get("support_range") != [9, 12]
            or len(document.get("cases", [])) != CASE_COUNT
            or len(document.get("selected_circuits", [])) != CASE_COUNT):
        raise ValueError("frozen Linux case contract disagreement")
    result = []
    seen = set()
    for case, circuit in zip(document["cases"], document["selected_circuits"]):
        case_id, n_vars = case.get("case_id"), case.get("n_vars")
        if (type(case_id) is not str or not case_id or case_id in seen
                or type(circuit) is not str or not circuit
                or type(n_vars) is not int or not 9 <= n_vars <= 12):
            raise ValueError("invalid frozen Linux case identity")
        seen.add(case_id)
        expression = expr_from_json(case["expression_v2"])
        if structural_digest(expression) != case.get("structural_sha256"):
            raise ValueError("frozen Linux case structural hash mismatch")
        result.append({"case_id": case_id, "circuit": circuit, "n_vars": n_vars,
            "expression": expression, "source_sha256": case["structural_sha256"]})
    return result, document


def measure(cases, matcher, references, round_index: int, arm: str) -> dict[str, Any]:
    rewrite_ns = cse_build_ns = kernel_ns = mismatches = 0
    details = []
    for case in cases:
        applications = conflicts = 0
        case_rewrite_ns = 0
        by_rule = {rule_id: 0 for rule_id in matcher.rule_ids}
        if arm == "one_pass":
            started = time.perf_counter_ns()
            rewrite = matcher.rewrite(case["expression"], case["n_vars"])
            case_rewrite_ns = max(1, time.perf_counter_ns() - started)
            rewrite_ns += case_rewrite_ns
            result = rewrite.result
            applications, conflicts = rewrite.applications, rewrite.conflicts
            by_rule = dict(rewrite.applications_by_rule)
        else:
            result = case["expression"]
        variables = tuple(f"x{i}" for i in range(case["n_vars"]))
        started = time.perf_counter_ns()
        program = compile_expr_cse(result, flatten=True)
        build_ns = max(1, time.perf_counter_ns() - started)
        cse_build_ns += build_ns
        started = time.perf_counter_ns()
        value = 0
        for _ in range(KERNEL_REPEATS):
            value = _eval_words(program, variables, {})
        case_kernel_ns = max(1, time.perf_counter_ns() - started)
        kernel_ns += case_kernel_ns
        mismatches += int(value != references[case["case_id"]])
        details.append({"case_id": case["case_id"], "circuit": case["circuit"],
            "n_vars": case["n_vars"], "result_sha256": structural_digest(result),
            "value_sha256": packed_sha(value, case["n_vars"]), "applications": applications,
            "conflicts": conflicts, "applications_by_rule": by_rule,
            "charged_case_ns": case_rewrite_ns + build_ns + case_kernel_ns})
    return {"schema": "crse-linux-one-pass-measurement/v1",
        "status": "ok" if not mismatches else "mismatch", "round": round_index,
        "arm": arm, "case_count": len(cases), "kernel_repeats": KERNEL_REPEATS,
        "rewrite_ns": rewrite_ns, "cse_build_ns": cse_build_ns, "kernel_ns": kernel_ns,
        "total_ns": rewrite_ns + cse_build_ns + kernel_ns, "mismatches": mismatches,
        "cases": details}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    medians = {arm: {metric: int(statistics.median(row[metric] for row in rows if row["arm"] == arm))
                     for metric in ("rewrite_ns", "cse_build_ns", "kernel_ns", "total_ns")}
               for arm in ARMS}
    lookup = {(row["round"], row["arm"], case["case_id"]): case
              for row in rows for case in row["cases"]}
    ratios = []
    circuit_ratios = defaultdict(list)
    for round_index in range(ROUNDS):
        no_row = next(row for row in rows if row["round"] == round_index and row["arm"] == "no_rewrite")
        for base in no_row["cases"]:
            one = lookup[(round_index, "one_pass", base["case_id"])]
            ratio = base["charged_case_ns"] / one["charged_case_ns"]
            ratios.append(ratio)
            circuit_ratios[base["circuit"]].append(ratio)
    sample = next(row for row in rows if row["round"] == 0 and row["arm"] == "one_pass")
    applications = {rule_id: sum(case["applications_by_rule"][rule_id]
                                  for case in sample["cases"])
                    for rule_id in next(iter(sample["cases"]))["applications_by_rule"]}
    speedup = medians["no_rewrite"]["total_ns"] / medians["one_pass"]["total_ns"]
    return {"median_ns": medians, "one_pass_speedup_over_no_rewrite": speedup,
        "case_speedup_geomean": math.exp(statistics.fmean(math.log(value) for value in ratios)),
        "case_speedup_p05": percentile(ratios, 0.05),
        "case_speedup_p95": percentile(ratios, 0.95),
        "circuits": {circuit: {"samples": len(values), "median_speedup": statistics.median(values)}
                     for circuit, values in sorted(circuit_ratios.items())},
        "applications_by_rule": applications,
        "confirmation_criterion": "exact outputs and median five-round sequence speedup > 1.0",
        "confirmation_passed": speedup > 1.0}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise SystemExit("refusing to overwrite Linux confirmation output")
    args.output.mkdir(parents=True)
    started_wall = time.perf_counter()
    cases, document = load_cases(args.cases)
    if sha256_file(args.pack) != EXPECTED_PACK_FILE_SHA256:
        raise ValueError("frozen Linux proved-pack file hash mismatch")
    matcher = compile_rule_pack(ProvedRulePack.load(args.pack))
    references = {case["case_id"]: scalar_reference(case["expression"], case["n_vars"])
                  for case in cases}
    rows = []
    rng = random.Random("crse-linux-one-pass-arm-order/v1")
    for round_index in range(ROUNDS):
        arms = list(ARMS)
        rng.shuffle(arms)
        for arm in arms:
            rows.append(measure(cases, matcher, references, round_index, arm))
    if any(row["status"] != "ok" for row in rows):
        raise RuntimeError("Linux confirmation exact audit failed")
    summary = summarize(rows)
    result = {"schema": SCHEMA, "status": "complete", "config": {"cases": CASE_COUNT,
        "rounds": ROUNDS, "kernel_repeats": KERNEL_REPEATS, "cpu_threads": 1},
        "input": {"cases_sha256": EXPECTED_CASES_SHA256,
            "pack_file_sha256": EXPECTED_PACK_FILE_SHA256,
            "upstream_commit": document["upstream_commit"], "training_use": False},
        "environment": {"python": sys.version, "platform": platform.platform(),
            "machine": platform.machine(), "processor": platform.processor(),
            "thread_environment": {name: os.environ.get(name) for name in
                ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
        "summaries": summary, "semantic_mismatches": 0,
        "wall_seconds": time.perf_counter() - started_wall,
        "scientific_scope": "cross-machine confirmation of the frozen one-pass 128-use policy on the unchanged D5 cases"}
    (args.output / "measurements.jsonl").write_bytes(b"".join(canonical(row) + b"\n" for row in rows))
    (args.output / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True,
        allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    files = [args.output / "measurements.jsonl", args.output / "summary.json"]
    (args.output / "manifest.json").write_text(json.dumps({"schema": "crse-linux-one-pass-artifacts/v1",
        "files_sha256": {path.name: sha256_file(path) for path in files}},
        indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "complete", "speedup": summary["one_pass_speedup_over_no_rewrite"],
        "confirmation_passed": summary["confirmation_passed"], "semantic_mismatches": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
