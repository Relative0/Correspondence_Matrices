# Native-gap campaign V15 preflight-timeout retry proposal

Date: 2026-08-29  
Status: authorized under the aggregate `$10` campaign instruction

The independent V14 preflight passed with empty inventories and the expected
`cpu3c` offer. The V14 controller's repeated provider read timed out before
any create request: `creation_attempted=false`, `pod_created=false`, and
zero workload files were uploaded. This is a zero-cost transport failure.

V15 preserves the exact V10 source manifest (37 files, 5,510,267 bytes), 66
focused tests, 144 P5 cells, controller gates, dependencies, zero-volume
resource shape, cleanup guard, 20-minute lifetime, `$0.10` phase cap and
`$10` aggregate cap. It performs exactly one create request only after its
new read-only preflight succeeds. This remains readiness evidence, not
performance evidence.
