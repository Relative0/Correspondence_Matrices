# Measurement boundaries, corrections, and limits

## Preserved run history

- `ladder-smoke-001.json`: harness development smoke, excluded from conclusions.
- `ladder-run-001.json`: retained original run. Peer review found that functions
  imported into `bitset_engine` were not all patched by the phase tracer. Public
  kernel self time could be folded into wrapper time. Dense byte metadata also
  used the packed-byte formula. Whole-call samples were not profiled and output
  equality passed, but the entire run is excluded from final numeric synthesis.
- `ladder-run-002.json`: corrected aliases in both `cm_ir` and `bitset_engine`,
  corrected dense byte metadata, followed by the same declared cases. This is
  the primary ladder run. No earlier measured file was overwritten.
- `PLAN.md` is unchanged. Repair and retry of a harness defect is within its
  frozen bounds; the defect did not justify changing cases or production code.

## Precise ladder caller

The measured library session begins at `Session.run` and ends after complete
output byte conversion and byte equality against a precomputed independent TT
oracle. Cold q1 includes JSON parsing/DAG decoding, source/IR/program preparation,
binding and execution; imports, fixture/oracle creation, cache clearing and
`Session.__init__` are outside. The latter constructs the variable-name tuple.
Thus there is no measured core-ladder variable-name-construction share. The
task harness separately measures basis mapping. The ladder input is an in-memory
JSON string; physical file loading is not inside that boundary.

Warm/resident q64 retains a previously prepared Session and executes/delivers
the same full result 64 times, then reports total and per-call time. Preparation
is not hidden: cold q1 is separately reported. This is a controlled persistence
ablation, not an application cost forecast, query diversification experiment, or
evidence that recomputing an identical result is useful. No output memo is used.
Actual lifecycle/API boundaries in predecessors remain separate.

The equality guard is audit harness work common to the compared ladder arms,
not a required feature of the bare production evaluator. Public output-budget
guards remain charged in public arms. `output_budget=None` disables a byte
ceiling but still runs public budget accounting; output width is capped by the
diagnostic plan. Explicit flat/words flags affect only these calls and never
module defaults. Dense cells request a complete byte-per-row matrix and are
contract comparisons, not same-output packed attributions.

Process startup measurements execute the diagnostic import surface in a fresh
child and charge parent launch-to-delivery wall time. Their import span starts
inside the script, so interpreter initialization, some early import work,
transport and shutdown remain a joint residual. They are not the larger
`cm_bench`/Y02–Y05 import surface and are not attached as a fabricated per-task
constant. Child process CPU and parent wall are different clocks/scopes.

Session teardown, dropping retained roots, a complete GC cycle, OS delivery,
and final process exit are not in the library session timer. They remain
unresolved for these new cells. Historic cleanup/lifecycle fields supply
separately qualified evidence; they cannot fill these holes by addition.

## Profiling and phase uncertainty

All ladder uninstrumented samples finish before any phase/cProfile/tracemalloc
pass. Phase tracing preserves `diagnostics=None`, except the deliberately
different `public_cm_diag` arm. Nested spans are exclusive, with an explicit
uncovered/harness/probe remainder. Timers perturb Python dispatch substantially;
phase percentages describe that pass, not the uninstrumented call. Dilation is
reported per treatment. A profile's cumulative helper costs are overlapping.

Bigint allocation/refcount release occurs inside logical operations. Word
execution includes mask resolution, scratch allocation and ndarray-to-integer
conversion. Without line/native allocation instrumentation these are joint
spans. Key tuple construction versus rewriting, CSE interning versus lowering,
and bound-cache validation versus lookup also remain joint. Their subdivisions
are unknown; a missing separate timer never means zero cost.

Process CPU readings in tiny Windows samples are often zero and quantized.
The requested absolute CPU values are retained; per-helper CPU percentages are
not asserted to be resolved. `get_clock_info` nominal resolution is not the
empirically effective scheduling/accounting quantum. Wall percentages are the
usable phase measurements at this scale.

## Memory and structure

Tracemalloc reports current/net retained and peak traced memory, with the result,
Session and module caches alive. It does not report cumulative bytes allocated,
complete native RSS, allocator fragmentation or allocator arena retention. It
is a separate pass, never a timing multiplier used to correct wall samples.

CM shallow node-plus-dict bytes are a partial retained representation size,
not a deep graph total. Deterministic flat-program metrics are computed after
the memory snapshot; the `cm_recursive` and dense arms may get a flat program
only for structural accounting at that point. Those derived instructions and
bound-cache counts do not describe memory retained at the earlier snapshot.
`final_dense_materializations` counts final outputs; dense intermediate counts
remain null. Kernel allocations in packed arms are not dense materializations.

Only disclosed small structural cases and one fixed-expression output-width
ladder were run. Source size, support widths and mutation rates are correlated.
No fitted independent complexity exponent, population interval, routing change,
or machine-independent performance claim follows from these measurements.
All task/cell failures and capability gaps must remain visible in synthesis.

## Bounds actually enforced

Case/output caps and exclusive file creation are checked. Suite/cell elapsed
deadlines are checked cooperatively between bounded operations; these are not
an OS preemptive per-allocation memory limit. The task runner also supervises
its child. No OS memory ceiling is claimed. Actual suites finish far inside
the predeclared time/size bounds. No optional dependency was installed and no
network/cloud service was used for diagnostics.
