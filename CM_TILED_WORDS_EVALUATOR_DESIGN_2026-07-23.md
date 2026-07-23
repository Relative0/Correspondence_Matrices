# Tiled numpy-words evaluator design

Date: 2026-07-23
Status: Audit V3 design note; not implemented

## Objective

Evaluate a `FlatProgram` over a full `2^n` truth-table domain without allocating
`O(n * 2^n)` input masks or one monolithic output. The evaluator should use a fixed
power-of-two row block (initial target: `2^24` rows, 2 MiB per uint64 buffer), so peak
memory is `O((n + peak_live_buffers) * block_rows)` and independent of total output
width.

This removes the RAM wall, not the exponential work or output-size wall. A full n=40
answer still contains about 128 GiB of packed output and must be streamed to a caller
that explicitly accepts that cost.

## Proposed API

```python
def iter_cm_node_word_tiles(
    node: CMNode,
    vars_all: Sequence[str],
    *,
    fixed: Mapping[str, int] | None = None,
    block_rows: int = 1 << 24,
) -> Iterator[WordTile]: ...

def iter_expr_word_tiles(
    expr: Expr,
    vars_all: Sequence[str],
    *,
    fixed: Mapping[str, int] | None = None,
    block_rows: int = 1 << 24,
) -> Iterator[WordTile]: ...

@dataclass(frozen=True)
class WordTile:
    row_start: int
    row_count: int
    words: np.ndarray  # little-endian uint64, read-only until next iteration
```

CM and the raw-AST Bitset control must use the same tile engine, variable builder,
block size, output sink, cache policy, and timing boundary. A convenience function may
join tiles into one integer only when an explicit byte limit permits it.

## Row ordering and input columns

The existing packed convention is retained: bit `r` is truth-table row `r`, and
`x_v(r) = (r >> (n - 1 - v)) & 1`.

For each tile `[start, start + count)`, construct variable words directly from the
periodic zero/one pattern:

- half-period for variable `v`: `2^(n - 1 - v)` rows;
- period: twice the half-period;
- phase: `start mod period`;
- fill whole zero/one spans where possible, then handle the two boundary fragments.

This avoids allocating `np.arange(2^n)`. A simple vectorized row-index builder is an
acceptable reference implementation for small blocks; the span filler is the optimized
path. Fixed variables use shared all-zero/all-one tile arrays.

`block_rows` must be a multiple of 64 except for the final tile. Unused high bits in the
final uint64 word are masked to zero after evaluation.

## Program execution and memory

Reuse `_compute_word_plan` unchanged. Its safety property is tile-independent: an output
buffer is selected before the current operation's dying inputs are released, so it
cannot alias any current input. Allocate the scratch pool once at the configured block
width and reuse it for every tile.

Do not retain a global environment cache for all tile offsets; it would recreate an
`O(number_of_tiles)` memory leak. Within one iterator:

1. allocate one array per non-fixed variable, plus constant views;
2. refill those arrays in place for the next row interval;
3. execute all program steps into the fixed scratch pool;
4. copy or synchronously consume the root tile before scratch is reused.

The iterator contract must say whether `words` is stable. The safest initial contract is
to return a copy; a faster `write_tiles(sink)` API can pass a borrowed view to a
synchronous sink.

## Output sinks

Supported sinks should include:

- packed binary file, little-endian words;
- callback receiving `(row_start, row_count, words)`;
- incremental hash/checksum for verification;
- bounded in-memory collector for small total outputs.

CSV or JSON must never be used for the packed payload. Metadata records `n`,
`output_vars`, row ordering, block size, final valid-bit count, evaluator kind, and a
content hash.

## Correctness plan

1. For n=0–12, compare the concatenated tiled result exhaustively with
   `eval_expr_tt`, bigint flat, and monolithic words for every block size in
   `{64, 128, 1024}` plus non-dividing final tiles.
2. Fuzz fixed bindings, variable-order permutations, constants, root-load programs,
   repeated operands, variadic AND/OR/XOR, IMP, EQV, and scratch-width reuse.
3. For n=16–26, compare tile-by-tile against the monolithic words evaluator; packed
   equality is exhaustive over every output row.
4. For outputs beyond local monolithic capacity, compare independent scalar samples,
   per-tile hashes from CM and raw AST, and a final streaming digest.
5. Force one-row, one-word, and partial-final-word boundaries.

## Benchmark protocol

- at least five paired/interleaved trials after one warm tile;
- report first-tile setup, steady-state per-tile time, total stream time, and sink time
  separately;
- record peak RSS, block size, program ops, scratch-buffer count, n, retained variable
  count, and output bytes;
- compare CM and raw AST using the same sink and exclude neither side's input-column
  refill;
- disclose that total runtime and output bytes remain exponential.

## Implementation sequence

1. Extract `_eval_words`' operation loop into an internal function accepting resolved
   load arrays and a scratch pool.
2. Add the reference tile-column builder and exhaustive boundary tests.
3. Add CM/raw iterators with copied tiles.
4. Add the span-based in-place column filler and benchmark it against the reference.
5. Add synchronous file/hash sinks and large-n sampled-oracle verification.

No library default should change until the tiled path has exhaustive parity tests and a
recorded output-sink contract.
