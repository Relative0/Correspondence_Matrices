# Kickoff Prompt for Opus — N=18/20 CM Scaling Campaign on RunPod

> Paste everything below the line into Opus. It is a standalone brief; the heavy
> operational detail lives in `OPUS_N20_RUNPOD_AGENDA.md`.

---

You are joining an ongoing research project on **Correspondence Matrices (CM)** for Boolean
computation, in `C:\Users\brian\Documents\CM_Computation` (Python 3.10; always use
`.\.venv\Scripts\python.exe`). Prior phases (see git log: Phase 1 investigation, Phase 2
speedups R1/R2/R3, Tier C re-scope) measured and optimized CM up to **n=16**. Your mission
is a **measurement campaign, not a development task**: determine whether **n=18 and n=20
are feasible** for CM — especially the `materialize_hybrid_no_reinflate` reduced-output
path — and how CM compares against the other methods (raw bitset, ROBDD, `dd`) at that
scale. Heavy computation (the `eval_expr_tt` oracle at 2^20 rows, long sweeps) runs on the
**already-provisioned RunPod worker**, not locally.

## Read first, in this order

1. `OPUS_N20_RUNPOD_AGENDA.md` — your operational playbook: pod lifecycle, cost hygiene,
   the experiment matrix, what breaks at n=20, and the deliverable spec. Follow it.
2. `FABLE_CM_HANDOFF.md` — system map, cost profile (§3.1), harness usage (§4), and the
   **proven dead ends (§6) you must not reopen**.
3. `CM_speedup_phase2_report.md` and `CM_tierC_rescope_report.md` — the current
   performance state of the code you are measuring (post-R1/R2/R3).
4. Skim `cm_ir.py` (esp. the `max_full_output_vars` guard at lines 1441–1494),
   `cm_runpod_deploy.py`, `cm_runpod_client.py`, and `cm_bench.py`'s CLI flags.

## Non-negotiable ground rules

- **Never materialize 2^n at n>16.** Keep `--cm-max-full-output-vars 16`; the
  reduced-output guard is a test subject, not an obstacle to remove.
- **Correctness oracle is `eval_expr_tt`**, verified bit-identically and **outside timed
  windows**. If you subsample oracle verification at n=20 for budget reasons, disclose it.
- **`python -m pytest -q` stays 159/159.** You should not need to change library code;
  if a change is truly required, it goes behind a flag.
- **Stop the pod when not actively running experiments** ($0.06/hr; container disk wipes
  on stop, so re-run `python cm_runpod_deploy.py --deploy` after every restart). Confirm
  `EXITED` via `--status` before ending any work session, and account for pod-hours in
  the report.
- Medians over ≥5 trials, instrumentation off for headline numbers, time-box ROBDD/`dd`
  at n=20 (~120 s/trial) and record timeouts as findings.
- Do not reopen `FABLE_CM_HANDOFF.md` §6 dead ends. Negative results, well measured,
  are valid deliverables.

## First concrete steps

1. Read the four items above.
2. Run a **local pilot** (`--sizes 16,18 --trials 1`, cheap flags) to validate the flag
   set and the guard behavior before spending pod time.
3. Start the pod, `--deploy`, `cm_runpod_smoke_test.py`, then run the experiment matrix
   from the agenda (§4) with `--cm-exec-target runpod` for the oracle-heavy sweeps.
4. Stop the pod. Write `CM_n20_feasibility_report.md` (spec in agenda §6) and present it.

Ask for clarification if scope is ambiguous. Otherwise, begin.
