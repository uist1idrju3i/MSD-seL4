#!/usr/bin/env python3
"""Check the repository's skill inventory and Claude mirrors without dependencies."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re


def check(root: Path) -> list[str]:
    errors: list[str] = []
    agents = root / ".agents/skills"
    claude = root / ".claude/skills"
    if not agents.is_dir() or not claude.is_dir():
        return ["Both .agents/skills and .claude/skills must exist."]
    canonical = {entry.name: entry for entry in agents.iterdir()}
    mirrors = {entry.name: entry for entry in claude.iterdir()}
    if not canonical:
        errors.append("The skill inventory is empty.")
    for name in sorted(canonical.keys() | mirrors.keys()):
        if name not in canonical:
            errors.append(f"{name}: Claude mirror has no canonical skill.")
            continue
        skill = canonical[name]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            errors.append(f"{name}: invalid skill directory name.")
        try:
            resolved = skill.resolve(strict=True)
            boundary = (root / ("vendor" if skill.is_symlink() else ".agents/skills")).resolve()
            if not resolved.is_relative_to(boundary):
                errors.append(f"{name}: canonical skill escapes its allowed directory.")
                continue
            content = (resolved / "SKILL.md").read_text(encoding="utf-8")
        except (OSError, RuntimeError, UnicodeError) as exc:
            errors.append(f"{name}: cannot read SKILL.md: {exc}")
            continue
        lines = content.splitlines()
        if not lines or lines[0] != "---" or "---" not in lines[1:]:
            errors.append(f"{name}: missing YAML front matter.")
        else:
            header = lines[1:lines.index("---", 1)]
            names = [line.removeprefix("name:").strip().strip("\"'")
                     for line in header if line.startswith("name:")]
            descriptions = [line.removeprefix("description:").strip()
                            for line in header if line.startswith("description:")]
            if names != [name]:
                errors.append(f"{name}: front matter name must match the directory.")
            if len(descriptions) != 1 or not descriptions[0].strip("\"'"):
                errors.append(f"{name}: one nonempty description is required.")
        mirror = mirrors.get(name)
        expected = f"../../.agents/skills/{name}"
        if mirror is None or not mirror.is_symlink() or os.readlink(mirror) != expected:
            errors.append(f"{name}: Claude mirror must be a symlink to {expected}.")
        elif not (mirror / "SKILL.md").is_file():
            errors.append(f"{name}: Claude mirror does not resolve to SKILL.md.")
    try:
        agents_text = (root / "AGENTS.md").read_text(encoding="utf-8")
        registered = re.findall(r"^\| `([a-z0-9-]+)` \|", agents_text, re.MULTILINE)
        if sorted(registered) != sorted(canonical):
            errors.append("AGENTS.md skill table must list each canonical skill exactly once.")
        if (root / "CLAUDE.md").read_text(encoding="utf-8").strip() != "@AGENTS.md":
            errors.append("CLAUDE.md must reference AGENTS.md without duplicating instructions.")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Cannot read agent instructions: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    errors = check(args.root.resolve())
    for error in errors:
        print(f"error: {error}")
    print(f"Skill inventory: {len(errors)} error(s)")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
