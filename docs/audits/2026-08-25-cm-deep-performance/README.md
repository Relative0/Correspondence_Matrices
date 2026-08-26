# 2026-08-25 CM Deep Performance Audit

Primary deliverables:

- `CM-DEEP-PERFORMANCE-AUDIT.md` — conclusions, execution map, cost model, profile, findings, implementation, and limitations.
- `CM-RESEARCH-LEDGER.md` — current primary-source review and applicability verdicts.
- `CM-BENCHMARK-RESULTS.md` — commands, timing windows, environment, paired results, tests, and evidence index.
- `CM-OPTIMIZATION-BACKLOG.md` — gated next work and rejected/theoretically blocked ideas.
- `NEXT-AGENT-HANDOFF.md` — exact continuation state and copy-paste prompt.
- `CM-CONSOLIDATED-RERUN-PROMPT-2026-08-25.md` — post-consolidation, phased local/external rerun playbook pinned to the accepted consolidation commit.
- `CM-NEXT-AGENT-FULL-RERUN-AND-IMPLEMENTATION-PROMPT-2026-08-25.md` — comprehensive future-agent audit memory, mandatory reruns, evidence-gated DP-R1 implementation, conditional reuse studies, approval boundaries, and completion contract.
- `CM-POST-CONSOLIDATION-LOCAL-RUNPOD-PLAN-2026-08-26.md` — completed-rerun inventory and the non-duplicative next local/Runpod campaign, with cloud gates and stop rules.
- `CM-REMAINING-WORK-DEPENDENCIES-TESTING-INTEGRATION-PLAN-2026-08-26.md` — trace-first execution plan, dependency isolation, testing gates, provisional Runpod budgets, and staged integration for cache/family/context, selector, CUDD/Numba, and optional SIMD work.
- `reruns/campaign-20260826-132038/` — full post-consolidation campaign: repeated V3 and selector evidence, preparation replication, guard/cache/family/context studies, rejected DP-R1 prototype, three-pod confirmation, untouched Berkeley ABC i10 selector validation, final tests, and next-agent handoff.
- `reruns/campaign-20260826-132038/EXTERNAL-RUNS-RESULTS.md` — per-host Runpod preparation results, cost/termination audit, and preregistered i10 held-out selector result.
- `remaining-work/campaign-20260826-154541/` — implemented metrics-only trace foundation, preserved full-rate negative overhead studies, accepted 1/16 diagnostic sampling result, 380-test validation, and three retained RP-D0 dependency attempts. The final run corrected build tooling and built `astutils`, then proved the authorized clean install still blocked on source-only PLY 3.10; all pods terminated with zero-pod postflights.
- `remaining-work/orchestration-20260826-213058/` — fresh 12/59/full-380 regression gates plus sampled single/family/context trace mechanics. All enabled correctness, schema, scrub, replay, and zero-drop checks passed; workload-dependent and native lanes stopped at their entry gates.
- `remaining-work/workload-intake-20260827-002305/` — non-benchmark consumer audit, conservative trace opportunity screen, real-workload intake contract, synthetic non-promotion results, 64-focused/full-385 validation, and comprehensive external-workload handoff prompt.
- `remaining-work/three-lane-20260827-011536/` — strict owner-declared workload manifest/validator, DP-R2 temporary-memory estimator evidence and no-default-change decision memo, bounded DP-R3 provenance consolidation, exact smoke artifacts, and 84-focused/full-391 validation.

## Reproducible runs

All commands are run from the repository root and require a new, nonexistent output prefix.

Quick correctness/performance smoke:

```powershell
& .\.venv\Scripts\python.exe scripts\cm_deep_performance_audit.py `
  --suite smoke --corpora bx1,b2,epfl --prep-repetitions 3 `
  --kernel-rounds 5 --max-kernel-temporary-bytes 8388608 `
  --output-prefix docs\audits\YYYY-MM-DD-cm-followup\smoke
```

Representative preparation A/B:

```powershell
& .\.venv\Scripts\python.exe scripts\cm_prepare_memo_ablation.py `
  --suite representative --corpora bx1,b2 --repetitions 11 --skip-allocation `
  --output-prefix docs\audits\YYYY-MM-DD-cm-followup\memo_bx1_b2
```

Larger opt-in EPFL run: use the same ablation tool with `--corpora epfl --repetitions 5 --skip-allocation` and bounded `--record-start/--record-limit` chunks. This avoids an unbounded verifier/materialization run and preserves per-root paired rows.

The tools refuse overwrite, record corpus/source hashes and environment metadata,
and capture immutable manifests of listed run-defining sources. Current writers
include the audited transitive project modules; older snapshots remain exact for
their listed entries. Ordinary unit tests assert correctness and policy behavior,
never hardware-specific timing.
