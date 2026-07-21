# CM Feasibility: Architecture, What Changed, and Correctness Audit (n=16 → 24)

> **Purpose.** A self-contained, publication-grade audit answering three questions you raised:
> (1) Why couldn't runs above n=16 happen before, and what specifically changed?
> (2) How is it *possible* to "run n=24" on a normal machine — is it real or an artifact?
> (3) Are CM, bitset, and BDD (dd/CUDD) each being computed **correctly**?
>
> Everything here was measured this session on your machine. Correctness is checked
> **exhaustively** (every one of the 2^n rows) against an **independent** oracle, not by
> sampling and not by any method checking itself. Where an earlier report of mine was
> imprecise (the "ROBDD unavailable" line), this document corrects it explicitly — that is
> what an audit is for.

---

## 0. The one distinction that resolves the paradox

"Running n=24" means two completely different things, and conflating them is the single
biggest risk to a correct write-up:

- **CM reduced-output path (`materialize_hybrid_no_reinflate`).** It **never builds a
  2^24 object.** It emits a *reduced* result over only the `live_k` variables the function
  actually depends on, capped by the guard at `live_k ≤ 16` (≤ 2^16 = 65,536 entries).
  Its cost tracks `live_k`, **not** `n`. So "CM at n=24" is really "an expression living in
  a 24-variable namespace but touching ≤ 16 of them." This was *always* structurally
  feasible; it is the whole point of the structure-preserving compiler.

- **The full-output methods (raw bitset, and the `eval_expr_tt` oracle).** These *do*
  build the full 2^n object. But 2^24 is only **16 M entries** — 16 MB as a `uint8` truth
  vector, or 2 MB as a packed bitset. That is *small* data. With numpy vectorization each
  whole-function operation over it is tens of milliseconds. This too was always feasible in
  principle; what made it *impractical* before was a since-fixed setup cost (§2), not the
  data size.

So neither "n=24" is doing 2^24 units of hard work in the way the phrase suggests. CM does
≤ 2^16; the flat methods do 2^24 of *cheap, vectorized* work. Nothing here is too good to be
true — but the reasons are specific and are documented and re-measured below.

---

## 1. Environment & reproducibility (read this before trusting any number)

| Item | Value | Note |
|---|---|---|
| Benchmark interpreter | **Python 3.13.5** (`.venv\Scripts\python.exe`), numpy 2.3.2, dd 0.6.0 | **Not 3.10.11** as the session banner / older handoff claims — the venv was evidently upgraded. All timing/correctness numbers here are on 3.13.5. |
| Test interpreter | **Python 3.10.11** (system), pytest 9.0.2 | The venv has no pytest; the suite runs on system Python. Tests and benchmarks therefore run on *different* interpreters — a real caveat for publication. |
| Test result (this session, current tree) | **159 passed in 412.7 s** | Run now, not assumed. No library code was modified in this campaign. |
| Git commit | `1a984e4` (working tree clean of code changes) | Speedups landed earlier in `041fd18`. |
| CUDD (`dd.cudd`) | **Not importable on this machine** | `ModuleNotFoundError`; harness agrees (`robdd_cudd_available=False`). Any CUDD figures in the repo are from Docker/WSL, per handoff §7. |
| BDD backend that *did* run | **`dd.autoref`** (pure-Python) | Exposed by the harness under both its `robdd_*` and `dd_*` columns. |

**Recommendation for the paper:** either rebuild the `.venv` on the same Python you cite, or
state plainly that benchmarks ran on 3.13.5 and the test suite on 3.10.11.

---

## 2. Architecture *before*, and why n>16 was impractical

### 2.1 The pipeline (unchanged in shape)

```
Expr AST ──compile_expr_to_cm_ir──► CM IR DAG (interned, canonical)
                                        │
              materialize_hybrid_no_reinflate (threshold test on live_k)
                                        │
             live_k ≤ threshold ─► eval_cm_node_bitset ─► packed bitset (repr 2/3)
             live_k >  threshold ─► numpy IR materialize ─► TT vector   (repr 1/4)
```

Every bitset evaluation (`eval_cm_node_bitset`, and the raw-bitset baseline
`eval_expr_bitset`) first needs a **variable environment**: for each variable, a packed
2^n-bit mask giving that variable's column of the truth table. That is built by
`_build_bitset_env_cached(vars_key)` (`bitset_backend.py`).

