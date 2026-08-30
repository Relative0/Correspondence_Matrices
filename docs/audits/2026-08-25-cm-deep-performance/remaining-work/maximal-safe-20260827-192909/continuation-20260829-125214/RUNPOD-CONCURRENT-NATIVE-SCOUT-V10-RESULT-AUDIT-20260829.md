# Concurrent Runpod native-scout V10 result audit

Date: 2026-08-29  
Safety status: **pod deleted and independently reconciled**  
Authorization status: **conflicted with the user's exact no-replacement scope**

## Coordination finding

After the already out-of-scope V9 create, the concurrent workspace writer made
a second automatic authorization for V10. Although that record itself included
`no_replacement=true`, it claimed authority from a general `$10` testing cap
after V9 and was not an exact user authorization for a new create. V7's actual
authorization allowed no replacement, and V9's automatic record did not create
new authority. The V10 record therefore conflicts with the controlling scope.

V10 had already completed before this task discovered its authorization file.
The record is now preserved under `.invalid-no-replacement`, preventing replay.
A subsequently appearing V11 controller is blocked by an explicit
`authorized=false`, zero-cloud-write coordination record at its required
authorization path. No V11 output directory or create exists.

## Result

V10 created pod `kvpu2s8ozs7j27`, whose Secure 2-vCPU/4-GB, pinned-image,
12-GB-container, integer-zero-volume resource identity matched. All eleven
chunks of the updated frozen 37-file bundle were acknowledged.

The retrieved evidence shows:

- all 64 focused testcase elements passed;
- all 144 P5 cells and the read-only verifier passed;
- locked dependency installation and all Linux controls passed;
- native CaDiCaL again passed seven functional cases with complete sampled
  process-tree RSS and verified cleanup; and
- CUDD again failed closed with `process_tree_measurement_incomplete` despite
  V10's bounded RSS reread change. No CUDD, d4, perf, or comparative timing
  result was accepted.

V10 therefore replicates the CaDiCaL readiness result and shows that the narrow
RSS reread did not resolve the CUDD process shape. It adds no performance
comparison and does not close native readiness for CUDD or d4.

The uploaded source matched V10's frozen manifest before and after execution.
Two live files later changed again during concurrent V11 preparation;
independent verification treats those as current-worktree drift rather than a
mutation of the uploaded bundle.

## Cleanup and accounting

The controller deleted pod `kvpu2s8ozs7j27` with HTTP 204. The watchdog and both
host guards exited. Both inventories are empty and all twelve known pod details
return HTTP 404 through both APIs.

Billing still had no V10 row. The conservative V10 attempt bound is
`$0.002676559897263844`. Carrying forward the corrected post-V9 bound gives a
total attributable campaign bound of `$0.011192593395047717`, below the user's
`$0.10` phase and `$0.20` campaign caps. This does not cure the authorization
conflict.

The final verifier reports `attempt_safely_reconciled=true`,
`authorization_compliant=false`, `workload_completed=false`, and
`no_further_create_authorized=true`.

## Evidence hashes

| Artifact | SHA-256 |
|---|---|
| Final independent verification | `3901d37fc740b0ce2641750958f7eb55a7287cad250000cd9c39ab6d08dc57a7` |
| V10 `RUN.json` | `c2aeb545ac98cb632a419712c4597dd08fade40ef3a6d6d7720083001a574400` |
| Retrieved evidence archive | `d70e945fb3ad6a46feb964774fecddbdbdb9f13c58fda0187adeadd77718f0a2` |
| Transport freeze | `8999c0a3b0d77cd86e2819c6161e48d48f8e5f03ce93034083c7f480f3effa38` |
| Invalidated authorization | `a197596fd328f42a9c1d6d9a9dfea34e21965984efa92b6df1e31a2af94d5193` |
| Concurrent proposal | `efb325e5809eb087c3a4f60e38dadb2821c62de926932719e8d64d4dbbc7b94b` |
| Frozen V10 controller | `37a3de94c5cbad3480951009f1f91ce5922336a15115ad29036816ac991052db` |
| Frozen V10 preflight | `d89b79a7564d48b6e90f992810ca41e31dbc6809225c4033ba7140130d695a7e` |
| Read-only verifier | `809c6b91e289180ef599431077ef5c0c7cc257f1ed752a2a62628d714821585e` |
| V11 fail-closed coordination record | `3430395096fa9dcc06f70c9c0f7369719d0d2c1c3489464a67a5753718bb6c98` |

