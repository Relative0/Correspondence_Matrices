# Frozen Phase-2 specification: bounded two-operand cut fusion

Version 1, 2026-09-16. **Design only: no prototype or performance run has been performed.** This document is the preregistration for one local experiment following the [research report](REPORT.md). Amendments require a new version written before affected measurements; consumed results stay labeled exploratory. This is not authorization for cloud resources, publication or broader optimization.

## 1. Question and falsifiable mechanism

Can exact composition of Boolean logic over two structurally identified compound operand signals reduce the **whole executable flat program**, enough to repay its discovery and rebuild costs, versus current CSE, CM and proved-rule controls?

Primary implementation arm: source DAG → structural IDs → bounded two-leaf cuts → one deterministic rewrite batch → existing CSE-flat → existing bigint executor. Secondary attribution arm: the same rewritten source → existing CM-IR → CM-flat. If CSE benefits equally, report a generic Boolean compiler improvement; do not label it an advantage unique to CM.

There is no new runtime opcode, learned policy, wider cut, native backend, persistent cache, numerical approximation, equality-saturation engine, or default-route change in this experiment.

## 2. Input and output contract

Admit only existing pure total `Var`, `Not`, `And`, `Or`, `Xor`, `Imp`, `Eqv` DAGs with a declared ordered ambient basis. Keep variable identity and source sharing explicit. Constants may be represented by existing compiler constant nodes/templates. Refuse unknown operators, duplicate/invalid basis names and out-of-basis fixed assignments through the existing contract checks.

For each request, return the exact packed truth relation over **unfixed ambient variables in the incumbent order**, even if the rewritten expression no longer depends on some of them. Serialize into the existing canonical bit/byte order with an explicit bit length and defined padding. No existential projection, count-only replacement, deduced-axis deletion or output-format shortcut is permitted.

Two independent correctness paths are required: scalar assignment evaluation for all assignments on small cases, and existing direct packed evaluation on every admitted timed case. Axis-order tests must use asymmetric functions and nontrivial basis permutations; constants alone do not test orientation. An output digest is an audit aid, not the sole equality proof when exact bytes are available.

## 3. Frozen implementation bounds

| Item | Bound / policy |
| --- | --- |
| Source | At most 4,096 unique nodes, depth 96, 16 ambient variables; retain every refusal. |
| Cut width | At most 2 exact opaque leaves; allow one-leaf and constant degeneration. |
| Cut frontier | Self cut plus at most 8 nontrivial cuts/node, deterministic sort by leaf count and ordered structural IDs. |
| Token work | At most 400,000 cut-pair combinations per source; count even failed unions. |
| Shell audit | At most 32 distinct interior nodes/cut, at most 1,000,000 aggregate interior visits/source. Abort this candidate on excess. |
| Sharing | Conservative first implementation rejects a shell if an interior node other than its root has an external consumer. Boundary operands may have arbitrary fanout. |
| Selection | Bottom-up stable source order; among eligible cuts at a root choose greatest proved marginal bigint saving, then smaller added-node count, then lexicographic leaf IDs. Skip overlapping selected interiors. |
| Rewrites | One batch, at most 256 replacements, no rematching the rewritten graph. |
| Rebuild | At most one rewritten-source reconstruction and one lowering per arm; no full compile per candidate. Track local fixed-size template costs. |
| Acceptance | After whole-program lowering, at least 2 fewer bigint primitives and at least 10% fewer than the unmodified CSE program; no increase in reported peak live word buffers. Otherwise return the unmodified CSE plan and charge all attempted work. |
| Memory / wall | Local only; one worker; at most 512 MiB child committed memory, 60 seconds/case subprocess and 30 minutes total measured campaign wall time. If enforceable containment is unavailable, stop before timing and report missing tooling. |

Precompute and prove a small fixed template table before input-dependent work. Start with the probe's exact template pool, adding only `Not(And(A,B))` and `Not(Or(A,B))` plus operand swaps/polarities for these templates. Select minimal current-bigint cost within this **declared pool**, with deterministic node-count and textual tie breakers. Freeze and hash this table before measuring a dataset. Do not call it globally optimal synthesis. Verify every chosen template on all four abstract assignments.

Structural IDs come from exact operator/child-ID/name tuples. Hashes may index them, but must not stand in for equality. Track input permutation/polarity witnesses explicitly when canonicalizing frames. No equality inferred from common support, diagram size or NPN class. Leaf substitutions may share physical variables; abstract four-row correctness remains required.

The acceptance gate compares executable programs, but selection cannot repeatedly invoke the full compiler to discover a profitable cut. Record token combinations, shell visits, candidate counts, selected cuts, removed/added nodes and fallback reason. Refusal must leave the caller's source and incumbent plan usable. Any partial candidate produced internally must not escape as an accepted optimized result after a bound failure.

## 4. Data partitions, fixed before timings

### Exposed natural audit: all 82 existing cases

