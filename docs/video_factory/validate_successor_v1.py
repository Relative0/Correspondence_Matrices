"""Local validation for the additive full-course successor source delta."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import html.parser
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "video_factory" / "deep_series" / "cm_full_course_successor_v1"
REVIEW = ROOT / "docs" / "video_factory" / "deep_series" / "cm_full_course_panel_review_v1"


def sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


class Parser(html.parser.HTMLParser):
    pass


def main() -> None:
    assert OUT.is_dir(), "Run cm_full_course_successor_v1.py first."
    deltas = json.loads((OUT / "CURRICULUM_SUCCESSOR_V1.json").read_text(encoding="utf-8"))
    required = {
        "04_symbolic_implication": {10}, "07_compound_rule": {8}, "10_transpose": {7},
        "15_lm_factors": {7}, "16_lm_measurement": {3,4}, "18_larger_operations": {7},
        "20_public_api": {1,4,5,6,7,9}, "21_packed_outputs": {5},
    }
    for lesson, expected in required.items():
        got = {state["scene_number"] for state in deltas[lesson]["scenes"]}
        assert got == expected, (lesson, expected, got)
    text = (OUT / "CHANGELOG.md").read_text(encoding="utf-8")
    implementation_text = text + (OUT / "CURRICULUM_SUCCESSOR_V1.json").read_text(encoding="utf-8") + (OUT / "visual_replacements" / "21_packed_outputs" / "scene_05.html").read_text(encoding="utf-8")
    for key in ("CMR-01", "CMR-02", "CMR-03", "CMR-04", "CMR-05", "CMR-06", "CMR-07", "CMR-08"):
        assert key in (OUT / "README.md").read_text(encoding="utf-8")
    assert "entrywise convention" in text
    assert "Three representative balanced partitions" in text
    assert "bitset_to_bool_array(packed, n_vars=4)" in implementation_text

    html_files = list((OUT / "visual_replacements").rglob("*.html"))
    assert len(html_files) == 19
    for path in html_files:
        parser = Parser()
        page = path.read_text(encoding="utf-8")
        parser.feed(page)
        assert "<!doctype html>" in page and 'class="takeaway"' in page

    before = json.loads((REVIEW / "evidence" / "production_hashes_before.json").read_text(encoding="utf-8"))
    mismatches = [p for p, prior in before.items() if not Path(p).is_file() or sha(Path(p)) != prior]
    assert not mismatches, mismatches[:3]
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(OUT / "examples" / "successor_course_examples.py")], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    print(json.dumps({"status":"pass", "delta_lessons":len(deltas), "visual_html":len(html_files), "frozen_hashes_verified":len(before), "example_output":result.stdout.strip()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
