# Native-gap campaign V20 d4v2 bare-comment proposal

Date: 2026-08-29  
Status: authorized under the aggregate `$10` campaign instruction

V19 successfully ran d4 and preserved the full first-case stdout after a parse
refusal. The only unadmitted syntax was the exact token `c`, which d4v2 uses
for blank comment lines. The same output contains the expected SAT status and
exact integer 2. Pod `hzn77xb71bq281` was deleted and both inventories were
empty. Estimated compute was `$0.0012129468`.

V20 admits only the exact bare-comment token and adds it to the strict parser
fixture. All other competition, progress, status, exact-count and refusal
rules are unchanged.

The exact V14 upload manifest has 37 files and 5,518,220 bytes. Focused tests
remain 68; P5 remains 144 cells. This is readiness only, not performance
evidence. All prior resource, dependency, transport, deadline, zero-volume,
cleanup, `$0.10` phase and `$10` aggregate caps are unchanged. This
controller performs exactly one create request.
