# Native-gap campaign V16 static-d4 proposal

Date: 2026-08-29  
Status: authorized under the aggregate `$10` campaign instruction

V15 passed all 66 focused tests and 144 P5 cells, and completed native CaDiCaL
and CUDD evidence. It then refused d4 at the dynamic-dependency gate. The exact
pinned d4 ELF has no `PT_DYNAMIC` and no `PT_INTERP`: it is a static
x86-64 executable, so invoking `ldd` is inapplicable and its nonzero
"not a dynamic executable" result was incorrectly treated as a missing
dependency. Pod `od0zndjtowjwon` was deleted and both inventories were empty.
Estimated compute was `$0.0014268835`.

V16 adds a bounded, non-executing ELF64 program-header parser. Static binaries
record `ldd_executed=false`; dynamic binaries retain the prior bounded ldd
gate and now preserve its diagnostic even on refusal. A local test binds the
classification to the exact pinned d4 SHA-256.

The exact V11 upload manifest has 37 files and 5,513,196 bytes. Focused tests
are 67; P5 remains 144 cells. This is readiness only, not performance evidence.
All prior resource, dependency, transport, deadline, zero-volume, cleanup,
`$0.10` phase and `$10` aggregate caps are unchanged. This controller
performs exactly one create request.