Use the exact selection and on-disk dependency hashes in `probe-results-pack-control.json`: 64 EPFL cases with equal syntactic/semantic support 11–16, followed by all 18 C36 cases. This is exposed development/diagnostic data, **not independent confirmation**. Recompute incidence under the new shell/resource bounds; the earlier 1,821 residual count is not a promised activation count. Report every ID and refusal. Never replace a failed or unprofitable case.

The historical EPFL byte validator fails on Windows CRLF while the LF-normalized content equals the pinned Git blob. Preserve the original file and validator. The new experiment must bind both actual bytes and semantic parsed-DAG identities in its manifest and describe this distinction; it must not claim historical byte-validator admission. Do not mass-normalize repository files.

### Prospective synthetic mechanics panel

Freeze a generator manifest before optimizer timings. For each `(family,k,t)`, make an exact variable permutation by sorting indices `i=0..k-1` by SHA-256 of UTF-8 `cm-cut-v1|family|k|t|i`, with numeric index as tie breaker. Thus no library PRNG-version dependence enters generation.

Let the permuted names be `p_i`. For `j=0..k/2-1`, define compound operands

`A_j = XOR(p_(2j mod k), p_((2j+1) mod k))`

`B_j = AND(p_((2j+1) mod k), p_((2j+2) mod k))`.

Reuse these same operand objects inside each shell. Combine shells by a balanced OR tree, splitting the ordered list at its midpoint recursively. Families:

| Family | j-th shell / construction | Role |
| --- | --- | --- |
| F1 | `XOR(AND(A_j,B_j), OR(A_j,B_j))` | Positive identity beyond current one-pass pack. |
| F2 | `AND(IMP(A_j,B_j), IMP(B_j,A_j))` | Second positive identity beyond current one-pass pack. |
| F3 | `OR(AND(A_j,B_j), AND(A_j,NOT(B_j)))` | Overlap control: pack followed by CM can already recover A_j. |
| F4 | `XOR(A_j,B_j)` | Already simplified control. |
| F5 | F1 shells, plus their exact `AND(A_j,B_j)` interior objects included as additional leaves of the outer OR tree | Sharing/deletion control; do not assume a local shell saving is removable. |
| F6 | Balanced binary tree over each `p_i` once; internal operator cycles AND, OR, XOR by postorder internal-node index modulo 3 | Cut-unfriendly read-once control; do not require zero activation if the exact source reveals a valid one. |

Development: six families × k in `{8,12}` × t in `{0,1}` = **24 cases**. Locked synthetic confirmation: six families × k in `{8,12,16}` × t in `{2,3}` = **36 cases**. Generate/hash both manifests before timings, but inspect development outcomes first. After a bug fix, rerun correctness/development; do not inspect confirmation timing until implementation is sealed. Once confirmation timings are consumed, further tuning requires a new version and cannot relabel these cases as fresh.

These partitions test generalization across sizes/permutations of specified mechanisms. They are **not independent application families** and cannot justify production promotion. Case rows are correlated within F1/F2/etc.; do not use variable renamings as independent statistical samples.

### Boundary correctness panel, outside timed selection

Use all 16 abstract functions; both operand orders and all input/output polarities; identical, complemented and overlapping physical operands; constant/dead support; separately allocated structural duplicates; fanout sharing; one-over-limit cut/node/work cases; invalid basis and unknown operators; deterministic repeated compilation. Exhaustive two-physical-variable substitutions from the probe remain a required finite check. Verify exact fallback and counter bounds. Add only tests that challenge a semantic or resource boundary, not tests mirroring implementation lines.

## 5. Request traces and output control

For each case, request 0 has no fixed variables. Subsequent requests enumerate all two-variable fixed contexts in lexicographic ambient-position order: unordered pair `i<j`, then values `(0,0),(0,1),(1,0),(1,1)`. Use prefixes q in `{1,4,16,64}`. Each q experiment begins a fresh session; it may not prebind future requests outside its prefix. There are enough distinct contexts even at k=8. No repeated identical-output request is manufactured to favor either result caching or recomputation.

Compile once per session and charge it. Report a separate retained-plan replay with the initial creation cost both shown and allocated back to the full session. Do not call a warm replay “end to end” while hiding that cost.

Return and serialize exact full/restricted results through the same bounded in-memory byte consumer for all arms. Include serialization and byte-consumer completion in output time; correctness comparisons run outside the timed region and are also recorded. This tests an in-process delivery contract, not disk durability, OS-pipe throughput or production network latency. If the output consumer dominates, report that result rather than subtracting it away.

## 6. Comparator arms

All controls use current source, identical input bytes, variable order, context sequence, cache policy and output sink. Separate cold mask/cache runs from explicitly warm runs; do not let earlier arms warm later arms accidentally.

Required local arms:

