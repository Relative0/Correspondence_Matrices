# Runpod corpus/oracle/RSS validation result

## Outcome

The single authorized corpus validation completed successfully on August 29,
2026. One Secure CPU pod ran the exact 71-file package, installed the 13
hash-locked binary wheels, passed all 79 focused tests, and completed the
frozen 35-case study. All **630 measured calls** from **420 isolated child
jobs** returned `ok`, matched the independent scalar oracle, and were saved
with complete whole-child RSS records.

The controller created pod `4q816o02xw5lxn` at 06:20:38 UTC (HTTP 201,
request `req_74f02480-9559-4cd9-8740-54211770ee1e`). The returned allocation
matched the authorization: Secure `cpu3c`, 2 vCPU, 4 GB RAM, $0.06/hour,
12-GB container storage, zero pod volume, no network volume, and the pinned
Python 3.13.15 image digest. The corpus study took 47.49 seconds; the
controller measured 153.90 seconds from create through evidence retrieval and
cleanup.

The pod was deleted with HTTP 204. The controller, watchdog, and two later
read-only postflight checks found both Runpod inventories empty and all four
campaign pod IDs absent through both detail APIs. The controller and watchdog
host guards exited. The one create is consumed and no replacement is queued.

## Frozen grid and correctness

The selected cases were 8 BX1, 8 B2, and 19 EPFL records, split before the run
into 17 calibration-corpus and 18 heldout-corpus cases. The grid covered dense,
bigint, and words representations; cold and warm schedules; and three recorded
calls per cell. The postflight analysis found exactly 630 unique call
identities, with no missing, duplicate, non-`ok`, or inexact rows.

Truth was recomputed directly from each serialized v2 DAG by a scalar
topological evaluator that imports no CM compiler or bitset evaluator. All 35
frozen truth hashes verified. Every representation/schedule/repetition output
then matched the corresponding independent live oracle hash.

The special `epfl-k10-dead-axis-1` record had syntactic support 11 but live
support 10, with `x5=0`. Its 18 calls covered all representations, schedules,
and repetitions and were exact. Its projected live-output hash differs from
the full 11-axis frozen-truth hash by construction; both hashes were computed
and checked independently. This is positive fixed-axis projection evidence,
not a correctness mismatch.

## Temporary-memory estimator result

These comparisons use the recorded **call-window `tracemalloc` peak** and the
candidate's `temporary_bytes`. They do not measure whole-process RSS.

| Scope | Calls | Candidate below peak | Median estimate/peak | P95 | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| All | 630 | 0 | 7.91× | 126.03× | 464.03× |
| Calibration corpus | 306 | 0 | 8.22× | 126.03× | 464.03× |
| Held-out corpus | 324 | 0 | 7.85× | 112.24× | 408.05× |
| Cold calls | 315 | 0 | 4.30× | 20.26× | 22.72× |
| Warm calls | 315 | 0 | 20.51× | 141.42× | 464.03× |

The candidate exceeded the measured peak in all **630/630** calls. Its
smallest estimate/peak ratio was 1.85×. The legacy estimator was below the
measured peak in **468/630** calls: 228/306 calibration calls and 240/324
held-out calls. Candidate medians were 5.76× for dense, 14.04× for bigint,
and 16.83× for words; the largest 464.03× ratio was a small warm words call.
The large ratios reflect small measured temporary allocations and should not
be read as large absolute consumption.

Under the exact inclusive temporary-memory rule `estimate <= limit`, the
fixed-limit counterfactual was:

| Limit | Model | Correct admissions | False refusals | False admissions | Correct refusals |
| --- | --- | ---: | ---: | ---: | ---: |
| 4 MiB | Candidate | 612 | 18 | 0 | 0 |
| 4 MiB | Legacy | 630 | 0 | 0 | 0 |
| 16 MiB | Candidate | 630 | 0 | 0 | 0 |
| 16 MiB | Legacy | 630 | 0 | 0 | 0 |
| 64 MiB | Candidate | 630 | 0 | 0 | 0 |
| 64 MiB | Legacy | 630 | 0 | 0 | 0 |

The 18 candidate false refusals at 4 MiB are the three repetitions in both
schedules for dense `epfl-k15-first`, `epfl-k16-first`, and
`epfl-k16-last`. Output-byte and variable-count gates are excluded from this
counterfactual. The legacy estimator's frequent underestimation does not
create a fixed-limit error here because every recorded peak still fits below
4 MiB.

## Whole-child RSS result

