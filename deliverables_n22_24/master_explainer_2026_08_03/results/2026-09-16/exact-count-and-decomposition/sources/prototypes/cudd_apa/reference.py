"""Load the unchanged CM reference without importing unrelated CM backends."""
import importlib.util
from pathlib import Path

REFERENCE_PATH = Path(__file__).resolve().parents[2] / "cmbench/comparative/exact_cudd_count.py"
spec = importlib.util.spec_from_file_location("cm_exact_cudd_reference", REFERENCE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
exact_cudd_count = module.exact_cudd_count
