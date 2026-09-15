# Frozen evidence audit

This is a diagnostic reinterpretation of recorded measurements, not a benchmark rerun or a change in scientific disposition. The exact baseline is `e334de594262059cc18cf37eaab56b0f79e94843`. No benchmark module was imported, no input fixture was loaded, and no new timing was performed for this sub-study.

## Provenance and reproducibility

The requested September 11 performance `REPORT.md`, September 15 development-gate directory, SymPy worker source, performance development ledgers, and continuation packed-panel ledgers are absent from the exact baseline checkout. The user explicitly requested those predecessor records. They were read from the original repository without editing it. `frozen_evidence.json` labels their origin `dirty_root_read_only_predecessor`; these bytes do not become baseline production code.

`recompute_frozen_evidence.py` uses only Python's standard library and reads the precise predecessor paths recorded in `frozen_evidence.json`. Its default refuses an existing output. The verification command recomputes and byte-compares without writing, from the isolated worktree:

```powershell
& 'C:/Users/brian/Documents/CM_Computation/.venv/Scripts/python.exe' -B 'docs/audits/2026-09-15-cm-time-attribution-deep-dive/recompute_frozen_evidence.py' --verify
```

The output records 45 source-file hashes and 26 comparisons against already saved predecessor manifest/source bindings, with **zero mismatches**. It reaggregates 186 SymPy cells, 1,296 performance development cells plus the separate strengthened-CSE records, 612 continuation development cells, 19,646 architecture-retry records and 27,648 Clang query-ladder records. It reads already measured lifecycle records that refer to previously consumed confirmation cases; no confirmation input or query trace is read, created or executed. Stored correctness flags are checked; semantics are not independently replayed in this arithmetic pass.

The initial arithmetic-script check failed because `serialization_ns_when_applicable` does not end in `_ns`. The script was corrected to use the actual complete timing dictionary. All architecture accounted totals then reconcile exactly. This was an analysis-field selection error, not an inconsistency in predecessor evidence.

Seven standalone invariant tests pass (`test_frozen_records.py`), checking complete stage reconciliation, same-row phase percentages, nested SymPy partitions, cold/warm separation, nine gate recomputations and predecessor matches, absence of fixture reads, and refusal to overwrite existing evidence. The final `--verify` also rehashes every predecessor read and confirms the full output is unchanged.

## Rules for the arithmetic

- A median phase divided by a median total is not generally an additive decomposition. Tables below use medians for descriptive latency, and same-row sums for aggregate phase shares.
- `caller_total = task_total + outside_task` and `task_total = named_stages + task_unattributed` are separate nested decompositions. Summing both partitions would double-count.
- `outside_task` is a measured difference. Its allocation to startup, imports, input decode, transport and process exit is **unknown** unless separately recorded.
- An unmeasured residual is not relabeled “wrapper overhead.” It can include validation, assignment generation, minterm construction, loop/control work and output operations.
- cProfile, tracemalloc, stored allocation observations and uninstrumented timings remain separate passes. Printed cumulative cProfile entries cannot be summed. Historical profile dumps are rounded to milliseconds and truncated to 25 functions, so they cannot reconstruct an exclusive helper ledger.
- Arm medians and phase shares across cases describe the recorded schedule. They are not a production request mix or causal estimate for another machine.

## Timer validity and overlap

