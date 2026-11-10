#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Check the GitHub Pages sources in docs/ and, optionally, the built site."""

from __future__ import annotations

import argparse
import html.parser
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SUFFIXES = {".md", ".yml", ".svg", ".png", ".webp"}
SITE_SUFFIXES = {".html", ".css", ".svg", ".xml", ".png", ".webp", ".txt"}
MD_LINK = re.compile(r"\]\(([^)\s]+)")
CONFIG_KEY = re.compile(r"^(\w+):\s*(.*?)\s*$", re.M)


def config(root: Path) -> dict[str, str]:
    text = (root / "docs/_config.yml").read_text(encoding="utf-8")
    return {k: v.strip("\"'") for k, v in CONFIG_KEY.findall(text)}


def source_errors(root: Path) -> list[str]:
    errors = []
    docs = root / "docs"
    cfg = config(root)
    if cfg.get("lang") != "ja":
        errors.append("docs/_config.yml: lang must be ja")
    for path in sorted(p for p in docs.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if path.suffix not in SOURCE_SUFFIXES:
            errors.append(f"{rel}: only site sources belong in docs/")
            continue
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            errors.append(f"{rel}: missing front matter")
        for target in MD_LINK.findall(text):
            parts = urlsplit(target)
            if parts.scheme == "http":
                errors.append(f"{rel}: use https: {target}")
            if parts.scheme or not parts.path:
                continue
            resolved = (path.parent / unquote(parts.path)).resolve()
            if not resolved.is_relative_to(docs.resolve()):
                errors.append(f"{rel}: link leaves docs/; use a GitHub URL: {target}")
    return errors


class Page(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lang = ""
        self.h1 = 0
        self.title = ""
        self.viewport = False
        self.refs: list[str] = []
        self.scripts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "h1":
            self.h1 += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "meta" and a.get("name") == "viewport":
            self.viewport = True
        elif tag == "script":
            self.scripts.append(a.get("src") or a.get("type", ""))
        for key in ("href", "src"):
            if key in a:
                self.refs.append(a[key])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def site_errors(root: Path, site: Path) -> list[str]:
    errors = []
    cfg = config(root)
    origin = cfg.get("url", "").rstrip("/")
    base = cfg.get("baseurl", "").rstrip("/")
    for md in sorted((root / "docs").glob("*.md")):
        page = "index.html" if md.stem == "index" else f"{md.stem}/index.html"
        if not (site / page).is_file():
            errors.append(f"{md.relative_to(root).as_posix()}: not built as {page}")
    for path in sorted(p for p in site.rglob("*") if p.is_file()):
        rel = path.relative_to(site).as_posix()
        if path.suffix not in SITE_SUFFIXES:
            errors.append(f"{rel}: unexpected file in the built site")
        if path.suffix != ".html":
            continue
        page = Page()
        page.feed(path.read_text(encoding="utf-8"))
        if page.lang != "ja":
            errors.append(f"{rel}: <html lang> is {page.lang!r}, expected 'ja'")
        if page.h1 != 1:
            errors.append(f"{rel}: expected one <h1>, found {page.h1}")
        if not page.title.strip():
            errors.append(f"{rel}: empty <title>")
        if not page.viewport:
            errors.append(f"{rel}: missing viewport meta")
        for script in page.scripts:
            if script != "application/ld+json":
                errors.append(f"{rel}: only inline JSON-LD scripts are allowed: {script!r}")
        for ref in page.refs:
            parts = urlsplit(ref)
            if parts.scheme == "http":
                errors.append(f"{rel}: insecure reference {ref}")
            target = ref
            if origin and ref.startswith(origin + base + "/"):
                target = ref[len(origin):]
            elif parts.scheme or parts.netloc or not parts.path:
                continue
            target_path = urlsplit(target).path
            if target_path.endswith(".md"):
                errors.append(f"{rel}: link to Markdown source {ref}")
                continue
            if target_path.startswith("/"):
                if not target_path.startswith(base + "/"):
                    errors.append(f"{rel}: link outside {base}/: {ref}")
                    continue
                local = site / unquote(target_path[len(base) + 1:])
            else:
                local = (path.parent / unquote(target_path)).resolve()
            if local.is_dir() or target_path.endswith("/"):
                local = local / "index.html"
            if not local.is_file():
                errors.append(f"{rel}: broken reference {ref}")
    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--site", type=Path, help="Jekyll output directory to check")
    args = parser.parse_args(argv)
    errors = source_errors(args.root)
    if args.site:
        errors += site_errors(args.root, args.site)
    for error in errors:
        print(f"error: {error}")
    print(f"Summary: site={'built' if args.site else 'sources'} errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