### 2.2 The actual bottleneck: the env-build cliff

**Before** (commit `af23e8a`), `_build_bitset_env_cached` built each mask with a
**pure-Python big-integer loop** — for every variable it OR-ed `one_block << start` across
the whole 2^n range. That is O(n · 2^n) shifts on integers that are themselves 2^n bits
wide. It is fine at n≤16 and explodes past it. Re-measured on your machine this session
(`CM_env_build_cliff.csv`):

| n | old env-build (pre-R3) | new env-build (R3) | speedup | output identical? |
|--:|--:|--:|--:|:--:|
| 14 | 20 ms | 1.6 ms | 13× | ✅ |
| 16 | 120 ms | 5.2 ms | 23× | ✅ |
| 18 | **1.41 s** | 30.6 ms | 46× | ✅ |
| 20 | **20.6 s** | 140 ms | 147× | ✅ |
| 22 | **> 2 min (timed out)** | 577 ms | > 200× | (old not run to completion) |
| 24 | **> 2 min (timed out)** | 2.78 s | > 200× | (old not run to completion) |

This is the answer to "why couldn't I run above n=16." This env build sits on the hot path
of **every** bitset evaluation — the raw-bitset baseline *and* the CM path's bitset kernel
whenever the output scope is wide. At n=20 it cost **20 seconds per fresh variable set**; at
n=22/24 it ran for minutes. A benchmark that touches the full variable space at n≥18 was
effectively unusable. The data was never the problem; the **setup** was.

(The oracle `eval_expr_tt` was *already* vectorized and never part of this cliff — see §4.)

---

## 3. What changed (commit `041fd18`, "Phase 2: R1/R2/R3")

All five changes are **output-identical** — they change *when/how* a value is computed, not
the value. Verified byte-for-byte at the time and re-verified exhaustively here (§4).

| ID | File / symbol | Change | Effect |
|---|---|---|---|
| **R3** | `bitset_backend._build_bitset_env_cached` | Vectorized mask construction via `numpy.packbits` for n>10 (Python loop kept for n≤10). | **The feasibility enabler.** Kills the cliff in §2.2. Masks verified bit-identical to the old loop at n=14–20. |
| R1a | `cm_ir.CMNode.__hash__` | Cache the (identical) structural hash on the instance. | Memo/set lookups O(subtree) → O(1). Speedup, not enabling. |
| R1b | `bitset_backend.eval_cm_node_bitset` | Memo keyed by `id(node)` not the node. | O(1) memo. Correctness-safe: distinct-but-equal nodes cost a miss, never a wrong answer (they are usually the *same* interned object). |
| A4 | `cm_ir` no-reinflate + recursion | Skip `live_vars` rebuild when `fixed` is empty. | Speedup. |
| R2 | `cm_ir` persistent compiler | Share one blake2b digest memo across the build (was quadratic). | Faster cold compile; cache keys byte-identical. |

**Bottom line:** R3 is why n>16 became runnable. R1/R2/A4 make the compile-once/cached
regime 2–5× faster but do not change what is *feasible*. The CM reduced path itself needed
no change to be correct at large n — it was already `live_k`-bounded.

---

## 4. Correctness audit (exhaustive, independent)

### 4.1 Method

For each audited expression:

1. Compute the **independent oracle** `O = eval_expr_tt(expr, n)` — a numpy recursion over
   the *original* AST across all 2^n assignments (`cm_exprlib.py:80`). It shares no code with
   the CM IR or the bitset kernels, so it is a genuine external reference.
2. **CM reduced check (the important one).** Take the reduced no-reinflate result and expand
   it back to the full 2^n space by mapping every full row to its reduced index (MSB-first
   over `output_vars`) and gathering — then require `expanded == O` on **all 2^n rows**.
   This one check proves *two* things at once:
   - the reduced output is correct for every input; and
   - the "dropped" variables are **genuinely irrelevant** — if a dropped variable actually
     mattered, two full rows sharing a reduced index would disagree in `O` but be forced
     equal by the expansion, firing a mismatch. (This is the subtle failure the reduction
     could have; the test is built to catch it.)
