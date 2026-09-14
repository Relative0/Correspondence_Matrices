"""Local-only correctness audit using existing environments, no installation.

Windows: --phase prepare --evidence-root <preserved checkout>
Existing pinned Ubuntu Python: --phase native
All output goes to the new attribution directory; historical evidence is read.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs/audits/2026-09-14-cm-benchmark-attribution"
from cmbench.biology_bnet import parse_bnet
from cmbench.biology_controls import bnet_scalar_oracle, encode_fixed_points, native_fixed_points, is_fixed_point
from cmbench.backends.exact_controls_v2 import run_exact_counter_v2, run_sat_v2


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def aeon_worker(path):
    from biodivine_aeon import BooleanNetwork, AsynchronousGraph, FixedPoints
    if importlib.metadata.version("biodivine-aeon") != "1.4.2":
        raise RuntimeError("AEON version differs from existing campaign pin")
    network = BooleanNetwork.from_file(str(path)).infer_valid_graph()
    vertices = FixedPoints.symbolic(AsynchronousGraph(network)).vertices()
    count = int(vertices.cardinality())
    functions = parse_bnet(path.read_text(encoding="utf-8"))
    witness = None
    if count:
        model = next(iter(vertices.items()))
        witness = {f.target: bool(model[f.target]) for f in functions}
        if not is_fixed_point(functions, witness):
            raise ValueError("AEON witness fails original BNet")
    print(json.dumps({"count": count, "witness": witness, "witness_validated": bool(count)}))


def prepare(evidence_root):
    corpus = json.loads((OUT / "BIOLOGY_CORPUS_AUDIT.json").read_text())
    directory = OUT / "control-inputs"
    directory.mkdir(exist_ok=True)
    cases = []
    for model in corpus["models"]:
        if model["classification"] != "closed":
            continue
        source = evidence_root / model["path"]
        if sha(source) != model["input_sha256"]:
            raise ValueError("retained BNet input hash mismatch")
        text = source.read_text(encoding="utf-8")
        functions = parse_bnet(text)
        encoded = encode_fixed_points(functions)
        bnet_path = directory / f'{model["model_id"]}.bnet'
        bnet_path.write_bytes(source.read_bytes())
        cnf_path = directory / f'{model["model_id"]}.cnf'
        cnf_path.write_text(encoded.dimacs(), encoding="utf-8", newline="\n")
        row = {"model_id": model["model_id"], "targets": len(functions),
               "cnf_variables": encoded.variables, "cnf_clauses": len(encoded.clauses),
               "bnet_sha256": sha(bnet_path), "cnf_sha256": sha(cnf_path),
               "cluster_id": model["independence_cluster"], "control_scope": "unperturbed_fixed_points"}
        if len(functions) <= 16:
            started = time.perf_counter()
            scalar = bnet_scalar_oracle(functions, max_variables=16)
            native = native_fixed_points(functions, max_targets=16)
            if scalar.count != native.count:
                raise ValueError("scalar/native fixed-point count mismatch")
            row.update(scalar=asdict(scalar), cadical195=asdict(native), diagnostic_seconds=time.perf_counter() - started)
        else:
            row["scalar_status"] = "unsupported_local_width_cap_16"
        cases.append(row)
    write("LOCAL_CONTROL_RESULTS.json", {"schema": "cm-biology-local-controls/v1", "phase": "prepare",
          "platform": platform.platform(), "python_sat": importlib.metadata.version("python-sat"),
          "corpus_sha256": sha(OUT / "BIOLOGY_CORPUS_AUDIT.json"), "cases": cases,
          "claim": "correctness/control evidence; diagnostic elapsed times are not benchmark results"})


def native():
    cases = json.loads((OUT / "LOCAL_CONTROL_RESULTS.json").read_text())["cases"]
    runtime = ROOT / "docs/audits/2026-09-13-cm-benchmark-campaign/wsl-successor-remote-replay-003/evidence/RUNTIME.json"
    pins = json.loads(runtime.read_text())["native_sha256"]
    binaries = {k: Path("/usr/local/bin") / k for k in ("ganak", "d4-counter", "cryptominisat5")}
    for name, path in binaries.items():
        if sha(path) != pins[name]:
            raise ValueError("existing local binary differs from recorded WSL runtime")
    result = {"schema": "cm-biology-local-native-controls/v1", "platform": platform.platform(),
              "runtime_reference_sha256": sha(runtime), "native_sha256": {k: sha(v) for k, v in binaries.items()},
              "aeon_version": importlib.metadata.version("biodivine-aeon"), "timeout_seconds_per_arm": 5,
              "cases": [], "correctness_mismatches": [], "claim": "correctness only, no performance attribution"}
    for case in cases:
        ident = case["model_id"]
        bnet = OUT / "control-inputs" / f"{ident}.bnet"
        cnf = bnet.with_suffix(".cnf")
        if sha(bnet) != case["bnet_sha256"] or sha(cnf) != case["cnf_sha256"]:
            raise ValueError("prepared input hash mismatch")
        functions = parse_bnet(bnet.read_text(encoding="utf-8"))
        arms = {}
        for arm in ("aeon", "d4", "ganak", "cryptominisat"):
            start = time.perf_counter()
            try:
                if arm == "aeon":
                    process = subprocess.run([sys.executable, str(Path(__file__)), "--worker", str(bnet)],
                                             capture_output=True, text=True, timeout=5, check=True)
                    value = json.loads(process.stdout)
                elif arm == "cryptominisat":
                    solved = run_sat_v2(cnf, executable=binaries["cryptominisat5"], timeout_seconds=5)
                    witness = None if solved.assignment is None else dict(zip((f.target for f in functions), solved.assignment))
                    if witness is not None and not is_fixed_point(functions, witness):
                        raise ValueError("CMS witness fails original BNet")
                    value = {"satisfiable": solved.status == "SATISFIABLE", "witness": witness,
                             "witness_validated": witness is not None}
                else:
                    solved = run_exact_counter_v2(cnf, backend=arm, executable=binaries["d4-counter" if arm == "d4" else "ganak"], timeout_seconds=5)
                    value = {"count": solved.count, "witness": None, "witness_source": "companion_CMS_not_counter"}
                arms[arm] = {"status": "ok", **value}
            except (TimeoutError, subprocess.TimeoutExpired):
                arms[arm] = {"status": "timeout", "count": None}
            except (ValueError, RuntimeError, subprocess.CalledProcessError, OSError) as exc:
                arms[arm] = {"status": "backend_error", "count": None, "reason": str(exc)[-1000:]}
            arms[arm]["diagnostic_seconds"] = time.perf_counter() - start
        counts = [v["count"] for v in arms.values() if v["status"] == "ok" and "count" in v]
        if "scalar" in case:
            counts.append(case["scalar"]["count"])
        if len(set(counts)) > 1 or (counts and arms["cryptominisat"]["status"] == "ok" and
                                  arms["cryptominisat"]["satisfiable"] != bool(counts[0])):
            result["correctness_mismatches"].append(ident)
        result["cases"].append({"model_id": ident, "arms": arms})
        print(ident, {k: v["status"] for k, v in arms.items()}, flush=True)
        write("NATIVE_CONTROL_RESULTS.json", result)
    if result["correctness_mismatches"]:
        raise ValueError("native correctness mismatch")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("prepare", "native"))
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    if args.worker:
        aeon_worker(args.worker)
    elif args.phase == "prepare" and args.evidence_root:
        prepare(args.evidence_root)
    elif args.phase == "native":
        native()
    else:
        parser.error("choose prepare with evidence-root, or native")
