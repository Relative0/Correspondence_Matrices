# Phase 6 corpus, schedule, and P7 execution-gate audit

Date: 2026-08-30  
Authoritative package: `docs/research/verification/comparative-p6-candidate-v4-2026-08-30`  
Offline execution gate: `docs/research/verification/comparative-p7-offline-gate-v1-2026-08-30`

## Supersession finding

The immutable V3 package remains a valid record of its formal schema and source
gate, but an execution audit found two blocking ambiguities:

1. its 20 EPFL cases named whole BLIF files without freezing a primary output
   root, so they did not define one reproducible expression or relation; and
2. `cm-compact-key` was listed as a separate IR arm even though compact
   interning is already part of `cm-ir-current`. The relation policy also named
   `cm-fast-frozen` before a distinct combined configuration existed.

V3 was not edited. V4 supersedes it for execution. No comparative timing or
paid compute was inspected while making these corrections.

## V4 frozen result

The V4 package passes its read-only verifier and formal P6 gate.

- Freeze SHA-256:
  `54ea61a38135426975a0d1fead9b24c020dc565eb3d952356640fa38062598dd`.
- 104 cases and 104 independent cluster IDs: 32 regression, 42 development,
  and 30 untouched confirmation.
- Development contains 24 synthetic cases, ten natural EPFL output cones, and
  eight adversarial CNFs. Confirmation contains 30 previously untimed CNFs.
- Six task policies contain 9,672 deterministic case/order rows.
- P7 IR uses four distinct controls over 8–16 blocks: current one-memo IR,
  historical two-memo IR, CSE-flat preparation, and raw-flat preparation.
- P7 complete relation uses five distinct arms over 10–20 blocks: dense,
  packed bigint, packed words, no-reinflation, and CSE-flat.
- The combined `CM-Fast-Frozen` arm is deliberately deferred until a distinct
  checked-in stack is frozen from development evidence. It is not an alias for
  the current no-reinflation implementation.
- Every schedule retains complete deterministic counterbalance cycles,
  conditional extension under the frozen MAD/median rule, and independent
  units before added repeats.
- Primary metrics remain task-total wall time and process-tree peak RSS.
- All source identities, JSONL member identities, package checksums, the saved
  source check, and the saved formal gate reproduce. `--require-ready` exits
  zero with no formal gate reason.

The package file `freeze.json` is 5,562,003 bytes with SHA-256
`02038bad06f72da2b47a4f63a2857f484f141fa48e4842440e80464e777da2d0`.

## EPFL output-cone rule

For each circuit sorted by path, V4 selects the first bytewise-sorted primary
output whose exact support is 4–16 and whose driven cone has at most 4,096
nodes. It freezes the root name, ordered support, source nodes/edges, depth,
local LUT fields, source bytes, and source hash.

Ten circuits supplied an eligible root: adder, multiplier, sqrt, square,
cavlc, ctrl, dec, i2c, int2float, and mem_ctrl. Ten circuits were excluded
before timing because no primary output met the frozen bound: bar, div, hyp,
log2, max, sin, arbiter, priority, router, and voter.

The new bounded metadata query stops after the first support or source-node
bound violation rather than constructing full transitive sets for a large
netlist. Its parser/oracle regression suite passes.

## P7 offline execution gate

The separate immutable P7 package binds the frozen human-readable arm names to
concrete code and verifies every eligible case can be prepared.

- 58 unique P7 cases prepare successfully: 24 regression and 34 development.
- The ten EPFL roots reproduce their frozen static metadata and translate to
  bounded expressions.
- Four IR arm bindings and five complete-relation bindings are exact; no
  unknown or duplicate label remains.
- A two-case `k=8` non-performance dry run passed. All nine arms matched the
  independent scalar relation digest on both cases, and current one-memo versus
  historical two-memo produced identical ordered CM-IR signatures.
- The read-only verifier reproduces the readiness record, dry-run record,
  package checksums, and all 18 local source identities.
- No duration is retained, and both records explicitly prohibit a performance
  claim.

`execution-readiness.json` SHA-256 is
`ac2400e068ac59dcae3f36b55bf2c09a201df7cfdb7b2941853100d431ef20c3`;
`dry-run.json` SHA-256 is
`e069772c27ba07da1095ee91a393fd1715da3a85d19a85402cbc4357f2383cdf`.

## Scope and next gate

Formal P6 and the offline P7 execution gate are complete. They do not yet
authorize or constitute a paid benchmark. The next implementation step is the
Linux isolated-cell runner: fresh owned process group per retained cell,
bounded input/output, deadline and RSS limits, outside-span scalar validation,
append-only cell evidence, exact resume/reconciliation, environment identity,
and source rehashing before and after the shard.

Only after that runner's fake success/refusal/timeout/mismatch/cleanup tests
pass should an exact Runpod P7 development-scout proposal be frozen. The
current confirmation cohort covers count/SAT/witness/frontier tasks; a
principal complete-relation or IR claim still requires a later untouched
formula/circuit confirmation cohort.

No pod create, dependency installation, production default change, commit, or
push occurred in this correction.
