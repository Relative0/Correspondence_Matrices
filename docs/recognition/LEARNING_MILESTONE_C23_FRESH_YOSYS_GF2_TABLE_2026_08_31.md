# Learning Milestone C23: fresh Yosys-family exact GF(2) transfer

**Date:** 2026-08-31  
**Status:** fresh Windows and unchanged Linux seven-method tables independently verified; production promotion refused

## Fresh corpus and task contract

C23 tests whether the C21 conclusions transfer to previously unused generator families from the
pinned YosysHQ/yosys-bench revision
`52ff6fa991f2ab509618d8aaad02f307aac78848`. The freezer implements exact adapters for decoder
indexing, reverse shifts, set/clear-bit operations, adder trees, low multiply and multiply-add
cones, and LFSR feedback. Every selected case has an independent scalar Boolean oracle.

The initial 48-case freeze exposed a contract error before a timing claim was made. Supports above
six can have more candidates than the 64-partition experiment bound, so a proposal arm could add a
partition outside the exhaustive reference set. The failed run was preserved as incomplete. The
task-complete v2 freeze restricts selection to supports 3-6, where the same bounded partition set is
complete for all seven methods. It contains 48 cases across all eight generator families; 18 truth
functions already present in C16/C18/C19/C7 were excluded, and 142 otherwise eligible support 7-10
cases were excluded by the task contract. Independent replay found zero source, scalar-oracle,
expression, selection, or prior-overlap mismatches.

The seven C21 implementations were then run unchanged. Every arm had to deliver the deterministic
exhaustive-best exact CM/GF(2) artifact. Proposal arms retained screened exact completion and exact
checking, and fresh BDD construction and cleanup remained charged. Each case ran for five balanced
fresh-engine, single-query rounds.

## Fresh local results

All 1,680 timed executions and 56 memory diagnostics passed exact reconstruction and artifact
identity. The independent verifier replayed 48 exhaustive oracles, checked 48 contracts, five source
fingerprints and eight artifact fingerprints, and recomputed the complete summary.

| Method | Aggregate vs exhaustive | Aggregate vs screened | Median case vs exhaustive | Minimum case vs exhaustive |
|---|---:|---:|---:|---:|
| Source packed ANF | **3.3060x** | **1.0062x** | **3.1387x** | **1.2819x** |
| Compiled screened CM | 3.2924x | 1.0021x | 3.0681x | 1.1520x |
| Screened CM | 3.2856x | 1.0000x | 3.0857x | 1.2458x |
| Source-interaction cut | 3.2637x | 0.9933x | 3.1252x | 1.1365x |
| Truth-ANF min-cut | 3.2477x | 0.9885x | 3.1187x | 1.0888x |
| Fresh ROBDD level cut | 1.1201x | 0.3409x | 1.2670x | 0.0422x |
| Exhaustive CM | 1.0000x | 0.3044x | 1.0000x | 1.0000x |

The fresh corpus confirms the main C21 result: screened CM is about 3.29x faster than exhaustive CM
for the same exact best-artifact task, and packed source ANF is the fastest fixed path by a narrow
0.62% over screened CM. Packed source ANF proposed a component cut on three cases and abstained on
45, so most of its result comes from the alternate exact representation path rather than search
pruning. Its median diagnostic Python allocation peak was 22,914 bytes.

The compiled screened leaf is slightly faster in aggregate than direct screened CM but misses the
predeclared no-regret condition on individual cases: its minimum speedup versus screened CM is
0.812x. Fresh single-query BDD remains a negative control after charged cleanup. The unattainable
per-case timing oracle is only 1.047x faster than the best fixed path before router cost. That
headroom is too small to justify another neural router or a production default change.

## Sealed second-machine package

The unchanged Linux replication is frozen as 52 files totaling 903,745 uncompressed bytes. It uses
the digest-pinned Python 3.13.15 slim-bookworm image, a hash-pinned NumPy 2.3.2 wheel, and a vendored
pure-Python `dd` 0.6.0 subset. Isolated local package validation ran both frozen commands without
`PYTHONPATH`, produced 1,680 timing rows and 56 memory rows with zero mismatches, loaded the vendored
BDD package, and kept retrieved-result size below the 16 MiB cap.

The controller is bounded to one Secure CPU pod, no replacement, 2 vCPU, at least 4 GB RAM, 12 GB
ephemeral disk, no persistent volume, one HTTPS port, a $0.25/hour rate ceiling, a $0.05 controller
cost ceiling, ten-minute cleanup, and twelve-minute reconciliation. Offline validation confirmed a
297,286-byte transport payload and exact remote command replacement. After exact user approval, the
single authorized create request returned HTTP 500. RunPod issued no pod identity; the controller
uploaded zero files, queued no replacement, and observed empty v1/v2 inventories. The independent
watchdog continued through the full twelve-minute uncertainty horizon and again found both
inventories empty with no errors or deletion attempts. The failure verifier passed every frozen,
no-upload, and reconciliation invariant. No compute cost was recorded. The Linux scientific
replication did not execute, so another create requires a new exact authorization.

