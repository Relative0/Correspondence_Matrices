# Exact-control contract audit — 2026-09-14

## Scope and conclusion

This audit inspected the preserved campaign adapters and evidence in the consolidation checkout, then reviewed the newly implemented controls and their saved local results. Historical filenames are evidence identifiers, not endorsements of their attribution. The recorded successor campaign's exact-count lane measures Ganak against d4; its biology lane measures a Python scalar exhaustive oracle against native AEON. Neither comparison establishes a CM mechanism advantage. The historical name `bnet_cm_scalar` must be described as **scalar BNet oracle** in successor analysis.

The new control audit executed existing local Windows and WSL environments without installation or paid remote execution. Its 22 closed-model native checks and ten small-model scalar/CaDiCaL comparisons are verified correctness evidence, separate from the historical campaign and from any future performance experiment. This document's reviewer inspected source, reproduced bounded wrapper gaps, and independently rechecked saved counts, input hashes and witnesses. Historical artifacts remain unchanged.

Paths below are relative to `C:/Users/brian/Documents/CM_Computation/tmp/cm-consolidation-20260914`. `CAMPAIGN/` abbreviates `docs/audits/2026-09-13-cm-benchmark-campaign/`.

## Verified historical adapter contracts

| Control | Input and result | Validation and preprocessing | Boundaries |
| --- | --- | --- | --- |
| Ganak exact | DIMACS CNF; full-universe count intended. Executes `--verb 0 --prob 0 --appmct -1 --threads 1 INPUT`. | Requires exit 0, exactly one `c s exact arb int N`, exactly one SAT/UNSAT status, and zero iff UNSAT. Native preprocessing remains solver controlled. | Native exact counter, not CM. Historical adapter accepts support directives without checking their semantic validity; the selected exact campaign cases avoid this by requiring zero declared support variables. |
| Ganak projected | DIMACS CNF with nonempty `c ind` or `c p show` visible set. Same deterministic exact invocation. | Integer count and status checks as above. Hidden assignments are existentially collapsed by the intended native projection contract. | Historical projected lane has one native arm only. No CM speedup comparison and no second native projected oracle on the selected corpus. |
| d4 exact | Plain DIMACS CNF; rejects nonempty support/projection set. Executes `-i INPUT --cache-size-first-page 268435456 --cache-size-additional-page 67108864`. | Requires exit 0 and one `s N` nonnegative integer; derives SAT/UNSAT from N. Native preprocessing remains solver controlled. | Exact incumbent, not CM. Cache change repairs a resource-contract collision; it is not an algorithmic CM improvement. |
| CryptoMiniSat SAT | Line-oriented CNF plus explicit `x` clauses. Each XOR clause requires odd parity of signed literals. | Exactly one status; SAT exit 10, UNSAT exit 20. SAT requires all declared variables and independent evaluation of original CNF/XOR constraints. | SAT witness checking is meaningful; UNSAT is trusted solver status, without an independently checked proof. This adapter is smoke evidence, not a timed SAT arm in the core successor plan. |
| Python scalar BNet | Parsed `targets,factors`; constants, identifiers, negation, conjunction, disjunction; closed under declared targets. | Enumerates every target assignment and checks every original update function equals its target. No expression evaluation through Python `eval`. | Independent bounded exhaustive oracle; default at most 20 variables, campaign at most 16. Its historical CM label is misleading. |
| Biodivine AEON | Same closed BNet input, parsed independently again by AEON. | `BooleanNetwork.from_file(...).infer_valid_graph()`, `FixedPoints.symbolic(AsynchronousGraph(network))`, then `vertices().cardinality()`. | Native symbolic fixed-point control; no per-witness validation in this count-only adapter. Graph inference is part of this arm's measured work. |
| PySAT local projected oracle | `ProjectedCNF` in memory, with explicit projection tuple. | Native `Cadical195`; repeatedly solve and block visible assignment only. Scalar oracle independently enumerates all assignments then deduplicates projections. | Exact enumeration, not specialized native #SAT. Projection and solution bounds are 20 and 2^20; no intrinsic wall timeout, so a bounded worker is required. Supports empty projection in memory, although historical text parser rejects it. |

