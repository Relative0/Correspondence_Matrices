"""Read-only audit for the foundational CM v3 editorial package."""

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
    "operator": REPO
    / "docs/video_factory/deep_series/episodes/operator-cms-from-truth-tables/revision_v1/SCRIPT_V1.md",
    "lm": REPO
    / "docs/video_factory/deep_series/episodes/logical-matrices-to-higher-dimensional-cms/revision_v1/SCRIPT_V1.md",
    "layout": REPO
    / "docs/video_factory/deep_series/episodes/what-is-explicit-cm/revision_v3/SCRIPT_V3.md",
}

SPECS = {
    "operator": SCRIPTS["operator"].with_name("VISUAL_AND_PRODUCTION_SPEC_V1.md"),
    "lm": SCRIPTS["lm"].with_name("VISUAL_AND_PRODUCTION_SPEC_V1.md"),
    "layout": SCRIPTS["layout"].with_name("VISUAL_AND_PRODUCTION_SPEC_V3.md"),
}

JSON_DELTAS = [
    PACKAGE / "SOURCE_REGISTRY_DELTA_V3.json",
    PACKAGE / "CLAIM_REGISTRY_DELTA_V3.json",
    PACKAGE / "GLOSSARY_DELTA_V3.json",
    PACKAGE / "CONTENT_BIBLE_DELTA_V3.json",
    PACKAGE / "SERIES_ORDER_DELTA_V3.json",
]

BANNED_LEARNER_PHRASES = (
    "this episode has one job",
    "watch for the label",
    "now isolate",
    "matched before-and-after view",
    "holding that element fixed",
    "the invariant is",
    "the accompanying view makes this step concrete",
    "read that statement only within this scope",
    "the measurement boundary is",
    "the uncertainty field says",
    "the nearest confusing lesson",
    "only their addresses changed",
    "sixteen answers",
)


def sha256(path: Path) -> str:
    # Git may check text files out with CRLF on Windows. Hash their canonical
    # repository form so the audit remains stable across checkout platforms.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:['-][a-z0-9]+)?", text.casefold())


def voiceover(text: str) -> str:
    blocks = re.findall(
        r"\*\*Voiceover\*\*\s*(.*?)(?=\n\*\*Visual\*\*)", text, re.S
    )
    return "\n".join(blocks)


def timestamp_seconds(value: str) -> int:
    minutes, seconds = value.split(":")
    return int(minutes) * 60 + int(seconds)


def truth_value(a: int, b: int, c: int, d: int) -> int:
    return (a & b) ^ (c | d)


