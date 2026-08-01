# Kickoff — Benchmark Gap Analysis: What Should CM Be Tested Against Next?

Project: Correspondence Matrices (CM), `C:\Users\brian\Documents\CM_Computation`.
Contact: Brian Theory (Droncheff). Repo state at kickoff: `main` = `b6ce6b2`, clean,
`python -m pytest -q` collects 223.

## Mission

Produce a **prioritized experiment design document**, not a campaign. The question
is: *which benchmarks and comparisons that we have not already run would most change
what we believe about CM?* Focus on untested ground. Re-testing an existing result is
acceptable only when you can state what specifically is wrong or unconvincing about
the existing version of it.

Bias toward experiments that could **falsify** the structural-layer thesis, not ones
that would decorate it. An experiment whose failure mode teaches us nothing is a bad
experiment. For every proposal, the failure interpretation must be as concrete as the
success criterion.

## Read these (in order, and no more than you need)

**Read fully — these define current claims and the existing roadmap:**

1. `CM_REMAINING_TESTS_AND_RESEARCH_PRIORITIES_2026-07-25.md` — the existing
   11-priority research roadmap. Your document supersedes and sharpens this; do not
   simply restate it. Say explicitly where you agree, disagree, and reprioritize.
2. `CM_AUDIT_V4_2026-07-24.md` — what is currently valid, what was superseded, and
   the mandatory caveats. Section D (methodology) matters most for designing new work.

**Read the named sections only:**

3. `docs\audits\2026-07-26-cm-performance\CM-PERFORMANCE-AUDIT.md` — newest audit.
   Read "Prioritized findings", "Rejected or inconclusive experiments", and
   "Remaining risks and recommended next steps". The rejected list is important:
   do not re-propose GPU, naive multiprocessing, sparse-truth-table replacement, or
   approximation without new evidence that the rejection was wrong.
4. `docs\audits\2026-07-26-cm-performance\CM-OPTIMIZATION-BACKLOG.md` — ordered
   unimplemented engineering work, for distinguishing "needs a benchmark" from
   "needs an implementation first".

**Skim conclusions/abstract only — these are experiments already done, so you know
what not to re-propose naively:**

5. `CM_experiment_A_related_families_report.md`, `CM_experiment_B_partial_contexts_report.md`,
   `CM_experiment_C_operator_difference_quotient_report.md` — the three CM-native
   value experiments, preliminary synthetic results only.
6. `ROBDD_CM_fair_comparison_report.md`, `ROBDD_CM_equivalence_report.md` — prior
   BDD comparison methodology and its known limits.

**Data to inspect (do not read whole files; load with pandas and describe):**

7. `deliverables_n22_24\CM_v4audit_packed_eval_summary_runpod.csv` — CM vs BitSet by
   stratum, the current headline.
8. `deliverables_n22_24\CM_v4audit_symbolic_build_raw_runpod.csv` — native `dd.cudd`
   columns (`cudd_*`). Note: the matching `_summary_` file contains only `autoref_*`
   build columns, which are 5–20× larger. Do not confuse them.
9. `deliverables_n22_24\v4audit_corpus_2026_07_24.jsonl` — the frozen 49-formula
   corpus. **Characterize it before proposing anything**: operator histogram, depth,
   `live_k` distribution, and how many genuinely distinct expressions it contains.
   Its composition is the single biggest constraint on what current results mean.

