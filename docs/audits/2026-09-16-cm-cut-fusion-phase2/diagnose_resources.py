"""Isolate Stage-A resource failures under the same Windows Job limits."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from bitset_backend import build_bitset_env, compile_expr_cse, compile_flat, eval_expr_bitset, program_metrics
from cm_ir import compile_expr_to_cm_ir
from cmbench.biology_session_supervisor import run_worker
from cmbench.recognition.cut_fusion import optimize_cut_fusion

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cm_cut_stage_a", HERE / "run_stage_a.py")
stage = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(stage)


def worker(case_index, phase):
    synthetic = stage.make_synthetic_manifest()
    case = stage.stage_cases(synthetic)[case_index]
    _cohort, ident, _group, n_vars, expr = case
    if phase == "direct_truth":
        value = eval_expr_bitset(expr, build_bitset_env(tuple(f"x{i}" for i in range(n_vars))))
        output = {"bits": value.bit_length()}
    elif phase == "fusion_complete":
        result = optimize_cut_fusion(expr, n_vars)
        output = {"accepted": result.accepted, "reason": result.fallback_reason}
    elif phase == "plain_cse":
        output = program_metrics(compile_expr_cse(expr, flatten=True))
    elif phase == "plain_cm":
        output = program_metrics(compile_flat(compile_expr_to_cm_ir(expr)))
    elif phase == "one_pass_pack":
        output = stage.metrics(stage.PACK.rewrite(expr, n_vars).result)
    elif phase == "d10_indexed":
        output = stage.metrics(stage.D10.rewrite(expr, n_vars, index_mode="indexed").result)
    else:
        raise ValueError(phase)
    print(json.dumps({"id": ident, "phase": phase, "output": output}), flush=True)


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        worker(int(sys.argv[2]), sys.argv[3])
        return
    results = json.loads((HERE / "stage-a-results.json").read_text(encoding="utf-8"))
    indices = [row["case_index"] for row in results["receipts"]
               if row["status"] == "resource_limit"]
    phases = ("direct_truth", "plain_cse", "plain_cm", "fusion_complete",
              "one_pass_pack", "d10_indexed")
    rows = []
    for index in indices:
        for phase in phases:
            receipt = run_worker([sys.executable, "-B", str(Path(__file__).resolve()),
                                  "--worker", str(index), phase], timeout_seconds=60,
                                 memory_limit_bytes=512 << 20, max_output_bytes=1 << 20, cwd=ROOT)
            rows.append({"case_index": index, "phase": phase,
                         **{key: value for key, value in receipt.items()
                            if key not in ("stdout", "stderr")},
                         "worker_output": json.loads(receipt["stdout"]) if receipt["status"] == "ok" else None})
            print(json.dumps({"case_index": index, "phase": phase,
                              "status": receipt["status"], "reason": receipt["reason"]}), flush=True)
    document = {"schema": "cm-cut-fusion-resource-diagnosis/v1",
                "limits": {"memory_bytes": 512 << 20, "timeout_seconds": 60}, "rows": rows}
    with (HERE / "resource-diagnosis.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