def main() -> int:
    checks: list[dict[str, object]] = []

    def check(check_id: str, condition: bool, detail: object) -> None:
        checks.append({"id": check_id, "passed": bool(condition), "detail": detail})

    for path in [*SCRIPTS.values(), *SPECS.values(), *JSON_DELTAS]:
        check(f"file-exists:{path.name}", path.is_file(), path.as_posix())

    parsed = {}
    for path in JSON_DELTAS:
        try:
            parsed[path.name] = json.loads(path.read_text(encoding="utf-8"))
            check(f"json-parse:{path.name}", True, "valid JSON")
        except Exception as exc:  # pragma: no cover - diagnostic path
            check(f"json-parse:{path.name}", False, str(exc))

    source_note = REPO / "docs/video_factory/sources/CM_PAPER_SOURCE_NOTE_2026_09_01.md"
    expected_source_note_hash = (
        parsed.get("SOURCE_REGISTRY_DELTA_V3.json", {})
        .get("proposed_sources", [{}])[0]
        .get("sha256")
    )
    check(
        "source-note-hash",
        source_note.is_file() and sha256(source_note) == expected_source_note_hash,
        {"expected": expected_source_note_hash, "actual": sha256(source_note)},
    )

    script_text = {name: path.read_text(encoding="utf-8") for name, path in SCRIPTS.items()}
    spoken = {name: voiceover(text) for name, text in script_text.items()}

    word_counts = {name: len(words(text)) for name, text in spoken.items()}
    expected_word_ranges = {
        "operator": (520, 620),
        "lm": (620, 730),
        "layout": (590, 690),
    }
    for name, count in word_counts.items():
        low, high = expected_word_ranges[name]
        check(f"word-count:{name}", low <= count <= high, {"words": count, "range": [low, high]})

    for name, text in script_text.items():
        lower = text.casefold()
        found = [phrase for phrase in BANNED_LEARNER_PHRASES if phrase in lower]
        check(f"banned-phrases:{name}", not found, found)
        check(f"bad-old-vector:{name}", "0001111011100001" not in text, "absent")
        check(
            f"voiceover-visual-pairing:{name}",
            text.count("**Voiceover**") == text.count("**Visual**") >= 1,
            {"voiceover": text.count("**Voiceover**"), "visual": text.count("**Visual**")},
        )

        ranges = re.findall(r"^## (\d+:\d+)–(\d+:\d+) —", text, re.M)
        seconds = [(timestamp_seconds(start), timestamp_seconds(end)) for start, end in ranges]
        contiguous = all(end == next_start for (_, end), (next_start, _) in zip(seconds, seconds[1:]))
        ordered = all(start < end for start, end in seconds)
        check(
            f"timestamps:{name}",
            bool(seconds) and seconds[0][0] == 0 and contiguous and ordered,
            seconds,
        )

    # Detect exact sentence reuse and long common spoken runs across the three lessons.
    sentence_sets = {
        name: {
            " ".join(words(sentence))
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if len(words(sentence)) >= 8
        }
        for name, text in spoken.items()
    }
    exact_sentence_overlap = {
        f"{left}/{right}": sorted(sentence_sets[left] & sentence_sets[right])
        for left, right in combinations(sentence_sets, 2)
    }
    check(
        "cross-episode-exact-sentence-overlap",
        all(not overlap for overlap in exact_sentence_overlap.values()),
        exact_sentence_overlap,
    )

    def shingles(text: str, width: int = 12) -> set[tuple[str, ...]]:
        tokens = words(text)
        return {tuple(tokens[index : index + width]) for index in range(len(tokens) - width + 1)}

    long_overlap = {
        f"{left}/{right}": [" ".join(item) for item in sorted(shingles(spoken[left]) & shingles(spoken[right]))]
        for left, right in combinations(spoken, 2)
    }
    check(
        "cross-episode-12-word-overlap",
        all(not overlap for overlap in long_overlap.values()),
        long_overlap,
    )

    # Standard Boolean semantics for the operator examples in paper state order: 11,10,01,00.
    state_order = [(1, 1), (1, 0), (0, 1), (0, 0)]
    operator_vectors = {
        "and": [x & y for x, y in state_order],
        "or": [x | y for x, y in state_order],
        "xor": [x ^ y for x, y in state_order],
        "equivalence": [int(x == y) for x, y in state_order],
        "implication": [int((not x) or y) for x, y in state_order],
    }
    expected_operators = {
        "and": [1, 0, 0, 0],
        "or": [1, 1, 1, 0],
        "xor": [0, 1, 1, 0],
        "equivalence": [1, 0, 0, 1],
        "implication": [1, 0, 1, 1],
    }
    check("operator-matrix-semantics", operator_vectors == expected_operators, operator_vectors)
    all_patterns = {tuple((mask >> shift) & 1 for shift in (3, 2, 1, 0)) for mask in range(16)}
    check("operator-pattern-count", len(all_patterns) == 16, len(all_patterns))

    # Repository example and coordinate contract.
    flat = [truth_value(a, b, c, d) for a in (0, 1) for b in (0, 1) for c in (0, 1) for d in (0, 1)]
    bit_string = "".join(str(bit) for bit in flat)
    rows = [bit_string[index : index + 4] for index in range(0, 16, 4)]
    check("repository-truth-vector", bit_string == "0111011101111000", bit_string)
    check("repository-matrix-rows", rows == ["0111", "0111", "0111", "1000"], rows)

    tracked = {
        "AB/CD": ((2, 3), truth_value(1, 0, 1, 1)),
        "A/BCD": ((1, 3), truth_value(1, 0, 1, 1)),
        "ABC/D": ((5, 1), truth_value(1, 0, 1, 1)),
        "1110": ((3, 2), truth_value(1, 1, 1, 0)),
        "1101": ((3, 1), truth_value(1, 1, 0, 1)),
    }
    check(
        "repository-coordinate-examples",
        tracked
        == {
            "AB/CD": ((2, 3), 1),
            "A/BCD": ((1, 3), 1),
            "ABC/D": ((5, 1), 1),
            "1110": ((3, 2), 0),
            "1101": ((3, 1), 0),
        },
        tracked,
    )

    paper_rows = ["1100", "1110", "0011", "1011"]
    lm_all = script_text["lm"] + "\n" + SPECS["lm"].read_text(encoding="utf-8")
    check("paper-4x4-result-present", all(row in lm_all for row in paper_rows), paper_rows)
    check(
        "paper-4x4-order-present",
        "(Y,W)" in lm_all and "(X,Z)" in lm_all,
        "left (Y,W), right (X,Z)",
    )

    required_visual_terms = {
        "operator": ("persistent", "state order", "retrieval"),
        "lm": ("positive valuation", "tensor", "retrieval"),
        "layout": ("invariant rail", "layout rail", "re-partition"),
    }
    for name, path in SPECS.items():
        text = path.read_text(encoding="utf-8").casefold()
        missing = [term for term in required_visual_terms[name] if term.casefold() not in text]
        check(f"visual-contract:{name}", not missing, {"missing": missing})

    bible_delta = parsed.get("CONTENT_BIBLE_DELTA_V3.json", {})
    series_delta = parsed.get("SERIES_ORDER_DELTA_V3.json", {})
    added_ids = [item.get("video_id") for item in bible_delta.get("episodes_to_add", [])]
    check(
        "bible-added-episode-ids",
        added_ids == ["operator-cms-from-truth-tables", "logical-matrices-to-higher-dimensional-cms"],
        added_ids,
    )
    check(
        "series-count-and-order",
        series_delta.get("proposed_episode_count") == 53
        and series_delta.get("proposed_boolean_foundations_order", [])[3:6]
        == [
            "operator-cms-from-truth-tables",
            "logical-matrices-to-higher-dimensional-cms",
            "what-is-explicit-cm",
        ],
        series_delta.get("proposed_boolean_foundations_order"),
    )

    failed = [item for item in checks if not item["passed"]]
    result = {
        "schema_version": "1.0",
        "status": "pass" if not failed else "fail",
        "revision_id": "foundational-cm-v3",
        "word_counts": word_counts,
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

