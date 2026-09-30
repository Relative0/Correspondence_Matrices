# Gate A: Contract Alignment and Pre-Freeze Qualification

## A. Gate verdict

**NO-GO — do not freeze or run the confirmatory experiment.**

The manuscript, clean source snapshot, Protocol v4, endpoint harness, raw-row schema, analyzer, generated corpora, schedules, natural intake, and native comparators now describe the same computational objects within their declared scopes. Native CUDD and ABC/Yosys are no longer blockers. The one remaining blocking discrepancy is the timing environment: every completed non-confirmatory pilot failed the predeclared requirement that all 200 primary case/arm controls have `MAD/median <= 0.05`. Timer-call overhead passed in every completed pilot.

No confirmatory benchmark was run. No confirmatory result was opened or inspected. No Frozen Execution Prompt is supplied. Section N points to the successor repair prompt.

## B. Artifacts and final source identity

The primary manuscript PDF/TEX, companion foundations PDF/TEX, recovered deep audit, revision history, Protocol v3 evidence, current repository source, and v4 working artifacts were inspected. The recovered audit is `outputs/evidence/CM_Compiler_Deep_Audit_2026-09-22.md`, SHA-256 `f673f6e53ca106901a36bfcbcaf56bd48d7d2a4289c9f9a66e9217273d049a4d`.

Repository: `https://github.com/Relative0/Correspondence_Matrices`

Qualified source commit: **`0ab8ffd0c23ffa71ee951d375b1c170ffdcc084b`**.

The isolated repository was clean at final reconfirmation. Its 187-file dependency closure remains byte-equal to the recorded SHA-256/length list and to every Git blob at that commit. Closure-list digest: `59bf13d09c18fc8762bd5662cc337c96506114f209c98577bfdf2c3918d8fec4`. `FINAL_SOURCE_IDENTITY_V4.json` has SHA-256 `e6faa49782cc66dbb5c044e0a54842f84f2dc0bee16aad33f9c1d8665d082f37` and embedded identity digest `db6999392b87f6e2e8f56dbf3551d87d87f0812443509c2b600e8b4d6bd3d243`.

The user's separate checkout `C:/Users/brian/Documents/CM_Computation` was read only. It remained at commit `9a8ec9172fa1ba841c7960d088b94ef04c67c9b8`, with 312 porcelain-v2 entries and status digest `a209b853fb15149edb0131256ccc4516b586ba421d300fa21d9bd1d39ac75778`. It was not cleaned, reset, restored, staged, or edited.

No production source repair was made. Every Gate A repair is external and individually hash-bound in the non-authorizing candidate manifest.

## C. Manuscript–source–protocol contract matrix

The final matrix is `outputs/v4_freeze/CONTRACT_MATRIX_V4_FINAL.csv`, SHA-256 `3978ad9a61513ed35f3f522e9ab55980eccda5f625f94dd67e912bef80db59a9`.

| Contract | Manuscript/source/protocol result | Status |
|---|---|---|
| Pair-root compiler and fallback | Failed root construction discards speculative child pairs; token returns NoPair; dense wrapper recompiles the original root | Aligned |
| Frame, token, fixed-axis, dense output | True-first four-bit token; fixed-first ambient mapping; false-first declared dense axes; owned writable bool output | Aligned |
| Strategy and provenance | Requested pure/hybrid/retabulate is distinct from observed S/T/H/NoPair; provenance combination is non-idempotent | Aligned |
| Attempted/discarded work | Native metrics plus untimed probes record actual constructions, support scans, retention, and discard | Aligned |
| Cache and staging | Arm-independent identity-DAG reconstruction; complete workload-cache reset assertions; fresh worker per observation | Aligned |
| Primary/secondary designs | 100-case primary and 30-cell/900-case secondary population, endpoints, reuse, schedules, and exclusions are explicit | Aligned |
| Natural intake | 142 outputs selected before translation/pairability; provenance, licenses, tools, commands, source and translation hashes frozen | Aligned; pairability deliberately unobserved |
| Native ROBDD | dd 0.6.0 / CUDD 3.0.0, fixed order, no dynamic reordering, fresh manager | Aligned; 1,000/1,000 untimed matches |
| Native AIG | Yosys 0.33 / ABC 1.01, one-output combinational AIG, current latch values treated as inputs, ABC CEC | Aligned; 142/142 untimed matches |
| Raw rows and analysis | Strict 125-field rows, independent equal digests on success, failure retention, schedule/manifest binding | Aligned |
| Timing environment | Single-call policy plus all-case repeatability requirement | **Blocking: no attempted environment passed** |
| Confirmatory state | Five registered append-only result files are empty | Aligned; unexecuted |

