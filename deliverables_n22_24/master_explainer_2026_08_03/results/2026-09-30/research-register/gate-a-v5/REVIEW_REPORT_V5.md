# Protocol v5 candidate review — Gate A remains NO-GO

Candidate identity: **gate-a-v5-candidate-20260924-01**. Date: 2026-09-24.
Disposition: prospective design and implementation complete for review; **no performance qualification, no confirmatory freeze, no execution authorization**.

## What was completed

Protocol v5 fixes the reported timing replicate as a median of nine elementary calls, each in a separately launched fresh process. Inputs are reconstructed separately, workload caches reset, GC enabled, and all arm-specific preparation charged. No warm-up or warm inner loop is introduced. Both primary arms share the import/staging/timer/oracle policy. The nine-member count was selected prospectively without new timing data, relative arm speeds, or formula outcomes.

The package contains the numbered protocol; unchanged audited production source; new harness, elementary runner, exploratory launcher, strict row validator, hash-chained writer, pilot/primary analyzer; scalar oracle digest manifest; explicit pilot schedule and primary/secondary schedule expansions; schema documentation; v4 migration and evidence index; manuscript working TEX and diff; contract matrix; tests and retained validation logs. Generated secondary corpus and inherited endpoint adapters are preserved. The natural population stays in the original controlling package and was not staged, traversed, or executed here.

The full-pass rule remains all 200 controls, MAD/median <=0.05, now over 11 median-of-nine replicates per control. Every elementary row must also pass the 1% timer-pair and clock-resolution controls, correctness, integrity, and environment checks. All 19,800 rows must be present exactly once in order. Failure stops collection without retry. Tests do not establish that this design will pass on any real host. Sustained contention or timer-resolution limits can still fail it.

The v4 primary scientific question and thresholds remain unchanged: R>=1.20, lower bootstrap endpoint>1.00, M<=1.10. Resampling remains by case and paired outer repetition, never by elementary process as an independent formula. Memory remains 15 independent single-call process peaks. The v5 estimand must not be pooled with v4 single-call measurements.

## Evidence and preservation

- Controlling package SHA-256 reconfirmed: `93c556a4c15099c260919287e95809079bf8d5ff21b8117e4155fd0482a7306a`; 68 manifest entries verified as opaque bytes. No confirmatory result content was opened.
- All 187 source files match the packaged SHA-256/size records, their Git blob identities, and the tree at `0ab8ffd0c23ffa71ee951d375b1c170ffdcc084b`. No production repair was made.
- Primary corpus remains `aa0cb2f1f4f665ee77ae0fa881a755eb1baa27971d870eec9e5680dc1049112b`. Retained v4 harness/pilot/runner hashes are preserved; raw WSL and Runpod pilot durations were not parsed or compared.
- WSL identities retain their own hashes and failures (17, 56, 14, 20). Runpod remains its separate identity, 194/200 passing with six failures, zero timer-overhead failures, affinity [0], nice 0. The retained host limitations are not used to excuse the failed rule.
- The task directory is outside `CM_Computation`. Before/after Git status and tracked binary diff are byte-identical; v4 package hash is unchanged. No checkout clean/reset/restore/stage/commit/push occurred. The preservation record states the scope of these checks; it does not claim a full hash inventory of unrelated untracked files.
- Six append-only candidate result templates are zero bytes (pilot, time, memory, correctness, diagnostics, intake). Qualification test logs are separate from those result ledgers.

## Validation performed

| Check | Result | Interpretation |
|---|---:|---|
| V5 final untimed/synthetic suite | **61 passed, 0 failed** | Schema, code boundaries, schedule/aggregation, host refusal, and adversarial tests |
| Audited focused source suite | **147 passed, 0 failed** | Original project checks for the relevant production surface |
| Boundary regression suite | **95 passed, 0 failed** | Retained 17-category contract suite |
| Finite Boolean core | **333,794 checks, 0 failures** | Exhaustive finite checks, not an unbounded proof |
| Primary API/oracle checks within v5 suite | **100 cases x 2 arms, all passed** | Untimed; scalar/direct equality and pure structural provenance |
| Explicit fresh-process tests | **4 real untimed subprocesses, all passed** | Child/parent identity, separate nonces, equal digests, no durations |
| Pilot analyzer tests | **Synthetic all-200 pass and 199/200 failure** | No real performance evidence; Gate A stays NO-GO in both reports |