3. **Raw bitset** `eval_expr_bitset` on the original Expr, unpacked to 2^n → require `== O`.
4. **CM-IR bitset** `eval_cm_node_bitset` over all n vars → require `== O` (independent of
   the reduced path).

Script: `audit_correctness.py` (in session scratchpad); per-expression results in
`CM_correctness_audit.csv`.

### 4.2 Result

| check | result |
|---|---|
| Expressions audited (n = 16, 18, 20, 22, 24; **all 2^n rows each**) | **74** |
| CM reduced == oracle (exhaustive) | **74 / 74** |
| Raw bitset full == oracle | **74 / 74** |
| CM-IR bitset full == oracle | **74 / 74** |
| Any method disagreeing on any row | **0** |

Every method agrees with the independent oracle on every row at every size through n=24.

### 4.3 BDD (dd.autoref) — verified separately, CUDD not run

- The harness's ROBDD backend **is `dd.autoref`** (pure-Python), not CUDD. It ran and
  self-reported correct: `robdd_status=ok`, `robdd_ok=True`,
  `robdd_correctness_mode=exact_tt` (i.e. its full truth table was compared to
  `eval_expr_tt` at n≤16). The repo's own `custom_tt_robdd` also reports `ok=True`.
- **Independent re-check (not trusting the harness flag):** I built dd.autoref BDDs directly
  and enumerated their truth tables against the oracle — **6/6 exhaustive passes** at n=12,14.
- **CUDD did not run here** (native Windows). If the paper reports CUDD numbers they must be
  labeled as Docker/WSL and not mixed with these Windows timings.
- ⚠️ **Correction to my earlier `CM_n20_feasibility_report.md`:** it said "ROBDD/CUDD
  unavailable on native Windows … returned null." That conflated two things. Precisely:
  **CUDD is unavailable; ROBDD via dd.autoref ran and was correct.** The "null" I saw was an
  empty *TT-extraction* column (extraction was flag-off), not a failed build.

---

## 5. Why it works now — and why that's legitimate, not a trick

1. **CM at large n is `live_k`-bounded.** The guard (`cm_ir.py:1486-1495`) refuses to emit
   more than 2^16 entries; feasible cases have `live_k ≤ 16`, so the "size" of a CM result at
   n=24 is at most that of an n=16 result. No 2^24 anything is built. (Confirmed: repr codes
   3/4 and guard-fired on every n>16 headline trial.)
2. **The flat methods handle small, vectorized data.** 2^24 = 16 M cells = 16 MB (uint8) /
   2 MB (packed). numpy does whole-array boolean ops on that in tens of ms. The *former*
   blocker was the O(n·2^n) big-integer env build (§2.2), now vectorized (R3).
3. **The oracle was never the wall.** `eval_expr_tt` is `n` vectorized `np.tile`/boolean
   ops; measured 3.7 ms (n=16) → 2.4 s (n=24). The agenda that motivated remote/RunPod
   compute assumed a scalar "2^20 Python evals" oracle; that assumption was wrong, which is
   why this whole campaign ran locally with **0 pod-hours**.

The feasibility ceiling for the *flat* methods is RAM for the 2^n array (16 MB at n=24,
doubling per +1 n), reached well past n=24 on a normal machine. The *reduced CM* path has no
such ceiling — only `live_k ≤ 16`.

---

## 6. Results — method comparison (`CM_methods_comparison.csv`)

Depth-4 random expressions. CM-reduced vs bitset "matched cached" compares the two over the
**same output scope** (the only apples-to-apples comparison, since CM does not emit full
2^n output at n>16). Bitset full-output and oracle are full-2^n. dd is build-only.

| n | CM reduced cached µs | bitset matched cached µs | CM/bitset | bitset **full** output ms | oracle ms | dd build ms | CUDD |
|--:|--:|--:|--:|--:|--:|--:|:--:|
| 16 | 123.8 | 73.5 | 1.68× | 0.13 | 3.2 | 0.23 | not run |
| 18 | 29.8 | 16.6 | 1.80× | 0.46 | 16.6 | 0.27 | not run |
| 20 | 16.4 | 16.4 | 1.00× | 1.37 | 86.8 | 0.17 | not run |
| 22 | 19.6 | 11.7 | 1.67× | 5.25 | 491 | (n/a) | not run |
| 24 | 19.7 | 19.3 | 1.02× | 37.5 | 2354 | (n/a) | not run |

