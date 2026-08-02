"""EPFL/AIGER external-corpus extractor + campaign driver (2026-08-03).

Executes CM_GAP_EPFL_PROTOCOL_2026-08-03.md as pre-registered. Stages:

  --stage provenance   write the clone/file provenance manifest
  --stage extract      parse .aig files, select cones, write frozen corpus
  --stage pilot        measure the pilot subset (first qualifying circuit per
                       category, per-circuit cap 4)
  --stage campaign     measure the full corpus
  --stage analyze      circuit-clustered analysis from raw rows

Parser: binary AIGER (aig M I L O A, delta-encoded AND list per AIGER 1.9)
and ASCII AIGER (aag) for test fixtures. Combinational only (L must be 0).
Conversion: one expression node per AIG node, And/Not only, AIG sharing
preserved, no rewriting. cm_exprlib has no constant node; a cone referencing
AIG constant literals (0/1) is recorded ``skipped_constant_literal`` — if any
otherwise-qualifying cone is dropped for this reason the run STOPS per the
protocol's defect rule (none is expected in EPFL combinational circuits).

Cone eligibility (protocol section 3): syntactic support <= 16; semantic
support 8..16 measured on the complete packed truth function by an
independent bigint evaluator over the cone (no cm_ir, no bitset_backend);
<= 5000 AIG AND nodes; raw ablation only under 60,000 unfolded occurrences
(otherwise admitted with raw_arm_skipped_unfolded_cap); constants/degenerate
recorded and skipped. Dedup by (structural hash, truth SHA-256), processing
order, first wins. Per-circuit cap 8: qualifying PO cones by output index,
then qualifying internal cones at evenly spaced ranks floor(j*(Q-1)/(m-1)).

Measurement: corrected-E3 harness class — arms cm / cse / cse_flat / raw,
bare _eval_words kernels, packed equality across all arms + wrapper before
timing, truth SHA re-verified; blocked (4 rounds, adaptive repeats as in the
corrected driver) and round-robin (60 passes) reported separately. Runtime
guards: prep > 10 s or blocked round > 5 s => skipped_runtime_guard with
partial data. Outputs refuse-overwrite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(1_000_000)

import numpy as np

from bitset_backend import (
    _eval_words,
    compile_expr_cse,
    compile_expr_flat,
    compile_flat,
    get_flat_program,
    program_metrics,
)
from cm_expr_serde import expr_from_json, expr_to_json_dag
from cm_exprlib import And, Not, Var
from cm_ir import compile_expr_to_cm_ir, expr_structural_hash, materialize_hybrid_no_reinflate

CLONE = ROOT / "external" / "epfl-benchmarks"
CATEGORIES = ("arithmetic", "random_control")
DATE = "2026_08_03"
OUT = ROOT / "deliverables_n22_24"
RUN_DIR = OUT / f"epfl_run_{DATE}"
CORPUS_PATH = OUT / f"CM_gap_epfl_corpus_{DATE}.jsonl"
PROVENANCE_PATH = OUT / f"cm_gap_epfl_provenance_{DATE}.json"
RESULTS_PATH = OUT / f"cm_gap_epfl_results_{DATE}.json"
PILOT_RESULTS_PATH = RUN_DIR / f"cm_gap_epfl_pilot_results_{DATE}.json"
SUMMARY_PATH = OUT / f"CM_gap_epfl_summary_{DATE}.csv"

SYNT_CAP = 16
SEM_LO, SEM_HI = 8, 16
AND_CAP = 5000
RAW_UNFOLDED_CAP = 60_000
PER_CIRCUIT_CAP = 8
PILOT_CAP = 4
ROUNDS = 4
RR_PASSES = 60
BOOT_DRAWS = 4000
BOOT_SEED = 20260803
PREP_GUARD_S = 10.0
ROUND_GUARD_S = 5.0


# ---------------------------------------------------------------- parsing --

def _decode_varint(buf, pos):
    x, shift = 0, 0
    while True:
        b = buf[pos]; pos += 1
        x |= (b & 0x7F) << shift
        if not (b & 0x80):
            return x, pos
        shift += 7


def parse_aig(path: Path):
    """Parse binary (.aig) or ASCII (.aag) AIGER. Returns dict or raises."""
    data = path.read_bytes()
    nl = data.index(b"\n")
    header = data[:nl].decode("ascii").split()
    fmt = header[0]
    if fmt not in ("aig", "aag") or len(header) < 6:
        raise ValueError(f"not an AIGER file: {path}")
    M, I, L, O, A = (int(x) for x in header[1:6])
    if L != 0:
        raise ValueError(f"latch-bearing file (L={L}): {path.name}")
    pos = nl + 1
    outputs = []
    ands = []
    if fmt == "aig":
        # inputs implicit; O output literal lines, then A delta-coded ANDs
        for _ in range(O):
            nl2 = data.index(b"\n", pos)
            outputs.append(int(data[pos:nl2]))
            pos = nl2 + 1
        for i in range(A):
            lhs = 2 * (I + L + i + 1)
            d0, pos = _decode_varint(data, pos)
            d1, pos = _decode_varint(data, pos)
            rhs0 = lhs - d0
            rhs1 = rhs0 - d1
            if rhs0 < 0 or rhs1 < 0 or rhs0 >= lhs:
                raise ValueError(f"malformed delta at AND {i}: {path.name}")
            ands.append((lhs, rhs0, rhs1))
    else:
        text = data.decode("ascii").splitlines()
        lines = text[0:]  # header already parsed as line 0
        idx = 1
        inputs = []
        for _ in range(I):
            inputs.append(int(lines[idx].split()[0])); idx += 1
        for _ in range(O):
            outputs.append(int(lines[idx].split()[0])); idx += 1
        for _ in range(A):
            parts = lines[idx].split(); idx += 1
            ands.append((int(parts[0]), int(parts[1]), int(parts[2])))
        if inputs != [2 * (i + 1) for i in range(I)]:
            raise ValueError(f"non-canonical aag input numbering: {path.name}")
    return {"M": M, "I": I, "L": L, "O": O, "A": A,
            "outputs": outputs, "ands": ands, "format": fmt}


# ------------------------------------------------------- cone machinery --

def build_tables(aig):
    """Per-node child table and capped support sets.

    Node index = literal >> 1. Inputs are 1..I; ANDs are I+1..I+A in
    topological order (AIGER guarantees rhs < lhs in binary format).
    support[node] = frozenset of input indices (0-based) or None if > cap.
    n_ands_in_cone computed per candidate lazily.
    """
    I, ands = aig["I"], aig["ands"]
    n_nodes = I + len(ands) + 1
    child = [None] * n_nodes
    support = [None] * n_nodes
    support[0] = frozenset()          # constant node
    for i in range(1, I + 1):
        support[i] = frozenset((i - 1,))
    for lhs, r0, r1 in ands:
        v = lhs >> 1
        child[v] = (r0, r1)
        s0, s1 = support[r0 >> 1], support[r1 >> 1]
        if s0 is None or s1 is None:
            support[v] = None
        else:
            u = s0 | s1
            support[v] = u if len(u) <= SYNT_CAP else None
    return child, support


def cone_stats(root_var, child):
    """Iterative cone walk: (n_ands, uses_constant, node_list_topo)."""
    seen = set()
    stack = [root_var]
    n_ands = 0
    uses_const = False
    order = []
    while stack:
        v = stack.pop()
        if v in seen:
            continue
        seen.add(v)
        if v == 0:
            uses_const = True
            continue
        if child[v] is not None:
            n_ands += 1
            order.append(v)
            stack.append(child[v][0] >> 1)
            stack.append(child[v][1] >> 1)
    return n_ands, uses_const, seen


def cone_truth_bigint(root_lit, child, support_vars):
    """Independent packed truth function of the cone over its support.

    Pure-python bigint evaluation, standard variable order: support_vars[j]
    (sorted input indices) toggles with period 2^(j+1). No cm_ir, no
    bitset_backend.
    """
    s = len(support_vars)
    nbits = 1 << s
    full = (1 << nbits) - 1
    col = {}
    for j, inp in enumerate(support_vars):
        block = ((1 << (1 << j)) - 1) << (1 << j)
        pat = 0
        period = 1 << (j + 1)
        for start in range(0, nbits, period):
            pat |= block << start
        col[inp] = pat
    memo = {}

    def val(lit):
        v = lit >> 1
        neg = lit & 1
        if v in memo:
            r = memo[v]
        else:
            if v == 0:
                r = 0
            elif child[v] is None:
                r = col[v - 1]
            else:
                r0, r1 = child[v]
                r = val(r0) & val(r1)
            memo[v] = r
        return (full ^ r) if neg else r

    # iterative topo evaluation to avoid recursion on deep cones
    stack = [root_lit >> 1]
    post = []
    seen = set()
    while stack:
        v = stack.pop()
        if v in seen or v in memo:
            continue
        seen.add(v)
        if v == 0 or child[v] is None:
            memo[v] = 0 if v == 0 else col[v - 1]
            continue
        r0, r1 = child[v]
        need = [u for u in (r0 >> 1, r1 >> 1) if u not in memo]
        if need:
            stack.append(v)
            stack.extend(need)
            seen.discard(v)
        else:
            a = memo[r0 >> 1] ^ (full if r0 & 1 else 0)
            b = memo[r1 >> 1] ^ (full if r1 & 1 else 0)
            memo[v] = a & b
    return val(root_lit), full


def semantic_support(bits, support_vars):
    s = len(support_vars)
    arr = np.frombuffer(
        int(bits).to_bytes(max(1, (1 << s) // 8), "little"), dtype=np.uint8)
    arr = np.unpackbits(arr, bitorder="little")[: 1 << s].astype(bool)
    cube = arr.reshape((2,) * s, order="F")   # axis j = support_vars[j]
    return [support_vars[ax] for ax in range(s)
            if not np.array_equal(np.take(cube, 0, axis=ax),
                                  np.take(cube, 1, axis=ax))]


def cone_to_expr(root_lit, child, var_index_of_input):
    """One expression node per AIG node; Not for inverted edges; no rewriting."""
    node_memo = {}

    def build(v):
        if child[v] is None:
            return Var(var_index_of_input[v - 1])
        r0, r1 = child[v]
        a = edge(r0); b = edge(r1)
        return And(a, b)

    not_memo = {}

    def edge(lit):
        v = lit >> 1
        e = node_memo[v]
        if lit & 1:
            ne = not_memo.get(v)
            if ne is None:
                ne = not_memo[v] = Not(e)
            return ne
        return e

    # iterative postorder
    stack = [root_lit >> 1]
    seen = set()
    while stack:
        v = stack.pop()
        if v in node_memo:
            continue
        if child[v] is None:
            node_memo[v] = build(v)
            continue
        r0, r1 = child[v]
        need = [u for u in (r0 >> 1, r1 >> 1) if u not in node_memo]
        if need:
            stack.append(v)
            stack.extend(need)
        else:
            node_memo[v] = build(v)
    return edge(root_lit)


# ------------------------------------------------------------ selection --

def select_circuit_cones(path: Path, category: str, per_circuit_cap: int, log):
    rejects = Counter()
    try:
        aig = parse_aig(path)
    except ValueError as exc:
        return [], {"file": path.name, "category": category,
                    "status": "skipped_file", "reason": str(exc)}
    child, support = build_tables(aig)

    def qualify(root_lit, kind, index):
        v = root_lit >> 1
        if v == 0 or child[v] is None and v > aig["I"]:
            rejects["constant_or_invalid_root"] += 1
            return None
        if child[v] is None:
            rejects["input_root"] += 1
            return None
        sup = support[v]
        if sup is None:
            rejects["synt_support_gt16"] += 1
            return None
        n_ands, uses_const, _seen = cone_stats(v, child)
        if uses_const:
            rejects["constant_literal"] += 1
            return {"__constant_literal__": True}
        if n_ands > AND_CAP:
            rejects["skipped_structural_cap"] += 1
            return None
        sup_sorted = sorted(sup)
        bits, full = cone_truth_bigint(root_lit, child, sup_sorted)
        if bits == 0 or bits == full:
            rejects["constant_function"] += 1
            return None
        sem = semantic_support(bits, sup_sorted)
        if not (SEM_LO <= len(sem) <= SEM_HI):
            rejects["semantic_support_out_of_range"] += 1
            return None
        return {"root_lit": root_lit, "kind": kind, "index": index,
                "synt_support": sup_sorted, "sem_support": sem,
                "n_ands": n_ands, "bits": bits}

    qualified_po = []
    constant_literal_hit = False
    for oi, out_lit in enumerate(aig["outputs"]):
        q = qualify(out_lit, "po", oi)
        if q and q.get("__constant_literal__"):
            constant_literal_hit = True
        elif q:
            qualified_po.append(q)
    selected = qualified_po[:per_circuit_cap]
    m = per_circuit_cap - len(selected)
    n_internal_qualifying = 0
    if m > 0:
        qualified_internal = []
        for i, (lhs, _r0, _r1) in enumerate(aig["ands"]):
            q = qualify(lhs, "internal", i)
            if q and q.get("__constant_literal__"):
                constant_literal_hit = True
            elif q:
                qualified_internal.append(q)
        Q = len(qualified_internal)
        n_internal_qualifying = Q
        if Q:
            if m == 1 or Q == 1:
                idxs = [0]
            else:
                idxs = sorted({(j * (Q - 1)) // (min(m, Q) - 1)
                               for j in range(min(m, Q))})
            selected += [qualified_internal[i] for i in idxs]
    info = {"file": path.name, "category": category, "status": "ok",
            "I": aig["I"], "A": aig["A"], "O": aig["O"],
            "n_po_qualifying": len(qualified_po),
            "n_internal_qualifying": n_internal_qualifying,
            "constant_literal_encountered": constant_literal_hit,
            "rejection_histogram": dict(rejects)}
    log(f"  {category}/{path.name}: {len(selected)} selected "
        f"(po_q={len(qualified_po)}, int_q={n_internal_qualifying}) "
        f"rejects={dict(rejects)}")
    return selected, info


def extract(per_circuit_cap=PER_CIRCUIT_CAP, log=print):
    records, circuit_infos = [], []
    seen_keys = {}
    for category in sorted(CATEGORIES):
        cat_dir = CLONE / category
        for path in sorted(cat_dir.glob("*.aig"), key=lambda p: p.name):
            file_sha = hashlib.sha256(path.read_bytes()).hexdigest()
            selected, info = select_circuit_cones(path, category, per_circuit_cap, log)
            info["sha256"] = file_sha
            circuit_infos.append(info)
            if info["status"] != "ok":
                continue
            aig = parse_aig(path)
            child, _support = build_tables(aig)
            for q in selected:
                var_index_of_input = {inp: j for j, inp in enumerate(q["synt_support"])}
                expr = cone_to_expr(q["root_lit"], child, var_index_of_input)
                h = expr_structural_hash(expr)
                s = len(q["synt_support"])
                truth_sha = hashlib.sha256(
                    int(q["bits"]).to_bytes(max(1, (1 << s) // 8), "little")).hexdigest()
                key = (h, truth_sha)
                cid = (f"epfl-{category}-{path.stem}-{q['kind']}{q['index']}-{h[:10]}")
                if key in seen_keys:
                    records.append({"id": cid, "status": "skipped_duplicate",
                                    "duplicate_of": seen_keys[key],
                                    "circuit": path.name, "category": category})
                    continue
                seen_keys[key] = cid
                # unfolded occurrences via multiplicity propagation on the expr
                import importlib.util as _ilu
                unf = _tree_unfolded(expr)
                records.append({
                    "id": cid, "status": "admitted",
                    "category": category, "circuit": path.name,
                    "circuit_sha256": file_sha,
                    "root_kind": q["kind"], "root_index": q["index"],
                    "root_literal": q["root_lit"],
                    "n_aig_ands": q["n_ands"],
                    "synt_support_inputs": q["synt_support"],
                    "synt_support_size": s,
                    "sem_support_inputs": q["sem_support"],
                    "sem_support_size": len(q["sem_support"]),
                    "structural_hash": h, "truth_sha256": truth_sha,
                    "unfolded_occurrences": unf,
                    "raw_arm": ("ok" if unf <= RAW_UNFOLDED_CAP
                                else "raw_arm_skipped_unfolded_cap"),
                    "expression_v2": expr_to_json_dag(expr),
                })
    return records, circuit_infos


def _tree_unfolded(expr):
    """Exact unfolded occurrence count by multiplicity propagation."""
    uid_by_id, spec = {}, []
    intern = {}
    stack = [(expr, False)]
    scheduled = set()
    while stack:
        e, processed = stack.pop()
        if processed:
            if isinstance(e, Var):
                skey = ("v", int(e.i)); children = ()
            elif isinstance(e, Not):
                children = (uid_by_id[id(e.a)],); skey = ("n",) + children
            else:
                children = (uid_by_id[id(e.a)], uid_by_id[id(e.b)])
                skey = (type(e).__name__,) + children
            uid = intern.get(skey)
            if uid is None:
                uid = intern[skey] = len(spec)
                spec.append(children)
            uid_by_id[id(e)] = uid
            continue
        if id(e) in scheduled:
            continue
        scheduled.add(id(e))
        stack.append((e, True))
        if isinstance(e, Not):
            stack.append((e.a, False))
        elif not isinstance(e, Var):
            stack.append((e.b, False)); stack.append((e.a, False))
    occ = [0] * len(spec)
    occ[uid_by_id[id(expr)]] = 1
    for uid in range(len(spec) - 1, -1, -1):
        if occ[uid]:
            for c in spec[uid]:
                occ[c] += occ[uid]
    return sum(occ)


# ----------------------------------------------------------- measurement --

def timed(fn, repeats=1, blocks=3):
    best = float("inf")
    for _ in range(blocks):
        t0 = time.perf_counter()
        for _ in range(repeats):
            fn()
        best = min(best, (time.perf_counter() - t0) / repeats)
    return best


def measure_record(rec):
    expr = expr_from_json(rec["expression_v2"])
    s = rec["synt_support_size"]
    # vars_key[0] packs as the MSB axis in _eval_words; the corpus truth SHA
    # uses LSB-first variable order (cone_truth_bigint), so reverse the key.
    support = tuple(f"x{i}" for i in range(s - 1, -1, -1))
    row = {k: rec[k] for k in ("id", "category", "circuit", "root_kind",
                               "sem_support_size", "synt_support_size",
                               "structural_hash", "truth_sha256",
                               "n_aig_ands", "unfolded_occurrences", "raw_arm")}
    t0 = time.perf_counter()
    node = compile_expr_to_cm_ir(expr)
    cm_prep_first_s = time.perf_counter() - t0
    if cm_prep_first_s > PREP_GUARD_S:
        row["status"] = "skipped_runtime_guard"
        row["guard_reason"] = f"cm first prep {cm_prep_first_s:.1f}s"
        return row
    progs = {"cm": get_flat_program(node), "cse": compile_expr_cse(expr),
             "cse_flat": compile_expr_cse(expr, flatten=True)}
    if rec["raw_arm"] == "ok":
        progs["raw"] = compile_expr_flat(expr)
    vals = {a: _eval_words(p, support, {}) for a, p in progs.items()}
    if len(set(vals.values())) != 1:
        raise AssertionError(f"packed mismatch: {rec['id']}")
    ref = vals["cm"]
    sha = hashlib.sha256(
        int(ref).to_bytes(max(1, (1 << s) // 8), "little")).hexdigest()
    if sha != rec["truth_sha256"]:
        raise AssertionError(f"truth drift vs corpus: {rec['id']}")
    wrapped = materialize_hybrid_no_reinflate(
        node, support, fixed={}, hybrid_threshold=16, allow_reduced_output=False,
        max_full_output_vars=16, flat_eval=True, words_eval=True)
    if int(wrapped.bits) != ref:
        raise AssertionError(f"wrapper mismatch: {rec['id']}")
    row["packed_equal_all_arms"] = True

    for a, p in progs.items():
        m = program_metrics(p)
        row[f"{a}_flat_instructions"] = m["flat_instructions"]
        row[f"{a}_executed_word_ops"] = m["executed_word_ops"]
        row[f"{a}_loads"] = m["loads"]
        row[f"{a}_peak_live_word_buffers"] = m["peak_live_word_buffers"]

    row["cm_prep_us"] = timed(lambda: compile_expr_to_cm_ir(expr)) * 1e6
    row["cse_prep_us"] = timed(lambda: compile_expr_cse(expr)) * 1e6
    row["cse_flat_prep_us"] = timed(
        lambda: compile_expr_cse(expr, flatten=True)) * 1e6
    row["prep_ratio_cm_vs_cse"] = row["cm_prep_us"] / row["cse_prep_us"]
    row["prep_ratio_cm_vs_cse_flat"] = row["cm_prep_us"] / row["cse_flat_prep_us"]

    repeats = max(20, min(200, 20_000 // max(1, len(progs["cm"].ops))))
    row["kernel_repeats"] = repeats
    times = {a: [] for a in ("cm", "cse", "cse_flat")}
    for rnd in range(ROUNDS):
        order = ("cm", "cse", "cse_flat") if rnd % 2 else ("cse_flat", "cse", "cm")
        t_round = time.perf_counter()
        for a in order:
            times[a].append(timed(lambda a=a: _eval_words(progs[a], support, {}),
                                  repeats, blocks=1))
        if time.perf_counter() - t_round > ROUND_GUARD_S:
            row["status"] = "skipped_runtime_guard"
            row["guard_reason"] = "blocked round > 5s"
            return row
    for a in times:
        row[f"{a}_kernel_us"] = statistics.median(times[a]) * 1e6
    if "raw" in progs and len(progs["raw"].ops) <= 20_000:
        reps = max(3, min(repeats, 20_000 // max(1, len(progs["raw"].ops))))
        row["raw_kernel_us"] = timed(
            lambda: _eval_words(progs["raw"], support, {}), reps) * 1e6
    row["blocked_ratio_cm_cse"] = row["cm_kernel_us"] / row["cse_kernel_us"]
    row["blocked_ratio_cm_cse_flat"] = row["cm_kernel_us"] / row["cse_flat_kernel_us"]

    for base in ("cse", "cse_flat"):
        prep_gap = row["cm_prep_us"] - row[f"{base}_prep_us"]
        eval_gain = row[f"{base}_kernel_us"] - row["cm_kernel_us"]
        be = ((0 if prep_gap <= 0 else math.ceil(prep_gap / eval_gain))
              if eval_gain > 0 else None)
        row[f"breakeven_evals_vs_{base}"] = be
        row[f"never_breaks_even_vs_{base}"] = be is None
    row["status"] = "ok"
    return row


def measure_round_robin(prepared, rr_passes):
    tot_cm = defaultdict(float); tot_flat = defaultdict(float)
    for p in range(rr_passes):
        for rid, support, progs in prepared:
            if p % 2:
                t0 = time.perf_counter(); _eval_words(progs["cm"], support, {})
                t1 = time.perf_counter(); _eval_words(progs["cse_flat"], support, {})
                t2 = time.perf_counter()
                tot_cm[rid] += t1 - t0; tot_flat[rid] += t2 - t1
            else:
                t0 = time.perf_counter(); _eval_words(progs["cse_flat"], support, {})
                t1 = time.perf_counter(); _eval_words(progs["cm"], support, {})
                t2 = time.perf_counter()
                tot_flat[rid] += t1 - t0; tot_cm[rid] += t2 - t1
    return {rid: tot_cm[rid] / tot_flat[rid] for rid, _, _ in prepared}


def run_measurement(records, out_path, log=print):
    admitted = [r for r in records if r["status"] == "admitted"]
    rows = []
    prepared = []
    t0 = time.perf_counter()
    for i, rec in enumerate(admitted):
        row = measure_record(rec)
        rows.append(row)
        if row.get("status") == "ok":
            expr = expr_from_json(rec["expression_v2"])
            support = tuple(f"x{i}" for i in
                            range(rec["synt_support_size"] - 1, -1, -1))
            prepared.append((rec["id"], support,
                             {"cm": get_flat_program(compile_expr_to_cm_ir(expr)),
                              "cse_flat": compile_expr_cse(expr, flatten=True)}))
        if (i + 1) % 20 == 0:
            log(f"  measured {i + 1}/{len(admitted)}")
    rr = measure_round_robin(prepared, RR_PASSES)
    for row in rows:
        if row["id"] in rr:
            row["rr_ratio_cm_cse_flat"] = rr[row["id"]]
    try:
        git_rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.strip()
    except Exception:
        git_rev = "unknown"
    results = {
        "_meta": {
            "driver": Path(__file__).name,
            "protocol": "CM_GAP_EPFL_PROTOCOL_2026-08-03.md (frozen)",
            "python": sys.version, "numpy": np.__version__,
            "cpu": platform.processor(), "platform": platform.platform(),
            "git_revision": git_rev,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "wall_time_s": time.perf_counter() - t0,
            "corpus_sha256": hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest()
                             if CORPUS_PATH.exists() else None,
            "rounds": ROUNDS, "rr_passes": RR_PASSES,
            "primary_comparison": "cm vs cse_flat, blocked kernel ratios, "
                                  "circuit-clustered bootstrap",
            "cache_state": "warm process; blocked warm within formula; "
                           "round-robin cycling formulas; schedules never pooled",
            "runtime_guards": f"prep>{PREP_GUARD_S}s, round>{ROUND_GUARD_S}s",
        },
        "rows": rows,
    }
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite {out_path}")
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    log(f"wrote {out_path} ({len(rows)} rows, wall {time.perf_counter() - t0:.1f}s)")
    return results


# -------------------------------------------------------------- analysis --

def cluster_bootstrap(rows, key, draws=BOOT_DRAWS, seed=BOOT_SEED):
    import random as _r
    rng = _r.Random(seed)
    by_circuit = defaultdict(list)
    for r in rows:
        by_circuit[r["circuit"]].append(math.log(r[key]))
    circuits = sorted(by_circuit)
    point = math.exp(statistics.mean(
        [v for c in circuits for v in by_circuit[c]]))
    means = []
    for _ in range(draws):
        sample = []
        for _ in range(len(circuits)):
            sample.extend(by_circuit[circuits[rng.randrange(len(circuits))]])
        means.append(statistics.mean(sample))
    means.sort()
    lo = math.exp(np.percentile(means, 2.5, method="linear"))
    hi = math.exp(np.percentile(means, 97.5, method="linear"))
    return point, lo, hi


def analyze(results, log=print):
    rows = [r for r in results["rows"] if r.get("status") == "ok"]
    out = {"n_ok": len(rows),
           "n_guard_skipped": sum(1 for r in results["rows"]
                                  if r.get("status") == "skipped_runtime_guard"),
           "n_circuits": len({r["circuit"] for r in rows})}
    for key, name in (("blocked_ratio_cm_cse_flat", "primary_blocked_cm_cse_flat"),
                      ("rr_ratio_cm_cse_flat", "round_robin_cm_cse_flat"),
                      ("blocked_ratio_cm_cse", "secondary_blocked_cm_cse")):
        sel = [r for r in rows if key in r]
        if sel:
            point, lo, hi = cluster_bootstrap(sel, key)
            out[name] = {"geomean": point, "ci95_lo": lo, "ci95_hi": hi,
                         "n": len(sel), "bootstrap": "circuit_clustered",
                         "draws": BOOT_DRAWS, "seed": BOOT_SEED}
    per_circuit = []
    by_c = defaultdict(list)
    for r in rows:
        by_c[r["circuit"]].append(r)
    for c, sel in sorted(by_c.items()):
        per_circuit.append({
            "circuit": c, "category": sel[0]["category"], "n_formulas": len(sel),
            "geomean_cm_cse_flat": math.exp(statistics.mean(
                math.log(r["blocked_ratio_cm_cse_flat"]) for r in sel)),
            "geomean_cm_cse": math.exp(statistics.mean(
                math.log(r["blocked_ratio_cm_cse"]) for r in sel)),
        })
    out["per_circuit"] = per_circuit
    buckets = {"8-10": (8, 10), "11-13": (11, 13), "14-16": (14, 16)}
    out["by_sem_bucket"] = {}
    for bname, (lo_b, hi_b) in buckets.items():
        sel = [r for r in rows if lo_b <= r["sem_support_size"] <= hi_b]
        if sel:
            out["by_sem_bucket"][bname] = {
                "n": len(sel),
                "geomean_cm_cse_flat": math.exp(statistics.mean(
                    math.log(r["blocked_ratio_cm_cse_flat"]) for r in sel))}
    ilogs = [math.log(r["cm_flat_instructions"] / r["cse_flat_flat_instructions"])
             for r in rows]
    klogs = [math.log(r["blocked_ratio_cm_cse_flat"]) for r in rows]
    if len(set(ilogs)) > 1:
        out["corr_log_instr_vs_log_kernel_cse_flat"] = float(
            np.corrcoef(ilogs, klogs)[0, 1])
    out["instr_ratio_cm_cse_flat_geomean"] = math.exp(statistics.mean(ilogs))
    op_logs = [math.log(r["cm_executed_word_ops"] / r["cse_flat_executed_word_ops"])
               for r in rows]
    out["execop_ratio_cm_cse_flat_geomean"] = math.exp(statistics.mean(op_logs))
    prep = [r["prep_ratio_cm_vs_cse_flat"] for r in rows]
    out["prep_multiple_cm_vs_cse_flat_geomean"] = math.exp(
        statistics.mean(math.log(x) for x in prep))
    be = [r["breakeven_evals_vs_cse_flat"] for r in rows
          if r["breakeven_evals_vs_cse_flat"] is not None]
    out["breakeven_vs_cse_flat"] = {
        "n_finite": len(be),
        "n_never": sum(1 for r in rows if r["never_breaks_even_vs_cse_flat"]),
        "median_finite": statistics.median(be) if be else None}
    # materiality rule (pre-registered)
    p = out.get("primary_blocked_cm_cse_flat", {})
    all_be = [r["breakeven_evals_vs_cse_flat"] for r in rows]
    med_be_all = (statistics.median([b for b in all_be if b is not None])
                  if be and len(be) * 2 > len(rows) else None)
    cond1 = p.get("geomean", 1.0) <= 0.95
    cond2 = p.get("ci95_hi", 1.0) < 1.0
    cond3 = (out["breakeven_vs_cse_flat"]["median_finite"] is not None
             and out["breakeven_vs_cse_flat"]["n_never"] * 2 <= len(rows)
             and statistics.median(
                 [b if b is not None else float("inf") for b in all_be]) <= 1000)
    out["materiality"] = {
        "cond1_geomean_le_0.95": cond1,
        "cond2_clustered_ci_excludes_parity": cond2,
        "cond3_median_breakeven_le_1000": bool(cond3),
        "optimization_worthy": bool(cond1 and cond2 and cond3),
    }
    return out


# ------------------------------------------------------------------ main --

def stage_provenance():
    if PROVENANCE_PATH.exists():
        raise SystemExit(f"refusing to overwrite {PROVENANCE_PATH}")
    clone_sha = subprocess.run(["git", "-C", str(CLONE), "rev-parse", "HEAD"],
                               capture_output=True, text=True).stdout.strip()
    lic = CLONE / "LICENSE"
    files = []
    for category in sorted(CATEGORIES):
        for path in sorted((CLONE / category).glob("*.aig"), key=lambda p: p.name):
            files.append({"relpath": f"{category}/{path.name}",
                          "category": category,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                          "bytes": path.stat().st_size})
    total = sum(p.stat().st_size for p in CLONE.rglob("*") if p.is_file())
    manifest = {
        "remote_url": "https://github.com/lsils/benchmarks.git",
        "clone_command": "git clone --depth 1 https://github.com/lsils/"
                         "benchmarks.git C:\\Users\\brian\\Documents\\"
                         "CM_Computation\\external\\epfl-benchmarks",
        "clone_commit_sha": clone_sha,
        "clone_date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "license_name": "MIT License",
        "license_sha256": hashlib.sha256(lic.read_bytes()).hexdigest(),
        "total_on_disk_bytes": total,
        "categories_consumed": list(CATEGORIES),
        "aig_files": files,
    }
    PROVENANCE_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {PROVENANCE_PATH} ({len(files)} .aig files)")


def stage_extract():
    if CORPUS_PATH.exists():
        raise SystemExit(f"refusing to overwrite {CORPUS_PATH}")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    records, circuit_infos = extract()
    # protocol defect stop-rule: constant-literal cones
    if any(ci.get("constant_literal_encountered") for ci in circuit_infos):
        sys.exit("STOP: qualifying cone referenced AIG constant literal — "
                 "protocol defect rule triggered; version a successor protocol")
    meta = {"record_type": "epfl_corpus_meta",
            "protocol": "CM_GAP_EPFL_PROTOCOL_2026-08-03.md",
            "per_circuit_cap": PER_CIRCUIT_CAP,
            "eligibility": {"synt_cap": SYNT_CAP, "sem_range": [SEM_LO, SEM_HI],
                            "and_cap": AND_CAP, "raw_unfolded_cap": RAW_UNFOLDED_CAP},
            "circuit_infos": circuit_infos}
    lines = [json.dumps(meta, sort_keys=True, separators=(",", ":"))]
    lines += [json.dumps(r, sort_keys=True, separators=(",", ":")) for r in records]
    CORPUS_PATH.write_bytes(("\n".join(lines) + "\n").encode())
    n_adm = sum(1 for r in records if r["status"] == "admitted")
    n_dup = sum(1 for r in records if r["status"] == "skipped_duplicate")
    print(f"wrote {CORPUS_PATH}: {n_adm} admitted, {n_dup} duplicates, "
          f"wall {time.perf_counter() - t0:.1f}s")
    print(f"corpus sha256: {hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest()}")


def load_corpus():
    lines = CORPUS_PATH.read_text(encoding="utf-8").splitlines()
    meta = json.loads(lines[0])
    records = [json.loads(l) for l in lines[1:] if l.strip()]
    return meta, records


def stage_pilot():
    meta, records = load_corpus()
    admitted = [r for r in records if r["status"] == "admitted"]
    pilot = []
    for category in sorted(CATEGORIES):
        cat = [r for r in admitted if r["category"] == category]
        by_circuit = defaultdict(list)
        for r in cat:
            by_circuit[r["circuit"]].append(r)
        for circuit in sorted(by_circuit):
            pilot.extend(by_circuit[circuit][:PILOT_CAP])
            break
    print(f"pilot: {len(pilot)} formulas from "
          f"{sorted({r['circuit'] for r in pilot})}")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    results = run_measurement(pilot, PILOT_RESULTS_PATH)
    n_admitted = len(admitted)
    est = results["_meta"]["wall_time_s"] * (n_admitted / max(1, len(pilot)))
    print(f"projected full-campaign wall: {est / 60:.1f} min "
          f"({n_admitted} admitted formulas)")
    if est > 3600:
        print("EXCEEDS 60-MINUTE GATE — stop and request re-scoping")


def stage_campaign():
    _meta, records = load_corpus()
    admitted = [r for r in records if r["status"] == "admitted"]
    results = run_measurement(admitted, RESULTS_PATH)
    summary = analyze(results)
    (RUN_DIR / f"cm_gap_epfl_analysis_{DATE}.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("per_circuit",)}, indent=2))


def stage_analyze():
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    summary = analyze(results)
    print(json.dumps(summary, indent=2))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["provenance", "extract", "pilot", "campaign", "analyze"])
    args = ap.parse_args(argv)
    {"provenance": stage_provenance, "extract": stage_extract,
     "pilot": stage_pilot, "campaign": stage_campaign,
     "analyze": stage_analyze}[args.stage]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
