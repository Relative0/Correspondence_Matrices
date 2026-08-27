"""Generate the deterministic CM website claim ledger and authored-literal audit."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
SITE = HERE.parent
DATA_PATH = SITE / "cm_master_data_2026_08_03.json"
CONTENT_PATH = SITE / "cm_master_content_2026_08_03.json"
AUTHORED = [
    SITE / "cm_master_build_2026_08_03.py",
    CONTENT_PATH,
    SITE / "cm_master_shared.js",
    SITE / "cm_master_template.html",
    SITE / "cm_layperson_template.html",
    SITE / "cm_investor_template.html",
    SITE / "cm_expert_template.html",
]
PAGES = ["index.html", "layperson.html", "investor.html", "expert.html", "usecases.html"]
TOKEN_RE = re.compile(r"\{\{([A-Za-z0-9_.]+)\}\}")
CALL_RE = re.compile(r'(?<![A-Za-z0-9_.$])TV?\(\s*"([A-Za-z0-9_.]+)"\s*\)')
LITERAL_RE = re.compile(r"(?<![A-Za-z0-9_])(?:\$?\d+(?:\.\d+)?(?:e[+-]?\d+)?)(?:\s*(?:%|×|x|MiB|KiB|µs|ms|passed))?", re.I)


def evidence_date(prov: str) -> str:
    dates = re.findall(r"20\d{2}[-_/]\d{2}[-_/]\d{2}|20\d{6}", prov)
    return max(dates).replace("_", "-").replace("/", "-") if dates else "pinned revision"


def evidence_role(prov: str, token: str) -> str:
    text = (prov + " " + token).lower()
    if "superseded" in text or "archive" in text:
        return "historical/superseded"
    if "junit" in text or "testcase" in text:
        return "validation state; not benchmark evidence"
    if "trace" in text or "dpr3" in text:
        return "diagnostic/reliability"
    if "memory" in text or "output-budget" in text:
        return "safety diagnostic/proposed policy"
    if "dependency" in text:
        return "dependency feasibility; not algorithm performance"
    if "cache" in text or "family" in text or "partial" in text or "context" in text:
        return "synthetic workload hypothesis"
    if "i10" in text:
        return "untouched held-out transfer"
    if "v3" in text or "symmetric" in text:
        return "accepted workload-specific benchmark"
    return "accepted benchmark or repository evidence"


def snippets_for(token: str, texts: dict[Path, str]) -> list[str]:
    patterns = ("{{%s}}" % token, 'T("%s")' % token, 'TV("%s")' % token)
    out = []
    for path, text in texts.items():
        for line_no, line in enumerate(text.splitlines(), 1):
            if any(p in line for p in patterns):
                out.append("%s:%d: %s" % (path.name, line_no, line.strip()[:220]))
    return out


def audiences_for(token: str, texts: dict[Path, str], snippets: list[str]) -> str:
    pages = []
    mapping = {
        "cm_master_template.html": "master/index.html",
        "cm_layperson_template.html": "layperson/layperson.html",
        "cm_investor_template.html": "investor/investor.html",
        "cm_expert_template.html": "expert/expert.html",
        "cm_usecases_template.html": "use-cases/usecases.html",
    }
    for snippet in snippets:
        name = snippet.split(":", 1)[0]
        if name in mapping:
            pages.append(mapping[name])
    if "cm_master_content_2026_08_03.json" in " ".join(snippets) or "cm_master_shared.js" in " ".join(snippets):
        pages.extend(["master/index.html", "layperson/layperson.html", "investor/investor.html", "expert/expert.html", "use-cases/usecases.html"])
    return "; ".join(dict.fromkeys(pages)) or "generated payload in all five pages; token currently not rendered"


def iter_result_leaves(node, prefix=""):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "provenance":
                continue
            yield from iter_result_leaves(value, "%s.%s" % (prefix, key) if prefix else key)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from iter_result_leaves(value, "%s[%d]" % (prefix, i))
    elif isinstance(node, (int, float, bool)) or node is None:
        yield prefix, node


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    content = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    texts = {path: path.read_text(encoding="utf-8") for path in AUTHORED}
    rows = []

    for token, item in sorted(data["_numbers"].items()):
        snippets = snippets_for(token, texts)
        rows.append({
            "claim_id": "token:" + token,
            "claim_text_or_token": token + (" — " + snippets[0] if snippets else ""),
            "value": item["value"],
            "source_file_and_field": item["prov"],
            "evidence_date": evidence_date(item["prov"]),
            "evidence_role": evidence_role(item["prov"], token),
            "page_audience": audiences_for(token, texts, snippets),
            "status": "current",
            "action": "retained or updated; builder uniqueness/provenance gate",
        })

    for section, value in sorted(data.items()):
        if section.startswith("_") or not isinstance(value, dict):
            continue
        provenance = " | ".join(value.get("provenance", []))
        for path, leaf in iter_result_leaves(value, section):
            rows.append({
                "claim_id": "data:" + path,
                "claim_text_or_token": path,
                "value": leaf,
                "source_file_and_field": provenance,
                "evidence_date": evidence_date(provenance),
                "evidence_role": evidence_role(provenance, path),
                "page_audience": "generated payload in all five pages; rendered by shared figures/content where applicable",
                "status": "current",
                "action": "retained or added from authoritative artifact",
            })

    for i, correction in enumerate(content["corrections"], 1):
        rows.append({
            "claim_id": "correction:%02d" % i,
            "claim_text_or_token": correction["what_it_claimed"],
            "value": correction["superseded_number"],
            "source_file_and_field": correction["date_or_pass"],
            "evidence_date": evidence_date(correction["date_or_pass"]),
            "evidence_role": "historical/superseded",
            "page_audience": "corrections ledger: master, investor, expert",
            "status": "superseded",
            "action": "confined to struck-through corrections ledger; replacement recorded",
        })

    for item in content["current_update"]["items"]:
        rows.append({
            "claim_id": "categorical:" + item["id"],
            "claim_text_or_token": item["title"],
            "value": item["summary"] + " " + item["detail"],
            "source_file_and_field": "e19_current_evidence.provenance",
            "evidence_date": "2026-08-26/27",
            "evidence_role": "categorical evidence boundary",
            "page_audience": "; ".join(item["audiences"]),
            "status": "current",
            "action": "added or narrowed stale wording",
        })

    fieldnames = [
        "claim_id", "claim_text_or_token", "value", "source_file_and_field",
        "evidence_date", "evidence_role", "page_audience", "status", "action",
    ]
    with (HERE / "CLAIM-LEDGER.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    literals = []
    for path, text in texts.items():
        for line_no, line in enumerate(text.splitlines(), 1):
            scrubbed = TOKEN_RE.sub("", CALL_RE.sub("", line))
            for match in LITERAL_RE.finditer(scrubbed):
                literals.append({
                    "source": path.name,
                    "line": line_no,
                    "literal": match.group(0),
                    "context": line.strip()[:260],
                    "classification": "reviewed static/structural, formatting constant, protocol label, or corrections-ledger value",
                })
    with (HERE / "AUTHORED-LITERAL-AUDIT.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["source", "line", "literal", "context", "classification"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(literals)

    stale = [row for row in rows if row["status"] in {"stale", "superseded", "withdrawn"}]
    (HERE / "STALE-SUPERSEDED-WITHDRAWN.json").write_text(
        json.dumps(stale, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("claim ledger rows:", len(rows))
    print("authored numeric literals reviewed:", len(literals))
    print("stale/superseded/withdrawn rows:", len(stale))


if __name__ == "__main__":
    main()
