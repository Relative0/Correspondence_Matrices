# CM benchmark campaign prelaunch report

Campaign: `cm-mega-prelaunch-20260914-008`

This is a tested local preparation package, not benchmark performance evidence and not launch authorization.

## Outcome

- 641 public inputs were hash/license/parser admitted.
- 1241 of 2,400 base slots are planned; 1159 remain explicit quota shortfalls.
- Adapter probes: 14 verified, 2 unverified, 5 missing.
- Reduced scope: 14 verified adapter entries planned and 7 frozen not-run.
- The deterministic upload package contains 641 files in 11 bounded shards (171502157 compressed bytes).
- Paid launch is blocked and unauthorized.

## Admission and schedule

| Group | Planned | Not run |
|---|---:|---:|
| hardware | 30 | 570 |
| feature_models | 10 | 390 |
| biological_functions | 300 | 0 |
| sat_and_counting | 288 | 12 |
| affine | 13 | 187 |
| synthetic_mechanisms | 600 | 0 |

Previously consumed LogikBench, SoftVarE and GNU Radio inputs remain regression cases. The newly frozen Biodivine biology functions and CC0 exact/projected counting inputs were split by source cluster before benchmarking; no synthetic case was relabeled as real-world.

## Adapter readiness

| Adapter | State | Evidence |
|---|---|---|
| `biology.biodivine_native` | present_verified | bounded_local_probe_passed |
| `biology.bnet_cm` | present_verified | bounded_local_probe_passed |
| `bitmaps.croaring` | missing | record-set semantic adapter deferred |
| `complete_relation.cm_cse_bitset` | present_verified | bounded_local_probe_passed |
| `exact_count.cudd_arbitrary_precision` | present_unverified | capability probe failed:ImportError |
| `exact_count.d4` | present_verified | bounded_local_probe_passed |
| `exact_count.ganak` | present_verified | bounded_local_probe_passed |
| `gf2.m4ri` | present_unverified | local source present; no pinned locally executed library binding |
| `gf2.python_packed_elimination` | present_verified | bounded_local_probe_passed |
| `hardware.abc_equivalence` | missing | pinned ABC executable unavailable |
| `hardware.yosys_transform` | missing | pinned Yosys executable unavailable |
| `policies.native_services` | missing | Cedar/OPA semantic adapters deferred |
| `projected_count.cm` | present_verified | bounded_local_probe_passed |
| `projected_count.native_ganak` | present_verified | bounded_local_probe_passed |
| `sat.cryptominisat_xor` | present_verified | bounded_local_probe_passed |
| `sat.kissat_one_shot` | present_verified | bounded_local_probe_passed |
| `sat_witness.pysat_cadical` | present_verified | bounded_local_probe_passed |
| `streaming.packed_backpressure` | present_verified | bounded_local_probe_passed |
| `sympy.matched_callable` | present_verified | bounded_local_probe_passed |
| `tracing.metrics_replay_contract` | present_verified | bounded_local_probe_passed |
| `weighted_inference` | missing | weighted Boolean/probability contract deferred |

## Public RunPod quote

The official public Pods listing checked at `2026-09-13T18:55:31.685914Z` showed RTX 3090 at $0.50/hour with 125 GB advertised RAM and 16 advertised vCPUs. Sixteen hours plus prorated 30 GB container disk estimates $8.07. Availability, cloud class, assigned region, usable cgroup RAM and CPU quota were not account-verified.

## Gate

The reduced scope freezes corpus quota gaps and unavailable adapters as explicit not-run entries rather than launch blockers. Before a paid launch: refresh account-visible placement, then obtain explicit authorization for these exact shards and caps. The pinned Linux image passed Ganak exact/projected, d4 exact, Kissat, CryptoMiniSat XOR-witness, and Biodivine AEON fixed-point smoke tests. No cloud resource or upload was created by this preparation.
