# Learning milestone C31: prospective prepared-policy replication freeze

**Date:** 2026-09-01  
**Status:** exact package locally verified; second-machine upload authorization pending  
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

## RunPod boundary

No RunPod resource was created and no package was uploaded during the freeze. The exact
request is recorded with authorization false and zero resource writes. If approved, the
controller permits one Secure CPU create, no replacement, 2 vCPU, at least 4 GB RAM,
12 GB ephemeral disk, no persistent/network volume, a $0.25/hour rate ceiling, a $0.05
controller cost ceiling, 16 MiB retrieval, ten-minute cleanup, and twelve-minute
reconciliation. Credential values are neither recorded nor uploaded.

## Evidence

- Manifest: `c31_linux_confirmation/c31_linux_upload_manifest.json`
- Protocol: `c31_linux_confirmation/C31_SECOND_MACHINE_REPLICATION_PROTOCOL_2026_09_01.md`
- Prospective contract: `c31_prepared_policy_replication_contract.json`
- Local package validation:
  `c31_linux_confirmation/C31_PACKAGE_LOCAL_VALIDATION_20260901.json`
- Local prospective adjudication:
  `c31_linux_confirmation/C31_LOCAL_PROSPECTIVE_ADJUDICATION_20260901.json`
- Exact request, still unauthorized:
  `c31_linux_confirmation/RUNPOD_C31_AUTHORIZATION_REQUEST_20260901.json`
- Adjudicator: `../../cmbench/comparative/gf2_prepared_policy_adjudication.py`
- Controller: `c31_linux_confirmation/runpod_c31_linux_controller.py`