The counting parser permits split clauses and multiple clauses per line. CryptoMiniSat's parser deliberately rejects split or multi-clause lines and requires the total ordinary-plus-XOR count to match the header. Admission must preserve this distinction rather than treating a general CNF parse success as native-XOR admission.

## Historical gaps and their impact

1. **Exact versus projected directives are conflated.** `parse_counting_dimacs` collects `c ind` and `c p show` into one tuple and loses declaration type/presence. `mode="exact"` ignores the tuple for its Python oracle but `run_ganak` forwards the original bytes to native Ganak. An arbitrary support is not necessarily independent. Example: `p cnf 3 1`, `c ind 1 0`, `1 0` has full count 4 and visible count 1. The local scalar and Cadical oracles both returned 4 in exact mode; that does not validate forwarding the directive to a native counter. Future exact control should explicitly reject or strip declarations under a recorded policy, and projected control should preserve the visible-set meaning. Explicit empty declarations must remain distinguishable from absent declarations. The existing eight selected exact cases have zero support variables, so this gap is not evidence that their recorded counts are wrong.

2. **Native count range is unchecked.** Both historical adapters accept an integer larger than `2^variables`; projected counts additionally need the tighter `2^visible_variables` bound. A local mocked-subprocess probe accepted 999999 from both adapters on the existing three-variable `exact.cnf`. This is a verified parser gap, not a native solver correctness failure.

3. **Conflicting witness literals are silently overwritten.** CryptoMiniSat's witness dictionary accepts `v -1 1 -2 0`, retaining +1. The existing two-variable XOR fixture accepted this malformed witness and returned `(True, False)` in a local mocked-subprocess probe. A strict successor must reject contradictory duplicates and malformed terminators, while still evaluating the final complete witness against the original constraints. UNSAT proof checking remains separate.

4. **Path and output limits are weaker than their wording.** Native count, SAT, and AEON resolve the source before checking `is_symlink`, which hides a direct symlink from that check. Output limits are checked after `capture_output=True` has buffered output, not during production. Input byte limits likewise follow an entire file read. These are implementation boundaries to correct in successor wrappers or document under an enforced bounded worker; they do not by themselves invalidate the frozen results.

5. **Failure categories are not fully implemented by the historical worker.** V1 generally records adapter exceptions as `worker_error`; the finalizer separates known Ganak deadlines, undeclared-regulator rejection, and d4 signal-6 abort from logs. V2 catches `TimeoutError` as `timeout` with `reason=adapter_deadline`, but other validation errors, missing executable/imports, solver aborts, and wrong witnesses remain generic worker errors. Pair count disagreement is detected only in summary as `failed_correctness`. An explicit future result should separate admission rejection, unavailable, timeout, resource exhaustion/native abort, parser/protocol failure, wrong answer, and not-run. Never turn any of these into a zero count.

6. **Resource fields do not cover equivalent processes.** `cpu_ns=time.process_time_ns()` and `rss_highwater_kib=RUSAGE_SELF` describe the Python worker. They exclude child native solver CPU/RSS but include in-process AEON/scalar work. They cannot support cross-arm CPU or memory claims. `wall_ns` includes lazy imports, parsing, native process launch and solve, and AEON inference; it excludes outer worker startup. `parent_wall_ns` includes outer startup. End-to-end and isolated solver timings must be labeled separately; whole-process-tree resources require different instrumentation.

7. **No native SAT/#SAT fixed-point control existed in these historical arms.** AEON/scalar count agreement checks semantics on small closed networks, but cannot attribute a CM mechanism. A direct parsimonious fixed-point CNF with native SAT/count controls is the missing comparison described below.

## Evidence and bounded verification

The successor frozen ledger contains 108 terminal cells: 105 successful and three Ganak timeouts. Biology has 30 successful paired repetitions on ten closed models. Exact count has 21 successful paired repetitions on seven cases; the eighth case completed only with d4. Thus zero paired mismatches does not certify that eighth count against Ganak. Timed-out repetitions are absent from paired speed ratios and must be reported separately.

