# Task and family findings

**Measured scope:** 70/70 diagnostic cells completed with exact outputs in 44.120 seconds. Five uninstrumented repeats per cell; three separate phase passes and independent profile/memory passes. These disclosed, small cases identify mechanisms and accounting boundaries, not general performance rankings. Details and limitations are in `TASK_METHODS.md`; all medians and phase shares are in `TASK_SUMMARY.json` and `TASK_LEDGER.md`.

## Supplied assignments are not full-relation enumeration

For balanced-k8 and 4096 supplied assignment rows, raw/CSE/CM ingress into the **same** NumPy evaluator took 5.934/6.037/5.940 ms including common input construction and delivery. Absorption-k4 took 3.981/3.960/4.056 ms. These small differences do not demonstrate a CM-specific batch advantage. The SymPy lambdify arms took 8.260–8.422 ms on balanced-k8 and include conversion/callable compilation that the CM evaluator does not require.

The separate CM phase pass attributes 64.7% (balanced) and 59.9% (absorption) to constructing the deterministic assignment rows, 11.9%/18.5% to packing the answers, and only 7.5%/7.6% to the grouped assignment binding/evaluation/list conversion. Input JSON loading adds 8.3%/9.4%. The labels matter: the supplied-row construction phase is not an operation a caller with an already supplied byte buffer necessarily repeats. The grouped evaluator phase still includes materialization and conversion, so a pure NumPy kernel percentage is **unknown**.

**Code-supported inference:** CM's full-information mathematical language does not force full `2**n` relation construction in this path. Here CM nodes act as an evaluation DAG over selected rows. Retained support/keys and rewrite preparation remain CM representation work; their value depends on repeated structure and rewrite effect. The same-evaluator controls remove the earlier ambiguity that a gain over lambdify necessarily came from CM.

## Repeated restriction amortizes preparation

For balanced-k8 fixing x0/x1 and delivering the remaining six-variable relation, q1 CSE/CM medians are 0.439/0.575 ms. At q64 they are 1.153/1.136 ms. q64 compiles once and cycles four distinct contexts, so cached binding and reduced program work are repeatedly reused. This is a local incremental interaction, not a general q64 winner claim.

CM representation compile accounts for 31.8% of the q1 phase caller and 13.6% at q64. The q64 kernel is 16.4%; binding, per-query conversion, input handling and Python book-keeping account for the rest. Because total output is 512 bytes at q64 versus 8 bytes at q1, these fractions are not additive causal shares between the two sessions.

**Code-supported inference:** compile and per-basis masks can amortize. Each requested cofactor still incurs execution or retrieval policy, result delivery and its guard. A BDD returning a restricted compact function has a different contract until complete cofactor delivery is charged.

## Count, SAT and equivalence: fast tiny enumeration does not remove task mismatch

Balanced-k8 CSE/CM count takes 0.757/0.890 ms; direct SymPy exhaustive count takes 22.107 ms. CM preparation is 31.9% of its phase caller, and common JSON input loading is 38.8%. This compares packed enumeration to a truth-table generator. It does not establish competitiveness against structural exact counting or a mature symbolic counter.

Balanced-k8 SAT CSE/CM/SymPy medians are 0.588/0.762/1.485 ms; equivalence medians are 0.792/0.944/1.148 ms. Contradiction-k4 shows submillisecond totals on all arms. Witness/status outputs are exact. The small width makes exhaustive packed execution cheap; no result generalizes to many-variable SAT.

**Code-supported inference:** the explicit packed arms calculate `2**n` bits before extracting a tiny answer. SAT can stop after one witness, equivalence can solve a difference miter, and structured counting can combine counts without emitting every assignment. They solve a smaller output task. A CM rewrite to a constant may remove operations, but a request for full ordered packed output still fixes its representational width. The responsible classes are task/algorithm mismatch, CM representation preparation, and output/kernel cost—not mathematical inability to express the answer.

## Expression delivery is dominated by minimization and verification

Balanced-k8 CSE/CM into the same `SOPform` minimizer takes 69.355/66.369 ms and delivers exactly 996 bytes in both arms. SymPy default/forced takes 75.659/76.374 ms. All are semantically exact and satisfy the measured quality contract. The small CSE/CM difference is not a CM advantage claim: the same minimizer and exhaustive guard dominate and can vary between observations.

