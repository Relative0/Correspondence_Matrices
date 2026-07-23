"""Print dd/cudd availability for the current interpreter."""
import importlib
import importlib.metadata
import platform
import sys

print("python", sys.version.replace("\n", " "))
print("platform", platform.platform())
try:
    print("dd_version", importlib.metadata.version("dd"))
except Exception as exc:  # pragma: no cover
    print("dd_version FAIL", repr(exc))
for name in ["dd", "dd.autoref", "dd.cudd"]:
    try:
        mod = importlib.import_module(name)
        print(name, "OK", getattr(mod, "__file__", mod))
    except Exception as exc:
        print(name, "FAIL", repr(exc))