The historical first screen had 60 undeclared-regulator failures, 24 d4 native aborts, and 18 Ganak deadlines classified from worker logs. The d4 correction report identifies a default eager 4 GiB cache allocation colliding with the worker's 4 GiB address-space limit. The postfix Linux report records smoke counts 4 and 0 with explicit 256/64 MiB cache pages, then seven of eight corpus cases finishing under a 30-second bound and one timeout. This supports the diagnosed resource-contract repair without converting aborted results into algorithmic losses.

The preserved Linux smoke stdout records Ganak exact/projected/UNSAT counts 4/2/0, d4 counts 4/0, CryptoMiniSat SAT/UNSAT with validated `[true,false]` witness, Kissat exits 10/20, and AEON/scalar count 2/2 under a 4 GiB address-space limit. This audit read the frozen smoke evidence without replaying that historical package. New native controls were executed separately as recorded below.

On 2026-09-14 the preserved checkout interpreter `C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe -B` ran bounded, non-writing probes from the consolidation checkout with `unittest.mock.patch` of native `subprocess.run`. Results: Ganak impossible count accepted = 999999; d4 impossible count accepted = 999999; conflicting-duplicate CryptoMiniSat witness accepted = `[true,false]`; invalid-support example full count = 4 for both scalar and actual installed Cadical195. These probes isolate wrapper acceptance; they do not establish native projected behavior for arbitrary directives.

## Implemented successor controls and verified local results

`cmbench/biology_controls.py` now implements deterministic parsimonious CNF, explicit `bnet_scalar_oracle`, original-equation witness validation, and native `Cadical195` fixed-point enumeration. Negation is a signed literal; every constant/conjunction/disjunction auxiliary has a full equivalence. Both clamp and condition semantics are explicit. The tests check all auxiliary extensions for each original assignment on small fixtures, in addition to comparing counts and original witnesses.

`cmbench/backends/exact_controls_v2.py` preserves historical adapters while adding strict wrappers. Exact mode strips untrusted independent-support hints during normalized CNF serialization and rejects explicit projection directives; projected parsing requires explicit `c p show`, including the empty set, without confusing it with `c ind`. Exact count results are bounded by the declared universe. Source paths are checked for symlinks before resolution, including parent components, and checked bytes are copied before solver invocation. SAT output rejects contradictory literals, missing/followed witness terminators, and witnesses accompanying UNSAT. The local projected enumerator explicitly registers free visible variables and handles an empty clause as logical UNSAT before passing clauses to PySAT, avoiding the observed python-sat 1.8.dev20 `Cadical195` empty-clause bootstrap error. These are successor fixes; no historical measured adapter was rewritten.

`cmbench/benchmark_contracts.py` provides structural admission for future attribution results: mechanism and preprocessing labels, separate timing phases and memory scope, input/query/source identities, distinct failure states, explicit SAT/count outputs, and witness provenance. An isolated-effect category requires a CM arm, ablation identifier and evidence hash. This is expressly a structural validator; callers must verify the referenced evidence and actual ablation. It neither certifies an effect from a label nor implements the general future benchmark runner.

`scripts/cm_biology_control_audit.py` prepared inputs and ran the new correctness controls. `LOCAL_CONTROL_RESULTS.json` records 22 closed models with BNet/CNF hashes and target/auxiliary dimensions. The ten models with at most 16 targets have matching exact scalar and native CaDiCaL counts, with original-model witnesses whenever satisfiable. The other twelve are explicitly outside the local scalar width cap; they are not failures or zero counts. This phase used Windows with python-sat 1.8.dev20.

`NATIVE_CONTROL_RESULTS.json` records all 22 models in the existing WSL environment with AEON 1.4.2 and hash-checked native binaries. AEON, d4 and Ganak exact counts agree on every model; CryptoMiniSat's SAT decisions agree with whether those counts are positive. All 88 arm checks succeeded under five-second per-arm deadlines: zero timeouts, backend errors or count mismatches. AEON and CryptoMiniSat produced checked original-model witnesses for all 15 satisfiable models. The seven zero-count models correctly have no witness. d4/Ganak are count-only arms: their records explicitly identify the companion CryptoMiniSat witness source and do not pretend the counters produced witnesses.

