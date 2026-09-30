# Convergence audit and computation preparation — 28 September 2026

**Verdict: RETURN TO BOTH THREADS. Publication form: retain the current technical report.**

The earlier responses in this task performed intake only. This pass performed a fresh primary-source search, reconstructed the principal proofs, inspected the source manuscripts and external audit, reran the independent mathematical checker, reran the original correctness and timing programs, and implemented C1/C3/C4 preparation. The external Astra audit is preserved under `inputs/external_audit/`, credited as an input rather than presented as a report authored by this task. The seven new reports in `REVIEWER_REPORTS/` are same-assistant specialist perspectives, not seven independent agents or human peer reviews.

## Surviving findings

The exact indexed Q_k/Fourier equivalence is sound over characteristic-zero fields. The query rank is the dimension of the low-degree character span. Boolean collision bounds have established trade-theoretic antecedents. The rank-one/rank-two reconstruction jump is correct under a fixed nonempty cut and a promised rank-bounded class, but remains a short corollary with uncertain exact priority. It does not itself predict compressed storage, query latency, or amortization.

The lower bound for linear sketches requires all real-valued inputs. Encoding a Boolean truth vector as a single arbitrarily precise integer refutes an attempted extension from scalar dimension to Boolean bit complexity. The parity pair can be distinguished by one bit of stored class identity while its worst-case reconstruction depth is n. This directly separates reconstruction depth from required storage.

Q16 needs cumulative-budget and all-protocol quantifiers. Q_k supports residual queries of depth k-s after s coordinates have been fixed; it does not generally support a fresh depth-k horizon after each update. The xy versus (1-x)y example independently shows why unordered global factor histograms lose named-coordinate information. No new T3 theorem or falsifiable hypothesis has been supplied; the user expressly confirmed this during this pass.

## Reproduced evidence

- Imported external audit integrity: 85 manifest entries pass.
- Its mathematical checker passes again; the entire `tests` object agrees with the external result. Coverage includes exact operator ranks through n=6, all Boolean fibres through n=4, direct class thresholds, and 613,656 restricted-profile comparisons.
- The original baseline's eight-command correctness replay passes. The original Theory verifier passes with only its output-path literal redirected by the external audit's recorded wrapper.
- The original 38-case/570-trial lifecycle replay again has **zero artifact wins versus packed** by per-case median. This is a local reproduction of a narrow negative result, not a theorem that artifacts cannot win.
- New C1 adapter tests check all 65,536 4x4 factorizations, 613,656 rank-at-most-two restrictions against the project implementation, and 42,192 reordered-cut/cumulative-update cases. Main source is pinned by file hashes because the repository already contained unrelated dirty changes.

## New preparation, separate from publication evidence

The corpus protocol was saved before extraction. All 2,861 primary outputs of 20 original EPFL designs in two application families are accounted for. At structural support <=12, 1,088 outputs from 11 designs are admitted and 1,773 excluded. Two deterministic cuts, deduplicated per output, yield 2,119 cases. All admitted output hashes agree with a separate repository parser/evaluator, including independent scalar evaluation of 31 constant outputs.

The split is design-disjoint and prospective for this experiment, not historically unseen: the EPFL suite appeared in earlier project work. Low-rank incidence is tabulated per design. No favorable T3 regime has been defined, and natural rank incidence must not be equated with favorable-runtime incidence. One decoder and the memory-controller design contribute many correlated outputs, making pooled-output conclusions particularly unsafe.

Matched packed binary, retained coordinate-indexed rank factors, and a compiled CUDD fixed-order backend now support the same count/update endpoint. Their binary round trips and original/residual query semantics pass all Boolean functions through n=3. CUDD is a compiled representation with exact Python-integer traversal; its adapter is not claimed to match every optimization of an industrial counting pipeline. No decomposition-quality superiority is claimed, so no LUT-mapping result is used as a surrogate comparator.

The harness records source preparation, compile/discovery, verification, serialization, load, indexing, update, query, executed batch counts and absolute process peak RSS. Fresh-process loads use a separately created artifact. File-specific advisory eviction is available on Linux, but no claim of proven physical cold disk/cache is made. Smoke timings are infrastructure validation, not the main performance campaign.

## Paper-type decision

| Candidate | Finding |
|---|---|
| Theory-first | No differentiated substantial main theorem is established. |
| Empirical/methods | Baseline negative result is reproducible but narrow; new comparator/corpus preparation has not yet yielded a preregistered methods result. |
| Integrated | The missing T3 statement still prevents an experiment from testing a quantitative theory prediction. |
| Technical report | Supported and remains the current publication form. |
| Split papers | Neither new branch independently supports the claimed stronger publication threshold. |

## Required next action

**SEND RESULTS/QUESTION TO THEORY:** use `COMPUTATION_REQUEST_TO_THEORY.md`. Keep C2 paused until a frozen theorem, restricted negative theorem, or falsifiable hypothesis supplies the target. C1 and the bounded C3/C4 infrastructure are prepared; this is not completion of the scientific convergence gate. Send this dated audit to Master as a status supplement, not as approval for manuscript promotion or a Runpod launch.
