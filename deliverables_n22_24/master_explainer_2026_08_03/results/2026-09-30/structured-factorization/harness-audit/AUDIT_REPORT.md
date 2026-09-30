# Audit of the live-vtree integration gate — 30 September 2026

**The saved numerical results and bounded exactness evidence check out, but
the experiment does not adequately test the proposed factor-exposure benefit.**
Keep the tooling/mechanism GO and the registered NO-GO on this particular
dataset. Do not infer that M1/M2 live search is generally unhelpful, or that no
further developmental investigation is worthwhile.

This is a separate audit addendum. No frozen source, protocol, measurement,
or archived Phase 4/5 file was changed. No campaign worker was executed.
Semantic truth was used only to audit saved outputs and dataset suitability.

**What was performed and what survives the audit.** The original Phase 5B
implementation compiled the CNF anew for each candidate. The separate tooling
probe established a live manager/root method, followed by an integration of
matched fresh/live M1/M2 with the existing exact residual SAT and carrier
assembly. Three baselines and four search adapters underwent development
checks. The subsequent Linux campaign froze 12 validation and 24 held-out
inputs, seven methods and three repetitions, producing 252 + 504 saved rows.
Validation selected syntax baseline B3 and live challenger L2.

The live implementation references its root, disables automatic minimization,
collects garbage before edits, resolves manager-owned vtrees afresh, checks
native return codes, undoes candidates, and replays the winner. This follows
the maintainer's [rotation example](https://pysdd.readthedocs.io/en/latest/examples/build_formula.html#example-4-vtree-rotations)
and [Vtree API](https://pysdd.readthedocs.io/en/latest/classes/Vtree.html).
The method remains supported on the tested PySDD 1.0.6 backends; it is not a
claim of arbitrary-input resource safety.

The new `audit_results.py` independently checks the saved data using exhaustive
CNF models, projection-cardinality factorization and separate carrier merging.
It does not call the experiment's truth routine or compile an SDD. It also
reconstructs neighborhood order, scores, decisions and analysis from raw rows.

| Audit check | Result |
|---|---:|
| Raw rows, identity/repetition completeness, registered shuffled order | 756 pass |
| Semantic and carrier partitions against fresh exhaustive evaluation | 756 pass |
| Fresh/live matched runs, across both splits and both objectives | 216 pass |
| Candidate trace entries, ordering, scores and acceptance | 4,572 pass |
| Distinct input/direct-partition combinations, including candidates | 46 valid factorizations |
| Frozen source/protocol/manifest hashes | 11/11 match |
| Protected original archive files | 3,821 unchanged |
| Existing integration-directory files changed by this audit | 0 |

The auditor includes 19 small oracle controls. Linux-recorded and
Windows-recomputed M2 scores differ by one floating-point ULP in 54 trace
entries; tree tie keys and independently reconstructed decisions still agree.
The auditor permits two ULPs for cross-platform score recomputation. Fresh/live
scores from the same campaign remain exactly identical.

| Registered held-out quantity | Independently recomputed |
|---|---:|
| L2/B3 geometric total-time ratio | 1.0381785768 |
| One-sided 95% instance-bootstrap upper ratio | 1.0496056867 |
| L1/F1 geometric search-stage ratio; upper | 0.2783907633; 0.2943183801 |
| L2/F2 geometric search-stage ratio; upper | 0.3309788741; 0.3508823986 |

Thus live search was approximately 3.59x / 3.02x faster than its matched fresh
adapters, while selected L2 was approximately 3.82% slower than B3 in the
algorithm timer. The selection and the registered decision arithmetic are
correct. These comparisons include the adapters' file/manager handling;
they are not pure native-move microbenchmarks. The earlier probe separately
included a preloaded-vtree control.

**1. High priority: the dataset has zero factor-exposure headroom.**
On all **12/12 validation and 24/24 held-out instances**, B3's certified direct
partition already equals the finest semantic partition. Twenty held-out
instances are semantically indecomposable. The remaining four XOR instances
have one nontrivial block and a free last variable, both already separated by
B3. This conclusion comes from the independent oracle in this audit, not just
from trusting the stored correctness flags.

Consequently, no exact search starting at B3 could expose additional factors
on these inputs. M2 could still change SDD size, but this pipeline hands only
the certified partition and original CNF to residual SAT. The actual B3/L2
partitions and SAT-call counts were identical. The experiment therefore
measured the cost of searching when the desired exposure benefit is absent.
It is a useful overhead control, but an inadequate test of the main research
question. Merely increasing n or allocating more RAM does not repair this.

**Update:** retain the registered NO-GO for this set and explicitly qualify its
scope. Retract any blanket recommendation to abandon further M1/M2 work based
on this experiment alone. Before any new performance campaign, add separate
developmental positive controls with semantically factorable but syntactically
entangled CNFs, alongside saturated/prime negative controls. Known products
with redundant cross-component clauses are one construction to investigate.
Verify that a reachable candidate can improve direct extraction on at least
some developmental controls, without feeding those partitions into objectives.
Freeze a new family/seed mixture prospectively; do not screen or retune either
existing held-out set based on this audit or use truth to rank candidates.

**2. Medium priority: analysis guards do not enforce the full data contract.**
`campaign_runner.py:191` checks only total row count and flags literally equal
to false. `per_instance_costs` checks group length but not repetition identity.
In-memory fault injections demonstrated that duplicate repetition labels,
deleted correctness flags and one negative timing survive both checks.
The actual stored data pass stricter checks, so this does not overturn the
current arithmetic. It is a reproducibility defect for future interrupted,
edited or malformed runs.

`load_selection` at line 238 checks eligibility but does not recompute the
validation winner; `select` does not independently reject an already-started
held-out split if the selection file disappears. Mechanism analysis at line
278 skips failed pairs, then computes ratios from surviving complete instances.
There is no explicit mechanism-GO field requiring complete coverage. A manually
interpreted favorable ratio could therefore hide missing pairs. No such pairs
are missing in the present data.

**Update:** in a new revision, validate the exact Cartesian job-key set,
unique repetition labels, row identity and schema, finite positive timings,
explicit true correctness flags for successes, and explicit allowed failure
statuses. Bind every row and the held-out start receipt to source, manifest and
selection hashes. Recompute and compare the selected identities. Require
full predeclared parity coverage for mechanism GO or state a conservative
failure/censoring rule; never silently use survivor-only ratios. Test these
guards with malformed saved rows and interrupted/resumed execution.

**3. Medium priority: hostile/resource correctness was only partly covered.**
The Windows development record supports 398 main-root SAT miters, 337
additional-root miters, 36 forced native failures and 119 long-walk inverse
restorations. All 36 recorded failures occurred in the explicitly forced branch
and received both function checks. However, the permissive-failure branch at
`stress_worker.py:85` checks the snapshot and then continues, skipping both
function miters and the memory check. That branch had zero failures in the
saved runs. Immediate successful undos also omit the second-root miter at
that instant. The gap is coverage, not an observed semantic failure.

The stress fixtures had only 213 and 486 live elements initially and 180 total
forward-walk steps. That is useful regression evidence, not a large-SDD or
near-limit memory-growth test. The Linux freeze ran a small L1 smoke and a
separate allocation-limit control; the complete stress/integration suite was
not recorded on the Linux execution backend. Equality of final partitions
alone does not prove equality of the live Boolean function on every move.

The Linux worker correctly sets and verifies `RLIMIT_AS` before PySDD import.
However, `bounded_trial.test_hard_cap` tests separate inline code, not the actual
worker's failure/classification path. The parent adds cap metadata to rows;
the worker does not return its effective limit. No recorded trial exercised
watchdog expiry, native crash, or actual capped-worker exhaustion.
`bounded_trial.py:43` also groups SIGSEGV with SIGKILL as `killed` rather than
distinguishing a native crash. Equal PAR2 penalties make that harmless to this
run's decision, but it obscures engineering diagnosis.

**Update:** move all-root miters and memory observations into a shared
post-operation check that covers every success, failure, inverse and replay.
Add deterministic tests for the permissive-failure branch. Exercise timeout,
allocation failure, malformed output and crash classification through the
real launcher on separate development inputs. Return the effective limits
from the child. Run the complete gate on the intended Linux backend before a
new freeze, and add a bounded larger-SDD stress tier. Do not replay the frozen
held-out campaign to accomplish this.

**4. Lower priority: clarify timing, uncertainty and provenance.**
The original plan's algorithmic accounting is substantially implemented:
construction, GC, moves, undo/replay, extraction, scoring and residual SAT are
inside the algorithm timer. However, the final protocol says “worker setup”
is charged to `total_ns`, while the timer at `integrated_pipeline.py:215`
starts after imports, input parsing and validation and ends before output
serialization. The separately recorded process-wall time includes these costs.
An exploratory recomputation using process-wall medians gives L2/B3 =
**1.01643**, still failing the registered improvement threshold. This secondary
calculation does not replace the frozen primary analysis.

There are six held-out templates at four deterministic sizes, rather than
24 independent draws from a broad problem population. For example, every
ring-equivalence instance has two models; every nested-gate instance has four.
The registered instance bootstrap is reproduced, but its interpretation must
remain conditional on this designed set. An exploratory bootstrap resampling
whole families gives upper ratio **1.04632** and does not rescue a GO. More
sizes from these same templates would not create broad independent evidence.

The source receipt omits `dev_fixtures.py`, although freeze and exclusion checks
import it. It also omits the development tests/miter, wheel hashes, immutable
container digest, CPU model/affinity and cgroup settings. Source hashes are
valuable, but saved rows lack their own run timestamps and freeze/selection
identifiers. Thus the sequential chronology is supported by the execution
record and receipts, not independently sealed by the raw rows alone. The
standalone post-run audit script was not retained; this audit now supplies one.

The earlier execution record reported container `memory.max=8000000000`
bytes: 8 GB, approximately 7.45 GiB. The report's “8 GiB container memory”
wording is inaccurate. This does not establish a breach of the protocol's
host-RAM condition, but the saved receipt does not establish that condition
either. The 2 GiB per-worker cap was separately recorded. The 90-minute limit
is cumulative worker process-wall time, not elapsed Pod lifetime or billing;
it excludes provisioning, package installation and evaluator work and can
overshoot by one worker. Do not present 104.32 seconds of worker time as total
Pod uptime or actual billed cost.

**Update:** define algorithm and process timers explicitly, preserve the
existing primary result, report family strata and limitations, freeze every
execution dependency and test source, and retain sanitized resource/teardown
receipts. For future paid work, add an elapsed-job deadline and cleanup on
failure; record actual provision-to-termination time and cost separately.

**Runpod cleanup evidence.** The earlier execution record reports successful
termination of Pod `t4cb81ztfk0i8m` (DELETE 204, subsequent GET 404), zero
remaining Pods, and removal of the temporary registered SSH key. This audit
attempted a fresh read-only check using the previously authorized credential.
Both sandboxed requests and an approved escalated v2 request returned HTTP
403; current account state could not be independently reconfirmed.
`runpod_cleanup_check.json` records that limitation. This is an API access
failure, not an automatic approval rejection, and is not evidence that a Pod
is still running. No new resources were created and no credentials were
printed or written into the audit artifacts.

**Recommended next gate.** First preserve this qualification with the original
report, then repair the harness and hostile tests in a new revision and validate
developmental factor-exposure controls. Defer any new performance campaign
until those checks pass; do not retune or rerun the archived held-out sets.
The closely related repair belongs in this thread because it reuses the exact
implementation and audit evidence. `gpt-6-sol` with high reasoning is a suitable
available model for that bounded coding/review task; no price-saving estimate
is implied. No additional paid benchmark is required to complete this audit.

Reproduce only the offline audit from this audit directory:

```powershell
& '../phase5b_output/.venv/Scripts/python.exe' -B audit_results.py
```

It writes only `audit_results.json` here and never executes a campaign trial. The separate
`check_runpod_cleanup.py` performs only authenticated GET requests and writes
its sanitized receipt; it is not part of the offline audit.