Protocol v4 remains required. Protocol v3 does not fully specify fixed ambient axes, request/outcome distinctions, cache/reset behavior, schedules, strict raw rows, failure retention, the primary bootstrap, or native/natural freeze inputs.

## D. Blocking discrepancies

| ID | Blocking discrepancy | Evidence | Required repair |
|---|---|---|---|
| V4-B1 | All-case repeatability failed | Completed pilots failed 17, 56, 14, and 20 of 200 controls; timer overhead failed zero controls | Move the unchanged v4 single-call experiment to a demonstrably stable host, or prospectively define Protocol v5 without relaxing the 0.05 limit; then pass a new full `pilot-*` run |
| V4-B2 | No final environment can be frozen | Mounted/native staging, CPU 0/11 affinity, and nice -20 did not satisfy V4-B1; host power policy was Balanced and recorded, not changed | After a pilot passes, bind exact host/power/affinity/priority/runtime/package/memory identities under a new freeze ID |

These are measurement-validity blockers. Native tools, natural translation, mathematical soundness, adapters, schema, analyzer, and source identity now pass.

## E. Reconstructed implementation boundary

The current compiler recognizes a requested pair only at the expression root. Primitive signed/permuted pair tokens are normalized to one row and one column frame. NOT transforms a recognized token. Same-frame Boolean fusion combines child tokens. Hybrid mode may exactly retabulate a rejected subtree over four assignments. Retabulate mode applies whole-root tabulation when the syntactic unfixed-variable rule permits it.

If root recognition fails, successful child pairs are discarded. The token API returns NoPair. The dense pair wrapper then compiles the original root through ordinary CM IR and materializes the requested artifact. There is no persistent local-rewrite pass.

`FV_F(e)` is syntactic free-variable support minus fixed bindings. Fixed bindings are applied before ambient axes while declared axes remain in the output shape. The direct adapter overrides overlapping ambient masks to enforce this rule. Fresh identity-DAG deserialization preserves intended sharing and equal-but-distinct structure without transferring attached programs or caches between arms.

The pair compiler is not identity-memoized. `N` counts occurrences; `U` counts distinct objects. Recursive work follows occurrences. The final harness also records real pair constructions, support scans, retained/discarded constructions, scalar evaluations, cache state, output ownership, digests, and failure dispositions.

## F. Finite mathematical core

The final checker ran **333,794 checks with zero failures**:

- selection: 64;
- query: 64;
- transforms: 192;
- complement: 64;
- signed alignment: 512;
- five Boolean fusions: 5,120;
- signed fusions: 327,680;
- all-token compilation: 48;
- all-token provenance: 48;
- worked implication: 2.

This verifies the enumerated finite token algebra and compiler cases. It is not an unbounded proof and contains no performance conclusion.

The recovered audit reports **1,083,999 reference assertions**, including 1,048,576 scalar fusion comparisons. That historical count is retained separately and is not added to the new 333,794 checks.

## G. Regression and qualification suites

Final retained successful counts from the final source/harness identity are:

| Check | Result |
|---|---:|
| Focused source suite | 147 passed, 0 failed |
| Required boundary suite | 17 categories, 95 passed, 0 failed |
| V4 adversarial schema/harness/analyzer suite | 20 passed, 0 failed |
| Primary untimed qualification | 100/100 oracle-equal; 100 pure-structural outcomes |
| Native ROBDD qualification | 1,000/1,000 oracle-equal; 0 failures |
| Native AIG qualification | 142/142 ABC CEC-equivalent; 0 failures |
| Finite core | 333,794 checks, 0 failures |

The 17 boundary categories cover invalid layouts; syntactic cancellation; fixed/ambient overlap; the raw packed counterexample; fixed-only and canonical-fixed rejection; fallback/discard; original-root dense fallback; requested versus observed outcome; all nine provenance fusions; negation provenance; pure-mode exclusion of tabulation; all tokens and dense ownership; independent dense calls; identity-shared versus equal-distinct nodes; pre-attempt output budget; semantic constants under syntactic support; and identical query endpoints.

The 20 adversarial tests additionally cover strict missing/unknown fields, invalid natural provenance, duplicate/missing/failed logical rows, illegal retries, schedule pairing, threshold equality, platform memory boundaries, independent correctness digests, fresh-worker output, append-only chaining, cache resets, fixed-first mapping, AIG latch combinationalization, and analysis manifest bindings.