| Evidence | Valid arithmetic | What the timer actually covers | Prohibited interpretation |
| --- | --- | --- | --- |
| Performance `development_raw.jsonl` | Per-case cold `total_ns` and separate `warm_ns` | Session decode, construction, queries and ordered byte delivery; warm repeats use existing session state | Adding warm to cold; treating warm as caller lifetime |
| Performance `stages.json` | Sum disjoint named `step` spans | Single diagnostic staged call; compiler includes all internal IR work; public execution includes binding and guards | Claiming a separately observed total; splitting kernel from guard/bind using this file |
| Performance `development_strong_raw.jsonl` | Separate `flatten=True` CSE results | Strengthened sharing-aware CSE run after identifying that earlier CSE did not request flattening | Pooling absolute timings with the first development run |
| Performance `fresh_process_timing.json` | Lifecycle, import and operation observations within each row | One build plus checksum delivery, harness imports and child shutdown | Using `fresh_process.json`, which includes a second traced build, as clean one-shot latency |
| Continuation packed-panel RAW | Exact `setup + query_delivery + cleanup = total` in every row | Serialized ingress/setup; one consumed query pass; explicit runner/cache release; warm pass occurs before cleanup but is separately timed | Adding first-chunk time or warm time; treating cache counters as cold-only |
| Architecture retry A/B/C | Exact sum of eight stage fields | Resident preparation, result representation and serialization, explicit `gc.collect()` | Complete caller latency; per-arm peak RSS; equating GC with complete object release |
| Architecture retry B | q64 only | q1/q4/q16 are correctness-prefix hashes inside a q64 request | Query-count crossover claims from these prefixes |
| Corrected Clang query ladder | Separate q1/q4/q16/q64; exact stage sum | One isolated child's resident work; measured child lifecycle is separate | Adding the enclosing child lifecycle to its already included resident stages |
| Architecture D | Whole nested task total | Stored as `evaluation_ns`, other outer stage fields zero | Calling `evaluation_ns` a bare kernel or saying prep/validation is free |
| SymPy Y02–Y05 | Named disjoint stages; residual against task; task against caller | Fresh child per cell, all compared runtimes preloaded before task timer | Attributing caller gain to CM evaluator or treating unnamed worker residual as API-only overhead |

Two field names are particularly misleading without code inspection. In architecture A/B, `compilation_ns` is hardcoded zero; CM construction and flat/CSE compilation are charged to `representation_construction_ns`. Flat-program mask binding occurs lazily inside `evaluation_ns`, while direct-expression column construction is charged to `binding_ns`. The phases are disjoint in time but their meanings differ by arm.

Architecture-retry `cleanup_ns` invokes `gc.collect()` while local `node`, `program`, environment and output references still exist. **Measured:** this span is large. **Code-supported inference:** it does not measure complete release of those live locals, and may collect garbage arising earlier in the resident process. The corrected ladder times cache clearing and leaves full release to an isolated child exit outside the accounted total.

## SymPy development gate: exact recomputation

All 186 ledger rows are `ok` and record `matches_oracle=true`. Nine geometric means of candidate/incumbent caller-time ratios were independently recomputed from within-contract, within-arm repetition medians. All match `REVIEW.json` to relative tolerance `1e-12`.

| Contract | Candidate / incumbent | Recomputed caller ratio |
| --- | --- | ---: |
| Complete relation | CM / SymPy truth table | 1.038364015450 |
| Assignment batch | CM / lambdify CSE off | 0.692280853666 |
| Assignment batch | CM / lambdify CSE on | 0.704257357669 |
| SAT status | CM / SymPy SAT | 0.938264533811 |
| SAT status | CM / PySAT Tseitin | 0.907559746218 |
| Equivalence status | CM / SymPy difference SAT | 0.994221792861 |
| Equivalence status | CM / PySAT miter | 0.984345326487 |
| Simplified expression | CM + SymPy minimizer / SymPy default | 0.912912894923 |
| Simplified expression | CM + SymPy minimizer / SymPy forced | 1.007271972510 |

The confidence intervals in the predecessor review were not reimplemented here. The gate's no-go remains: no matched same-evaluator ingress control exists in that predecessor, arms ran in fixed blocks, and no hard memory ceiling was enforced. A smaller caller ratio does not isolate the mathematical representation.

### How much is outside the worker task?

These latency medians pool repetitions and cases only to describe the recorded arm. Gate ratios above instead collapse repetitions within each independent case before comparing. These are different statistics.

