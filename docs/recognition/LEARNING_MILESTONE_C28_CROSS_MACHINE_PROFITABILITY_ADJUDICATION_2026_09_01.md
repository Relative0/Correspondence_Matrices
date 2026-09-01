# Learning milestone C28: no-refit cross-machine profitability adjudication

Status: implemented and independently verified; shadow and production promotion refused

## Question

C27 showed an eight-query point-estimate win on the primary Windows run, three Linux
Docker repetitions on the same computer, and one physical second-machine RunPod run.
C28 asks whether those frozen measurements justify a general profitability rule once
within-run timing uncertainty and physical-machine identity are treated conservatively.

C28 does not train a model, refit the transparent C27 support rule, rerun a timing, or
change an exact output. It reads the five independently verified C27 artifacts and makes
an evaluation-only decision.

## Inputs and machine scope

The adjudicator hash-binds five executions of the same C27 policy, dataset, methods, and
exactness contract:

1. the primary Windows confirmation;
2. three pinned Linux/amd64 Docker repetitions on that same physical computer; and
3. the Secure `cpu5c` RunPod confirmation on an AMD EPYC 4564P.

The three Docker repetitions and Windows execution count as four executions but only one
physical machine. RunPod supplies the second physical machine. In total, C28 verifies
**3,600 measurement batches**, **37,800 timed queries**, and **120 memory batches**, with
zero semantic or artifact mismatches.

## Prespecified adjudication rule

For every execution and query count, C28 jointly resamples complete round identities so
the screened baseline and support-aware candidate stay paired across all four widths. It
exhaustively enumerates all **3,125** five-of-five round resamples rather than using a
random bootstrap seed.

Admission requires both the recorded point estimate and the one-sided 95% paired-round
lower bound to reach:

- aggregate speedup over resident direct screened: at least **1.00x**; and
- minimum-width speedup over resident direct screened: at least **0.90x**.

The cross-machine value is the minimum across all five executions. A general `q >= k`
shadow rule additionally requires every measured query count at or above `k` to pass.

## Cross-execution envelope

| Queries | point aggregate floor | point width floor | bootstrap aggregate floor | bootstrap width floor | admissible |
|---:|---:|---:|---:|---:|:---:|
| 1 | 0.7940x | 0.5118x | 0.6527x | 0.2624x | no |
| 2 | 0.9209x | 0.6771x | 0.5878x | 0.4506x | no |
| 4 | 0.9407x | 0.8391x | 0.7555x | 0.5054x | no |
| 8 | **1.0240x** | **0.9498x** | 0.9279x | 0.5972x | no |
| 16 | 0.9854x | 0.8520x | 0.8376x | 0.6726x | no |
| 32 | 0.9700x | 0.9163x | 0.7983x | 0.6538x | no |

Eight queries is the only count whose point estimates pass on every execution. It does
not survive the paired-round lower-bound gate. No query count is uncertainty-admissible,
and the measured surface contains no point-safe or uncertainty-safe monotonic suffix.

The q8 RunPod execution alone clears both lower-bound thresholds at 1.0165x aggregate
and 0.9217x minimum width. Each of the four executions on the primary physical computer
fails at least one q8 uncertainty threshold; the primary Windows run supplies the worst
0.9279x aggregate and 0.5972x minimum-width bounds. This localizes the immediate problem
to execution/round/width stability on the primary machine rather than showing a uniform
regression on the second machine.

## Decision

C28 refuses both shadow and production promotion. The exact resident direct screened
path remains the required fallback. The earlier q8 wins remain useful research evidence,
but they do not justify a general `q >= 8` router.

This is a deliberately conservative result. With only five rounds per execution, the
paired bootstrap measures sensitivity to recorded round variation rather than providing
a publication-grade hardware confidence interval. Counting the three Docker repetitions
as independent machines would overstate the evidence, so C28 does not do that.

## C29 follow-up

C29 now preserves the same exact candidate and baseline while localizing all 100 frozen
q8 width/round cells and adding 64 adjacent counterbalanced local pairs. It confirms that
the 0.5972x floor is a Windows n=4 query-path outlier, while n=3 is the persistent
width-level regression. In the new diagnostic, policy loading and validation account for
92.38% of median candidate setup; that fixed cost erases the n=4 query-only gain, but it
does not explain all query-path variance. Promotion remains refused. C30 should implement
a hash-bound prepared-policy context and repeat the unchanged diagnostic before another
two-machine confirmation.

## Evidence

- Run: `docs/recognition/runs/c28-cross-machine-profitability-adjudication-20260901-001`
- Input manifest: `docs/recognition/runs/c28-cross-machine-profitability-adjudication-20260901-001/input_manifest.json`
- Results: `docs/recognition/runs/c28-cross-machine-profitability-adjudication-20260901-001/results.json`
- Independent verification: `docs/recognition/runs/c28-cross-machine-profitability-adjudication-20260901-001/independent_verification.json`
- Adjudicator: `cmbench/comparative/gf2_cross_machine_adjudication.py`
- Experiment runner: `scripts/cm_comparative_c28_cross_machine_adjudication.py`
- Verifier: `scripts/crse_gf2_cross_machine_adjudication_verify.py`
- Tests: `tests/test_cm_comparative_gf2_cross_machine_adjudication.py`
