# Native-gap campaign V14 bounded RSS-window proposal

Date: 2026-08-29  
Status: authorized under the aggregate `$10` campaign instruction

V13's source, tests, P5 controls, transport and cleanup passed, but the first
CaDiCaL worker was observed during a Linux exec/start transition in which
`/proc/<pid>/status` temporarily omitted `VmRSS`. The strict supervisor
refused the run before d4. Pod `4ovdjr0todatgl` was deleted and both
inventories were empty. Estimated compute was `$0.0015499419`.

V14 retains fail-closed handling of a persistently live unmeasurable process,
but extends the bounded `VmRSS` appearance reread window from two to twenty
1-ms-spaced reads. The worker and external-child measurement fences remain.
A new local test proves recovery only within that finite window and the
existing test proves a process still missing `VmRSS` is refused.

The exact V10 upload manifest has 37 files and 5,510,267 bytes. Focused tests
are 66; P5 remains 144 cells. This is readiness only, not performance evidence.
Resource, dependency, transport, deadline, zero-volume, cleanup, `$0.10`
phase and `$10` aggregate caps are unchanged. This controller performs
exactly one create request.
