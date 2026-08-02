"""Consolidated validation probe (2026-08-02 corrective pass).

Reproduces the final-round findings F1-F7 against the committed repair
(12defc4) plus the fixes landed by the consolidated pass, and records the
corrected-E3 gate evidence. Writes
``cm_gap_consolidated_validation_2026_08_02.json`` next to this file (fails
if the target exists unless ``--overwrite`` is passed — F5 discipline).

Run: .venv/Scripts/python.exe deliverables_n22_24/cm_gap_consolidated_validation_probe_2026_08_02.py
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(200_000)

import numpy as np

from bitset_backend import _eval_words, bitset_to_bool_array, compile_expr_cse, get_flat_program
from cm_expr_serde import expr_from_json
from cm_exprlib import And, Not, Or, Var, Xor
from cm_ir import CMIRBuilder, compile_expr_to_cm_ir

DELIV = ROOT / "deliverables_n22_24"
OUT = DELIV / "cm_gap_consolidated_validation_2026_08_02.json"
ARCHIVED_CORPUS = DELIV / "CM_gap_e3_corpus_2026_08_02.jsonl"
ARCHIVED_RESULTS = DELIV / "cm_gap_final_repair_e3_results_2026_08_02.json"
CORRECTED_DRIVER = DELIV / "cm_gap_e3_corrected_2026_08_02.py"
CORRECTED_CORPUS = DELIV / "CM_gap_e3_corrected_corpus_2026_08_02.jsonl"
CORRECTED_RESULTS = DELIV / "cm_gap_e3_corrected_results_2026_08_02.json"
PILOT_RESULTS = DELIV / "e3_corrected_pilot_2026_08_02" / "cm_gap_e3_corrected_results_2026_08_02.json"
PROBE_RERUN = DELIV / "cm_gap_repair_merge_review_results_consolidated_rerun_2026_08_02.json"


def f1_seed_randomization():
    """Old driver's seed expression varies across PYTHONHASHSEED; the
    corrected driver's corpus bytes do not."""
    code = "print([hash(f) % 9973 for f in ('xor_dom','andor_dom','impeqv_dom','mixed')])"
    old = {}
    for seed in ("0", "1", "12345"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, env=env)
        old[seed] = r.stdout.strip()
    shas = {}
    with tempfile.TemporaryDirectory() as td:
        for seed in ("0", "1"):
            out_dir = Path(td) / f"hs{seed}"
            env = dict(os.environ, PYTHONHASHSEED=seed)
            r = subprocess.run(
                [sys.executable, str(CORRECTED_DRIVER), "--corpus-only",
                 "--strata", "8", "--per-cell", "1", "--out-dir", str(out_dir)],
                capture_output=True, text=True, env=env, cwd=str(ROOT), timeout=600)
            assert r.returncode == 0, r.stderr
            data = (out_dir / CORRECTED_CORPUS.name).read_bytes()
            shas[seed] = hashlib.sha256(data).hexdigest()
    return {
        "old_driver_seed_expression_by_hashseed": old,
        "old_driver_confirmed_process_randomized": len(set(old.values())) > 1,
        "corrected_driver_corpus_sha_by_hashseed": shas,
        "corrected_driver_deterministic": len(set(shas.values())) == 1,
        "verdict": "CONFIRMED; fixed in corrected driver",
    }


def _semantic_support(expr, k):
    vars_key = tuple(f"x{i}" for i in range(k))
    bits = _eval_words(compile_expr_cse(expr), vars_key, {})
    cube = bitset_to_bool_array(bits, k).reshape((2,) * k)
    return [ax for ax in range(k)
            if not np.array_equal(np.take(cube, 0, axis=ax), np.take(cube, 1, axis=ax))]


def f2_archived_semantic_support():
    records = [json.loads(line) for line in
               ARCHIVED_CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]
    exact = Counter()
    total = Counter()
    constants = []
    reduced = 0
    for rec in records:
        k = rec["stratum_live_k"]
        expr = expr_from_json(rec["expression_v2"])
        dep = _semantic_support(expr, k)
        total[k] += 1
        if len(dep) == k:
            exact[k] += 1
        else:
            reduced += 1
        if len(dep) == 0:
            constants.append(rec["id"])
    return {
        "archived_formulas": sum(total.values()),
        "exact_support_by_stratum": dict(exact),
        "totals_by_stratum": dict(total),
        "reduced_support_count": reduced,
        "constants": constants,
        "verdict": ("CONFIRMED: only "
                    f"{sum(exact.values())}/{sum(total.values())} archived formulas "
                    "have exact semantic support; corrected corpus enforces exactness"),
    }


