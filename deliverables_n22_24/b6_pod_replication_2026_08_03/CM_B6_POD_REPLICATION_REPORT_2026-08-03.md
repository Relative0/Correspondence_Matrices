# B6 — Cross-platform replication of B1 on RunPod (2026-08-03)

Authorization: `POD_REPLICATION_APPROVED = YES`, hard cap $5. Orchestrator
`cm_b6_pod_replication_2026_08_03.py` + pod worker
`cm_b6_pod_worker_2026_08_03.py`; acceptance criteria pre-registered in the
orchestrator before any pod ran.

## Worker gate (latent fix 2)

The previously deployed worker pod no longer exists (terminated; status check
showed the configured pod down with no desiredStatus), so no stale worker
remained anywhere. Every B6 pod carried the **current** `cm_remote_worker.py`
and, before its driver ran, executed an in-process words_eval request that
had to return the `remote_words_eval: true` echo — **verified on all 5
evidence pods** (fail closed otherwise; no local-fallback path exists in the
worker).

## Execution

- 7 pods created in total: 2 failed pre-measurement on a RunPod proxy race
  (`/put` 404 immediately after bootstrap health; ~30–49 s lifetimes, no
  evidence collected, terminated, $0.0013 combined), fixed by adding
  404-retry and replaced by 2 new pods in run 2. **5 pods delivered full
  evidence.** Every pod was terminated after collection (verified in audits).
- All evidence pods: `cpu3c` SECURE, 2 vCPU (cgroup cpu.max "max 100000"),
  image python:3.10-slim, AMD EPYC 9655, numpy 2.2.6 (pods) vs 2.3.2 local —
  recorded provenance difference. Frozen corpus SHA verified on-pod by the
  frozen driver (`8a6da87c…f6e68a`); driver wall ~13 s/pod (2× local guard
  never triggered — the EPYC is faster than the local Ryzen).
- **Cost: $0.0022 (run 2) + $0.0050 (run 1) ≈ $0.0072 total for B6**, far
  under the $5 cap. Per-pod actuals in `b6_pod_audit_2026_08_03.json` (+ run2).

## Results (pod-clustered; per-pod stratified bootstrap, never pooled)

| pod | blocked geomean [95% CI] | rr geomean | cm/cse_flat | identity |
|---|---|---:|---:|---|
| run1 pod3 | 0.8773 [0.866, 0.889] | 0.883 | 0.961 | exact |
| run1 pod4 | 0.8773 [0.866, 0.889] | 0.885 | 0.964 | exact |
| run1 pod5 | 0.8805 [0.869, 0.892] | 0.887 | 0.961 | exact |
| run2 pod1 | 0.8793 [0.868, 0.891] | 0.884 | 0.960 | exact |
| run2 pod2 | 0.8884 [0.877, 0.900] | 0.895 | 0.971 | exact |

Pod-to-pod spread 0.011 (σ 0.0046); local reference 0.8876. Every pod:
identity fields exact (192/192 formulas), corpus SHA match, CI excludes
parity, point within ±0.05 of local. The cm/cse_flat ratios (0.96–0.97 on
EPYC vs ≈1.00 local) show a platform-dependent tilt of the ≈parity residual
— consistent with "kernel-equivalent, residual not stable" and reported, not
pooled away.

## Verdict

**CROSS-PLATFORM REPLICATION PASSED**
