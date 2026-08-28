# Maximal safe CM campaign preregistration

Date: 2026-08-27. Written before implementation or new measurement.

## State and authority

- Root: `C:/Users/brian/Documents/CM_Computation`.
- Branch/HEAD: `main` / `1f51e651cb08ccda3284bd8476e4a9dbaedacf37`.
- Origin: `https://github.com/Relative0/Correspondence_Matrices.git`.
- No tracked modifications or staged files at intake. Exact untracked paths and
  git permission warnings are captured in `REPOSITORY-INITIAL.json` and tool logs.
- No on-disk ancestor/project AGENTS.md found; Brian's supplied global guidance applies.
- Preserve the entire master-explainer tree, three untracked feature-model tests,
  `.claude/`, `external/`, `tmp/`, all existing pytest scratch, and the untracked
  campaign prompt. No website audit, staging, commit, push, publish, or secret reads.
- The 15 requested authority documents were read in order. Latest accepted
  artifacts override historic hypotheses, including the rejection of DP-R1.
- Read-only scans, documentation, source edits and tiny checks are local.
  Brian's explicit Runpod instruction overrides prior plans for local studies.
  Nontrivial studies and full pytest require a new exact cloud authorization.
  Previous RP-D0 approvals are consumed. No pod/download/install/upload is authorized here.

## Frozen questions and decisions

| Rank | Hypothesis / mechanism | Evidence / files | Benefit | Correctness / memory risk | Maintenance / dependency | Validation / decision |
|---|---|---|---|---|---|---|
| 1 | Refusal may leave stale diagnostics or reach allocation too early | output_budget, cm_ir, pair, parallel, worker, protocol | Reliable typed failure, no partial result | Medium / high on unguarded paths | Small focused tests; existing runtime | Sentinel tests and exact admitted output; fix reproducible defects only |
| 2 | Estimation itself accepts malformed counts and unbounded shifts | output_budget.py int coercions and `1 << k` | Bounded admission arithmetic | Medium compatibility / high if unbounded | Small helper; no dependencies | Tiny malformed/boundary checks; avoid unsafe shifts; retain normal integer and None meanings |
| 3 | Dense two-buffer estimate omits memo arrays and metadata | Prior dense negative; bitset_backend and materializers | Honest diagnostic admission model | High if promoted without evidence | One reusable diagnostic driver | Structural allocation model, cold/warm calibration and held-out; no production estimator promotion without every gate |
| 4 | Separate bigint and words accounting exposes representation costs | Values slots, word plan and scratch, conversion | Explain false admissions/refusals | Low diagnostic / medium measurement | Existing NumPy and stdlib OS memory facilities | Per-window traced peak and process high-water separately |
| 5 | Additive provenance fields might be worthwhile | Current worker/protocol lack resolved-limit echo | Auditable remote decisions | Legacy serialization risk | Small change or specification only | Missing/null fixtures, local/mock/worker parity; defer if not one attributable change |
| 6 | A newly supplied owner manifest could open one lane | Filename/schema/caller scan | Real application evidence | Content approval / no ambient telemetry | Existing strict validator/sink | Metrics-ready declared owner only; benchmarks are not application traffic |
| 7 | Optional backend readiness changed | Official package, SIMD, corpus and Runpod sources | Exact next approval package | Build/ABI/cloud cost | No installs or downloads | Dated primary URLs; no lane without workload gate |

## Study design frozen before outcomes

Diagnostic model identifier: `cm-memory-structure-v1-candidate`; legacy model
remains `legacy-output-v1`. Candidate estimates are NOT production guarantees.
No fitted universal multiplier and no changes to defaults, guards, ordering,
artifacts, or engine routing. Any diagnostic corrections after smoke must be
recorded; held-out families cannot be used to tune coefficients.

