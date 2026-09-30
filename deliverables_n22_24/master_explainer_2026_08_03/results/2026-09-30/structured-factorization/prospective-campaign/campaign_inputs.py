"""Prospective inputs for the unfrozen integration gate.

Product cases contain independent Boolean modules. Cross-module clauses
subsume existing clauses, obscuring syntax without changing the function.
No semantic partition or search outcome is computed here.
"""
from __future__ import annotations

from itertools import combinations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SIZES = {'validation': (8, 10, 12), 'heldout': (8, 10, 12, 14)}
FAMILIES = {
    'validation': ('equivalence_pair_weave', 'equivalence_cardinality_weave',
                   'split_implication_paths', 'prime_equivalence_ring'),
    'heldout': ('equivalence_ladder_bridge', 'cardinality_equivalence_bridge',
                'dual_cardinality_bridge', 'split_implication_dag',
                'prime_global_at_most_one', 'connected_nested_gates'),
}


def _equivalence(a, b):
    return [[-a, b], [a, -b]]


def _at_most_one(variables):
    return [[-a, -b] for a, b in combinations(variables, 2)]


def _padding_pairs(n):
    return [clause for a in range(7, n, 2)
            for clause in _equivalence(a, a + 1)]


def _redundant(base, extras):
    """Add only clauses implied by an existing clause in another module."""
    out = list(base)
    for index, literal in extras:
        clause = base[index] + [literal]
        if -literal in base[index]:
            raise ValueError('Tautological bridge')
        out.append(clause)
    return out


def _carrier(n, family):
    if family in {'equivalence_cardinality_weave',
                  'cardinality_equivalence_bridge', 'split_implication_dag',
                  'connected_nested_gates'}:
        used = {1, n, 2, n - 1}
        return [[1, n], [2, n - 1]] + [[v] for v in range(1, n + 1)
                                         if v not in used]
    return [[v] for v in range(1, n + 1)]


