# CM Gap Series — Post-Acceptance Optimization Decision (2026-08-03)

Decision scope: what to test and what to optimize next, given (a) the
passed independent spot replication, (b) the pre-registered but
**unexecuted** EPFL external campaign, and (c) the pod-replication
decision below. Written by the post-acceptance independent session.

## 1. Evidence table

| evidence | status | key numbers |
|---|---|---|
| Corrected E3 (authoritative, local, synthetic) | accepted 2026-08-03 | CM/CSE kernel geomean 0.888 [0.876, 0.899]; CM/CSE-flat **0.985** (≈parity); executed-op ratio median 1.000; instr ratio 0.693, r = 0.824; prep 4.30× CSE; break-even median 78.5 evals; 30/192 never break even |
| Independent spot replication (this pass) | **PASSED** | all 60 summary rows ≤ 2e-16; break-even exact 192/192; 8/8 stratified bootstrap CIs within ±0.005; derived stats 0 deviation (`CM_GAP_INDEPENDENT_SPOT_REPLICATION_2026-08-03.md`) |
| EPFL external validation | **BLOCKED (approval)** | protocol pre-registered with materiality rule (`CM_GAP_EPFL_PROTOCOL_2026-08-03.md`); no external number exists yet |
| Pod replication (E8) | **NOT WARRANTED** (below) | prepared plan retained; nothing run |
| Fresh timing replay (acceptance review) | passed 2026-08-03 | Δ geomean 0.0001, CI overlap; direction stable |

## 2. Pod-replication decision (Phase 5 record)

