# Policy compatibility replay

Status: driver prepared; accepted-corpus replay NOT RUN. No profile activated.

| Diagnostic profile | Output limit | Estimated temporary limit | Output-variable limit |
|---|---:|---:|---:|
| legacy-direct | 256 KiB | None | None |
| legacy-benchmark | 64 KiB | None | 16 |
| legacy-remote | 64 KiB | None | None |
| production-balanced-v1 benchmark/new remote | 64 KiB | 16 MiB | 16 |
| production-balanced-v1 direct | 256 KiB | 64 MiB | None |
| strict-diagnostic | 16 KiB | 4 MiB | 14 |
| permissive-diagnostic | 256 KiB | 64 MiB | 16 |

The driver records decisions under each profile with both legacy and candidate estimates. Legacy is the current separate-surface policy; it is not silently assigned a temporary cap or a new remote variable guard.

The local smoke has only three comparable calls. All 21 per-model profile decisions admit those tiny outputs. This establishes plumbing, not a compatibility rate. An admission counter is not proof that all allocations fit a process quota.

False admission means a profile admits but the matching observed traced peak exceeds its temporary limit. False refusal means output/k limits fit, temporary estimate refuses, and the matching measured peak fits. Unmeasured/failed calls produce unknown diagnostics. These definitions apply to tracemalloc only, not RSS.

BX1/B2/EPFL can be replayed with the prepared Runpod-only command. The existing authoritative context mapper and frozen truth verifier are reused; EPFL LSB/MSB and dead-axis mapping are not reinvented. Cases exceeding the driver's bounds remain refused with denominators preserved. Whole families alternating-tree and reconvergent-xor are reserved for structural held-out checks.

These are benchmark-corpus and synthetic structural checks. Real caller compatibility is unknown until an approved application trace exists. Brian must separately approve numeric profiles and newly refused formerly valid calls before any profile becomes a default.

## Protocol preparation decision

Defer optional policy/estimator IDs and resolved-limit echo in production until the estimator and compatibility study identify a stable contract. Only the observed malformed-limit and refusal-metadata defects were fixed now.

Future additive contract: absent/null policy_id means legacy; no numeric field is filled merely because a policy ID exists; diagnostics echo caller-resolved limits and estimator ID only when supplied; ok/reduced/refused agree in local/mock/worker tests; older serialized fixtures preserve their meanings. No remote pod is needed to test this contract.