def clauses_for(family, n):
    if n < 8 or n % 2:
        raise ValueError('Prospective sizes must be even and at least eight')
    if family == 'equivalence_pair_weave':
        base = _equivalence(1, 2) + _equivalence(4, 5) + _padding_pairs(n)
        return _redundant(base, [(0, 4), (1, -4), (1, 6), (1, -6),
                                 (2, -1), (3, 2), (0, -5)])
    if family == 'equivalence_cardinality_weave':
        base = _equivalence(1, 2) + _at_most_one((4, 5, 6)) + _padding_pairs(n)
        return _redundant(base, [(0, 6), (1, -6), (2, -2), (3, -3),
                                 (4, -3), (0, -4), (1, 5)])
    if family == 'split_implication_paths':
        half = n // 2
        base = [[-a, a + 1] for a in range(1, half)] + [
            [-a, a + 1] for a in range(half + 1, n)]
        return _redundant(base, [(0, half + 1), (1, -(half + 2)),
                                 (half - 1, 1), (half, -2)])
    if family == 'prime_equivalence_ring':
        base = [clause for a in range(1, n + 1)
                for clause in _equivalence(a, 1 if a == n else a + 1)]
        return _redundant(base, [(0, -4), (1, -5)])
    if family == 'equivalence_ladder_bridge':
        base = _equivalence(1, 2) + _equivalence(4, 5) + _padding_pairs(n)
        return _redundant(base, [(0, -4), (0, 5), (1, 4), (1, -5),
                                 (2, -1), (2, 2), (3, 1), (3, -2),
                                 (0, 6), (2, -6)])
    if family == 'cardinality_equivalence_bridge':
        base = _at_most_one((1, 2, 3)) + _equivalence(4, 5) + _padding_pairs(n)
        return _redundant(base, [(0, -4), (0, 5), (1, 4), (2, -5),
                                 (3, -1), (4, 2), (3, -3), (4, 6)])
    if family == 'dual_cardinality_bridge':
        base = (_at_most_one((1, 2, 3)) + _at_most_one((4, 5, 6)) +
                _padding_pairs(n))
        return _redundant(base, [(0, -4), (1, -5), (2, -6),
                                 (3, -1), (4, -2), (5, -3),
                                 (0, 6), (4, 2)])
    if family == 'split_implication_dag':
        half = n // 2
        base = [[-a, a + 1] for a in range(1, half)] + [
            [-a, a + 1] for a in range(half + 1, n)]
        base += [[-a, a + 2] for a in range(1, half - 1)]
        base += [[-a, a + 2] for a in range(half + 1, n - 1)]
        return _redundant(base, [(0, -(half + 1)), (1, half + 2),
                                 (half - 1, -1), (half, 2),
                                 (len(base) - 1, -3)])
    if family == 'prime_global_at_most_one':
        return _at_most_one(range(1, n + 1))
    if family == 'connected_nested_gates':
        out = []
        for z in range(3, n + 1):
            a, b = z - 2, max(1, z // 2)
            if z % 2:
                out += [[-a, -b, z], [a, -z], [b, -z]]
            else:
                out += [[a, b, -z], [-a, z], [-b, z]]
        return _redundant(out, [(0, -n), (1, -n), (2, -n)])
    raise ValueError(family)


def generate_manifest():
    records = []
    for split in ('validation', 'heldout'):
        for family in FAMILIES[split]:
            for n in SIZES[split]:
                clauses = clauses_for(family, n)
                carrier = _carrier(n, family)
                fingerprint = hashlib.sha256(json.dumps(
                    {'n': n, 'clauses': clauses}, sort_keys=True,
                    separators=(',', ':')).encode()).hexdigest()
                records.append({'id': f'{split}_{family}_n{n}',
                                'split': split, 'family': family, 'n': n,
                                'clauses': clauses, 'carrier': carrier,
                                'cnf_sha256': fingerprint})
    return {'generator': 'campaign_inputs.py', 'records': records}


def compare_archived(manifest):
    def key(record):
        return record['n'], tuple(sorted(tuple(sorted(c)) for c in record['clauses']))

    archived = ROOT.parent / 'phase5b_output' / 'data' / 'benchmark_manifest.json'
    old = json.loads(archived.read_text())['records']
    old_keys = {key(r) for r in old if r['split'] == 'heldout'}
    earlier = ROOT.parent / 'live_integration_2026-09-30' / 'candidate_manifest.json'
    earlier_keys = {key(r) for r in json.loads(earlier.read_text())['records']}
    from dev_fixtures import factor_exposure_cases, timing_cases
    development_keys = {key(r) for r in timing_cases() + factor_exposure_cases()}
    current = {key(r) for r in manifest['records']}
    for record in manifest['records']:
        n, clauses = record['n'], record['clauses']
        if (not clauses or any(not clause or any(abs(lit) not in range(1, n + 1)
                                                for lit in clause)
                               for clause in clauses)):
            raise AssertionError('Malformed CNF')
        if (any(not block for block in record['carrier']) or
            sorted(v for block in record['carrier'] for v in block) != list(range(1, n + 1))):
            raise AssertionError('Malformed carrier partition')
        fingerprint = hashlib.sha256(json.dumps(
            {'n': n, 'clauses': clauses}, sort_keys=True,
            separators=(',', ':')).encode()).hexdigest()
        if fingerprint != record['cnf_sha256']:
            raise AssertionError('CNF fingerprint mismatch')
    if len(current) != len(manifest['records']):
        raise AssertionError('Duplicate prospective CNF')
    if current & (old_keys | earlier_keys | development_keys):
        raise AssertionError('Archived or developmental CNF reused')
    if any(not any(lit < 0 for lit in clause) for r in manifest['records']
           for clause in r['clauses']):
        raise AssertionError('All-zero satisfying assignment no longer holds')
    return {'phase5b_heldout': len(old_keys),
            'earlier_integration': len(earlier_keys),
            'development': len(development_keys)}


if __name__ == '__main__':
    manifest = generate_manifest()
    exclusions = compare_archived(manifest)
    path = ROOT / 'candidate_manifest.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'records': len(manifest['records']),
                      'exclusions': exclusions, 'path': str(path)}))
