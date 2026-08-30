# W8 LogikBench acquisition authorization request

Date: 2026-08-30  
Status: proposed; no checkout or corpus download performed

## Purpose

Acquire a new, license-auditable formula/circuit source pool for the W8 untouched-confirmation freeze before any P7 comparative timing is inspected.

The existing local `YosysHQ/yosys-bench` checkout is pinned and ISC licensed, but it contains only 28 benchmark directories and several are sequential, generator-only, or otherwise unsuitable for the bounded complete-relation task. It cannot safely guarantee the W8 minimum of 30 eligible independent circuit clusters by itself.

The proposed source is the public `zeroasiccorp/logikbench` repository. Its project documentation describes 250 self-contained RTL benchmarks, per-benchmark provenance, and permissive licensing with benchmark-local overrides. The remote `main` identity observed read-only on 2026-08-30 is:

- repository: `https://github.com/zeroasiccorp/logikbench.git`
- commit: `891ced851ea4c2f9a46f6ab991eeee199e2fd516`
- project license: MIT, subject to stricter or different benchmark-local license files

## Exact local effect requested

Create only:

`C:\Users\brian\Documents\CM_Computation\external\logikbench-confirmation-20260830`

The acquisition will:

1. clone the named public repository with blob filtering and no checkout;
2. detach at exact commit `891ced851ea4c2f9a46f6ab991eeee199e2fd516`;
3. sparse-check out the root license/readme/metadata and only `logikbench/benchmarks/basic`, `logikbench/benchmarks/arithmetic`, and `logikbench/benchmarks/blocks`;
4. refuse submodules, hooks, package installation, generator execution, and repository scripts;
5. record commit, remote, tracked paths, byte counts, SHA-256 identities, and clean status; and
6. perform only static license/provenance/source inventory after acquisition.

No email, publication, upstream write, Runpod upload, pod creation, benchmark execution, source generator, synthesis, or comparative timing is authorized by this acquisition request.

## Frozen pre-inspection admission policy

Before reading comparative results, W8 will:

- treat one benchmark directory as one dependent cluster regardless of parameters or outputs;
- reject a directory without an explicit compatible project or local license identity;
- reject any source used in the current CM regression/development corpus;
- retain AI-origin metadata as a declared stratum and prefer human/vendored circuits for the primary confirmation set;
- reject unsupported or ambiguous HDL, ambiguous tops, malformed sources, and unresolved dependencies;
- convert with a separately frozen, hash-pinned Yosys contract;
- select at most one primary output cone per cluster using only bytewise source/root identity and bounded structural metadata;
- require `1 <= live support <= 16` and at most 4,096 source nodes for the complete-output task;
- reject cross-cluster duplicates by normalized cone identity and exact truth hash;
- freeze at least 30 eligible independent clusters across source/support/node/depth strata if available; and
- inspect no CM arm timing until the final confirmation freeze is immutable.

Any later Runpod conversion or performance workload will have its own exact upload manifest, command, resource limits, and authorization record. The standing `$5` spend authorization can cover its compute cost, but it does not replace exact private-upload disclosure.
