"""Conversion-only W8 worker: public LogikBench RTL to bounded BLIF evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


MAX_CLUSTERS = 80
PER_CLUSTER_SECONDS = 20
TOTAL_CONVERSION_SECONDS = 600
MAX_LOG_BYTES = 16 << 10
MAX_BLIF_BYTES = 4 << 20
MAX_TOTAL_BLIF_BYTES = 20 << 20
RTL_SUFFIXES = frozenset({".v", ".sv"})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def bounded(data: bytes) -> str:
    return data[:MAX_LOG_BYTES].decode("utf-8", errors="replace")


def yosys_script(files: list[Path], top: str, destination: Path) -> str:
    names = " ".join('"' + path.as_posix().replace('"', '\\"') + '"' for path in files)
    output = destination.as_posix().replace('"', '\\"')
    return (
        f"read_verilog -sv -Irtl {names}; "
        f"hierarchy -check -top {top}; "
        "proc; opt; memory; opt; fsm; opt; check -assert; "
        "techmap; opt; abc -g AND; opt_clean; check -assert; "
        f"write_blif -top {top} -noalias \"{output}\""
    )


def convert(cluster_root: Path, top: str, files: list[Path], destination: Path,
            timeout: int = PER_CLUSTER_SECONDS) -> dict:
    started = time.monotonic()
    try:
        result = subprocess.run(
            ["/usr/bin/yosys", "-Q", "-T", "-p", yosys_script(files, top, destination)],
            cwd=cluster_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        status = "converted" if result.returncode == 0 and destination.is_file() else "rejected"
        error = None if status == "converted" else "yosys_exit_or_missing_output"
    except subprocess.TimeoutExpired as exc:
        result = None
        status = "rejected"
        error = "yosys_timeout"
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
    else:
        stdout, stderr = result.stdout, result.stderr
    record = {
        "status": status,
        "error": error,
        "returncode": None if result is None else result.returncode,
        "elapsed_seconds": time.monotonic() - started,
        "stdout": bounded(stdout),
        "stderr": bounded(stderr),
        "stdout_truncated": len(stdout) > MAX_LOG_BYTES,
        "stderr_truncated": len(stderr) > MAX_LOG_BYTES,
    }
    if status == "converted":
        size = destination.stat().st_size
        if not 0 < size <= MAX_BLIF_BYTES:
            destination.unlink(missing_ok=True)
            record.update(status="rejected", error="blif_size_bound", bytes=size)
        else:
            record.update(bytes=size, sha256=sha256(destination))
    return record


def parse_blif(path: Path) -> tuple[list[str], list[str], list[tuple[list[str], str, list[str]]]]:
    logical = []
    pending = ""
    for physical in path.read_text(encoding="utf-8").splitlines():
        line = physical.split("#", 1)[0].strip()
        if not line:
            continue
        pending = (pending + " " + line).strip() if pending else line
        if pending.endswith("\\"):
            pending = pending[:-1].rstrip()
            continue
        logical.append(pending)
        pending = ""
    inputs: list[str] = []
    outputs: list[str] = []
    nodes: list[tuple[list[str], str, list[str]]] = []
    index = 0
    while index < len(logical):
        parts = logical[index].split()
        if parts[0] == ".inputs":
            inputs.extend(parts[1:])
        elif parts[0] == ".outputs":
            outputs.extend(parts[1:])
        elif parts[0] == ".names":
            incoming, outgoing = parts[1:-1], parts[-1]
            cubes = []
            index += 1
            while index < len(logical) and not logical[index].startswith("."):
                cubes.append(logical[index])
                index += 1
            nodes.append((incoming, outgoing, cubes))
            continue
        elif parts[0] not in {".model", ".end"}:
            raise ValueError("fixture BLIF contains unsupported directive: " + parts[0])
        index += 1
    return inputs, outputs, nodes


def eval_blif(path: Path, assignment: dict[str, bool], output: str) -> bool:
    _inputs, _outputs, nodes = parse_blif(path)
    values = dict(assignment)
    pending = list(nodes)
    while pending:
        progressed = False
        for position, (incoming, outgoing, cubes) in list(enumerate(pending)):
            if not all(name in values for name in incoming):
                continue
            value = False
            for cube in cubes:
                parts = cube.split()
                pattern = parts[0] if incoming else ""
                cube_output = parts[-1]
                if cube_output != "1":
                    raise ValueError("fixture BLIF uses a non-one cube")
                if all(bit == "-" or (bit == "1") == values[name]
                       for bit, name in zip(pattern, incoming)):
                    value = True
                    break
            values[outgoing] = value
            pending.pop(position)
            progressed = True
            break
        if not progressed:
            raise ValueError("fixture BLIF is cyclic or has an unresolved input")
    return values[output]


def fixture_gate(output: Path) -> dict:
    fixture_root = output / "fixtures"
    fixture_root.mkdir(parents=True, exist_ok=False)
    fixtures = {
        "andor": ("module andor(input a,b,c,d, output y); assign y=(a&b)|((~c)&d); endmodule\n",
                  ("a", "b", "c", "d"), lambda a, b, c, d: (a and b) or ((not c) and d)),
        "xor3": ("module xor3(input a,b,c, output y); assign y=a^b^c; endmodule\n",
                 ("a", "b", "c"), lambda a, b, c: a ^ b ^ c),
        "mux2": ("module mux2(input a,b,s, output y); assign y=s?b:a; endmodule\n",
                 ("a", "b", "s"), lambda a, b, s: b if s else a),
        "shared": ("module shared(input a,b,c,d, output y); wire t=a^b; assign y=(t&c)|(t&d); endmodule\n",
                   ("a", "b", "c", "d"), lambda a, b, c, d: ((a ^ b) and c) or ((a ^ b) and d)),
        "cmp2": ("module cmp2(input [1:0] a,b, output y); assign y=(a>=b); endmodule\n",
                 ("a[0]", "a[1]", "b[0]", "b[1]"),
                 lambda a0, a1, b0, b1: (a0 + 2*a1) >= (b0 + 2*b1)),
    }
    rows = []
    retained_blif_bytes = 0
    for name, (source, variables, expected) in fixtures.items():
        source_path = fixture_root / f"{name}.v"
        blif_path = fixture_root / f"{name}.blif"
        source_path.write_text(source, encoding="utf-8")
        conversion = convert(fixture_root, name, [Path(source_path.name)], blif_path, timeout=15)
        if conversion["status"] != "converted":
            raise RuntimeError("fixture conversion failed: " + name)
        inputs, outputs, _nodes = parse_blif(blif_path)
        if set(inputs) != set(variables) or outputs != ["y"]:
            raise RuntimeError("fixture interface changed: " + name)
        for mask in range(1 << len(variables)):
            values = tuple(bool(mask & (1 << index)) for index in range(len(variables)))
            assignment = dict(zip(variables, values))
            if eval_blif(blif_path, assignment, "y") != bool(expected(*values)):
                raise RuntimeError("fixture semantic mismatch: " + name)
        rows.append({
            "name": name,
            "variables": list(variables),
            "assignments": 1 << len(variables),
            "source_sha256": sha256(source_path),
            "blif_sha256": sha256(blif_path),
            "semantic_equivalence": True,
        })
    return {"fixtures": rows, "fixture_count": len(rows), "semantic_equivalence": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--static-admission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("output already exists")
    args.output.mkdir(parents=True)
    admission = json.loads(args.static_admission.read_text(encoding="utf-8"))
    candidate_ids = admission["static_admitted_cluster_ids_in_frozen_order"]
    by_id = {row["cluster_id"]: row for row in admission["clusters"]}
    if len(candidate_ids) != 70 or len(candidate_ids) > MAX_CLUSTERS:
        raise RuntimeError("static candidate count changed")

    version = subprocess.run(["/usr/bin/yosys", "-V"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, check=True, timeout=10)
    dpkg = subprocess.run(["/usr/bin/dpkg-query", "-W", "-f=${Package}=${Version}\\n", "yosys"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)
    environment = {
        "schema": "cm-comparative-w8-conversion-environment/v1",
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "logical_cpus_host_visible": os.cpu_count(),
        "affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "yosys_version": bounded(version.stdout),
        "yosys_package": bounded(dpkg.stdout),
        "static_admission_sha256": sha256(args.static_admission),
        "performance_measurement": False,
    }
    write(args.output / "environment.json", environment)
    fixtures = fixture_gate(args.output)
    write(args.output / "fixture-summary.json", fixtures)

    converted_root = args.output / "converted"
    converted_root.mkdir()
    rows = []
    deadline = time.monotonic() + TOTAL_CONVERSION_SECONDS
    for cluster_id in candidate_ids:
        source_row = by_id[cluster_id]
        cluster_root = args.source_root / "logikbench/benchmarks" / source_row["group"] / source_row["name"]
        sources = []
        for relative, expected_hash in zip(source_row["rtl_paths"], source_row["rtl_sha256"]):
            path = args.source_root / relative
            if sha256(path) != expected_hash:
                raise RuntimeError("source identity changed: " + relative)
            if path.suffix.lower() in RTL_SUFFIXES:
                sources.append(path.relative_to(cluster_root))
        destination = converted_root / f"{cluster_id}.blif"
        if time.monotonic() >= deadline:
            conversion = {"status": "rejected", "error": "total_conversion_deadline"}
        else:
            conversion = convert(cluster_root, source_row["name"], sources, destination,
                                 timeout=min(PER_CLUSTER_SECONDS, max(1, int(deadline - time.monotonic()))))
        if conversion.get("status") == "converted":
            size = int(conversion["bytes"])
            if retained_blif_bytes + size > MAX_TOTAL_BLIF_BYTES:
                destination.unlink(missing_ok=True)
                conversion.update(status="rejected", error="aggregate_blif_size_bound")
                conversion.pop("sha256", None)
            else:
                retained_blif_bytes += size
        rows.append({
            "cluster_id": cluster_id,
            "group": source_row["group"],
            "name": source_row["name"],
            "source_set_sha256": source_row["source_set_sha256"],
            "source_paths": [path.as_posix() for path in sources],
            "top": source_row["name"],
            **conversion,
        })
    write(args.output / "conversions.json", {
        "schema": "cm-comparative-w8-yosys-conversions/v1",
        "performance_measurement": False,
        "rows": rows,
        "attempted": len(rows),
        "converted": sum(row["status"] == "converted" for row in rows),
        "rejected": sum(row["status"] != "converted" for row in rows),
        "retained_blif_bytes": retained_blif_bytes,
        "conversion_time_limit_seconds": TOTAL_CONVERSION_SECONDS,
        "per_cluster_time_limit_seconds": PER_CLUSTER_SECONDS,
        "performance_claim_permitted": False,
    })
    files = sorted((path for path in args.output.rglob("*") if path.is_file()),
                   key=lambda path: path.relative_to(args.output).as_posix())
    write(args.output / "checksums.json", {
        "schema": "cm-comparative-w8-conversion-checksums/v1",
        "files": [{
            "path": path.relative_to(args.output).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        } for path in files],
    })
    print(json.dumps({
        "fixtures": fixtures["fixture_count"],
        "fixture_equivalence": True,
        "attempted": len(rows),
        "converted": sum(row["status"] == "converted" for row in rows),
        "rejected": sum(row["status"] != "converted" for row in rows),
        "retained_blif_bytes": retained_blif_bytes,
        "performance_measurement": False,
        "performance_claim_permitted": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