Reading:
- **CM reduced cached per-eval is flat in n** (~16–30 µs for n≥18) because it tracks
  `live_k`, which depth-4 keeps ≤ ~13. The CM/bitset ratio (1.0–1.8×) is µs-scale noise at
  these tiny outputs, not a trend; both are far under the n=16 full-output cost.
- **Bitset full output** grows ~4×/+2n (it is 4× the bits) but stays at tens of ms → the
  honest flat lower bound. CM does not compete at full output; its n>16 value is the reduced
  representation.
- **dd build is structure-bound, not n-bound** (~0.1–0.3 ms; 6–7 BDD nodes for these
  functions). Build-only: flat-output *extraction* from a BDD is far costlier and is the
  fair thing to compare if flat output is the goal (handoff §6).

Companion tables: `CM_n16_24_headline.csv` (per-n medians + correctness),
`CM_n16_24_guard_rate.csv` (guard outcomes by depth), `CM_n16_24_scaling.csv`
(full-output/oracle scaling), `CM_env_build_cliff.csv` (§2.2), `CM_correctness_audit.csv`
(§4).

### 6.1 Guard behavior = feasibility boundary (`CM_n16_24_guard_rate.csv`)

30 expressions per (n, depth); `live_k` is set by depth. Feasibility is entirely governed by
`live_k ≤ 16`:

| depth | n=18 (b/t/refused) | n=20 | n=22 | n=24 |
|--:|:--|:--|:--|:--|
| 2 | 30/0/0 | 30/0/0 | 30/0/0 | 30/0/0 |
| 4 | 17/13/0 | 16/14/0 | 16/14/0 | 15/15/0 |
| 6 | 0/23/7 | 0/14/16 | 0/12/18 | 0/8/22 |
| 8 | 0/1/29 | 0/1/29 | 0/0/30 | 0/0/30 |
| 10 | 0/0/30 | 0/0/30 | 0/0/30 | 0/0/30 |

`b` = repr 3 (packed bitset, live≤7), `t` = repr 4 (TT vector, 7<live≤16), `refused` = the
guard `ValueError` (live>16). Refusal is correct behaviour: for a function that truly depends
on >16 inputs there is no sub-2^17 representation, and bitset/BDD are the right tools.

---

## 6.2 What "declined" means, and the benchmark-validity implication (READ THIS)

This directly answers the question "if I have a full 24-variable expression, is the whole
thing run, or is something silently lost?"

**Definitions.** CM "declines" an expression when the function it computes genuinely depends
on **more than 16 variables** (`live_k > 16`). The reduced-output path then raises
`cm_ir.py`'s guard `ValueError` instead of building a > 2^16 object. "Declined" ≠ "wrong" and
≠ "silently dropped":

- The benchmark **writes the row** (raw CSV) with `cm_hybrid_no_reinflate_ok = False`,
  `..._representation_code = -1`, and an **empty timing** — it is recorded as a *failure*,
  never given a fabricated value. (Verified: `bench_decline_d8` raw CSV.)
