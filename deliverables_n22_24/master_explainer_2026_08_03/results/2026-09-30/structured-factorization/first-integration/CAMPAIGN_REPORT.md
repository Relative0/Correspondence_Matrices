# Live-vtree integration gate — measured result

**Mechanism GO; algorithmic NO-GO.** The new bounded campaign ran on 30
September 2026 (Asia/Bangkok), after a Linux source/protocol freeze. Native
live moves reproduce fresh-compilation M1/M2 decisions and make their search
stages much cheaper. The validation-selected live L2 method did **not** reduce
complete exact factorization time against the validation-selected syntax B3
baseline. Phase 5B's earlier negative result remains unchanged and separate.

## Locked design and execution

The new manifest contains 12 validation and 24 held-out nonfalse CNFs from
disjoint generator templates (n=8,10,12,14); no CNF duplicates Phase 5B's 30
held-out cases or the tooling probe's eight timing cases. Seven non-oracle
methods ran three fresh-process repetitions per input, for **756 completed
trials**. Every worker had a 20-second watchdog and Linux `RLIMIT_AS=2 GiB`
set before PySDD import. A 256 MiB allocation-over-cap negative control
raised `MemoryError`; a 2 GiB-capped PySDD smoke matched an independent exact
partition before the freeze. The Runpod CPU3 General Purpose Pod supplied two
vCPUs and 8 GiB container memory at the live quoted rate of **$0.08/hour**.
It was terminated after the raw rows were retrieved, and the temporary SSH
key was removed from the account. All rows were sequential; cumulative worker
process wall time was **104.32 seconds**, below the registered 90-minute cap.
Maximum reported worker peak RSS was **66.05 MiB**. `RLIMIT_AS` constrained
virtual address space; RSS was observed, not itself capped at 2 GiB.

The Linux freeze receipt is `campaign_freeze.json` (SHA-256
`e4c192955d8f9291309f31aa328b5912f0530fef4d93621d91d84b6e6156227d`).
It captures source/protocol/manifest hashes, Python 3.11.16, PySDD 1.0.6,
python-sat 1.9.dev15, other pinned packages, cap evidence, limits and job IDs.
The receipt was written before validation. Validation then locked **B3** as
baseline and **L2** as challenger: their validation geometric complete times
were 20.40 and 21.66 ms, respectively. The selection file binds the
validation raw-row SHA-256 before held-out execution. Source hashes and all
756 stored semantic/carrier partitions passed a separate local post-run audit.
There were **zero worker failures, timeouts, memory-cap breaches or independent
partition disagreements**. The original Phase 4/5 archive verifier again
found no changes among 3,821 protected files.

## Held-out decision

| Registered measure | Result |
|---|---:|
| L2/B3 paired geometric complete-time ratio | **1.0382** |
| One-sided 95% instance-bootstrap upper ratio | **1.0496** |
| Required for algorithmic GO | ratio <=0.90 and upper <1 |
| Instance wins / losses for L2 | 1 / 23 |
| Failures for B3 / L2 | 0 / 0 |

The held-out geometric complete times were **48.18 ms for B3** and **50.02
ms for L2**. The registered algorithmic decision is **NO-GO**. B3 and L2
returned the same certified direct partition on all 72 matched held-out
repetitions, and each made the same number of residual SAT calls. The live
search therefore bought no additional direct-factor exposure on this set;
its extra move/search work raised total time. Across held-out repetitions,
the B3 and L2 residual SAT-call totals were both 179,448. Geometric search
stage times were 1.85 ms (B3) and 3.00 ms (L2); geometric exact-stage times
were 45.56 and 45.82 ms.

The separate mechanism gate is **GO**. Both fresh/live pairs matched every
held-out candidate score, acceptance decision, final tree, certified direct
partition and exact partition, with no pair mismatch. L1/F1 paired geometric
search-stage ratio was **0.2784** (95% bootstrap upper **0.2943**); L2/F2
was **0.3310** (upper **0.3509**). These ratios establish cheaper matched
search on this bounded set, not an algorithmic total-time benefit. The 2 GiB
hard cap and watchdog covered uncapped native inverse moves during the run.

## Evidence and limits

`validation_results.jsonl` has 252 raw rows (SHA-256
`b52e14b20fb7c5f3fe9e42acefcf7ffb400976480cb459a7fe65520df629d018`);
`heldout_results.jsonl` has 504 (SHA-256
`5e5296ea6ac6d3ee07cff8a6c9984548ac3ee3f14656cf19a14d58674a2e5fde`).
`baseline_selection.json`, `campaign_analysis.json` and `postrun_audit.json`
record the locked choice, bootstrap analysis and independent local audit.
Each raw success row retains the candidate trace, stage costs, SAT statistics,
final exact partitions and peak memory. The Runpod result archive matched its
local SHA-256 after transfer. All remote work stayed in a new ephemeral Pod;
only this sibling integration directory received new local files.

These are synthetic n<=14 cases, not industrial inputs. The local gate shows
that PySDD live moves are implementable, exact and cheaper than recompiling
the same candidates, while the tested M1/M2 objectives did not improve the
complete exact pipeline over syntax B3. The result does not justify changing
the archived Phase 5B outcome or claiming a broader factorization speedup.
