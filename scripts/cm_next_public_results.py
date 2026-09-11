"""Export current scientific results without account inventories or transport receipts."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'docs/audits/2026-09-11-cm-next-research'


def export():
    v=json.loads((AUDIT/'VERIFICATION.json').read_text())
    assert v['final_regression'] is not None and not v['final_regression']['new_failures']
    assert set(v['isolated'])=={'attempt-012','attempt-013'}
    public=v['isolated']['attempt-012']['summaries']+v['isolated']['attempt-013']['summaries']
    assert len(public)==90 and len({(r['case'],r['mode'],r['method']) for r in public})==90
    synthetic=v['counts']['attempt-010']['summaries']
    assert len(synthetic)==100 and not v['counts']['attempt-010']['missing_rows']
    for row in public+synthetic:
        assert row['status'] in ('complete','refused','incomplete')
        if row['status']!='complete': assert 'cold_ms' not in row and 'warm_ms' not in row
    result=dict(schema='cm-next-public-results/v1',status='verified_with_explicit_limitations',measured_utc='2026-09-11',
        synthetic=synthetic,public=public,pipes=v['pipes']['attempt-008']['summary'],
        preparation=v['preparation']['attempt-008']['summary'],
        synthetic_scope='Linux CPU; latest same-machine replay of the declared development and confirmation cases; nine repetitions',
        synthetic_note='Count each selected-variable assignment once, including when auxiliaries have multiple witnesses. Full counts are a separate selectable contract. The natural-order native control is faster on the tested independent-auxiliary and adjacent-exclusion families; hidden-star projection is explicitly refused by all three bucket variants. No general native-performance advantage is established.',
        public_scope='Additional public systems; latest isolated-method diagnostic on consumed inputs; nine repetitions where complete',
        public_note='Whole DIMACS files and unchanged 32-request traces. Projection selects even-position declared variables; this is not claimed to reconstruct original feature-product semantics. Each measured method has its own process and 120-second limit. If the independent oracle times out, the methods are explicitly marked not measured. The earlier harness stopped a whole case when one competing native control failed; these diagnostic reruns preserve failed/refused methods and carry no paired comparative confidence claim.',
        pipe_scope='Linux CPU; producer plus separate OS-pipe reader; nine fresh-process repetitions',
        pipe_note='The reader checks every delivered byte. Slow-reader cases wait 0.5 ms after each up-to-4-KiB read. Cancellation is checked between chunks; a full-output chunk completes before it can stop. First-reader time is the return of the first read, not the arrival of its first byte. Memory is the sum of separate lifetime peak RSS measurements, an upper bound rather than simultaneous RSS. No durable-storage claim.',
        preparation_scope='Linux CPU; four structural inputs and 1/32/256 requests; nine repetitions',
        preparation_note='Fresh compilation starts with an existing expression. Checked reload includes file read, SHA-256 check, JSON validation and compilation. Resident-call timing excludes original construction; the second metric adds its separately recorded construction. Initial fsync storage costs are in the download. Reload did not beat fresh compilation; reuse requires a useful plan lifetime.',
        headlines=dict(pipe_rows=v['pipes']['attempt-008']['rows'],soak_queries=v['soaks']['attempt-008']['queries'],
            soak_seconds=v['soaks']['attempt-008']['seconds'],final_passed_tests=v['final_regression']['counts']['passed'],
            final_failed_or_error_tests=len(v['final_regression']['failures']),new_regressions=0),
        disposition='Projected counting and explicit repository task adapters are implemented and tested. Pipe consumption, cancellation, concurrent cache lifetimes and preparation reuse were measured. The full regression replay has no new failures against the published checkout, but historical/platform failures remain. Broader claims still need real consumer traces and independent workload diversity. These APIs remain explicit options; no automatic selector, failed native-batch candidate or compiled-plan persistence was promoted.',
        source_attempts=dict(synthetic='attempt-010',public=['attempt-012','attempt-013'],pipes='attempt-008',
                             preparation='attempt-008',regression='attempt-014'),
        cross_placement=dict(first='attempt-007',second='attempt-011',
             distinct_provider_machine_ids=v['attempts']['attempt-007']['machine_id']!=v['attempts']['attempt-011']['machine_id'],
             note='Original-harness replay on two provider machine IDs; virtualized placements and shared CPUs do not establish broad architecture generalization.'),
        corpus_selection=json.loads((AUDIT/'CORPUS.json').read_text()),
        regression_summary=v['final_regression']['counts'],
        regressions_remaining=v['final_regression']['failures'])
    (AUDIT/'PUBLIC-RESULTS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(synthetic_rows=len(synthetic),public_rows=len(public),pipe_rows=len(result['pipes']),preparation_rows=len(result['preparation']))))


if __name__=='__main__': export()
