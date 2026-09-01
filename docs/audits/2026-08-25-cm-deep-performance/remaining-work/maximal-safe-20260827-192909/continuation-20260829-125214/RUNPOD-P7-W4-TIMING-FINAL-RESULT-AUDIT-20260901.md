# P7 W4 timing/RSS scout: final result audit

Date: 2026-09-01
Status: passed diagnostic development scout; W5 relation extension path indicated

## Execution and evidence

The first exact create (`fixszqtou7pal8`) exposed a local bootstrap allowlist
defect after 4,194,304 encoded bytes had been accepted. No source archive was
extracted and no workload ran. Owned deletion returned HTTP 204 and both
inventories were empty. Estimated cost was `$0.000998864511648814`.

The preserved V2 retry changed only the bootstrap environment allowlist to
accept the already frozen `CM_EXECUTION_DEADLINE`. Pod `75v5aefblt3cnf` then:

- matched the approved Secure 2-vCPU/4-GB/$0.06-per-hour allocation, pinned
  image, 12-GB container disk, zero pod volume, and zero network volume;
- received the exact 96-file bundle and 13 locked binary dependencies;
- passed 42 unique focused JUnit cases with zero failures/errors/skips;
- passed the offline correctness/readiness gate;
- completed 384/384 P7 IR and 600/600 P7 relation cells;
- produced 984 unique fresh-worker identities with exact oracle agreement;
- preserved every uploaded source hash before and after execution;
- returned a 47-file evidence archive with SHA-256
  `28fe8c80bb50f80bf2b1ffded4ab477d826af26991d24cf1d40d73bd5087755f`;
- passed independent ZIP, checksum, plan, ledger, summary, oracle, source, and
  counterbalance reconciliation; and
- was deleted with HTTP 204, followed by empty v1/v2 inventories and 404 detail
  checks for both W4 pod IDs.

Successful-run estimated compute cost was `$0.005539172677199045`; combined W4
attempt estimate was `$0.006538037188847859`. Itemized account billing was still
lagging at final postflight.

## Descriptive timing findings

These are development-scout diagnostics. They are not the principal P7 result,
do not use the untouched W8 confirmation set, and are not external-method
comparisons.

### Ordered IR artifact family

`cm-ir-current` versus historical `cm-ir-two-memo` was effectively tied:

- paired geometric-mean ratio, two-memo/current: `1.0003`;
- paired median ratio: `0.9982`;
- two-memo lower in 49/96 pairs and higher in 47/96; and
- no resolved sampled-RSS difference.

The scout therefore provides no development evidence that restoring the second
memo table improves ordered-IR preparation.

### Flat-program control family

Within the comparable flat-program artifact family, CSE-flat/raw-flat had:

- paired geometric-mean ratio `1.0411`;
- paired median ratio `1.0243`; and
- CSE-flat lower in 27/96 pairs and higher in 69/96.

Raw-flat was modestly faster in this scout. Flat-program timing must not be
ranked against ordered-IR timing as though they deliver the same artifact.

### Complete-relation full-output contract

Relative to dense, paired geometric-mean task-total ratios were:

| Arm | Candidate/dense | Candidate lower |
| --- | ---: | ---: |
| CSE-flat | 0.8326 | 112/120 |
| Packed bigint | 0.9409 | 103/120 |
| Packed words | 0.9526 | 101/120 |
| No-reinflation | 1.2177 | 8/120 |

CSE-flat was the strongest development signal under this exact full-output
contract. Packed bigint and packed words showed smaller improvements. The
current no-reinflation arm was slower when charged for the complete delivered
relation; this result does not establish its behavior for reduced-output or
multi-query lifecycle tasks, which remain W7 work.

Synthetic and natural cases agreed in direction for all four comparisons. The
effects were larger on the six natural EPFL cases.

## RSS and measurement limits

Median sampled process-tree RSS was about 38.9–39.0 MiB for every arm; the
largest observed value was 68.6 MiB, far below the 1-GiB sampled stop. At this
scale, interpreter/process baseline dominates RSS, so the scout does not resolve
representation-level memory savings.

Fresh-process controller wall time was roughly 19–27 times the worker's timed
task interval at the median. The primary task-total metric excludes that startup
and supervision overhead, but W5 must continue reporting both metrics. The
successful pod completed setup, 984 cells, verification, retrieval, and cleanup
in about 5.5 minutes, leaving substantial headroom under the 20-minute limit.

## Frozen noise rule

The threshold is MAD/median greater than 50,000 ppm (5%).

- P7 IR: 0/48 case-arm units and 0/36 paired-ratio units exceeded the threshold.
- P7 relation: 1/60 case-arm units and 2/48 paired-ratio units exceeded it.
- The only raw case-arm exceedance was dense on natural EPFL `dec`, at 5.57%.
- Normalized block medians ranged 0.990–1.044 for IR and 0.988–1.058 for
  relation.

The predeclared conditional extension is therefore indicated for relation, not
IR. This is a rule application, not a post-hoc choice of favorable arms.

## W5 shard sizing decision

Use complete case/block units and preserve the frozen order ledger:

- IR minimum: two 29-case shards, 928 primary cells each (1,856 total).
- Relation minimum: two 29-case shards, 1,450 primary cells each (2,900 total).
- Relation conditional extension: two additional 29-case shards containing
  blocks 10–19, 1,450 cells each, if the frozen rule remains triggered.
- Do not run the IR extension unless W5's own frozen minimum-block analysis
  triggers it.
- Add a separately labeled, frozen diagnostic anchor set to each allocation;
  anchors do not count as independent formulas or primary cells.

This yields four minimum W5 shards and at most two presently indicated relation
extension shards. The empirical W4 throughput places every proposed shard well
inside a 20-minute pod horizon, while retaining complete counterbalance cycles.

## Result

W4 passes its integrity, correctness, resource, retrieval, cleanup, and cost
gates. It supports proceeding to an exact W5 P7A/P7B development freeze and
sequential shard campaign. It does not yet justify freezing a final combined
`CM-Fast-Frozen` configuration or making claims against external algorithms.
