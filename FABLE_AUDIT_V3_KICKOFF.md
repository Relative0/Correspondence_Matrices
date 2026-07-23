# Kickoff — Audit V3: Adversarial Review of the Fable Session (2026-07-21/23)

> Paste everything below the line into a fresh agent. It is standalone; detail lives in
> the referenced files. Project contact: **Brian Theory (Droncheff)**.

---

You are joining the **Correspondence Matrices (CM)** project in
`C:\Users\brian\Documents\CM_Computation`. This project runs on a chain of adversarial
audits: an Opus session built the n=18–24 feasibility campaign (`fe73f82`); a third-party
LLM audited it and made unreviewed changes; a Fable session (2026-07-21/23) audited THOSE,
kept all of them, then added a new numpy-words backend and five benchmark campaigns
(two on RunPod), finding and fixing two configuration-level bugs along the way. **Your
mission: audit the Fable session's work with the same skepticism it applied to its
predecessors.** Nothing it concluded is fact until you re-derive it. You are the reviewer
of record for commits `f4cac02..7bb0566` on `main`.

## Environment (verify first)

- Windows 10. Benchmarks: `.\.venv\Scripts\python.exe` = **Python 3.13.5** (numpy 2.3.2).
  Tests: system `python` = **3.10.11** — `python -m pytest -q` must stay **159 passed**.
- CUDD does not import on this box (only pure-Python `dd.autoref`).
- A RunPod CPU pod (`x82z2pbpofhcgz`, $0.06/hr) is kept warm; credentials in
  `.env.runpod{,.local}` — **never print the API key**. Container RAM is ~2 GB despite
  `/proc/meminfo` showing the host's; read cgroup limits. Replacing a running remote
  worker requires a pod stop/start (the bootstrap cannot kill processes).

## Read first, in this order

1. `CM_SESSION_2026-07-22_STATE_AND_FINDINGS.md` — the complete map of the session under
   audit: commit ledger, bugs found, artifact locations, protocols, open items.
   **Start here; it is your table of contents.**
2. `git log --stat fe73f82..HEAD` and the per-commit diffs — form your own view of every
   code change before reading its justification (the C1a/C3 lesson: never trust a
   comparator or a claim you haven't traced to source).
3. `CM_FABLE_AUDIT_V2_2026-07-21.md` — the session's audit verdicts (C1–C7).
4. `deliverables_n22_24/CM_FABLE_BENCHMARKS_2026-07-21.md` — every benchmark result,
   §§1–8 (esp. 7b/7c/7d, added as the campaigns ran).
5. The public-facing pages whose claims you are ultimately certifying:
   `deliverables_n22_24/cm_head_to_head_explained.html` and `cm_benchmark_charts.html`.

## The claims you must confirm or refute (each with fresh measurement)

**F1 — The words backend is bit-exact and its speed claims hold.**
`bitset_backend.py`: `_compute_word_plan` / `_eval_words` / `eval_cm_node_words` /
`eval_expr_words_bitset`. Re-derive the buffer-coloring argument (an op's output buffer
can never alias an input because dying buffers are recycled only after the op — check
this against the multi-step IMP/EQV and variadic AND/OR/XOR lowering, which the session
itself got wrong once in a prototype). Re-run
`deliverables_n22_24/fable_words_verify_2026_07_21.py` on BOTH interpreters; try to break
it beyond its cases: repeated args, width switching under cache-eviction pressure
(`_WORDS_SCRATCH_WIDTHS_MAX=2`, `_WORDS_ENV_CACHE_MAX=4` — build adversarial call
sequences that thrash both), all-fixed bindings, the <6-var fallback boundary at exactly
n=5/6. Confirm the crossover (loses ≤n≈14, ~7× at n=24) and that CM and Bitset gain
near-equally (the fairness invariant).

**F2 — The threshold-16 recommendation is right and safe.**
Claim: `hybrid_threshold=7` sent live_k≥8 formulas to a ~40× numpy fallback; 16 fixes it
with no regression elsewhere and bit-identical outputs
(`CM_FABLE_wrapper_stats300{,_t16}_*.csv`). Re-run both configs (the scripts are
archived); check the strata the session reported AND ones it didn't (e.g. does 16 hurt
anything at live_k exactly 8–11 at n=16 where output width is large relative to ambient?).
Decide whether the recommendation should become the harness default and, if you endorse
it, make the config change with tests.

