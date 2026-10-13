"""Prepare, but never publish, the standalone neural GitHub Pages package.

Only the generated neural page and its explicit evidence links are exported.
No repository-wide copy, credential access, benchmark or external write occurs.
The destination must be new; existing packages are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables_n22_24/master_explainer_2026_08_03"
TARGET = "https://relative0.github.io/Correspondence_Matrices_Neural/"
MAIN = "https://relative0.github.io/Correspondence_Matrices/"


def evidence_paths(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from evidence_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from evidence_paths(child)
    elif isinstance(value, str) and value.startswith("../../"):
        yield value[6:]


def export(destination: Path, target_url: str = TARGET):
    if target_url not in (TARGET, MAIN + "neural/"):
        raise ValueError("Unexpected publication target")
    destination = destination.resolve()
    if destination.exists() or not destination.is_relative_to(ROOT / "build"):
        raise ValueError("Export requires a new directory under the workspace build directory")
    data = json.loads((SITE / "cm_master_data_2026_08_03.json").read_text(encoding="utf-8"))
    evidence = data["e22_learning_neural"]
    paths = set(evidence_paths(evidence))
    paths.update(item["path"] for item in evidence["identities"])
    # Preserve the result paired with the directly linked independent verifier.
    paths.add("docs/audits/2026-09-11-cm-continuation/native-run/RESULT.json")
    payloads = {}
    for relative in sorted(paths):
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT / "docs") or path.suffix not in {".md", ".json", ".jsonl"}:
            raise ValueError(f"Outside the explicit documentation allowlist: {relative}")
        payloads[relative] = path.read_bytes()
        if len(payloads[relative]) >= 100_000_000:
            raise ValueError(f"Evidence exceeds GitHub's per-file limit: {relative}")
    for identity in evidence["identities"]:
        digest = hashlib.sha256(payloads[identity["path"]].replace(b"\r\n", b"\n")).hexdigest()
        if digest != identity["sha256"]:
            raise ValueError(f"Evidence drift: {identity['path']}")
    page = (SITE / "learning-neural-evidence.html").read_text(encoding="utf-8")
    if any(marker in page for marker in ("/*__CM_DATA__*/", "/*__CM_CSS__*/", "/*__CM_LIB__*/")) or json.dumps(evidence["updated"]) not in page:
        raise ValueError("Regenerate the evidence-bound page before export")
    # Keep the generated architecture, replacing only link routing in this export.
    # Inline data has no runtime fetch; published evidence stays beside the page.
    marker = "function hostedEvidenceHref(href) {"
    if page.count(marker) != 1:
        raise ValueError("Unexpected shared link helper")
    page = page.replace(marker, marker + '\n  if (typeof href === "string" && href.startsWith("../../")) return "evidence/" + href.slice(6);')
    companions = ("index", "layperson", "investor", "expert", "usecases", "feature-model-evidence", "data-downloads", "latest-results")
    for name in companions:
        # Companion section links must leave the nested export too.
        pattern = r'(["\'])(' + re.escape(name) + r'\.html(?:[?#][^"\']*)?)\1'
        page = re.sub(pattern, lambda match: match[1]+MAIN+match[2]+match[1], page)
    if re.search(r"[A-Za-z]:\\\\|/Users/|/home/", page):
        raise ValueError("Machine-local path in generated page")
    destination.mkdir(parents=True)
    public = destination / "_site"
    public.mkdir()
    for name in ("index.html", "learning-neural-evidence.html"):
        (public / name).write_text(page, encoding="utf-8", newline="\n")
    (public / "og.png").write_bytes((SITE / "og.png").read_bytes())
    (public / ".nojekyll").write_text("", encoding="utf-8")
    manifest = {"schema": "cm-neural-static-export/v1", "target": target_url,
                "evidence_updated": evidence["updated"], "publication_status": "prepared_not_published",
                "scope": "Direct website evidence links only; not the complete transitive reproduction archive.",
                "files": {}}
    for relative, payload in payloads.items():
        target = public / "evidence" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    for path in sorted(public.rglob("*")):
        if path.is_file():
            payload = path.read_bytes()
            manifest["files"][path.relative_to(public).as_posix()] = {
                "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    (public / "publication-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    workflow = destination / ".github/workflows/publish-neural-site.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("""name: Publish neural results
on:
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
        with:
          enablement: true
      - uses: actions/upload-pages-artifact@v3
        with:
          path: _site
      - uses: actions/deploy-pages@v4
        id: deployment
""", encoding="utf-8", newline="\n")
    (destination / "README.md").write_text(
        f"# CM learning and neural results\n\nPrepared for {target_url}\n\n"
        "This package is not a publication receipt. The results are the home page. "
        "Companion knowledge-base navigation points to the existing main site. "
        "Direct neural-page source links are bundled under `_site/evidence`; links "
        "inside original reports can require the full research repository. "
        "Original evidence is copied byte-for-byte and indexed in publication-manifest.json.\n\n"
        "Publication requires an account permitted to create/manage "
        "`Relative0/Correspondence_Matrices_Neural`. Use a separate checkout, never "
        "stage this shared research tree wholesale. Copy this package into that "
        "repository, deliberately commit its files, push, configure GitHub Pages "
        "for GitHub Actions and dispatch `Publish neural results`. Verify the "
        "published home page, source links, date and manifest after deployment. "
        "The workflow does not deploy automatically on push.\n",
        encoding="utf-8", newline="\n")
    return {"destination": str(destination), "files": len(manifest["files"]),
            "bytes": sum(item["bytes"] for item in manifest["files"].values()), "target": target_url}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=(TARGET, MAIN + "neural/"), default=TARGET)
    arguments = parser.parse_args()
    print(json.dumps(export(arguments.output, arguments.target), indent=2))
