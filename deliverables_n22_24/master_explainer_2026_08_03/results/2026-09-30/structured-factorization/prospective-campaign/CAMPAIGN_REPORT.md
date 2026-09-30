# Prospective live-vtree integration campaign — final record

The new, separately frozen synthetic campaign completed on Linux. **Mechanism
GO passed; algorithmic GO failed.** Live PySDD moves preserved every matched
fresh-search decision and made the search stage cheaper, but they did not make
the selected complete exact factorization method faster than the selected
baseline on the held-out split. The Phase 5B negative result remains unchanged.

## Provenance and execution

The registered `CAMPAIGN_PROTOCOL.md` and 36-record
`candidate_manifest.json` were frozen before any validation row. The freeze
receipt SHA-256 is
`e7b1250c3a512fa7b2d1bbf76cf46a4ff8b0e2654c7231035fb29411f252c587`.
The local Linux Docker run used `python:3.11-slim` image digest
`sha256:e41613d42d4891e4930f79523f93f81bbc7632584ec65e36ab055f41a800b41e`,
Python 3.11.16, pinned packages including PySDD 1.0.6, 4 GiB container
memory, 2 CPUs, a 2 GiB worker `RLIMIT_AS` and a 20-second watchdog. The
freeze hard-cap negative control and capped PySDD exactness smoke passed.
Earlier Phase 5B and integration directories were mounted read-only.

Validation completed all 252 planned rows. The registered selection rule
locked B2 as baseline and L1 as challenger; the validation-results SHA-256
is `35ff39d90574722392b31995ad5fdc77bc145e8cdcb5a2e345bc4d0fb56ba168`.
Held-out then completed all 504 planned rows, with SHA-256
`f667606603bd2f6383e73ccd61c31c8ebe77f0d5a8130bdfc6706c207b23b21e`.
All 756 rows had status `ok`, matched their frozen job identities and
resource metadata, and passed the runner's independent semantic and carrier
partition checks. Cumulative worker process-wall time was 270.31 seconds,
well below the registered 90-minute ceiling; no row was censored. The
maximum reported worker peak RSS was 31.8 MB.

## Registered decision

| Gate | Registered measure | Result |
|---|---|---:|
| Complete-time primary | L1 / B2 held-out paired geometric ratio | 1.03798 |
| Complete-time uncertainty | One-sided 95% bootstrap upper ratio | 1.14154 |
| Fresh/live M1 parity | F1/L1 matched pairs and mismatches | 72/72; 0 |
| Fresh/live M2 parity | F2/L2 matched pairs and mismatches | 72/72; 0 |
| M1 search mechanism | L1 / F1 geometric ratio; upper 95% | 0.18050; 0.20167 |
| M2 search mechanism | L2 / F2 geometric ratio; upper 95% | 0.18087; 0.20094 |

The complete-time ratio fails the required <=0.90 improvement and its upper
bound fails the <1 condition. Both matched search mechanisms satisfy their
registered criteria with complete pairing and no decision mismatches. The
saved `campaign_analysis.json` accordingly records `mechanism_go: true`
and `algorithmic_go: false`; there were no method failures.

## Exposure diagnostic and scope

As a post-campaign diagnostic on saved rows, B3's direct partition missed
the exact semantic partition on 12 of 24 held-out instances. L1 missed on
8 of 24. L1 reached the exact direct partition in four B3-miss cases, all
four sizes of the equivalence-ladder-bridge family. This exposure result was
not used to select methods or change the registered objective. It establishes
some genuine factor recovery in the new synthetic inputs, while the primary
complete-time result remains negative. These small, constructed CNFs do not
support a public-corpus or large-scale performance claim.

The source hashes, complete rows, frozen selection and analysis were checked
again after the run. The disposable container exited and was removed. No
Runpod resource was used.