Independent read-only verification recomputed all 44 retained BNet/CNF input hashes, checked all 22 three-counter agreements and SAT decisions, and re-evaluated 30 AEON/CryptoMiniSat witnesses plus 16 scalar/CaDiCaL witnesses against the original BNet equations. The ten small-model scalar/CaDiCaL counts also agree with all three native/symbolic counts. This confirms the saved result contents without rerunning the expensive checks. Diagnostic elapsed values are not benchmark speed measurements and establish no CM advantage. The real-model checks are **unperturbed fixed points**; clamp-versus-condition semantics have fixture coverage, not a completed real-model session campaign.

## Remaining future experiment work

The local correctness runner is deliberately narrower than the planned performance experiment. Whole-process-tree CPU and memory accounting, streaming input/output caps, comprehensive worker failure classification, frozen repeated query schedules, mechanism-on/off comparisons, and split cold/preparation/warm/total-session measurements remain part of the future runner specification. Existing wrapper output limits still operate after buffering; the new structural result schema does not repair that resource boundary by itself. A source-path symlink check is not a general race-free filesystem sandbox.

Future measurements must include parse/encoding/setup work in end-to-end cost and separately charge any companion witness control. Solver-only costs may be additional diagnostics. Freeze source/CNF/query hashes and variable maps, use equivalent solver/version/thread/timeout/resource policies, and evaluate real-model clamp/condition sessions under their declared semantics. Clamp replaces a target's update equation; condition retains it and constrains the target. Unspecified regulators remain admission failures until an explicit input-variable or parameter contract is implemented. Additional randomized closed-network property coverage would strengthen the deterministic encoding tests but is not a claim about the completed corpus checks.

Any subsequent CM performance claim additionally requires an actually implemented CM arm, matched output semantics, mechanism-on/off controls, and the same case selection. Native baseline validation alone cannot establish that claim.

## Successor source and result identities

Additional local native projection probes are recorded in `PROJECTED_NATIVE_PROBE.json` (claim L03). On `p cnf 3 1; 1 0`, plain exact Ganak returns 4 but the invalid hint `c ind 1 0` changes its output to 1. Ganak rejects simultaneous `c ind` and `c p show` directives. Explicit `c p show` returns the expected hidden-multiplicity count 2, empty-projection SAT count 1 and UNSAT count 0. `run_projected_ganak_v2` now normalizes away independent-support hints, preserves the explicit projection (including empty), validates status and projected-universe bounds, and passes four actual native wrapper checks. This closes the clear local protocol gap without turning the historical unpaired projected lane into a CM comparison. Weighted counting directives are rejected by the successor unweighted contract.

The following hashes bind the implemented controls and verified result bytes. They are separate from the historical identities below; no audit-document hash is used as a substitute for source or result evidence.

| Relative path | SHA-256 |
| --- | --- |
| `cmbench/biology_controls.py` | `968b23c20c73ca8ef8513c559d5ca26acbc43348474da0a614ce052836e50a2c` |
| `cmbench/backends/exact_controls_v2.py` | `7d604c516ead3868d2b64d165a6ef95537b196fcf310873ec1502daf6d3b6a9c` |
| `cmbench/benchmark_contracts.py` | `0649844b041ebdf07b5895db20fc4fe5083e6fe4f30ecf23b8455767f667a1c8` |
| `tests/test_cm_biology_attribution_controls.py` | `6a2c0dd2b2a78c0ecee36603807e237c506ad20c88550e30cc7df0ea41f039de` |
| `scripts/cm_biology_control_audit.py` | `b5feef563fad49807b749ee5a5c876ad30ce26f41565062c4ae728cd70fb749a` |
| `docs/audits/2026-09-14-cm-benchmark-attribution/LOCAL_CONTROL_RESULTS.json` | `34e9e548383d1b459451036e1ece13b6fcda6a32c9b5411415f5da26bab6bf95` |
| `docs/audits/2026-09-14-cm-benchmark-attribution/NATIVE_CONTROL_RESULTS.json` | `3bb7ee7e916f2bb5f0bb1d5ccd2e933270a7df6ede4d3908230af2cb59997001` |

