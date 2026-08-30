# Runpod native-scout attempt result audit

Date: 2026-08-29  
Attempt: `http-native-scout-execute-001`  
Pod: `84442bdg4m47x8`

## Result

The one authorized create request was consumed. Runpod returned HTTP 201 and
the pod matched the approved resource identity:

- Secure CPU placement verified through the v2 detail response;
- `cpu3c`, 2 vCPUs, 4 GB RAM, and `$0.06/hour`;
- pinned Python 3.13.15 slim-bookworm image;
- 12 GB container disk, integer zero pod volume, and no network volume;
- only the two token-gated HTTP ports requested by the frozen bootstrap.

The controller then failed locally with `KeyError` before source transfer.
`uploaded_source_files` is zero, and no focused test, P5 cell, Linux control, or
native tool ran. There is therefore no correctness, compatibility, refusal, or
performance result from this attempt.

## Root cause

The controller called:

`validate_pod(..., ready["prior_cost_bound_usd"])`

The new preflight returned the prior comparative cost inside its budget/prior
attempt structures but omitted that top-level interface field. Component tests
covered the preflight budget and resource validator independently, so the
return-value mismatch was not exercised before create.

The frozen V1 controller and preflight are preserved unchanged. The corrected
V2 preflight publishes the top-level value, carries forward the larger of
observed and conservatively estimated first-attempt cost, and now has an
integration regression test that passes the real preflight result into the
resource validator.

## Cleanup and cost reconciliation

The controller requested abort and performed ownership-only DELETE, which
returned HTTP 204. The watchdog independently acknowledged controller cleanup
without errors. At 09:52:52 UTC:

- v1 and v2 inventories were empty;
- v1 and v2 detail requests returned 404 for this pod and all four prior pods;
- controller and watchdog host-awake guards were released and their processes
  had exited;
- the upload count remained zero;
- provider billing contained no row for this pod yet and was marked subject to
  lag;
- the conservative seven-second cost bound, including the storage-rate reserve,
  was `$0.000147912`, within the `$0.10` phase and `$0.20` campaign caps.

The independent receipt is
`HTTP-NATIVE-SCOUT-FINAL-VERIFICATION-20260829-095302-117832.json`; it records
`attempt_safely_reconciled: true`, `workload_completed: false`, and
`authorization_consumed: true`.

## Retry boundary

No retry is authorized or queued. The corrected transport refuses to run while
`HTTP-NATIVE-SCOUT-RETRY-AUTHORIZED-20260829.json` is absent. A distinct bounded
proposal is recorded in
`RUNPOD-NATIVE-SCOUT-RETRY-AMENDMENT-PROPOSAL-20260829.md` for review and, only
if desired, separate authorization.