In the CM phase pass, exhaustive semantic verification is **68.9%**, the shared SymPy minimizer **28.4%**, JSON input **0.7%**, and expression-quality inspection **0.6%**. Compiler contribution is correspondingly small. This directly demonstrates why calling the whole result a CM kernel time is misleading. In the successor Y05 worker, its semantic verification is likewise inside `task_total_ns` despite a contrary docstring/contract label; that source-bound finding is in `WRAPPER_AUDIT.md`.

**Unknown:** the new diagnostic cannot reconstruct historical unmeasured verifier subspans. It also does not identify a CM-native simplified-expression delivery mechanism: this arm explicitly uses SymPy.

## Family CM has a distinct reuse mechanism and extra recurring work

| Treatment | Root hits | Persistent hits / misses | Root-only variants | CM core cache off / on (ms) | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| identical seed2, 8 variants | 7 | 15 / 17 | 0 / 8 | 2.844 / 2.120 | Whole-root reuse actually realized |
| shared seed2, 8 variants | 0 | 52 / 58 | 1 / 8 | 3.462 / 3.862 | Many subtree hits, no repeated root; net slower here |
| composition seed3, 5 variants | 0 | 0 / 5 | 5 / 5 | 2.880 / 3.380 | Negligible reuse actually realized: every root misses |
| mutation rate 0 | 0 | 26 / 33 | 1 / 5 | 2.198 / 2.190 | Rate zero still performs at least one mutation in generator |
| mutation rate 0.15 | 0 | 35 / 41 | 1 / 5 | 2.428 / 2.632 | Subtree reuse with preparation overhead |
| mutation rate 1 | 0 | 35 / 48 | 4 / 5 | 9.290 / 9.831 | Most variants require root-only caching; larger source construction |

Counters above are measured in separate diagnostic passes. Root-hit/mode context is an untimed reconstruction, not a timing estimate. Identical-root hit counts are not equivalent to total hit counts: the first expression already produces eight subtree hits. Negligible reuse is established by the composition seed3 case, not inferred from a high mutation-rate label.

**Code-supported inference:** shared associative classes make canonical flattening context-dependent, so baseline persistent compilation switches to root-only reuse. This is why structural sharing does not guarantee reusable subnodes across variants. Every attempted lookup still computes structural UID/digest context. Cache entries also retain nodes and potentially bound programs; enabled traced peaks exceed disabled peaks here, e.g. shared-seed2 core 167,480 versus 70,749 traced bytes. Tracemalloc does not establish total native retention.

The actual public family workload retains internal timing/diagnostics and validation. Its inner identical-seed2 total is 2.753 ms without persistence and 1.404 ms with it; the cache-enabled nested medians are 0.891 ms compile, 0.385 ms evaluation and 0.129 ms residual conversion/check/book-keeping. The surrounding reconstructed public caller is 4.749 ms because reference construction, family structural diagnostics and disclosed-fixture generation are also charged. In its separate phase pass, structural family diagnostics take 38.9%, inner family 34.6%, fixture generation 14.3% and references 10.4%.

For the zero-hit composition family, inner public total instead rises from 2.281 to 2.962 ms. Root-only misses retain five entries and provide no compile reuse. The public caller's cost is therefore neither identical to bare CM nor explained solely by root kernel speed. **Unknown:** per-lookup versus validation versus eviction time is not independently measured by this harness; the grouped compile span and profiles provide bounds, not exact subshares.

## What remains unresolved

- Windows process CPU resolution prevents reliable submillisecond CPU phase attribution; recorded zeros are not zero work.
- The unchanged assignment evaluator combines binding, execution, allocation and list conversion; those subshares remain null.
- Profile self times localize hot helpers but are perturbed; cumulative profiles are not additive phase partitions.
- Family cache counts do not separate leaf versus expensive-subgraph saved time. Root-only versus subtree regimes are identified, but exact saving per hit is unknown.
- The q64 treatment repeats four contexts. It does not represent 64 unrelated contexts, cache eviction pressure, arbitrary variable orders or high-width outputs.
- These tiny task cases do not establish broad SAT/count/BDD rankings. Frozen task-matched evidence is required for that part of the final report.
- Public-family statistics and explicitly delivered core-family relations are different caller contracts. Their full totals cannot support a pure wrapper subtraction.

No scientific disposition changed. These observations do not justify a routing
choice, benchmark claim, dependency installation, or push. The user separately
authorized committing the additive audit artifacts.