All **420/420** isolated child jobs had external 5 ms `/proc/<pid>/status`
samples and a kernel `VmHWM` observation. For every job, the largest sampled
`VmRSS` equaled the largest observed `VmHWM`.

| Whole-child RSS scope | Jobs | Minimum | Median | P95 | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| All jobs | 420 | 39,370,752 B | 41,115,648 B | 44,376,064 B | 45,256,704 B |
| Cold | 315 | 39,370,752 B | 41,082,880 B | 44,498,944 B | 45,256,704 B |
| Warm | 105 | 39,444,480 B | 41,623,552 B | 44,085,248 B | 45,080,576 B |

The overall median is about 39.2 MiB and the maximum about 43.2 MiB. This is
the entire evaluator child lifetime, including interpreter startup, imports,
compilation, evaluation, hashing, and allocator retention. It is neither a
per-call peak nor directly comparable with the candidate's temporary-only
estimate. It also does not prove memory-limit enforcement or cover descendant
processes.

Runtime exposed 192 host logical CPUs but affinity only to `[15, 111]`,
consistent with the assigned two CPUs; 192 must not be reported as the pod's
vCPU allocation. The recorded cgroup values were CPU `max 100000` and memory
`3999997952` bytes. These are runtime observations, not an independent test of
quota enforcement.

## Cost, transport, and evidence

The compute-only estimate for this pod is **$0.002565**. The final read-only
billing query at 06:32 UTC still listed only the three earlier campaign pods,
totaling **$0.00304477**; the new charge may lag. The conservative attributable
campaign bound remains **$0.032565**, including the $0.03 delayed-charge
reserve, below the $0.10 phase and $0.20 campaign caps. This is not a final
invoice.

The actual upload contained the approved 71 members and 1,680,864 source
bytes, and every member hash matched the approved manifest. The aggregate
source ZIP hash was `982b33e6...b1c15edf`, while the proposal recorded an
illustrative locally built ZIP hash `cb1aa9ce...879525f`. The preserved ZIP
helper writes fresh member timestamps, so aggregate ZIP bytes are not
reproducible across builds; content identity is established by the frozen
71-member manifest. The actual transport payload was 448,161 bytes and no
credential was recorded or uploaded.

Run directory:

```text
docs/audits/2026-08-25-cm-deep-performance/remaining-work/maximal-safe-20260827-192909/runpod-authorized-20260827-213104/http-corpus-execute-001/
```

| Evidence | SHA-256 |
| --- | --- |
| `RUN.json` | `2a5ff95da5e2631953cfb7b22580fca3b9d9b01a480826da6a0689b853a29009` |
| `evidence.zip` | `b8e35db1f6d2c8f6835375ebf3cb0bf716b4a1b0116cf112f9b52bff8bbf3498` |
| `corpus-memory/raw.jsonl` | `0631deb878d78efd22e8d204d30d1ec72289450c65a2f25541a097ce4cf89560` |
| `corpus-memory/rss-jobs.jsonl` | `a53c389cb516957f2cee96b19fc08e2ec46026fadc227494fbfdbac76fda8a9e` |
| `corpus-memory/summary.json` | `d6caf665c6743d16b1832eaaedae3cabbb74e294aa097771b9b90786732732c2` |
| `corpus-memory/oracles.json` | `b779cf979841c6074890191efa93effd11aa821b3820a903f26905d3ba062b0d` |
| `HTTP-CORPUS-ANALYSIS-V2-20260829.json` | `61624b24ed95c4a9b79ff77b273ecf702a22ffd14d3fe8c34a26afceedc8ad47` |
| Final verification | `81af00b9613558986b4fa9d0ddcb0dfcb031fbf70d781b1b868a8e7368106327` |

The evidence archive contains 36 files and is 250,275 bytes. The final
verification record is
`HTTP-CORPUS-FINAL-VERIFICATION-20260829-063212-489230.json` in the parent
directory.

## Decision and remaining gaps

This run adds corpus compatibility, an independent semantic oracle, a dead
syntactic-axis case, and whole-child RSS provenance. It does **not** fit or
accept the candidate, alter any coefficient or production default, or measure
genuine application traffic. `production_estimator_accepted` and
`calibration_performed` remain false.

The main remaining evidence gaps are real workload traces, wider supports or
larger structures that approach production limits, repeated allocations for
machine-level variability, and a prespecified acceptance/calibration method.
Any further paid run needs a new exact proposal and authorization. No further
pod is required to preserve or interpret this result.