- A declined expression is **not run by CM at all.** In `--large-n-safe` mode the matched
  bitset comparison for that row is skipped too (it needs CM's reduced `output_vars`, which
  don't exist), so a genuine 24-live-variable expression yields **no timing for any method**
  on that row.
- Correctness is never at stake: the §4 audit proves every expression CM *does* process is
  bit-exact. Nothing CM outputs is wrong; the hard cases are simply refused.

**The trap — two things that are easy to conflate:**

1. **Function arity vs. ambient n.** A depth-`d` random expression has at most `2^d` leaves,
   hence at most `2^d` distinct variables. At the benchmark's **`--max-depth 4`**, that is
   **≤ 16 variables no matter how large n is.** Measured decline rate
   (`CM_decline_rate_by_depth.csv`, fraction with `live_k > 16`, 300 exprs each):

   | depth | n=16 | n=20 | n=24 | n=28 | n=32 | median live_k @ n=24 |
   |--:|--:|--:|--:|--:|--:|--:|
   | 3 | 0% | 0% | 0% | 0% | 0% | 4 |
   | **4 (benchmark)** | **0%** | **0%** | **0%** | **0%** | **0%** | **7** |
   | 5 | 0% | 0.7% | 2.7% | 5.7% | 9.3% | 12 |
   | 6 | 0% | 38% | 66% | 75% | 80% | 18 |
   | 8 | 0% | 99% | 100% | 100% | 100% | 24 |

   So at depth 4 **nothing is declined** — *but nothing is a genuine high-arity function
   either.* Every "n=24" (or n=28/32) depth-4 expression is really a **≤16-variable function
   embedded in a large namespace** (median arity ~7, max ~13). The scaling axis being
   demonstrated is **ambient dimension for structurally-sparse functions**, not function
   arity.

2. **Selection bias when declines *do* happen (depth ≥ 5).** The summary's per-`n` medians
   are computed with a **NaN-skipping median**, so declined rows are **silently excluded**.
   Confirmed at n=24, depth 8: of 5 trials, 3 declined; the reported
   `CM_hybrid_no_reinflate_med_s = 0.003187` is exactly `median(1860 µs, 4514 µs)` over the
   **2 survivors only**. The summary flags this only *indirectly* —
   `cm_hybrid_no_reinflate_ok_all = False` and
   `cm_hybrid_no_reinflate_final_output_vars_count_median = 0` — there is **no explicit
   "3/5 declined" count** the way `sympy_ok_count` exists. A reader who takes the median at
   face value would be seeing only the easy (≤16-live) subset, which biases CM to look better.

**Practical guidance for the paper:**
- If you benchmark at **depth 4** (as the paper scripts do): decline rate is 0, no rows are
  lost, no bias — but you must **not** describe these as arbitrary n-variable functions.
  Report them as sparse/low-arity functions in an n-variable namespace, and report the
  measured `live_k` distribution alongside n.
- If you benchmark **genuine high-arity functions** (depth ≥ 6, or a variable-forcing
  generator): expect large decline rates, and **report the decline rate as a first-class
  result** and either (a) exclude declined rows from *all* methods symmetrically and say so,
  or (b) treat "declined" as CM's honest answer of "not representable" (which is the truthful
  framing — those functions have no sub-2^17 representation).
- Consider adding an explicit `cm_hybrid_no_reinflate_declined_count` to the summary
  (`cmbench/results` + `reporting/summary_tables`) so the bias can never hide.

**Bottom line:** nothing is silently lost or wrong. But the depth-4 benchmark cannot exhibit
a true >16-variable function at all, and any deeper benchmark must disclose the decline rate,
because the per-n median otherwise describes only the survivors.

## 7. Threats to validity (for your audit / reviewers)

1. **Depth-4 keeps `live_k` small**, so the headline n=18–24 numbers mostly exercise the
   cheap `live_k≤7` (repr 3) branch. That is *representative of structurally simple
   functions*, not of dense ones. State the expression distribution in the paper; do not
   imply n=24 is cheap for arbitrary 24-variable functions (it is not — those get refused).
2. **Matched-scope comparison.** CM-reduced vs bitset is compared over the reduced scope.
   That is the fair comparison, but it is *not* "CM beats bitset at producing a full 2^24
   table" — CM does not produce that. Be explicit.
3. **BDD numbers are build-only** and via pure-Python `dd.autoref`; CUDD (the fast C engine)
   did not run here. Cross-engine timing comparisons are not valid across the Windows/WSL
   boundary.
4. **Interpreter split** (benchmarks 3.13.5, tests 3.10.11) — §1.
5. **Correctness coverage.** §4 is exhaustive over all 2^n rows but over 74 expressions of
   depth ≤4. The `repr 4` (TT-fallback, 7<live≤16) branch is thinly covered; a `live_k`-
   targeted generator would harden it. The refusal path is verified as *refusal*, not output.
6. **Single-shot timings** (oracle, env-build, full-output) carry ~±20% run-to-run variance;
   the cached per-eval numbers are medians and are stable.

---

## 8. Verdict

- **Feasibility is real and explained**, not an artifact: CM at n=18–24 is `live_k`-bounded
  (≤ 2^16), the flat methods handle small vectorized data, and the *former* blocker (the
  O(n·2^n) Python env build) was replaced by a vectorized one (R3) — re-measured here as a
  13×–>200× setup speedup with bit-identical output.