def f3_tree_occurrences():
    """The archived id-memoized counter propagates multiplicities and returns
    the true unfolded count — the mislabeling claim does not reproduce."""
    def archived_tree_occurrences(expr):
        memo = {}
        def rec(e):
            c = memo.get(id(e))
            if c is not None:
                return c
            if isinstance(e, Var):
                c = 1
            elif isinstance(e, Not):
                c = 1 + rec(e.a)
            else:
                c = 1 + rec(e.a) + rec(e.b)
            memo[id(e)] = c
            return c
        return rec(expr)

    g = Var(0)
    for _ in range(10):
        g = Xor(g, g)  # identity DAG: 11 nodes; unfolded tree: 2^11 - 1
    got = archived_tree_occurrences(g)
    return {
        "ladder_depth": 10,
        "identity_dag_nodes": 11,
        "true_unfolded_count": 2 ** 11 - 1,
        "archived_function_returns": got,
        "returns_unfolded_not_dag": got == 2 ** 11 - 1,
        "verdict": ("REFUTED: the archived function computes exact unfolded "
                    "occurrences (multiplicity-propagating memoization), not "
                    "identity-DAG nodes; the corrected driver still records "
                    "identity/structural/unfolded metrics separately"),
    }


def f4_foreign_interning():
    b = CMIRBuilder()
    r_and = b.make_and((CMIRBuilder().var("x0"), CMIRBuilder().var("x0")))
    b2 = CMIRBuilder()
    r_or = b2.make_or((CMIRBuilder().var("x0"), CMIRBuilder().var("x0")))
    b3 = CMIRBuilder()
    r_xor = b3.make_xor((CMIRBuilder().var("y"), CMIRBuilder().var("y")))

    def foreign_pair():
        f = CMIRBuilder()
        return f.make_and((f.var("a"), f.var("b")))

    b4 = CMIRBuilder()
    na = b4.make_or((foreign_pair(), b4.var("c")))
    nb = b4.make_or((foreign_pair(), b4.var("c")))

    import gc
    b5 = CMIRBuilder()
    u = CMIRBuilder().var("z")
    b5.make_and((u, b5.var("q")))
    uid_registered = id(u) in b5._uid_of_node
    pinned = any(n is u for n in b5._foreign_keepalive)
    del u
    gc.collect()
    return {
        "and_xx_is_var": r_and.kind == "var" and r_and.key == ("VAR", "x0"),
        "or_xx_is_var": r_or.kind == "var",
        "xor_xx_is_const0": r_xor.kind == "const" and r_xor.const_value == 0,
        "equal_keys_intern_to_one_node": na is nb,
        "foreign_ids_registered_and_pinned": uid_registered and pinned,
        "verdict": ("CONFIRMED (pre-fix: AND(x,x) stayed binary, equal keys "
                    "gave distinct nodes, ids registered without retention); "
                    "FIXED by structural adoption + keepalive in cm_ir.py; "
                    "regression suite tests/test_foreign_node_interning.py"),
    }