The separately authorized retry preserved that failure and bound one new create to its verification
hash. Two preliminary retry preflights found all eligible Secure CPU flavors unavailable and sent no
create request. A bounded read-only availability wait then selected `cpu3c` at $0.06/hour. RunPod
created one Secure pod with 2 vCPU, 4 GB RAM, 12 GB ephemeral disk, no persistent or network volume,
and the pinned Python image. The first same-pod upload was accepted; both frozen commands completed;
the 52-file evidence was retrieved; and the pod was deleted with final v1/v2 inventories empty. The
estimated compute cost was $0.001049.

The controller initially marked the retrieved result failed because `DEPENDENCIES.json` did not list
`dd`. That inventory reports installed distributions only, while `dd` 0.6.0 was intentionally
vendored in the sealed package. The workload imported it and recorded `dd_version: 0.6.0`; the
remote verifier checked all source and artifact fingerprints; and the final host verifier checked
the vendored metadata and module manifest entries directly. Independent adjudication therefore
passes the scientific run while preserving the controller metadata false-negative in the record.

## Unchanged second-machine results

Linux reproduced all 1,680 exact timing executions and 56 memory diagnostics with zero semantic or
artifact mismatches. Relative results were close to Windows, but the narrow fixed-arm winner changed.

| Method | Windows vs exhaustive | Linux vs exhaustive | Linux vs screened |
|---|---:|---:|---:|
| Compiled screened CM | 3.2924x | **3.3467x** | **1.0030x** |
| Screened CM | 3.2856x | 3.3366x | 1.0000x |
| Source packed ANF | **3.3060x** | 3.3309x | 0.9983x |
| Source-interaction cut | 3.2637x | 3.3082x | 0.9915x |
| Truth-ANF min-cut | 3.2477x | 3.2889x | 0.9857x |
| Fresh ROBDD level cut | 1.1201x | 1.5342x | 0.4598x |
| Exhaustive CM | 1.0000x | 1.0000x | 0.2997x |

The robust cross-machine conclusion is that screened CM materially beats exhaustive CM for the
same exact task: 3.286x on Windows and 3.337x on Linux. The 0.62% Windows advantage for packed
source ANF reversed to a 0.17% Linux disadvantage, and compiled screened CM led Linux by only 0.30%
over screened CM. Linux per-case oracle headroom was just 1.0049x, compared with 1.0470x on Windows.
These narrow, machine-sensitive margins provide even less support for training a router.

## Decision and next work

C23 is fresh and second-machine confirmation for the unchanged C21 exact methods. It strengthens the
screened-CM result while showing that the close packed-source/compiled ordering is machine-specific.
The small oracle headroom and individual arm regressions keep production promotion false. The
strongest implementation follow-up is a C24 end-to-end evaluation of the C22
dispatcher on the sealed C23 cases: advice on/off, refusal and malformed/OOD fallback, bounded
shadow comparison, exact artifact identity, and the full wrapper cost must all be charged.

## Evidence

- Source inventory: `docs/recognition/c23_yosys_fresh_source_inventory.json`
- Task-complete dataset: `docs/recognition/c23_yosys_fresh_gf2_dataset_v2.json`
- Dataset replay: `docs/recognition/c23_yosys_fresh_gf2_dataset_v2_verification.json`
- Failed incomplete-contract attempt: `docs/recognition/runs/c23-yosys-fresh-gf2-table-windows-20260831-001`
- Verified local run: `docs/recognition/runs/c23-yosys-fresh-gf2-table-windows-20260831-002`
- Local independent verification: `docs/recognition/runs/c23-yosys-fresh-gf2-table-windows-20260831-002/independent_verification.json`
- Linux manifest: `docs/recognition/c23_linux_confirmation/c23_linux_upload_manifest.json`
- Linux protocol: `docs/recognition/c23_linux_confirmation/C23_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_08_31.md`
- Isolated package validation: `docs/recognition/c23_linux_confirmation/C23_PACKAGE_LOCAL_VALIDATION_20260831.json`
- Linux controller: `docs/recognition/c23_linux_confirmation/runpod_c23_linux_controller.py`
- Linux final verifier: `docs/recognition/c23_linux_confirmation/verify_runpod_c23_attempt.py`
- Failed create attempt: `docs/recognition/c23_linux_confirmation/runpod-c23-linux-execute-001`
- Failed-attempt verification: `docs/recognition/c23_linux_confirmation/RUNPOD_C23_FAILED_ATTEMPT_VERIFICATION_20260831.json`
- Successful retry evidence: `docs/recognition/c23_linux_confirmation/runpod-c23-linux-execute-002c`
- Retry final verification: `docs/recognition/c23_linux_confirmation/RUNPOD_C23_RETRY_002C_FINAL_VERIFICATION_20260831.json`
- Cross-machine comparison: `docs/recognition/c23_linux_confirmation/C23_LOCAL_LINUX_COMPARISON_20260831.json`
