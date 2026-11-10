#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Decide whether a workflow run touches any of the given path globs.

Globs follow GitHub's `paths` syntax for `*` (no slash) and `**` (any).
The result is written as `relevant=true|false` to $GITHUB_OUTPUT. Runs that
cannot be narrowed down (schedule, manual, new branches, very large diffs)
are always relevant.
"""

import argparse
import json
import os
import re
import sys
import urllib.request

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
ZERO_SHA = "0" * 40
# GitHub truncates the file lists of these endpoints.
PR_FILES_LIMIT = 3000
COMPARE_FILES_LIMIT = 300


def glob_regex(pattern: str) -> re.Pattern[str]:
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def matches(files: list[str], patterns: list[str]) -> list[str]:
    regexes = [glob_regex(p) for p in patterns]
    return [f for f in files if any(r.match(f) for r in regexes)]


def api_get(path: str) -> object:
    request = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def changed_files() -> list[str] | None:
    """Return the changed paths, or None if every path must be assumed."""
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    repo = os.environ["GITHUB_REPOSITORY"]
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        event = json.load(f)
    files: list[str] = []
    if event_name == "pull_request":
        number = event["pull_request"]["number"]
        page = 1
        while True:
            batch = api_get(f"/repos/{repo}/pulls/{number}/files?per_page=100&page={page}")
            files += [item["filename"] for item in batch]
            files += [item["previous_filename"] for item in batch if "previous_filename" in item]
            if len(batch) < 100:
                break
            page += 1
        return None if len(files) >= PR_FILES_LIMIT else files
    if event_name == "push":
        before, after = event.get("before", ZERO_SHA), event.get("after", ZERO_SHA)
        if before == ZERO_SHA or after == ZERO_SHA:
            return None
        data = api_get(f"/repos/{repo}/compare/{before}...{after}")
        items = data.get("files", [])
        if len(items) >= COMPARE_FILES_LIMIT:
            return None
        files = [item["filename"] for item in items]
        files += [item["previous_filename"] for item in items if "previous_filename" in item]
        return files
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patterns", nargs="+")
    parser.add_argument("--files-from", help="read changed paths from a file (for tests)")
    args = parser.parse_args()

    if args.files_from:
        with open(args.files_from, encoding="utf-8") as f:
            files: list[str] | None = [line.strip() for line in f if line.strip()]
    else:
        files = changed_files()

    if files is None:
        relevant, reason = True, "all paths assumed for this event"
    else:
        hits = matches(files, args.patterns)
        relevant = bool(hits)
        reason = f"{len(hits)} of {len(files)} changed paths match"
        for hit in hits[:20]:
            print(f"match: {hit}")
    print(f"relevant={str(relevant).lower()} ({reason})")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"relevant={str(relevant).lower()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
