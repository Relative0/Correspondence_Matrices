# Native-gap campaign V17 d4v2 CLI-contract proposal

Date: 2026-08-29  
Status: authorized under the aggregate `$10` campaign instruction

V16 correctly classified the pinned d4 as static and reached native execution,
but the inherited legacy `-mc` command failed on the first zero-width case.
The binary is d4v2's competition build: its shipped wrapper passes the CNF as
the sole positional argument, and it requires positive DIMACS width. A local
WSL execution on Linux-native storage confirmed exact counts 8, 0, 0, 2, and
4 for five positive-width cases using that interface. Pod
`wctkcbmzs8ymze` was deleted and both inventories were empty. Estimated
compute was `$0.0019470522`.

V17 binds a separate strict d4v2 competition command/parser contract. It
requires one SAT/UNSAT status and exactly one
`c s exact (arb|quadruple) int N` line, checks status/count consistency and
the declared universe, and refuses all other non-comment output. Failures now
preserve bounded stdout/stderr excerpts and hashes.

The exact V12 upload manifest has 37 files and 5,517,333 bytes. Focused tests
are 68; P5 remains 144 cells. This is readiness only, not performance evidence.
All prior resource, dependency, transport, deadline, zero-volume, cleanup,
`$0.10` phase and `$10` aggregate caps are unchanged. This controller
performs exactly one create request.
