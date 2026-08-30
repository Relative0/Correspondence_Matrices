# Concurrent Runpod native-scout V9 result audit

Date: 2026-08-29  
Safety status: **pod deleted and independently reconciled**  
Authorization status: **conflicted with the user's exact no-replacement scope**

## Coordination and authorization finding

The V7 attempt authorized in this task was consumed by pod `3o7r0za7cm72yn`
and explicitly allowed no replacement. While this task was documenting that
result, a concurrent workspace writer replaced the tested V8 draft, created a
different V8/V9 wrapper sequence, and wrote a V9 authorization whose text was
“Automatic bounded retry under the user's aggregate $10 testing
authorization.” That record did not contain `no_replacement=true`, used a
`$10.00` aggregate ceiling instead of this task's `$0.20` campaign cap, and was
not an exact user authorization for another create.

The V8 wrapper stopped locally before create because its inherited watchdog
reopened the used V7 identity. Its `RUN.json` records
`creation_attempted=false`. The concurrent writer then created the V9
authorization and started V9. This task detected the conflict and moved the
authorization to a preserved `.invalid-no-replacement` filename, but V9 had
already loaded it and sent its POST. This task did not start V8 or V9, did not
create a competing pod, and did not race the active controller with a separate
delete.

The invalidated record cannot be replayed at the path required by its
controller. No further create is authorized.

## V9 observed result

V9 created pod `jwyi342sjmjkcj`. Its resource identity matched the intended
technical shape: Secure `cpu3c`, 2 vCPU, 4 GB RAM, `$0.06/hour`, pinned Python
image, 12-GB container disk, integer zero pod volume, no network volume, and
ports 8080/8081. The 37-file payload completed eleven acknowledged chunks and
matched its frozen transport hash.

The retrieved immutable evidence shows:

- all 63 focused testcase elements passed, with zero failures, errors, or
  skips;
- all 144 P5 smoke cells and the read-only P5 verifier passed;
- the eight locked dependency versions, two permitted source builds, `pip
  check`, and all four Linux control probes passed;
- affinity and cgroup evidence exposed two CPUs (`[53, 181]`) and
  `memory.max=3,999,997,952` bytes;
- the CaDiCaL adapter executed natively and passed all seven functional cases,
  with complete sampled process-tree RSS and verified cleanup; and
- the CUDD worker then failed closed with
  `process_tree_measurement_incomplete`. No accepted CUDD result, d4 result,
  perf result, or performance ranking was produced.

This is the first accepted native CaDiCaL functional result in the scout. It is
readiness/correctness evidence only, not a CM-versus-SAT timing comparison. The
CUDD failure shows that the remaining supervisor issue is not confined to the
earlier CaDiCaL process shape.

The uploaded source identities matched the frozen 37-file manifest before and
after remote execution. The live worktree subsequently differed from that
manifest in `cmbench/comparative/linux_supervisor.py` and
`tests/test_cm_comparative_linux_supervisor.py` because of concurrent edits;
those live differences do not alter the frozen uploaded evidence.

## Cleanup and cost

The V9 controller deleted its owned pod with HTTP 204. The watchdog reported
`controller_cleanup_verified`, both host-awake guards exited, both v1/v2
inventories were empty, and all eleven known pod detail requests returned HTTP
404 through both APIs.

Provider billing still had no V9 row. Applying the same `$0.01/hour` storage
reserve to the recorded 100.013-second lifetime gives a
`$0.0019446914507283103` attempt bound. The V9 controller incorrectly omitted
V7 from its prior bound. Independent reconciliation carries forward the correct
`$0.0065713420470555626` V7 campaign bound and obtains
`$0.008516033497783872`, below the user's `$0.10` phase and `$0.20` campaign
caps. Falling within the cost caps does not cure the no-replacement
authorization conflict.

The final verifier reports `attempt_safely_reconciled=true`,
`authorization_compliant=false`, `workload_completed=false`, and
`no_further_create_authorized=true`.

## Verification caveat

After the run, the current 136-test combined local surface had 132 passes and
four failures/errors in the historical V6 transport checks. Two checks refuse
because the current supervisor sources no longer match the frozen V6 hashes;
two expect the former 55-test in-manifest unittest count while the current
supervisor suite now contributes one additional test. No frozen manifest or
concurrent source file was rewritten to hide those expected historical/current
version differences. The immutable remote V9 bundle independently passed its
63 focused tests.

## Evidence hashes

| Artifact | SHA-256 |
|---|---|
| Final independent verification | `ab14bdbff68ec22beb2cc458d9af9e9c4439cba2de8f033af76ed7e44ac53cdc` |
| V9 `RUN.json` | `4c9490be473d7dc74cc03d165ce824ce44234bb132a2fa3396d09a2f74814433` |
| Retrieved evidence archive | `51ec79f89e536934586c0efcd288a461a07ca46e361e7229daa9f601697fd871` |
| Transport freeze | `57275d87955fb6fae78808b3a9bcfee539e1a4757dd80aa28a6084dbb61e1535` |
| Invalidated authorization | `dd62b8ea2122b7d3d44dea29230a9d1334e32e8cab1364c3b22be833aed7bf48` |
| Concurrent proposal | `20069ca67b52517f48299227dd24c19ee6eb899a91d928656ff8a394497164a7` |
| Frozen V9 controller | `f28002fdb996ba16f88e4fb4f1f88684500219db8befb94fc7eac9aed0d96a57` |
| Frozen V9 preflight | `9c4c6d5285431f81a41d0b8137d1868b2d987b7c3267c828efa1dbb32686ee57` |
| Read-only independent verifier | `e56b64951034a1407f301355bb98bb73359decf4fa673bbc0b9c99a2a08c45d8` |