**F3 — The sampling-luck correction and its statistics.**
The session replaced an 8-formula result (0.84 at n=24) with a 300-formula result (1.02).
Verify the 300-formula scripts' methodology (paired interleaving, per-trial reps
selection, median-of-medians) for bias; spot-check by rerunning one n with different
seeds. Confirm the published pages nowhere still rely on the retracted 0.84.

**F4 — The extended-campaign "drift" claim (§7c).**
Claim: wrapper CM/Bitset drifts from 1.01 (n=24) to 0.84 (n=32) because CM's reduced
program is ambient-size-independent while the matched-scope Bitset pays O(n)
fixed-binding bookkeeping. The session disclosed it did NOT isolate this by profiling
(state doc §5.5). Do the isolation: profile or micro-benchmark `_bind_flat_program`'s
key construction vs eval cost at n=24 vs n=32; determine what fraction of the drift is
harness bookkeeping vs genuine representation advantage; re-word the §7c/page claims if
the split disagrees with the stated mechanism.

**F5 — The comprehensive campaign (§7d) and its brackets.**
Verify the all-live generator really guarantees liveness (`balanced_all_vars` retry loop
in `fable_comprehensive_worker_2026_07_22.py`) and that the "sharing-rich upper bracket
/ sparse-family lower bracket" framing is quantitatively supported — e.g. measure DAG
node count vs raw AST op count per family and correlate with the ratio. Re-verify a
sample of Regime B (beyond-guard) rows locally, including at least one live_k=24–26 case.
Confirm the n=32 full-output result is reproducible in direction (words engine; needs
~45 GB — either the big-pod pattern in `fable_bigpod_provision_2026_07_22.py`, or verify
at n=28–30 locally and check the n=32 CSV row's internal consistency).

**F6 — The charts tell the truth.**
Every number on both HTML pages must trace to a committed CSV. Check the three-chart
split's per-chart captions/takeaways against the data (the pages were revised many times
— hunt for stale numbers, wrong color references, or claims that outran their caveats).
Check both light and dark themes render, and that the family caveat and the 0.84→1.02
correction narrative survived the edits.

**F7 — Session hygiene.**
`python -m pytest -q` = 159 passed; working tree clean; no library *defaults* changed
anywhere this session (words backend and threshold are opt-in — verify by diff); the
third party's original reports/CSVs remain verbatim (two files its scripts overwrote
were restored — confirm against `00c8ac3`); memory-file claims
(`~/.claude/.../memory/cm-fable-audit-v2.md`) match the repo record.

## Then: the open items (do what you endorse, after the audit)

Ranked in the state doc §5: (1) `--cm-words-eval` CLI flag + schema column;
(2) threshold-16 as harness default (if F2 endorses); (3) forced-gate liveness case in
the pytest suite; (4) tiled/blocked evaluator design note for full output beyond the RAM
wall; (5) the F4 profiling doubles as an open item; (6) leave CUDD alone until Brian
fills the placeholders in `FABLE_CUDD_COMPARISON_KICKOFF.md`.

## Ground rules (unchanged across all audits)

- Bit-exactness proven for every kernel touched (packed equality is exhaustive; sampled
  oracle only where exhaustive is infeasible — say so).
- Fairness: flattened raw-AST Bitset baseline, matched scope, matched engine,
  `bitset_baseline_kind` recorded; both sides get every optimization.
- Medians ≥5 trials, paired/interleaved, spreads + live_k/repr mix disclosed; declines
  counted; family caveats attached; negative results are deliverables.
- `pytest` stays green on system Python; direct-to-main commits whose messages say what
  was audited, confirmed, refuted, and changed; leave prior sessions' reports intact —
  your corrections go in YOUR documents.
- Do not reopen `FABLE_CM_HANDOFF.md` §6 dead ends.

## Deliverables

- `CM_AUDIT_V3_<date>.md` (repo root): F1–F7 verdicts (confirmed/refuted/partial +
  evidence), any corrections with blast radius, and the updated honest headline if it
  moved.
- Re-run artifacts as `deliverables_n22_24/*_v3audit_*` (never overwrite prior CSVs).
- If you change code/config: tests, bit-exactness proof, and a clean commit per logical
  change.
- Update the session state doc chain (a new `CM_SESSION_<date>_...md` or an addendum).

Begin with the state doc, then the diffs (`git log --stat fe73f82..HEAD`), then F1 —
the words backend is the largest new code surface. Ask Brian Theory (Droncheff) if scope
is ambiguous; otherwise proceed.
