"""Read-only audit for the teacher-revised foundational CM scripts."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from itertools import combinations
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parent

SCRIPTS = {
    "operator": REPO / "docs/video_factory/deep_series/episodes/operator-cms-from-truth-tables/revision_v2/SCRIPT_V2.md",
    "lm": REPO / "docs/video_factory/deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v2/SCRIPT_V2.md",
    "layout": REPO / "docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v4/SCRIPT_V4.md",
}
SPECS = {
    "operator": SCRIPTS["operator"].with_name("VISUAL_AND_PRODUCTION_SPEC_V2.md"),
    "lm": SCRIPTS["lm"].with_name("VISUAL_AND_PRODUCTION_SPEC_V2.md"),
    "layout": SCRIPTS["layout"].with_name("VISUAL_AND_PRODUCTION_SPEC_V4.md"),
}


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:['-][a-z0-9]+)?", text.casefold())


def voiceover(text: str) -> str:
    return "\n".join(re.findall(r"\*\*Voiceover\*\*\s*(.*?)(?=\n\*\*Visual\*\*)", text, re.S))


def seconds(value: str) -> int:
    minute, second = value.split(":")
    return 60 * int(minute) + int(second)


def truth_value(a: int, b: int, c: int, d: int) -> int:
    return (a & b) ^ (c | d)


def main() -> int:
    checks: list[dict[str, object]] = []

    def check(identifier: str, condition: bool, detail: object) -> None:
        checks.append({"id": identifier, "passed": bool(condition), "detail": detail})

    all_files = [*SCRIPTS.values(), *SPECS.values(), PACKAGE / "TEACHER_SCRIPT_AND_VISUAL_AUDIT_V4.md"]
    for path in all_files:
        check(f"file-exists:{path.name}", path.is_file(), path.as_posix())

    script_text = {name: path.read_text(encoding="utf-8") for name, path in SCRIPTS.items()}
    spoken = {name: voiceover(text) for name, text in script_text.items()}
    expected_ranges = {"operator": (400, 500), "lm": (520, 620), "layout": (460, 560)}
    counts = {name: len(words(text)) for name, text in spoken.items()}
    for name, count in counts.items():
        low, high = expected_ranges[name]
        check(f"word-count:{name}", low <= count <= high, {"words": count, "range": [low, high]})

    forbidden_openings = {
        "operator": ("not sixteen", "sixteen what"),
        "lm": ("the last lesson", "but the paper"),
        "layout": ("one quick reminder", "same number, different objects"),
    }
    for name, text in script_text.items():
        first_voiceover = voiceover(text).split("\n\n", 1)[0].casefold()
        found = [phrase for phrase in forbidden_openings[name] if phrase in first_voiceover]
        check(f"positive-opening:{name}", not found, found)
        check(
            f"voiceover-visual-pairing:{name}",
            text.count("**Voiceover**") == text.count("**Visual**") >= 1,
            {"voiceover": text.count("**Voiceover**"), "visual": text.count("**Visual**")},
        )
        spans = [(seconds(a), seconds(b)) for a, b in re.findall(r"^## (\d+:\d+)–(\d+:\d+) —", text, re.M)]
        contiguous = all(end == next_start for (_, end), (next_start, _) in zip(spans, spans[1:]))
        check(f"timestamps:{name}", bool(spans) and spans[0][0] == 0 and contiguous and all(a < b for a, b in spans), spans)

    banned = (
        "sixteen answers",
        "only their addresses changed",
        "this episode has one job",
        "now isolate",
        "the invariant is",
        "0001111011100001",
    )
    for name, text in script_text.items():
        found = [phrase for phrase in banned if phrase in text.casefold()]
        check(f"mechanical-or-inaccurate-language:{name}", not found, found)

    sentence_sets = {
        name: {" ".join(words(sentence)) for sentence in re.split(r"(?<=[.!?])\s+", text) if len(words(sentence)) >= 8}
        for name, text in spoken.items()
    }
    overlaps = {
        f"{a}/{b}": sorted(sentence_sets[a] & sentence_sets[b])
        for a, b in combinations(sentence_sets, 2)
    }
    check("cross-episode-exact-sentence-overlap", all(not value for value in overlaps.values()), overlaps)

    def shingles(text: str, width: int = 12) -> set[tuple[str, ...]]:
        tokens = words(text)
        return {tuple(tokens[i : i + width]) for i in range(len(tokens) - width + 1)}

    long_overlaps = {
        f"{a}/{b}": [" ".join(item) for item in sorted(shingles(spoken[a]) & shingles(spoken[b]))]
        for a, b in combinations(spoken, 2)
    }
    check("cross-episode-12-word-overlap", all(not value for value in long_overlaps.values()), long_overlaps)

    state_order = [(1, 1), (1, 0), (0, 1), (0, 0)]
    actual_ops = {
        "and": [x & y for x, y in state_order],
        "or": [x | y for x, y in state_order],
        "xor": [x ^ y for x, y in state_order],
        "equivalence": [int(x == y) for x, y in state_order],
        "implication": [int((not x) or y) for x, y in state_order],
    }
    expected_ops = {
        "and": [1, 0, 0, 0], "or": [1, 1, 1, 0], "xor": [0, 1, 1, 0],
        "equivalence": [1, 0, 0, 1], "implication": [1, 0, 1, 1],
    }
    check("operator-semantics", actual_ops == expected_ops, actual_ops)
    check("operator-pattern-count", len({format(n, "04b") for n in range(16)}) == 16, 16)

    lm_material = script_text["lm"] + SPECS["lm"].read_text(encoding="utf-8")
    check("paper-4x4-result", all(row in lm_material for row in ("1100", "1110", "0011", "1011")), "exact rows present")
    check("paper-4x4-order", "(Y,W)" in lm_material and "(X,Z)" in lm_material, "rows (Y,W), columns (X,Z)")
    check("lm-causal-rail", "LM expressions → V_T → CM bits" in script_text["lm"], "present")

    flat = [truth_value(a, b, c, d) for a in (0, 1) for b in (0, 1) for c in (0, 1) for d in (0, 1)]
    vector = "".join(map(str, flat))
    check("repository-vector", vector == "0111011101111000", vector)
    tracked = {
        "AB/CD": ((2, 3), truth_value(1, 0, 1, 1)),
        "A/BCD": ((1, 3), truth_value(1, 0, 1, 1)),
        "ABC/D": ((5, 1), truth_value(1, 0, 1, 1)),
        "1110": ((3, 2), truth_value(1, 1, 1, 0)),
    }
    check("repository-coordinates", tracked == {"AB/CD": ((2, 3), 1), "A/BCD": ((1, 3), 1), "ABC/D": ((5, 1), 1), "1110": ((3, 2), 0)}, tracked)

    required_visual_terms = {
        "operator": ("full gallery is a result", "retrieval", "state-pair identity"),
        "lm": ("positive valuation", "worked 4×4 cell", "persistent rail"),
        "layout": ("invariant rail", "layout rail", "repartition"),
    }
    for name, path in SPECS.items():
        lower = path.read_text(encoding="utf-8").casefold()
        missing = [term for term in required_visual_terms[name] if term.casefold() not in lower]
        check(f"visual-explanation:{name}", not missing, missing)

    failed = [item for item in checks if not item["passed"]]
    result = {
        "schema_version": "1.0",
        "revision_id": "foundational-cm-v4-teacher-audit",
        "status": "pass" if not failed else "fail",
        "word_counts": counts,
        "check_count": len(checks),
        "passed_count": len(checks) - len(failed),
        "failed_count": len(failed),
        "failed_checks": failed,
        "checks": checks,
    }
    sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
