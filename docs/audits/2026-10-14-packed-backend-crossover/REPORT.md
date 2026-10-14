# Packed-backend crossover trial — completed measurements

**Decision: keep explicit backend choice; these cases do not justify a new
dispatch threshold or promotion of CM/NumPy words.** All 112 scheduled cells
completed with matching complete outputs and 56 complete pairs. The independent
ANF verifier reproduced every case/context artifact hash. The scalar native
route remains unavailable because Numba is absent; no native crossover was
measured. Results are descriptive synthetic development evidence.

**Final preservation limitation:** the in-service verifier confirmed all frozen
source and runtime hashes before exit, but the later independent readback found
the temporary runtime directory absent. POST_EXECUTION.json therefore reports
passed=false for runtime preservation after exit. All other post-run checks
passed, including original source/pilot preservation and service/cgroup removal.
POST_RUNTIME_DIAGNOSIS.json records 2,055 missing runtime files, no changed
remaining file, and the unchanged system Python executable. Execution-service
and subsequent readback boot IDs match; a WSL reboot is not established as the
cause. The deletion cause remains unknown. No restoration or timing rerun was
performed after this observation. This limitation does not change the recorded
in-service output equality or resource checks, and must accompany these results.

## Full-task paired results

Ratio is candidate/reference full lifecycle time within each pair, including
startup, imports, preparation, the complete query sequence, verification,
serialization and cleanup. Below 1 favors the candidate. These are medians of
individual paired ratios, not ratios of arm medians. Three cold pairs and five
independently prepared pairs were used per case. As prespecified, both session
types start fresh; the prepared label does not remove startup from full-task
time. No statistical confirmation or universal crossover is claimed.

| Case | Candidate/reference | Cold paired median | Prepared paired median | Prepared candidate wins |
|---|---|---:|---:|---:|
| shared-12-full-q1 | CSE/raw integers | 1.0160 | 1.0163 | 2/5 |
| unshared-12-full-q1 | CSE/raw integers | 1.0261 | 1.0646 | 2/5 |
| shared-16-restriction-q64 | CM/CSE | 0.9357 | 1.0072 | 2/5 |
| unshared-16-restriction-q64 | CM/CSE | 1.0682 | 1.0552 | 2/5 |
| shared-22-full-q1 | words/CSE integers | 1.0297 | 1.0143 | 1/5 |
| unshared-20-full-q1 | words/CSE integers | 1.0428 | 1.0306 | 2/5 |
| shared-22-restriction-q1 | words/CSE integers | 0.9773 | 1.0137 | 2/5 |

No candidate has a prepared full-task paired median below 1 in this schedule.
Several individual pairs reverse direction. The shared q64 CM case includes a
large full-task outlier (one paired ratio 0.5401); its median arm times alone
would suggest a stronger benefit than the paired median supports. Retain raw
pairs and ranges in RUN_VERIFICATION.json and ROWS.jsonl.

The width-20 negative and width-22 positive words cases use different formulas;
the q1 and q64 restriction cases also differ in live width. These selected edges
cannot isolate a causal width or query-count effect. Actual live widths are
12/20/22 for full outputs and 10/16 for restrictions. All q64 contexts are
distinct influential restrictions, and the declared permutations affect outputs.

## Engineering components

Prepared phase medians below are milliseconds. Binding is excluded from the
integer query subtotal to prevent double-counting. Words query includes its
baseline internal binding, first scratch allocation and uint64→bytes→integer
conversion. Component medians need not sum to median lifecycle time.

