# Kickoff — Audit and Extend the 2026-08-01 Benchmark Gap Analysis

Project: Correspondence Matrices (CM), `C:\Users\brian\Documents\CM_Computation`.
Contact: Brian Theory (Droncheff). Repo at kickoff: `main` = `b6ce6b2`, clean apart from
untracked kickoff/analysis `.md` files.

## Mission

`CM_BENCHMARK_GAP_ANALYSIS_2026-08-01.md` claims that the project's published performance
numbers measure artifacts of the corpus rather than properties of CM, and that CM has a real
strength nobody has measured. Several of those claims are load-bearing enough that work will be
redirected on the strength of them.

Your job is **not** to agree. It is to:

1. **Adversarially audit** the eight findings (F1–F8), and
2. **Extend** the two that survive best, by actually measuring the things the analysis could
   only estimate.

A confirmed finding is a fine outcome. A **refuted** finding is a better one — it costs the
project less than acting on a wrong result. Treat "the analysis overreached here" as the
success case you are hunting for, and say so plainly when you find it.

Report your confidence separately from the original author's. Where you cannot resolve
something cheaply, say it is unresolved rather than picking a side.

## Read these

**Read fully:**

1. `CM_BENCHMARK_GAP_ANALYSIS_2026-08-01.md` — the document under audit. Parts 1 (findings
   F1–F8) and 2 (experiments E1–E10) are the audit target; Appendix A lists corrections the
   author already made to their own work, which tells you where they were already wrong once.

**Read the named sections only:**

2. `CM_AUDIT_V4_2026-07-24.md` — section C1 and "Interpretation". These are the claims the
   analysis says would not survive.
3. `CM_REMAINING_TESTS_AND_RESEARCH_PRIORITIES_2026-07-25.md` — Priorities 1, 6, 8, 9, 10. The
   analysis demotes all five; check whether its reasons hold.

**Do not re-read** the 2026-07-26 performance audit, the experiment A/B/C reports, or the ROBDD
reports end to end. The analysis already cites what it needs from them; verify the specific
citations rather than re-deriving their conclusions.

## What is already established — do not re-derive

These were verified this session and are not in dispute. Spend no time reconfirming them:

- The corpus has 31 distinct expressions across 49 records; `controlled_live_8/12/16` are one
  left-associated XOR chain each (`sha d5b65d38ee9c`, seed 0), re-bound into 7 ambient `n`.
- `v4audit_packed_eval_2026_07_24.py:103` computes `formulas` as `len({r["id"] for r in sel})`
  and ids embed the ambient-`n` token, so `formulas=7` counts bindings not functions.
- CM emits 1 flat op vs the baseline's 15 on AND/OR/XOR chains at k=16, and exactly 15 vs 15 on
  IMP/EQV (`cm_ir.py:31` `ASSOCIATIVE_OPS`).
- `CMIRBuilder.build` (`cm_ir.py:806-824`) has no memo; `_materialize_ir_tagged`
  (`cm_ir.py:1211`) does.
- `cudd_best10_order_search_us` is contaminated by in-band `validate_dd_bdd_correctness` with
  `correctness_samples=64` (`robdd_dd.py:398/420-428/447`).
- numba resolves cp313 wheels into `.venv`; `pysat` 1.8 is already installed there.
- Execution-order bias is dead (<1% pod, <5% local, from existing round-parity data).

## Audit targets, ordered by how much rests on them

### A1 — The compile-cost scaling claim (F3). Highest stakes.

**Claim:** CM's compile is Θ(tree unfolding), not Θ(DAG) and not a function of `live_k`; this
falsifies the cost model organizing every published number.

**Reported evidence:** 6×6 multiplier bit 7 = 152 DAG nodes / 43,251 tree nodes / 164.6 ms
compile / 97 resulting ops; compile ≈ 3.8 µs per tree node across a 17×→285× unfolding sweep.

**What to attack.** The scaling measurement looks clean, but the *inference* may not be. Check:

- Is the unfolding a property of CM's input format or of the author's generator? Every input
  reaching CM through the normal path is a tree (`cm_expr_serde.expr_to_json` is tree-recursive
  and has no ref/defs mechanism). If CM can never receive a DAG, then "CM's compile is
  tree-bound" may be a statement about the serde, not about `build`. Which is the real defect?