Injected clocks test exact charged boundaries and overhead accounting. A guard makes untimed API correctness fail if it touches the performance clock. Tests verify every cache-clear routine, separate reconstructed objects, missing/extra/duplicate/out-of-order rows, altered hashes, oracle mismatch, reused nonces, threshold equality, malformed durations, affinity drift, host quotas/governor/SMT constraints, append-only writes, timeout retention and no retry, and confirmation refusal. A timeout test writes only fabricated failure evidence to an external pytest temporary directory; it does not launch a pilot.

The local test environment is Windows, Python 3.10, NumPy 2.2.6, pytest 9.0.2. Exact runtime details are in DESIGN_TEST_ENVIRONMENT.json. This is not a qualified pilot host. Prior native CUDD and ABC/Yosys checks are retained v4 evidence; no new native/environment qualification is claimed. Test-framework wall-clock run times in logs are operational diagnostics, not measurements of either arm.

During preparation, a source ZIP lookup was initially ambiguous for `conftest.py`; using exact archive paths resolved it. Initial schedule generation assumed the primary `blocks` shape for secondary schedules; the implementation was corrected to preserve the secondary `cells` structure before final tests. No timing or results were collected in either attempt. Earlier v5 test runs (47 and 57 passed) are retained separately; the 61-test final log controls.

## What remains unqualified

1. **Empirical v5 stability:** zero new performance observations. The median-of-nine proposal has not passed the all-200 gate.
2. **A controlled host:** none selected. Exclusive physical-core dedication, offline siblings, no ancestor quotas, dependency/image identity, environmental monitoring and absence of competing experiments require concrete evidence. A binding's Boolean assertion is not proof of provider dedication.
3. **Portability to that host:** the complete untimed/synthetic suite and required source/native qualifications must be checked in the chosen environment. Native toolchain compatibility is not inferred from local Python tests.
4. **Confirmatory execution:** primary time/memory, secondary schedules, natural pairability and natural compiler calls remain unexecuted. The candidate contains no confirmatory campaign launcher or Frozen Execution Prompt. Inherited legacy executable files are provenance only, not alternate launch paths.
5. **Manuscript finalization:** the successor TEX and patch are updated; no new PDF was built or visually qualified. A final publication build and manuscript/protocol agreement check remain due before final Gate A adoption. The companion foundations artifacts are untouched.
6. **Independent review:** this is the task's implementation review report; no external reviewer or peer review is claimed.

## Required before a separately authorized pilot-v5-* run

In priority order:

1. Review and adopt this exact candidate design and code. Verify the detached package checksum and candidate manifest. Any methodological/code change requires a new candidate identity before timing.
2. Prospectively select one host using only the frozen administrative requirements, without timing probes or opportunistic replacements. Document provider/core dedication, disable sibling execution, require performance governor and unthrottled cgroup v2, freeze runtime/dependency/image hashes and CPU/memory/timer controls. The runtime checker enforces measurable controls; a reviewer must verify external evidence and ancestor quotas.
3. Reconfirm the source closure and run the untimed/synthetic qualification scope on that host. Prepare a reviewed host-binding file, immutable authorization record, monitoring contract and initial throttling snapshot, each hash-bound to the same run/environment. Freeze them before the first performance observation. Create a new external result directory and retain all setup failures.
4. Obtain separate explicit authorization for **exactly one** exploratory `pilot-v5-*` identity and its resource/time/cost cap. The pilot is 19,800 sequential fresh workers; no paid work is authorized by this task. A budget abort is an incomplete NO-GO, never permission to trim the schedule or resume with replacement observations.
5. Only under that authorization, execute the frozen pilot once, retain all raw rows and monitoring, and apply the complete rule. Any failure or incomplete coverage remains NO-GO. A stability pass still requires host-monitor closeout and every other Gate A criterion before a new confirmatory freeze could be considered.

The primary future time schedule requires 54,000 workers and memory 3,000. The generated secondary expansions require 1,757,700 time workers and 97,650 memory workers. These counts expose the prospective cost; they are not authorization or a reason to shrink the experiment after results. Natural scope remains separately blocked.

**Stop here. Gate A remains NO-GO. No performance pilot, confirmatory execution/inspection, natural-population use, paid Runpod work, or Frozen Execution Prompt occurred in this task.**
