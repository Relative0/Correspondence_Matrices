# Theory and priority audit

The following reconstruction uses the submitted Theory milestone, Draft 3 TeX, and primary sources searched afresh. Exact firstness is not established by a failed search. Let f be Boolean on n named coordinates, 0<=k<=n, and Q_k be the **indexed** integer counts for every partial assignment fixing at most k coordinates, including the empty assignment. Fourier statements extend to real/rational f. Matrix rank means GF(2) rank unless explicitly qualified.

## Complete Theory ledger

| Result | Precise surviving claim / independent reconstruction | Disposition |
|---|---|---|
| Q1 | Expand each literal indicator as (1+/-chi_i)/2. Thus Q(f;S,a)=2^(n-|S|) sum_(T subset S) (-1)^(a dot T) fhat(T); summing these counts with the same signs recovers fhat(T). | CORRECT BUT STANDARD |
| Q2 | Positive moments M_T=Q(T,1) form an integer query-row basis: include-exclude negative literals; each M_T is itself a query and square-free monomials are independent. The Walsh change is rational, not generally unimodular. | CORRECT BUT STANDARD |
| Q3 | The independent characters with |T|<=k form the query row span, hence rank=sum_(j=0)^k binom(n,j). | CORRECT BUT STANDARD |
| Q4 | Extend any smaller fixed set to k coordinates and sum over its completions. Exactly-k and at-most-k rows therefore have equal span for k<=n. | CORRECT BUT STANDARD |
| Q5 | Equal Q_k data iff the difference has zero low-degree Fourier coefficients. Boolean fibres are intersections with a discrete cube, not uniform real affine spaces. | CORRECT BUT STANDARD |
| Q6 | For k<n, multiply f-g by top parity to obtain nonzero degree <=n-k-1. A nonzero degree-d multilinear function has support >=2^(n-d), proving distance >=2^(k+1); opposite parity on a (k+1)-subcube attains equality. | CORRECT BUT STANDARD |
| Q7 | Cancel common support; equality of positive moments means equal incidence counts of all subsets of size <=k, precisely a simple [k]-trade. Trade volume is half the disagreement size. | CORRECT BUT STANDARD |
| Q8 | All Boolean functions have kappa=n: full assignments suffice; complementary global parity agrees at every smaller depth. | CORRECT BUT MINOR |
| Q9 | At-most-t juntas have Fourier degree <=t; Fourier inversion gives upper bound t, and t-bit parity gives lower bound t. Include t=0 constants. | CORRECT BUT MINOR |
| Q10 | Real Fourier degree <=d gives kappa=d for 0<=d<=n, by inversion and d-bit parity. | CORRECT BUT MINOR |
| Q11 | Degree-d PTF uniqueness follows because sum p(x)(f-g)(x)=0 by equal moments, while every nonzero summand is strictly positive after fixing a consistent strict threshold convention. Parity makes the bound sharp. | CORRECT BUT STANDARD |
| Q12 | ANF degree <=d has kappa=n for d>=1 because it contains global affine parity and its complement. For d=0, kappa=0. | CORRECT BUT MINOR |
| Q13 | Fixed nonempty cut p|q, full promised class rank<=1: row/column sum positivity recovers supports u,v of a nonzero rectangle uv^T at depth max(p,q). Parity on the larger side supplies the matching lower bound. Zero is identified by count zero. | CORRECT BUT MINOR; PRIORITY UNCERTAIN |
| Q14 | Complementary full parity matrices are sums of two separable terms and have rank two across a nonempty cut. They agree at depth n-1, proving kappa=n for every rank bound r>=2. | CORRECT BUT MINOR; PRIORITY UNCERTAIN |
| Q15 | If a real-linear map L on **all real functions** permits any decoder for Q_k, ker L is contained in ker Q_k. Therefore rank L >= sum binom(n,j). Moment coordinates attain it. | CORRECT BUT STANDARD |
| Q16 | Indistinguishability under **all** adaptive protocols with <=t distinct fixed coordinates in total equals Q_t equivalence. A single observed transcript does not reveal Q_t. A reset horizon after updates is a different, generally false claim. | CORRECT WITH REPAIR |
| Q17/T3 | A minimal coordinate-sensitive persistent representation with explicit construction/storage/update/query bounds and a predicted regime has not been supplied. | UNPROVED |

At n=k=0 there is one assignment and one count, not an empty sum of assignments. Bounds t,d must be capped by n. Empty matrix-side variable sets produce one row/column and cannot realize the nontrivial rank-two jump. Rank bound zero is a singleton class with threshold zero. These limits are mathematical domain requirements, not implementation failure cases.

### Priority and substantive value

