# CM hardware behavior-change corpus result

Date: 2026-09-04

Decision: **stop; the frozen corpus is not admissible for a Yosys correctness gate**

Scope: exact, non-neural source/activation feasibility only

## Result

The [preregistered protocol](CM_HARDWARE_BEHAVIOR_CHANGE_CORPUS_PROTOCOL_2026_09_04.md)
corrected the earlier “any HDL-touching commit” dilution by selecting only production-
RTL transitions with at least one normalized stable driver change, at least one reusable
stable driver, and no more than 90% changed comparable drivers. The rule and two new
confirmation projects were frozen before their histories were opened.

All four repositories passed exact public-origin, branch/head, readable-object, and
sampled-head license checks. The audit screened 214 first-parent non-merge commits and
selected 36 transitions. Offline independent replay reproduced all 214 scan decisions,
36 selected transitions, source and license hashes, identities, metrics, and the summary
with zero mismatches.

The corpus nevertheless fails the frozen gate because one of the two confirmation
histories supplied no qualifying transition and cannot be replaced.

| Frozen measure | Observed | Required | Decision |
| --- | ---: | ---: | --- |
| provenance-admitted repositories | 4/4 | 4/4 | pass |
| BlackParrot selected transitions | 12 after 75 scans | at least 8 | pass |
| `ultraembedded/riscv` selected transitions | 0 after all 42 available scans | at least 8 | fail |
| BlackParrot changed/comparable stable drivers | 332/1,716 (19.35%) | corpus total 1% to 80% | pass |
| BlackParrot distinct changed/reusable drivers | 236/713 | at least 8/8 | pass |
| BlackParrot changed paths/modules | 25/25 | at least 4/4 | pass |
| BlackParrot selected-path parse coverage | 3,654/5,035 (72.57%) | at least 60% | pass |
| `ultraembedded/riscv` selected-path coverage | no selected paths | at least 60% | fail |
| all-history selected-path parse coverage | 19,459/25,507 (76.29%) | at least 65% | pass |
| independent replay mismatches | 0 | 0 | pass |

For `ultraembedded/riscv`, 39 of 42 commits had no change under the frozen
`core/riscv/` production path. The other three were retained and refused:

- the `v1.0.1` commit touched 18 eligible paths but left all 202 comparable parsed
  drivers unchanged after comment/whitespace normalization;
- the missing-include commit touched one eligible path but left all 24 comparable
  parsed drivers unchanged; and
- the `v1.0` transition had 202 added and 41 removed parsed drivers but no stable
  comparable changed driver, so it could not demonstrate incremental reuse.

The subjects are provenance only and were not selection predicates. BlackParrot's
strong result cannot be paired post hoc with a replacement project, and its favorable
transitions cannot be promoted from one held-out history after the two-history gate
failed.

## Evidence boundary

These are conservative, pre-synthesis source-driver regions. They are not proof that a
revision changes synthesized behavior, not elaborated cells/nets/cones, and not a CM
benchmark. This phase did not run Yosys, construct or time CM/CSE/raw-flat artifacts,
measure memory, train a selector, alter routing, use RunPod, or change a website claim.

The exact evidence is in
[`verification/hardware-behavior-corpus-2026-09-04`](verification/hardware-behavior-corpus-2026-09-04/):

- `MANIFEST.json` binds source revision
  `b3b4c307cdd38e0013f9800f78538c04e88196e8`, protocol/program hashes, candidates,
  cutoff, bounds, origins, and environment;
- `AUDIT.json` retains every scanned commit through each stopping point, including all
  refusals and zero-change screens;
- `SUMMARY.json` records every frozen condition;
- `INDEPENDENT_VERIFICATION.json` records the exact offline replay;
- `INVENTORY.json` and `CHECKSUMS.sha256` bind the evidence files.

## Disposition

This third H9 workload attempt is closed as negative source-admission evidence. The
failed corpus must not progress to Yosys, timing, optimization, remote replication, or
publication as a speed result. Because source admission failed, no Yosys correctness
protocol is frozen in this task.

BlackParrot demonstrates that a naturally active, reusable hardware revision history
can satisfy the source screen. It is now exposed development evidence, not an untouched
confirmation source. Another H9 attempt would require a genuinely independent history
or a real user workflow identified before a new protocol freeze; it must not be a
sequence of replacement repositories chosen after observing failures. Until such a
source exists, H9 remains deferred and the current persistent CM cache remains the
verified related-version implementation.
