# Independent review of Audit V3

Date: 2026-07-23
Project contact: **Brian Theory (Droncheff)**
Range reviewed: `7bb0566..1a3adda` on `main` (Audit V3's three commits)
Reviewer stance: every V3 conclusion treated as an untrusted hypothesis until
re-derived; the F5 refutation, generators, and support computations were
reproduced with methods independent of V3's scripts wherever possible.

Environment: Windows 10, benchmark venv Python 3.13.5 / NumPy 2.3.2, system
Python 3.10.11 / NumPy 2.2.6, `dd.autoref` on both. 32 GB RAM. The starting
worktree was clean and the review range contained exactly the three V3 commits.

## Executive verdict

**All seven Audit V3 findings are CONFIRMED**, including the headline F5
refutation of the Fable "all-live" campaign. No V3 conclusion was refuted. The
review strengthens several of them with evidence V3 did not produce, and adds
five new findings — all latent code-quality or prose-precision issues, none of
which invalidates any published number. The corrected public headline stands
as V3 wrote it.

| V3 finding | Verdict | Strengthened by this review |
|---|---|---|
| F1 words backend | **CONFIRMED** | 1,827/1,827 reproduced on both interpreters; 28 new adversarial cases (root loads, live∩fixed overlap, re-eviction stability) pass on both |
| F2 threshold 16 | **CONFIRMED** | new depth-6 n=20 family: 0.98 at live_k≤7, 0.033 at 8–11, **0.079 at 12–16** (a stratum V3 never populated), all bit-exact |
| F3 1.02–1.09 range | **CONFIRMED** | bootstrap 95% CIs from committed raw data: 1.016 [0.984, 1.049] vs 1.089 [1.060, 1.125] / 1.079 [1.045, 1.107] — non-overlapping, so the spread is real session/population variation; a range is the correct publication form |
| F4 binding mechanism | **CONFIRMED** | independent cProfile attributes ~78% of ambient growth to the binder (V3's timers said 82%); key-construction scaling law measured directly; campaign populations shown comparable in live_k (median 5–6, p90 9 at n=24/28/32), so the same-formula isolation transfers |
| F5 all-live refutation | **CONFIRMED** | cancellation re-derived by hand; support of all 29 seeds recomputed by two independent methods (packed-cofactor and own-BDD) — every row matches V3; 4/29, median 16, n=32 support 16 |
| F5 corrected family | **CONFIRMED + proven** | the corrected generator is all-live **by construction** (proof below), and 150/150 fresh seeds disjoint from V3's pass exact BDD support |
| F5B beyond guard | **CONFIRMED** | local median 0.949 and range recomputed from V3's CSV; "retained scope" is the correct term |
| F6 public pages | **CONFIRMED** | every plotted value on both pages independently recomputed from source CSVs (one benign display rounding: 123 vs 123.08 ms); forbidden-phrase sweep clean; both themes verified via V3's captures |
| F7 hygiene | **CONFIRMED** | pytest exactly `159 passed`; third-party files byte-identical to `00c8ac3`; memory note carries the V3 correction; `cm_ir` library defaults remain threshold 7 / flat off / words off |

## F5 — the core refutation, independently re-derived

### The cancellation

`Eqv(A, Not(B)) = ¬(A ⊕ ¬B) = A ⊕ B`. The Fable mixer emits
`Xor(Xor(a, b), other(A, Not(B)))` where `a` is `A` or `Not(A)`:

- unnegated: `(A⊕B) ⊕ (A⊕B) =` **constant False**;
- negated: `¬(A⊕B) ⊕ (A⊕B) =` **constant True**.

Either way, whenever `other == Eqv` (probability 1/8 per join) the pair's
entire variable set dies semantically. The retry guard tests only
`len(CMNode.vars) == n`, a post-rewrite syntactic over-approximation, so the
dead formulas pass. I verified the other three mixers by truth table — And →
`¬A∧B`, Or → `¬A∨B`, Imp → `¬A∧¬B` (and the negated variants `A∨¬B`, `A∧¬B`,
`A∨B`) — all essential in both operands; Eqv is the unique constant channel.

### Independent support computation

Script: `deliverables_n22_24/independent_review_f5_support_2026_07_23.py`.
Two methods per formula, both independent of V3's script: (1) exact
packed-cofactor equality (`f|x=0` vs `f|x=1` over the full 2^(n−1) domain, no
BDD library involved) for n≤26; (2) my own BDD recursion using the `=>`/`<=>`
operators (V3 composed not/xor). Where both ran they agreed on every row, and
every row matches V3's CSV, including AST/CM op counts.

Results (`CM_independent_review_f5_support.csv`, `..._f5_summary.csv`):
29 rows; **4/29 all-live**; median semantic support **16**; **3 constants**
(n=18 t2 = True, n=18 t5 = False, n=28 t1 = False); n=32 row support **16**.
Dead variables at n≥28 additionally pass 512-sample scalar flip checks.

New evidence V3 did not produce: the compression↔advantage correlation
**survives controlling for ambient n** — partial correlation 0.944 (log/log
0.927) vs V3's pooled 0.945/0.927. The sharing-bracket interpretation is not
an artifact of pooling sizes.

### The corrected generator is all-live by construction

V3 verified its corrected family empirically per formula. This review adds the
proof: every mixer variant is essential in both operands (table above); sibling
subtrees have disjoint leaf sets; so if `h_A`, `h_B` are non-constant and live
in all their leaves, `g(h_A, h_B)` is live in all leaves (choose the other
operand's assignment independently) and non-constant. Induction from single
variables gives exact all-liveness for every generated formula. Empirical
cross-check: 150/150 fresh-seed formulas (seed base 91M, disjoint from V3's
73M) have exact full BDD support
(`independent_review_f3_f5gen_2026_07_23.py`). Answers to the kickoff
questions: liveness is guaranteed by construction, not only in tested samples;
excluding EQV is sufficient at the mixer position; no AND/OR/IMP composition
can cancel because only constants propagate cancellation and no mixer produces
one.

### The n=32 row

Remains a bit-exact full-ambient-output timing with semantic support 16. It
may be republished only under a label that makes no liveness claim
(V3's retraction note does this). No paid rerun is justified: the premise
failure is mathematical, not statistical.

## F1–F4 spot checks (fresh evidence)

- **F1**: original verifier reruns — 3.13.5: 1,827/1,827, n=24 CM 6.95× / raw
  7.03×; 3.10.11: 1,827/1,827, CM 7.11× / raw 6.84×. Crossover shape
  reproduced. Session-to-session movement of the realized gains (mine differ
  from V3's 6.28/7.47 and 7.13/8.21) further supports V3's narrowing: claim
  symmetric availability, not an invariant ratio. V3's 79-check adversarial
  script re-run clean on 3.10; 28 supplemental checks
  (`independent_review_f1_words_extra_2026_07_23.py`) pass on both
  interpreters: root-load programs, fixed root variables, live∩fixed overlap
  words/bigint agreement, and three cycles of scratch-width re-eviction with
  stable outputs.
- **F2**: `independent_review_f2_depth6_2026_07_23.py` — see table row above.
  The recommendation is, if anything, understated: the 12–16 stratum (64
  formulas, absent from V3's depth-4 data) gains ~13×.
- **F3**: bootstrap CIs (`CM_independent_review_f3_bootstrap.csv`) show
  per-session median uncertainty of about ±0.03 while cross-session spread is
  ~0.07. "1.02–1.09" as an observed cross-session range is the right public
  summary; any single constant would be wrong.
- **F4**: `independent_review_f4_profile_2026_07_23.py` — cProfile fraction,
  direct key-construction scaling (`tuple(sorted(fixed.items()))` grows from
  ~2.0 µs at 18 fixed entries to ~2.4 µs at 26 on this session; hash and
  dict-get flat and sub-µs), template copy scales with slot count not ambient
  n, and the campaign populations are live_k-comparable across n. V3's
  "essentially all … within measurement noise" wording is appropriately hedged
  — my data shows ~78–90% binder attribution with a small residual inside
  noise; the published negation ("not an inherently growing Bitset kernel") is
  supported and not overcorrected.

## F6/F7 verification

- All plotted values on both HTML pages recomputed from source CSVs
  (`independent_review_f6_chart_check_2026_07_23.py`): only benign display
  rounding found. Note V3's `CM_V3AUDIT_F6_chart_trace.csv` is *generated from*
  the CSVs; on its own it does not prove the HTML matches — this review closed
  that loop on the HTML side.
- Phrase sweep: no "true support", no "all variables live", no unretracted
  n=32 all-live claim, no bare 1.02 outside correction narratives, "inherent"
  appears only inside the corrected negations.
- Both themes inspected via V3's committed captures; the in-session preview
  pane renders `file://` pages as static snapshots without running the chart
  scripts, so live re-render was not possible in this harness — the numeric
  array verification substitutes for it.
- `python -m pytest -q` → exactly **159 passed**. Third-party historical
  files byte-identical to snapshot `00c8ac3`. External memory note verified
  against the corrected repo state.
- Words CLI end-to-end (`CM_independent_review_words_cli_{ord,lns}_*.csv`):
  ordinary n=16 records `raw_ast_words` and large-n-safe n=20 records
  `raw_ast_words_matched_scope`; `cm_words_eval=True`, threshold 16, all
  correctness flags true on both paths.

## New findings (none blocks the V3 record)

1. **Latent fairness gap — partial/family workloads.** `_cm_partial_workload`
   and `_cm_family_workload` now pass `words_eval` to the CM side
   ([cm_bench.py:390](cm_bench.py) and [cm_bench.py:864](cm_bench.py)), but the
   Bitset comparators in those same workloads still use the recursive bigint
   `eval_expr_bitset` (lines ~610, ~997) — words (and historically flat) never
   reach them. Under `--cm-words-eval`, partial/family CM-vs-Bitset
   comparisons would favor CM. No published result exercises this combination;
   the single-expression paths V3 verified are symmetric. Recommend either
   wiring the same engine into those controls or refusing/flagging the
   combination. Decision left to Brian since it changes recorded column
   semantics.
2. **Remote provenance gap.** `execute_remote_cm` forwards
   `hybrid_threshold` (so the new default propagates to RunPod runs by design)
   but not `cm_words_eval`; a remote run with the flag would record
   `cm_words_eval=True` while the pod evaluates without words. Latent until
   words+runpod is used together.
3. **Catch-all opcode.** Both `eval_cm_node_flat` and `_eval_words` treat any
   unrecognized opcode as EQV via their final `else` branch; a malformed
   FlatProgram computes garbage silently instead of raising. Unreachable from
   both compilers (they emit exactly the six opcodes); documented by
   `independent_review_f1_words_extra_2026_07_23.py`.
4. **Report prose understatement.** The V3 report says "two n=18 formulas are
   constants"; its own CSV (and my recomputation) show a **third** constant at
   n=28 trial 1. The 4/29 and median-16 numbers are unaffected.
5. **Minor inefficiency.** In the ordinary full-output path, `local_bit_env`
   (a full bigint environment) is built even when the words branch will not
   use it. Outside all timed windows; memory-only; harmless at current sizes.

## Blast radius of disagreements

None of the five findings changes any published number, chart, or headline
claim. Findings 1–2 are conditions on *future* use of `--cm-words-eval`
(partial/family/remote paths), not on anything published. Finding 4 is a
one-word prose correction to the V3 report (which this document records; the
V3 report itself is left intact per protocol).

## Corrected headline — unchanged

V3's five-point honest headline survives this review verbatim, including
1.75–2.52× through n=26 on the corrected all-live family, the 1.02–1.09
wrapper range, and the binder attribution of ambient drift.

## Artifacts of this review (all new; nothing overwritten)

- `deliverables_n22_24/independent_review_f5_support_2026_07_23.py`
- `deliverables_n22_24/CM_independent_review_f5_support.csv`
- `deliverables_n22_24/CM_independent_review_f5_summary.csv`
- `deliverables_n22_24/independent_review_f3_f5gen_2026_07_23.py`
- `deliverables_n22_24/CM_independent_review_f3_bootstrap.csv`
- `deliverables_n22_24/independent_review_f1_words_extra_2026_07_23.py`
- `deliverables_n22_24/independent_review_f2_depth6_2026_07_23.py`
- `deliverables_n22_24/CM_independent_review_f2_depth6.csv`
- `deliverables_n22_24/independent_review_f4_profile_2026_07_23.py`
- `deliverables_n22_24/CM_independent_review_f4_profile.csv`
- `deliverables_n22_24/independent_review_f6_chart_check_2026_07_23.py`
- `deliverables_n22_24/CM_independent_review_words_cli_{ord,lns}_{raw,summary}.csv`
