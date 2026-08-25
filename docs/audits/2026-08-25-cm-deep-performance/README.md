# 2026-08-25 CM Deep Performance Audit

Primary deliverables:

- `CM-DEEP-PERFORMANCE-AUDIT.md` — conclusions, execution map, cost model, profile, findings, implementation, and limitations.
- `CM-RESEARCH-LEDGER.md` — current primary-source review and applicability verdicts.
- `CM-BENCHMARK-RESULTS.md` — commands, timing windows, environment, paired results, tests, and evidence index.
- `CM-OPTIMIZATION-BACKLOG.md` — gated next work and rejected/theoretically blocked ideas.
- `NEXT-AGENT-HANDOFF.md` — exact continuation state and copy-paste prompt.
- `CM-CONSOLIDATED-RERUN-PROMPT-2026-08-25.md` — post-consolidation, phased local/external rerun playbook pinned to the accepted consolidation commit.

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
