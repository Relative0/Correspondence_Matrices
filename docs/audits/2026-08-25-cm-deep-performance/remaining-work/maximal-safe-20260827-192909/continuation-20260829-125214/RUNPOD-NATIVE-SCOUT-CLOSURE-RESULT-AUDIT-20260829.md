# Runpod dependency-closed native-scout result audit

Date: 2026-08-29  
Attempt: `http-native-scout-closure-retry-execute-001`  
Pod: `pes90ta8wgi2g6`

## Result

The separately authorized attempt issued exactly one create request. Runpod
returned HTTP 201, and the actual pod matched the approved Secure `cpu3c`,
2-vCPU, 4-GB, `$0.06/hour`, pinned-image, 12-GB-container, zero-volume, and
no-network-volume identity.

The 2,849,933-byte payload completed in eleven bounded chunks, matched its
frozen SHA-256, and the worker started. All 60 focused testcase elements passed
with zero failures, errors, or skips. Pytest suite metadata recorded 180 tests
because of subtests. All 37 source files matched before and after execution.

P5 then exited with code 2 before running. Its saved diagnostic is exact:
`cm_comparative_smoke.py run` requires `--output`, while the wrapper supplied
`--output-dir`. No P5 summary was created and the native CaDiCaL/CUDD/d4 scout
did not start. This attempt therefore establishes dependency closure and the
focused Linux test result, but no native readiness or performance result.

## Evidence handling

The hardened wrapper independently retained JUnit metadata, actual testcase
counts, P5 command/stderr, runtime identity, source-before, source-after, and a
bounded 18-file evidence archive. The controller stored that partial evidence
before reporting `remote workload reported failure`; no later missing artifact
masked the primary CLI failure.

The runtime affinity was `[87, 215]`, representing two allowed CPUs. The 256
host-visible logical CPUs are a host count, not the pod allocation.

## Cleanup and cost reconciliation

The controller performed ownership-only DELETE, which returned HTTP 204, after
about 88.2 seconds. The watchdog independently acknowledged controller cleanup
without errors. At 11:24:29 UTC:

- v1 and v2 inventories were empty;
- both APIs returned 404 for this pod and all seven earlier campaign pod IDs;
- controller and watchdog host-awake guards were released and had exited;
- provider billing contained no row for this pod yet and remained subject to
  lag;
- the conservative attempt bound was `$0.001715194` and the attributable
  campaign bound was `$0.004289399`, within the `$0.10` and `$0.20` caps;
- the separate billing row for pod `ek7697wrnxuawo` was not attributed to this
  campaign.

The final receipt is
`HTTP-NATIVE-SCOUT-CLOSURE-FINAL-VERIFICATION-20260829-112440-495599.json`.
It records `attempt_safely_reconciled: true`, `authorization_consumed: true`,
`workload_completed: false`, `failure_evidence_preserved: true`, and
`owned_pods_absent_verified: true`.

## Further-run boundary

No replacement is authorized or queued. The dependency-closed authorization is
consumed. The CLI-corrected package is separately proposed in
`RUNPOD-NATIVE-SCOUT-P5-CLI-RETRY-PROPOSAL-20260829.md`; any create from it
requires separate explicit authorization.

