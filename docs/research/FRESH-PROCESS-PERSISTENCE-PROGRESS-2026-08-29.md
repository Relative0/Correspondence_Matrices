# Fresh-process persistence progress

The corrected frozen local campaign passed all 256 scheduled cells. Each cell
used one supervised construction process and a different supervised
reload/query process, for 512 owned child-process executions. CM, structural
CSE, direct CNF and a clearly labelled portable `dd.autoref` ROBDD control all
reproduced both versions' exact bounded relations on eight cached-real
conditioned `k=8` feature-model slices.

This closes the earlier fresh-process functional gap for the four locally
available arms. It does not establish a speed, memory, artifact-size or
full-model advantage. The ROBDD control is not native CUDD, and no native arm
was replaced with a portable implementation.

## Accepted evidence

| Item | Result | Evidence |
| --- | --- | --- |
| Counterbalanced campaign | 256/256 cells passed: 64 each for CM, CSE, direct CNF and portable ROBDD | [summary](verification/fresh-process-persistence-v2-2026-08-29/summary.json) and [plan](verification/fresh-process-persistence-v2-2026-08-29/plan.json) |
| Process freshness | 256 construction workers and 256 distinct within-cell reload/query workers were observed in owned Windows Job Objects | [cell ledger](verification/fresh-process-persistence-v2-2026-08-29/ledger.jsonl) |
| Semantic checking | 512 relation rows agreed with scalar CNF; every saved structure also passed an independent structural replay | [oracles](verification/fresh-process-persistence-v2-2026-08-29/oracles.json) and [artifacts](verification/fresh-process-persistence-v2-2026-08-29/artifacts) |
| Determinism | Each arm/case artifact had identical bytes across the eight-block complete counterbalance cycle | [checksums](verification/fresh-process-persistence-v2-2026-08-29/checksums.json) |
| Frozen reproduction | 292 files, 5,959,657 bytes; verifier returned 256 cells and `mutated: false` | [frozen source snapshot](verification/fresh-process-persistence-v2-2026-08-29/source_snapshot) |
| Attempt accounting | Two dependency-closure failures and one complete but wording-superseded run are recorded, but are not accepted evidence | [attempt receipt](verification/fresh-process-persistence-attempts-2026-08-29.json) |

The accepted checksum manifest has SHA-256
`a9269e34fecffb32acdee75ff49bd9b9727cf7ea55b9b17ae8aa894c5c7dce81`.
The summary, plan and ledger hashes are preserved in the attempt receipt.

## What each process did

The construction worker received the bounded scenario and wrote one
answer-cache-free structural artifact. It did not compute or store a truth
vector. A second worker then read the exact hashed bytes, reconstructed the
representation and queried both versions. The controller compared the result
with scalar CNF enumeration outside the measured worker span and independently
replayed the stored structure:

- CM and CSE artifacts contain canonical flat structural instructions;
- direct-CNF artifacts contain the ordered clause structures; and
- the portable ROBDD artifacts use `dd`'s JSON graph format and are replayed by
  a separate bounded evaluator that does not import `dd`.

Unknown fields, malformed structures, duplicate JSON keys, noncanonical
standard bundles, changed hashes, answer-cache fields, wrong roots, BDD cycles,
BDD ordering violations and cross-arm requests are refused.

The implementation and verifier are in
[`cmbench/comparative/fresh_persistence.py`](../../cmbench/comparative/fresh_persistence.py)
and
[`scripts/cm_comparative_fresh_persistence_pilot.py`](../../scripts/cm_comparative_fresh_persistence_pilot.py).

## Descriptive artifact bytes

These are exact observed file sizes for two-version `k=8` cells. They are
useful for inspecting the saved evidence, but are not an efficiency ranking:
the formats carry different metadata, the cohort contains only eight
conditioned slices, and native implementations are absent.

| Arm | Cells | Minimum bytes | Median bytes | Maximum bytes |
| --- | ---: | ---: | ---: | ---: |
| Portable `dd.autoref` ROBDD control | 64 | 173 | 303 | 364 |
| CM flat structure | 64 | 661 | 997 | 1,227 |
| Direct CNF | 64 | 415 | 553 | 847 |
| Structural CSE flat structure | 64 | 662 | 1,030 | 1,307 |

The artifact bytes were deterministic for every arm/case identity across all
eight blocks. That is a serialization-repeatability result, not evidence that
one representation will remain smaller on full models or other distributions.

