"""Arbitrary-precision CUDD traversal for model-count research controls."""


def exact_cudd_count(manager, root):
    """Count over every declared manager variable without a floating result.

    Traversal is iterative and handles complemented edges explicitly. The caller
    must prevent concurrent mutation/reordering of the manager during traversal.
    Memory is linear in visited signed nodes; large BDDs need a separate guard.
    """
    width = len(manager.vars)
    zero, one = manager.false, manager.true
    counts = {zero: 0, one: 1}
    pending = [(root, False)]
    def level(node):
        return width if node == zero or node == one else node.level
    while pending:
        node, ready = pending.pop()
        if node in counts: continue
        if node.negated:
            positive = ~node
            if ready: counts[node] = (1 << (width-level(node))) - counts[positive]
            else: pending.extend(((node, True), (positive, False)))
        elif ready:
            low, high = node.low, node.high
            counts[node] = ((counts[low] << (level(low)-level(node)-1)) +
                            (counts[high] << (level(high)-level(node)-1)))
        else:
            pending.extend(((node, True), (node.low, False), (node.high, False)))
    return counts[root] << level(root)
