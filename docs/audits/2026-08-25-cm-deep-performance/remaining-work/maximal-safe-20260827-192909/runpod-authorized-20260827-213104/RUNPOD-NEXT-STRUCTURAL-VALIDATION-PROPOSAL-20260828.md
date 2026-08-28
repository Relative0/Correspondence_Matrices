# Next bounded structural validation phase — proposed only

**Not authorized; not launched.** The k=6,8 smoke passed. This prepares one
next phase without implying approval to reuse a consumed controller or
start a broad pod matrix. The complete corpus/full-regression upload package
is still separate work; those results remain unmeasured.

## Proposed scope

Use the unchanged 65-file manifest and 13-wheel lock, the same pinned
Python 3.13.15 image digest and authenticated HTTP bootstrap, and one new
Secure CPU pod: 2 vCPU, at least 4 GB RAM, at most $0.25/hour, 12-GB container
disk, zero pod volume and no network volume. No GPU, SSH, Jupyter, source
build, corpus download, additional dependency, or automatic replacement.

Cap this new phase at $0.10 and the entire smoke/validation campaign at $0.20,
including storage and prior charges. Conservatively reserve at least $0.02
for the two completed HTTP allocations while billing may lag, increasing
that amount if attributable billing requires it. These are proposed limits,
not permission to extend the completed HTTP approvals.

Keep a 20-minute lifetime from the sole create request, independent cleanup
at 18 minutes, zero-pod baseline, actual resource/price checks, private
root-loader authentication and owned-resource-only deletion. Maintain the
16-MiB evidence bound and independent inventory/billing/process postflight.

## Frozen scientific question and command

Test the existing candidate coefficients without changing them across all
five preregistered families and k=6,8,12,16. Keep **none-fixed contexts** in
this phase so output and lifetime bounds remain small. Keep calibration
families (mixed-chain, shared-diamond, wide-and) separate from held-out
structural families (alternating-tree, reconvergent-xor). The already-seen
smoke families must not be used to tune the candidate and relabeled untouched.

After the same hash-locked binary installation and `pip check`, rerun the
same 70 focused budget tests, then run exactly:

```sh
python scripts/cm_memory_estimator_study.py --execution runpod --supports 6 8 12 16 --families mixed-chain shared-diamond wide-and alternating-tree reconvergent-xor --contexts none --schedules cold warm --repetitions 3 --output-dir /workspace/cm-memory-smoke/run-output/structural
```

The prespecified complete grid is 20 structural cases, 240 child jobs
(180 cold / 60 warm), 360 recorded representation calls and 1,560 window
rows if every case completes. These are planned counts, not measured data.
The same per-child 30-second, 64-KiB output and 32-MiB candidate-estimate
limits remain. No threshold is raised to force a case to complete.

Keep setup within five minutes and focused tests within two minutes.
Bound the study to ten minutes and also to the watchdog's remaining time
minus a one-minute evidence/cleanup reserve. On timeout or output-cap
failure, retain available diagnostics, report incomplete coverage and stop;
never infer success for missing rows or create a replacement. This is a
bounded subset of the preregistered larger design, not its completion.

## Work required before launch if approved

Create a new controller/run identity; preserve executed v1/v2/v3 controllers.
Freeze the new remote-command adapter and verify the same 65 source hashes
and 13 wheel hashes. Extend only the offline command, expected-grid,
deadline and budget cases. Reconcile both completed pod IDs and attributable
costs; retain the independent Windows watchdog binding/liveness gates.

Approval would cover the exact source upload and locked installation on
this new pod, the stated tests/study, evidence retrieval and deletion. It
would not authorize corpus/full pytest, changed coefficients, a production
estimator, `production-balanced-v1`, workload capture/replay, native/JIT
lanes, publication, support messages or git operations.

## Approval text for a later decision

I authorize one additional Runpod structural-validation pod exactly as
specified here, using the same 65 files, 13 locked wheels and pinned image,
the stated k=6,8,12,16 none-fixed structural command, $0.10 phase / $0.20
campaign limits including prior costs, a 20-minute lifetime and independent
owned-pod cleanup. No replacement or wider workload is authorized.
