"""Prospective, structurally disjoint inputs for a new integration gate.

Only CNFs and carriers are generated here. This module never computes or
supplies semantic prime partitions to the non-oracle worker.
"""
from __future__ import annotations

from itertools import combinations, product
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SIZES = {'validation': (8, 10, 12), 'heldout': (8, 10, 12, 14)}
FAMILIES = {
    'validation': ('component_paths', 'block_cut_triangles',
                   'window_at_most_one', 'nested_implications'),
    'heldout': ('xor_bridges', 'ring_equivalence',
                'overlap_at_most_two', 'nested_gates',
                'ladder_grid', 'threshold_bridge'),
}


def _xor_even(variables):
    out = []
    for values in product((False, True), repeat=len(variables)):
        if sum(values) % 2:
            out.append([-v if val else v for v, val in zip(variables, values)])
    return out


def _at_most(variables, k):
    return [[-v for v in sub] for sub in combinations(variables, k + 1)]


def _carrier(n, family):
    if family in {'block_cut_triangles', 'xor_bridges', 'nested_gates',
                  'threshold_bridge'}:
        used = set()
        blocks = []
        for a, b in ((1, n), (2, n - 1)):
            if a != b and a not in used and b not in used:
                blocks.append([a, b])
                used.update((a, b))
        blocks.extend([v] for v in range(1, n + 1) if v not in used)
        return blocks
    return [[v] for v in range(1, n + 1)]


def clauses_for(family, n):
    v = list(range(1, n + 1))
    if family == 'component_paths':
        return [[-v[i], v[i + 2]] for i in range(n - 2)]
    if family == 'block_cut_triangles':
        out = []
        for i in range(0, n - 2, 2):
            a, b, c = v[i:i + 3]
            out += [[-a, b], [-b, c], [-a, c]]
        return out
    if family == 'window_at_most_one':
        return [list(c) for c in sorted(set(tuple(c) for i in range(n - 3)
                                            for c in _at_most(v[i:i + 4], 1)))]
    if family == 'nested_implications':
        return [[-v[i], v[2 * i + 1]] for i in range(n)
                if 2 * i + 1 < n] + [
                [-v[i], v[2 * i + 2]] for i in range(n)
                if 2 * i + 2 < n]
    if family == 'xor_bridges':
        out = []
        for i in range(0, n - 2, 2):
            out.extend(_xor_even(v[i:i + 3]))
        return out
    if family == 'ring_equivalence':
        return [[-v[i], v[(i + 1) % n]] for i in range(n)] + [
            [v[i], -v[(i + 1) % n]] for i in range(n)]
    if family == 'overlap_at_most_two':
        return [list(c) for c in sorted(set(tuple(c) for i in range(n - 4)
                                            for c in _at_most(v[i:i + 5], 2)))]
    if family == 'nested_gates':
        out = []
        for z in range(3, n + 1):
            a, b = z - 2, max(1, z // 2)
            if z % 2:
                # z iff (a AND b)
                out += [[-a, -b, z], [a, -z], [b, -z]]
            else:
                # z iff (a OR b)
                out += [[a, b, -z], [-a, z], [-b, z]]
        return out
    if family == 'ladder_grid':
        half = n // 2
        out = [[-v[i], v[i + 1]] for i in range(half - 1)]
        out += [[-v[i], v[i + 1]] for i in range(half, n - 1)]
        out += [[-v[i], v[i + half]] for i in range(half)]
        return out
    if family == 'threshold_bridge':
        half = n // 2
        return (_at_most(v[:half], 1) + _at_most(v[half:], 2) +
                [[-v[i], v[half + i]] for i in range(half)])
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
    archived = ROOT.parent / 'phase5b_output' / 'data' / 'benchmark_manifest.json'
    old = json.loads(archived.read_text())['records']
    def key(record):
        return record['n'], tuple(sorted(tuple(sorted(c)) for c in record['clauses']))
    old_keys = {key(r) for r in old if r['split'] == 'heldout'}
    from dev_fixtures import timing_cases
    probe_keys = {key(r) for r in timing_cases()}
    current = {key(r) for r in manifest['records']}
    if len(current) != len(manifest['records']) or current & (old_keys | probe_keys):
        raise AssertionError('Duplicate new, archived held-out, or probe CNF')
    if any(not any(lit < 0 for lit in clause) for r in manifest['records']
           for clause in r['clauses']):
        raise AssertionError('All-zero satisfying assignment no longer holds')
    return len(old_keys), len(probe_keys)


if __name__ == '__main__':
    manifest = generate_manifest()
    old_count, probe_count = compare_archived(manifest)
    path = ROOT / 'candidate_manifest.json'
    path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'records': len(manifest['records']),
                      'old_heldout_compared': old_count,
                      'probe_compared': probe_count, 'path': str(path)}))