- Does high unfolding factor actually occur in workloads anyone cares about, or only in the
  author's hand-built multiplier? This was asserted, not demonstrated. A cheap literature or
  benchmark-format check (ISCAS/EPFL/AIGER shapes) settles it.
- The analysis claims an id-keyed memo does **not** fix it, because `_interned` keys are deep
  nested tuples re-hashed structurally (`cm_ir.py:796`). **Verify this by implementing the memo
  in a scratch copy and measuring.** This is the single most consequential unverified assertion
  in the document — the author is relaying another agent's probe, not their own measurement. If
  the memo *does* fix it, the finding drops from "P0 architectural defect" to "six-line patch"
  and E1's ranking collapses.

### A2 — The 128× multiplier result (Headline, F2)

**Claim:** on high-sharing input CM is two orders of magnitude faster than the published
baseline, and the corpus contains nothing that could reveal it.

**What to attack.**

- The multiplier AST was built by the author's own generator. Build the same function a
  different way (different adder topology, different output bit, a published netlist) and see
  whether the 240× op compression is a property of the *function* or of that construction.
- Is 26,157 ops a fair baseline or a pathological input? `compile_expr_flat` has no memo, so it
  re-expands every shared subtree. Ask whether any real consumer would ever hand it that AST.
- The timings are one local Windows box, min-of-5 blocks of 200. The op counts are deterministic
  and machine-independent; the 128× is indicative only. Re-measure if you want to cite it.

### A3 — The variance and sample-size numbers (F1)

**Two independent estimates disagree** and the document uses the smaller one:

- author's pooled within-`live_k` between-formula σ(log ratio): **0.0935**, df=10
- an agent's `live_k`-centred pooled estimate: **0.065** (pod) / 0.084 (local)

Sample-size requirements swing from 17 to 77 formulas across the plausible σ range, so this is
not cosmetic. Recompute both from `CM_v4audit_packed_eval_raw{,_runpod}.csv`, decide which
estimator is right, and give a defensible interval on σ itself. All of it comes from
`sparse_depth4` — the only family with >1 distinct formula per cell — so also state whether
σ estimated on depth-≤4 mixed-operator formulas transfers to XOR chains at all.

### A4 — The pod/local mechanism story (F4). Known hole.

**Claim:** the pod is 4–5× faster than local for BitSet at small `live_k` but only ~2× for CM,
so the ratio is a platform artifact converging only at `live_k`=16.

**The hole the author flagged but did not close:** the local run used **mixed repeat counts**
(`repeat` ∈ {50, 200}; `live_k`=16 used 50, `live_k`=6/7/8 are mixed) while the pod used 200
uniformly. Timing loops with different repeat counts have different warm-up and cache behaviour.
Quantify whether the repeat difference explains any of the 1.390 geometric-mean gap or the 11
sign flips. If it does, F4's mechanism story weakens and E8's replication gate matters more.

### A5 — The BDD category-error argument (F7)

**Claim:** inside `live_k`≤16, BDD blowup is provably impossible because max ROBDD is
`(1+o(1))·2ⁿ/n`, so BDD-hard families cannot be a CM-favourable regime.

**What to attack.** The bound is correct but it is a worst case *over all functions*; the real
work is done by the practical claim that CUDD handles a few thousand nodes in milliseconds. Check
whether the argument survives when the comparison is a *pipeline* (build + downstream ops) rather
than build alone, and whether "CM's 2^k grows faster than the BDD's on multipliers" holds across
output bits or only the middle one.

### A6 — Cheap citation checks

Verify these actually say what the document claims, and flag any that do not:
`cm_ir.py:31`, `cm_ir.py:796`, `cm_ir.py:806-824`, `cm_ir.py:968-993`, `cm_ir.py:1211`,
`cm_ir.py:1589-1670`, `bitset_backend.py:248-277`, `bitset_backend.py:465-494`,
`bitset_backend.py:562-563`, `robdd_dd.py:398/420-428/447`,
`v4audit_packed_eval_2026_07_24.py:44-50/54-56/60-63/76-82/103`,
`v4audit_query_workloads_2026_07_24.py:69`, `cm_runpod_deploy.py:170-182`,
`CM_flat_liveness_wrapper_paired_summary.csv` columns, `CM_ir_cost_report.md` §3–4.

