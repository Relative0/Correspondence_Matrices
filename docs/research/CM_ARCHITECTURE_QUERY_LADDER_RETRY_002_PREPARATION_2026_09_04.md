# Architecture query-ladder retry 002 preparation

Date: 2026-09-04
Scope: corrected non-neural Lane-B q1/q4/q16/q64 execution
Status: exact authorization executed; result independently verified; Pod deleted

Attempt 001 is closed incomplete with no scientific result. It completed 11,744 of
27,648 cells before the 420-second workload bound, then deleted its only Pod. Both
controller cleanup and a later independent RunPod inventory query returned empty v1
and v2 inventories. Estimated compute cost was $0.008934.

The partial data are used only for engineering diagnosis. They showed that inherited-
heap `gc.collect()` calls consumed about 83% of accounted time. Retry 002 keeps the same
54 cases, eight arms, 16 counterbalanced blocks, four separately timed query counts,
exact output contract, and isolated-child RSS method. It changes cleanup accounting:

- declared backend caches are explicitly cleared and timed;
- child exit releases the remaining per-cell heap;
- `gc.collect()` does not scan the inherited parent heap in each child;
- full fork/IPC/exit lifecycle time is retained separately from backend task time.

The freeze is bound to source checkpoint `13d9927` and contains 27,648 cells, 6,912 at
each of q1, q4, q16, and q64. The 70-file, 3,937,209-byte package passed a clean isolated
Windows/MSVC functional replay without `PYTHONPATH`, network access, timing evidence,
memory evidence, or a decision-bearing result. All eight arms matched all four frozen
oracle checkpoints in the 32-cell smoke.

The exact request is
`docs/recognition/architecture_query_ladder_followup_retry_002_execution_20260904/RUNPOD_RETRY_002_AUTHORIZATION_REQUEST_20260904.json`
(SHA-256 `b1d867502776e855603d9948f3cf5e76226702d8e90a680d5e7387e7c3d17d79`).
It permits one Secure CPU Pod, one create with no replacement, the original 420-second
workload and 600-second cleanup bounds, and at most $0.04 for the retry. Attempt 001's
estimated cost plus the retry's hard ceiling remains below $0.05. It authorizes no
training, selector fitting, routing, website update, publication, persistent storage,
credential upload, or Git push.

The exact request received fresh user authorization. The authorization was recorded in
`RUNPOD_ARCHITECTURE_QUERY_LADDER_RETRY_002_EXACT_PAYLOAD_AUTHORIZED_2026_09_04.json`;
neither attempt 001 nor any earlier comparison authorization was reused.

## Execution outcome

The controller created one Secure CPU Pod (`r5wx3ximopqw7g`) with 2 vCPU and 4 GB RAM
at $0.06/hour. The workload completed all 27,648 rows in 88.074 seconds, including
6,912 separately timed rows at each query count. The independent verifier reported zero
semantic, schedule, source/artifact, and memory-field mismatches. The controller deleted
the Pod after 158.913 seconds from creation, with estimated retry compute cost $0.002649.
Combined estimated cost for attempt 001 and retry 002 was $0.011583, below both the
retry's $0.04 cap and the cumulative $0.05 ceiling. Controller and later independent
v1/v2 inventory checks were empty.

The verified interpretation is deliberately one-host and task-specific. CSE-flat bigint
was the best fixed arm at q16 and q64 and reached 1.100x over Python R2 at q64 with all
54 cases above 1.0. Native fused slots reached 1.049x at q64 overall, but its interval
included 1.0 and its 0.567x minimum failed the predeclared 0.95 floor. Native was 1.328x
on the 18 observed C36 cases but only 0.933x on 36 fresh cases. No selector, neural,
routing, website, or publication action was taken. A separate physical-machine/compiler
replication remains the next gate.
