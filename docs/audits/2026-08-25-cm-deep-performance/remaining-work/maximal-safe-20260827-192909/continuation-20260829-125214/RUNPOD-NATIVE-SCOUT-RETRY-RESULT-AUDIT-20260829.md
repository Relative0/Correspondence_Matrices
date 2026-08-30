# Runpod native-scout retry result audit

Date: 2026-08-29  
Attempt: `http-native-scout-retry-execute-001`  
Pod: `76exgpsv0y39bl`

## Result

The separately authorized retry issued exactly one create request. Runpod
returned HTTP 201, and the actual pod matched the approved Secure `cpu3c`,
2-vCPU, 4-GB, `$0.06/hour`, pinned-image, 12-GB-container, zero-volume, and
no-network-volume identity.

Both token-gated bootstrap health endpoints became ready. The controller then
timed out waiting for the monolithic `POST /payload` response. It never received
the payload hash acknowledgment, never sent `POST /run`, and retrieved no
workload evidence. Because a read timeout does not reveal how many request bytes
reached the server, payload delivery is uncertain. The worker and the 60-test,
144-cell, and native-tool workload did not start.

## Transport finding

The frozen request was 2,831,254 bytes. The prior successful corpus transport
was 448,161 bytes. The bootstrap also imposed a ten-second connection timeout,
while the controller allowed twenty seconds for the complete request and
response. The evidence proves only the controller-side `ReadTimeout`; the
combination of the larger monolithic payload and those timeouts is the strongest
local explanation, not a measured provider diagnosis.

The preserved controller correctly treated the timeout as failure and did not
retry an ambiguously delivered request.

## Cleanup and cost reconciliation

The controller performed ownership-only DELETE, which returned HTTP 204, after
about 52 seconds. The watchdog independently acknowledged controller cleanup
without errors. At 10:07:48 UTC:

- v1 and v2 inventories were empty;
- both APIs returned 404 for this pod and all five earlier pod IDs;
- controller and watchdog host-awake guards were released and their processes
  had exited;
- provider billing contained no row for this pod yet and remained subject to
  lag;
- the conservative retry bound was `$0.001016720` and the aggregate comparative
  campaign bound was `$0.001164632`, within the `$0.10` and `$0.20` caps.

The independent receipt is
`HTTP-NATIVE-SCOUT-RETRY-FINAL-VERIFICATION-20260829-100759-402074.json`; it
records `attempt_safely_reconciled: true`, `authorization_consumed: true`,
`payload_acceptance_uncertain: true`, and `workload_completed: false`.

## Further-run boundary

No replacement is authorized or queued. The V2 authorization is consumed. Any
further create requires a distinct proposal and explicit authorization.

