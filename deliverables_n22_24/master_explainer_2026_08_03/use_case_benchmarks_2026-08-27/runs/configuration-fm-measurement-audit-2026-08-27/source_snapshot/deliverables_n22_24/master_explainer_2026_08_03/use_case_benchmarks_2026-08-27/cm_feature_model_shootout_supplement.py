"""Native CUDD ordering, d4/d-DNNF, and isolated-RSS supplement."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

import psutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

import cm_feature_model_representation_battery as battery  # noqa: E402
from bitset_backend import _eval_words  # noqa: E402
from cm_ir import compile_expr_to_cm_ir  # noqa: E402


SCHEMA = "cm-fm-shootout-supplement/v1"
PROTOCOL = "CONFIGURATION-FM-HISTORY-SHOOTOUT-PROTOCOL.md"
DEFAULT_RUN = HERE / "runs" / "configuration-fm-history-shootout-cudd-full40-2026-08-27"
DEFAULT_OUTPUT = HERE / "runs" / "configuration-fm-history-shootout-supplement-2026-08-27"
D4_COMMIT = "333370cc1e843dd0749c1efe88516e72b5239174"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    if not rows and not fieldnames:
        raise ValueError(f"empty CSV requires explicit fields: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_checksums(output: Path) -> None:
    files = sorted(path for path in output.rglob("*") if path.is_file() and path.name != "CHECKSUMS.sha256")
    text = "".join(f"{sha256_file(path)}  {path.relative_to(output).as_posix()}\n" for path in files)
    (output / "CHECKSUMS.sha256").write_text(text, encoding="ascii")


def geomean(values: Iterable[float]) -> float:
    values = [float(value) for value in values]
    if not values or any(value <= 0 for value in values):
        raise ValueError(values)
    return statistics.geometric_mean(values)


def packed_sha(value: int, k: int) -> str:
    return hashlib.sha256(value.to_bytes(1 << max(0, k - 3), "little")).hexdigest()


def read_case(dimacs: Path, case_id: str, history: str, model_id: str, slice_kind: str, k: int) -> battery.Case:
    lines = dimacs.read_text(encoding="ascii").splitlines()
    header = lines[0].split()
    if header[:2] != ["p", "cnf"] or int(header[2]) != k:
        raise ValueError(f"invalid residual header: {dimacs}")
    residual = tuple(tuple(map(int, line.split()[:-1])) for line in lines[1:] if line.strip())
    if len(residual) != int(header[3]):
        raise ValueError(f"residual clause count mismatch: {dimacs}")
    return battery.Case(case_id, "real", model_id, history, slice_kind, k, residual, 0, {})


def packed_from_artifact(path: Path) -> int:
    value = json.loads(path.read_text(encoding="utf-8"))
    return int.from_bytes(bytes.fromhex(value["packed_hex"]), "little")


def monitored(command: list[str], timeout: float = 60.0) -> dict:
    started = time.perf_counter_ns()
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tracked = psutil.Process(proc.pid)
    try:
        peak = tracked.memory_info().rss
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        peak = 0
    timed_out = False
    while proc.poll() is None:
        try:
            rss = tracked.memory_info().rss
            rss += sum(child.memory_info().rss for child in tracked.children(recursive=True))
            peak = max(peak, rss)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        if (time.perf_counter_ns() - started) / 1e9 > timeout:
            timed_out = True
            proc.kill()
            break
        time.sleep(0.001)
    stdout, _ = proc.communicate()
    elapsed = time.perf_counter_ns() - started
    if timed_out:
        raise TimeoutError(f"timeout after {timeout}s: {command}")
    if proc.returncode:
        raise RuntimeError(f"command failed ({proc.returncode}): {command}\n{stdout[-4000:]}")
    return {"stdout": stdout, "wall_ns": elapsed, "peak_rss_bytes": peak}


def parse_d4(stdout: str) -> dict:
    counts = re.findall(r"(?m)^s\s+(\d+)\s*$", stdout)
    if not counts:
        raise ValueError(f"d4 output has no exact count: {stdout[-2000:]}")
    times = re.findall(r"Final time:\s*([0-9.]+)", stdout)
    nodes = re.findall(r"Number of nodes:\s*(\d+)", stdout)
    edges = re.findall(r"Number of edges:\s*(\d+)", stdout)
    return {
        "count": int(counts[-1]),
        "internal_seconds": float(times[-1]) if times else None,
        "nodes": int(nodes[-1]) if nodes else None,
        "edges": int(edges[-1]) if edges else None,
    }


def rss_worker(arm: str, dimacs: Path) -> int:
    lines = dimacs.read_text(encoding="ascii").splitlines()
    header = lines[0].split()
    k = int(header[2])
    residual = tuple(tuple(map(int, line.split()[:-1])) for line in lines[1:] if line.strip())
    if arm == "cnf":
        value = battery.cnf_bitset(residual, k)
    else:
        expression = battery.expression_from_residual(residual, k)
        if arm == "cm":
            program = battery.get_flat_program(compile_expr_to_cm_ir(expression))
            value = _eval_words(program, tuple(f"x{i}" for i in range(k - 1, -1, -1)), {})
        elif arm == "cudd":
            from dd import cudd

            artifact = battery.build_bdd(expression, k, cudd, [f"x{i}" for i in range(k)])
            value = battery.bdd_extract_enumerate(artifact, k)
        else:
            raise ValueError(arm)
    print(json.dumps({"arm": arm, "packed_sha256": packed_sha(value, k)}))
    return 0


def sifting_metrics(case: battery.Case, packed: int, rounds: int) -> dict:
    from dd import cudd

    expression = battery.expression_from_residual(case.residual, case.k)
    samples = []
    for _ in range(rounds):
        artifact = battery.build_bdd(expression, case.k, cudd, [f"x{i}" for i in range(case.k)])
        if battery.bdd_extract_enumerate(artifact, case.k) != packed:
            raise AssertionError(f"fixed CUDD mismatch: {case.case_id}")
        started = time.perf_counter_ns()
        artifact.manager.reorder()
        reorder_ns = time.perf_counter_ns() - started
        nodes = int(battery.safe_bdd_node_count(artifact.manager, artifact.root) or 0)
        if battery.bdd_extract_enumerate(artifact, case.k) != packed:
            raise AssertionError(f"sifted CUDD mismatch: {case.case_id}")
        samples.append({
            "setup_ns": artifact.setup_ns,
            "build_ns": artifact.build_ns,
            "fixed_nodes": artifact.nodes,
            "reorder_ns": reorder_ns,
            "sifted_nodes": nodes,
        })
    return {
        "cudd_setup_ns_median": statistics.median(item["setup_ns"] for item in samples),
        "cudd_build_ns_median": statistics.median(item["build_ns"] for item in samples),
        "cudd_fixed_nodes_median": statistics.median(item["fixed_nodes"] for item in samples),
        "cudd_reorder_ns_median": statistics.median(item["reorder_ns"] for item in samples),
        "cudd_sifted_nodes_median": statistics.median(item["sifted_nodes"] for item in samples),
        "cudd_sifted_over_fixed_nodes": statistics.median(item["sifted_nodes"] / item["fixed_nodes"] for item in samples),
        "cudd_sifting_samples_json": json.dumps(samples, separators=(",", ":")),
        "cudd_sifting_relation_equal": True,
    }


def current_git_head() -> str:
    supplied = os.environ.get("CM_BATTERY_GIT_HEAD")
    if supplied:
        return supplied
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unavailable"


def run_supplement(run: Path, output: Path, d4: Path, rounds: int) -> int:
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    if not d4.is_file():
        raise SystemExit(f"d4 binary unavailable: {d4}")
    d4_head = subprocess.run(
        ["git", "-C", str(d4.parent), "rev-parse", "HEAD"], capture_output=True, text=True
    )
    # The image locates the binary at /opt/d4/d4, so its repository is its parent.
    if d4_head.returncode or d4_head.stdout.strip() != D4_COMMIT:
        raise SystemExit(f"unexpected d4 source revision: {d4_head.stdout.strip() or d4_head.stderr.strip()}")
    output.mkdir(parents=True)
    ddnnf_root = output / "ddnnf"
    ddnnf_root.mkdir()

    core_rows = {row["case_id"]: row for row in csv.DictReader((run / "cases.csv").open(encoding="utf-8", newline=""))}
    corpus_rows = [json.loads(line) for line in (run / "corpus.jsonl").read_text(encoding="utf-8").splitlines()]
    if len(core_rows) != len(corpus_rows):
        raise AssertionError("core row/corpus cardinality mismatch")

    rows = []
    rss_rows = []
    for index, corpus in enumerate(corpus_rows):
        case_id = corpus["case_id"]
        core = core_rows[case_id]
        case_hash = hashlib.sha256(case_id.encode()).hexdigest()[:16]
        core_dir = run / "serialized" / case_hash
        dimacs = core_dir / "residual.dimacs"
        packed = packed_from_artifact(core_dir / "cm-flat-packed.json")
        case = read_case(dimacs, case_id, corpus["history"], corpus["model_id"], corpus["slice_kind"], int(corpus["k"]))
        if battery.cnf_bitset(case.residual, case.k) != packed:
            raise AssertionError(f"core packed mismatch: {case_id}")
        print(f"[{index + 1}/{len(corpus_rows)}] {case_id}", flush=True)

        sift = sifting_metrics(case, packed, rounds)
        count_trials = [monitored([str(d4), "-mc", str(dimacs)]) for _ in range(rounds)]
        count_parsed = [parse_d4(item["stdout"]) for item in count_trials]
        expected_count = packed.bit_count()
        if any(item["count"] != expected_count for item in count_parsed):
            raise AssertionError(f"d4 count mismatch: {case_id}")

        nnf = ddnnf_root / f"{case_hash}.nnf"
        compiled = monitored([str(d4), "-dDNNF", str(dimacs), f"-out={nnf}"])
        compiled_parsed = parse_d4(compiled["stdout"])
        if compiled_parsed["count"] != expected_count or not nnf.is_file():
            raise AssertionError(f"d4 d-DNNF mismatch: {case_id}")

        row = {
            "case_id": case_id,
            "model_id": corpus["model_id"],
            "history": corpus["history"],
            "slice_kind": corpus["slice_kind"],
            "k": case.k,
            "expected_count": expected_count,
            **sift,
            "d4_count": expected_count,
            "d4_count_wall_ns_median": statistics.median(item["wall_ns"] for item in count_trials),
            "d4_count_internal_ns_median": statistics.median(item["internal_seconds"] * 1e9 for item in count_parsed),
            "d4_count_peak_rss_bytes_median": statistics.median(item["peak_rss_bytes"] for item in count_trials),
            "d4_count_samples_json": json.dumps(
                [{"wall_ns": trial["wall_ns"], "peak_rss_bytes": trial["peak_rss_bytes"],
                  "internal_seconds": parsed["internal_seconds"]} for trial, parsed in zip(count_trials, count_parsed)],
                separators=(",", ":"),
            ),
            "d4_compile_wall_ns": compiled["wall_ns"],
            "d4_compile_peak_rss_bytes": compiled["peak_rss_bytes"],
            "d4_compile_internal_ns": compiled_parsed["internal_seconds"] * 1e9,
            "ddnnf_nodes": compiled_parsed["nodes"],
            "ddnnf_edges": compiled_parsed["edges"],
            "ddnnf_bytes": nnf.stat().st_size,
            "ddnnf_sha256": sha256_file(nnf),
            "d4_count_equal": True,
            "d4_compile_count_equal": True,
            "core_packed_count_ns": int(float(core["packed_count_ns"])),
            "core_cm_serialized_bytes": int(core["cm_serialized_bytes"]),
            "core_robdd_serialized_bytes": int(core["robdd_serialized_bytes"]),
        }
        rows.append(row)

        if case.k == 16 and case.slice_kind == "incidence":
            expected_sha = packed_sha(packed, case.k)
            for arm in ("cnf", "cm", "cudd"):
                measured = monitored([sys.executable, str(Path(__file__).resolve()), "--worker", arm, "--input", str(dimacs)])
                worker_result = next(
                    json.loads(line)
                    for line in reversed(measured["stdout"].splitlines())
                    if line.startswith("{") and "packed_sha256" in line
                )
                if worker_result["packed_sha256"] != expected_sha:
                    raise AssertionError(f"RSS worker mismatch: {case_id} {arm}")
                rss_rows.append({
                    "case_id": case_id,
                    "model_id": corpus["model_id"],
                    "history": corpus["history"],
                    "k": case.k,
                    "slice_kind": case.slice_kind,
                    "arm": arm,
                    "wall_ns": measured["wall_ns"],
                    "peak_rss_bytes": measured["peak_rss_bytes"],
                    "relation_equal": True,
                })
            rss_rows.append({
                "case_id": case_id,
                "model_id": corpus["model_id"],
                "history": corpus["history"],
                "k": case.k,
                "slice_kind": case.slice_kind,
                "arm": "d4_count",
                "wall_ns": row["d4_count_wall_ns_median"],
                "peak_rss_bytes": row["d4_count_peak_rss_bytes_median"],
                "relation_equal": True,
            })

    write_csv(output / "supplement.csv", rows)
    write_csv(
        output / "native-rss.csv",
        rss_rows,
        ["case_id", "model_id", "history", "k", "slice_kind", "arm", "wall_ns", "peak_rss_bytes", "relation_equal"],
    )
    by_k = {}
    for k in sorted({row["k"] for row in rows}):
        selected = [row for row in rows if row["k"] == k]
        by_k[str(k)] = {
            "n": len(selected),
            "sifted_over_fixed_nodes_geomean": geomean(row["cudd_sifted_over_fixed_nodes"] for row in selected),
            "d4_count_over_packed_count_geomean": geomean(row["d4_count_wall_ns_median"] / row["core_packed_count_ns"] for row in selected),
            "ddnnf_over_robdd_bytes_geomean": geomean(row["ddnnf_bytes"] / row["core_robdd_serialized_bytes"] for row in selected),
            "ddnnf_over_cm_bytes_geomean": geomean(row["ddnnf_bytes"] / row["core_cm_serialized_bytes"] for row in selected),
        }
    rss_summary = {
        arm: {
            "n": len([row for row in rss_rows if row["arm"] == arm]),
            "peak_rss_bytes_median": statistics.median(row["peak_rss_bytes"] for row in rss_rows if row["arm"] == arm),
        }
        for arm in sorted({row["arm"] for row in rss_rows})
    }
    summary = {
        "schema_version": SCHEMA,
        "status": "completed",
        "case_count": len(rows),
        "rss_case_count": len(rss_rows),
        "correctness": {"sifting_mismatches": 0, "d4_count_mismatches": 0, "ddnnf_count_mismatches": 0, "rss_worker_mismatches": 0},
        "by_k": by_k,
        "rss": rss_summary,
        "refusals": {
            "cudd_zdd": "dd.cudd 0.5.7 exposes BDD but no native ZDD API",
            "d4v2": "official pinned tree omits referenced 3rdParty/patoh/libpatoh.a; official legacy d4 used instead",
        },
    }
    json_dump(output / "summary.json", summary)
    image_id = os.environ.get("CM_SHOOTOUT_IMAGE_ID", "unavailable")
    json_dump(output / "manifest.json", {
        "schema_version": SCHEMA,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": PROTOCOL,
        "core_run": str(run),
        "core_checksums_sha256": sha256_file(run / "CHECKSUMS.sha256"),
        "rounds": rounds,
        "d4_commit": D4_COMMIT,
        "d4_binary_sha256": sha256_file(d4),
        "container_image_id": image_id,
        "python": sys.version,
        "git_head": current_git_head(),
    })
    write_checksums(output)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=("cnf", "cm", "cudd"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--d4", type=Path, default=Path(os.environ.get("D4_BINARY", "/opt/d4/d4")))
    parser.add_argument("--rounds", type=int, default=5)
    args = parser.parse_args()
    if args.worker:
        if args.input is None:
            parser.error("--worker requires --input")
        return rss_worker(args.worker, args.input.resolve())
    if args.rounds < 1:
        parser.error("rounds must be positive")
    return run_supplement(args.run.resolve(), args.output.resolve(), args.d4.resolve(), args.rounds)


if __name__ == "__main__":
    raise SystemExit(main())
