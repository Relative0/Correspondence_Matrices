# Audit of the CM fast-variant and comparative benchmark plan

Date: 2026-08-29  
Audited document: `CM-FAST-VARIANTS-COMPARATIVE-BENCHMARK-PLAN-20260829.md`, revision 2  
Result: expanded; no cloud run or authorization implied

## Audit question

Does the plan cover the useful work still available in the current repository
and evidence record, including IR and no-reinflation, while avoiding already
answered, mismatched, or theoretically uninformative campaigns?

## Sources cross-checked

- Current `cm_ir.py`, `bitset_backend.py`, `cm_bench.py`, measurement/session/
  native contract scripts, and process supervisor.
- `CM_BENCHMARK_GAP_ANALYSIS_2026-08-01.md`, experiments E1–E10.
- `docs/audits/2026-08-25-cm-deep-performance/CM-OPTIMIZATION-BACKLOG.md`,
  including DP-R1/R2/R4, DP-W1–W6, and DP-X1–X3.
- Accepted high-sharing, CSE-flat, symmetric V3, memo, cache/context, Runpod,
  structural-memory, and corpus/oracle/RSS evidence summarized by those files.
- `docs/research/PROCESS-AND-NATIVE-CONTRACT-PROGRESS-2026-08-28.md` and
  `docs/research/SESSION-AND-VERSION-CONTRACT-PROGRESS-2026-08-28.md`.

This was a document/repository audit. It did not execute benchmarks, access a
credential, install a dependency, allocate a pod, or modify production code.

## Corrections made

1. Removed every request to map or investigate Inflation/Deflation terminology.
   The revised plan works directly with the implemented IR, full materialization,
   hybrid no-reinflation, reduced-support, and restoration contracts.
2. Split IR preparation from packed execution. The plan now records structural
   UID/digest, canonicalization/interning, building, lowering, binding,
   instruction/primitive-op counts, transposes/permutations, and memory.
3. Added the current one-memo versus explicit historical two-memo control and
   the gated compact canonical-key prototype.
4. Expanded the first short pilot into a staged, sharded Runpod program with
   development, task-matched external, untouched confirmation, and fresh-host
   replication phases.
5. Added real cache/edit economics, native/JIT word fusion, exact independent
   blocks, streamed output, a frozen backend selector, CI, and independent
   reproduction as conditional later phases.
6. Added task-specific scaling ladders, larger independent-unit targets,
   multi-allocation replication, memory-counter calibration, latency versus
   throughput separation, censored frontier analysis, and failure retention.

## E1–E10 reconciliation

| Earlier item | Current evidence | Revised-plan disposition |
| --- | --- | --- |
| E1 DAG/circuit cost model | High-sharing and sharing-aware IR work now exists | P7A extends it with staged IR accounting and avoids repeating accepted cells |
| E2 CSE ladder | CSE-flat is implemented and is the strongest generic incumbent | Required same-language control in P7A and all complete-vector comparisons |
| E3 cluster-replicated headline | Symmetric V3 and Runpod replication exist; corpus independence remains limited | Phase 6 independent formula/circuit targets and P9 untouched confirmation |
| E4 amortization crossover | Compile/reuse mechanics exist; task-matched crossover remains useful | Full `q` ladder in P7C and real histories in P10 |
| E5 schedule regime | Prior evidence showed schedule movement | Blocked, round-robin, sliding-window, and Zipf/locality schedules in P7C/P10 |
| E6 compiled packed executor | Still conditional on kernel dominance | Factorized program × executor native/JIT study in P11 |
| E7 order dispersion | Still scientifically useful | Frozen relabellings in P7D and fixed/reordered native CUDD in P8 |
| E8 platform replication | Some cross-host evidence exists; fresh-allocation variance is not settled | At least five fresh allocations when scout variance warrants it in P9 |
| E9 feasibility/above guard | Some `k=17..20` evidence exists | Preserve it; extend only missing task-specific frontier strata in P7D/P8 |
| E10 CUDD metric repair | Native current CUDD is not yet ready | Native identity/readiness in P4; split setup/build/reorder/query/extract in P8 |

## Optimization-backlog reconciliation

| Backlog item | Revised-plan disposition |
| --- | --- |
| DP-R1 compact canonical ordering/key | Contingent `CM-IR-Compact-Key` arm with exact compatibility and memory gates |
| DP-R2 estimator hardening | P7D representation-specific estimate/RSS study; policy change remains separate |
| DP-R4 one-memo second machine | Required P7A confirmation arm |
| DP-W1 byte/cost-aware cache | P10 on real/captured access traces only |
| DP-W2 incremental compilation | P10 on true edits and unknown-version arrival |
| DP-W3 backend selector | P12 only after real crossover volume and a new untouched corpus |
| DP-W4 partial-context break-even | P7C/P8/P10 with matched CM, CSE, CaDiCaL, and CUDD lifecycles |
| DP-W5 related versions | P7C/P8/P10 with true version histories |
| DP-W6 independent blocks | Conditional P11 proof-and-materialization study |
| DP-X1 native/JIT word fusion | Conditional factorized P11 study |
| DP-X2 native CUDD frontier | P4 readiness and P8 task-matched campaign |
| DP-X3 streamed large output | Conditional P11 tiling/streaming study |

## Comparative-method coverage

The plan now uses a strong representative for each relevant task class:

- CSE-flat/BitSet for exact complete vectors and structural compilation;
- native CUDD, and ZDD only where applicable, for symbolic count/restrict/
  equivalence tasks, with extraction charged for explicit vectors;
- native d4 for exact unweighted model count;
- native CaDiCaL for SAT, assumptions, witnesses, cores, and miters;
- a scalar implementation and SymPy-like logic only as correctness oracles.

Adding weaker or task-mismatched tools would create a larger table without a
stronger conclusion. Espresso, minimized covers, sparse numerical matrices,
and symbolic-only build times are therefore excluded from complete-vector
rankings. Additional native tools can be added only through the same artifact,
identity, oracle, lifecycle, and failure gates.

## Compute coverage

The revised plan no longer assumes that the next meaningful study must fit the
historical 20-minute smoke limit. It gives an illustrative core envelope of
about 28–74 CPU pod-hours across readiness, CM ablation, external development,
and untouched confirmation, plus 10–40 pod-hours for each triggered cache,
JIT, streaming, or selector branch. These quantities are planning magnitudes,
not authorization or quotes.

The plan spends added compute first on independent formulas/circuits/histories,
task and structural coverage, and fresh allocations. It caps repeated timing
blocks through a frozen noise rule so duration does not merely make a narrow
existing corpus look more precise.

## Audit conclusion

The revised plan covers every open, testable item in the current performance
backlog and E1–E10 record, either as a required phase, a conditional branch
with an explicit trigger, or a retired line with a reason not to run it. It
cannot enumerate every future algorithm or dataset, but it now supplies the
contract by which a new method can be admitted without weakening fairness or
evidence controls.

The next work remains P0–P5 implementation and local validation. Any Runpod
scout or longer shard still requires an exact manifest, resource scope,
duration, retry rule, and budget authorization.

