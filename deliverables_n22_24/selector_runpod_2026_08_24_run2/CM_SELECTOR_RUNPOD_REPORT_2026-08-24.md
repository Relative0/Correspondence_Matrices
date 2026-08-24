# CM selector and website-claim compatibility rerun

Date: 2026-08-24
Accepted remote scope: three independent secure Linux CPU pods, $1 hard cap,
automatic termination, current selector replay plus frozen B1 control.

## Verdict

The guarded Runpod campaign **passed** its pre-registered remote gates. All
three pods verified the 64-file source snapshot and all frozen corpus digests,
ran Python 3.13.5 with NumPy 2.3.2, produced exact packed results, passed the
selector and B1 acceptance checks, and were terminated. A post-campaign Runpod
API listing found zero live `cm-selector-*` pods.

This does **not** establish a universal `live_k >= 16` selector threshold. The
immediately preceding Windows replay found one held-out CM row at `live_k=15`
with 2.109x regret. The same row favored words on every Linux pod, but only by
1.37x to 1.61x. The aggregate selector is good; the `k=13..15` tail is
hardware-sensitive and remains the next selector experiment.

## Remote results

| pod | CPU / Linux kernel | raw tuning regret | raw held-out regret | CM tuning regret | CM held-out regret | catastrophic rows | B1 blocked geomean [95% CI] | measured cost |
|---|---|---:|---:|---:|---:|---:|---|---:|
| 1 | AMD EPYC 7702P / 6.8.0-117 | 1.0069 | 1.0166 | 1.0035 | 1.0143 | 0 | 0.8961 [0.8854, 0.9058] | $0.001820 |
| 2 | AMD EPYC 7713 / 6.17.0-35 | 1.0071 | 1.0154 | 1.0037 | 1.0124 | 0 | 0.8890 [0.8783, 0.8991] | $0.003464 |
| 3 | AMD EPYC 4564P / 6.8.0-51 | 1.0044 | 1.0161 | 1.0014 | 1.0164 | 0 | 0.8846 [0.8739, 0.8946] | $0.001490 |

Acceptance required selector regret geomean <= 1.10 and zero rows with regret
>= 2x for all four raw/CM tuning/held-out summaries. The B1 control required
the all-corpus point estimate within 0.05 of 0.8876 and its interval below
parity. Every pod passed every check separately; results were never pooled.

The three successful pods cost $0.006774. The audit carries a conservative
$0.01 reserve for two failed pre-evidence attempts, so recorded total exposure
is $0.016774, far below the $1 hard cap.

## Local compatibility reruns

- Full suite before the campaign: 345 passed plus 4 subtests in 101.48 s.
- Full suite after campaign-tool changes: 345 passed plus 4 subtests in 109.53 s.
- Existing Runpod unit tests: 7 passed in 6.78 s.
- B1 replay: 0.8904 [0.8783, 0.9021], consistent with archived 0.8876
  [0.8724, 0.9016].
- B3 structural scaling: median preparation ratio 5.1618 versus archived
  5.1394. The 8,388,603-occurrence / 77-structural-node ladder compiled in
  1,046 us versus archived 984.5 us, with essentially unchanged ratio
  (5.2457 versus 5.2423). The structural-DAG scaling conclusion holds.
- B4 guard: 3,000 trials, zero wrong guards, zero oversized outputs.
- B1, B2, B4 and BX1 regenerated their exact frozen corpus hashes.

## Website claim warning: legacy B2/B4 baselines are now asymmetric

The current B2 and B4 reruns appear to reverse the old whole-call result at
`live_k=6..12`. That is **not accepted as a CM advantage**. The CM wrapper now
uses flat bigint through `k=15`, while those 2026-08-03 drivers retain a
words-oriented BitSet control above `k=6`. The rerun therefore compares the
improved selector on one side with the superseded selector policy on the other.

Consequently, do not update the website from the apparent B2/B4 sign reversal.
First create a successor wrapper protocol that gives both sides the same
current selector or directly reports flat and words arms separately. Preserve
the legacy reruns as evidence that the old protocol no longer answers the fair
current question.

## Next tests

1. Freeze a tuning corpus at exact supports `k=13,14,15`, retain a separate
   circuit-held-out slice, and run it on Windows plus materially different
   Linux CPUs. Include instruction count and peak live word buffers as possible
   selector features.
2. Replace B2/B4 with a symmetric current-policy wrapper comparison before
   changing the master explainer.
3. Map `k=17..20` with isolated processes, explicit scratch/output budgets,
   RSS telemetry, timeouts, and fail-closed refusal records.

## Evidence locations

- `selector_runpod_audit_2026_08_24.json`: campaign guards, snapshot hashes,
  per-pod environments, acceptance records, costs and termination state.
- `pod*/deliverables_n22_24/pod_out/current_*`: raw selector, phase, summary and
  environment evidence from each pod.
- `pod*/deliverables_n22_24/pod_out/b1/*`: frozen B1 controls.
- `../selector_runpod_2026_08_24/`: retained failed-attempt audit and recovery
  record; no failed-attempt result was accepted.
- `../reruns_2026_08_24/`: local B1/B2/B3/B4/BX1 and selector reruns.
