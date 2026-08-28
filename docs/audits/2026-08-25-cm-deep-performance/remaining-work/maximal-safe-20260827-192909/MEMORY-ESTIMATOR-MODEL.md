# Memory-estimator model

## Production model

The formulas remain legacy-output-v1:

- dense_bool/truth_table_uint8: E=2^k output bytes; temporary estimate 2E;
- packed_bitset: P=ceil(2^k/8); temporary estimate P(s+k+2).

The production docstring no longer calls this conservative. Input validation now requires nonnegative integral counts/limits, accepts NumPy integer scalars, rejects bool/string/fractional/nonfinite values, and retains zero-slot clamping to one. Arithmetic capacity is k<=4096 and at most 4096 bits per input integer. These are finite arithmetic limits, not new operational memory profiles. None still disables numeric admission for supported counts. No actual material allocation near the arithmetic capacity was attempted.

## Diagnostic candidate — not integrated

Identifier: cm-memory-structure-v1-candidate. Define:

- E=2^k, P=ceil(E/8);
- I=sizeof(0)+sizeof_digit*ceil(E/bits_per_digit), using the executing CPython;
- H=16,384+512(s+edges+k)+32k(s+2), a provisional metadata/frame/view envelope;
- cold mask construction C=16E for k>10, otherwise (k+4)I;
- dense storage S=(s+6)E;
- bigint storage S=(slots+k+6)I+C;
- words storage S=(k+buffers+4)(max(8,P)+192)+(k+2)I+C;
- candidate peak=ceil(1.25*(H+S)).

Dense s full-width memo arrays deliberately overbound smaller support arrays; extra buffers allow ufunc temporaries and final copies. Bigints use limbs rather than assuming one byte per eight truth bits. Words account for simultaneous bigint masks, word views, plan scratch, constants, conversion bytes and returned int. Metadata envelopes and the 25% allowance are hypotheses, not proven universal bounds.

Models apply only to whole dense materialization or packed evaluation after compilation/feature extraction. They do not claim to estimate preparation, isolated conversion, JSON serialization, total process RSS or parallel workers. The raw data saves those other windows but marks them ineligible for model comparisons.

## Evidence and gate

local-smoke-final contains one k=6 mixed-chain input and one cold repetition for each representation. All three exact outputs passed; both models are compared against the measured matching window in raw.jsonl. The summary retains every under/overestimate and full overestimate distributions without pooling representations or schedules.

The August 28 Runpod smoke subsequently completed k=6,8 for mixed-chain and
alternating-tree, cold/warm, three repetitions, with 312 exact/ok window
rows. Of 72 eligible comparisons, legacy underestimated 66 (dense 24/24,
bigint 24/24, words 18/24); the candidate underestimated zero. No coefficients
changed. See [the bounded smoke result](runpod-authorized-20260827-213104/HTTP-EPHEMERAL-RESULT-20260828.md).

Representative calibration across the full support/family/context design,
accepted corpus replay and full regression remain NOT RUN. The smoke's
limited held-out-family/cold/warm coverage is not a completed gate. No
measured cgroup memory limit was available. Null/unmeasured evidence is
not a zero-failure result.

The candidate is NOT accepted for production. No coefficients were fitted or changed after the tiny smoke. Metadata bounds, cold allocator behavior and representation tails require independent evidence; the full regression gate is also unmet.

The runner records per-repetition rows, cold subprocesses/warm children, operation costs, current/lifetime OS memory, exact hashes, source snapshots, failures and timeouts. The local CLI and child gate admit only the default tiny smoke. Larger modes require a Runpod Linux environment. Source snapshots and output directories refuse overwrite.
