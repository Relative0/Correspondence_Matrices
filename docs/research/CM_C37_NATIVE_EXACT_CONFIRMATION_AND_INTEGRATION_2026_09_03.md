# C37 native exact confirmation and guarded integration

Date: 2026-09-03  
Scope: exact, non-neural repeated restrictions and sibling-output evaluation  
Status: prospective local confirmation passed; guarded integration added; disabled by default

## Outcome

The exact native slot executor and native multi-root union both transferred to fresh,
parameter- and truth-disjoint cases without training, policy fitting, gate changes, or
method changes.

Evidence run:
`docs/recognition/runs/c37-native-exact-confirmation-windows-20260903-001/`

- 18 fresh single-root cases: three arithmetic generator families at each support width
  11–16;
- six fresh three-output sibling-root workloads;
- 12 balanced single-root blocks and 20 balanced multi-root blocks;
- 954 raw sessions;
- 44,928 single-root query checks and 48,384 multi-root output-query checks in the
  independent verifier;
- zero exact output, schedule, source, artifact, ABI, identity, summary, or decision
  mismatch.

### Single-root result

| Measure | Confirmed value | Frozen gate | Result |
|---|---:|---:|---|
| Aggregate case-median speedup over Python R2 | 1.4720x | >=1.10x | pass |
| Minimum case-median speedup | 0.9889x | >=0.95x | pass |
| Minimum width-aggregate speedup | 1.1638x | >=1.00x | pass |
| p95 session speedup | 1.8199x | >=0.95x | pass |
| Maximum native workspace | 23,168 bytes | <=64 MiB | pass |
| Speedup over `uint16` projection | 1.4081x | reported control | — |

The only individual case below parity was one width-11 adder-tree at 0.9889x, within
the frozen 5% no-regret allowance. Every support-width aggregate passed.

### Multi-root result

| Measure | Confirmed value | Frozen gate | Result |
|---|---:|---:|---|
| Aggregate union speedup over separate roots | 1.2851x | >=1.10x | pass |
| Minimum workload-median speedup | 1.2784x | >=1.00x | pass |
| p95 session speedup | 1.3839x | >=0.95x | pass |
| Node reduction on every workload | yes | required | pass |
| Union workspace no larger on every workload | yes | required | pass |

All six individual multi-root workloads were between 1.2784x and 1.2894x faster.

## Freeze history and scientific boundary

Two packages aborted before a dataset or timing result existed:

1. V1 inherited a portfolio admission cap unrelated to this evaluator and rejected a
   fixed expression before creating a dataset.
2. V2 removed that cap, then the mandatory freshness check found three nominally new
   generator rows whose low arithmetic cones were truth-identical to C36 because high
   operand bits could not affect the selected output.

V3 replaced those three rows by an explicit effective-width rule, sealed all source,
compiler, interpreter, ABI, binary, schedule, and gate identities, then created and
independently verified the dataset before the one-shot timing run. The aborted V1/V2
manifests and binaries remain under
`docs/recognition/c37_native_exact_confirmation/`; they are not confirmation evidence.

Frozen V3 identities:

- dataset SHA-256: `f5ad98f83551b3abeb59f26c101408a445a2a2498817487db482356b88f08892`;
- freeze SHA-256: `5d7c9a98c92ac4c15250945f741219fe482019da6e2c94d257894fa38c47023c`;
- native DLL SHA-256: `0f4510685988150b75ebf9579f8784c61ed90d49aee8ea17649f94a94134eb02`;
- results SHA-256: `83f84a8fb2e80419b12a367d7c4f2e23f9cf9157416cdb03b296aee81d7e7a88`;
- manifest SHA-256: `358e74c3e601703757ca4717280c7018c6de895be58b37084f0cda0a24725856`.

## Guarded integration

`cmbench/backends/native_restriction.py` provides exact single- and multi-root engine
objects. It is disabled by default. Opt-in activation requires all three environment
values:

```text
CM_NATIVE_FUSED_SLOTS=1
CM_NATIVE_FUSED_SLOTS_LIBRARY=<absolute or resolved library path>
CM_NATIVE_FUSED_SLOTS_SHA256=<expected 64-character SHA-256>
```

The boundary validates the file hash before loading, requires native ABI v1, validates
the serialized DAG during compilation, and preserves output order. Disabled flags,
missing configuration, missing/changed binaries, load/ABI errors, compile refusal, or a
runtime native error all use the exact Python R2 evaluator. A runtime failure disables
the native object for subsequent calls. Invalid restriction partitions are rejected
before either backend.

The confirmed DLL is a local Windows/MSVC artifact, not a portable release binary.
Other machines should rebuild from the sealed C source and run their own identity-bound
confirmation before enabling it.

## Regression verification

- focused confirmation/native/projection/restricted surface: 26 passed, 2 skipped;
- broad non-neural suite: 1,240 passed, 2 skipped, 1 unrelated failure, 1,127 subtests
  passed, and four existing `dd` shutdown warnings;
- the unrelated failure remains
  `test_generated_chart_data_is_current_and_pages_reference_it`: the pre-existing
  generated JavaScript records revision `5dd6ec77...`, while its current renderer emits
  `d2643523...`;
- original CM benchmark smoke at sizes 4 and 8: CM, Bitset, SymPy, and BDD-to-SOP exact
  checks all passed; scratch CSV/HTML outputs were removed afterward;
- post-integration replay found zero frozen-source and run-artifact hash mismatches.

## Relationship to the published expert benchmark

This work is non-neural, but it is not a replacement measurement for the original
straightforward CM-family build/materialization charts on `expert.html`. It targets a
newer exact resident-engine contract: 64 partial-context restrictions and, separately,
three sibling outputs. Updating the public CM-family charts with these numbers would
mix task contracts and would be misleading.

The appropriate public follow-up is a separately labelled repeated-restriction section
or benchmark campaign that includes the guarded native executor, Python R2, projection,
and relevant CM/CSE controls under the same exact output contract. No public site file
or production default was changed by C37.

## Next controlled work

1. Repeat the sealed V3 package on a physically independent machine/compiler build.
2. Exercise the guarded boundary in shadow/opt-in use while always retaining Python R2.
3. Build a separately labelled public repeated-restriction benchmark rather than
   altering the legacy CM-family chart.
4. Revisit routing only if a new exact backend creates measurable per-case oracle
   headroom. On the exposed C36 development set native already won every case, so a
   learned or structural selector is not currently justified.