- **Correctness is solid**: 74/74 expressions bit-identical to an independent oracle across
  all 2^n rows at n=16–24, for CM-reduced, raw bitset, and CM-IR bitset; dd.autoref
  independently verified; 159/159 unit tests pass.
- **Safe to publish** with the framing in §0 and §5 and the caveats in §7. **Do not publish**
  as "CM computes n=24 truth tables cheaply" — publish as "CM's structure-preserving reduced
  representation makes functions of ≤16 live variables feasible regardless of ambient n, and
  correctly declines the rest."

## 8.1 The guard: when it was added, and how to compute > 16-variable functions

**History.** The "decline" guard is **original to the no-reinflate design**, not a recent
restriction:

| commit | date | what it introduced |
|---|---|---|
| `843a4e5` | 2026-05-31 | The no-reinflate path itself **plus** the large-output guard, `allow_reduced_output`, and the `refusing to materialize …` error. |
| `e664551` | 2026-05-31 | The `--cm-max-full-output-vars` CLI knob (default **16**). |

So the 16-variable limit has been present since the feature was born (seven weeks before the
R1/R2/R3 speedups). It is a **safety rail against accidentally allocating a 2^n object**, and
it is **already a parameter** — nothing needs to be "removed" in code.

**Removing / raising it.** Two equivalent controls:
- **CLI:** `--cm-max-full-output-vars N` (e.g. `24`). Add a high `--cm-hybrid-threshold`
  (e.g. `64`) to keep the fast packed-bitset path for large `live_k` (otherwise `live_k >
  threshold` routes to the numpy TT-vector fallback — also correct, just a different repr).
- **API:** `materialize_hybrid_no_reinflate(..., max_full_output_vars=N)`, or `=None` to
  disable the guard entirely (full 2^n output over all live vars).

**Demonstrated** (guard disabled, genuine *all-variables-live* functions, verified
bit-exact vs the independent oracle this session):

| n | live_k | output | time | peak mem |
|--:|--:|--:|--:|--:|
| 18 | 18 (all) | full 2^18 | 81 ms | 9 MB |
| 20 | 20 (all) | full 2^20 | 206 ms | 32 MB |
| 22 | 22 (all) | full 2^22 | 918 ms | 153 MB |
| 24 | 24 (all) | full 2^24 | 4.1 s | 555 MB |

CLI end-to-end check: n=20, depth-8 expressions that decline at the default limit succeed at
`--cm-max-full-output-vars 24` (5/5, repr 2, full 2^20 output). See `bench_guard16_*` vs
`bench_guard24_*`.

**The RAM wall.** Peak memory roughly doubles per +1 n (the work is 2^n big-integer
arithmetic): ~0.5 GB at n=24 → ~2 GB at n=26 → ~9 GB at n=28. The practical ceiling on a
typical machine is around **n = 26–28** for full output; beyond that you are RAM-bound
regardless of method.

**The one caveat that matters for the thesis.** For a genuine high-arity function, CM's
full output **is** the 2^n truth table — it runs the *same* `eval_cm_node_bitset` kernel over
the *same* 2^n bits as the raw-bitset baseline. **There is no reduced-representation advantage
in this regime**; removing the guard buys *completeness/capability*, not *CM speed*. CM's
structural win exists only when `live_k` is small. So: raise the guard when you need to
**compute** big functions; do not expect it to make CM **beat** bitset there.

## 9. File manifest (this folder)

| File | Contents |
|---|---|
| `CM_ARCHITECTURE_AND_AUDIT.md` | This document. |
| `CM_correctness_audit.csv` | Per-expression exhaustive correctness (§4), 74 rows. |
| `CM_env_build_cliff.csv` | Old vs new env-build cost (§2.2). |
| `CM_decline_rate_by_depth.csv` | Decline rate + live_k distribution by n × depth (§6.2). |
| `CM_methods_comparison.csv` | Consolidated method comparison (§6). |
| `CM_n16_24_headline.csv` | CM-reduced vs bitset per-n medians + sampled correctness. |
| `CM_n16_24_guard_rate.csv` | Guard outcomes by n × depth (§6.1). |
| `CM_n16_24_scaling.csv` | Bitset full-output + oracle scaling. |
| `CM_n22_24_feasibility_report.md` | The n=22/24 feasibility write-up (prior turn). |