**Code surface, for what the harness can already do (grep, don't read end to end):**

10. `cm_bench.py` — the argparse block near the bottom lists every existing workload
    and flag. `cmbench\config.py` for the config fields.
11. `cmbench\expr\families.py`, `cmbench\expr\partial_contexts.py`,
    `cmbench\expr\equivalence.py`, `cmbench\backends\robdd_dd.py` — existing workload
    runners and the BDD adapter. Determines what is a flag away versus new code.

## What is already measured (do not re-derive)

- CM vs packed BitSet, controlled semantic support 8/12/16 and sparse 1–11, local and
  RunPod, exact packed equality on every row, zero mismatches.
- Native `dd.cudd` **construction only**, 49/49 formulas, fixed order and ten seeded
  orders, with the all-in search cost separated.
- Prepared/cached same-expression evaluation vs legacy bind-each-call, 378 pairs.
- CM-internal compile optimization (wide AND/OR), cold-vs-warm first-touch, packed and
  dense scaling through n=20.

## Seed hypotheses — verify, then extend or discard

These are starting points from a 2026-08-01 review, not conclusions. Treat each as a
claim to check against the data before you build on it.

- **The corpus is the binding limitation.** It is shallow, sparse, XOR-dominated, and
  binary, with median `live_k` about 5 and only 7 formulas per controlled stratum
  (repeated across ambient sizes, so the inferential unit is 7, not 49). Almost every
  current claim may be a statement about this corpus rather than about CM.
- **BDD-hard and order-sensitive families are entirely absent.** Multipliers, hidden
  weighted bit, and circuit-derived formulas are the regimes where BDD behavior is
  actually interesting. We have never tested one.
- **CUDD is measured only at construction.** Query, cofactor, model counting,
  equivalence, and extraction are unmeasured, so no downstream comparison exists.
  Note the one extraction datapoint we have (n=16 ≈ 0.364 s vs 75 µs BitSet) suggests
  extraction is the wrong axis and query workloads are the right one.
- **Non-BDD baselines have never been benchmarked at all** — SAT, Espresso, SymPy,
  AIG/ABC, and a Numba or C-compiled evaluator are all listed as "not target" but
  never measured. At least one of them is probably the real competitor for some task
  CM claims.
- **Explicit output may be the wrong contract to compete on.** Everything measured so
  far produces a complete 2^k result, where CM's ceiling is BitSet parity by
  construction. Query-only, streaming, or partial-answer workloads are where a
  structural layer could plausibly win outright, and are untested.
- **There is an unexplained local/remote discrepancy.** At `live_k=8` the same script
  gives 1.330 remote (tight, ±1%) and 1.053 local (p10–p90 0.832–1.336) — different
  magnitude *and* different sign relative to parity. Repeat count differed (200 remote
  vs 50 local at `live_k=16`). Worth its own small experiment; it currently undermines
  every crossover claim.
- **Statistics need clustering.** Rounds are repeated measures on the same formula.
  Any future campaign should cluster by expression hash and use genuinely independent
  formulas.

Look for gaps beyond this list. Areas nobody has framed as a question yet are more
valuable than sharper versions of questions already on the roadmap.

## Deliverable

`CM_BENCHMARK_GAP_ANALYSIS_2026-08-01.md` at repo root. For each proposed experiment:

- **Question** and the **hypothesis** it tests, stated so it can come out false.
- **Why it is not already covered** — cite the file/data showing the gap.
- **Design**: corpus, baselines, timing boundary, statistical unit, sample size.
- **Success and failure interpretation** — both concrete, both informative.
- **Cost**: local vs pod, rough wall-clock, and whether new implementation is needed
  before the benchmark is possible at all.
- **Rank**, with the reasoning for the ranking made explicit.

Close with: the three experiments most likely to *disprove* something we currently
believe, and an honest statement of which current claims would not survive them.

## Ground rules

- Benchmarks use `.\.venv\Scripts\python.exe` (3.13.5); tests use system Python (3.10.11).
- Cheap scouting runs to size an experiment are fine. **Do not launch campaigns** — the
  deliverable is the plan. No pods without Brian's approval.
- Never edit prior reports (`CM_AUDIT_*`, `CM_SESSION_*`, Fable/third-party docs) and
  never overwrite historical CSVs. New artifacts go in `deliverables_n22_24\` with a
  distinctive name.
- Do not print or commit secrets; `.env.runpod*` is off limits.
- Leave the worktree clean. Do not push. Library defaults must not change.
- If an area turns out not to be worth testing, say so and say why — a reasoned "not
  worth it" is a valid finding and more useful than a padded list.
