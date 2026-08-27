"""Correctness-gated EPFL real-cone/generated-context benchmark pilot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from bitset_backend import (  # noqa: E402
    PreparedFlatEvaluation,
    _bind_flat_program,
    _eval_prepared_flat,
    _eval_words,
    compile_expr_cse,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json  # noqa: E402
from cm_ir import (  # noqa: E402
    clear_cm_ir_persistent_cache,
    compile_expr_to_cm_ir,
)


CORPUS = REPO / "deliverables_n22_24" / "CM_gap_epfl_corpus_2026_08_03.jsonl"
EXPECTED_CORPUS_SHA256 = "bb98f14a5525a2d869a7ad80e25e879fd176e78ad6d01c51385edc947f2806ac"
DEFAULT_OUTPUT = HERE / "runs" / "hardware-epfl-context-pilot-2026-08-27"
FIXED_FRACTIONS = (0.0, 0.25, 0.50, 0.75)
CONTEXTS_PER_NONZERO_FRACTION = 4
BOOTSTRAP_DRAWS = 4000
BOOTSTRAP_SEED = 2026082701


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_records(limit: int = 0) -> list[dict]:
    actual = sha256_file(CORPUS)
    if actual != EXPECTED_CORPUS_SHA256:
        raise SystemExit(f"corpus SHA-256 mismatch: {actual}")
    records = []
    with CORPUS.open(encoding="utf-8") as handle:
        for line in handle:
            document = json.loads(line)
            if document.get("status") == "admitted" and "expression_v2" in document:
                records.append(document)
    if len(records) != 129:
        raise SystemExit(f"expected 129 admitted records, found {len(records)}")
    return records[:limit] if limit else records


def context_seed(record_id: str, fraction: float, index: int) -> int:
    material = f"{record_id}|{fraction:.2f}|{index}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def build_contexts(record: dict) -> list[dict]:
    semantic_k = int(record["sem_support_size"])
    syntactic_k = int(record["synt_support_size"])
    support = tuple(f"x{i}" for i in range(syntactic_k - 1, -1, -1))
    semantic_original = set(record["sem_support_inputs"])
    semantic_positions = {
        index for index, original in enumerate(record["synt_support_inputs"])
        if original in semantic_original
    }
    semantic_support = tuple(name for name in support if int(name[1:]) in semantic_positions)
    if len(semantic_support) != semantic_k:
        raise AssertionError(f"semantic support mapping mismatch: {record['id']}")
    result = [{"context_id": "fixed-000-c00", "fixed_fraction": 0.0, "seed": None, "fixed": {}, "free": support}]
    for fraction in FIXED_FRACTIONS[1:]:
        fixed_count = max(1, min(semantic_k - 1, int(round(semantic_k * fraction))))
        for index in range(CONTEXTS_PER_NONZERO_FRACTION):
            seed = context_seed(record["id"], fraction, index)
            rng = random.Random(seed)
            selected = set(rng.sample(list(semantic_support), fixed_count))
            fixed = {name: int(rng.getrandbits(1)) for name in support if name in selected}
            free = tuple(name for name in support if name not in fixed)
            result.append({
                "context_id": f"fixed-{int(fraction * 100):03d}-c{index:02d}",
                "fixed_fraction": fraction,
                "seed": seed,
                "fixed": fixed,
                "free": free,
            })
    return result


def eval_program(program, free: tuple[str, ...], fixed: dict[str, int]) -> int:
    if len(free) >= 6:
        return _eval_words(program, free, fixed)
    template, full_mask = _bind_flat_program(program, free, fixed)
    return _eval_prepared_flat(PreparedFlatEvaluation(program, template, full_mask, False))


def timed_call_ns(function, batch: int) -> float:
    start = time.perf_counter_ns()
    for _ in range(batch):
        function()
    return (time.perf_counter_ns() - start) / batch


def geomean(values: list[float]) -> float:
    if not values or any(value <= 0 or not math.isfinite(value) for value in values):
        raise ValueError("geomean requires positive finite values")
    return math.exp(statistics.fmean(math.log(value) for value in values))


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def circuit_cluster_summary(rows: list[dict]) -> dict:
    by_circuit: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_circuit[row["circuit"]].append(float(row["cm_over_cse_flat"]))
    circuit_values = {circuit: geomean(values) for circuit, values in by_circuit.items()}
    circuits = sorted(circuit_values)
    observed = geomean([circuit_values[circuit] for circuit in circuits])
    rng = random.Random(BOOTSTRAP_SEED)
    draws = []
    for _ in range(BOOTSTRAP_DRAWS):
        sampled = [circuit_values[rng.choice(circuits)] for _ in circuits]
        draws.append(geomean(sampled))
    return {
        "circuit_count": len(circuits),
        "geomean": observed,
        "ci95": [percentile(draws, 0.025), percentile(draws, 0.975)],
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "per_circuit_geomean": circuit_values,
    }


def benchmark(records: list[dict], rounds: int, batch: int) -> tuple[list[dict], dict]:
    expressions = [expr_from_json(record["expression_v2"]) for record in records]

    cse_programs = []
    cse_compile_ns = []
    fresh_cm_compile_ns = []
    for expression in expressions:
        start = time.perf_counter_ns()
        cse_programs.append(compile_expr_cse(expression, flatten=True))
        cse_compile_ns.append(time.perf_counter_ns() - start)
        start = time.perf_counter_ns()
        compile_expr_to_cm_ir(expression, persistent_cache=False, reuse_cache=False)
        fresh_cm_compile_ns.append(time.perf_counter_ns() - start)

    clear_cm_ir_persistent_cache()
    cm_nodes = []
    family_compile_rows = []
    for record_index, (record, expression) in enumerate(zip(records, expressions)):
        diagnostics: dict = {}
        start = time.perf_counter_ns()
        node = compile_expr_to_cm_ir(
            expression,
            diagnostics=diagnostics,
            persistent_cache=True,
            reuse_cache=False,
        )
        elapsed = time.perf_counter_ns() - start
        cm_nodes.append(node)
        family_compile_rows.append({
            "id": record["id"],
            "circuit": record["circuit"],
            "compile_ns": elapsed,
            "cm_fresh_compile_ns": fresh_cm_compile_ns[record_index],
            "cse_flat_compile_ns": cse_compile_ns[record_index],
            "persistent_hits": int(diagnostics.get("ir_persistent_cache_hits", 0)),
            "persistent_misses": int(diagnostics.get("ir_persistent_cache_misses", 0)),
            "persistent_size": int(diagnostics.get("ir_persistent_cache_size", 0)),
        })

    cm_programs = [get_flat_program(node) for node in cm_nodes]
    raw_rows = []
    all_free_hash_checks = 0
    for record_index, (record, cm_program, cse_program) in enumerate(zip(records, cm_programs, cse_programs)):
        cm_metrics = program_metrics(cm_program)
        cse_metrics = program_metrics(cse_program)
        semantic_k = int(record["sem_support_size"])
        syntactic_k = int(record["synt_support_size"])
        for context_index, context in enumerate(build_contexts(record)):
            free = tuple(context["free"])
            fixed = dict(context["fixed"])
            cm_value = eval_program(cm_program, free, fixed)
            cse_value = eval_program(cse_program, free, fixed)
            if cm_value != cse_value:
                raise AssertionError(f"packed mismatch: {record['id']} {context['context_id']}")
            if not fixed:
                packed = int(cm_value).to_bytes(max(1, (1 << syntactic_k) // 8), "little")
                actual_truth = hashlib.sha256(packed).hexdigest()
                if actual_truth != record["truth_sha256"]:
                    raise AssertionError(f"frozen truth mismatch: {record['id']}")
                all_free_hash_checks += 1

            cm_samples = []
            cse_samples = []
            cm_call = lambda: eval_program(cm_program, free, fixed)
            cse_call = lambda: eval_program(cse_program, free, fixed)
            for round_index in range(rounds):
                if (record_index + context_index + round_index) % 2:
                    cm_samples.append(timed_call_ns(cm_call, batch))
                    cse_samples.append(timed_call_ns(cse_call, batch))
                else:
                    cse_samples.append(timed_call_ns(cse_call, batch))
                    cm_samples.append(timed_call_ns(cm_call, batch))
            cm_ns = statistics.median(cm_samples)
            cse_ns = statistics.median(cse_samples)
            raw_rows.append({
                "id": record["id"],
                "category": record["category"],
                "circuit": record["circuit"],
                "root_kind": record["root_kind"],
                "semantic_live_k": semantic_k,
                "syntactic_k": syntactic_k,
                "context_id": context["context_id"],
                "fixed_fraction": context["fixed_fraction"],
                "fixed_count": len(fixed),
                "residual_semantic_k": semantic_k - len(fixed),
                "residual_syntactic_k": len(free),
                "context_seed": context["seed"],
                "fixed_json": json.dumps(fixed, sort_keys=True, separators=(",", ":")),
                "packed_equal": True,
                "cm_ns_median": cm_ns,
                "cse_flat_ns_median": cse_ns,
                "cm_over_cse_flat": cm_ns / cse_ns,
                "cm_flat_instructions": cm_metrics["flat_instructions"],
                "cse_flat_instructions": cse_metrics["flat_instructions"],
                "cm_executed_word_ops": cm_metrics["executed_word_ops"],
                "cse_executed_word_ops": cse_metrics["executed_word_ops"],
            })

    primary = circuit_cluster_summary(raw_rows)
    by_fraction = {}
    for fraction in FIXED_FRACTIONS:
        subset = [row for row in raw_rows if float(row["fixed_fraction"]) == fraction]
        by_fraction[f"{fraction:.2f}"] = circuit_cluster_summary(subset)
    hits = sum(row["persistent_hits"] for row in family_compile_rows)
    misses = sum(row["persistent_misses"] for row in family_compile_rows)
    summary = {
        "status": "complete",
        "scope": "real EPFL circuit cones with deterministic generated partial contexts",
        "claim_boundary": "not a natural design-history trace and not evidence of domain dominance",
        "correctness": {
            "context_rows": len(raw_rows),
            "packed_mismatches": 0,
            "all_free_frozen_truth_checks": all_free_hash_checks,
        },
        "corpus": {
            "sha256": EXPECTED_CORPUS_SHA256,
            "admitted_records_used": len(records),
            "circuits": len({record["circuit"] for record in records}),
            "categories": sorted({record["category"] for record in records}),
        },
        "measurement": {"rounds": rounds, "batch_per_round": batch, "arm_order": "deterministically alternated"},
        "primary_circuit_clustered": primary,
        "row_weighted": {
            "geomean": geomean([row["cm_over_cse_flat"] for row in raw_rows]),
            "median": statistics.median(row["cm_over_cse_flat"] for row in raw_rows),
        },
        "by_fixed_fraction_circuit_clustered": by_fraction,
        "construction_descriptive": {
            "cse_flat_compile_ns_geomean": geomean([float(value) for value in cse_compile_ns]),
            "cm_fresh_compile_ns_geomean": geomean([float(value) for value in fresh_cm_compile_ns]),
            "cm_family_compile_ns_geomean": geomean([float(row["compile_ns"]) for row in family_compile_rows]),
            "cm_persistent_hits": hits,
            "cm_persistent_misses": misses,
            "cm_persistent_hit_fraction": hits / (hits + misses) if hits + misses else None,
        },
        "followup_gate": {
            "rule": "geomean <= 0.95 and circuit-bootstrap upper CI < 1.0, with zero mismatches",
            "passed": bool(primary["geomean"] <= 0.95 and primary["ci95"][1] < 1.0),
        },
        "family_compile_rows": family_compile_rows,
    }
    return raw_rows, summary


def write_outputs(output: Path, raw_rows: list[dict], summary: dict, rounds: int, batch: int) -> None:
    output.mkdir(parents=True, exist_ok=False)
    raw_path = output / "raw.csv"
    with raw_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(raw_rows[0]))
        writer.writeheader()
        writer.writerows(raw_rows)
    summary_path = output / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:
        revision = "unavailable"
    manifest = {
        "schema_version": "1.0",
        "protocol": "HARDWARE-EPFL-CONTEXT-PILOT-PROTOCOL-V2.md",
        "repository_revision": revision,
        "corpus_path": CORPUS.relative_to(REPO).as_posix(),
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "rounds": rounds,
        "batch_per_round": batch,
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "outputs": ["raw.csv", "summary.json"],
    }
    manifest_path = output / "RUN-MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    checksum_paths = [raw_path, summary_path, manifest_path]
    checksum_text = "\n".join(f"{sha256_file(path)}  {path.name}" for path in checksum_paths) + "\n"
    (output / "CHECKSUMS.sha256").write_text(checksum_text, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rounds", type=int, default=7)
    parser.add_argument("--batch", type=int, default=20)
    parser.add_argument("--limit", type=int, default=0, help="debug only; zero uses all 129 admitted records")
    args = parser.parse_args()
    if args.rounds < 1 or args.batch < 1 or args.limit < 0:
        parser.error("rounds and batch must be positive; limit must be non-negative")
    records = load_records(args.limit)
    raw_rows, summary = benchmark(records, args.rounds, args.batch)
    write_outputs(args.output.resolve(), raw_rows, summary, args.rounds, args.batch)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "records": len(records),
        "context_rows": len(raw_rows),
        "geomean": summary["primary_circuit_clustered"]["geomean"],
        "ci95": summary["primary_circuit_clustered"]["ci95"],
        "followup_gate_passed": summary["followup_gate"]["passed"],
    }, indent=2))


if __name__ == "__main__":
    main()
