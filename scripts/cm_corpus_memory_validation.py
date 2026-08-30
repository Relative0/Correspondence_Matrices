#!/usr/bin/env python3
"""Frozen BX1/B2/EPFL compatibility, oracle, tracemalloc, and RSS study.

Selection freezing is a bounded local metadata operation.  The study itself is
Runpod-only: every measured job runs in an isolated child, while the parent
polls Linux ``/proc/<pid>/status`` for whole-child RSS.  Semantic truth comes
from a direct scalar evaluator over the serialized v2 DAG; it does not import
CM compilation, normalization, or bitset evaluation code.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "cm-corpus-memory-validation/v1"
SELECTION_SCHEMA = "cm-corpus-memory-selection/v1"
CORPUS_PATHS = {
    "bx1": Path("deliverables_n22_24/bx1_crossover_2026_08_03/CM_bx1_crossover_corpus_2026_08_03.jsonl"),
    "b2": Path("deliverables_n22_24/b2_wrapper_2026_08_03/CM_b2_wrapper_corpus_2026_08_03.jsonl"),
    "epfl": Path("deliverables_n22_24/CM_gap_epfl_corpus_2026_08_03.jsonl"),
}
TARGET_SUPPORTS = {
    "bx1": (6, 8, 12, 16),
    "b2": (6, 8, 12, 16),
    "epfl": tuple(range(8, 17)),
}
REPRESENTATIONS = ("dense", "bigint", "words")
EXPECTED_CASES = 35
EXPECTED_JOBS = 420
EXPECTED_CALLS = 630
MAX_CORPUS_BYTES = 2 << 20
MAX_MANIFEST_BYTES = 256 << 10
MAX_JOB_BYTES = 512 << 10
MAX_CHILD_OUTPUT_BYTES = 64 << 10
MAX_NODES = 512
MAX_EDGES = 1024
MAX_K = 16
MAX_TEMPORARY = 32 << 20
MAX_STUDY_SECONDS = 600
MAX_CHILD_SECONDS = 30
RSS_POLL_SECONDS = 0.005


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def write_json_exclusive(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _integer(value: Any, field: str, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} exceeds {maximum}")
    return value


def read_corpus(path: Path) -> list[dict[str, Any]]:
    if path.stat().st_size > MAX_CORPUS_BYTES:
        raise ValueError(f"corpus exceeds {MAX_CORPUS_BYTES} bytes: {path}")
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: record must be an object")
            if "expression_v2" in record:
                records.append(record)
    return records


def record_k(record: Mapping[str, Any]) -> int:
    return _integer(
        record.get("live_k") or record.get("stratum_live_k") or record.get("sem_support_size"),
        "live k", MAX_K,
    )


def record_shape(record: Mapping[str, Any]) -> tuple[int, int, int]:
    document = record.get("expression_v2")
    if not isinstance(document, Mapping) or document.get("version") != 2:
        raise ValueError("record lacks a v2 expression")
    nodes = document.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("expression nodes must be a list")
    node_count = len(nodes)
    edge_count = sum(int(isinstance(row, Mapping) and "a" in row) + int(isinstance(row, Mapping) and "b" in row)
                     for row in nodes)
    syntactic_k = _integer(record.get("synt_support_size", record_k(record)), "syntactic k", MAX_K)
    return node_count, edge_count, syntactic_k


def eligible_record(record: Mapping[str, Any]) -> bool:
    try:
        k = record_k(record)
        nodes, edges, syntactic_k = record_shape(record)
    except ValueError:
        return False
    truth = record.get("truth_sha256")
    return (
        2 <= k <= MAX_K and syntactic_k <= MAX_K and nodes <= MAX_NODES and edges <= MAX_EDGES
        and isinstance(truth, str) and len(truth) == 64
        and all(ch in "0123456789abcdef" for ch in truth)
    )


def freeze_selection(root: Path = ROOT) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    corpus_docs: dict[str, Any] = {}
    for corpus in ("bx1", "b2", "epfl"):
        relative = CORPUS_PATHS[corpus]
        path = root / relative
        records = read_corpus(path)
        corpus_docs[corpus] = {
            "path": relative.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "expression_records": len(records),
        }
        for k in TARGET_SUPPORTS[corpus]:
            matches = [(index, record) for index, record in enumerate(records)
                       if eligible_record(record) and record_k(record) == k]
            if len(matches) < 2:
                raise ValueError(f"{corpus} k={k} has fewer than two eligible records")
            for selection_rank, (role, selected) in enumerate(
                (("calibration-corpus", matches[0]), ("heldout-corpus", matches[-1])), 1
            ):
                record_index, record = selected
                nodes, edges, syntactic_k = record_shape(record)
                cases.append({
                    "case_id": f"{corpus}-k{k}-{'first' if selection_rank == 1 else 'last'}",
                    "corpus": corpus,
                    "record_index": record_index,
                    "record_id": record.get("id"),
                    "record_sha256": canonical_sha256(record),
                    "expression_sha256": canonical_sha256(record["expression_v2"]),
                    "truth_sha256": record["truth_sha256"],
                    "k": k,
                    "syntactic_k": syntactic_k,
                    "nodes": nodes,
                    "edges": edges,
                    "role": role,
                    "selection": "first eligible in corpus order" if selection_rank == 1
                                 else "last eligible in corpus order",
                })
        if corpus == "epfl":
            selected_indices = {case["record_index"] for case in cases if case["corpus"] == corpus}
            dead_axis = [
                (index, record) for index, record in enumerate(records)
                if eligible_record(record) and record_shape(record)[2] > record_k(record)
                and index not in selected_indices
            ]
            for ordinal, (record_index, record) in enumerate(dead_axis, 1):
                nodes, edges, syntactic_k = record_shape(record)
                k = record_k(record)
                cases.append({
                    "case_id": f"epfl-k{k}-dead-axis-{ordinal}",
                    "corpus": corpus, "record_index": record_index,
                    "record_id": record.get("id"), "record_sha256": canonical_sha256(record),
                    "expression_sha256": canonical_sha256(record["expression_v2"]),
                    "truth_sha256": record["truth_sha256"], "k": k,
                    "syntactic_k": syntactic_k, "nodes": nodes, "edges": edges,
                    "role": "heldout-corpus",
                    "selection": "all eligible EPFL records with syntactic support larger than semantic support",
                })
    if len(cases) != EXPECTED_CASES:
        raise AssertionError(f"expected {EXPECTED_CASES} cases, got {len(cases)}")
    role_counts = Counter(case["role"] for case in cases)
    if role_counts != {"calibration-corpus": 17, "heldout-corpus": 18}:
        raise AssertionError(f"unexpected split: {role_counts}")
    return {
        "schema": SELECTION_SCHEMA,
        "selection_rule": (
            "For each preregistered corpus/support stratum, take the first and last eligible "
            "expression record in immutable corpus order, then add every otherwise-unselected eligible "
            "EPFL record whose syntactic support exceeds semantic support. Selection uses no timing or memory outcome."
        ),
        "eligibility": {
            "live_k": [2, MAX_K], "syntactic_k_max": MAX_K,
            "nodes_max": MAX_NODES, "edges_max": MAX_EDGES,
            "requires_v2_expression": True, "requires_sha256_truth": True,
        },
        "supports": {name: list(values) for name, values in TARGET_SUPPORTS.items()},
        "corpora": corpus_docs,
        "cases": cases,
        "execution": {
            "representations": list(REPRESENTATIONS), "schedules": ["cold", "warm"],
            "repetitions": 3, "cold_processes_per_representation_case": 3,
            "warm_processes_per_representation_case": 1,
            "planned_jobs": EXPECTED_JOBS, "planned_calls": EXPECTED_CALLS,
        },
        "calibration_policy": (
            "The split is frozen for a possible later fit. This compatibility study does not fit "
            "or alter the candidate, and heldout-corpus rows remain untouched."
        ),
    }


def load_selection(path: Path, root: Path = ROOT) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("selection manifest exceeds input cap")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema") != SELECTION_SCHEMA:
        raise ValueError("unexpected selection schema")
    cases = manifest.get("cases")
    execution = manifest.get("execution")
    if not isinstance(cases, list) or len(cases) != EXPECTED_CASES or not isinstance(execution, dict):
        raise ValueError("selection case count mismatch")
    if (execution.get("planned_jobs") != EXPECTED_JOBS or execution.get("planned_calls") != EXPECTED_CALLS
            or execution.get("repetitions") != 3 or execution.get("representations") != list(REPRESENTATIONS)
            or execution.get("schedules") != ["cold", "warm"]):
        raise ValueError("selection execution grid mismatch")

    records_by_case: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for corpus in ("bx1", "b2", "epfl"):
        corpus_doc = manifest.get("corpora", {}).get(corpus)
        if not isinstance(corpus_doc, dict) or corpus_doc.get("path") != CORPUS_PATHS[corpus].as_posix():
            raise ValueError(f"{corpus}: corpus path mismatch")
        corpus_path = root / CORPUS_PATHS[corpus]
        if corpus_path.stat().st_size != corpus_doc.get("bytes") or sha256_file(corpus_path) != corpus_doc.get("sha256"):
            raise ValueError(f"{corpus}: corpus hash/size mismatch")
        records = read_corpus(corpus_path)
        if len(records) != corpus_doc.get("expression_records"):
            raise ValueError(f"{corpus}: corpus record count mismatch")
        for case in [row for row in cases if row.get("corpus") == corpus]:
            case_id = case.get("case_id")
            if not isinstance(case_id, str) or case_id in seen:
                raise ValueError("duplicate or invalid case id")
            seen.add(case_id)
            index = _integer(case.get("record_index"), f"{case_id} record index")
            if index >= len(records):
                raise ValueError(f"{case_id}: record index out of range")
            record = records[index]
            nodes, edges, syntactic_k = record_shape(record)
            checks = {
                "record_id": record.get("id"),
                "record_sha256": canonical_sha256(record),
                "expression_sha256": canonical_sha256(record["expression_v2"]),
                "truth_sha256": record.get("truth_sha256"),
                "k": record_k(record), "syntactic_k": syntactic_k,
                "nodes": nodes, "edges": edges,
            }
            for field, actual in checks.items():
                if case.get(field) != actual:
                    raise ValueError(f"{case_id}: {field} mismatch")
            if case.get("role") not in {"calibration-corpus", "heldout-corpus"}:
                raise ValueError(f"{case_id}: invalid role")
            records_by_case[case_id] = record
    if len(seen) != EXPECTED_CASES:
        raise ValueError("selection does not cover the expected corpora")
    return manifest, records_by_case


def compile_scalar_dag(document: Mapping[str, Any]) -> tuple[list[tuple[Any, ...]], int, tuple[int, ...]]:
    if document.get("version") != 2 or not isinstance(document.get("nodes"), list):
        raise ValueError("oracle requires a v2 DAG")
    source = document["nodes"]
    if not 1 <= len(source) <= MAX_NODES:
        raise ValueError("oracle DAG node bound")
    program: list[tuple[Any, ...]] = []
    variables: set[int] = set()
    seen_structures: set[tuple[Any, ...]] = set()
    children: list[tuple[int, ...]] = []
    for index, node in enumerate(source):
        if not isinstance(node, Mapping):
            raise ValueError(f"oracle node {index} is not an object")
        op = node.get("op")
        if op == "var":
            var = _integer(node.get("i"), f"oracle node {index} var")
            item = ("var", var)
            variables.add(var)
            refs: tuple[int, ...] = ()
        elif op == "not":
            a = _integer(node.get("a"), f"oracle node {index} ref")
            if a >= index:
                raise ValueError("oracle requires backward references")
            item = ("not", a)
            refs = (a,)
        elif op in {"and", "or", "xor", "imp", "eqv"}:
            a = _integer(node.get("a"), f"oracle node {index} ref a")
            b = _integer(node.get("b"), f"oracle node {index} ref b")
            if a >= index or b >= index:
                raise ValueError("oracle requires backward references")
            item = (op, a, b)
            refs = (a, b)
        else:
            raise ValueError(f"oracle node {index}: unsupported op")
        if item in seen_structures:
            raise ValueError("oracle refuses duplicate DAG definitions")
        seen_structures.add(item)
        program.append(item)
        children.append(refs)
    root = _integer(document.get("root"), "oracle root")
    if root != len(program) - 1:
        raise ValueError("oracle requires the root to be the final reachable definition")
    reachable = {root}
    for index in range(root, -1, -1):
        if index in reachable:
            reachable.update(children[index])
    if len(reachable) != len(program):
        raise ValueError("oracle refuses unreachable definitions")
    return program, root, tuple(sorted(variables))


def evaluation_context(corpus: str, record: Mapping[str, Any]) -> tuple[tuple[str, ...], dict[str, int]]:
    _program, _root, variable_indices = compile_scalar_dag(record["expression_v2"])
    all_variables = tuple(f"x{i}" for i in variable_indices)
    live_k = record_k(record)
    if corpus != "epfl":
        if len(all_variables) != live_k:
            raise ValueError("non-EPFL variable/live-k mismatch")
        return all_variables, {}
    syntactic_inputs = record.get("synt_support_inputs")
    semantic_inputs = set(record.get("sem_support_inputs") or ())
    if not isinstance(syntactic_inputs, list) or len(syntactic_inputs) != len(all_variables):
        raise ValueError("EPFL syntactic mapping mismatch")
    live_positions = {index for index, name in enumerate(syntactic_inputs) if name in semantic_inputs}
    variables = tuple(reversed(tuple(name for name in all_variables if int(name[1:]) in live_positions)))
    fixed = {name: 0 for name in all_variables if int(name[1:]) not in live_positions}
    if len(variables) != live_k:
        raise ValueError("EPFL semantic mapping mismatch")
    return variables, fixed


def scalar_oracle_sha256(document: Mapping[str, Any], variables: Sequence[str], fixed: Mapping[str, int]) -> str:
    program, root, variable_indices = compile_scalar_dag(document)
    variable_positions = {name: index for index, name in enumerate(variables)}
    known_names = {f"x{i}" for i in variable_indices}
    if set(variable_positions).intersection(fixed) or set(variable_positions).union(fixed) != known_names:
        raise ValueError("oracle live/fixed variables do not exactly cover the DAG")
    k = len(variables)
    if k > MAX_K:
        raise ValueError("oracle output width exceeds cap")
    rows = 1 << k
    packed = bytearray(max(1, (rows + 7) // 8))
    values = [0] * len(program)
    for row in range(rows):
        for slot, instruction in enumerate(program):
            op = instruction[0]
            if op == "var":
                name = f"x{instruction[1]}"
                if name in fixed:
                    value = int(bool(fixed[name]))
                else:
                    position = variable_positions[name]
                    value = (row >> (k - 1 - position)) & 1
            elif op == "not":
                value = 1 - values[instruction[1]]
            else:
                left, right = values[instruction[1]], values[instruction[2]]
                if op == "and":
                    value = left & right
                elif op == "or":
                    value = left | right
                elif op == "xor":
                    value = left ^ right
                elif op == "imp":
                    value = (1 - left) | right
                else:
                    value = 1 - (left ^ right)
            values[slot] = value
        if values[root]:
            packed[row >> 3] |= 1 << (row & 7)
    return hashlib.sha256(packed).hexdigest()


def oracle_case(corpus: str, record: Mapping[str, Any]) -> dict[str, Any]:
    variables, fixed = evaluation_context(corpus, record)
    live_digest = scalar_oracle_sha256(record["expression_v2"], variables, fixed)
    if corpus == "epfl":
        _program, _root, indices = compile_scalar_dag(record["expression_v2"])
        frozen_variables = tuple(reversed(tuple(f"x{i}" for i in indices)))
        frozen_digest = scalar_oracle_sha256(record["expression_v2"], frozen_variables, {})
    else:
        frozen_digest = live_digest
    if frozen_digest != record.get("truth_sha256"):
        raise AssertionError(f"{record.get('id')}: independent frozen truth mismatch")
    return {
        "method": "direct scalar evaluation of serialized v2 DAG; no CM compiler/bitset imports",
        "variables": list(variables), "fixed": dict(fixed),
        "live_output_sha256": live_digest, "frozen_truth_sha256": frozen_digest,
    }


def parse_proc_status(text: str) -> dict[str, int | None]:
    result: dict[str, int | None] = {"rss_bytes": None, "hwm_bytes": None}
    for line in text.splitlines():
        name, separator, value = line.partition(":")
        if not separator or name not in {"VmRSS", "VmHWM"}:
            continue
        fields = value.split()
        if len(fields) != 2 or fields[1] != "kB" or not fields[0].isdigit():
            raise ValueError(f"malformed {name} in proc status")
        result["rss_bytes" if name == "VmRSS" else "hwm_bytes"] = int(fields[0]) * 1024
    return result


def _monitor_proc(pid: int, stop: threading.Event, samples: list[dict[str, int | None]]) -> None:
    status = Path(f"/proc/{pid}/status")
    while not stop.is_set():
        try:
            samples.append(parse_proc_status(status.read_text(encoding="utf-8")))
        except (FileNotFoundError, ProcessLookupError):
            break
        except (OSError, ValueError):
            pass
        stop.wait(RSS_POLL_SECONDS)


def _tracemalloc_measure(fn):
    gc.collect()
    tracemalloc.start()
    started = time.perf_counter_ns()
    try:
        result = fn()
        elapsed = time.perf_counter_ns() - started
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, {
        "elapsed_ns": elapsed,
        "tracemalloc_current_bytes": current,
        "tracemalloc_peak_bytes": peak,
    }


def validate_child_job(job: Mapping[str, Any]) -> None:
    if not sys.platform.startswith("linux") or not os.environ.get("RUNPOD_POD_ID"):
        raise ValueError("corpus measurement child requires a Runpod Linux environment")
    if job.get("representation") not in REPRESENTATIONS or job.get("schedule") not in {"cold", "warm"}:
        raise ValueError("invalid child representation/schedule")
    repetitions = _integer(job.get("repetitions"), "child repetitions", 3)
    if repetitions < 1 or (job.get("schedule") == "cold" and repetitions != 1):
        raise ValueError("invalid child repetition plan")
    record = job.get("record")
    if not isinstance(record, Mapping) or canonical_sha256(record) != job.get("record_sha256"):
        raise ValueError("child record hash mismatch")
    if not eligible_record(record):
        raise ValueError("child record outside frozen bounds")
    expected = job.get("expected_output_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("child expected output hash missing")


def run_child(job: Mapping[str, Any]) -> list[dict[str, Any]]:
    validate_child_job(job)
    import numpy as np
    from bitset_backend import eval_cm_node_flat, eval_cm_node_words, get_flat_program, program_metrics
    from cm_expr_serde import expr_from_json
    from cm_ir import _cm_node_count, compile_expr_to_cm_ir, materialize_cm
    from cm_normalize import canonical_layout
    from cmbench.output_budget import estimate_explicit_output
    from scripts.cm_memory_estimator_study import candidate_estimate

    record = job["record"]
    expr = expr_from_json(record["expression_v2"])
    variables, fixed = evaluation_context(job["corpus"], record)
    node = compile_expr_to_cm_ir(expr, reuse_cache=False, persistent_cache=False)
    program = get_flat_program(node)
    metrics = program_metrics(program)
    s = _cm_node_count(node)
    k = len(variables)
    candidate = candidate_estimate(
        k=k, representation=job["representation"], nodes=s, slots=program.n_slots,
        edges=metrics["argument_edges"], buffers=metrics["peak_live_word_buffers"],
    )
    if candidate["temporary_bytes"] > MAX_TEMPORARY:
        raise ValueError("candidate exceeds diagnostic cap")
    representation_name = "dense_bool" if job["representation"] == "dense" else "packed_bitset"
    legacy = estimate_explicit_output(k, representation_name, operation_slots=s)
    R, C = canonical_layout(list(variables))

    def evaluate():
        if job["representation"] == "dense":
            return materialize_cm(node, R, C, fixed, materialize_mode="numpy", output_budget=None)
        if job["representation"] == "bigint":
            return eval_cm_node_flat(node, variables, fixed=fixed)
        return eval_cm_node_words(node, variables, fixed=fixed)

    if job["schedule"] == "warm":
        warm = evaluate()
        del warm
    rows: list[dict[str, Any]] = []
    for offset in range(job["repetitions"]):
        output, sample = _tracemalloc_measure(evaluate)
        if job["representation"] == "dense":
            flat = output.reshape(-1).astype(np.uint8)
            packed = int.from_bytes(np.packbits(flat, bitorder="little").tobytes(), "little")
            del flat, output
        else:
            packed = int(output)
        digest = hashlib.sha256(packed.to_bytes(max(1, (1 << k) // 8), "little")).hexdigest()
        if digest != job["expected_output_sha256"]:
            raise AssertionError("independent scalar oracle mismatch")
        rows.append({
            "schema": SCHEMA, "status": "ok", "exact": True,
            "case_id": job["case_id"], "record_id": record.get("id"),
            "corpus": job["corpus"], "role": job["role"], "k": k,
            "syntactic_k": int(record.get("synt_support_size", k)),
            "schedule": job["schedule"], "representation": job["representation"],
            "actual_engine": job["representation"] if job["representation"] != "words" or k >= 6 else "bigint-fallback",
            "repetition": job["repetition_base"] + offset,
            "window": "corpus_evaluation_whole_call", "comparison_eligible": True,
            "s": s, "slots": program.n_slots, "metrics": metrics,
            "legacy_estimate": legacy.temporary_bytes, "output_bytes": legacy.output_bytes,
            "candidate": candidate, "output_sha256": digest,
            "independent_oracle_sha256": job["expected_output_sha256"],
            **sample,
        })
    return rows


def make_jobs(manifest: Mapping[str, Any], records: Mapping[str, dict[str, Any]], oracles: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        case_id = case["case_id"]
        base = {
            "case_id": case_id, "corpus": case["corpus"], "role": case["role"],
            "record": records[case_id], "record_sha256": case["record_sha256"],
            "expected_output_sha256": oracles[case_id]["live_output_sha256"],
        }
        for representation in REPRESENTATIONS:
            for repetition in range(3):
                jobs.append({
                    **base, "job_id": f"{case_id}-{representation}-cold-r{repetition}",
                    "representation": representation, "schedule": "cold",
                    "repetitions": 1, "repetition_base": repetition,
                })
            jobs.append({
                **base, "job_id": f"{case_id}-{representation}-warm",
                "representation": representation, "schedule": "warm",
                "repetitions": 3, "repetition_base": 0,
            })
    if len(jobs) != EXPECTED_JOBS or sum(job["repetitions"] for job in jobs) != EXPECTED_CALLS:
        raise AssertionError("planned corpus grid mismatch")
    return jobs


def run_monitored_job(job: Mapping[str, Any], timeout: float = MAX_CHILD_SECONDS) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = json.dumps(job, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(raw.encode("utf-8")) > MAX_JOB_BYTES:
        raise ValueError("child job exceeds input cap")
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--child"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=ROOT,
    )
    samples: list[dict[str, int | None]] = []
    stop = threading.Event()
    monitor = threading.Thread(target=_monitor_proc, args=(proc.pid, stop, samples), daemon=True)
    monitor.start()
    timed_out = False
    try:
        stdout, stderr = proc.communicate(input=raw, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        stdout, stderr = proc.communicate(timeout=5)
    finally:
        stop.set()
        monitor.join(timeout=2)
    if len(stdout.encode("utf-8", errors="replace")) > MAX_CHILD_OUTPUT_BYTES:
        raise ValueError("child output exceeds cap")
    rss = [sample["rss_bytes"] for sample in samples if sample.get("rss_bytes") is not None]
    hwm = [sample["hwm_bytes"] for sample in samples if sample.get("hwm_bytes") is not None]
    monitor_row = {
        "schema": SCHEMA, "job_id": job["job_id"], "pid": proc.pid,
        "returncode": proc.returncode, "timed_out": timed_out,
        "sample_count": len(samples), "sample_interval_seconds": RSS_POLL_SECONDS,
        "sampled_rss_peak_bytes": max(rss, default=None),
        "kernel_hwm_peak_bytes_observed": max(hwm, default=None),
        "rss_scope": (
            "whole isolated evaluator child, including interpreter imports, compile, evaluation, "
            "output hashing, and allocator lifetime; externally polled /proc status; not a per-call peak"
        ),
        "stderr_tail": stderr[-2000:],
    }
    rows: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("child emitted a non-object")
        rows.append(value)
    if timed_out or proc.returncode or len(rows) != job["repetitions"] or any(row.get("status") != "ok" for row in rows):
        raise RuntimeError(f"child job failed: {job['job_id']}: {monitor_row!r}")
    return rows, monitor_row


def summarize(rows: Sequence[Mapping[str, Any]], rss_jobs: Sequence[Mapping[str, Any]], oracles: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["role"], row["schedule"], row["representation"])].append(row)
    summaries: list[dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        role, schedule, representation = key
        candidate_ratios = [row["candidate"]["temporary_bytes"] / row["tracemalloc_peak_bytes"] for row in group]
        legacy_ratios = [row["legacy_estimate"] / row["tracemalloc_peak_bytes"] for row in group]
        summaries.append({
            "role": role, "schedule": schedule, "representation": representation,
            "rows": len(group), "candidate_underestimates": sum(ratio < 1 for ratio in candidate_ratios),
            "legacy_underestimates": sum(ratio < 1 for ratio in legacy_ratios),
            "candidate_estimate_over_peak_median": statistics.median(candidate_ratios),
            "candidate_estimate_over_peak_max": max(candidate_ratios),
            "legacy_estimate_over_peak_median": statistics.median(legacy_ratios),
        })
    rss_values = [row["sampled_rss_peak_bytes"] for row in rss_jobs if row.get("sampled_rss_peak_bytes") is not None]
    hwm_values = [row["kernel_hwm_peak_bytes_observed"] for row in rss_jobs if row.get("kernel_hwm_peak_bytes_observed") is not None]
    return {
        "schema": SCHEMA, "cases": len(oracles), "jobs": len(rss_jobs), "rows": len(rows),
        "statuses": dict(Counter(row["status"] for row in rows)),
        "exact_rows": sum(row.get("exact") is True for row in rows),
        "independent_oracle_cases": len(oracles),
        "frozen_truth_cases": sum(bool(row.get("frozen_truth_sha256")) for row in oracles.values()),
        "groups": summaries,
        "rss": {
            "jobs_with_samples": len(rss_values), "jobs_with_kernel_hwm": len(hwm_values),
            "sampled_rss_peak_bytes_max": max(rss_values, default=None),
            "sampled_rss_peak_bytes_median": statistics.median(rss_values) if rss_values else None,
            "kernel_hwm_peak_bytes_max_observed": max(hwm_values, default=None),
            "definition": "whole isolated child, not a per-call peak or cgroup enforcement proof",
        },
        "calibration_performed": False, "production_estimator_accepted": False,
        "acceptance_note": "Compatibility evidence only; no model coefficient or production default changes.",
        "real_workload_compatibility": "not measured; BX1/B2/EPFL are frozen benchmark corpora",
    }


def source_paths(selection_path: Path) -> list[Path]:
    relative_selection = selection_path.resolve().relative_to(ROOT.resolve())
    return [
        Path("scripts/cm_corpus_memory_validation.py"), Path("scripts/cm_memory_estimator_study.py"),
        Path("bitset_backend.py"), Path("cm_expr_serde.py"), Path("cm_exprlib.py"),
        Path("cm_ir.py"), Path("cm_normalize.py"), Path("cmbench/output_budget.py"),
        Path("cmbench/backends/bitset_engine.py"), relative_selection,
        *(CORPUS_PATHS[name] for name in ("bx1", "b2", "epfl")),
    ]


def run_study(selection_path: Path, output_dir: Path) -> int:
    if not sys.platform.startswith("linux") or not os.environ.get("RUNPOD_POD_ID"):
        raise ValueError("nontrivial corpus study requires a Runpod Linux environment")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite: {output_dir}")
    manifest, records = load_selection(selection_path)
    oracles: dict[str, dict[str, Any]] = {}
    for case in manifest["cases"]:
        oracles[case["case_id"]] = oracle_case(case["corpus"], records[case["case_id"]])
    jobs = make_jobs(manifest, records, oracles)
    output_dir.mkdir(parents=True, exist_ok=False)
    write_json_exclusive(output_dir / "selection-manifest.json", manifest)
    write_json_exclusive(output_dir / "oracles.json", oracles)
    hashes = {path.as_posix(): sha256_file(ROOT / path) for path in source_paths(selection_path)}
    write_json_exclusive(output_dir / "source-manifest.json", hashes)
    for relative, digest in hashes.items():
        destination = output_dir / "source_snapshot" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write((ROOT / relative).read_bytes())
        if sha256_file(destination) != digest:
            raise RuntimeError("source snapshot hash mismatch")
    environment = {
        "schema": SCHEMA, "platform": platform.platform(), "python": sys.version,
        "executable": sys.executable, "logical_cpus_host_visible": os.cpu_count(),
        "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "runpod_pod_id": os.environ.get("RUNPOD_POD_ID"),
        "rss_definition": "external 5 ms /proc child sampling; whole child lifetime, not a per-call peak",
        "cgroup_cpu_max": Path("/sys/fs/cgroup/cpu.max").read_text().strip() if Path("/sys/fs/cgroup/cpu.max").exists() else None,
        "cgroup_memory_max": Path("/sys/fs/cgroup/memory.max").read_text().strip() if Path("/sys/fs/cgroup/memory.max").exists() else None,
    }
    write_json_exclusive(output_dir / "environment.json", environment)
    started = time.monotonic()
    all_rows: list[dict[str, Any]] = []
    rss_jobs: list[dict[str, Any]] = []
    with (output_dir / "raw.jsonl").open("x", encoding="utf-8", newline="\n") as raw_stream, \
            (output_dir / "rss-jobs.jsonl").open("x", encoding="utf-8", newline="\n") as rss_stream:
        for index, job in enumerate(jobs):
            remaining = MAX_STUDY_SECONDS - (time.monotonic() - started)
            if remaining <= 10:
                raise TimeoutError("study deadline reached before evidence reserve")
            rows, rss = run_monitored_job(job, min(MAX_CHILD_SECONDS, remaining - 10))
            rss["job_index"] = index
            rss_stream.write(json.dumps(rss, sort_keys=True, allow_nan=False) + "\n")
            rss_stream.flush()
            rss_jobs.append(rss)
            for row in rows:
                row["job_index"] = index
                row["job_id"] = job["job_id"]
                raw_stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                raw_stream.flush()
                all_rows.append(row)
    summary = summarize(all_rows, rss_jobs, oracles)
    summary["elapsed_seconds"] = time.monotonic() - started
    summary["source_unchanged"] = all(sha256_file(ROOT / path) == digest for path, digest in hashes.items())
    if (summary["cases"] != EXPECTED_CASES or summary["jobs"] != EXPECTED_JOBS
            or summary["rows"] != EXPECTED_CALLS or summary["statuses"] != {"ok": EXPECTED_CALLS}
            or summary["exact_rows"] != EXPECTED_CALLS or not summary["source_unchanged"]):
        raise RuntimeError("completed corpus evidence fails the frozen grid")
    write_json_exclusive(output_dir / "summary.json", summary)
    print(json.dumps({
        "cases": summary["cases"], "jobs": summary["jobs"], "rows": summary["rows"],
        "statuses": summary["statuses"], "source_unchanged": summary["source_unchanged"],
    }, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-selection", type=Path)
    parser.add_argument("--selection-manifest", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--execution", choices=["runpod"])
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.child:
        raw = sys.stdin.read(MAX_JOB_BYTES + 1)
        if len(raw.encode("utf-8")) > MAX_JOB_BYTES:
            raise ValueError("child input exceeds cap")
        job = json.loads(raw)
        try:
            for row in run_child(job):
                print(json.dumps(row, sort_keys=True, allow_nan=False), flush=True)
            return 0
        except (AssertionError, MemoryError, ValueError, RecursionError) as exc:
            print(json.dumps({"schema": SCHEMA, "status": "failed", "reason": str(exc)}), flush=True)
            return 2
    if args.freeze_selection is not None:
        if args.selection_manifest is not None or args.output_dir is not None or args.execution is not None:
            parser.error("--freeze-selection cannot be combined with study options")
        if args.freeze_selection.exists():
            parser.error(f"refusing to overwrite: {args.freeze_selection}")
        args.freeze_selection.parent.mkdir(parents=True, exist_ok=True)
        manifest = freeze_selection()
        write_json_exclusive(args.freeze_selection, manifest)
        print(json.dumps({"cases": len(manifest["cases"]), "path": str(args.freeze_selection)}, sort_keys=True))
        return 0
    if args.execution != "runpod" or args.selection_manifest is None or args.output_dir is None:
        parser.error("study requires --execution runpod, --selection-manifest, and --output-dir")
    return run_study(args.selection_manifest, args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
