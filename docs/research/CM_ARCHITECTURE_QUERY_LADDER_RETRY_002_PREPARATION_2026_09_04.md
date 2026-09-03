# Architecture query-ladder retry 002 preparation

Date: 2026-09-04
Scope: corrected non-neural Lane-B q1/q4/q16/q64 execution
Status: frozen, locally verified, and not authorized

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

No cloud action may occur until the exact retry request receives fresh user authorization.
