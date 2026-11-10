# SPDX-License-Identifier: BSD-3-Clause
"""Tests for .github/scripts/check-site.py."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".github/scripts/check-site.py"
spec = importlib.util.spec_from_file_location("check_site", SCRIPT)
check_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_site)

CONFIG = "title: T\nlang: ja\nurl: https://example.github.io\nbaseurl: /Repo\n"
PAGE = """<!DOCTYPE html><html lang="ja"><head><title>T</title>
<meta name="viewport" content="width=device-width">
<link rel="stylesheet" href="/Repo/assets/main.css">
<script type="application/ld+json">{}</script></head>
<body><h1>T</h1>{body}</body></html>"""


class CheckSiteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs/_config.yml").write_text(CONFIG, encoding="utf-8")
        (self.root / "docs/index.md").write_text("---\n---\n[a](design.md)\n", encoding="utf-8")
        (self.root / "docs/design.md").write_text("---\n---\nx\n", encoding="utf-8")
        self.site = self.root / "_site"
        (self.site / "assets").mkdir(parents=True)
        (self.site / "design").mkdir()
        (self.site / "assets/main.css").write_text("", encoding="utf-8")
        self.write("index.html", '<a href="/Repo/design/">d</a>')
        self.write("design/index.html", '<a href="https://example.github.io/Repo/">top</a>')

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, name: str, body: str, page: str = PAGE) -> None:
        (self.site / name).write_text(page.replace("{body}", body), encoding="utf-8")

    def errors(self) -> list[str]:
        return check_site.source_errors(self.root) + check_site.site_errors(self.root, self.site)

    def test_accepts_valid_site(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_rejects_link_out_of_docs(self) -> None:
        (self.root / "docs/index.md").write_text("---\n---\n[r](../research/README.md)\n", encoding="utf-8")
        self.assertIn("leaves docs/", "\n".join(self.errors()))

    def test_rejects_non_site_file(self) -> None:
        (self.root / "docs" / "notes.txt").write_text("x", encoding="utf-8")
        self.assertIn("only site sources", "\n".join(self.errors()))

    def test_rejects_missing_front_matter(self) -> None:
        (self.root / "docs/design.md").write_text("x\n", encoding="utf-8")
        self.assertIn("front matter", "\n".join(self.errors()))

    def test_rejects_unbuilt_page(self) -> None:
        (self.root / "docs/status.md").write_text("---\n---\nx\n", encoding="utf-8")
        self.assertIn("not built", "\n".join(self.errors()))

    def test_rejects_broken_reference(self) -> None:
        self.write("index.html", '<a href="/Repo/missing/">m</a>')
        self.assertIn("broken reference", "\n".join(self.errors()))

    def test_rejects_absolute_broken_reference(self) -> None:
        self.write("index.html", '<a href="https://example.github.io/Repo/gone/">g</a>')
        self.assertIn("broken reference", "\n".join(self.errors()))

    def test_rejects_markdown_link(self) -> None:
        self.write("index.html", '<a href="/Repo/design.md">d</a>')
        self.assertIn("Markdown source", "\n".join(self.errors()))

    def test_rejects_external_script(self) -> None:
        self.write("index.html", '<script src="https://cdn.example/x.js"></script>')
        self.assertIn("JSON-LD", "\n".join(self.errors()))

    def test_rejects_http(self) -> None:
        self.write("index.html", '<a href="http://example.com/">x</a>')
        self.assertIn("insecure", "\n".join(self.errors()))

    def test_rejects_wrong_lang_and_headings(self) -> None:
        page = PAGE.replace('lang="ja"', 'lang="en"').replace("<h1>T</h1>", "")
        self.write("index.html", "", page)
        text = "\n".join(self.errors())
        self.assertIn("lang", text)
        self.assertIn("one <h1>", text)


if __name__ == "__main__":
    unittest.main()
