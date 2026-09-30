# Structured factorization evidence package — 30 September 2026

This is a separate research track linked from the Correspondence Matrices
P-series study guide. It is not P16, and its timings are not comparable with
the P1–P15 lowering ratios. The original Phase 4/5 archives and frozen
campaigns were not altered.

1. [Phase 5B package](phase5b/STRUCTURED_FACTORIZATION_PHASE5B_2026-09-29.zip)
   and [master report](phase5b/PHASE5B_MASTER_REPORT.md): the archived
   recompilation-based M5 campaign was an algorithmic NO-GO (M5/B3
   complete-time ratio 2.212 on its held-out set).
2. [Live-vtree tooling probe](tooling-probe/REPORT.md): PySDD 1.0.6 supports
   correct local swaps and rotations on a referenced compiled SDD without
   recompiling the CNF for every candidate. Source, correctness records and
   timings are retained in that folder.
3. [First integration](first-integration/CAMPAIGN_REPORT.md): 756 Linux trials
   established fresh/live decision parity and cheaper live search, but
   selected L2/B3 complete time was 1.0382 (algorithmic NO-GO). The frozen
   protocol, manifest, raw rows, selection and code are retained.
4. [Independent audit](harness-audit/AUDIT_REPORT.md): the first campaign had
   no factor-exposure headroom. The audit also identified harness and hostile
   check gaps, with its source and machine-readable findings retained.
5. [Revised prospective campaign](prospective-campaign/CAMPAIGN_REPORT.md):
   repaired harness, positive developmental controls and Linux capped-worker
   and larger-SDD checks preceded a new freeze. All 756 formal rows passed
   exactness checks. Fresh/live mechanism GO passed; selected L1/B2
   complete-time ratio was 1.03798 (upper 95% 1.14154), so algorithmic GO
   failed. Four held-out cases gained direct factor exposure. Frozen protocol,
   source, raw rows and analysis are retained in that folder.

The prospective campaign's [50-step n=32 watchdog timeout](prospective-campaign/linux_scale_timeout_32x50.json)
is retained beside the shorter passed scale walks. It is a throughput limit,
not an observed exactness failure. The package makes no industrial-scale or
publication-ready novelty claim.

[artifact-manifest.json](artifact-manifest.json) gives SHA-256 and byte count
for every copied file. The Phase 5B ZIP contains the complete original
253-entry packaged deliverable; the four later directories are copied
file-for-file except generated Python caches. The original Phase 5B ZIP also
retains its historical continuity archive and broader project-context
manuscripts; those are historical supporting material, not new validated claims.

## Restoring the original directory layout

The website uses short stage labels. To inspect the code with its original
relative paths, extract the Phase 5B ZIP and place copies of these folders
beside its `phase5b_output` directory using the following names:

| Website folder | Original sibling directory |
|---|---|
| tooling-probe | live_vtree_probe_2026-09-29 |
| first-integration | live_integration_2026-09-30 |
| harness-audit | live_integration_audit_2026-09-30 |
| prospective-campaign | live_integration_revision_2026-09-30 |

The frozen receipts bind the recorded source and execution environment.
They document historical measurements; a new measurement requires a new
directory and prospective freeze. Development correctness checks and saved
artifact verification are separate from rerunning a frozen held-out campaign.