## Native admission results

Three requested native persistence arms did not pass their admission gates:

| Arm | Recorded result | What is still required |
| --- | --- | --- |
| Native CUDD BDD | Refused: the local `dd.cudd` native extension is unavailable | Identified native extension, reviewed dump/load adapter, independent replay and matched Linux resource accounting |
| Native CUDD ZDD | Refused even if a module later appears: the reviewed ZDD serialize/reload adapter is not implemented | Exact ZDD semantic contract, named-root serialization, reload and independent replay |
| d4 d-DNNF | Refused: the current d4 contract parses exact counts only and records `ddnnf_serialization_measured: false` | Hash-pinned binary, documented d-DNNF output dialect, bounded parser, fresh reload/extraction and exact replay |

The machine-readable admissions are embedded in the accepted
[plan](verification/fresh-process-persistence-v2-2026-08-29/plan.json).
The locally installed `dd.autoref` module is retained only as a portable
correctness control; `native_execution` is false and `portability_control` is
true in every one of its cells.

## Measurement boundary

Windows Job Objects verified ownership, process limits, cleanup and aggregate
committed-memory high-water values. That memory metric is explicitly
`job_committed_high_water_not_rss`; it is not comparable process-tree RSS.
The controller therefore sets `memory_ranking_permitted: false` for every
cell. Timings likewise remain diagnostics from one local functional cycle, not
a calibrated performance campaign.

The strongest supported statement is:

> On eight cached conditioned `k=8` feature-model slices, the tested CM,
> structural CSE, direct-CNF and portable `dd.autoref` ROBDD implementations
> wrote answer-cache-free structures in supervised construction processes,
> reconstructed them in different supervised processes, and reproduced both
> versions' exact relations in all 256 counterbalanced cells.

It does not establish native CUDD/ZDD/d4 persistence, full-model behavior,
Linux peak RSS, cold/reload throughput rankings, broad file-size rankings,
production compatibility or independent third-party replication.

## Attempt history

Two initial frozen-worker attempts stopped before completing a cell because
the copied source closure omitted, first, `scripts/cm_native_contracts.py` and,
second, `cmbench/comparative/ir.py`. A frozen-worker unit test was then added so
future changes exercise the copied dependency closure before a full campaign.

A complete 256-cell v1 subsequently verified, but its generated limitation
text incorrectly retained the phrase “two-block” after the plan had expanded
to the required eight-block counterbalance cycle. That evidence was not edited.
The claim text was corrected in source and the entire accepted v2 campaign was
rerun. The concise hash/count receipt preserves all four attempt outcomes.

## Reproduce locally

Use a new output directory:

```powershell
.\.venv\Scripts\python.exe -B scripts/cm_comparative_fresh_persistence_pilot.py run --output tmp/fresh-persistence-NEW-ID
.\.venv\Scripts\python.exe -B scripts/cm_comparative_fresh_persistence_pilot.py verify --output tmp/fresh-persistence-NEW-ID
.\.venv\Scripts\python.exe -B -m unittest tests.test_cm_comparative_fresh_persistence tests.test_cm_comparative_fresh_persistence_pilot
```

The accepted run used no network, cloud resource or dependency installation.
No Runpod authorization was inferred from this local continuation.

## Next priorities

1. Reconcile with the concurrent native-scout continuation and, only after its
   separate exact cloud authorization, use the latest
   `RUNPOD-NATIVE-SCOUT-PROCFS-RACE-RETRY-PROPOSAL-20260829.md`; do not replay
   an older consumed attempt. Use native CUDD BDD as the first persistence
   extension and keep `dd.autoref` separate.
2. Implement and adversarially test a native CUDD ZDD serialization/reload
   contract before scheduling any ZDD measurements.
3. Extend the hash-pinned d4 contract from count parsing to a documented,
   bounded d-DNNF artifact and fresh-process reload/extraction path.
4. On Linux, collect simultaneous process-group peak RSS, construction,
   serialization, reload, first-query and repeated-query measurements with
   preregistered repetitions. Keep those performance receipts separate from
   this correctness campaign.
5. Expand from conditioned `k=8` slices to admitted full feature models and
   history cohorts, including timeouts, refusals and never-break-even cases.
6. Obtain an external-person reproduction and continue the license/privacy
   work needed for genuinely observed configurator traces.
