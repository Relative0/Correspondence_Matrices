# Native-gap campaign V19 offer-endpoint retry proposal

Date: 2026-08-29  
Status: authorized under the aggregate `$10` campaign instruction

V18 sent no create request because all three read-only CPU-offer requests
returned provider `ConnectionError`. Its receipt records
`creation_attempted=false`, `pod_created=false`, and zero uploaded files.
A subsequent read-only check found empty inventories, all offers eligible,
`cpu3c` HIGH at `$0.06/hour`, and `$0.0048599334` in posted billing for
the new comparative campaign.

V19 preserves the exact V13 upload manifest (37 files, 5,518,172 bytes), 68
focused tests, 144 P5 cells, and every V18 validation gate. Resource,
dependency, transport, deadline, zero-volume, cleanup, `$0.10` phase and
`$10` aggregate caps are unchanged. This is readiness only and the
controller performs exactly one create request after a fresh preflight.
