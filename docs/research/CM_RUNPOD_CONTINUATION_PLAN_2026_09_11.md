# RunPod continuation: output consumers and larger query workloads

Brian authorized implementation, testing, RunPod workloads expected to exceed
ten seconds locally, and reruns within $5 total. This adds cloud execution to
the previous plan; previous audit artifacts and failed scientific gates remain
unchanged. All long correctness, timing, allocation and process tests run on
RunPod. Local work is limited to implementation and short checks.

| Phase | Concrete work | Completion or stopping condition |
| --- | --- | --- |
| R0 | Preserve source identities; source-bound cloud package, prospective cases, account and price checks, independent cleanup watchdog, attempt cost reservations. | At most $5 reserved across attempts. No creation without acknowledged watchdog. Each pod has no persistent volume and an enforced controller deadline; verify termination after retrieval. |
| R1 | Add synchronous packed-stream delivery with exact short writes, backpressure, prefix cancellation and SHA-256 receipt. | Independent scalar tests cover ordering, padding, early guards, short/failed writes and concurrent separate sinks. Caller owns flush, durability and partial-output policy. |
| R2 | Run relevant core and new tests on Linux, plus previous packed-query panels using a fresh source freeze. | All outputs exact. Preserve failures and repair before another source freeze. No native batch promotion rerun. |
| R3 | New larger n22/n24 synthetic count and file-delivery cases, paired nine times, q1/q8, cold and warm. Add native CUDD count control. | Full ingress/compilation, query, hashing, file open/write/flush/fsync/close and cleanup charged. All arms use improved masks. Separate allocation runs and exact independent tiled NumPy oracle. |
| R4 | Use real buffered file consumers; reread stored bytes, check digest/length, cancel after a bounded prefix. Compare full CSE output, positional full output and fixed chunk widths 12/16/18. | No in-memory retention of all streamed output. Real filesystem exercise on synthetic formula inputs; no claim of deployed application adoption or consumer trace. |
| R5 | Exercise JSON reload, fresh process cost, renamed/pressure cache sessions and concurrent clients. | Reuse validated expression DAG serialization; all loading charged. Record process lifetime separately. Concurrency establishes correctness and memory ownership, not unmeasured parallel speedup. |
| R6 | Reconcile broader hypotheses and close the evidence package. | Native batching, H2/H3/H6/router, incremental and hardware gates retain their prior negative results. GF(2), hierarchical/ZDD and GPU work require a new admitted task; paid hardware alone does not establish it. |

The cloud campaign uses one two-vCPU CPU pod at a time, initially cpu3g (8 GB),
with a maximum compute rate of $0.10/hour, $0.01/hour storage reserve, 5,400-second
cleanup deadline and 300-second reconciliation allowance. Each attempt reserves
$0.18 before creation, rounded above the maximum deadline cost. Failed/uncertain
attempts retain that reservation; no replacement while ownership is unresolved.
The live quote, assigned rate, elapsed upper bound and cleanup evidence are saved.
The $5 ceiling is not a spending target. Idle sleep prevention is temporary;
controller/watchdog protection cannot survive host power or network loss.

The API credential is used through the existing credential loader only on the
controller. It is never printed, recorded or sent to the pod. Uploads contain an
explicit allowlist of source/tests and inert fixture JSON, verified by hashes.
The worker receives a separate ephemeral transport token, not the API key.

All chunk widths are frozen before timing; there is no winner-based default
selection. New width/seed panels are prospective synthetic extrapolation on a
cloud VM, not an independent physical-host promotion or real-world prevalence
claim. Fresh small/large workloads remain separate from consumed historical data.

RunPod's [pricing documentation](https://docs.runpod.io/pods/pricing) states
per-second compute/storage billing and no ingress/egress charge. Resources use
the documented [pod API](https://docs.runpod.io/api-reference/pods/POST/pods).
Termination, rather than stopping with retained storage, closes each attempt.

**Completed status.** R0–R6 reached their feasible execution boundaries. The
writer is implemented and documented. Linux verification passed 267 tests and
four subtests, 1,692 timing cells, 162 allocation rows, 85 fresh lifecycles,
1,620 file rereads and 16 concurrent cancellation sessions. A separate 39-child
diagnostic corrected interpretation of inherited process-memory high-water
counters; original rows remain intact. All five created pods were terminated,
all cleanup watchdogs agreed, and both final inventories were empty. Total
conservative elapsed compute/storage estimate: $0.01124; reservations: $0.90
of the authorized $5. Billing records were still pending at closeout.

The source/archive transport repairs, stronger native count comparison,
large-output gains, small-chunk/warm regressions and untouched negative gates
are recorded in the [cloud report](../audits/2026-09-11-cm-runpod-continuation/REPORT.md).
No further paid run is queued. Remaining adoption work requires an admitted
real workload/consumer trace; the available conditioned k8 feature-model
fixtures and synthetic sessions do not supply that prerequisite.