The document's Appendix A already retracts one finding (output-budget calibration) because a
probe omitted `operation_slots`. Assume there is another mistake of that kind and go find it.

## Extension work, once the audit is done

Do these only after reporting audit results. **E1's measurement half is the highest-value day
available and needs no pod and no fix:**

1. **Compile-vs-unfolding scaling law.** Extend the author's 9-point sweep into a proper curve
   across circuit families and unfolding factors 1→1000×, with compile and materialize timed
   separately. Report whether compile is linear, super-linear, or has a knee. Include the
   memo-patched arm from A1.
2. **The CSE ladder pilot (E2).** Even a 2-rung version — baseline vs baseline+hash-consing — on
   20 formulas answers the thesis question well enough to rank the full experiment. Both arms
   must return the identical bigint, asserted before timing. Primary arm must be
   kernel-vs-kernel (`eval_cm_node_words` vs `eval_expr_words_bitset`), **not**
   `materialize_hybrid_no_reinflate`, which is an output-admission API.
3. **E4 (amortization) and E5 (schedule)** if time remains — both are ~40 min, need no new
   tracked code, and both attack already-published numbers.

If your audit refutes A1 or A2, **stop and re-rank before extending.** The extension list above
assumes those findings hold.

## Reproduction

Scratch scripts from the original session are in a session-specific temp directory that may have
been cleaned; assume you must rewrite them. The two probes worth reproducing first:

```bash
.\.venv\Scripts\python.exe -c "import sys;sys.path.insert(0,'.');from cm_expr_serde import expr_from_json;from cm_ir import compile_expr_to_cm_ir;from bitset_backend import compile_expr_flat,get_flat_program;V=lambda i:{'op':'var','i':i};B=lambda o,a,b:{'op':o,'a':a,'b':b};e=expr_from_json(B('xor',B('xor',V(0),V(1)),V(2)));n=compile_expr_to_cm_ir(e);print('CM ops',len(get_flat_program(n).ops),'BS ops',len(compile_expr_flat(e).ops))"
```

For the multiplier probe, build an `nb`×`nb` array multiplier as nested `{'op':..,'a':..,'b':..}`
dicts, take output bit `nb-1`, and compare `len(get_flat_program(compile_expr_to_cm_ir(e)).ops)`
against `len(compile_expr_flat(e).ops)`. Assert
`int(eval_cm_node_words(node, support, fixed={})) == int(eval_expr_words_bitset(e, support, fixed={}))`
before timing anything.

## Deliverable

`CM_GAP_AUDIT_2026-08-0X.md` at repo root. For each of A1–A6:

- **verdict**: CONFIRMED / CONFIRMED-WITH-CORRECTION / REFUTED / UNRESOLVED
- the evidence you ran or read, with file:line or command
- if corrected or refuted: what the right statement is, and which E-rank changes as a result

Close with: a re-ranked E1–E10, and an explicit list of anything in the gap analysis that should
**not** be relied on until further work.

## Ground rules

- Benchmarks use `.\.venv\Scripts\python.exe` (3.13.5); tests use system Python (3.10.11).
- Cheap scouting and scratch implementations are fine. **Do not launch campaigns.** No pods
  without Brian's approval — none of the audit work above needs one.
- Never edit prior reports (`CM_AUDIT_*`, `CM_SESSION_*`, `CM_BENCHMARK_GAP_ANALYSIS_*`,
  Fable/third-party docs) and never overwrite historical CSVs. New artifacts go in
  `deliverables_n22_24\` with a distinctive name.
- Any memo/patch you write to test A1 goes in a **scratch copy**, not in `cm_ir.py`. Library
  defaults must not change.
- Do not print or commit secrets; `.env.runpod*` is off limits.
- Leave the worktree clean. Do not push, do not commit.
- A reasoned "this finding is wrong and here is why" is the most valuable thing you can produce.
  Do not pad the audit to make all six come out confirmed.
