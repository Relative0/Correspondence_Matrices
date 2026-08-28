"""Filesystem/HTML navigation checks; explicitly not browser interaction tests."""

import re
import unittest
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "deliverables_n22_24/master_explainer_2026_08_03"
PAGES = ("index.html", "layperson.html", "investor.html", "expert.html", "usecases.html", "feature-model-evidence.html")


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids = []
        self.links = []
        self.images = []
        self.headings = []
        self.language = None
        self.title = ""
        self.in_title = False
        self.text = path.read_text(encoding="utf-8")
        self.feed(self.text)
        # Most page markup is constructed by JavaScript. Inspect literal
        # source references without executing it; do not call this DOM QA.
        self.literal_links = re.findall(r'<a\b[^>]*\bhref=[\"\']([^\"\']+)[\"\']', self.text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag == "html":
            self.language = attrs.get("lang")
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "img":
            self.images.append(attrs)
        if tag == "h1":
            self.headings.append(attrs)
        if tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def local_link_issues(documents):
    issues = []
    checked = 0
    for document in documents:
        for href in set(document.links + document.literal_links):
            if "${" in href or "{{" in href:
                continue
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc:
                continue
            if not parsed.path:
                # JS-generated target IDs require browser verification.
                continue
            checked += 1
            target = (document.path.parent / unquote(parsed.path)).resolve() if parsed.path else document.path.resolve()
            if not target.is_relative_to(ROOT):
                issues.append(f"{document.path.name}: out-of-project link {href}")
                continue
            if not target.exists():
                issues.append(f"{document.path.name}: missing target {href}")
                continue
            # File existence is checked; dynamic fragment resolution is not.
    return checked, issues


class WebsiteNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = [Document(SITE / page) for page in PAGES]

    def test_literal_local_link_file_targets_exist(self):
        checked, issues = local_link_issues(self.documents)
        self.assertGreater(checked, 10)
        self.assertEqual(issues, [])

    def test_no_duplicate_ids_in_static_html_shells(self):
        for doc in self.documents:
            with self.subTest(page=doc.path.name):
                self.assertEqual([key for key, count in Counter(doc.ids).items() if count > 1], [])

    def test_each_page_has_title_language_and_application_shell(self):
        for doc in self.documents:
            with self.subTest(page=doc.path.name):
                self.assertTrue(doc.title.strip())
                self.assertEqual(doc.language, "en")
                self.assertEqual(doc.ids.count("app"), 1)

    def test_images_declare_alternative_text(self):
        for doc in self.documents:
            for attrs in doc.images:
                with self.subTest(page=doc.path.name, image=attrs.get("src")):
                    self.assertIn("alt", attrs)

    def test_shared_navigation_declares_all_six_entry_pages(self):
        for doc in self.documents:
            with self.subTest(page=doc.path.name):
                for page in PAGES:
                    if page != doc.path.name:
                        self.assertTrue('"' + page + '"' in doc.text, f"missing declared route: {doc.path.name} -> {page}")

    def test_no_template_placeholders_or_absolute_machine_links(self):
        for doc in self.documents:
            with self.subTest(page=doc.path.name):
                for token in ("/*__CM_CSS__*/", "/*__CM_LIB__*/", "/*__CM_DATA__*/"):
                    self.assertNotIn(token, doc.text)
                self.assertFalse(any(href.lower().startswith(("file:", "c:/", "c:\\")) for href in doc.links))


if __name__ == "__main__":
    unittest.main()
