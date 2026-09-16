"""Frozen Stage-B lifecycle timing for bounded cut fusion."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from bitset_backend import (
    PreparedFlatEvaluation, _bind_flat_program, _eval_prepared_flat,
    build_bitset_env, clear_bitset_env_cache, compile_expr_cse, compile_flat,
    eval_expr_bitset,
)
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_ir import (clear_cm_ir_compile_cache, clear_cm_ir_persistent_cache,
                   compile_expr_to_cm_ir)
from cmbench.biology_session_supervisor import run_worker
from cmbench.comparative.gf2_restricted_evaluators import (
    PreparedRestriction, compile_restricted_arena, eval_restricted_r2,
)
from cmbench.recognition.cut_fusion import optimize_cut_fusion, template_table
from cmbench.recognition.normalization import normalize_to_fixpoint

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cm_cut_stage_a_timing", HERE / "run_stage_a.py")
stage = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(stage)

ARMS = ("direct", "r2", "cse", "cm", "pack_cse", "pack_cm", "d10_cse",
        "d10_cm", "fixpoint_cse", "fixpoint_cm", "precompute_full",
        "candidate_cse", "candidate_cm")
QS = (1, 4, 16, 64)
ROUNDS = 7


def sha(data):
    return hashlib.sha256(data).hexdigest()


def trace(n_vars):
    result = [{}]
    for i in range(n_vars):
        for j in range(i + 1, n_vars):
            for a, b in ((0, 0), (0, 1), (1, 0), (1, 1)):
                result.append({f"x{i}": a, f"x{j}": b})
    assert len(result) >= 64
    return result[:64]


def serialize_bits(bits, n_vars):
    width = max(1, ((1 << n_vars) + 7) // 8)
    return bytearray(int(bits).to_bytes(width, "little", signed=False))


def restrict_full(bits, names, fixed):
    remaining = tuple(name for name in names if name not in fixed)
    positions = {name: index for index, name in enumerate(remaining)}
    result = 0
    for row in range(1 << len(remaining)):
        source = 0
        for name in names:
            source <<= 1
            if name in fixed:
                source |= fixed[name]
            else:
                source |= (row >> (len(remaining) - 1 - positions[name])) & 1
        result |= ((bits >> source) & 1) << row
    return result, remaining


def compile_arm(arm, expr, n_vars):
    metadata = {}
    if arm == "direct":
        return ("direct", expr), metadata
    if arm == "r2":
        return ("r2", compile_restricted_arena(expr_to_json_dag(expr))), metadata
    if arm == "cse":
        return ("flat", compile_expr_cse(expr, flatten=True)), metadata
    if arm == "cm":
        node = compile_expr_to_cm_ir(expr, reuse_cache=False, persistent_cache=False,
                                     share_aware_flatten=True)
        return ("flat", compile_flat(node)), metadata
    if arm.startswith("pack_"):
        rewritten = stage.PACK.rewrite(expr, n_vars).result
        if arm.endswith("cse"):
            return ("flat", compile_expr_cse(rewritten, flatten=True)), metadata
        node = compile_expr_to_cm_ir(rewritten, reuse_cache=False, persistent_cache=False,
                                     share_aware_flatten=True)
        return ("flat", compile_flat(node)), metadata
    if arm.startswith("d10_"):
        rewritten = stage.D10.rewrite(expr, n_vars, index_mode="indexed").result
        if arm.endswith("cse"):
            return ("flat", compile_expr_cse(rewritten, flatten=True)), metadata
        node = compile_expr_to_cm_ir(rewritten, reuse_cache=False, persistent_cache=False,
                                     share_aware_flatten=True)
        return ("flat", compile_flat(node)), metadata
    if arm.startswith("fixpoint_"):
        rewritten = normalize_to_fixpoint(stage.PACK, expr, n_vars).result
        if arm.endswith("cse"):
            return ("flat", compile_expr_cse(rewritten, flatten=True)), metadata
        node = compile_expr_to_cm_ir(rewritten, reuse_cache=False, persistent_cache=False,
                                     share_aware_flatten=True)
        return ("flat", compile_flat(node)), metadata
    if arm == "precompute_full":
        return ("precompute", compile_expr_cse(expr, flatten=True)), metadata
    if arm.startswith("candidate_"):
        result = optimize_cut_fusion(expr, n_vars)
        metadata = {"candidate_accepted": result.accepted,
                    "candidate_fallback_reason": result.fallback_reason,
                    "selected_rewrites": result.selected_rewrites}
        if arm.endswith("cse"):
            program = result.proposed_cse_program if result.accepted else result.baseline_cse_program
        else:
            program = result.proposed_cm_program if result.accepted else result.baseline_cm_program
        return ("flat", program), metadata
    raise ValueError(arm)


def run_session(document_bytes, n_vars, arm, q, expected):
    clear_bitset_env_cache()
    clear_cm_ir_compile_cache()
    clear_cm_ir_persistent_cache()
    parse_started = time.perf_counter_ns()
    expr = expr_from_json(json.loads(document_bytes))
    parse_ns = time.perf_counter_ns() - parse_started
    compile_started = time.perf_counter_ns()
    try:
        plan, metadata = compile_arm(arm, expr, n_vars)
    except Exception as exc:
        return {"status": "refused", "reason": type(exc).__name__ + ": " + str(exc),
                "parse_ns": parse_ns, "compile_ns": time.perf_counter_ns() - compile_started,
                "bind_ns": 0, "execute_ns": 0, "output_ns": 0, "total_ns": 0}
    compile_ns = time.perf_counter_ns() - compile_started
    names = tuple(f"x{i}" for i in range(n_vars))
    contexts = trace(n_vars)[:q]
    bind_ns = execute_ns = output_ns = 0
    hashes = []
    precomputed = None
    if plan[0] == "precompute":
        started = time.perf_counter_ns()
        template, mask = _bind_flat_program(plan[1], names, {})
        precomputed = _eval_prepared_flat(PreparedFlatEvaluation(plan[1], template, mask, False))
        bind_ns += time.perf_counter_ns() - started
    for request_index, fixed in enumerate(contexts):
        remaining = tuple(name for name in names if name not in fixed)
        if plan[0] == "direct":
            started = time.perf_counter_ns()
            env = build_bitset_env(remaining)
            bind_ns += time.perf_counter_ns() - started
            started = time.perf_counter_ns()
            bits = eval_expr_bitset(plan[1], env, fixed=fixed)
            execute_ns += time.perf_counter_ns() - started
        elif plan[0] == "r2":
            started = time.perf_counter_ns()
            env = build_bitset_env(remaining)
            prepared = PreparedRestriction(dict(fixed), remaining, env, (1 << (1 << len(remaining))) - 1)
            bind_ns += time.perf_counter_ns() - started
            started = time.perf_counter_ns()
            bits = eval_restricted_r2(plan[1], prepared)
            execute_ns += time.perf_counter_ns() - started
        elif plan[0] == "flat":
            started = time.perf_counter_ns()
            template, mask = _bind_flat_program(plan[1], remaining, fixed)
            prepared = PreparedFlatEvaluation(plan[1], template, mask, False)
            bind_ns += time.perf_counter_ns() - started
            started = time.perf_counter_ns()
            bits = _eval_prepared_flat(prepared)
            execute_ns += time.perf_counter_ns() - started
        else:
            started = time.perf_counter_ns()
            normalized_fixed = {name: int(value) for name, value in fixed.items()}
            bind_ns += time.perf_counter_ns() - started
            started = time.perf_counter_ns()
            bits, checked_remaining = restrict_full(precomputed, names, normalized_fixed)
            if checked_remaining != remaining:
                raise AssertionError("precompute restriction order changed")
            execute_ns += time.perf_counter_ns() - started
        started = time.perf_counter_ns()
        delivered = serialize_bits(bits, len(remaining))
        digest = sha(delivered)
        output_ns += time.perf_counter_ns() - started
        if digest != expected[request_index]:
            raise RuntimeError(f"semantic mismatch for {arm} request {request_index}")
        hashes.append(digest)
    total_ns = parse_ns + compile_ns + bind_ns + execute_ns + output_ns
    return {"status": "ok", "parse_ns": parse_ns, "compile_ns": compile_ns,
            "bind_ns": bind_ns, "execute_ns": execute_ns, "output_ns": output_ns,
            "total_ns": total_ns, "output_sha256": hashes, **metadata}


def case_worker(case_row, round_index):
    expr = expr_from_json(case_row["expression_v2"])
    n_vars = case_row["n_vars"]
    names = tuple(f"x{i}" for i in range(n_vars))
    contexts = trace(n_vars)
    env_cache = {}
    expected = []
    for fixed in contexts:
        remaining = tuple(name for name in names if name not in fixed)
        env = env_cache.setdefault(remaining, build_bitset_env(remaining))
        expected.append(sha(serialize_bits(eval_expr_bitset(expr, env, fixed=fixed), len(remaining))))
    clear_bitset_env_cache()
    document_bytes = json.dumps(case_row["expression_v2"], sort_keys=True,
                                separators=(",", ":")).encode("utf-8")
    shift = round_index % len(ARMS)
    order = list(ARMS[shift:] + ARMS[:shift])
    if round_index % 2:
        order.reverse()
    rows = []
    for q in QS:
        for arm_position, arm in enumerate(order):
            value = run_session(document_bytes, n_vars, arm, q, expected[:q])
            rows.append({"case_id": case_row["id"], "family": case_row["family"],
                         "split": case_row["split"], "n_vars": n_vars,
                         "round": round_index, "q": q, "arm": arm,
                         "arm_position": arm_position, **value})
    return rows


def geometric_mean(values):
    return math.exp(sum(math.log(value) for value in values) / len(values))


def summarize(rows):
    groups = {}
    for row in rows:
        if row["status"] != "ok":
            continue
        groups.setdefault((row["case_id"], row["q"], row["arm"]), []).append(row["total_ns"])
    medians = {key: statistics.median(values) for key, values in groups.items() if len(values) == ROUNDS}
    summary = []
    for q in QS:
        case_ids = sorted({key[0] for key in medians if key[1] == q})
        arms = []
        for arm in ARMS:
            values = [medians[(case_id, q, arm)] for case_id in case_ids
                      if (case_id, q, arm) in medians]
            if len(values) == len(case_ids) and values:
                arms.append({"arm": arm, "geomean_median_total_ns": geometric_mean(values)})
        arms.sort(key=lambda row: row["geomean_median_total_ns"])
        summary.append({"q": q, "complete_cases": len(case_ids), "arms": arms})
    return summary


def main():
    manifest = json.loads((HERE / "synthetic-manifest.json").read_text(encoding="utf-8"))
    if len(sys.argv) == 5 and sys.argv[1] == "--worker":
        split, case_index, round_index = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        cases = [row for row in manifest["rows"] if row["split"] == split]
        print(json.dumps(case_worker(cases[case_index], round_index),
                         sort_keys=True, allow_nan=False), flush=True)
        return
    split = sys.argv[1] if len(sys.argv) == 2 else "development"
    if split not in ("development", "locked_confirmation"):
        raise ValueError("timing split must be development or locked_confirmation")
    cases = [row for row in manifest["rows"] if row["split"] == split]
    started = time.perf_counter()
    rows, receipts = [], []
    for case_index, case in enumerate(cases):
        for round_index in range(ROUNDS):
            receipt = run_worker([sys.executable, "-B", str(Path(__file__).resolve()),
                                  "--worker", split, str(case_index), str(round_index)],
                                 timeout_seconds=60, memory_limit_bytes=512 << 20,
                                 max_output_bytes=8 << 20, cwd=ROOT)
            receipts.append({"case_id": case["id"], "round": round_index,
                             **{key: value for key, value in receipt.items()
                                if key not in ("stdout", "stderr")}})
            if receipt["status"] != "ok":
                document = {"schema": "cm-cut-fusion-stage-b-results/v1", "split": split,
                            "status": "stop", "reason": "worker_" + receipt["reason"],
                            "rows": rows, "receipts": receipts}
                stage.write_json(HERE / f"stage-b-{split}-results.json", document)
                print(json.dumps({"status": "stop", "case": case["id"],
                                  "round": round_index, "reason": receipt["reason"]}), flush=True)
                return
            rows.extend(json.loads(receipt["stdout"]))
        print(json.dumps({"completed_cases": case_index + 1, "total_cases": len(cases),
                          "elapsed_seconds": time.perf_counter() - started}), flush=True)
        if time.perf_counter() - started > 1800:
            raise RuntimeError("frozen Stage-B campaign wall limit exceeded")
    refusals = [row for row in rows if row["status"] != "ok"]
    document = {"schema": "cm-cut-fusion-stage-b-results/v1", "split": split,
        "status": "stop" if refusals else "complete", "reason": "arm_refusal" if refusals else "complete",
        "limits": {"rounds": ROUNDS, "qs": list(QS), "memory_bytes": 512 << 20,
                   "worker_timeout_seconds": 60, "campaign_wall_seconds": 1800},
        "arms": list(ARMS), "abc_control": "unavailable_on_path",
        "elapsed_seconds": time.perf_counter() - started, "summary": summarize(rows),
        "refusals": refusals, "rows": rows, "receipts": receipts}
    stage.write_json(HERE / f"stage-b-{split}-results.json", document)
    print(json.dumps({"status": document["status"], "split": split,
                      "refusals": len(refusals), "summary": document["summary"],
                      "elapsed_seconds": document["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    template_table()
    main()
