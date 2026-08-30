# CRSE Learning Milestone C12: adaptive exact representation dispatch

Date: 2026-08-30  
Status: **complete local and Linux confirmation; platform-sensitive profitability**  
Production promotion: **guarded candidate; not an unconditional default**

## What was implemented

This sequence tested deterministic routing among three exact decomposition
representations: sparse set ANF, cached packed source ANF, and direct bitset
truth-vector ANF. No neural model was trained. The dispatcher selects an exact
algorithm; an independent truth computation still verifies every accepted
partition.

Four successive designs were retained rather than hiding negative results:

1. **C9 static analytic tree.** A depth-two source-only tree was fitted on C6
   train/validation timing and serialized before C6 held-out and C7 evaluation.
2. **C10 guarded restart.** Sparse set ANF stopped before a validation-frozen
   cumulative product budget and restarted exactly with cached packed ANF.
3. **C11 one-pass conversion.** The set prefix was converted in place to packed
   coefficient bits, so no DAG prefix was evaluated twice.
4. **C12 robust policy.** The largest budget within 1% of the C6-validation
   minimum was frozen: 4,096 product pairs. The fast set path removed diagnostic
   scans, and the policy was confirmed with 15 balanced method-order repetitions.

## Fresh source controls

C11 and C12 each contain 40 Yosys-derived cases, balanced 10/10 by label in two
splits. Each has 20 unused raw generator outputs and 20 explicitly identified
disjoint-XOR compositions of generator outputs. The compositions provide fresh
positive decomposition boundaries; they are not described as raw single-output
circuits. C12 excludes all C7 and C11 semantic identities and alpha-renamed
structures. Its audit reports zero prior semantic overlap and zero prior alpha
overlap.

## Results

All fixed, staged, and adaptive methods reproduced every exact label and
canonical partition. Independent replay verified 940 method/case rows and
14,100 timing samples with zero semantic mismatches.

| Design / split | Speedup over best fixed | Relevant result |
| --- | ---: | --- |
| C9 static tree, C6 confirmatory | 0.722x | Static routing failed to transfer |
| C9 static tree, C7 A / B | 0.892x / 0.950x | Exact but not profitable |
| C10 restart, C6 confirmatory | 0.959x | p95 was 15.27x faster than unguarded set ANF |
| C10 restart, C7 A / B | 0.783x / 0.849x | Restart cost dominated sparse cases |
| C11 one pass, fresh A / B | 0.935x / 0.933x | Beat restart by 1.084x / 1.022x |
| C12 robust, fresh A / B | 0.968x / 0.925x | Failed the 5% no-regret gate on B |
| C12 Linux replay, fresh A / B | 0.988x / 0.969x | Passed the predefined 5% second-machine gate |
| C12 robust, C6 confirmatory development | 0.926x | p95 was 15.58x faster than unguarded set ANF |

The robust C12 policy never switched on its 40 fresh cases. Its loss there is
the small product-budget guard overhead, not packed conversion. On the dense C6
confirmatory slice it switched 13 of 36 cases and retained the intended tail
protection. The policy therefore solves the catastrophic-tail problem but is
not yet a universal production default. The Linux replay put both sparse C12
splits inside the allowed 5% regret band, while the original Windows B timing
remained outside it. That difference is evidence of platform sensitivity near
the gate, not a semantic difference.

## Runpod status

A 14-file, 355,934-byte package was frozen for a second-machine C12 timing run:
Python 3.13.15, NumPy 2.3.2, one Secure CPU pod, two vCPU, at least 4 GB RAM,
12 GB ephemeral disk, no persistent volume, no replacement, a $0.25/hour rate
ceiling, and a controller-enforced $0.05 total ceiling. After payload-specific
authorization, one matching pod was created at $0.06/hour. Its health endpoint
became ready, but `POST /payload` returned HTTP 404. The controller uploaded zero
files, made no replacement attempt, deleted the pod after 33.216 seconds, and
recorded empty v1 and v2 inventories. No result was retrieved. Estimated cost
was $0.000554. This is a safely reconciled transport failure, not Linux timing
evidence.

A separately authorized same-pod retry then proved the transport correction:
after one proxy 404, the second payload request was accepted and all 14 files
were uploaded. The remote workload stopped before measurement because the
package omitted the transitive import `cmbench/output_budget.py`; the next import
would also have required `cmbench/recognition/features.py`. The pod was deleted
after 39.505 seconds with empty inventories. Estimated cost was $0.000658.

The corrected package contains those two additions: **16 files and 368,532
bytes**. The complete 2,560-measurement workload first passed from an isolated
local directory containing only those 16 files, with 160 per-case rows, zero
semantic mismatches, and no import or stderr output.

After exact payload-specific authorization, the fail-closed v6 controller
created one Secure CPU pod at $0.06/hour. Two health observations passed and the
first payload request was accepted. Python 3.13.15 and NumPy 2.3.2 completed all
2,560 measurements with zero semantic mismatches. Linux measured 0.988x and
0.969x over the best fixed arm on sealed A and B, respectively, so both passed
the predefined 1/1.05 no-material-regret threshold. The controller retrieved
62,053 bytes of evidence and deleted the pod after 44.159 seconds. Controller
and watchdog inventories were empty. Estimated cost was $0.000736; total cost
across all three reconciled C12 cloud attempts was approximately $0.001948.

Independent local verification replayed all 160 Linux method/case semantics,
recomputed every per-case median and aggregate from 2,560 raw timing rows,
verified the package, authorization, controller, and evidence hashes, and
confirmed the positive second-machine gate.

## Decision

Do not enable the adaptive path as an unconditional production default. The
second-machine gate passed, so it is now a justified guarded candidate for
workloads that value tail protection. Keep the exact set, packed, and bitset
implementations as fallbacks. The next implementation should place a
near-zero-overhead tail sentinel inside the existing set kernel or use a
task-level policy to enable the guard only where tail latency matters, followed
by a shadow comparison that records platform-specific regret.

## Evidence

- `docs/recognition/runs/exact-representation-dispatcher-20260830-002`
- `docs/recognition/runs/staged-exact-dispatcher-20260830-001`
- `docs/recognition/runs/adaptive-exact-dispatcher-20260830-001`
- `docs/recognition/runs/adaptive-exact-dispatcher-robust-20260830-002`
- `docs/recognition/verification/adaptive-exact-dispatcher-robust-20260830-002.json`
- `docs/recognition/c12_linux_confirmation/c12_linux_upload_manifest.json`
- `docs/recognition/c12_linux_confirmation/C12_SECOND_MACHINE_TIMING_PROTOCOL_2026_08_30.md`
- `docs/recognition/c12_linux_confirmation/RUNPOD_C12_LINUX_ATTEMPT_FINAL_VERIFICATION_20260830.json`
- `docs/recognition/c12_linux_confirmation/RUNPOD_C12_LINUX_RETRY_FINAL_VERIFICATION_20260830.json`
- `docs/recognition/c12_linux_confirmation/c12_linux_upload_manifest_v2.json`
- `docs/recognition/c12_linux_confirmation/C12_PACKAGE_V2_LOCAL_VALIDATION_20260830.json`
- `docs/recognition/c12_linux_confirmation/RUNPOD_C12_LINUX_PACKAGE_V2_FINAL_VERIFICATION_20260830.json`
- `docs/recognition/c12_linux_confirmation/runpod-c12-linux-execute-006`