`VALIDATION_EXECUTION_RECORD_V4.json` retains exact successful commands and setup failures separately. The final focused rerun initially lacked `requests`; the declared dependency was added. A full requirements installation could not build optional `pyeda` because Python headers were absent, but the focused scope did not import it. One post-test reporting wrapper mishandled shell variables after all four logs had already recorded success. These failures are retained and are not counted as test failures.

## H. Manuscript repair and PDF inspection

The working manuscript now states the actual pair-root boundary, syntactic support rule, fixed-first ambient contract, request/outcome distinction, provenance map, cache policy, primary estimand, separate historical/new check counts, completed native qualifications, and failed repeatability gate. It does not reintroduce formula-valued LM theory, higher-dimensional LM material, spectral material, or quantum-adjacent foundations.

Working TEX SHA-256: `af2588ace8f8a51c4768bac74296c6d103e51048f583209a84b765e4e9fb87bd`. Rebuilt 15-page PDF SHA-256: `0d6cb3e4c53b6ca88fa7650cf721e10fac71920471a288640b88daa9e76c5747`. All 15 pages were rendered and visually reviewed, with full-size inspection of the changed evidence and verification pages. There is no clipping, overlap, missing glyph, unresolved reference, or overfull box. Existing underfull paragraph warnings do not affect legibility.

The companion foundations PDF/TEX remains byte-unchanged. No objective cross-reference error required a companion edit.

## I. Protocol disposition

**Protocol v4 is required and materially complete, but it is not freeze-authorized.** Its SHA-256 is `bdf0983d485321279d17597bb508e7f780c35a2760032c9d0c0903b1a2ffc52e`.

It fixes the primary and secondary designs, delivered artifacts, fixed-first mapping, cache regime, fresh-worker boundary, timing and memory definitions, schedules, failures, sole primary statistic, paired hierarchical bootstrap, natural contamination barrier, and native comparators. It retains `R >= 1.20`, confidence lower bound `> 1.00`, and `M <= 1.10`; equality at the lower confidence boundary fails.

The protocol now records the completed native qualifications and the four failed exploratory pilots. Its STOP condition remains active. Any change to the timing estimand requires a numbered Protocol v5, updated manuscript/schema/runner/analyzer/tests, and a new pilot and freeze identity.

## J. Endpoint adapters, raw schema, and runner

The harness implements fixed-first ambient packed/dense mapping; raw request validation; complete cache-reset assertions; fresh identity-DAG reconstruction; arm-independent staging; token/scalar/packed/dense materialization; output ownership; correctness and oracle digests; actual attempted/discarded pair work; CUDD with fixed order/no reordering; Linux and Windows memory adapters; and retained failures/retries.

Successful rows now require an independently reconstructed direct-oracle digest equal to the arm digest. Oracle work occurs after the timed and peak-memory boundaries in a worker that then exits. The Linux candidate binds `ru_maxrss` converted from KiB to bytes; the analyzer rejects a memory metric different from the freeze manifest.

The ABC adapter is deliberately separate from token/dense estimands. It converts each preselected sequential AAG output into a one-output combinational AIG by treating current latch values as inputs, runs native ABC structural hashing, and requires ABC CEC against the raw one-output binary AIG.

Key hashes: `v4_harness.py` `8b5478d03df58d2a9e5928bd99f7709a9f6f0edde12e2614b0de12c1f74ee041`; `runner_v4.py` `e44a7312c106055a2983114b5ad645d45293d93728171ce694e231363a2b7e6a`; `row_schema_v4.py` `cd1ad00aac3296c97de5dccc6aecb1c7ed4c8fb68882a44a50600ba766fbd337`; machine schema `68a53176a5b281bbcd53ca1d2431aa0f2fd28c9eb060a6475bf402becf359ce0`; ABC adapter `59d2d79568c4b31177e1734d7f345f9111409beb04dde99a5fe567fde48fa8bd`.

## K. Corpora, natural intake, schedules, and analyzer

The primary corpus has exactly 100 distinct PCG64-seeded cases. Every case has `N=U=1023`, 240 primitive operators, 120 swaps, 64 signed literals, no fixed variables, token output, and `K=1`. Primary corpus SHA-256: `aa0cb2f1f4f665ee77ae0fa881a755eb1baa27971d870eec9e5680dc1049112b`.

