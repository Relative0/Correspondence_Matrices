"""Small Valgrind workload; run with 0 and many calls to separate interpreter noise."""
import argparse
import gc
from dd import cudd

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--calls", type=int, default=20000)
args = parser.parse_args()
manager = cudd.BDD()
manager.configure(reordering=False)
manager.declare(*(f"x{i}" for i in range(64)))
root = manager.false
for i in range(64):
    root |= manager.var(f"x{i}")
complement = ~root
assert manager.count(root, 256) == ((1 << 64) - 1) << 192
assert manager.count(complement, 256) == 1 << 192
for _ in range(args.calls):
    assert manager.count(root, 256) == ((1 << 64) - 1) << 192
    assert manager.count(complement, 256) == 1 << 192
del root, complement, manager
gc.collect()
print(f"Completed {2 * args.calls} measured APA calls plus 2 warmups and destroyed the manager")