| Arm | Caller median ms | Worker-task median ms | Outside-task share of caller aggregate |
| --- | ---: | ---: | ---: |
| CM complete relation | 1194.6728 | 0.3709 | 99.962% |
| SymPy complete relation | 1168.1477 | 2.0114 | 99.194% |
| CM assignment batch | 1101.0402 | 5.3816 | 99.509% |
| SymPy lambdify, CSE off | 1600.3981 | 269.6683 | 82.234% |
| SymPy lambdify, CSE on | 1537.1272 | 268.0784 | 82.738% |
| CM SAT | 1043.7188 | 2.6119 | 99.685% |
| PySAT SAT | 1215.4316 | 2.4453 | 99.732% |
| SymPy SAT | 1089.2401 | 52.3952 | 95.287% |
| CM equivalence | 1302.9289 | 0.6724 | 99.942% |
| PySAT equivalence | 1284.9143 | 0.3298 | 99.972% |
| SymPy equivalence | 1273.3646 | 60.1684 | 95.260% |
| CM + SymPy minimizer | 1280.6997 | 6.1652 | 97.268% |

**Measured:** caller totals and the much smaller nested task totals differ by these amounts. **Unknown:** the individual shares of interpreter startup, imports, JSON transport, parse/decode and shutdown. **Code-supported inference:** fixed arm order permits host/lifecycle drift to interact with algorithm differences; the residual is not evidence that CM reduced import cost.

### Worker totals include some harness validation

The worker docstring says validation is outside its timer. The executable boundary differs: `_result` reads the clock only after arguments have been evaluated.

- Y04 SAT computes `scalar_truth_values(expr, n_vars)` and validates the witness before `_result`; that exhaustive reference work lies inside `task_total_ns` and outside the named solver/evaluator stages.
- Y05 computes `_sympy_values(simplified, n_vars)`, packs and hashes the semantic vector, emits `srepr`, and computes expression quality before `_result`; those operations lie inside the task total.
- Y03 generates supplied-assignment bytes after starting the task clock. CM batching includes Boolean-array evaluation rather than complete-relation enumeration. The task residual therefore also includes input generation and packing.
- Y02 packs values and hashes the packed bytes inside the task total. The CM path has first expanded its packed bigint into a Python list of all Boolean answers.
- Y04 equivalence parses the right-hand expression after starting the task timer.

**Measured residual shares of task time:** CM assignment batch 86.937%, CM SAT 88.209%, PySAT SAT 94.275%, and CM + SymPy minimizer 67.684%. **Code-supported inference:** the named validation/input/conversion work contributes to those residuals. Its individual causal share is **unknown**; it was not separately timed. These are harness contract observations, not a finding that the public CM API requires exhaustive validation for scalar status requests.

## Architecture phases recomputed from recorded rows

### Complete relation, Linux/GCC retry

| Arm | Median accounted ms | Representation share | Evaluation share | Explicit GC share |
| --- | ---: | ---: | ---: | ---: |
| Dense CM full reinflation | 4.1082 | 5.04% | 6.44% | 86.95% |
| CM hybrid no reinflate | 4.0832 | 4.93% | 6.08% | 87.49% |
| CM recursive packed | 3.8741 | 5.31% | 2.59% | 90.56% |
| CM packed bigint | 3.9090 | 5.97% | 2.34% | 90.15% |
| CM packed words | 3.9661 | 5.85% | 3.41% | 89.21% |
| Structural CSE-flat | 3.6706 | 1.74% | 2.47% | 94.19% |
| Raw flat | 3.6211 | 0.84% | 2.52% | 95.03% |
| Direct expression BitSet | 3.5702 | 0.02% | 0.57% | 95.68% |

The direct arm additionally records 2.12% in mask binding. Flat arms put analogous binding inside evaluation. Consequently the apparent 0.57% versus 2.34% kernel gap cannot be read as an isolated packed-operation gap. The GC-dominated accounted task remains the original task; removing its cost would be a different diagnostic view, not a rescue of the scientific outcome.

