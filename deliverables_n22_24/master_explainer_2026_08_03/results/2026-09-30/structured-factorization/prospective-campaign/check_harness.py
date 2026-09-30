"""Fault-injection checks for saved-row guards, selection and worker failures.

No formal campaign input or worker is executed. All forged results are in
memory or a temporary directory.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

import bounded_trial
import campaign_runner as runner
from campaign_integrity import selection_values, validate_rows

CAP = bounded_trial.MEMORY_CAP_BYTES
TIMEOUT = bounded_trial.TIMEOUT_SECONDS
METHODS = runner.METHODS
REPS = runner.REPETITIONS
FREEZE_HASH = 'f' * 64


def sample_rows(split='validation'):
    instance = {'id': split + '_control_n2', 'split': split,
                'family': 'control', 'n': 2,
                'clauses': [[-1]], 'carrier': [[1], [2]]}
    bases = {'B2': 100, 'B3': 80, 'B4': 110,
             'F1': 120, 'F2': 115, 'L1': 105, 'L2': 90}
    rows = []
    for method in METHODS:
        for rep in REPS:
            total = bases[method] + rep
            rows.append({'status': 'ok', 'method': method, 'id': instance['id'],
                         'n': 2, 'satisfiable': True, 'split': split,
                         'family': 'control', 'rep': rep,
                         'freeze_sha256': FREEZE_HASH,
                         'cap_bytes': CAP, 'effective_cap_bytes': CAP,
                         'timeout_seconds': TIMEOUT, 'process_wall_ns': total + 100,
                         'peak_memory_bytes': 1000000,
                         'semantic_correct': True, 'carrier_correct': True,
                         'tree': [1, 2], 'direct_partition': [[1], [2]],
                         'trace': [], 'rounds': [],
                         'exact': {'semantic_partition': [[1], [2]],
                                   'partition': [[1], [2]], 'sat_calls': 0},
                         'timing_ns': {'total_ns': total,
                                       'search_stage_ns': 30,
                                       'exact_stage_ns': total - 30}})
    return instance, rows


def rejects(rows, instance):
    expected = [(r['id'], r['method'], r['rep']) for r in rows]
    try:
        validate_rows(rows, {instance['id']: instance}, 'validation', expected,
                      METHODS, REPS, CAP, TIMEOUT, FREEZE_HASH, complete=True)
    except ValueError:
        return True
    return False


def run():
    instance, clean = sample_rows()
    expected = [(r['id'], r['method'], r['rep']) for r in clean]
    assert validate_rows(clean, {instance['id']: instance}, 'validation',
                         expected, METHODS, REPS, CAP, TIMEOUT, FREEZE_HASH,
                         complete=True) == clean
    variants = {}
    for name in ('duplicate_repetition', 'missing_correctness', 'negative_time',
                 'wrong_cap', 'wrong_hash', 'unknown_status', 'missing_row',
                 'invalid_partition', 'reordered_rows'):
        data = deepcopy(clean)
        if name == 'duplicate_repetition':
            data[0]['rep'] = 1
        elif name == 'missing_correctness':
            data[0].pop('semantic_correct')
        elif name == 'negative_time':
            data[0]['timing_ns']['total_ns'] = -1
        elif name == 'wrong_cap':
            data[0]['effective_cap_bytes'] = CAP - 1
        elif name == 'wrong_hash':
            data[0]['freeze_sha256'] = '0' * 64
        elif name == 'unknown_status':
            data[0]['status'] = 'mystery'
        elif name == 'missing_row':
            data.pop()
        elif name == 'invalid_partition':
            data[0]['direct_partition'] = [[1], [1, 2]]
        else:
            data[0], data[1] = data[1], data[0]
        try:
            validate_rows(data, {instance['id']: instance}, 'validation',
                          expected, METHODS, REPS, CAP, TIMEOUT, FREEZE_HASH,
                          complete=True)
            variants[name] = False
        except ValueError:
            variants[name] = True
    assert all(variants.values()), variants

    estimates, baseline, challenger = selection_values(
        clean, [instance['id']], METHODS, REPS, runner.PAR2_NS)
    assert (baseline, challenger) == ('B3', 'L2')
    with tempfile.TemporaryDirectory(prefix='live-harness-check-') as directory:
        temp = Path(directory)
        (temp / 'campaign_freeze.json').write_text('{}')
        (temp / 'validation_results.jsonl').write_text('{}\n')
        choice = {'freeze_sha256': runner.digest(temp / 'campaign_freeze.json'),
                  'validation_results_sha256': runner.digest(temp / 'validation_results.jsonl'),
                  'baseline': baseline, 'challenger': challenger,
                  'validation_geometric_total_ns': estimates}
        (temp / 'baseline_selection.json').write_text(json.dumps(choice))
        with (patch.object(runner, 'ROOT', temp),
              patch.object(runner, 'FREEZE', temp / 'campaign_freeze.json'),
              patch.object(runner, 'complete_rows', return_value=clean)):
            assert runner.load_selection() == choice
            wrong = deepcopy(choice)
            wrong['baseline'] = 'B2'
            (temp / 'baseline_selection.json').write_text(json.dumps(wrong))
            try:
                runner.load_selection()
                raise AssertionError('Forged selection accepted')
            except RuntimeError as error:
                assert 'differs' in str(error)

        heldout, pairs = sample_rows('heldout')
        for row in pairs:
            row['selection_sha256'] = 's' * 64
        failed = next(row for row in pairs if row['method'] == 'F2' and row['rep'] == 0)
        failed['status'] = 'error'
        failed['semantic_correct'] = None
        failed['carrier_correct'] = None
        (temp / 'heldout_results.jsonl').write_text('{}\n')
        (temp / 'baseline_selection.json').write_text(json.dumps(choice))
        with (patch.object(runner, 'ROOT', temp),
              patch.object(runner, 'FREEZE', temp / 'campaign_freeze.json'),
              patch.object(runner, 'verify_freeze', return_value=None),
              patch.object(runner, 'load_selection', return_value=choice),
              patch.object(runner, 'complete_rows', return_value=pairs)):
            analyzed = runner.analyze()
        assert analyzed['mechanism_go'] is False
        assert analyzed['mechanism_parity']['L2']['incomplete_pairs'] == [(heldout['id'], 0)]

    # Exercise the actual runner sequence with synthetic rows and mocked
    # workers, including resume and the validation-before-heldout boundary.
    with tempfile.TemporaryDirectory(prefix='live-runner-check-') as directory:
        temp = Path(directory)
        (temp / 'campaign_freeze.json').write_text('{}')
        validation, _ = sample_rows('validation')
        heldout, _ = sample_rows('heldout')
        records = [validation, heldout]
        totals = {'B2': 100, 'B3': 80, 'B4': 110,
                  'F1': 120, 'F2': 115, 'L1': 105, 'L2': 90}
        searches = {'B2': 30, 'B3': 30, 'B4': 30,
                    'F1': 100, 'F2': 95, 'L1': 40, 'L2': 35}

        def fake_worker(method, item):
            total = totals[method]
            return {'status': 'ok', 'id': item['id'], 'method': method,
                    'n': 2, 'satisfiable': True, 'tree': [1, 2],
                    'direct_partition': [[1], [2]], 'trace': [], 'rounds': [],
                    'exact': {'semantic_partition': [[1], [2]],
                              'partition': [[1], [2]], 'sat_calls': 0},
                    'timing_ns': {'total_ns': total,
                                  'search_stage_ns': searches[method],
                                  'exact_stage_ns': total - searches[method]},
                    'peak_memory_bytes': 1000000,
                    'process_wall_ns': total + 100,
                    'cap_bytes': CAP, 'effective_cap_bytes': CAP,
                    'timeout_seconds': TIMEOUT}

        with (patch.object(runner, 'ROOT', temp),
              patch.object(runner, 'FREEZE', temp / 'campaign_freeze.json'),
              patch.object(runner, 'verify_freeze', return_value=None),
              patch.object(runner, 'load_manifest', return_value=records),
              patch.object(runner, 'run_bounded', side_effect=fake_worker),
              patch.object(runner, 'truth_for', return_value=([[1], [2]], [[1], [2]]))):
            runner.run_split('validation')
            locked = runner.select()
            assert (locked['baseline'], locked['challenger']) == ('B3', 'L2')
            runner.run_split('heldout')
            heldout_hash = runner.digest(temp / 'heldout_results.jsonl')
            runner.run_split('heldout')
            assert runner.digest(temp / 'heldout_results.jsonl') == heldout_hash
            formal = runner.analyze()
            assert formal['mechanism_go'] is True
            assert formal['algorithmic_go'] is False
            assert formal['mechanism_parity']['L2']['complete_pairs'] == 3
            raw = temp / 'heldout_results.jsonl'
            original = raw.read_bytes()
            saved_rows = [json.loads(line) for line in original.splitlines()]
            saved_rows[0]['exact']['semantic_partition'] = [[1, 2]]
            raw.write_text(''.join(json.dumps(row) + '\n' for row in saved_rows))
            try:
                runner.complete_rows('heldout')
                raise AssertionError('Forged semantic result accepted')
            except RuntimeError as error:
                assert 'independent truth' in str(error)
            raw.write_bytes(original)
            try:
                runner.run_split('validation')
                raise AssertionError('Validation restarted after held-out')
            except RuntimeError as error:
                assert 'may not run' in str(error)

    worker_instance = {'id': 'worker-control', 'n': 2}
    valid = json.dumps({'status': 'ok', 'method': 'L1', 'id': 'worker-control',
                        'n': 2, 'effective_cap_bytes': CAP})
    completed = lambda code, stdout='', stderr='': subprocess.CompletedProcess(
        [], code, stdout, stderr)
    observations = {}
    cases = {
        'success': completed(0, valid),
        'wrong_effective_cap': completed(0, valid.replace(str(CAP), str(CAP - 1))),
        'malformed_json': completed(0, 'not-json'),
        'memory_cap': completed(1, '', 'MemoryError'),
        'native_crash': completed(-11),
        'killed': completed(-9),
    }
    with patch.object(bounded_trial.sys, 'platform', 'linux'):
        for name, fake in cases.items():
            with patch.object(bounded_trial.subprocess, 'run', return_value=fake):
                observations[name] = bounded_trial.run_bounded('L1', worker_instance)['status']
        with patch.object(bounded_trial.subprocess, 'run',
                          side_effect=subprocess.TimeoutExpired([], TIMEOUT)):
            observations['timeout'] = bounded_trial.run_bounded('L1', worker_instance)['status']
    assert observations == {
        'success': 'ok', 'wrong_effective_cap': 'bad_output',
        'malformed_json': 'bad_output', 'memory_cap': 'memory_cap',
        'native_crash': 'native_crash', 'killed': 'killed', 'timeout': 'timeout'}
    result = {'status': 'PASS', 'faulty_rows_rejected': variants,
              'forged_selection_rejected': True,
              'incomplete_mechanism_rejected': True,
              'mocked_runner_sequence_and_resume': True,
              'forged_saved_semantics_rejected': True,
              'worker_failure_classification': observations,
              'formal_workers_executed': 0}
    (Path(__file__).resolve().parent / 'harness_checks.json').write_text(
        json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    run()
