"""Corrected E3 replication driver (2026-08-02 consolidated audit).

Supersedes ``cm_gap_final_repair_e3_2026_08_02.py``, whose corpus generation
had three defects (consolidated-audit findings F1/F2/F5):

  F1  seeds derived from ``hash(family)`` — process-randomized under
      PYTHONHASHSEED, so the archived corpus was not regenerable;
  F2  strata enforced *syntactic* support only — 43/96 archived formulas had
      reduced semantic support and 5 were constants;
  F5  outputs were written to fixed archived filenames, so reproduction runs
      overwrote the evidence they were meant to check.

This driver:

- **Stable generation.** Seeds come from blake2b digests of an explicit
  ``(generator version, k, family code, shape code, attempt)`` tuple with
  integer family/shape codes (``FAMILY_CODES``/``SHAPE_CODES``); no use of
  ``hash()`` anywhere. Corpus bytes are identical across processes and
  PYTHONHASHSEED values (see tests/test_e3_corpus_determinism.py); the file
  SHA-256 is recorded in the results. The corpus contains no timestamps and
  is reloadable via ``--corpus`` without regeneration.
- **Exact semantic support.** Every candidate's complete packed truth
  function is computed (independent structural-CSE pipeline) and per-variable
  influence is checked by hypercube axis comparison; a formula is admitted
  only if its semantic support is exactly the target variable set. Constants
  and reduced-support functions are rejected; semantic support indices are
  recorded. The CM pipeline must agree bit-for-bit at admission time.
- **Independent functions.** Structural hash and packed-truth-function
  SHA-256 are recorded; within a stratum both must be distinct.
- **Actual operator-family membership** (measured on structural-DAG binary
  operator classes, not generator weights):
    xor_dom     XOR >= 60% of binary operator classes
    andor_dom   AND+OR >= 60%
    impeqv_dom  IMP+EQV >= 60%
    mixed       >= 3 binary operator types, none > 50%
- **Actual shape membership.** Structural metrics are recorded (unfolded
  occurrences via multiplicity propagation, identity-DAG nodes,
  structural-DAG nodes, unfolding factors, depth, fanout distribution).
  Admission: ``shared`` requires structural sharing factor
  (unfolded/structural) >= 1.5; ``tree`` requires no repeated non-leaf
  structural subtree (every non-leaf structural class occurs exactly once).
  All formulas are capped at 60,000 unfolded occurrences so the raw
  (no-CSE) ablation arm stays feasible on every formula.
- **Output safety.** Outputs go to ``--out-dir``; if any target exists the
  driver fails unless ``--overwrite`` is passed (see
  tests/test_e3_output_safety.py).

Measurement (unchanged in structure from the superseded driver where it was
sound; corrected labels):

- Primary arms: repaired CM kernel vs structural-CSE kernel, bare
  ``_eval_words`` on prebuilt programs. Secondary: CSE+flatten, raw no-CSE
  ablation, admission wrapper, warm-environment compile+evaluate totals
  (labelled ``warmenv`` — a warm-process, warm-words-env measurement, NOT a
  cold start), repeated-workload totals, per-formula break-even.
- Exact packed equality across every arm and the wrapper before timing.
- Blocked and round-robin schedules measured and reported separately.
- Statistics: per-formula paired log ratios; geomean/median/sigma_log/df;
  formula-level bootstrap CIs for subgroups; stratified bootstrap (resampling
  within each family x shape cell) for stratum and all-corpus aggregates so
  the designed mixture stays fixed; family x shape interaction rows;
  truth-function uniqueness. Results generalize only to this balanced
  synthetic generator; an interval excluding parity is not a universal CM
  claim.

Recommended sequence (60-minute gate):

  # pilot (4 per cell, 96 formulas)
  .venv/Scripts/python.exe deliverables_n22_24/cm_gap_e3_corrected_2026_08_02.py \
      --per-cell 4 --out-dir deliverables_n22_24/e3_corrected_pilot_2026_08_02
  # if estimated full runtime (pilot wall x 2) < 60 min, run the full design
  .venv/Scripts/python.exe deliverables_n22_24/cm_gap_e3_corrected_2026_08_02.py \
      --per-cell 8 --out-dir deliverables_n22_24
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(200_000)

import numpy as np

from bitset_backend import (
    _eval_words,
    bitset_env_cache_stats,
    bitset_to_bool_array,
    compile_expr_cse,
    compile_expr_flat,
    compile_flat,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Eqv, Imp, Not, Or, Var, Xor
from cm_ir import compile_expr_to_cm_ir, expr_structural_hash, materialize_hybrid_no_reinflate

GENERATOR_VERSION = "e3-corrected-2026-08-02.1"
FAMILY_CODES = {"xor_dom": 1, "andor_dom": 2, "impeqv_dom": 3, "mixed": 4}
SHAPE_CODES = {"tree": 1, "shared": 2}
STRATA_DEFAULT = (8, 12, 16)
MAX_UNFOLDED = 60_000
SHARED_MIN_SHARING = 1.5

CORPUS_NAME = "CM_gap_e3_corrected_corpus_2026_08_02.jsonl"
RESULTS_NAME = "cm_gap_e3_corrected_results_2026_08_02.json"
SUMMARY_NAME = "CM_gap_e3_corrected_summary_2026_08_02.csv"

OPS = {"and": And, "or": Or, "xor": Xor, "imp": Imp, "eqv": Eqv}
FAMILIES = {
    "xor_dom": {"xor": 0.75, "and": 0.08, "or": 0.07, "imp": 0.05, "eqv": 0.05},
    "andor_dom": {"and": 0.40, "or": 0.40, "xor": 0.10, "imp": 0.05, "eqv": 0.05},
    "impeqv_dom": {"imp": 0.40, "eqv": 0.40, "and": 0.07, "or": 0.07, "xor": 0.06},
    "mixed": {"and": 0.2, "or": 0.2, "xor": 0.2, "imp": 0.2, "eqv": 0.2},
}
GENERALIZATION_NOTE = (
    "Results generalize only to this balanced synthetic generator "
    f"({GENERATOR_VERSION}); an interval excluding parity is not a universal "
    "CM claim."
)


def stable_seed(k: int, family: str, shape: str, attempt: int) -> int:
    """Deterministic 63-bit seed from explicit stable codes (no hash())."""
    tag = (f"{GENERATOR_VERSION}|k={k}|family={FAMILY_CODES[family]}"
           f"|shape={SHAPE_CODES[shape]}|attempt={attempt}")
    digest = hashlib.blake2b(tag.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") >> 1


def pick_op(rng, weights):
    r = rng.random()
    acc = 0.0
    for name, w in weights.items():
        acc += w
        if r <= acc:
            return name
    return "xor"


def tree_formula(rng, k, weights):
    """Low-sharing random tree; every variable appears syntactically."""
    extra = rng.randrange(0, max(1, k // 2) + 1)
    leaves = list(range(k)) + [rng.randrange(k) for _ in range(extra)]
    rng.shuffle(leaves)
    nodes = [Var(i) for i in leaves]
    while len(nodes) > 1:
        i = rng.randrange(len(nodes) - 1)
        a = nodes.pop(i)
        b = nodes.pop(rng.randrange(len(nodes)))
        combined = OPS[pick_op(rng, weights)](a, b)
        if rng.random() < 0.12:
            combined = Not(combined)
        nodes.insert(rng.randrange(len(nodes) + 1), combined)
    return nodes[0]


def shared_formula(rng, k, weights):
    """Controlled shared DAG; every variable appears syntactically."""
    pool = [Var(i) for i in range(k)]
    for _ in range(k + rng.randrange(k, 2 * k)):
        name = pick_op(rng, weights)
        e = OPS[name](rng.choice(pool), rng.choice(pool))
        if rng.random() < 0.10:
            e = Not(e)
        pool.append(e)
    root = pool[-1]
    for e in pool[-5:-1]:
        root = OPS[max(weights, key=weights.get)](root, e)
    missing = set(range(k)) - set(syntactic_support(root))
    dom = max(weights, key=weights.get)
    for m in sorted(missing):
        root = OPS[dom](root, Var(m))
    return root


def syntactic_support(expr):
    seen, out, stack = set(), set(), [expr]
    while stack:
        cur = stack.pop()
        if id(cur) in seen:
            continue
        seen.add(id(cur))
        if isinstance(cur, Var):
            out.add(int(cur.i))
        elif isinstance(cur, Not):
            stack.append(cur.a)
        else:
            stack.extend((cur.a, cur.b))
    return sorted(out)


def analyze_structure(expr):
    """Structural-DAG analysis (consolidated-audit F3 correction).

    Returns a dict with separately recorded identity-DAG node count,
    structural-DAG node count, full unfolded occurrence count (multiplicity
    propagation over the structural DAG — exact, no per-occurrence walk),
    unfolding factors, maximum depth, fanout distribution, operator mixes
    (identity and structural), and tree/sharing admission facts.
    """
    uid_by_id = {}
    intern = {}
    spec = []            # uid -> (kind, payload, child uids); postorder => children first
    identity_nodes = 0
    scheduled = set()
    stack = [(expr, False)]
    while stack:
        e, processed = stack.pop()
        if processed:
            if isinstance(e, Var):
                skey = ("v", int(e.i))
                entry = ("var", int(e.i), ())
            elif isinstance(e, Not):
                children = (uid_by_id[id(e.a)],)
                skey = ("n",) + children
                entry = ("not", "NOT", children)
            else:
                opname = type(e).__name__
                children = (uid_by_id[id(e.a)], uid_by_id[id(e.b)])
                skey = (opname,) + children
                entry = ("bin", opname, children)
            uid = intern.get(skey)
            if uid is None:
                uid = intern[skey] = len(spec)
                spec.append(entry)
            uid_by_id[id(e)] = uid
            continue
        if id(e) in scheduled:
            continue
        scheduled.add(id(e))
        identity_nodes += 1
        stack.append((e, True))
        if isinstance(e, Var):
            pass
        elif isinstance(e, Not):
            stack.append((e.a, False))
        elif isinstance(e, (And, Or, Xor, Imp, Eqv)):
            stack.append((e.b, False))
            stack.append((e.a, False))
        else:
            raise TypeError(e)
    root_uid = uid_by_id[id(expr)]
    n = len(spec)

    # Unfolded occurrences per structural class: multiplicity propagation in
    # reverse topological (descending uid) order. Exact tree-unfolding counts.
    occ = [0] * n
    occ[root_uid] = 1
    for uid in range(n - 1, -1, -1):
        if occ[uid] == 0:
            continue
        for child in spec[uid][2]:
            occ[child] += occ[uid]
    unfolded_total = sum(occ)

    # Depth (children-first order) and structural fanout (consumer edges per
    # class, each structurally distinct parent counted once).
    depth = [1] * n
    fanout = [0] * n
    for uid, (_kind, _payload, children) in enumerate(spec):
        for child in children:
            fanout[child] += 1
            if depth[child] + 1 > depth[uid]:
                depth[uid] = depth[child] + 1

    struct_mix = Counter(payload for kind, payload, _c in spec if kind == "bin")
    identity_mix = Counter()
    seen = set()
    stack = [expr]
    while stack:
        e = stack.pop()
        if id(e) in seen:
            continue
        seen.add(id(e))
        if isinstance(e, Not):
            identity_mix["NOT"] += 1
            stack.append(e.a)
        elif not isinstance(e, Var):
            identity_mix[type(e).__name__] += 1
            stack.extend((e.a, e.b))

    repeated_nonleaf = [uid for uid, (kind, _p, _c) in enumerate(spec)
                        if kind != "var" and occ[uid] > 1]
    fanout_hist = Counter(fanout[uid] for uid in range(n))
    return {
        "identity_dag_nodes": identity_nodes,
        "structural_dag_nodes": n,
        "unfolded_occurrences": unfolded_total,
        "unfolding_factor_identity": unfolded_total / identity_nodes,
        "unfolding_factor_structural": unfolded_total / n,
        "sharing_factor": unfolded_total / n,
        "max_depth": depth[root_uid],
        "max_fanout": max(fanout) if fanout else 0,
        "fanout_histogram": {str(f): c for f, c in sorted(fanout_hist.items())},
        "operator_mix_structural": dict(sorted(struct_mix.items())),
        "operator_mix_identity": dict(sorted(identity_mix.items())),
        "n_repeated_nonleaf_structural": len(repeated_nonleaf),
    }


def family_admission(struct_mix):
    """Actual operator-family membership from structural binary-op classes."""
    n_bin = sum(struct_mix.values())
    if n_bin == 0:
        return {"n_binary_classes": 0, "actual_families": []}
    frac = {op: struct_mix.get(op, 0) / n_bin
            for op in ("And", "Or", "Xor", "Imp", "Eqv")}
    families = []
    if frac["Xor"] >= 0.60:
        families.append("xor_dom")
    if frac["And"] + frac["Or"] >= 0.60:
        families.append("andor_dom")
    if frac["Imp"] + frac["Eqv"] >= 0.60:
        families.append("impeqv_dom")
    n_types = sum(1 for v in struct_mix.values() if v > 0)
    if n_types >= 3 and max(frac.values()) <= 0.50:
        families.append("mixed")
    return {
        "n_binary_classes": n_bin,
        "binary_fractions": {k: round(v, 4) for k, v in frac.items()},
        "n_binary_types": n_types,
        "actual_families": families,
    }


def semantic_profile(expr, k):
    """Exact semantic support and truth-function SHA-256 over x0..x{k-1}.

    Uses the structural-CSE pipeline (independent of cm_ir) as the reference;
    the packed function is the full 2^k truth table.
    """
    vars_key = tuple(f"x{i}" for i in range(k))
    bits = _eval_words(compile_expr_cse(expr), vars_key, {})
    arr = bitset_to_bool_array(bits, k)
    cube = arr.reshape((2,) * k)
    dep = [ax for ax in range(k)
           if not np.array_equal(np.take(cube, 0, axis=ax), np.take(cube, 1, axis=ax))]
    truth_sha = hashlib.sha256(int(bits).to_bytes((1 << k) // 8, "little")).hexdigest()
    return dep, truth_sha, bits


def _orientation_self_check():
    """Axis j of the reshaped truth cube must correspond to vars_key[j]."""
    expr = And(Or(Var(0), Var(0)), Var(0))  # == x0
    vars_key = tuple(f"x{i}" for i in range(6))
    bits = _eval_words(compile_expr_cse(expr), vars_key, {})
    cube = bitset_to_bool_array(bits, 6).reshape((2,) * 6)
    dep = [ax for ax in range(6)
           if not np.array_equal(np.take(cube, 0, axis=ax), np.take(cube, 1, axis=ax))]
    if dep != [0]:
        raise AssertionError(f"truth-cube orientation self-check failed: {dep}")


def build_corpus(strata, per_cell, max_attempts=500, log=print):
    _orientation_self_check()
    records = []
    rejection_stats = {}
    for k in strata:
        stratum_hashes = set()
        stratum_truths = set()
        for family, weights in FAMILIES.items():
            for shape in ("tree", "shared"):
                made = 0
                attempt = 0
                rejects = Counter()
                while made < per_cell:
                    attempt += 1
                    if attempt > max_attempts:
                        raise RuntimeError(
                            f"rejection sampling exhausted {max_attempts} attempts "
                            f"for cell k={k}/{family}/{shape} after {made} admissions; "
                            f"rejects={dict(rejects)}")
                    seed = stable_seed(k, family, shape, attempt)
                    rng = random.Random(seed)
                    expr = (tree_formula if shape == "tree" else shared_formula)(rng, k, weights)
                    if len(syntactic_support(expr)) != k:
                        rejects["syntactic_support"] += 1
                        continue
                    struct = analyze_structure(expr)
                    if struct["unfolded_occurrences"] > MAX_UNFOLDED:
                        rejects["unfolded_cap"] += 1
                        continue
                    if shape == "tree" and struct["n_repeated_nonleaf_structural"] > 0:
                        rejects["tree_repeated_nonleaf"] += 1
                        continue
                    if shape == "shared" and struct["sharing_factor"] < SHARED_MIN_SHARING:
                        rejects["shared_low_sharing"] += 1
                        continue
                    fam = family_admission(struct["operator_mix_structural"])
                    if family not in fam["actual_families"]:
                        rejects["family_membership"] += 1
                        continue
                    dep, truth_sha, bits_cse = semantic_profile(expr, k)
                    if len(dep) == 0:
                        rejects["constant"] += 1
                        continue
                    if dep != list(range(k)):
                        rejects["semantic_support"] += 1
                        continue
                    h = expr_structural_hash(expr)
                    if h in stratum_hashes:
                        rejects["dup_structural_hash"] += 1
                        continue
                    if truth_sha in stratum_truths:
                        rejects["dup_truth_function"] += 1
                        continue
                    # Differential admission check: CM pipeline must agree.
                    vars_key = tuple(f"x{i}" for i in range(k))
                    bits_cm = _eval_words(
                        get_flat_program(compile_expr_to_cm_ir(expr)), vars_key, {})
                    if bits_cm != bits_cse:
                        raise AssertionError(
                            f"CM/CSE truth disagreement at admission: k={k} "
                            f"{family}/{shape} seed={seed}")
                    stratum_hashes.add(h)
                    stratum_truths.add(truth_sha)
                    made += 1
                    records.append({
                        "id": f"e3c-k{k}-{family}-{shape}-{made}-{h[:12]}",
                        "generator_version": GENERATOR_VERSION,
                        "stratum_live_k": k,
                        "op_family": family,
                        "family_code": FAMILY_CODES[family],
                        "shape": shape,
                        "shape_code": SHAPE_CODES[shape],
                        "seed": seed,
                        "attempt": attempt,
                        "structural_hash": h,
                        "truth_sha256": truth_sha,
                        "syntactic_support_size": k,
                        "semantic_support_size": len(dep),
                        "semantic_support_indices": dep,
                        "family_admission": fam,
                        **struct,
                        "expression_v2": expr_to_json_dag(expr),
                    })
                rejection_stats[f"k{k}/{family}/{shape}"] = {
                    "attempts": attempt, "admitted": made, "rejects": dict(rejects)}
                log(f"  cell k={k}/{family}/{shape}: {made} admitted in {attempt} attempts")
    return records, rejection_stats


def corpus_to_bytes(records, rejection_stats, strata, per_cell):
    """Deterministic corpus serialization (no timestamps, sorted keys)."""
    meta = {
        "record_type": "e3_corrected_corpus_meta",
        "generator_version": GENERATOR_VERSION,
        "family_codes": FAMILY_CODES,
        "shape_codes": SHAPE_CODES,
        "strata": list(strata),
        "per_cell": per_cell,
        "max_unfolded": MAX_UNFOLDED,
        "shared_min_sharing": SHARED_MIN_SHARING,
        "admission_rules": {
            "semantic_support": "exact packed-truth influence == target set",
            "family": "structural binary classes: dominant >=60%; mixed: >=3 types, none >50%",
            "tree": "no repeated non-leaf structural subtree",
            "shared": f"sharing factor (unfolded/structural) >= {SHARED_MIN_SHARING}",
            "distinctness": "structural hash AND truth-function SHA-256 unique per stratum",
        },
        "rejection_stats": rejection_stats,
    }
    lines = [json.dumps(meta, sort_keys=True, separators=(",", ":"))]
    lines.extend(json.dumps(rec, sort_keys=True, separators=(",", ":")) for rec in records)
    return ("\n".join(lines) + "\n").encode("utf-8")


def load_corpus(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    meta = json.loads(lines[0])
    if meta.get("record_type") != "e3_corrected_corpus_meta":
        raise ValueError(f"{path} is not an e3-corrected corpus (missing meta line)")
    records = [json.loads(line) for line in lines[1:] if line.strip()]
    return meta, records


def timed(fn, repeats=1, blocks=3):
    best = float("inf")
    for _ in range(blocks):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        best = min(best, (time.perf_counter() - t0) / repeats)
    return best


def prepare(record):
    expr = expr_from_json(record["expression_v2"])
    k = record["stratum_live_k"]
    support = tuple(f"x{i}" for i in range(k))
    node = compile_expr_to_cm_ir(expr)
    progs = {
        "cm": get_flat_program(node),
        "cse": compile_expr_cse(expr),
        "cse_flat": compile_expr_cse(expr, flatten=True),
        "raw": compile_expr_flat(expr),   # feasible: corpus caps unfolding
    }
    vals = {arm: _eval_words(p, support, {}) for arm, p in progs.items()}
    ref = vals["cm"]
    if any(v != ref for v in vals.values()):
        raise AssertionError(f"packed mismatch: {record['id']}")
    ref_sha = hashlib.sha256(int(ref).to_bytes((1 << k) // 8, "little")).hexdigest()
    if ref_sha != record["truth_sha256"]:
        raise AssertionError(f"truth drift vs corpus record: {record['id']}")
    wrapped = materialize_hybrid_no_reinflate(
        node, support, fixed={}, hybrid_threshold=16, allow_reduced_output=False,
        max_full_output_vars=16, flat_eval=True, words_eval=True)
    if int(wrapped.bits) != ref:
        raise AssertionError(f"wrapper mismatch: {record['id']}")
    return expr, node, support, progs


def measure_blocked(record, expr, node, support, progs, rounds):
    row = {
        "id": record["id"], "stratum_live_k": record["stratum_live_k"],
        "op_family": record["op_family"], "shape": record["shape"],
        "structural_hash": record["structural_hash"],
        "truth_sha256": record["truth_sha256"],
        "unfolded_occurrences": record["unfolded_occurrences"],
        "structural_dag_nodes": record["structural_dag_nodes"],
        "schedule": "blocked_warm", "rounds": rounds,
        "packed_equal_all_arms": True,
    }
    row["parse_us"] = timed(lambda: expr_from_json(record["expression_v2"])) * 1e6

    for arm, prog in progs.items():
        m = program_metrics(prog)
        row[f"{arm}_flat_instructions"] = m["flat_instructions"]
        row[f"{arm}_executed_word_ops"] = m["executed_word_ops"]
        row[f"{arm}_loads"] = m["loads"]
        row[f"{arm}_peak_live_word_buffers"] = m["peak_live_word_buffers"]

    row["cm_prep_us"] = timed(lambda: compile_expr_to_cm_ir(expr)) * 1e6
    row["cm_lower_us"] = timed(lambda: compile_flat(node)) * 1e6
    row["cse_prep_us"] = timed(lambda: compile_expr_cse(expr)) * 1e6
    row["cse_flat_prep_us"] = timed(lambda: compile_expr_cse(expr, flatten=True)) * 1e6
    row["raw_prep_us"] = timed(lambda: compile_expr_flat(expr), blocks=1) * 1e6
    row["prep_ratio_cm_vs_cse"] = row["cm_prep_us"] / row["cse_prep_us"]

    repeats = max(20, min(200, 20_000 // max(1, len(progs["cm"].ops))))
    row["kernel_repeats"] = repeats
    ratios = []
    cm_times, cse_times = [], []
    for rnd in range(rounds):
        if rnd % 2:
            cm_s = timed(lambda: _eval_words(progs["cm"], support, {}), repeats, blocks=1)
            bs_s = timed(lambda: _eval_words(progs["cse"], support, {}), repeats, blocks=1)
        else:
            bs_s = timed(lambda: _eval_words(progs["cse"], support, {}), repeats, blocks=1)
            cm_s = timed(lambda: _eval_words(progs["cm"], support, {}), repeats, blocks=1)
        ratios.append(cm_s / bs_s)
        cm_times.append(cm_s)
        cse_times.append(bs_s)
    row["cm_kernel_us"] = statistics.median(cm_times) * 1e6
    row["cse_kernel_us"] = statistics.median(cse_times) * 1e6
    row["blocked_ratio_median"] = statistics.median(ratios)
    row["blocked_ratios"] = ratios

    for arm in ("cse_flat", "raw"):
        if len(progs[arm].ops) <= 20_000:
            reps = max(3, min(repeats, 20_000 // max(1, len(progs[arm].ops))))
            row[f"{arm}_kernel_us"] = timed(
                lambda a=arm: _eval_words(progs[a], support, {}), reps) * 1e6

    def wrapper_call():
        return materialize_hybrid_no_reinflate(
            node, support, fixed={}, hybrid_threshold=16, allow_reduced_output=False,
            max_full_output_vars=16, flat_eval=True, words_eval=True)

    row["cm_wrapper_total_us"] = timed(wrapper_call, repeats=30) * 1e6
    row["cm_wrapper_overhead_us"] = row["cm_wrapper_total_us"] - row["cm_kernel_us"]

    # Warm-environment compile+evaluate totals: warm process, warm words-env /
    # global caches. NOT a cold start (superseded driver mislabelled this).
    def warmenv_cm():
        n = compile_expr_to_cm_ir(expr)
        return _eval_words(compile_flat(n), support, {})

    row["cm_warmenv_compile_eval_us"] = timed(warmenv_cm) * 1e6
    row["cse_warmenv_compile_eval_us"] = timed(
        lambda: _eval_words(compile_expr_cse(expr), support, {})) * 1e6
    row["cm_repeated100_total_us"] = row["cm_prep_us"] + 100 * row["cm_kernel_us"]
    row["cse_repeated100_total_us"] = row["cse_prep_us"] + 100 * row["cse_kernel_us"]
    prep_gap = row["cm_prep_us"] - row["cse_prep_us"]
    eval_gain = row["cse_kernel_us"] - row["cm_kernel_us"]
    row["breakeven_evals_vs_cse"] = (
        (0 if prep_gap <= 0 else math.ceil(prep_gap / eval_gain)) if eval_gain > 0 else None)
    row["never_breaks_even_vs_cse"] = row["breakeven_evals_vs_cse"] is None
    return row


def measure_round_robin(prepared, rr_passes):
    tot_cm = defaultdict(float)
    tot_bs = defaultdict(float)
    for p in range(rr_passes):
        for rec_id, support, progs in prepared:
            if p % 2:
                t0 = time.perf_counter(); _eval_words(progs["cm"], support, {})
                t1 = time.perf_counter(); _eval_words(progs["cse"], support, {})
                t2 = time.perf_counter()
                tot_cm[rec_id] += t1 - t0; tot_bs[rec_id] += t2 - t1
            else:
                t0 = time.perf_counter(); _eval_words(progs["cse"], support, {})
                t1 = time.perf_counter(); _eval_words(progs["cm"], support, {})
                t2 = time.perf_counter()
                tot_bs[rec_id] += t1 - t0; tot_cm[rec_id] += t2 - t1
    return {rid: tot_cm[rid] / tot_bs[rid] for rid, _, _ in prepared}


def _bootstrap_plain(logs, rng, draws):
    n = len(logs)
    means = []
    for _ in range(draws):
        means.append(statistics.mean([logs[rng.randrange(n)] for _ in range(n)]))
    means.sort()
    return math.exp(means[int(0.025 * draws)]), math.exp(means[int(0.975 * draws)])


def _bootstrap_stratified(cells, rng, draws):
    """Resample formulas within each cell; cell sizes (the designed mixture)
    stay fixed. ``cells`` is a list of per-cell log-ratio lists."""
    total = sum(len(c) for c in cells)
    means = []
    for _ in range(draws):
        acc = 0.0
        for cell in cells:
            m = len(cell)
            acc += sum(cell[rng.randrange(m)] for _ in range(m))
        means.append(acc / total)
    means.sort()
    return math.exp(means[int(0.025 * draws)]), math.exp(means[int(0.975 * draws)])


def summarize(rows, ratio_key, label, draws):
    out = []
    rng = random.Random(20260802)

    def stat_block(sel, group, stratified_cells=None):
        logs = [math.log(r[ratio_key]) for r in sel]
        n = len(logs)
        entry = {
            "schedule": label, "group": group, "n_formulas": n,
            "geomean": math.exp(statistics.mean(logs)),
            "median": math.exp(statistics.median(logs)),
            "sigma_log": statistics.stdev(logs) if n > 1 else None,
            "df": n - 1,
            "n_distinct_truth": len({r["truth_sha256"] for r in sel}),
        }
        if stratified_cells is not None:
            lo, hi = _bootstrap_stratified(stratified_cells, rng, draws)
            entry["bootstrap"] = "stratified_by_cell"
            entry["ci95_lo"], entry["ci95_hi"] = lo, hi
        elif n > 3:
            lo, hi = _bootstrap_plain(logs, rng, draws)
            entry["bootstrap"] = "formula"
            entry["ci95_lo"], entry["ci95_hi"] = lo, hi
        return entry

    def cells_of(sel, keys):
        cells = defaultdict(list)
        for r in sel:
            cells[tuple(r[key] for key in keys)].append(math.log(r[ratio_key]))
        return list(cells.values())

    by_stratum = defaultdict(list)
    for r in rows:
        by_stratum[r["stratum_live_k"]].append(r)
    for k, sel in sorted(by_stratum.items()):
        out.append(stat_block(sel, f"live_k={k}",
                              stratified_cells=cells_of(sel, ("op_family", "shape"))))
        for family in FAMILIES:
            sub = [r for r in sel if r["op_family"] == family]
            if sub:
                out.append(stat_block(sub, f"live_k={k}/family={family}"))
        for shape in ("tree", "shared"):
            sub = [r for r in sel if r["shape"] == shape]
            if sub:
                out.append(stat_block(sub, f"live_k={k}/shape={shape}"))
    # family x shape interaction rows pooled over strata
    for family in FAMILIES:
        for shape in ("tree", "shared"):
            sub = [r for r in rows if r["op_family"] == family and r["shape"] == shape]
            if sub:
                out.append(stat_block(sub, f"family={family}/shape={shape}"))
    out.append(stat_block(
        rows, "all",
        stratified_cells=cells_of(rows, ("stratum_live_k", "op_family", "shape"))))
    return out


def resolve_outputs(out_dir, overwrite, writing_corpus=True):
    out_dir = Path(out_dir)
    targets = {"results": out_dir / RESULTS_NAME, "summary": out_dir / SUMMARY_NAME}
    if writing_corpus:
        targets["corpus"] = out_dir / CORPUS_NAME
    existing = [str(p) for p in targets.values() if p.exists()]
    if existing and not overwrite:
        raise SystemExit(
            "refusing to overwrite existing output(s):\n  " + "\n  ".join(existing)
            + "\nPass --overwrite to replace them, or choose a different --out-dir.")
    out_dir.mkdir(parents=True, exist_ok=True)
    return targets


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", default=str(ROOT / "deliverables_n22_24"),
                    help="output directory (default: deliverables_n22_24)")
    ap.add_argument("--overwrite", action="store_true",
                    help="allow replacing existing output files (default: fail)")
    ap.add_argument("--per-cell", type=int, default=8,
                    help="formulas per (stratum, family, shape) cell (pilot: 4)")
    ap.add_argument("--strata", default="8,12,16",
                    help="comma-separated live_k strata")
    ap.add_argument("--corpus", default=None,
                    help="load an existing corrected corpus instead of generating")
    ap.add_argument("--corpus-only", action="store_true",
                    help="generate and write the corpus, skip measurement")
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--rr-passes", type=int, default=60)
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--max-attempts", type=int, default=500)
    args = ap.parse_args(argv)

    strata = tuple(int(s) for s in args.strata.split(","))
    t_start = time.perf_counter()
    targets = resolve_outputs(args.out_dir, args.overwrite,
                              writing_corpus=args.corpus is None)

    if args.corpus is not None:
        corpus_meta, corpus = load_corpus(args.corpus)
        corpus_bytes = Path(args.corpus).read_bytes()
        corpus_path = Path(args.corpus)
        rejection_stats = corpus_meta.get("rejection_stats", {})
        print(f"loaded corpus: {corpus_path} ({len(corpus)} formulas)")
    else:
        print("generating corpus ...", flush=True)
        corpus, rejection_stats = build_corpus(
            strata, args.per_cell, max_attempts=args.max_attempts)
        corpus_bytes = corpus_to_bytes(corpus, rejection_stats, strata, args.per_cell)
        corpus_path = targets["corpus"]
        corpus_path.write_bytes(corpus_bytes)
        print(f"wrote {corpus_path}")
    corpus_sha = hashlib.sha256(corpus_bytes).hexdigest()
    print(f"corpus sha256: {corpus_sha}")

    n_cells = len(strata) * len(FAMILIES) * 2
    counts = Counter((r["stratum_live_k"], r["op_family"], r["shape"]) for r in corpus)
    assert len(counts) == n_cells
    per_cell_actual = set(counts.values())
    print(f"  {len(corpus)} formulas, {len(counts)} cells, per-cell {sorted(per_cell_actual)}")
    for k in strata:
        sel = [r for r in corpus if r["stratum_live_k"] == k]
        assert all(r["semantic_support_size"] == k for r in sel)
        assert len({r["structural_hash"] for r in sel}) == len(sel)
        assert len({r["truth_sha256"] for r in sel}) == len(sel)
    print("  semantic support exact and hashes/truths distinct in every stratum")

    if args.corpus_only:
        print(f"corpus-only run complete in {time.perf_counter() - t_start:.1f}s")
        return 0

    try:
        git_rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.strip()
    except Exception:
        git_rev = "unknown"

    rows = []
    by_stratum_prepared = defaultdict(list)
    for rec in corpus:
        expr, node, support, progs = prepare(rec)
        rows.append(measure_blocked(rec, expr, node, support, progs, args.rounds))
        by_stratum_prepared[rec["stratum_live_k"]].append((rec["id"], support, progs))
        if len(rows) % 24 == 0:
            print(f"  [{time.strftime('%H:%M:%S')}] measured {len(rows)}/{len(corpus)}",
                  flush=True)

    print("round-robin schedules ...", flush=True)
    rr_ratio_by_id = {}
    for k, prepared in sorted(by_stratum_prepared.items()):
        rr_ratio_by_id.update(measure_round_robin(prepared, args.rr_passes))
    for r in rows:
        r["rr_ratio"] = rr_ratio_by_id[r["id"]]

    blocked_summary = summarize(rows, "blocked_ratio_median", "blocked", args.bootstrap)
    rr_summary = summarize(rows, "rr_ratio", "round_robin", args.bootstrap)
    wall_s = time.perf_counter() - t_start

    never_be = sorted(r["id"] for r in rows if r["never_breaks_even_vs_cse"])
    be_values = [r["breakeven_evals_vs_cse"] for r in rows
                 if r["breakeven_evals_vs_cse"] is not None]

    results = {
        "_meta": {
            "driver": Path(__file__).name,
            "supersedes": "cm_gap_final_repair_e3_2026_08_02.py",
            "generator_version": GENERATOR_VERSION,
            "python": sys.version, "numpy": np.__version__,
            "cpu": platform.processor(), "platform": platform.platform(),
            "git_revision": git_rev,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_time_s": wall_s,
            "corpus_file": str(corpus_path),
            "corpus_sha256": corpus_sha,
            "per_cell": args.per_cell if args.corpus is None else "from corpus",
            "rounds": args.rounds, "rr_passes": args.rr_passes,
            "bootstrap_draws": args.bootstrap,
            "cache_state": (
                "blocked: warm within formula; round-robin: cycling supports. "
                "warmenv_compile_eval totals run in a warm process with warm "
                "global caches (bitset words env, node-attached programs "
                "excluded by recompiling) — they are NOT cold-start numbers."),
            "bitset_env_cache": bitset_env_cache_stats(),
            "primary_arms": "repaired CM kernel vs structural-CSE kernel, bare _eval_words",
            "schedules_note": "blocked and round-robin reported separately, never pooled",
            "inferential_unit": "formula (structural hash + truth function)",
            "generalization": GENERALIZATION_NOTE,
            "rejection_stats": rejection_stats,
        },
        "formulas": rows,
        "summary_blocked": blocked_summary,
        "summary_round_robin": rr_summary,
        "breakeven": {
            "n_formulas": len(rows),
            "n_never_breaks_even_vs_cse": len(never_be),
            "never_breaks_even_ids": never_be,
            "breakeven_evals_median": statistics.median(be_values) if be_values else None,
        },
    }
    targets["results"].write_text(json.dumps(results, indent=2), encoding="utf-8")

    with targets["summary"].open("w", newline="", encoding="utf-8") as fh:
        fields = ["schedule", "group", "n_formulas", "geomean", "median",
                  "ci95_lo", "ci95_hi", "bootstrap", "sigma_log", "df",
                  "n_distinct_truth"]
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(blocked_summary + rr_summary)
    print(f"wrote {targets['results']}\nwrote {targets['summary']}")
    print(f"total wall time: {wall_s:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
