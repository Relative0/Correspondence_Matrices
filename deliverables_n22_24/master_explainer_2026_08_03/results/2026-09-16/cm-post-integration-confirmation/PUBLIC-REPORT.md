# CM post-integration performance confirmation

## Outcome

Commit `63285d2bd16e16ca48d8a0328b6f6328ea038b35` completed the original B2/B4 and corrected-E3 schedules on Windows and on a disposable Linux CPU
host. All 792 accepted Windows B2/B4 rows, 264 Linux B2/B4 rows, 576 accepted Windows E3 rows, and 192 Linux E3 rows
matched their frozen packed outputs exactly. Every B2/B4 run selected 208 flat-engine and 56 word-engine rows.

The bare CM kernel remained about 9% faster than CSE-flat: CM/CSE-flat was **0.9075** across three Windows repetitions
and **0.9098** on Linux. This closely reproduces the accepted V3 result of **0.8906**.

The whole-call wrapper ratio moved in an unfavorable direction: **3.8786** on Windows and **3.6618** on Linux, versus
the historical **3.0941**. This is a ratio change, not an absolute wrapper regression. The current wrapper absolute
geometric mean was **34.152 us** on Windows and **43.168 us** on Linux, both below the historical **56.082 us**;
CSE-flat improved more.

## Matched B2/B4 results

| Host / record | CM bare / CSE-flat | CM wrapper / CSE-flat | CM bare | CM wrapper | CSE-flat |
|---|---:|---:|---:|---:|---:|
| Windows, 3-run geometric mean | **0.9075** | **3.8786** | 8.422 us | 34.152 us | 9.223 us |
| Linux, 1 run | **0.9098** | **3.6618** | 11.208 us | 43.168 us | 12.262 us |
| Accepted V3, historical | **0.8906** | **3.0941** | 16.907 us | 56.082 us | 18.849 us |

The Linux bare ratio differs from the Windows result by about 0.26%. The Linux wrapper ratio is about 5.6% below the
Windows result and 18.3% above the historical result. Host-specific absolute times remain visible because cross-host
latencies are not paired comparisons.

## Corrected-E3 and break-even

| Host / record | Blocked CM / CSE | Round-robin CM / CSE | CM / CSE-flat kernel |
|---|---:|---:|---:|
| Windows, 3-run geometric mean | **0.8943** | **0.9021** | approximately 1.002 |
| Linux, 1 run | **0.8788** | **0.8941** | 0.9755 |
| August replay, historical | **0.8876** | **0.9336** | 1.0038 |

Plain-CSE finite-median crossover ranged from 69.5 to 86.5 calls on Windows and was 92 calls on Linux. CSE-flat
crossover ranged from 115 to 195 calls on Windows and was 346 calls on Linux. These estimates divide preparation
gaps by small per-call timing gaps, which magnifies routine timing variation. They remain machine-specific planning
estimates rather than stable performance claims.

## Monitoring repair and evidence boundary

The first Windows symmetric attempt was excluded after a short-lived descendant exited between process discovery and
process opening. The supervisor was repaired before repetition: it suppresses an access error only after a fresh
snapshot proves that exact PID has exited; a still-live access failure remains fatal. A deterministic check exercised
both paths. The replacement A1 and all later accepted workers verified the real Python PID before imports.

The public bundle is derived from sealed local manifests
`a064fc5db7b660542eb9594678e62058c0cc968b69e608e95b22279cc736a931` and
`144ea6b7b095c21ba73712b151bc7f6856fc918a09617dc90713cd0ff08f61ce`. It includes numerical evidence,
analysis, verification, and a reproduction protocol. It omits absolute private paths, credentials, pod identifiers,
operational logs, failed pre-creation attempts, and duplicated source snapshots. The immutable source commit and file
hashes preserve the source identity.
