# Milestone C16/R06: exact-screened CM/GF(2) tail

Date: 2026-08-30
Status: implemented, measured, and independently verified locally; exact payload approval required for second-machine execution

## What changed

C15 repeatedly laid out each candidate correspondence matrix for rank, cofactor,
and Kronecker analysis, then built, hashed, and fully reconstructed every valid
artifact. C16 separates discovery from admission:

- each of the same bounded partitions is laid out once;
- exact rank, cofactor, and Kronecker conditions produce inert descriptors;
- descriptors are ordered by the original exhaustive analyzer's complete
  deterministic artifact key; and
- only the best four descriptors are materialized, hashed, and reconstructed.

An inert descriptor cannot be used as a computed value. Every returned artifact
still passes the existing strict schema and complete truth-vector reconstruction.
The original exhaustive materializer remains the advice-off control.

## Exact results

The retained Windows run is
[`c16-gf2-screened-tail-windows-20260830-001`](runs/c16-gf2-screened-tail-windows-20260830-001).
It reused the frozen C15 40-case Yosys family without timing-based reselection.
The screened best artifact was byte-for-byte identical to the exhaustive best on
all 40 cases and all 12 structured/dense controls. Thirty-seven retained best
artifacts replayed exactly, all eight dense controls remained uncompressed, and
360 balanced timing rows had zero semantic or artifact-identity mismatches.

The independent verifier regenerated all source cases and controls, replayed the
packed source ANF, reran both analyzers, reloaded every retained artifact, and
recomputed the timing summary from the raw rows.

## Local task-equivalent timing

| Method | Analysis sum | Whole-path sum |
| --- | ---: | ---: |
| Explicit CM plus exhaustive materialization | 18,762,648,100 ns | 18,772,643,300 ns |
| Explicit CM plus screened tail | 5,285,152,100 ns | 5,295,043,500 ns |
| Packed source ANF plus screened tail | 5,267,882,300 ns | 5,315,514,300 ns |

The screened analyzer was **3.5501x** faster, and the explicit-CM whole path was
**3.5453x** faster with a **3.4777x** p95 gain. Packed source ANF measured
**0.9961x** versus explicit CM under the same screened analyzer, so representation
choice is effectively tied here. The improvement comes from shared exact matrix
layout and bounded artifact materialization, not training or a learned value.

The minimum individual case speedup was **0.8928x**. Aggregate and p95 gates pass,
but the optimization is not a universal per-case win; a cheap small-case bypass
remains appropriate before default enablement.

## Frozen second-machine package

The exact 18-file, 423,661-byte package is described by
[`c16_linux_upload_manifest.json`](c16_linux_confirmation/c16_linux_upload_manifest.json)
and the bounded lifecycle by
[`C16_SECOND_MACHINE_TIMING_PROTOCOL_2026_08_30.md`](c16_linux_confirmation/C16_SECOND_MACHINE_TIMING_PROTOCOL_2026_08_30.md).
An isolated package-only replay produced 360 exact rows and retained a **3.3568x**
whole-path and **3.3853x** p95 speedup.

The external controller was not launched. The first host approval review timed
out before process creation; its one permitted retry rejected the broad $5
authorization as insufficiently specific for this new payload. No pod was
created, nothing was uploaded, and cost was **$0**. Second-machine timing is
therefore pending explicit approval of this exact manifest and protocol.

## Interpretation and next step

C16 establishes real deterministic headroom before fitting any partition model:
the expensive part was redundant exact artifact construction, not failure to
predict a partition. After Linux confirmation, the next implementation should
place this analyzer behind an advice-off switch, add a cheap bypass for tiny
cases that regressed, and evaluate a fresh independently sourced non-XOR-heavy
family. Learned ranking is justified only if larger bounded searches leave
additional measured screening headroom after this exact optimization.
