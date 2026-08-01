# Kickoff (Fable) — Optimization Opportunity Hunt for Correspondence Matrices

Project: Correspondence Matrices (CM), `C:\Users\brian\Documents\CM_Computation`.
Contact: Brian Theory (Droncheff). Repo state at kickoff: `main` = `b6ce6b2`, clean
tree, `python -m pytest -q` collects 223.

## Mission

Find where the CM implementation is leaving performance on the table, prove it with
profile evidence, and prototype enough to size the win. This is an **internal speed
and memory hunt** — not a comparison against other Boolean tools. (That question is
scoped separately in `CM_BENCHMARK_GAP_KICKOFF_2026-08-01.md`; do not duplicate it.)

The prize is a ranked, evidence-backed list of optimizations with measured impact.
An opportunity you disprove is as valuable as one you confirm — say so and show the
measurement.

## Non-negotiable constraints

- **Bit-exactness.** Every proposed change must produce byte-identical output on the
  six known opcodes. Anything that alters results is out of scope, not a trade-off to
  offer. This project has rejected approximation and mixed precision outright.
- **Library defaults must not change** without Brian's approval: `cm_ir.py` threshold
  7, flat off, words off; harness default threshold 16.
- **Land nothing on `main` without approval.** Prototype freely — worktree, branch, or
  clearly-named scratch files — and leave the working tree clean at the end.
- Tests must stay at 223 passing on system Python (3.10.11). Benchmarks use
  `.\.venv\Scripts\python.exe` (3.13.5).

## Read these — and no more than you need

**Read fully:**

1. `docs\audits\2026-07-26-cm-performance\CM-PERFORMANCE-AUDIT.md` — the most recent
   performance audit. Its "Profiling results and hotspots", "Implemented changes", and
   **"Rejected or inconclusive experiments"** sections define the current floor. Do not
   re-propose anything on the rejected list without new evidence that the rejection was
   wrong.
2. `docs\audits\2026-07-26-cm-performance\CM-OPTIMIZATION-BACKLOG.md` — eleven already-
   catalogued items with priorities and dependencies. **These are known.** Your value is
   in what is *not* on this list, or in showing that the list's ordering is wrong.
3. `bitset_backend.py` (~725 lines) — the execution kernel. This is the hot path.

**Read selectively (grep to the relevant functions; do not read end to end):**

4. `cm_ir.py` (~1875 lines) — the compiler and structural IR. Focus on
   `compile_expr_to_cm_ir`, `expr_structural_hash`, `CMNode.__hash__` (already
   memoized — verify the memoization actually holds under the current call pattern),
   `materialize_hybrid_no_reinflate`, and the word-plan construction.
5. `numba_backend.py` — a compiled-execution path exists in the tree. Determine
   whether it is wired into the dispatcher, whether it is ever exercised, and whether
   it has ever been benchmarked against the words kernel. If it is dead code, say so.
6. `cm_bench.py` (~4955 lines) — orchestration only. Grep for timing boundaries; do
   not audit the CLI.
7. `docs\audits\2026-07-26-cm-performance\OUTPUT-BUDGET-CONTINUATION.md` — the output
   budget contract that just landed; new work must respect its typed status semantics.

## Seed leads — verify or kill each

Starting points, not conclusions. Several may already be closed.

- **Kernel inner loops.** `_eval_words`, `eval_cm_node_flat`, `eval_expr_flat_bitset`:
  temporaries not reused, dtype width larger than needed, operations not done in place,
  loop-invariant work inside the operand loop, opcode dispatch cost per node.
- **Word plan and slot allocation.** `_compute_word_plan` — scheduling quality, slot
  reuse, dead-slot freeing, and whether plan construction is amortized across repeated
  evaluation or silently rebuilt.
- **Binding-key construction.** Audit V3 finding F4 measured the ambient-`n` cost delta
  as living in binding-key construction, *not* in the bound evaluator (n=24 full 7.083
  µs vs prebound 2.424 µs; n=32 8.909 vs 2.347). That gap has never been attacked
  directly and looks like the cleanest remaining win.
- **Engine thresholds may be mis-tuned.** The bigint→words crossover (library 7,
  harness 16) predates several kernel changes. Re-derive the crossover empirically on
  current code; a stale threshold is a free win or a free loss.
- **Pre-execution structural work.** Constant folding, common-subexpression
  elimination across the DAG, XOR-chain balancing, De Morgan normalization, and
  restricting to live support earlier in the pipeline. CM's whole thesis is that
  structure is exploitable — if none of this is implemented, that is itself a finding.
- **Query-only and partial-answer paths.** Everything currently materializes a complete
  2^k artifact. Where a caller wants a count, a hash, a single assignment, or a
  cofactor, the complete artifact may be pure waste. Backlog item 10 (tiled/streaming)
  is the design; check whether cheaper non-streaming wins exist first.
- **Cold start.** The audit measured 3.712/4.860 s in imports plus 1.501 s in backend
  discovery. Backlog item 5 covers it; confirm the number still holds and whether it
  affects any *measured* benchmark path or only developer iteration.

Look beyond this list. Novel hot spots are worth more than refinements of known ones.

## Method

Match the project's existing measurement discipline:

- **Paired and interleaved** before/after on the same process and formula set, with
  enough rounds to report a median paired ratio (not a ratio of medians — this project
  has corrected that error once already) plus p10–p90.
- Report the **statistical unit** honestly: rounds on one formula are repeated
  measures, not independent observations.
- Prove bit-exactness with a fuzz set spanning the support range you touch, and state
  the comparison used.
- Profile before proposing. A claimed hotspot without profile data is a guess.

## Deliverable

`FABLE_OPTIMIZATION_FINDINGS_2026-08-01.md` at repo root. Per opportunity:

- **Evidence** — profile output or measurement showing the cost is real and where.
- **Root cause** — the specific code and why it costs what it costs.
- **Proposed change** and its blast radius (which callers, which outputs, which flags).
- **Measured or estimated impact**, with the measurement method stated. Distinguish
  measured from projected.
- **Risk** and what could break.
- **Verdict** — worth doing, not worth doing, or needs a decision from Brian.

Close with a ranked implementation order and, separately, an explicit list of leads you
investigated and **killed**, with the evidence that killed them. Negative results go in
the report; they stop the next agent from re-treading the ground.

Supporting artifacts (profiles, CSVs) go in `deliverables_n22_24\` with `optfable` in
the filename. Never overwrite historical CSVs; never edit prior reports
(`CM_AUDIT_*`, `CM_SESSION_*`, `docs\audits\**`).

## Out of scope

GPU and distributed execution, multiprocessing as a default, sparse truth tables as the
default artifact, approximate or mixed-precision execution, dense CM reinflation as a
shortcut, and performance assertions inside ordinary pytest. All previously considered
and rejected — see the audit's rejected list for the reasoning before you disagree.
