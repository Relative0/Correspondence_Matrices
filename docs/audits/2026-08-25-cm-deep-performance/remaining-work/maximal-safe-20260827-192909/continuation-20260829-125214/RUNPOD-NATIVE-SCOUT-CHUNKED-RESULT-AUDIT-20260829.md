# Runpod native-scout chunked-retry result audit

Date: 2026-08-29  
Attempt: `http-native-scout-chunked-retry-execute-001`  
Pod: `mljd0t0sb3h1u3`

## Result

The separately authorized chunked retry issued exactly one create request.
Runpod returned HTTP 201, and the actual pod matched the approved Secure
`cpu3c`, 2-vCPU, 4-GB, `$0.06/hour`, pinned-image, 12-GB-container,
zero-volume, and no-network-volume identity.

The bounded transport succeeded. Both token-gated health endpoints became
ready, all eleven 256-KiB-or-smaller chunks were acknowledged at exact offsets,
the complete 2,831,254-byte payload matched SHA-256
`c4845e966e3dcd6fd710e4984ed31f1fce45897111cbda88e6203fa8d25cfc68`,
and the worker-start request succeeded.

The remote focused tests then stopped with
`ModuleNotFoundError: No module named 'cmbench.backends'`. The 30-file manifest
omitted `cmbench/backends/__init__.py` and
`cmbench/backends/bitset_engine.py`; a complete local closure audit subsequently
found two other direct and three transitive local dependencies. P5 and the
native readiness scout did not start, so this attempt establishes transport
readiness but no CaDiCaL, CUDD, d4, or performance result.

## Evidence interpretation

The retrieved JUnit document contains 60 testcase elements, seven failed.
Pytest suite metadata reports 180 tests and 22 failures because subtest outcomes
are expanded in the suite totals. All seven failed testcase elements carry the
same missing-package cause. The frozen remote wrapper then failed to find the
unstarted P5 summary, and the frozen controller similarly raised
`FileNotFoundError` while loading that artifact. Those are secondary evidence
handling failures; the focused-test import failure is the primary workload
failure.

The saved runtime shows two allowed CPUs through affinity `[99, 227]`. Its
256 host-visible logical CPUs are a host count, not the pod allocation. The
frozen wrapper did not record source-after identity after the earlier failure.

## Cleanup and cost reconciliation

The controller performed ownership-only DELETE, which returned HTTP 204, after
about 72.5 seconds. The watchdog independently acknowledged controller cleanup
without errors. At 10:59:20 UTC:

- v1 and v2 inventories were empty;
- both APIs returned 404 for this pod and all six earlier campaign pod IDs;
- controller and watchdog host-awake guards were released and had exited;
- provider billing contained no row for this pod yet and remained subject to
  lag;
- the conservative attempt bound was `$0.001409574` and the aggregate
  attributable campaign bound was `$0.002574206`, within the `$0.10` and
  `$0.20` caps;
- the separate billing row for pod `ek7697wrnxuawo` was not attributed to this
  campaign.

The final receipt is
`HTTP-NATIVE-SCOUT-CHUNKED-FINAL-VERIFICATION-20260829-105930-771906.json`.
It records `attempt_safely_reconciled: true`, `authorization_consumed: true`,
`chunked_transport_verified: true`, `workload_completed: false`, and
`owned_pods_absent_verified: true`.

## Further-run boundary

No replacement is authorized or queued. The chunked-retry authorization is
consumed. A dependency-closed package and hardened evidence path are prepared
under `RUNPOD-NATIVE-SCOUT-CLOSURE-RETRY-PROPOSAL-20260829.md`; any create from
that proposal requires separate explicit authorization.

