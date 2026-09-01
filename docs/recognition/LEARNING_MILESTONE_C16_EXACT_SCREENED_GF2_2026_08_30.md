# Milestone C16/R06: exact-screened CM/GF(2) tail

Date: 2026-08-30 (Linux lifecycle updated 2026-08-31)
Status: implemented and independently verified locally and on a second Linux machine; first Linux attempt safely reconciled after an import-bootstrap failure; corrected v2 package passed all gates

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

## First second-machine attempt

The exact 18-file, 423,661-byte package is described by
[`c16_linux_upload_manifest.json`](c16_linux_confirmation/c16_linux_upload_manifest.json)
and the bounded lifecycle by
[`C16_SECOND_MACHINE_TIMING_PROTOCOL_2026_08_30.md`](c16_linux_confirmation/C16_SECOND_MACHINE_TIMING_PROTOCOL_2026_08_30.md).
An isolated package-only replay produced 360 exact rows and retained a **3.3568x**
whole-path and **3.3853x** p95 speedup. That validation injected `PYTHONPATH`,
however, while the remote launcher did not. The exact package was subsequently
authorized and uploaded to one Secure RunPod CPU pod. The pinned Python 3.13.15
image, 2 vCPU, 4 GB RAM, 12 GB container disk, zero persistent volumes, and
$0.06/hour rate were all verified before upload.

The workload entry point then failed before measurement because the uploaded
package root was absent from `sys.path`, producing `ModuleNotFoundError` for the
uploaded `cm_expr_serde.py`. The one-pod/no-replacement rule was honored. The
controller retrieved 5,003 bytes of bounded evidence, deleted the pod with HTTP
204, and reconciled both RunPod inventories to empty. Estimated cost was
**$0.000699**. The independent lifecycle record is
[`RUNPOD_C16_LINUX_FINAL_VERIFICATION_20260831.json`](c16_linux_confirmation/RUNPOD_C16_LINUX_FINAL_VERIFICATION_20260831.json).
No second-machine scientific measurement was obtained from this attempt.

## Corrected v2 package

The entry point now inserts its uploaded package root before project imports,
matching the established Linux confirmation launchers. The package validator no
longer injects `PYTHONPATH`. The corrected frozen package is described by
[`c16_linux_upload_manifest_v2.json`](c16_linux_confirmation/c16_linux_upload_manifest_v2.json)
and
[`C16_SECOND_MACHINE_TIMING_PACKAGE_V2_PROTOCOL_2026_08_31.md`](c16_linux_confirmation/C16_SECOND_MACHINE_TIMING_PACKAGE_V2_PROTOCOL_2026_08_31.md).

The v2 package remains 18 files and is 423,735 bytes. A fresh isolated replay
with `PYTHONPATH` absent completed all 360 rows with zero semantic mismatches,
an exact best-artifact match, **3.4371x** whole-path speedup, and **3.4480x** p95
speedup.

The exactly authorized v2 package then completed on a Secure RunPod AMD EPYC
7713 CPU under the pinned Python 3.13.15 image. All **360/360** measurement rows
had zero semantic and artifact mismatches, all 40 functional rows reconstructed
exactly, and the screened best artifact matched the exhaustive best throughout.
Linux measured **3.1819x** analysis speedup, **3.1779x** whole-path speedup, and
**3.1180x** p95 speedup. Packed source ANF was effectively tied with explicit CM
under the screened tail at **0.9960x**.

The controller retrieved and independently verified the bounded evidence, deleted
the pod with HTTP 204, and reconciled both RunPod inventories to empty. The v2
run cost an estimated **$0.002779**; both C16 attempts together cost
**$0.003478**. The final record is
[`RUNPOD_C16_PACKAGE_V2_FINAL_VERIFICATION_20260831.json`](c16_linux_confirmation/RUNPOD_C16_PACKAGE_V2_FINAL_VERIFICATION_20260831.json).

## Interpretation and next step

C16 establishes real deterministic headroom before fitting any partition model:
the expensive part was redundant exact artifact construction, not failure to
predict a partition. The next implementation should place the analyzer behind an
advice-off switch, add a cheap bypass for tiny cases that regressed, and evaluate
a fresh independently sourced non-XOR-heavy family. Learned ranking is justified
only if larger bounded searches leave additional measured screening headroom
after this exact optimization.
