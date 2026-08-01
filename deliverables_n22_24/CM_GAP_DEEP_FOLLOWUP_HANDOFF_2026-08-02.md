# Handoff to Codex — Review of the 2026-08-02 Deep Follow-Up Audit

Project root: `C:\Users\brian\Documents\CM_Computation`
Repo state at audit: `main` = `b6ce6b2`, no tracked file modified.
Benchmark interpreter: `.venv\Scripts\python.exe` (3.13.5, numpy 2.3.2, dd 0.6.0).

## Read first (all seven)

New (this audit):

1. `deliverables_n22_24\CM_GAP_DEEP_FOLLOWUP_2026-08-02.md` — the updated audit report.
2. `deliverables_n22_24\cm_gap_deep_followup_2026_08_02.py` — reproduction driver
   (sections selectable via `--sections`).
3. `deliverables_n22_24\cm_gap_deep_followup_results_2026_08_02.json` — machine-readable
   results for every claim in the report.
4. This file.

Prior round (context you produced):

5. `deliverables_n22_24\CM_GAP_AUDIT_2026-08-01.md`
6. `deliverables_n22_24\cm_gap_audit_probe_2026_08_01.py`
7. `deliverables_n22_24\cm_gap_audit_probe_results_2026_08_01.json`

## What this audit claims — the parts you should attack hardest

1. **Executed-op accounting (new).** `len(prog.ops)` is not an executed-operation count:
   CM's n-ary AND/OR/XOR expand to `arity−1` word-kernel calls, IMP/EQV to 2. Under this
   accounting, `CSE + associative flattening` reproduces CM's multiplier programs
   *op-for-op* (both `len(ops)` and executed ops), and CM executes 368 word ops where a
   plain binary hash-consed baseline executes 167 on the 8×8 sequential central bit —
   because share-blind flattening (`cm_ir.py:516-532`) splices shared subchains into every
   consumer. This explains your unexplained "CSE ran 1.6–1.8× faster than CM". Verify the
   counter (`expanded_word_ops`) against `_eval_words` semantics and try to refute the
   splice-duplication mechanism (e.g. by refcount-guarded flattening).
2. **Your `IdMemoBuilder` has a lifetime hazard**: it memoizes `id(expr) → node` without
   holding the `Expr`. Reused across builds after GC, a recycled id can return a wrong
   node. Also: the repo already contains a digest-memoized builder,
   `compile_expr_to_cm_ir_persistent` (`cm_ir.py:233-297`), which matches your memo cold
   and is ~3× better than the current builder even on sharing-destroyed tree input.
   Check both claims; construct the id-reuse failure if you can.
3. **Compact intern-ID keys are justified now**: a scratch builder mirroring CM's
   canonicalization with small-int keys is a further 5–10× over the id-memo (e.g. 8×8
   bit 8: 362 ms current → 10.8 ms memo → 1.0 ms compact, bit-exact). Audit the compact
   builder (`CompactBuilder` in the driver) for semantic drift vs `CMIRBuilder` — its
   commutative sort key is intern uid, not structural key, which changes arg order but
   should not change semantics. Find a counterexample if one exists.
4. **Schedule effect (old F5) refuted as material**: paired blocked-vs-interleaved moves
   the geomean 0.936 → 0.956 (~2%); the earlier 27% was pooled-mixture reweighting. The
   mechanism is measured: 50% words-env LRU miss rate interleaved, ~138 µs per k=16
   rebuild, additive to both arms. Re-run with your own schedule harness if skeptical.
5. **Wrapper-vs-kernel sign flip**: on the three controlled corpus formulas the kernel
   ratios are 0.73/0.81/0.77 (CM faster) while the published harness-arm shape gives
   2.83/3.90/1.44 on this box. If this replicates on your machine, the published C1
   sentence is arm-definition-dependent, not merely under-powered.
6. **Exact max ROBDD at n=16 is 8447**, not ~4096 (the `2^n/n` asymptote is not an exact
   bound), so your 4419-node measurement contradicts the gap analysis but not the theorem.
   Also: autoref sifting beat *both* fixed orders on every hard nb=8 bit tested, and
   task-matched pipelines at n=16 were won by neither CM nor the BDD but by the binary-CSE
   flat pipeline (~2 ms vs ~350 ms for equivalence). Check `bdd_packed_from_pick_iter`
   and the pipeline arm boundaries for fairness.
7. **Variance**: your df-corrected sigmas verified independently to the digit
   (0.1190 local / 0.0935 pod, df=10; the 0.065/0.084 are √(SS/21)). New numbers: χ² CIs
   [0.083, 0.209] / [0.065, 0.164]; regression-on-live_k gives *larger* σ (0.15/0.22);
   moment correction is negligible. Attack the CI assumptions if you disagree.
8. **Repeat/platform**: your repeat-50/200 group split (1.10 vs 1.50) is a speed confound
   — repeat was assigned adaptively, corr(log gap, log local BitSet µs) = −0.86, gap
   declines 2.67 → 1.01 across live_k. Pod-side repeat sensitivity remains unidentifiable
   from existing data.

## Rules for your run

- Benchmarks with `.venv\Scripts\python.exe`; project tests with system Python 3.10.
- Do not start a pod, commit, push, download external files, or edit historical reports
  (`CM_AUDIT_*`, `CM_SESSION_*`, `CM_BENCHMARK_GAP_ANALYSIS_*`, prior CSVs, third-party
  documents, and do not modify any `*2026_08_02*` artifact — respond in new files).
- New artifacts go in `deliverables_n22_24\` with distinctive names containing your date.
- Scratch implementations only; do not edit `cm_ir.py` or other production modules.
- Prefer refutation over agreement; separate measured facts, inferences, and unresolved
  questions; assert packed equality before every timed comparison; report deterministic
  program sizes separately from timings; state exactly which tests you ran and skipped.

## Specific deliverables requested

1. Independent verdict on claims 1–8 above (CONFIRMED / CONFIRMED-WITH-CORRECTION /
   REFUTED / UNRESOLVED), with your own reproduction where feasible.
2. A review of `CompactBuilder` and the v2 defs/ref serde in the driver as *semantics
   specs* for production work: name any rule mismatch vs `CMIRBuilder` / any schema flaw.
3. A decision recommendation for Brian on the staged optimization order proposed in the
   report (§Optimizations, steps 1–6), flagging any step you would reorder or veto.
4. If you refute the flattening-duplication mechanism or the compact-key speedup, stop and
   re-rank the E-list before proposing further extensions.
