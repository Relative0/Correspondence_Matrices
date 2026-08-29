# Runpod structural validation result — 2026-08-29

## Outcome

The one authorized structural-validation attempt completed successfully.
Pod `8voqzr4b1a4qti` was created once (HTTP 201; request
`req_b7c892ed-8d71-4593-9bbd-4de26cf27924`), ran the exact frozen workload,
returned complete bounded evidence, and was deleted once (HTTP 204). The
controller and watchdog subsequently found both v1 and v2 inventories empty.
The independent postflight found all three campaign pod IDs absent (404) in
both APIs, both host wake guards exited, and no replacement was queued.

The verified allocation was Secure CPU `cpu3c`, 2 vCPU, 4 GB RAM,
$0.06/hour, the pinned Python 3.13.15 image digest, 12-GB container disk,
zero pod volume, no network volume, and only HTTPS proxy ports 8080/8081.
The measured allocation interval was about 84.16 seconds; compute-only cost
is estimated at $0.001403. Billing currently contains the two earlier pod
records totaling $0.001686 but not this new pod, so billing may still lag.
The conservative campaign bound used for postflight is $0.021403, below the
$0.20 cap; the pre-create phase projection was $0.023333, below $0.10.

## Evidence reconciliation

- All 70 focused JUnit cases passed with no failure, error, or skip.
- The exact planned grid completed: 20 cases, 240 child jobs (180 cold and
  60 warm), 360 comparable representation calls, and 1,560 rows.
- Every row reported `ok` and exact semantic agreement. Each case had one
  consistent output hash across representations, schedules, and repetitions.
- All 13 locked package versions matched. All 19 study-source snapshots
  matched their source manifest, and the current 65-file upload manifest
  still hashes cleanly.
- The 41-file evidence archive matched every extracted byte. Extracted
  evidence totaled 4,272,521 bytes, within the 16-MiB cap.
- The remote summary retains `production_estimator_accepted: false` and
  `real_workload_compatibility: "not measured"`.

## Memory findings

The ratios compare estimator values with measured tracemalloc peaks in the
single eligible window for each representation call. They are not whole
process RSS guarantees.

| Representation | Calls | Legacy estimate too low | Candidate too low | Largest candidate estimate / peak |
| --- | ---: | ---: | ---: | ---: |
| Dense | 120 | 120 | 0 | 26.01x |
| Bigint | 120 | 87 | 0 | 110.52x |
| Words | 120 | 78 | 0 | 195.86x |
| **Total** | **360** | **285** | **0** | **195.86x** |

The legacy estimate was too low for 285/360 calls (79.2%), reaching a
312.19x peak/estimate ratio in a cold dense `reconvergent-xor`, k=6 case.
The candidate covered every measured call. Its tightest observed case still
had about 1.80x headroom, while its median estimate was 8.58x the measured
peak, p95 was 154.09x, and maximum was 195.86x in a warm words
`reconvergent-xor`, k=8 case. Coverage improved, but overconservatism remains
large enough that these data do not justify accepting the candidate unchanged.

The study recorded 5,040 profile decisions. Both models produced 2,430 `ok`
and 90 `refused` decisions. Every refusal was the preregistered
`strict-diagnostic` profile rejecting k=16 on its `max_output_vars=14`
boundary. Recorded false-admission and false-refusal flags were zero. The
study code defines false refusal only for temporary-memory refusals, so that
zero does not validate whether the variable-count refusals were desirable.

Runtime reported 192 host logical CPUs, but the process affinity was exactly
two CPUs (`[86, 182]`), consistent with the allocation. The captured CPU
cgroup value was `max 100000`, so no CPU quota should be inferred from that
field. The captured memory cgroup ceiling was 3,999,997,952 bytes, which
provides machine-level limit provenance absent from the earlier smoke.

## What remains important

This closes the preregistered synthetic structural phase, not estimator
acceptance. The highest-value next experiment is a separately frozen,
bounded real-corpus compatibility study using the existing BX1/B2/EPFL
inputs, with an independent semantic oracle where feasible. It should retain
raw per-case attribution and explicitly separate corpus refusals from
measurement failures.

A second priority is a temporary-memory boundary study that places candidate
estimates just below and above configured limits. The current k=16 refusals
exercise only the variable-count rule and therefore do not test whether the
candidate's large conservatism causes avoidable memory-policy refusals. Model
coefficients and production defaults should remain unchanged until those
studies and a full regression are reviewed. Any new Runpod allocation needs
a new exact authorization; this one-create authorization is consumed.

## Reproducible evidence

Run directory: `http-structural-execute-001/`.

| Evidence | SHA-256 |
| --- | --- |
| `RUN.json` | `6b4a7dfdb035ba098104b36e65d167186ddf9bb2ae968f4ea100c6a16ab426ae` |
| `evidence.zip` | `ccd5c877f2ce9a8e14cb71a23be4e964c2f150514d6683339f64c630f3200b2d` |
| `structural/raw.jsonl` | `c7f5d74e82c22be9fea676ce41b2f25e50bc8b4c4c320438100e05fc577b7574` |
| `structural/summary.json` | `99bd31e1596114ed81bfbe12f0f58063fb51c248ed2e8250e4f01d2733bb4f63` |
| Final verification | `845dd51834d813f6f50f5251ad6ca9ce494f697bf269998a7f2e02a9364ee801` |
| Analysis | `5df5c3891a90f71b49c5a19d50f563c3e426dd87ba4305f1120f1e71de270de8` |

The executed controller SHA-256 is
`f512333e1623fd921b3d4a965064f33398a9ebd7368cde58715c8898c7c4f2f7`;
the executed preflight SHA-256 is
`023a431eaf9b35603333637a984a84dc74fda4e61ee153d9179dfc8f27d8c89b`.
The failed read-only preflights and billing-shape probes were preserved. No
pod create occurred until the final preflight passed.
