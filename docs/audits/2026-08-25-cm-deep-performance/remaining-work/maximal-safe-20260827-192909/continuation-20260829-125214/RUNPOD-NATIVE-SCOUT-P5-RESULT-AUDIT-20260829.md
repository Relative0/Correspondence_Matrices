# Runpod native-scout P5-corrected result audit

Date: 2026-08-29  
Status: **attempt consumed; partial workload passed; native readiness incomplete**

## Result

The one P5-CLI-corrected create authorization was used once. Runpod created pod
`pow0qre2q39m4t` (name `cm-native-scout-2f9d4cf14d50`) with the requested
Secure `cpu3c` allocation: 2 vCPUs, 4 GB RAM, `$0.06/hour`, the pinned Python
3.13.15 image, 12 GB container storage, integer zero pod volume, no network
volume, and only the two approved HTTP ports.

The bounded chunk transport uploaded all 37 files in eleven chunks. The
2,850,402-byte payload and complete SHA-256 were acknowledged before worker
start. Source identity was unchanged before and after the workload.

The remote stages produced these results:

- all 60 focused JUnit testcase elements passed, with no failure, error, or
  skip;
- the corrected P5 command and its independent read-only verifier both exited
  zero;
- P5 reconciled exactly 144 planned and observed cells, all `ok`;
- all eight native dependency artifacts were hash checked, the two allowed
  source distributions built locally into wheels, seven bounded setup commands
  succeeded, and `pip check` reported no broken requirements;
- the Linux control probes passed their declared outcomes: normal completion,
  bounded-output stop, process-tree deadline/cleanup, and sampled-tree-RSS stop;
- the first CaDiCaL worker was launched, but its supervisor returned
  `process_tree_measurement_incomplete`; the scout then failed closed before
  writing CaDiCaL, CUDD, d4, or perf results.

No comparative timing or performance ranking ran. This attempt establishes the
P5 package and dependency closure, but it does not complete the P4 native gate.

## Instrumentation finding

The Linux supervisor reads `/proc/<pid>/stat`, then `/proc/<pid>/status`, and
requires `VmRSS` for every live member of its owned process group. Its frozen
version excluded zombie state `Z`, but not Linux terminal states `X`/`x`, and
did not recheck state when `VmRSS` disappeared between the two reads. A fast
worker can therefore be rejected during exit even though no live descendant was
left unmeasured.

The saved evidence records the incomplete-measurement refusal, but not the
individual state that triggered it. The terminal-transition explanation is a
specific code-level false-refusal path consistent with the observation; it is
not claimed as a directly recorded kernel-state fact.

The local V6 correction now:

- excludes `Z`, `X`, and `x` as terminal states;
- rereads `stat` when a status snapshot has no `VmRSS` and downgrades only a
  proven disappearance, group change, or terminal transition to a procfs race;
- continues to fail closed for a still-live owned process without measurable
  RSS; and
- marks `whole_tree_rss_measured=false` on any remaining incomplete sample.

Three regression tests cover terminal states, the between-read transition, and
the still-live fail-closed case. This correction has not yet been exercised on
Linux/Runpod.

## Allocation and measurement limits

The runtime saw host logical CPU count 192, but the pod's actual allocation
evidence is affinity `[59, 155]`, exactly two CPUs. The cgroup record showed
`memory.max=3,999,997,952` bytes. `cpu.max` had no quota, so CPU allocation is
claimed from affinity, not the host count or a cgroup quota.

The successful RSS control demonstrates sampled owned-process-group RSS and
cleanup behavior. It is not a kernel-enforced per-worker memory cap and is not
a performance measurement.

The native identities in the initial environment record were captured before
the native dependency installation. They must not be interpreted as a final
post-install availability result. The scout stopped before the worker results
could provide those final identities.

## Cleanup and cost reconciliation

The controller deleted its owned pod with HTTP 204. The watchdog reported
`controller_cleanup_verified`; both host guards exited. A separate read-only
postflight found empty v1 and v2 inventories and HTTP 404 for all nine known pod
IDs through both API versions.

Provider billing had not yet posted a row for this pod. The conservative
elapsed-time bound, including the storage-rate reserve, is `$0.0016653375`.
The attributable comparative campaign bound is `$0.0059547362`, below the
`$0.10` phase and `$0.20` campaign caps.

## Evidence identities

| Evidence | SHA-256 |
|---|---|
| retrieved archive (`135,887` bytes, 61 files) | `7b43b5c203c1a3a1a58b586580e52a3cd0ec8c25a45dcc99f3651fa56960387d` |
| source-before/source-after record | `094c6cb6526bddf57e06700fb42906053be7aaa27c1122f491cf8ead108b67c2` |
| final read-only verification | `b110d7c6bdd356ff9fa33f930479557c9593b37491be8e69ab75b4bddb082dd6` |
| V5 controller | `4d08ae9ca02431e87f10516e1f10ec115b9285a773a1a1227d7804a700ea24e9` |
| V5 manifest | `f2550901addb878f6d36bbb55fee98b8ae18732958aa3a962b898910f7795f8e` |

The authorization is consumed. No automatic replacement, new pod, timing
campaign, publication, or production change is authorized by this result.
