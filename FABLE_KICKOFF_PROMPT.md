# Kickoff Prompt for Fable — CM Speedup Investigation (Phase 1: Investigate)

> Paste everything below the line into Fable. It is a standalone brief; it points Fable at the
> research files and sets up a measurement-first, multi-step investigation focused on
> Correspondence Matrix (CM) speedups.

---

You are joining an ongoing research project on **Correspondence Matrices (CM)** for Boolean
computation, in the repository `C:\Users\brian\Documents\CM_Computation` (Python 3.10, `.venv` at
repo root; use `.\.venv\Scripts\python.exe`). Your mission is to **find and validate speedups for
CM-related computation** — the CM IR, dense CM inflation (`materialize_cm`), the no-reinflate path
(`materialize_hybrid_no_reinflate`), the CM-node bitset evaluator, IR compilation, and anywhere
else you see genuine potential. We are **not in a rush**; we care about *correct, well-measured*
findings, not speed of turnaround. Do not waste computation on brute-force runs — think first,
measure deliberately, and pursue the highest-value leads.

## Start here (read before doing anything)

1. **[FABLE_CM_HANDOFF.md](FABLE_CM_HANDOFF.md)** — the system map: architecture, the `CMNode` IR
   model, the four execution modes, the two caches, the measured cost profile (§3.1 — this is the
   crux), how to run the benchmark harness (§4), current capabilities (§5), and the **proven dead
   ends you must not reopen** (§6: CM_parallel, threshold-only partial-hybrid, boundary micro-opts,
   "dense CM beats bitset").
2. **[FABLE_CM_SPEEDUP_AGENDA.md](FABLE_CM_SPEEDUP_AGENDA.md)** — the ranked target list (Tiers
   A–E) with `file:line`, hypotheses, how to measure, payoff, and risk. This is your menu, **not a
   fixed script** — you are expected to investigate deeper and add or re-rank targets based on what
   you actually find.
3. Then read, in the code: [`cm_ir.py`](cm_ir.py) end-to-end (it holds almost every hot path),
   [`bitset_backend.py`](bitset_backend.py) (the `eval_cm_node_bitset` kernel), and skim
   [`cm_normalize.py`](cm_normalize.py) (lifting/alignment).
4. For prior evidence and to avoid redoing solved work, read the frontier reports:
   `CM_pre_writing_validation_report.md`, `CM_ir_cost_report.md`, `CM_no_reinflation_report.md`,
   `CM_final_robustness_report.md`.

## What to focus on

Speedups for **anything CM-related**, wherever you see value. Explicitly in scope:
- **CM inflation** — dense `materialize_cm` and the numpy/hybrid/partial_hybrid materialize paths.
- **CM no-inflation** — `materialize_hybrid_no_reinflate` and its reduced-output (large-n) path.
- **IR compilation** — the `CMIRBuilder`, interning, canonicalization, structural-hash caching.
- **The CM-node bitset evaluator** — `eval_cm_node_bitset` (the dominant residual cost once compile
  is cached — see HANDOFF §3.1).
- **Execution scaffolding** — per-node dispatch, alignment, result wrapping; and the structural bet
  of flattening/codegen the evaluator.

Keep the **two-regime framing** central at all times: one-shot cost is *IR-compile-dominated*;
compile-once/cached cost (the flagship use-case) is *bitset-eval + dispatch dominated*. For every
finding, state **which regime it moves**.

## How to work — a deliberate, multi-step approach

This is **Phase 1: Investigate**. Do **not** start rewriting kernels yet. Instead:

1. **Reproduce the baseline cost profile on this machine.** Run the canonical profile command
   (HANDOFF §4.1) and confirm the regime split from §3.1. Keep the CSVs. If your machine disagrees
   with the recorded numbers, that itself is a finding.
2. **Profile, don't guess.** Use the existing instrumentation (`--cm-report-ir-breakdown`,
   `--cm-profile-cached-exec`, `--cm-eval-repeat`, the `ir_*` / `nr_*` / `cached_exec_*` diagnostic
   columns). Add a targeted `cProfile`/`perf_counter` probe only where the built-in diagnostics
   don't resolve the question. Confirm hot spots empirically before proposing a fix.
3. **Investigate deeper than the agenda.** For each promising lead, dig into *why* the cost exists
   (allocation? Python dispatch? bigint width? redundant recompute?), quantify it, and estimate the
   realistic ceiling (you cannot beat raw bitset one-shot — see the dead ends).
4. **Produce an investigation report** — `CM_speedup_investigation_phase1.md` — that ranks
   concrete, evidence-backed opportunities with: measured cost, root cause, proposed change,
   predicted effect on a named diagnostic, effort, risk, and which regime it helps. Recommend the
   1–3 highest-value targets to implement first, and explicitly note anything that looks tempting
   but is a dead end.
5. **Stop and present** the report before implementing. We will approve targets, then move to a
   Phase 2 implementation pass (behind flags, correctness-swept). We take multiple steps on
   purpose.

If, during investigation, a fix is *obviously* low-risk and you can prove it bit-for-bit
identical, you may prototype it behind a flag and include before/after medians — but the
investigation report is the primary deliverable of this phase.

## Ground rules (non-negotiable)

- **Correctness oracle is `eval_expr_tt`.** Any change must produce bit-identical results; verify
  against it. Keep correctness checks **outside timed windows** (benchmark fairness invariant).
- **Keep the suite green:** `python -m pytest -q` must stay 159/159. Run it after any code change.
- **Never materialize `2^n`** on the large-n path; preserve the `--cm-max-full-output-vars` guard
  (`cm_ir.py:1461`).
- **Do not remove backends, modes, or diagnostics.** Add behind explicit flags; keep compare modes
  interpretable. Prefer root-code edits; extend `cmbench/results/schema.py` if you add columns.
- **Do not reopen the proven dead ends** (HANDOFF §6) unless you bring a genuinely new mechanism,
  and say so explicitly.
- **Measure honestly:** n≤16 times are tens of µs — use `--cm-eval-repeat 100`, `--trials 5+`,
  compare medians, and confirm wins with instrumentation *off* (it adds per-node overhead).
- A well-measured **negative result is a valid, valuable deliverable** — record it like the
  existing `CM_*_report.md` files do.

## First concrete steps

1. Read the two research files + `cm_ir.py` + `bitset_backend.py`.
2. Reproduce the baseline profile; confirm the regime split.
3. Deep-profile the two biggest levers: (a) IR compilation cost, and (b) `eval_cm_node_bitset` in
   the cached regime.
4. Write `CM_speedup_investigation_phase1.md` with ranked, evidence-backed recommendations, and
   present it for approval before implementing.

Ask for clarification if scope is ambiguous. Otherwise, begin the investigation.