Calibration structural families: mixed-chain, shared-diamond, wide-and.
Held-out structural families: alternating-tree, reconvergent-xor.
Use fixed synthetic seeds 20260827 and 20260828. Contexts: none fixed, alternating
half fixed, all fixed. These are synthetic stress cases, never real workloads.
Accepted BX1/B2/EPFL are benchmark-corpus compatibility/reused validation only.
Neither EPFL nor i10 is newly held out; i10 is excluded from fitting and this study.

Local smoke: at most one tiny case per representation, k<=6, one repetition,
at most 64 output bytes. Tiny functional tests use k<=6 or mocked allocators.
No local corpus replay, performance fitting, native/JIT execution, or full suite.
Runpod smoke after authorization: k=6,8; one calibration and one held-out family,
three repetitions in each cold/warm schedule, all three representations. A larger
run is contingent on smoke review and a separate exact approval.
Opt-in representative design: k=6,8,12,16, all families/contexts, five repetitions;
accepted corpus replay k<=16. Absolute diagnostic limits: 1,024 structural nodes,
2,048 edges, 64 KiB output, 32 MiB candidate estimate, 30 s per child, 20 min total.
Stop on any exactness failure; preserve all planned-case timeout/refusal/skip rows.

Each cold repetition uses a fresh isolated subprocess. Warm repetitions share
one child per case/representation with one untimed warmup; caches remain warm.
Use blocked schedules, never pool cold and warm. No timing comparison across hosts.
Python import/process start is outside operation timing but inside child wall time
and lifetime RSS high-water. Preparation, packed evaluation, dense materialization,
packed-to-uint8 conversion, and serialization are separate windows. Correctness
reference and hashing run outside measured windows. `tracemalloc` starts for each
window; peak includes newly allocated returned output and any cache fills. Do not
sum window peaks or subtract output bytes to claim a total temporary peak.
RSS uses OS lifetime high-water and before/after current RSS when available;
high-water deltas are not window peaks. No psutil dependency will be added.

Per-row schema: case/family/role/seed/context, representation and actual engine,
repetition/schedule/window, s/k/m/operator mix/word buffers, output bytes,
legacy/candidate estimates and estimate cost, tracemalloc current/peak, OS RSS
method/before/after/high-water, duration, status/reason, exactness, digest.
Emit exclusive JSONL raw rows, JSON environment/summary/manifest, CSV summary;
manifest records source and corpus byte hashes, not secret/environment values.

Profiles (diagnostic only): legacy; production-balanced-v1 (benchmark/new remote
64 KiB output / 16 MiB temporary / k<=16; direct 256 KiB / 64 MiB / no new k guard);
strict (16 KiB / 4 MiB / k<=14); permissive (256 KiB / 64 MiB / k<=16).
Report every admission/refusal and reason. False admission means admitted but
observed *matching window* traced peak exceeds temporary limit. False refusal
means refused by temporary estimate with output/k otherwise fitting and measured
peak fitting. Unmeasured or failed cases are unknown, never counted as safe.

## Acceptance and stopping gates

- Production estimator: structure-derived, cheap/bounded/deterministic, monotone,
  explicit safety margin, zero underestimates in every calibration AND held-out
  measured window, focused/full regression passing, no changed defaults/routing.
  RSS is a separate diagnostic, not an OS-enforced guarantee. Missing evidence
  means defer, not pass. Version any retained estimator change.
- Reliability: sentinel proves refusal before guarded allocation; zero stale
  failure state or partial serialized result; exact admitted bits/order; numeric
  limit-1/limit/limit+1; legacy None/missing fields unchanged.
- Real workload: strict pass AND metrics-ready declaration, separate replay/upload
  approvals. No gate-clearing trace means no cache/family/context/selector/native
  implementation. Apply the intake contract's unchanged volume/opportunity gates.
- No policy activation. Brian must approve numeric limits and newly refused calls.
- Runpod validation is infrastructure for this requested safety campaign, not a
  claim of production remote-compute benefit. No optional backend smoke is bundled.
- Record negative/unmeasured results and remaining Runpod gate honestly; do not
  report the full campaign complete without its nontrivial validation.
