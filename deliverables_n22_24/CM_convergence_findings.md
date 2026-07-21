# CM ↔ Bitset Convergence at Larger n (full output) — Audited

> **Scope correction (2026-07-21):** this is a pre-C1a study of the recursive CM kernel
> against the recursive raw-AST bitset walk.  It explains the old trend but is not the
> current flat-vs-flat performance result; use the C1a fairness control and the later audit.

> Answers: "does CM No-Reinflate converge closer to Bitset past n=16, and are there
> improvements that would push it further?" Measured this session on your machine
> (Python 3.13.5, post-R1/R2/R3), **full-output, genuine full-arity expressions**
> (`live_k = n`, guard disabled), cached per-eval medians. Every measured point spot-checked
> bit-exact vs `eval_expr_tt`. Data: `CM_convergence_fulloutput.csv`.

## 1. The two claims, kept separate

- **"CM beats bitset in absolute time"** — only via the *reduced* representation (small
  `live_k`). Unchanged; bitset is the flat lower bound.
- **"The CM/Bitset *ratio* converges toward 1.0 as n grows"** — this is what your chart's
  downward trend hinted at, and it is **real**. It is a different phenomenon from the first,
  and it lives in the *full-output* regime.

## 2. Measured convergence (full output, full arity, cached per-eval)

| n | CM-NR / Bitset | CM-kernel / Bitset | Expr-tree nodes | CM-DAG nodes | DAG/tree |
|--:|--:|--:|--:|--:|--:|
| 16 | **1.67×** | 1.61× | 296 | 134 | 0.45 |
| 18 | 1.63× | 1.62× | 315 | 149 | 0.47 |
| 20 | 1.50× | 1.50× | 298 | 150 | 0.50 |
| 22 | 1.47× | 1.47× | 313 | 155 | 0.49 |
| 24 | **1.31×** | 1.37× | 336 | 176 | 0.52 |

The ratio drops **monotonically 1.67 → 1.31** from n=16 to n=24. So yes — it converges
closer at n=20 (1.50×) and closer still at n=24 (1.31×). (The n=16 value 1.67× reproduces
the deck's threshold-9 one-shot figure of 1.69×, a useful cross-check that the pipeline is
measuring the same thing.)

## 3. Why it converges — and where the floor actually is

Per full-output eval, both methods do roughly *(number of nodes) × (one 2^n-bit integer op)*
plus fixed Python per-node overhead (dispatch, memo, wrapper). As n grows, the 2^n-bit op
grows without bound while the per-node Python overhead is fixed, so:

```
ratio(CM/bitset)  →  (CM-DAG node count) / (Expr-tree node count)   as n → ∞
```

Two measured facts drive this:

1. **CM's canonicalized IR DAG has ~half the nodes of the raw Expr tree** (interning shares
   common subtrees; DAG/tree ≈ **0.45–0.52**). So in the pure-arithmetic limit CM does *fewer*
   big-integer ops than the raw-bitset AST walk — the structural floor of the ratio is ~**0.5**,
   i.e. CM could in principle end up ~2× *faster* on full output.

2. **But CM currently pays a large per-node Python overhead**, which only slowly amortizes.
   Backing it out of the timings (kernel-ratio × tree/DAG, → 1.0 would mean "pure arithmetic,
   no overhead"):

   | n | 16 | 18 | 20 | 22 | 24 |
   |---|--:|--:|--:|--:|--:|
   | per-node overhead factor | 3.55 | 3.43 | 2.99 | 2.97 | 2.62 |

   CM's per-node cost is still ~2.6× the raw walk's at n=24 — i.e. even with 2 MB integers,
   fixed overhead (the `id()`-keyed memo that holds *every* intermediate 2^n-bit result, the
   recursive dispatch, the wrapper) is not yet negligible. It is *shrinking* (3.55 → 2.62),
   which is exactly why the ratio falls, but the approach to the 0.5 floor is slow:
   extrapolating, the ratio would only cross **1.0 around n ≈ 30**, which is RAM-infeasible
   for full output (§ audit doc §8.1: ~9 GB at n=28).

So: convergence is genuine, but on the *current* recursive kernel the break-even point sits
past where full 2^n output fits in memory. The interesting part is that the *structural*
advantage (half the nodes) is already there — it is being masked by per-node overhead, not
absent.

## 4. The improvement that actually moves this (and it's already scoped)

The lever is **cut the per-node overhead factor from ~3× toward 1×.** That does *not* need
larger n — it makes CM realize its 0.5 node-count advantage at *practical* sizes. That is
precisely the **Tier-C flat evaluator** (`CM_tierC_rescope_report.md`), whose prototype
already measured **bound-flat ≤ raw bitset at n=16** (ratio ≤ 1.0) by lowering the DAG to a
linear instruction list with slot reuse — no per-node dict/dispatch, and no holding of all
intermediates. Concretely, the promising directions, in order:

1. **Flat/linear kernel (Tier-C C1a).** Compile the DAG once to a postorder program; eval
   touches slots, not a memo dict. Removes the dominant overhead term measured above.
   Prototype: kernel ≤ raw bitset at n≤16. **Highest leverage; directly attacks the 3× factor.**
2. **Memory-lean intermediates.** The current `id()` memo keeps *all* node results live
   (176 × 2 MB ≈ 350 MB at n=24). A last-use / refcount-style free (or memoizing only
   fan-out>1 nodes) would cut cache pressure that grows with 2^n — likely a real chunk of the
   residual at large n. (Hypothesis, worth a profiling pass to confirm.)
3. **numpy-word kernel for wide outputs (Tier-C C1b / "numpy-words").** At n≥16 the Tier-C
   report already found the numpy-uint64 kernel wins (width ≥ 65 K bits); width-selected, it
   would lower the per-op constant itself at exactly the large-n end where you want
   convergence.

Expected effect: with the flat kernel, the full-output ratio should sit near or below 1.0
from n≈16 upward (realizing the 0.5 structural floor as overhead → 1×), instead of waiting
for n≈30. That is the concrete "closer convergence" answer.

## 5. Honest caveats

- Full-arity random trees have little *deep* sharing beyond what interning already captures;
  DAG/tree ≈ 0.5 is representative of these, but a workload with more shared structure would
  push the floor lower (better for CM) and one with less would push it toward 1.0.
- The "per-node overhead factor" is a *model-derived* quantity (assumes equal per-op arithmetic
  cost for both walks). It is a decomposition aid, not a directly-timed number; the timed,
  audited quantities are the ratios and node counts in §2.
- Large-n points use fewer trials (n=24: 7 exprs); the trend is monotonic and consistent with
  the node-count model, but n≥22 carries more variance than n≤20.
- This is all the *full-output* regime (guard disabled). It does not change the reduced-path
  story, and full-output at n>16 is bitset-territory work either way (§ audit doc §8.1).

## 6. Bottom line

Yes: CM No-Reinflate converges toward Bitset as n grows — measured **1.67× (n=16) → 1.31×
(n=24)**, monotonic. The structural floor is ~**0.5×** (CM's IR DAG has half the nodes), so
the headroom is real; it is currently masked by a ~3× per-node Python overhead that amortizes
only slowly with n. The **flat evaluator (Tier-C)** is the scoped improvement that would
realize that floor at practical n rather than at RAM-infeasible n≈30. I'd recommend
implementing C1a next and re-running this exact table as the before/after.