The secondary corpus has 30 explicit cells and 900 cases spanning balanced/skewed sizes, identity sharing, equal-distinct and unshared structure, fixed-false/true/only/overlap cases, token/scalar/packed/dense artifacts, reuse `K=1/10/100/1000`, mixed/root tabulation, multiple-pair and non-pair boundaries. The repaired scalar cell has no ambient axes. Secondary SHA-256: `106f8ff3f7b25ca7a9ead7b501684160538f67d151492bc5fe62d8410b9b2cc0`.

Primary schedule hashes: time `58b0bcffe377e65de491e6add332bc60043047615e5d8b3a25567def92de32a2`, memory `bd0970045dd74b0fbb58742d1f8cbf8bac0f5b5f9158a3de9266c578c87d3a9f`. Secondary: time `0e5f05fa85593bcfea3d293717ff5fd4e474971b32538341a75f168592a670d4`, memory `a06d18bf0d4d30c3a8cafe64b830468ccda3490b61cfb4c4ddc882b2623a09a0`.

Natural provenance was frozen before any pairability pass. It retains source repositories/revisions, MIT/ISC licensing records, original hashes, exact staging, all failed and successful extraction attempts, and final translations for every selected output. Manifest SHA-256: `f55c5fcd6ae6ed661ae7c133a53607e8a7148ab8751d91b5400ee215b075ea47`. Pair compiler executed: false. Performance observed: false. Native AIG qualification SHA-256: `58cc7a90d6f94394bced1bfcf48d89e85386baa49643eb46ab5bad2c474a71d1`.

The native tool record SHA-256 is `86fdf3f07231272ce5b7266a49676092ca76cab431a634384cfb606ef1c65f62`; the CUDD qualification SHA-256 is `2288695c5c89a1dcf726d5a631198559876d691b3e683c546ed65abeb8a470c7`.

`primary_analysis.py` SHA-256 is `06cd18bf22d47f254ff646351281748ed61a5d3d95fdfe2cbc3161ab8b74c1ef`. It validates schema, manifest and schedule hashes, exact coverage/order, attempt sequences, correctness, environment memory metric, primary provenance, endpoints, and failure-free completeness. It implements the 100-case median of per-case 30-repetition median ratios, the paired hierarchical 20,000-draw PCG64 bootstrap at seed `2026092304`, and 15 independent memory repetitions.

## L. Immutable non-authorizing manifest

`CONFIRMATORY_FREEZE_MANIFEST_V4_NO_GO.json` is candidate `gate-a-v4-candidate-20260923-02-stability-no-go`. It is immutable evidence, not a confirmatory freeze. File SHA-256: `c45f98b48ada5cb3bd4c40bb67bd333625a5668ab55d48e6a3eda4e55ad8e538`.

The recursive validator checked every bound path/size/SHA-256 triple and returned `valid_candidate=true`, `authorized_freeze=false`, no failures, and `confirmatory_performance_inspected=false`. It binds source, all external repairs, manuscript/PDF, Protocol v4, schema, analyzer, corpora, schedules, natural intake, native tools and qualifications, candidate environment, pilot evidence, exact commands/logs, recovered audit, repair prompt, and five zero-byte append-only result files. Each empty file has SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

This candidate identity cannot be promoted or reused. A successful successor receives a new freeze/run identity.

## M. Non-blocking issues

The PDF retains harmless underfull-box warnings. The source requirements list includes `pyeda`, whose source build needs Python development headers in this WSL image; none of the qualified focused, boundary, finite, harness, CUDD, or AIG checks depended on it. A future fully reproducible environment should install and hash the complete declared dependency closure before a successor freeze.

Public archival identifiers, venue formatting, and an external human compiler/logic-synthesis review remain useful before submission but do not resolve or replace the timing-stability gate.

## N. Successor repair prompt; no execution prompt

Use `outputs/REPAIR_PROMPT_TIMING_STABILITY_V4.md`, SHA-256 `c8d6436bb2dc8d3532c96172c42c228f215407fff6a1a2e7432387413e5c494e`.

The preferred repair is to rerun the unchanged v4 single-call pilot on a stable, fully controlled host. If no host can pass, draft Protocol v5 prospectively with a robust timing unit that keeps preparation charged and workload caches/input reconstruction independent; do not relax the 0.05 threshold. Rerun every qualification and assign a new freeze identity after one full pilot passes.

**Final gate question:** Can a skeptical reviewer reproduce the algorithm, endpoints, charged work, corpora, schedules, raw rows, native comparators, and primary statistic? **Yes.** Can that reviewer reproduce a measurement environment that passes the prespecified all-case stability rule? **No.** Gate A therefore remains **NO-GO**.