| Case | Arm | Compile | Masks/environment | Binding | Query | Validation |
|---|---|---:|---:|---:|---:|---:|
| shared-12-full-q1 | raw | 0 | 0.0239 | 0 | 0.0593 | 0.2149 |
| shared-12-full-q1 | CSE | 0.1927 | 0.0448 | 0.0067 | 0.0192 | 0.1968 |
| unshared-12-full-q1 | raw | 0 | 0.0266 | 0 | 0.0528 | 0.2056 |
| unshared-12-full-q1 | CSE | 0.1774 | 0.0550 | 0.0072 | 0.0185 | 0.2230 |
| shared-16-restriction-q64 | CSE | 0.2797 | 0.1308 | 0.2267 | 0.8382 | 6.2344 |
| shared-16-restriction-q64 | CM | 1.8729 | 0.1354 | 0.2205 | 0.8040 | 5.6974 |
| unshared-16-restriction-q64 | CSE | 0.1763 | 0.1081 | 0.1668 | 0.5611 | 4.5601 |
| unshared-16-restriction-q64 | CM | 1.5298 | 0.1072 | 0.1754 | 0.5452 | 4.5230 |
| shared-22-full-q1 | CSE | 0.2362 | 14.9448 | 0.0158 | 6.1539 | 140.4978 |
| shared-22-full-q1 | words | 0.2328 | 26.2041 | included | 6.0282 | 142.3290 |
| unshared-20-full-q1 | CSE | 0.2127 | 2.1549 | 0.0101 | 1.5191 | 32.5707 |
| unshared-20-full-q1 | words | 0.2127 | 4.8952 | included | 1.6596 | 33.6976 |
| shared-22-restriction-q1 | CSE | 0.2534 | 0.1327 | 0.0079 | 0.0469 | 2.2219 |
| shared-22-restriction-q1 | words | 0.2244 | 0.2061 | included | 0.1286 | 2.1716 |

CSE's smaller width-12 online query subtotal does not offset its preparation
cost in this one-vector task. CM adds compilation cost while giving similar
q64 binding/query totals. The words kernel's near-equal width-22 query subtotal
does not offset its larger mask/conversion preparation; at width-20 and residual
width-16, its query subtotal is larger too. Validation and process/import costs
dominate these short synthetic full-task lifecycles. They are part of this
contract; an application that retains one process and excludes independent
validation has a different denominator and needs a separately frozen trial.

## Recovery, limits and cleanup

The first approved launch found the old /tmp runtime missing and ran zero cells.
The renewed human grant explicitly authorized offline restoration and one
execution. A recovery bootstrap import-path error also occurred before any
restoration; its correction and additional debit are retained. The corrected
service restored the three hash-locked wheels offline with networking disabled.
All 2,056 frozen interpreter/library/metadata hashes matched exactly before
timing; all eight fresh host control checks passed.

The measurement service entry consumed 77.48 seconds through restoration,
qualification, all cells and independent verification. The experiment cgroup
recorded 25.96 CPU seconds and a 60.58 MiB memory peak; this peak excludes the
guardian and restoration processes outside the experiment branch. The enclosing
service enforced one CPU, 2 GiB memory and zero swap for all descendants too.
No experiment memory/task limit events, truncation, timeouts, malformed outputs,
wrong results or incomplete pairs occurred. The four-task experiment limit held.
Largest output is 524,288 bytes. Post-run package/artifacts occupy about 6 MiB,
well below 128 MiB. No paid resources, installs of optional native backends,
publication, commits, pushes or tracked-file edits were performed.

Conservative accounting is 407.48 seconds elapsed/core through in-service final
verification, including 180 seconds preparation, 60 seconds original failed
launch, 60 seconds bootstrap failure, and 30 seconds helper reservation. The
independent readback adds 5.57 seconds, giving 413.05 seconds before final
diagnosis/report allowances. FINAL_RECEIPT.json adds a further 60-second
conservative allowance for diagnosis and reporting rather than claiming exact
unsampled helper CPU. This remains below both shared 1,200-second caps. No debit
was reset and no performance cell was rerun. All three owned launch/recovery
services are collected and all experiment cgroups are removed.

Evidence: APPROVAL.json, RECOVERY_APPROVAL.json, RECOVERY_BOOTSTRAP_CORRECTION.json,
RUNTIME_RESTORATION.json, EXECUTION_HOST.json, LAUNCH_STARTED.json, ROWS.jsonl,
EXECUTION.json, FINAL_ACCOUNTING.json, RUN_VERIFICATION.json, PHASE_MEDIANS.json,
POST_EXECUTION.json, POST_RUNTIME_DIAGNOSIS.json, FINAL_RECEIPT.json and
EXECUTION_SHA256SUMS.json. Historical preparation and failure records are retained;
the original SOURCE_SEAL.json and all previous pilot evidence remain unchanged.

Required measurement and analysis work is complete. Keep the current explicit
backend choice; skip another synthetic timing run without a concrete application
decision. Before a future campaign, identify the runtime deletion source and
prepare a persistent isolated runtime under a new scoped setup authorization.
Defer that work until another campaign is requested. No further thread or model
run is needed now; closely related interpretation belongs in this chat.
