"""Independent SAT miter for a live SDD and original CNF.

The SDD DAG is encoded afresh after each move. No model count equality is used
as a substitute for functional equivalence.
"""
from pysat.solvers import Solver


def equivalent_to_cnf(n, clauses, root):
    next_var = n
    encoded = {}
    gates = []

    def new():
        nonlocal next_var
        next_var += 1
        return next_var

    true = new()
    gates.append([true])

    def visit(node):
        if node.is_true():
            return true
        if node.is_false():
            return -true
        if node.is_literal():
            return int(node.literal)
        if node.id in encoded:
            return encoded[node.id]
        terms = []
        for prime, sub in node.elements():
            a, b = visit(prime), visit(sub)
            term = new()
            gates.extend([[-term, a], [-term, b], [term, -a, -b]])
            terms.append(term)
        output = new()
        gates.extend([[-term, output] for term in terms])
        gates.append([-output] + terms)
        encoded[node.id] = output
        return output

    output = visit(root)
    with Solver(name='g4', bootstrap_with=gates) as solver:
        # Direction 1: a satisfying CNF assignment rejected by the SDD.
        for clause in clauses:
            solver.add_clause(clause)
        if solver.solve(assumptions=[-output]):
            return False
    # Direction 2: an SDD model falsifies at least one original clause.
    # Separate queries avoid constructing a second Tseitin encoding of the CNF.
    with Solver(name='g4', bootstrap_with=gates) as solver:
        for clause in clauses:
            if solver.solve(assumptions=[output] + [-lit for lit in clause]):
                return False
    return True