Marginal/Fourier sufficiency appears explicitly in [Barak et al., Theorem 5 and equation (11)](https://cseweb.ucsd.edu/~kamalika/pubs/bcdkmt07.pdf). The low-degree coordinate count and transformations therefore provide background infrastructure. The minimum trade volume underlying Q6/Q7 is already recorded by [Ghorbani et al.](https://www.combinatorics.org/ojs/index.php/eljc/article/view/v27i1p29). PTF uniqueness is existing Chow theory, explicitly discussed by [Diakonikolas and Kane](https://arxiv.org/abs/1811.03491).

For Q13/Q14 the present bounded search did not find the exact threshold sentence. That is not firstness clearance. The proof uses elementary rectangle marginal recovery and complementary parity. Moreover the witnesses are also sums of two **disjoint** nonnegative rectangles, so the same mechanism applies to corresponding binary real/nonnegative/Boolean-OR rank classes. GF(2) terminology does not create a distinct difficult theorem. The contribution type is a concise synthesis/corollary.

## Persistent-state attacks

**Depth is not memory:** for the promised two-element class consisting of parity and its complement, one bit identifies the function and supports every query, although kappa=n. **Scalar dimension is not bits:** the scalar sum_i 2^i f_i injectively encodes every Boolean truth vector, at exponential bit precision. Q15 remains valid on its stated real domain; importing it as a Boolean bit lower bound is invalid.

**Horizon does not reset:** after s fixed coordinates, Q_k supplies residual depth k-s by unioning restrictions. Parity/complement on k+1 coordinates have the same original Q_k but different residual full-depth answers after one update. The independent oracle tests this through n=10. Contradictory or already-removed coordinates require explicit API semantics; the current residual API rejects removed names.

**Histograms are not coordinate maps:** xy and (1-x)y have matching global rank-state histograms but give different x=0 counts. A sufficient unordered statistic for one count cannot silently become a state for future named restrictions. Factor-basis changes act by invertible linear relabeling on state profiles; a proposed canonical/minimal storage bound must specify whether this gauge freedom is quotiented.

## Complete Draft 3 theorem audit

| Statement | Reconstruction, assumptions, and attack | Disposition |
|---|---|---|
| Family-wise conditioning (5.1) | Entrywise substitution on disjoint product/XOR blocks; Cartesian row/column selection on fixed-cut factors; restrict selectors/prototypes. Preserve free axes and empty residual assignment. | CORRECT BUT STANDARD |
| Retained structural monotonicity (5.2) | Submatrix rank and a retained factor list do not increase. This is not serialized-size monotonicity or monotonicity after fresh factor discovery. xyz XOR x XOR y loses z and splits into x XOR y. | CORRECT BUT MINOR |
| XOR/product/prototype counts (6.1) | XOR count=(product t_i - (-1)^c product(t_i-2o_i))/2; product count=product o_i; prototypes use selector multiplicities. All block scopes must be disjoint and all free-axis multiplicities counted. | CORRECT BUT STANDARD |
| Rank-profile identity (7.1) | Apply z=(1-(-1)^z)/2 to each GF(2) inner product and sum. Histograms for the **chosen restriction** suffice. Dense transform costs O(r2^r) arithmetic plus construction; integers need log(R'C'+1) bits. This is not a new T3 solution. | CORRECT BUT STANDARD / SYNTHESIS |
| Factor-only minimal recompression (7.2) | U=AB with A injective; factor BW=EF minimally, so UW=(AE)F and rank is preserved by A. Both factors must have full inner rank. O((R'+C')r^2) counts field operations. | CORRECT BUT STANDARD |
| Complement quotient (8.1) | Quotient row span W by its intersection with the all-ones line. If delta is that intersection's dimension, occurring prototype classes c obey r<=c+delta and 1<=c<=min(R,2^(r-delta)). Zero matrix fits. | CORRECT BUT MINOR; exact packaging PRIORITY UNCERTAIN |
| Inner-product dictionary gap (8.2) | At fixed x|y cut, rows are distinct characters; none are complementary because column zero is zero. GF(2) rank r; whole-row dictionary 2^(2r) bits versus 2r2^r factor bits. Orthogonal sign rows give real sign-matrix rank 2^r, not sign-rank. | CORRECT BUT MINOR |
| Global histogram insufficiency (9.1) | Explicit xy/(1-x)y counterexample above. Does not lower-bound every coordinate-aware encoding. | CORRECT BUT MINOR |
| All-query state bound (9.2) | Full assignments separate any two functions, so a fixed b-bit state has b>=ceil(log2|F|). Variable-length worst-case conventions must be separately declared. | CORRECT BUT STANDARD |
| Black-box verification bound (9.3) | A deterministic zero-error verifier accepting zero must inspect every point, otherwise an unseen single spike (rank one) gives the same transcript. Formula/certificate/aggregate access is outside this model. | CORRECT BUT STANDARD |

The inner-product example admits a small interleaved OBDD and a disjoint XOR of pairwise products. It therefore supplies neither an all-order OBDD separation nor a separation against an optimized decomposition portfolio. Ordinary tensor arithmetic and GF(2) factors must not be interchanged; [Onaka et al.](https://arxiv.org/html/2502.03702v1) is direct tensor/KC comparison prior art. [DeSantis et al.](https://arxiv.org/abs/2012.10496) supplies relevant distinctions among binary matrix ranks. General query/transform tradeoffs are established [knowledge-compilation comparison criteria](https://arxiv.org/abs/1106.1819).

## Computation alignment

The imported finite oracle directly tests Q1/Q3/Q4/Q5 and Q13/Q14 on its stated finite classes. The new adapter integration tests the actual MSB project factors against its LSB coordinate oracle, including all low-rank 4x4 restrictions, constants, unequal cuts and repeated residual operations. The original 38-case benchmark does not test a T3 prediction: its random restriction depths, representation selection and mixed costs answer a different empirical question. No finite enumeration establishes historical priority or asymptotic optimality.

**Next: SEND RESULTS/QUESTION TO THEORY.** Repair Q16 framing and freeze T3's state/access/bit/update contract before C2. None of the main correctness claims was refuted under the qualifications above, but no newly substantial theorem justifies a theory-first manuscript yet.
