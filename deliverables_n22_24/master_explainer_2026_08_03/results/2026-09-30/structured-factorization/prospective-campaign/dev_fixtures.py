"""New fixed synthetic cases, unrelated to archived campaign records."""
import random


def table_cnf(n, truth):
    return [[-v if x & (1 << (v - 1)) else v for v in range(1, n + 1)]
            for x in range(1 << n) if not (truth >> x) & 1]


def planted(n, m, seed):
    rng = random.Random(seed)
    assignment = [rng.choice([False, True]) for _ in range(n)]
    clauses = []
    for _ in range(m):
        vs = rng.sample(range(1, n + 1), 3)
        clause = [v if rng.choice([False, True]) else -v for v in vs]
        if not any(assignment[abs(l) - 1] == (l > 0) for l in clause):
            clause[0] = -clause[0]
        clauses.append(clause)
    return clauses


def timing_cases():
    def case(name, n, clauses):
        return {'name': name, 'n': n, 'clauses': clauses}
    return [
        case('implication_chain_6', 6, [[-v, v + 1] for v in range(1, 6)]),
        case('independent_pairs_6', 6, [[1, 4], [-1, -4], [2, 5], [-2, -5], [3, 6], [-3, -6]]),
        case('interleaved_factors_8', 8, [[1, 3], [-3, 5], [5, 7], [2, 4], [-4, 6], [6, 8]]),
        case('parity_8', 8, table_cnf(8, sum(1 << x for x in range(256) if x.bit_count() % 2))),
        case('planted_3cnf_8', 8, planted(8, 24, 2026092911)),
        case('implication_chain_10', 10, [[-v, v + 1] for v in range(1, 10)]),
        case('planted_3cnf_10', 10, planted(10, 30, 2026092912)),
        case('planted_3cnf_12', 12, planted(12, 36, 2026092913)),
    ]


def factor_exposure_cases():
    """Factorable development controls whose redundant clauses obscure syntax.

    Each longer clause is implied by a shorter clause already present, so it
    changes the primal graph without changing the Boolean function. These are
    fixed correctness cases, never validation or held-out campaign inputs.
    """
    def case(name, clauses, carrier=None):
        return {'id': name, 'n': 6, 'clauses': clauses,
                'carrier': carrier or [[v] for v in range(1, 7)]}

    return [
        case('exposure_xor_pairs_n6',
             [[1, 2], [-1, -2], [4, 5], [-4, -5],
              [4, 5, 1], [-4, -5, 2], [-1, -2, 4],
              [-1, -2, 5], [-4, -5, 3]]),
        case('exposure_xor_equivalence_n6',
             [[1, 2], [-1, -2], [-4, 5], [4, -5],
              [1, 2, 4], [4, -5, 3], [4, -5, 1],
              [-1, -2, 5], [-4, 5, 2], [-4, 5, 1],
              [-4, 5, 3], [-1, -2, 4]],
             [[1, 4], [2], [3], [5], [6]]),
        case('exposure_xor_triple_n6',
             [[1, 2], [-1, -2], [4, 5, 6], [-4, -5], [-5, -6],
              [-5, -6, 2], [1, 2, 5], [1, 2, 6],
              [-4, -5, 1], [4, 5, 6, 3]]),
    ]