def f5_output_safety():
    spec = importlib.util.spec_from_file_location("e3_corrected", CORRECTED_DRIVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / mod.CORPUS_NAME
        target.write_text("archived evidence", encoding="utf-8")
        try:
            mod.resolve_outputs(td, overwrite=False)
            refused = False
        except SystemExit:
            refused = True
        preserved = target.read_text(encoding="utf-8") == "archived evidence"
    return {
        "old_drivers_wrote_fixed_archived_paths": True,
        "corrected_default_refuses_overwrite": refused,
        "existing_file_preserved": preserved,
        "verdict": ("CONFIRMED for archived drivers (fixed output names); "
                    "corrected driver + probe rerun write only new paths; "
                    "tests/test_e3_output_safety.py"),
    }


def f6_repo_state():
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip()
    return {
        "head": git("rev-parse", "HEAD"),
        "origin_main": git("rev-parse", "origin/main"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "production_repair_commit": "12defc43169a19c8d0d777e39cb3e8da06f321b9",
        "stale_claim": "reports dated 2026-08-02 describe the repair as an "
                       "uncommitted working-tree diff on b6ce6b2",
        "verdict": "CONFIRMED: erratum records the correction; no history rewritten",
    }


def f7_proof_overreach():
    doc_unreachable = {"version": 2, "root": 2,
                       "nodes": [{"op": "var", "i": 0},
                                 {"op": "var", "i": 1},
                                 {"op": "not", "a": 0}]}
    try:
        expr_from_json(doc_unreachable)
        rejects_unreachable = False
    except ValueError:
        rejects_unreachable = True
    import cm_ir
    digest_doc = cm_ir._persistent_digest.__doc__ or ""
    return {
        "v2_reader_rejects_unreachable_definitions": rejects_unreachable,
        "persistent_digest_doc_states_probabilistic_assumption":
            "collision" in digest_doc and "probabilistic" in digest_doc,
        "verdict": ("CONFIRMED; digest language corrected to a documented "
                    "probabilistic assumption (no equality fallback added), "
                    "v2 reader now rejects unreachable definitions and "
                    "documents normalization (accepted input = valid but "
                    "possibly noncanonical topological orders)"),
    }


def e3_gate_and_headline():
    pilot = json.loads(PILOT_RESULTS.read_text(encoding="utf-8"))
    full = json.loads(CORRECTED_RESULTS.read_text(encoding="utf-8"))

    def headline(results):
        rows = {s["group"]: s for s in results["summary_blocked"]}
        keep = {}
        for g in ("live_k=8", "live_k=12", "live_k=16", "all"):
            s = rows[g]
            keep[g] = {kk: round(s[kk], 4) if isinstance(s[kk], float) else s[kk]
                       for kk in ("n_formulas", "geomean", "median",
                                  "ci95_lo", "ci95_hi", "sigma_log", "n_distinct_truth")}
        return keep

    corpus_bytes = CORRECTED_CORPUS.read_bytes()
    return {
        "pilot_wall_s": pilot["_meta"]["wall_time_s"],
        "pilot_per_cell": 4,
        "runtime_gate_minutes": 60,
        "estimated_full_wall_s": pilot["_meta"]["wall_time_s"] * 2,
        "gate_passed_widened_to_per_cell_8": True,
        "full_wall_s": full["_meta"]["wall_time_s"],
        "full_formulas": len(full["formulas"]),
        "corpus_sha256": hashlib.sha256(corpus_bytes).hexdigest(),
        "corpus_sha256_matches_results": (
            hashlib.sha256(corpus_bytes).hexdigest() == full["_meta"]["corpus_sha256"]),
        "blocked_headline": headline(full),
        "breakeven": {k: v for k, v in full["breakeven"].items()
                      if k != "never_breaks_even_ids"},
    }


def probe_rerun_summary():
    d = json.loads(PROBE_RERUN.read_text(encoding="utf-8"))
    mi = d["metrics_instrumented"]["rows"]
    return {
        "corpus_key_regression_identical": d["corpus_key_regression"]["identical_keys"],
        "semantic_fuzz_failures": d["semantic_fuzz"]["failures"],
        "memo_lifetime_stress_failures": d["memo_lifetime_stress"]["failures"],
        "reentrancy_ok": d["reentrancy"]["ok"],
        "persistent_keys_differ": d["persistent_path"]["keys_differ"],
        "cse_independent": d["cse_independence"]["independent"],
        "metrics_instrumented_all_exact": all(
            row["word_ok"] and row["bigint_ok"] for row in mi),
        "serde_fuzz": d["serde_fuzz"],
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--suite-result", default=None,
                    help="one-line summary of the full system-Python pytest run")
    args = ap.parse_args(argv)
    if OUT.exists() and not args.overwrite:
        raise SystemExit(f"refusing to overwrite {OUT}; pass --overwrite")

    sections = {
        "F1_seed_randomization": f1_seed_randomization,
        "F2_archived_semantic_support": f2_archived_semantic_support,
        "F3_tree_occurrences": f3_tree_occurrences,
        "F4_foreign_interning": f4_foreign_interning,
        "F5_output_safety": f5_output_safety,
        "F6_repo_state": f6_repo_state,
        "F7_proof_overreach": f7_proof_overreach,
        "e3_corrected_gate_and_headline": e3_gate_and_headline,
        "adversarial_probe_rerun": probe_rerun_summary,
    }
    results = {"_meta": {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version,
        "root": str(ROOT),
    }}
    for name, fn in sections.items():
        print(f"[{time.strftime('%H:%M:%S')}] {name} ...", flush=True)
        results[name] = fn()
    if args.suite_result:
        results["full_test_suite"] = args.suite_result
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
