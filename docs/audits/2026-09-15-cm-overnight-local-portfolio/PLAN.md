# Overnight local CM portfolio assurance plan

Status: complete. This was an exploratory correctness, boundary and reproducibility campaign. It cannot promote a CM performance claim or authorize cloud work.

Completed attempt: `run-003`. Its 271-cell plan and 273 source/test snapshots are frozen. All 271 module cells ran, the terminal reason is `schedule_complete`, and full evidence verification passed. The raw ledger records 232 passes and 39 generic nonzero-worker outcomes; terminal JUnit analysis separates those into 30 baseline-matched pytest nonpassing modules, eight expected optional-dependency/platform collection refusals and one all-skipped optional-control module. No further execution slice is required. The idempotent command is retained for reproduction and returns the existing terminal state:

```powershell
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' -m scripts.cm_overnight_local_portfolio execute --output 'docs/audits/2026-09-15-cm-overnight-local-portfolio/run-003' --slice-seconds 3000
```

If `EXECUTION.lock` exists, another controller owns the attempt. Inspect its recorded PID and current `STATE.json`; do not delete the lock or start a concurrent controller. Use the runner's `status` and partial `verify` commands between slices. `run-001` is an excluded three-cell smoke attempt and `run-002` was prepared but never executed; their successor notes explain the corrections.

## Objective

Use the existing pushed source and already retained local corpora to exercise the most useful remaining catalog surfaces while the machine is unattended. Preserve every scheduled outcome, including refusal, timeout, error and not-run. Stop adding timing repetitions once a mechanism has already produced a no-go; use the budget for new correctness and boundary coverage.

The completed biology B03/B04 and SymPy Y02–Y05 timing lanes are excluded. The deferred 396-session biology replication and 2,400-case cloud proposal are not part of this run.

## Workspace and custody

- Work only in `C:/Users/brian/Documents/CM_Computation/tmp/cm-consolidation-20260914`.
- Preserve the original dirty checkout at `C:/Users/brian/Documents/CM_Computation`.
- Write new evidence under `docs/audits/2026-09-15-cm-overnight-local-portfolio/` using exclusive output paths, incremental ledgers and source/input SHA-256 bindings.
- Never overwrite a completed ledger or historical artifact. Use a successor attempt directory after any pre-execution correction.
- Do not commit, push, publish, download dependencies, access credentials or use paid/cloud compute.

## Hard envelope

- Local Windows execution only.
- Eight-hour campaign ceiling; stop admitting new cells by 7 hours 30 minutes and reserve the final 30 minutes for cleanup, verification and reporting.
- One active benchmark worker at a time and one assigned CPU for timed cells.
- Two-GiB whole-job committed-memory limit, 30-second default benchmark-cell deadline, 300-second test-module deadline and one-MiB combined worker-output limit. Smaller existing safe bounds may be retained.
- Kill and verify cleanup of the owned process tree after every timeout, output breach, memory breach or cancellation.
- Disk output ceiling: 2 GiB. The current free-space check exceeded 100 GiB.

## Execution order

### 1. Freeze and readiness

Record Git commit, dirty state, Python/package/platform versions, source hashes, available native controls, retained input hashes and the exact schedule before performance timing. Refuse sources that cannot be bound. Create an adapter-readiness matrix with `ready`, `correctness_only`, `unsupported`, `missing_input` and `deferred` states.

### 2. Broad reproducibility replay

Run the repository's broadest practical Windows pytest suite once, with a bounded temporary directory and JUnit output. Compare failing/error test IDs with the most recent retained baseline rather than describing the suite as green. Then rerun the 232-test CM attribution/session selection and both audit verifiers.

### 3. Deterministic correctness and boundary expansion

Implement or reuse resumable workers for these high-value surfaces:

- S01–S13: constants, unused variables, balanced/deep trees, shared/duplicated DAGs, parity, cardinality, multiplexers, arithmetic functions, random 3-CNF, Horn/2-CNF, components, width ladders, projection traps and rewrite adversaries.
- C01/C04/C05: small generated SAT, ordinary-count and projected-count instances checked against exhaustive enumeration and available native controls. Keep task contracts separate.
- A01/A02/A03: seeded dense/sparse GF(2) systems checked against scalar elimination and available native affine controls. Report the algorithm as general unless an ingress ablation isolates CM.
- L01–L05/L07: cold/resident preparation, cache pressure, invalidation, fresh-process reload, fully consumed bounded streams, timeout recovery and refusal behavior.
- Random closed BNet and Boolean-expression cases may extend correctness coverage, but do not repeat the closed-model performance pilot.

Use deterministic seeds, vary variable/support/elimination width independently, and retain the first minimal reproducible failure. Do not keep running equivalent random cases after a correctness disagreement is found; stop the affected lane and preserve diagnostics.

### 4. Existing-input application smoke screen

Only if adapters and already retained inputs are ready without acquisition, run bounded correctness/readiness cells for H01/H02/H07–H10 and F01/F06/F09/F10. Prefer previously unused roots/models selected by a frozen hash rule. Require full output consumption, native/oracle agreement where feasible and explicit abstraction labels for cut cones or projected features. These cells assess portability and coverage; they do not become a CM speedup claim merely because one arm is faster.

Skip policy, weighted inference, fault-tree probability and Bayesian lanes because they lack a demonstrated consumer and require new semantic adapters. Skip broader SAT competition or hardware acquisition. Record these as deferred, not silently absent.

### 5. Analysis and handoff

Produce `RUN.json`, an append-only ledger, `SUMMARY.json`, `REPORT.md`, `TEST_RESULTS.md`, `ADAPTER_READINESS.json`, a source/input manifest and a verifier. Separate measured facts from hypotheses. Aggregate repetitions within instances; never treat repetitions as independent cases. Do not calculate a heldout acceptance interval for exposed exploratory inputs.

The final report must answer:

1. Did any new correctness disagreement, unsafe cleanup, or silent semantic mismatch appear?
2. Which catalog families gained real executable coverage?
3. Which width/resource boundaries were observed?
4. Did any result reveal a new representation-specific mechanism worth a separately frozen development study?
5. What should be stopped, deferred or investigated next?

## Stop conditions

Stop the whole campaign on an unverified process-tree cleanup, source/input hash drift, evidence corruption, disk ceiling breach or repeated supervisor failure. Stop only the affected lane on a semantic mismatch or worker defect while preserving all other independent results. Budget exhaustion is a normal terminal state and must leave explicit not-run cells.

Success means trustworthy additional coverage and a clean negative result if no new mechanism emerges. Runtime consumption is not itself a success criterion.
