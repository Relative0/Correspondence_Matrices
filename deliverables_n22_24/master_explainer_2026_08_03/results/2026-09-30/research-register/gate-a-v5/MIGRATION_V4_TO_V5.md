# V4 → v5 migration record

This candidate is a prospective successor, not a promotion of the failed v4 identity. No v4 file is overwritten. Production code is unchanged. All revisions are external measurement and documentation code. The archive manifest binds these bytes; no real timing data were collected to set them.

| Surface | V4 | V5 |
|---|---|---|
| Timing unit | One cold process/call | Median of nine independent cold process/calls; raw members retained |
| Pilot | 11 single-call repetitions, 2,200 workers | 11 median-of-nine replicates, 19,800 workers |
| Confirmatory time | 30 single-call repetitions | 30 median-of-nine replicates; 54,000 elementary workers |
| Memory | 15 independent single-call workers | Unchanged 3,000 primary workers; never grouped by nine |
| Primary thresholds | R>=1.20, lower CI>1.00, M<=1.10 | Unchanged; no inference in this task |
| Stability | All 200 MAD/median <=0.05 | Same all-200 limit applied to frozen aggregate estimand |
| Overhead | Parent-clock median compared with case median | Per-worker 1,001 empty pairs; median and clock resolution <=1% of each elementary duration |
| Scheduling | Pilot arm-major observations | Explicit paired members and alternating arm order; outer confirmatory schedules preserved |
| Retry | One certain pre-start infrastructure retry allowed | No retries; fail/retain/stop, missing remainder invalidates pass |
| Oracle | Independent reconstructed direct oracle | Scalar exhaustive oracle plus reconstructed direct and frozen digest |
| Host | Candidate controls insufficient for stability | Exclusive core, offline siblings, performance governor, cgroup v2/no quotas, bound environment and monitoring |
| Primary row metadata | Repeated 125 fields | Content-addressed case metadata plus strict elementary-process envelope |
| Secondary | Frozen generated corpus/schedules and adapter contracts | Same generated corpus; time schedule expands by nine, memory unchanged; no execution authorized |
| Natural | Untouched pairability population | Remains in original package, not staged or used here |

No duration calibration or new tuning data were used. Median-of-nine changes the estimand; comparisons with v4 duration statistics are not permitted. The v4 0.05 gate is not retrospectively reinterpreted. Complete historical WSL identities and artifact hashes are retained separately in V4_EVIDENCE_INDEX.json. Their stored corpus_sha256 field is preserved exactly (9622f2...); it is not relabeled as the final primary file's byte hash (aa0cb2...). Runpod evidence has its own identity and hashes. Raw pilot observations are not parsed by this task.

The copied legacy pilot/runner are provenance only and must never be invoked from this candidate. Only runner_v5.py implements the new elementary observation contract. No confirmatory launcher or Frozen Execution Prompt is supplied. The future confirmatory analyzer has a fail-closed GO/freeze authorization gate; pure-estimator tests use synthetic arrays only.
