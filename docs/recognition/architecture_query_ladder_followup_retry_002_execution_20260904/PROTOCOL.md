# Corrected query-ladder and isolated-memory execution protocol

This package is a source-bound Lane-B follow-up to architecture comparison retry 002.
It preserves the same 54 cases, eight exact residual-relation arms, and 16 balanced arm
orders, but creates a distinct timed cell at q1, q4, q16, and q64. The schedule therefore
contains 27,648 rows (6,912 per query count). It does not rerun or
revise the complete-vector, multi-root, or smaller-task lanes.

Every decision-bearing cell runs inside a fresh Linux fork child. Timing starts and ends
inside that child, so process-isolation launch cost is excluded from backend task time.
The parent records the child's total peak RSS from `wait4` and the inherited baseline
from `/proc/self/statm`, then reports their nonnegative difference. The task charges
explicit backend-cache clearing and uses child exit for the remaining cell heap; the
full fork/IPC/exit lifecycle is reported separately. These are descriptive per-cell
host-memory measurements; publication still requires a second machine.

The required artifact at every query count is the ordered explicit residual-relation
prefix, including exact count, SAT flag, canonical witness, and digest. An independent
verifier must match every schedule position, timing sum, oracle digest, and memory field
before interpretation. The workload uses no network after dependency setup.

A later exact approval is limited to one Secure CPU Pod, one create and no replacement,
2 vCPU, at least 4 GB RAM, 12 GB ephemeral disk, no persistent/network volume, a
$0.25/hour rate ceiling and a separately declared total ceiling, cleanup within
600 seconds, and inventory reconciliation within
720 seconds. It authorizes no selector fitting, neural training,
production routing, website update, publication, commit, push, or reuse of an earlier
authorization.