1. Is any cross-machine performance claim intended? **No.** The accepted
   claim disposition retains an explicitly local-box scope ("no
   cross-platform claim"); nothing in the accepted text needs pod evidence.
2. Would pod evidence change a project decision? **No.** The next decision
   (optimize vs declare kernel-equivalent) keys on the EPFL materiality
   rule, which is a same-machine external-corpus test. Cross-machine
   variance affects neither branch today.
3. Is the corrected E3 corpus still the appropriate frozen replication
   workload? Yes (if pods are ever warranted).
4. Estimated cost still below $1? Yes (5 × cpu3c × ~5 pod-minutes).
5. Is the current remote worker deployed with the `remote_words_eval`
   provenance echo? **No** — the deployed worker predates the fix-2
   protocol (`CM_LATENT_FIXES_2026-07-23.md`); a redeploy from current
   `cm_remote_worker.py` is required before any live words+runpod run, and
   the client fails closed against the stale worker.

Questions 1 and 2 are both no ⇒ **POD REPLICATION NOT WARRANTED.**
Standing trigger to revisit: a cross-machine performance claim becomes
intended (e.g., publication beyond the local scope), or EPFL results make
platform sensitivity a live question. The prepared plan (5 × cpu3c, frozen
corrected corpus + driver, worker redeploy first, fail-closed provenance,
<$1) remains valid and is restated in the master handoff.

## 3. Outcome selection

**Outcome A — CM and CSE-flat are treated as kernel-equivalent —
PROVISIONAL, pending the gated EPFL campaign.**

The pre-registered materiality rule requires an external-corpus CM/CSE-flat
geomean ≤ 0.95 with a circuit-clustered CI excluding parity. No external
evidence exists (download unapproved), so the threshold is **not met**, and
the only synthetic estimate of the same quantity is 0.985 — itself far
above the threshold. Both roads lead to the same operational posture
today:

- **Do not optimize around the synthetic 0.985 ratio.** No kernel work
  aimed at the CM-vs-CSE-flat residual.
- **Treat CM and CSE-flat as kernel-equivalent** in engineering decisions;
  CM's differentiators are canonical keys, the persistent cache, and serde
  — not kernel speed against a flattened CSE.
- **Priorities shift to preparation cost (4.30×), cache behavior, and
  workload-aware backend selection.**

Provisionality is one-directional: an approved EPFL run that *meets* the
materiality rule reopens Outcome B with a mechanism analysis; an EPFL run
that fails it simply converts this provisional decision to final.

## 4. Selector proposal (analysis stage only — not production)

Proposal: a backend selector choosing CM vs CSE-flat per workload from
(a) expected evaluation reuse count E and (b) measured expression
properties (structural nodes, sharing factor, operator mix).

- Rule sketch: predict break-even Ê from expression properties (the E3
  data shows break-even median 78.5 with heavy family/shape structure;
  impeqv-dominant trees frequently never break even); choose CM only when
  E ≫ Ê **and** CM-specific features are wanted; otherwise CSE-flat.
- Validation requirement (pre-commitment): the decision rule must be fit on
  one slice of data and validated **out of sample** (minimum: fit on two
  E3 strata, validate on the third; better: validate on the EPFL corpus
  once approved) before any production integration is proposed.
- Explicitly **kept separate from production implementation** until that
  validation exists.

## 5. Agreed / disagreed claims

Agreed (re-verified independently this pass): the 0.888 headline and CIs;
mechanism = instruction merging, not executed-op compression; 0.985
≈parity vs CSE-flat; prep and break-even economics; blocked/round-robin
agreement; supersession of 0.843 and the 128×/240× retraction.

Disagreed: none. Two documentation nuances added (log-space median
definition; R1/R2 clarifications) — neither changes a number or a claim.

## 6. Generalization limits (unchanged, restated)

One local Windows box; one balanced synthetic generator
(`e3-corrected-2026-08-02.1`); CI excluding parity is not a universal CM
claim; AND/INV-form real circuits are untested until EPFL runs; no
cross-machine evidence and none claimed.

## 7. Ranked next tests

1. **EPFL external campaign** (gated on download approval) — decisive for
   Outcome A vs B; protocol frozen.
2. **Reuse-distribution measurement** on a real consumer workload, when one
   exists — calibrates the selector threshold E vs Ê.
3. **CM preparation-cost profile** (where the 4.30× goes:
   canonicalization, interning, lowering) — Outcome A names prep the top
   optimization surface; profile before optimizing.
4. **Persistent-cache behavior study** (hit rates, LRU maxsize sensitivity
   under realistic mixes) — second Outcome A surface.
5. **Pod replication** — only if the §2 trigger fires.

## 8. Ranked optimizations (gated on evidence above)

1. Prep-cost reduction targeting the top profiled contributor (needs test
   3 first; expected leverage: break-even median drops proportionally).
2. Selector production integration (needs §4 out-of-sample validation).
3. Cache-policy tuning (needs test 4).

## 9. Rejected optimizations (and why)

- **Kernel work on the 1.5% synthetic residual** — below the pre-registered
  materiality bar; synthetic-only; both schedules already agree it is
  ≈parity.
- **R2 foreign/twin slot dedup** — measured cost is one duplicated slot in
  a constructed corner case; no profiled production occurrence; explicitly
  deferred by the R2 clarification.
- **Further n-ary-merging ports into the CSE baseline** — sharing-aware
  flattening already closed the gap (0.985); no demonstrated residual to
  port.
- **Speculative cross-platform tuning** — no cross-machine claim intended;
  pod replication not warranted.

## 10. Go / no-go summary

| item | decision |
|---|---|
| EPFL campaign | **GO once download approved** (protocol frozen; no dependency install anticipated) |
| Pod replication | **NO-GO** (not warranted; standing trigger documented) |
| Any production optimization now | **NO-GO** (Outcome A posture; profiling first) |
| Selector analysis/validation | **GO** (analysis-only; production integration gated on out-of-sample validation) |
| Public claim text | already authorized by the acceptance handoff §5 to move to the corrected §3 statements; unchanged by this pass |

## 11. Implementation prompt for the next justified change

The next justified implementation is **not a production change**; it is the
EPFL extractor + campaign per the frozen protocol. The copy-paste prompt
for that session is included in
`CM_GAP_NEXT_PHASE_MASTER_HANDOFF_2026-08-03.md` §"Next implementation
prompt". No production-code change is justified by current evidence.