The current local WSL d4 binary is `94b265f035e8ea366957b192fc31055f19901f9231abdd9de839414c3d07e5cf`, distinct from both historical d4 builds listed below. The native results bind its recorded WSL runtime using SHA-256 `ca71ef5b2d27180e064dc8b43e1ee3a37acb87fd3ff6da7bb093d422ea9582f9`. Current Ganak and CryptoMiniSat binary hashes match their historical identities below.

## Artifact identities

Hashes were computed over actual local bytes with SHA-256. These identify the inspected historical baseline, even when successor modules are added alongside it.

| Relative path | SHA-256 |
| --- | --- |
| `cmbench/backends/native_count.py` | `dc44b8961623ecfff897cc57ea4616de352d23d6b6d408b05c3be03768e1802d` |
| `cmbench/backends/native_sat.py` | `f46218ce04a84d567cf166dd518bf04e90dd099ab3b02112c3933040b7bb591d` |
| `cmbench/backends/projected_count.py` | `7b2f52e40ba5bb0f68c0c20c34b64b1a30495503b34ed75f3893c84560c4a13b` |
| `cmbench/biology_bnet.py` | `67769b55d962aa8b3b06f17749033864b457a9a97195cff5adde6adb2d56dd81` |
| `scripts/cm_benchmark_core_screen.py` | `92637f101559c5a05b7399d74d4a1550520b643f1b0cd6ba59744b5d67ed52de` |
| `scripts/cm_benchmark_core_screen_v2.py` | `6df590b69949bd7808f928da5f2ebdc2b15f6c6ae2d9356d99e8a2559e78877e` |
| `docker/cm-benchmark-smoke/NATIVE_LOCK.json` | `170fd248e7822d5d6b157930e2f90c461ecaa195ae33cc4bd14c2f086592688f` |
| `CAMPAIGN/runpod-successor-001/evidence/core-screen/ledger.jsonl` | `e07f23c8c41bf7560b328ac8ae1ff0c899616a0d5c500edeb22e1a54b4eed82e` |
| `CAMPAIGN/runpod-successor-001/evidence/RUNTIME.json` | `4b6934338230eabe01971d65976ee13d3eda3fe48c980e94d394075abaa2f112` |
| `CAMPAIGN/successor-results-analysis-001/RESULTS.json` | `b3c12ff2123b85e152974e8339aaca44ea73409cdbdb5ef7e3aae0e1d43a2dde` |
| `CAMPAIGN/wsl-successor-remote-replay-003/evidence/native-linux-smoke-v3.stdout.txt` | `a1e02358e6cc07019e93a800d7c1551888684aadeb70c63f9f2e59be0cfb48ce` |
| `CAMPAIGN/admission-d4-correction-001/REPORT.md` | `2df16402427dd6f0f4f0092a9f3dc2e4f53cc8b2ca75bc2d6439c314c8536380` |
| `CAMPAIGN/postfix-linux-smoke-001/REPORT.md` | `7b84a0075615d2c63b81ea17daff3a2552e64aa479530e2cf41bd85de8a179c9` |
| `CAMPAIGN/results-analysis-001/REPORT.md` | `d7c17f543f82077af887a9722238cd3a34f3795f091b133dc7404648ac688c59` |

Actual successor runtime binary hashes are Ganak `c43a7d7c6d1e2ba438ee72541ceb15bc81b414bff5aa22038a9f6baa9f82bb61`, CryptoMiniSat `774b55032f6c6d64948e73c8b10ba373002c4b7f5a545056180cefb9311303ab`, and d4 `d1347702218104b9c4b4846550ca7394aa757990aec36e930a2615f17587d790`. The lock's d4 binary hash is instead `e76b48375fc35ed6d3ebea44a94ad8f2fb914c7049e1ab0a5d466c0202f1e205`; use the actual run identity for measured results. Both records identify d4 source archive `f3263aa02cb4229f81df79cdaa624e508cec7a7fba754f9efa9bcd64ce11478d` at revision `15eff31962466804a48374826b9e5a746fc2766e`. A source revision alone does not uniquely identify a compiled binary. AEON runtime is 1.4.2 with wheel hash `7084f222407d31220569fe9f1c1ed31c5ce6a04d2497e9e28811aa1ea97d70f3`.