### Corrected Clang restriction ladder

| q | Arm | Median accounted ms | Representation share | Evaluation share | Binding share |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | R2 | 0.2866 | 21.33% | 9.35% | 16.30% |
| 1 | CSE-flat bigint | 0.3537 | 41.45% | 14.74% | 1.01% |
| 1 | CM bigint | 0.6365 | 70.04% | 7.18% | 0.52% |
| 64 | R2 | 2.8418 | 2.58% | 23.63% | 44.65% |
| 64 | CSE-flat bigint | 2.6160 | 6.63% | 58.86% | 2.78% |
| 64 | CM bigint | 2.9550 | 18.63% | 51.21% | 2.44% |

The constructor contribution is **measured** and falls as a share when queries reuse preparation. Assignment order, representation, lowerings and query binding differ, so attribution within representation construction remains unresolved in this predecessor. The two verified interpretation reports establish R2 as best fixed q1/q4 and CSE-flat bigint as best fixed q64 on both historical hosts; q16 straddles parity. Compiler and CPU changed together, so their effects cannot be separated. All Clang incremental RSS values are zero and cannot calibrate memory comparisons.

## Development count and direct-versus-CM ingress

The continuation development panel is useful because `IndependentCountPlan.from_expr` and `.from_cm_node` reach the same family of decomposition/count algorithms, while the latter includes CM construction. At width 16 on the disjoint (`entangled0`) case:

| Method | q1 cold median ms | Separate warm median ms |
| --- | ---: | ---: |
| Direct | 0.7988 | 0.1414 |
| CSE-flat | 1.0648 | 0.1132 |
| Independent expression plan | 0.8070 | 0.0787 |
| Independent CM plan | 1.4865 | 0.0695 |
| Portable `dd.autoref` | 2.5896 | 0.3486 |

The 0.6795 ms difference between the plan cold medians is **measured** as a total difference, not an exclusive CM-build timer. The same algorithm receives a rewritten CM root on one path and a source AST on the other; preparation shape and interning can interact. The warm observations do not establish that a public wrapper crosses over, because these are explicit resident plans. Restriction uses q16 here, not q64. The separate September 11 performance count controls supply measured development q1/q64 cases.

`frozen_evidence.json` retains each continuation cache snapshot, separate traced peak/retention observation, count control, and per-case latency summary. Positional cache stats cover both cold and warm consumption in the original harness. They do not contain lookup-time or validation-time breakdowns. Traced memory excludes some native allocations; stored process RSS is not interchangeable with it.

## What cannot be concluded from this evidence

1. No source provides an exhaustive non-overlapping caller-to-kernel decomposition with CPU time, helper counts and retained bytes for every requested implementation.
2. No predecessor isolates how much IR time is UID construction, associative rewriting, sorting, interning, support propagation or Python object management. The old truncated profiles identify possible helpers but do not quantify that whole partition.
3. The public-wrapper 0.89/1.00/3.09 image discussed in the research report lacks a recovered raw paired ledger in this selected evidence chain. Algebra says its displayed whole-call excess over bare evaluation is `3.09 - 0.89 = 2.20` control-time units, or 71.20% of displayed public time. It does not identify which phase paid that amount, establish exact timing compatibility, or predict amortization.
4. SAT, count and equivalence controls solve scalar requests without necessarily retaining all assignment answers. A CM relation's complete-information semantics cannot alone explain runtime of a CM IR batch evaluator that never constructs the full relation.
5. No universal best backend, native-CUDD conclusion, production savings or routing threshold follows from these records. Portable `dd.autoref` is a specific Python symbolic control.
6. Startup/import/kernel causes can interact with order and residency. Differences of totals are valid diagnostics but are not automatically causal percentages.

The new study can use measured direct-versus-CM controls to refine these boundaries. Any unresolved cause requires evidence from a matching boundary and lifetime; no implementation optimization or new scientific promotion is implied here. **All predecessor scientific dispositions remain unchanged.**
