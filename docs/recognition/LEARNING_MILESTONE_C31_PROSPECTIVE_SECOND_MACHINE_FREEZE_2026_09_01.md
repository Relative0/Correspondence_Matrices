# Learning milestone C31: prospective prepared-policy replication freeze

**Date:** 2026-09-01  
**Status:** unchanged second-machine replication verified; eligible for separate shadow review
**Training or policy refit:** none  
**Shadow/production promotion:** false / false

## Purpose

C30 removed the per-session policy-validation overhead and passed its local q8 point
gate. C31 freezes the exact implementation and decision rule before collecting any new
second-machine timing. It does not change the dataset, policies, exact query path,
counterbalanced schedule, preparation-charge accounting, or fallback behavior.

## Frozen experiment

The C31 payload contains 71 files and 1,153,868 bytes. It runs the unchanged C30 seed and
16-block schedule over n=3/4/5/6 with eight queries per batch. The required result remains
128 measurement batches, 64 paired batches, 1,024 timed exact GF(2) queries, 512 replayed
verified contexts, six fail-closed controls, zero semantic or artifact mismatches, and a
fully conserved lifecycle-preparation charge.

The package contains source, sealed policy and dataset JSON, the two required C29 evidence
files, and vendored pure-Python dependencies. It excludes local C30 measurements,
credentials, generated video/media, archives, compiled BDD backends, source checkouts, and
unrelated worktree files.

## Prospective adjudication

Every physical-machine execution must pass both point floors:

- aggregate charged speedup at least 1.00x; and
- minimum-width charged speedup at least 0.90x.

It must also pass the same floors with a distribution-free one-sided median lower bound
over the 16 prespecified counterbalanced blocks. The rule uses the fifth ordered paired
speedup. Its exact binomial coverage is 63,019 / 65,536, or 96.1594%, which exceeds the
requested 95% confidence level. The sampling unit, rank, thresholds, local C30 hashes, and
cross-machine requirement were frozen before second-machine timing.

Applying this rule to the already existing C30 Windows evidence gives:

| Metric | Point estimate | Paired-block median lower bound | Floor | Pass |
|---|---:|---:|---:|:---:|
| Aggregate charged speedup | 1.0360x | 1.0241x | 1.00x | yes |
| Minimum-width charged speedup | 1.0002x | 0.9555x | 0.90x | yes |

This local check leaves the second-machine result scientifically open. The cross-machine
adjudication will fail closed if either execution misses either point or lower-bound gate.
A pass only makes the frozen candidate eligible for a separate shadow review; it does not
automatically authorize shadow or production use.

## Isolated package validation

The exact 71-file package was copied into an isolated directory with no `PYTHONPATH` and
executed using the project virtual environment. The packaged C30 runner and independent
verifier both returned zero. Validation observed all required counts, controls, exactness,
charge conservation, vendored `dd` 0.6.0 isolation, and the C31 rank-5 adjudicator. The run
took 6.60 seconds and produced 629,069 bytes of bounded evidence.

## RunPod execution

The first authorized controller invocation stopped locally before the create request. Its
C31 ownership name did not match the inherited safety watchdog's historical namespace.
The failure was reconciled with both RunPod inventories empty, zero uploaded files, no pod,
and no compute cost, so the one authorized create remained unused. A transport-only retry
used the watchdog's established ownership namespace; the scientific package, protocol,
runtime, command, and gates did not change.

The one create request then started a Secure `cpu3c` pod backed by an AMD EPYC 9655 at
$0.06/hour. The pod had 2 vCPU, 4 GB RAM, 12 GB ephemeral disk, no persistent or network
volume, and the pinned Python 3.13.15 image. After two consecutive HTTPS health checks,
the controller uploaded the 71-file payload once. The unchanged experiment and on-pod
verifier completed, bounded evidence was retrieved, and a post-retrieval verifier produced
a byte-identical verification record. The controller deleted the pod after 47.20 seconds;
both final inventories were empty. Estimated compute cost was $0.000787.

## Cross-machine result

The Linux execution reproduced 128 measurement batches, 64 exact pairs, 1,024 timed
queries, 512 replayed verified contexts, and six fail-closed controls with zero semantic
or artifact mismatches. Its charged point estimates were 1.0385x aggregate and 1.0154x at
the minimum width. Its rank-5 paired-block lower bounds were 1.0334x aggregate and 0.9764x
at the minimum width.

Applying the frozen adjudicator to the original Windows C30 execution and this physical
Linux execution gives the following worst-machine floors:

| Cross-machine floor | Observed | Required | Pass |
|---|---:|---:|:---:|
| Aggregate point estimate | 1.0360x | 1.00x | yes |
| Minimum-width point estimate | 1.0002x | 0.90x | yes |
| Aggregate paired median lower bound | 1.0241x | 1.00x | yes |
| Minimum-width paired median lower bound | 0.9555x | 0.90x | yes |

The prospective replication is admissible and the candidate is eligible for a separate
shadow review. C31 did not authorize or perform shadow promotion, production promotion,
training, policy refitting, or a production write.

## Evidence

- Manifest: `c31_linux_confirmation/c31_linux_upload_manifest.json`
- Protocol: `c31_linux_confirmation/C31_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_09_01.md`
- Prospective contract: `c31_prepared_policy_replication_contract.json`
- Local package validation:
  `c31_linux_confirmation/C31_PACKAGE_LOCAL_VALIDATION_20260901.json`
- Local prospective adjudication:
  `c31_linux_confirmation/C31_LOCAL_PROSPECTIVE_ADJUDICATION_20260901.json`
- Initial exact request and authorization:
  `c31_linux_confirmation/RUNPOD_C31_AUTHORIZATION_REQUEST_20260901.json`
- Initial no-create reconciliation:
  `c31_linux_confirmation/C31_INITIAL_NO_CREATE_RECONCILIATION_20260901.json`
- Transport retry request and authorization:
  `c31_linux_confirmation/RUNPOD_C31_TRANSPORT_RETRY_001_REQUEST_20260901.json`
- Final transport and post-retrieval verification:
  `c31_linux_confirmation/RUNPOD_C31_FINAL_VERIFICATION_20260901.json`
- Frozen cross-machine adjudication:
  `c31_linux_confirmation/C31_CROSS_MACHINE_ADJUDICATION_20260901.json`
- Adjudicator: `../../cmbench/comparative/gf2_prepared_policy_adjudication.py`
- Corrected transport controller:
  `c31_linux_confirmation/runpod_c31_linux_controller_retry_001.py`