1. Direct packed evaluator, including its real preparation and existing zero-safe memo behavior.
2. Existing R2/prepared path as implemented in the repository's comparative harness; record exact adapter/source identity, not just the label “R2”.
3. CSE-flat with existing flattening.
4. CM-IR → flat with current sharing-aware builder.
5. Existing one-pass proved rule pack v2 → CSE-flat, and the same rewritten source → CM-flat; also the D10 indexed motif engine → CSE/CM as separate fixed arms, including its bypass and verification costs.
6. Existing bounded fixpoint normalizer → CSE/CM; retain its actual stop/refusal behavior. This is a control for additional simplification, not a recommendation to revive D7.
7. Precompute the full packed relation once using each eligible incumbent compiler, then answer restrictions by an exact incumbent cofactor path; retain the fastest whole-session fixed variant. Pay original computation, cofactoring, storage, context validation and output. If a matching existing API is absent, a simple exact reference projection adapter belongs in this experiment's harness only and its cost is charged.
8. Candidate → CSE, and candidate → CM attribution arm.

Do not use a per-case free oracle as the claimed baseline. Report the best **single fixed arm per predeclared cohort and q**, with all arms shown. Also report the per-case oracle as an explicitly unattainable upper bound on routing headroom. Candidate acceptance can use its deterministic operation-count gate, whose rejected attempts are included in its total.

External synthesis comparison: if an existing local ABC executable is available, freeze its version and a supported bounded AIG rewrite command sequence before timing; preserve conversion semantics, simulate the result through the same packed/output contract, and charge export/process/import/rewrite. No install or network dependency acquisition is part of this run. A missing or incompatible ABC control is a recorded limitation: the result may establish a local repository improvement only, never superiority to established synthesis. For scalar alternative candidates, CUDD/d4 would matter, but adding those unrelated scalar experiments is out of scope here.

## 7. Measurement and stopping gates

### Stage A: proof and static activation, before timing

- All correctness and boundary checks pass with zero mismatches.
- Whole-program metrics show accepted savings on F1 and F2, beyond both plain CSE and the best of one-pass-pack/D10→CSE/CM for at least one case in each family.
- At least 8/64 exposed EPFL cases show accepted whole-program primitive savings beyond both plain CSE and the best one-pass-pack/D10 control. This is an engineering activation threshold chosen now, not a statistical claim or a restatement of the unbounded census.
- Keep all 18 C36 cases and every refusal in the output, regardless of activation.
- If any requirement fails, **STOP** this candidate before timings. Explain whether existing normalization, fanout, caps or template quality removed the opportunity. Do not widen the bounds or add passes to rescue it.

### Stage B: development, then one sealed synthetic confirmation

Use seven complete fresh-process paired rounds, serially. Within each round rotate arm order by round index and reverse it on alternating rounds. Every arm runs every admitted case and every q; missing cells remain failures/refusals, not zeros. Record CPU/OS/Python/source hashes, cache state, startup, parse, cut discovery, rewrite, compile, initial bind, each request's bind/execute/output, counters, peak committed memory and exact result identities. Stop on the first semantic mismatch or containment breach.

Report medians and all raw rounds. Compute cohort speedups using equal weight per source circuit for EPFL and per generator family for synthetic cases; report individual cases too. Pair uncertainty by round and source/family block; with few independent groups, display the range and avoid a universal generalization claim. Do not treat each renamed case or query as independent evidence.

Frozen local success gate (all required):

1. Stage A passes and no correctness/resource failure occurs.
2. On locked F1/F2 synthetic confirmation, q64 whole-session geometric-mean speedup is at least **1.10× versus the best fixed matched control**, and the candidate wins the aggregate in every one of the seven paired rounds.
3. On the complete exposed EPFL cohort, including fallback overhead, q64 speedup is at least **1.05×** versus the best fixed control. This is exploratory natural relevance, not independent confirmation.
4. Across F3–F6 and the complete C36 cohort, no cohort/q geometric mean is below **0.95×**, and no individual median session is below **0.80×**. No q1 cohort is below **0.95×**. Tiny absolute differences must still be shown, not hidden by ratios.
5. Peak committed memory is no more than **1.25×** the matched CSE control and remains inside the absolute containment cap; report both absolute and relative values.

Failure of any gate is **STOP**, preserving results and the original thresholds. Passing yields **retain an opt-in local experiment**, not production/default promotion. Promotion would require a new source-blind application/consumer confirmation and appropriate external control; it is a separate instruction and decision.

### Amortization report

For each case and cohort report the measured parse/compile/bind/execute/output ledger and observed cumulative difference for q1/q4/q16/q64. Where requests vary, use actual prefix sums. Report a stationary break-even estimate only for genuinely repeated comparable request costs, with its assumptions and uncertainty. If candidate steady-state execute plus output is not faster, explicitly write **“no finite amortization break-even.”** Do not invent q256 or q1024 wins by extrapolation or spend extra time sweeping for a crossing.

## 8. Required outputs and final decision

Create a new uniquely named audit directory for Phase 2. Keep this research folder and historical artifacts intact. Deliver source manifest, generator/trace manifest, proved template table, raw per-case metrics and timings, refusals, correctness evidence, resource receipts, comparison summary and a concise PROCEED/STOP result against every frozen gate. Review status/diff and run the project's relevant tests without weakening historical validators. No commits, pushes, publishing, credentials, paid resources or other checkout access.

The implementation is complete when the bounded candidate and matched harness exist, tests are run, and either Stage A stops it or the frozen local timing decision is reached. Stopping for a failed gate is a completed experiment, not a request to tune indefinitely.
