# Exact native batch successor — functional implementation note

Date: 2026-09-10

## Scope

The completed two-host q64 learning cohort is a verified scientific no-go for
the frozen selector contract. It remains diagnostic-only and was not reused to
fit a policy, change its labels, or make a new performance claim.

The cost ledger nevertheless isolates an exact-side opportunity. The fixed
`native_fused_slots` backend performs 64 separate Python-to-native evaluation
calls per case. Native evaluation accounts for about 41% of its summed staged
time on the Windows host and 45% on the Linux host; binding accounts for a
further 18% and 17%, respectively.

## Implemented successor

The successor keeps all frozen source and artifacts unchanged:

- `native/cm_fused_slots_batch/fused_slot_executor_batch.c` includes the
  frozen scalar kernel and adds an ABI-v1 batch entry point.
- `cmbench/comparative/gf2_native_slot_batch.py` prepares one contiguous
  binding matrix, groups queries by residual width, crosses the FFI boundary
  once per width, reuses native workspaces, and restores original output order.
- `scripts/build_cm_fused_slots_batch.py` builds only into the separate
  `build/cm_fused_slots_batch` development directory.

This is an execution change, not a learned router: every query uses the same
exact native kernel and preserves canonical residual-variable order.

Functional validation built the successor DLL locally and checked all 1,152
restrictions in the exposed C36 dataset. Batched output, scalar native output,
and independently restricted full-truth output agreed exactly, including
mixed residual widths.

## Evidence boundary

The implementation is eligible only for functional exactness testing now.
Any speedup, gate, or production statement requires a genuinely new,
independently frozen prospective timing workload. No benchmark, model training,
prospective learning case, production routing change, commit, publish, or
deployment is part of this work.
