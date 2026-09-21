"""Apply the local APA experiment to an unpacked dd 0.6.0 source release.

Never patches an installed environment. The original double method is retained
as count_double, solely to measure the old API on the same resident root.
"""
from pathlib import Path
import argparse
import difflib
import hashlib


SOURCE_SHA256 = "bffda64a915bf14a94695b6732cb5ed9b13dbd98598f7f4136a732745e2c5b58"
DECLARATIONS = """    # Arbitrary-precision model counting (local prototype).
    ctypedef stdint.uint32_t DdApaDigit
    ctypedef DdApaDigit *DdApaNumber
    DdApaNumber Cudd_ApaCountMinterm(
        const DdManager *dd, DdNode *f, int nvars, int *digits)
    void Cudd_FreeApaNumber(DdApaNumber number)
"""
COUNT = '''    def count(
            self,
            u:
                Function,
            nvars:
                _Cardinality |
                None=None
            ) -> _Cardinality:
        """Return the exact integer number of models of node `u`.

        If `nvars` is omitted, count over `support(u)`. Otherwise it must
        be an integer at least as large as the support, and may exceed
        the number of variables declared in this manager.
        """
        cdef DdApaNumber number = NULL
        cdef int digits = 0
        cdef int i
        cdef int width
        cdef object result = 0
        if u.manager != self.manager:
            raise ValueError(
                '`u.manager != self.manager`')
        n = len(self.support(u))
        if nvars is None:
            nvars = n
        else:
            nvars = _operator.index(nvars)
        if nvars < n:
            raise ValueError(nvars, n)
        # CUDD computes nvars + 1 in a signed C int.
        if nvars >= INT_MAX:
            raise OverflowError('nvars must be less than INT_MAX')
        width = nvars
        number = Cudd_ApaCountMinterm(
            self.manager, u.node, width, &digits)
        if number == NULL:
            raise MemoryError('CUDD APA model count failed')
        try:
            # CUDD stores the most significant digit first. Folding directly
            # avoids float rounding and Python's decimal-string digit limit.
            for i in range(digits):
                result = (result << (sizeof(DdApaDigit) * CHAR_BIT)) | number[i]
            return result
        finally:
            # This is CUDD-owned memory, not a Python allocator buffer.
            Cudd_FreeApaNumber(number)

'''


def patch(source: Path, patch_file: Path) -> None:
    path = source / "dd" / "cudd.pyx"
    original = path.read_text(encoding="utf-8")
    if hashlib.sha256(original.encode()).hexdigest() != SOURCE_SHA256:
        raise SystemExit("Expected pristine dd 0.6.0 cudd.pyx; refusing to overwrite")
    updated = original.replace("import logging\n", "import logging\nimport operator as _operator\n", 1)
    updated = updated.replace("from libc.stdio cimport", "from libc.limits cimport CHAR_BIT, INT_MAX\nfrom libc.stdio cimport", 1)
    updated = updated.replace("    double Cudd_CountMinterm(\n", DECLARATIONS + "    double Cudd_CountMinterm(\n", 1)
    updated = updated.replace("    def count(\n", COUNT + "    def count_double(\n", 1)
    patch_file.write_text("".join(difflib.unified_diff(
        original.splitlines(True), updated.splitlines(True),
        fromfile="a/dd/cudd.pyx", tofile="b/dd/cudd.pyx")), encoding="utf-8")
    path.write_text(updated, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--patch-file", type=Path, default=Path(__file__).with_name("dd-0.6.0-apa.patch"))
    args = parser.parse_args()
    patch(args.source, args.patch_file)
