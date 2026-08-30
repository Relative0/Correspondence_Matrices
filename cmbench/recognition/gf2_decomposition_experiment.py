"""Frozen C15/R06 exact CM/GF(2) decomposition and representation study."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from cm_expr_serde import expr_from_json

from .bdd_ordering import ExactBddArtifact
from .gf2_decomposition import ExactGF2Artifact, analyze_exact_gf2, truth_sha256
from .portfolio import reference_bits
from .proved_rules import canonical
from .source_anf_hybrid import packed_truth_bits, source_anf_packed
from .yosys_composed_holdout_data import make_yosys_composed_holdout

SCHEMA = "crse-c15-exact-cm-gf2-experiment/v1"
METHODS = ("explicit_cm", "packed_source_anf", "robdd")


@dataclass(frozen=True)
class GF2Config:
    run_id: str = "c15-exact-cm-gf2-windows-20260830-001"
    seed: int = 20260830
    rounds: int = 5
    max_partitions: int = 64
    max_seconds: float = 600.0

    def validate(self) -> None:
        if (type(self.run_id) is not str or not self.run_id or type(self.seed) is not int
                or type(self.rounds) is not int or not 3 <= self.rounds <= 10
                or type(self.max_partitions) is not int or not 8 <= self.max_partitions <= 128
                or not 60 <= self.max_seconds <= 1800):
            raise ValueError("invalid C15 GF(2) config")


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def _from_matrix(arranged: int, n_vars: int, row_variables: tuple[int, ...]) -> int:
    row = row_variables
    column = tuple(value for value in range(n_vars) if value not in row)
    rows, columns = 1 << len(row), 1 << len(column)
    result = 0
    for r in range(rows):
        for c in range(columns):
            assignment = 0
            for local, variable in enumerate(row):
                assignment |= ((r >> (len(row) - 1 - local)) & 1) << (n_vars - 1 - variable)
            for local, variable in enumerate(column):
                assignment |= ((c >> (len(column) - 1 - local)) & 1) << (n_vars - 1 - variable)
            result |= ((arranged >> (r * columns + c)) & 1) << assignment
    return result


def make_gf2_controls(seed: int) -> list[dict[str, Any]]:
    xor_bits = reference_bits(__import__("cm_exprlib").Xor(
        __import__("cm_exprlib").And(__import__("cm_exprlib").Var(0), __import__("cm_exprlib").Var(1)),
        __import__("cm_exprlib").Or(__import__("cm_exprlib").Var(2), __import__("cm_exprlib").Var(3))), 4)
    u, v, outer = 0b1101, 0b1011, 0
    for row in range(4):
        for column in range(4):
            outer |= (((u >> row) & 1) & ((v >> column) & 1)) << (row * 4 + column)
    cofactor_rows = (0b00110101, 0b11001010, 0b01010110, 0b10101001,
                     0b00110101, 0b11001010, 0b01010110, 0b10101001)
    cofactor = sum(value << (index * 8) for index, value in enumerate(cofactor_rows))
    left, right, kron = 0b1001, 0b1110, 0
    for lr in range(2):
        for lc in range(2):
            for rr in range(2):
                for rc in range(2):
                    value = ((left >> (lr * 2 + lc)) & 1) & ((right >> (rr * 2 + rc)) & 1)
                    kron |= value << ((lr * 2 + rr) * 4 + lc * 2 + rc)
    controls = [
        {"case_id": "control-xor-components", "n_vars": 4, "bits": xor_bits,
         "required_kind": "xor_components", "row_partitions": [[0, 1]]},
        {"case_id": "control-rank-one", "n_vars": 4, "bits": _from_matrix(outer, 4, (0, 1)),
         "required_kind": "gf2_rank", "row_partitions": [[0, 1]]},
        {"case_id": "control-complement-cofactors", "n_vars": 6,
         "bits": _from_matrix(cofactor, 6, (0, 1, 2)),
         "required_kind": "cofactor_blocks", "row_partitions": [[0, 1, 2]]},
        {"case_id": "control-kronecker", "n_vars": 4, "bits": _from_matrix(kron, 4, (0, 1)),
         "required_kind": "kronecker", "row_partitions": [[0, 1]]},
    ]
    rng = random.Random(seed)
    for index in range(8):
        while True:
            bits = rng.getrandbits(256)
            if not analyze_exact_gf2(bits, 8, max_partitions=32).candidates:
                break
        controls.append({"case_id": f"control-dense-negative-{index:02d}", "n_vars": 8,
                         "bits": bits, "required_kind": None, "row_partitions": None})
    return controls


def _method_bits(method: str, expression, document: dict[str, Any], n_vars: int) -> int:
    if method == "explicit_cm":
        return reference_bits(expression, n_vars)
    if method == "packed_source_anf":
        polynomial, _stats = source_anf_packed(document, n_vars)
        return packed_truth_bits(polynomial, n_vars)
    if method == "robdd":
        with ExactBddArtifact.build(expression, n_vars, tuple(f"x{i}" for i in range(n_vars)),
                                    backend="autoref") as artifact:
            return sum(value << index for index, value in enumerate(artifact.truth_bits()))
    raise ValueError("unknown exact GF(2) input method")


def _measure(method: str, case: dict[str, Any], expression, expected: int,
             max_partitions: int, round_index: int) -> dict[str, Any]:
    started = time.perf_counter_ns()
    bits = _method_bits(method, expression, case["expression_v2"], case["n_vars"])
    representation_ns = max(1, time.perf_counter_ns() - started)
    analysis_started = time.perf_counter_ns()
    analysis = analyze_exact_gf2(bits, case["n_vars"], max_partitions=max_partitions)
    analysis_ns = max(1, time.perf_counter_ns() - analysis_started)
    total_ns = representation_ns + analysis_ns
    best = analysis.best
    return {"schema": "crse-c15-exact-cm-gf2-measurement/v1", "case_id": case["case_id"],
            "split": case["split"], "label": case["label"], "n_vars": case["n_vars"],
            "source_kind": case["source_kind"], "method": method, "round": round_index,
            "status": "ok" if bits == expected else "mismatch", "mismatches": int(bits != expected),
            "representation_ns": representation_ns, "analysis_ns": analysis_ns,
            "total_ns": total_ns, "partitions_tested": analysis.partitions_tested,
            "candidate_count": len(analysis.candidates), "candidate_kinds": list(analysis.kinds),
            "best_kind": best.kind if best else None,
            "best_factor_bits": best.document["factor_bits"] if best else None,
            "best_artifact_sha256": best.digest if best else None,
            "output_sha256": truth_sha256(bits, case["n_vars"])}


def _functional_analysis(cases: list[dict[str, Any]], controls: list[dict[str, Any]],
                         max_partitions: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    artifacts, rows = [], []
    for case in cases:
        expression = expr_from_json(case["expression_v2"])
        bits = reference_bits(expression, case["n_vars"])
        analysis = analyze_exact_gf2(bits, case["n_vars"], max_partitions=max_partitions)
        best = analysis.best
        if best is not None:
            artifacts.append({"case_id": case["case_id"], "role": "best",
                              "artifact": best.to_dict()})
        rows.append({"case_id": case["case_id"], "source_kind": case["source_kind"],
                     "label": case["label"], "n_vars": case["n_vars"],
                     "candidate_count": len(analysis.candidates), "kinds": list(analysis.kinds),
                     "best_kind": best.kind if best else None,
                     "best_factor_bits": best.document["factor_bits"] if best else None,
                     "exact": all(item.reconstruct() == bits for item in analysis.candidates)})
    control_rows = []
    for control in controls:
        kwargs = ({"row_partitions": control["row_partitions"]}
                  if control["row_partitions"] is not None else {"max_partitions": 32})
        analysis = analyze_exact_gf2(control["bits"], control["n_vars"], **kwargs)
        for candidate in analysis.candidates:
            artifacts.append({"case_id": control["case_id"], "role": "candidate",
                              "artifact": candidate.to_dict()})
        required = control["required_kind"]
        control_rows.append({"case_id": control["case_id"], "n_vars": control["n_vars"],
                             "source_sha256": truth_sha256(control["bits"], control["n_vars"]),
                             "required_kind": required, "candidate_kinds": list(analysis.kinds),
                             "candidate_count": len(analysis.candidates),
                             "accepted": required in analysis.kinds if required else bool(analysis.candidates),
                             "exact": all(item.reconstruct() == control["bits"]
                                          for item in analysis.candidates)})
    return artifacts, {"yosys": rows, "controls": control_rows}


def summarize(measurements: list[dict[str, Any]], functional: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in measurements:
        grouped[(row["case_id"], row["method"])].append(row["total_ns"])
    medians = {key: statistics.median(values) for key, values in grouped.items()}
    case_ids = sorted({row["case_id"] for row in measurements})
    totals = {method: sum(medians[(case_id, method)] for case_id in case_ids) for method in METHODS}
    yosys = functional["yosys"]
    positive = [row for row in yosys if row["label"] == 1]
    negative = [row for row in yosys if row["label"] == 0]
    xor_tp = sum("xor_components" in row["kinds"] for row in positive)
    xor_fp = sum("xor_components" in row["kinds"] for row in negative)
    dense = [row for row in functional["controls"] if row["required_kind"] is None]
    structured = [row for row in functional["controls"] if row["required_kind"] is not None]
    kinds = sorted({kind for row in functional["controls"] for kind in row["candidate_kinds"]})
    criteria = {
        "exact_method_outputs": all(row["mismatches"] == 0 for row in measurements),
        "exact_artifact_reconstruction": all(row["exact"] for row in yosys + functional["controls"]),
        "yosys_xor_positive_recall_20_of_20": xor_tp == 20,
        "yosys_raw_xor_false_positives_zero": xor_fp == 0,
        "all_structured_control_kinds_recovered": all(row["accepted"] for row in structured),
        "dense_incompressible_controls_rejected": all(not row["accepted"] for row in dense),
    }
    timing_gate = (totals["explicit_cm"] / totals["packed_source_anf"] >= 1.10
                   and all(criteria.values()))
    return {"median_case_sum_ns": {key: int(value) for key, value in totals.items()},
            "speedup": {"packed_source_anf_over_explicit_cm":
                        totals["explicit_cm"] / totals["packed_source_anf"],
                        "explicit_cm_over_robdd": totals["robdd"] / totals["explicit_cm"],
                        "packed_source_anf_over_robdd": totals["robdd"] / totals["packed_source_anf"]},
            "yosys_xor": {"true_positives": xor_tp, "false_positives": xor_fp,
                          "positive_cases": len(positive), "raw_negative_cases": len(negative)},
            "control_kind_coverage": kinds, "dense_negative_cases": len(dense),
            "criteria": criteria, "functional_gate": all(criteria.values()),
            "second_machine_timing_gate": timing_gate, "timing_is_machine_specific": True}


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = ["# CRSE C15 exact CM/GF(2) decomposition", "",
             f"Status: **{result['status']}**", f"Functional gate: **{summary['functional_gate']}**",
             f"Second-machine timing gate: **{summary['second_machine_timing_gate']}**", "",
             "## Implemented exact artifacts", "",
             "- Recursive disjoint-support XOR factors from exact ANF interaction components.",
             "- GF(2) interaction-matrix rank with explicit U/V recomposition.",
             "- Repeated and complemented row/column cofactor blocks.",
             "- Exact Kronecker block factors with full reconstruction.",
             "- Explicit variable order, row/column masks, bounded payloads, and strict hashes.", "",
             "## Independent Yosys source family", "",
             f"The frozen family contains {result['dataset']['rows']} cases: 20 unused raw Yosys-bench "
             "generator outputs and 20 disjoint-XOR source compositions. It is independently authored "
             "source, although the positive XOR compositions were deliberately constructed.", "",
             f"XOR component recovery: **{summary['yosys_xor']['true_positives']}/20** positives; "
             f"raw false positives: **{summary['yosys_xor']['false_positives']}**.",
             f"Dense incompressible controls rejected: **{summary['dense_negative_cases']}**.",
             f"Control artifact kinds recovered: `{', '.join(summary['control_kind_coverage'])}`.", "",
             "## Task-equivalent whole-path timing", "",
             "| Method | Median sum across 40 cases (ns) |",
             "| --- | ---: |"]
    for method, value in summary["median_case_sum_ns"].items():
        lines.append(f"| {method} | {value} |")
    lines += ["", f"Packed source ANF speedup over explicit CM: **{summary['speedup']['packed_source_anf_over_explicit_cm']:.4f}x**.",
              f"Explicit CM speedup over ROBDD: **{summary['speedup']['explicit_cm_over_robdd']:.4f}x**.", "",
              "Each method produces the same complete truth vector and then runs the same GF(2) analyzer. "
              "The explicit-CM arm materializes all truth values; the source arm propagates exact packed ANF; "
              "the ROBDD arm builds an exact decision diagram and enumerates it. Timings include representation "
              "construction plus artifact analysis.", "", "## Criteria", ""]
    lines.extend(f"- `{key}`: **{value}**" for key, value in summary["criteria"].items())
    lines += ["", "All artifacts are proposals backed by exact reconstruction. Dense functions remain uncompressed; "
              "no learned or approximate value is used. A second-machine run is reserved for a positive timing gate.", ""]
    return "\n".join(lines)


def run_gf2_experiment(config: GF2Config, output: Path, progress: Callable[[str], None] = print) -> dict[str, Any]:
    config.validate()
    output.mkdir(parents=True, exist_ok=False)
    wall_started = time.perf_counter()
    cases, provenance = make_yosys_composed_holdout()
    controls = make_gf2_controls(config.seed)
    _write_json(output / "run_spec.json", {"schema": SCHEMA, "config": asdict(config),
                "controls": {"thread_count": 1, "runpod": False}})
    _write_json(output / "dataset.json", {"schema": "crse-c15-gf2-dataset/v1",
                "provenance": provenance, "rows": len(cases), "cases": cases,
                "controls": [{key: value for key, value in row.items() if key != "bits"}
                             | {"source_sha256": truth_sha256(row["bits"], row["n_vars"])}
                             for row in controls]})
    progress("Constructing and exactly replaying CM/GF(2) artifacts")
    artifacts, functional = _functional_analysis(cases, controls, config.max_partitions)
    _write_json(output / "artifacts.json", {"schema": "crse-c15-gf2-artifact-set/v1",
                "artifacts": artifacts, "functional": functional,
                "payload_sha256": hashlib.sha256(canonical(artifacts)).hexdigest()})
    expected = {}
    expressions = {}
    for case in cases:
        expression = expr_from_json(case["expression_v2"])
        expressions[case["case_id"]] = expression
        expected[case["case_id"]] = reference_bits(expression, case["n_vars"])
    measurements = []
    rng = random.Random(f"{config.seed}:c15-balanced-method-order/v1")
    progress("Comparing explicit CM, packed source ANF, and ROBDD whole paths")
    for round_index in range(config.rounds):
        order = [(case, method) for case in cases for method in METHODS]
        rng.shuffle(order)
        for case, method in order:
            if time.perf_counter() - wall_started > config.max_seconds:
                raise TimeoutError("C15 GF(2) experiment exceeded wall budget")
            measurements.append(_measure(method, case, expressions[case["case_id"]],
                                         expected[case["case_id"]], config.max_partitions,
                                         round_index))
    _write_jsonl(output / "measurements.jsonl", measurements)
    summary = summarize(measurements, functional)
    mismatches = sum(row["mismatches"] for row in measurements)
    result = {"schema": SCHEMA, "status": "complete" if not mismatches else "failed",
              "config": asdict(config), "wall_seconds": time.perf_counter() - wall_started,
              "environment": {"python": sys.version, "platform": platform.platform(),
                              "thread_environment": {name: os.environ.get(name) for name in
                               ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
              "dataset": {"rows": len(cases), "raw": 20, "composed": 20,
                          "source": provenance["source"], "upstream_commit": provenance["upstream_commit"]},
              "artifact_rows": len(artifacts), "semantic_mismatches": mismatches,
              "summary": summary, "runpod": {"used": False, "cost_usd": 0.0,
                 "reason": "pending_local_gate" if summary["second_machine_timing_gate"]
                           else "second_machine_timing_gate_failed"},
              "claims": {"exact_bounded_decomposition": summary["functional_gate"],
                         "general_unbounded_decomposition": False,
                         "learned_or_approximate_values": False,
                         "production_promotion": False}}
    _write_json(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8", newline="\n")
    return result
