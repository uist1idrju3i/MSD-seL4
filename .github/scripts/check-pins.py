#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Check duplicated pins offline and compare pins with their upstreams."""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ElementTree
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
RUST_SMOKE_TOOLCHAIN = "projects/rust-smoke/rust-toolchain.toml"
DOCKERFILE = "docker/msd-sel4-dev.Dockerfile"
DEPENDENCIES = "research/vendor/dependencies.md"
SNAPSHOT_MAX_AGE_DAYS = 30
# Submodules whose commit is defined by the seL4 release manifest.
MANIFEST_PROJECTS = {
    "vendor/seL4": "seL4.git",
    "vendor/seL4_tools": "seL4_tools.git",
    "vendor/sel4runtime": "sel4runtime.git",
    "vendor/musllibc": "musllibc.git",
    "vendor/util_libs": "util_libs.git",
}

USES = re.compile(r"^\s*-?\s*uses:\s*([^\s@#]+)@([^\s#]+)\s*(?:#\s*(\S+))?", re.M)
IMAGE_PIN = re.compile(r"[\w./-]+:[\w.-]+@(sha256:[0-9a-f]+)")
RUNS_ON = re.compile(r"^\s*runs-on:\s*([^\s#]+)", re.M)
VERSION = re.compile(r"v?(\d+(?:\.\d+)+)")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL, timeout=60
    ).strip()


def version_key(version: str) -> tuple[int, ...]:
    match = VERSION.fullmatch(version)
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def submodules(root: Path) -> dict[str, dict[str, str]]:
    parser = configparser.ConfigParser()
    parser.read(root / ".gitmodules")
    result: dict[str, dict[str, str]] = {}
    for section in parser.sections():
        values = dict(parser[section])
        if "path" in values:
            result[values["path"]] = values
    return result


def gitlinks(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in git(root, "ls-files", "--stage", "--", "vendor").splitlines():
        mode, sha, _stage, path = line.split(maxsplit=3)
        if mode == "160000":
            result[path] = sha
    return result


def workflow_texts(root: Path) -> dict[str, str]:
    paths = sorted((root / ".github/workflows").glob("*.yml"))
    paths += sorted((root / ".github/actions").glob("*/action.yml"))
    return {str(path.relative_to(root)): path.read_text() for path in paths}


def dockerfile_value(text: str, name: str) -> str:
    match = re.search(rf"^ARG {name}=(\S+)$", text, re.M)
    return match.group(1) if match else ""


def dockerfile_base(text: str) -> tuple[str, str]:
    match = re.search(r"^FROM ([\w./-]+:[\w.-]+)@(sha256:[0-9a-f]{64})\s*$", text, re.M)
    return (match.group(1), match.group(2)) if match else ("", "")


def consistency(root: Path) -> list[str]:
    errors: list[str] = []
    workflows = workflow_texts(root)

    action_pins: dict[str, set[tuple[str, str]]] = {}
    for path, text in workflows.items():
        for action, ref, comment in USES.findall(text):
            if action.startswith("./"):
                continue
            if not re.fullmatch(r"[0-9a-f]{40}", ref):
                errors.append(f"{path}: {action}@{ref} is not pinned to a full commit SHA")
            if not VERSION.fullmatch(comment or ""):
                errors.append(f"{path}: {action}@{ref} needs a '# vX.Y.Z' comment")
            repository = "/".join(action.split("/")[:2])
            action_pins.setdefault(repository, set()).add((ref, comment))
        for digest in IMAGE_PIN.findall(text):
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                errors.append(f"{path}: image digest {digest} is not a full SHA-256")
        for name, value in re.findall(r"^\s*(\w+_DIGEST):\s*\"?([^\s\"]+)", text, re.M):
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
                errors.append(f"{path}: {name} is not a full SHA-256 digest")
    for repository, pins in sorted(action_pins.items()):
        if len(pins) > 1:
            listed = ", ".join(f"{ref[:12]} {comment}" for ref, comment in sorted(pins))
            errors.append(f"{repository} is pinned to different revisions: {listed}")

    labels = {label for text in workflows.values() for label in RUNS_ON.findall(text)}
    if len(labels) > 1:
        errors.append(f"workflows use different runner labels: {', '.join(sorted(labels))}")

    dockerfile = (root / DOCKERFILE).read_text()
    base, _digest = dockerfile_base(dockerfile)
    if not base:
        errors.append(f"{DOCKERFILE}: FROM must pin a tag and a full sha256 digest")
    if not re.fullmatch(r"\d{8}T\d{6}Z", dockerfile_value(dockerfile, "DEBIAN_SNAPSHOT")):
        errors.append(f"{DOCKERFILE}: DEBIAN_SNAPSHOT must look like 20260101T000000Z")
    nightly = dockerfile_value(dockerfile, "RUST_SEL4_NIGHTLY")
    if not re.fullmatch(r"nightly-\d{4}-\d{2}-\d{2}", nightly):
        errors.append(f"{DOCKERFILE}: RUST_SEL4_NIGHTLY must be a dated nightly")
    toolchain = root / RUST_SMOKE_TOOLCHAIN
    if toolchain.exists():
        channel = tomllib.loads(toolchain.read_text()).get("toolchain", {}).get("channel", "")
        if channel != nightly:
            errors.append(f"{RUST_SMOKE_TOOLCHAIN}: channel {channel} must equal RUST_SEL4_NIGHTLY {nightly}")

    modules = submodules(root)
    links = gitlinks(root)
    dependencies = (root / DEPENDENCIES).read_text()
    for path, values in sorted(modules.items()):
        if values.get("shallow") != "true":
            errors.append(f".gitmodules: {path} must set shallow = true")
        sha = links.get(path)
        if not sha:
            errors.append(f".gitmodules: {path} has no gitlink in the index")
        elif sha not in dependencies:
            errors.append(f"{DEPENDENCIES}: record the full commit {sha} of {path}")
    for path in sorted(set(links) - set(modules)):
        errors.append(f"{path}: gitlink is missing from .gitmodules")
    return errors


def fetch(url: str, accept: str = "application/vnd.github+json") -> str:
    request = Request(url, headers={"Accept": accept, "User-Agent": "msd-sel4-check-pins"})
    origin = urlsplit(url)
    token = os.environ.get("GITHUB_TOKEN")
    if token and origin.scheme == "https" and origin.hostname == "api.github.com":
        request.add_unredirected_header("Authorization", f"Bearer {token}")
    with urlopen(request, timeout=30) as response:
        return response.read().decode()


def parse_manifest(text: str) -> dict[str, str]:
    tree = ElementTree.fromstring(text)
    return {
        project.get("name", ""): project.get("revision", "")
        for project in tree.iter("project")
    }


def parse_peeled_tags(text: str) -> dict[str, str]:
    """Map commit SHA to tag name from `git ls-remote --tags` output."""
    plain: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for line in text.splitlines():
        sha, _, ref = line.partition("\t")
        if not ref.startswith("refs/tags/"):
            continue
        name = ref.removeprefix("refs/tags/")
        if name.endswith("^{}"):
            peeled[name[:-3]] = sha
        else:
            plain[name] = sha
    commits = {**plain, **peeled}
    return {sha: name for name, sha in commits.items()}


def parse_heads(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.startswith("refs/heads/"):
            result[ref.removeprefix("refs/heads/")] = sha
    return result


def rust_sel4_version(root: Path) -> str:
    """Return the release recorded next to the rust-sel4 rev in Cargo.toml."""
    path = root / "projects/rust-smoke/Cargo.toml"
    if not path.exists():
        return ""
    match = re.search(r'rust-sel4".*rev = "[0-9a-f]{40}".*#\s*(v[0-9.]+)', path.read_text())
    return match.group(1) if match else ""


def snapshot_status(snapshot: str, today: date) -> str:
    match = re.fullmatch(r"(\d{8})T\d{6}Z", snapshot)
    if not match:
        return "確認失敗"
    age = (today - datetime.strptime(match.group(1), "%Y%m%d").date()).days
    return "更新あり" if age > SNAPSHOT_MAX_AGE_DAYS else "最新"


def latest_release(repository: str) -> str:
    data = json.loads(fetch(f"https://api.github.com/repos/{repository}/releases/latest"))
    return str(data.get("tag_name") or "")


def ls_remote(url: str, *patterns: str) -> str:
    return subprocess.check_output(
        ["git", "ls-remote", url, *patterns], text=True, timeout=60
    )


def manifest_revisions(tag: str) -> dict[str, str]:
    return parse_manifest(fetch(
        f"https://raw.githubusercontent.com/seL4/sel4test-manifest/{tag}/default.xml",
        accept="application/xml",
    ))


def sel4_tag(root: Path, links: dict[str, str]) -> str:
    url = submodules(root)["vendor/seL4"]["url"]
    return parse_peeled_tags(ls_remote(url, "refs/tags/*")).get(links["vendor/seL4"], "")


def manifest(root: Path) -> list[str]:
    """Check that manifest-defined submodules match the seL4 release manifest."""
    links = gitlinks(root)
    tag = sel4_tag(root, links)
    if not tag:
        return [f"vendor/seL4 {links['vendor/seL4'][:12]} is not a seL4 release tag"]
    revisions = manifest_revisions(tag)
    errors = []
    for path, project in MANIFEST_PROJECTS.items():
        expected = revisions.get(project, "")
        if links.get(path) != expected:
            errors.append(
                f"{path} is {links.get(path, 'missing')[:12]}, but "
                f"sel4test-manifest {tag} pins {project} at {expected[:12] or 'nothing'}"
            )
    return errors


def workflow_env(root: Path, name: str) -> str:
    for text in workflow_texts(root).values():
        match = re.search(rf"^\s*{name}:\s*\"?([^\s\"]+)", text, re.M)
        if match:
            return match.group(1)
    return ""


def image_tag_version(root: Path, image: str) -> str:
    for text in workflow_texts(root).values():
        match = re.search(rf"{re.escape(image)}:v?(\d+(?:\.\d+)+)@", text)
        if match:
            return match.group(1)
    return ""


def compare(current: str, latest: str) -> str:
    if not latest:
        return "確認失敗"
    return "最新" if version_key(current) >= version_key(latest) else "更新あり"


def patch_preimages(text: str) -> list[tuple[str, str]]:
    """Return (path, pre-image text) for each hunk of a unified diff."""
    hunks: list[tuple[str, str]] = []
    path, lines = "", None
    for line in text.splitlines():
        if line.startswith("+++ "):
            path = line[4:].split("\t")[0].removeprefix("b/")
        elif line.startswith("@@"):
            if lines is not None:
                hunks.append((path, "\n".join(lines)))
            lines = []
        elif lines is not None and line[:1] in (" ", "-", ""):
            lines.append(line[1:])
    if lines is not None:
        hunks.append((path, "\n".join(lines)))
    return hunks


def upstream_rows(root: Path, today: date) -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []

    def add(name: str, current: str, check, status_of=compare, note: str = "") -> None:
        try:
            latest = check()
            status = status_of(current, latest)
        except Exception as error:  # noqa: BLE001 - report every upstream failure
            latest, status = f"取得失敗（{type(error).__name__}）", "確認失敗"
        rows.append((name, current, latest, status, note))

    links = gitlinks(root)
    modules = submodules(root)
    current_tag = sel4_tag(root, links) or links["vendor/seL4"][:12]
    add("seL4", current_tag, lambda: latest_release("seL4/seL4"),
        note="上げるときは seL4_tools も manifest に合わせる")

    def tools_status(current: str, latest: str) -> str:
        return "最新" if current == latest else "更新あり"

    add("seL4_tools", links["vendor/seL4_tools"][:12],
        lambda: manifest_revisions(latest_release("seL4/seL4"))["seL4_tools.git"][:12],
        tools_status, "最新の seL4 release の sel4test-manifest と比べる")
    for patch in sorted((root / "patches" / "seL4").glob("*.patch")):
        def patched_site_state(patch: Path = patch) -> str:
            cache: dict[str, str] = {}
            for path, pre in patch_preimages(patch.read_text()):
                if path not in cache:
                    cache[path] = fetch(
                        f"https://raw.githubusercontent.com/seL4/seL4/master/{path}",
                        accept="text/plain",
                    )
                if pre not in cache[path]:
                    return "変更あり"
            return "修正前のまま"
        add(f"seL4 の patch {patch.name[:4]}", "修正前のまま", patched_site_state,
            lambda current, latest: "最新" if current == latest else "更新あり",
            "seL4 master の該当箇所。変わったら上流の修正を確かめ、取り込めたら patch を外す")

    yomiyasu = parse_peeled_tags(
        ls_remote(modules["vendor/yomiyasu"]["url"], "refs/tags/*")
    ).get(links["vendor/yomiyasu"], links["vendor/yomiyasu"][:12])
    add("yomiyasu", yomiyasu, lambda: latest_release("nanaism/yomiyasu"))
    add("m5stack-linux-dtoverlays", links["vendor/m5stack-linux-dtoverlays"][:12],
        lambda: parse_heads(ls_remote(
            modules["vendor/m5stack-linux-dtoverlays"]["url"], "refs/heads/main"
        ))["main"][:12],
        lambda current, latest: "最新" if current == latest else "参考",
        "参照用。差分の内容を読んで採否を決める")

    dockerfile = (root / DOCKERFILE).read_text()
    base, digest = dockerfile_base(dockerfile)
    repository, _, tag = base.partition(":")
    add(f"{base}（digest）", digest[:19],
        lambda: json.loads(fetch(
            f"https://hub.docker.com/v2/repositories/library/{repository}/tags/{tag}",
            accept="application/json",
        )).get("digest", "")[:19],
        lambda current, latest: "最新" if current == latest else "更新あり",
        "Dependabot の docker でも追う")
    snapshot = dockerfile_value(dockerfile, "DEBIAN_SNAPSHOT")
    rows.append(("Debian snapshot", snapshot, f"{SNAPSHOT_MAX_AGE_DAYS} 日以内",
                 snapshot_status(snapshot, today), "古いと security 更新が入らない"))
    add("rust-sel4", rust_sel4_version(root),
        lambda: latest_release("seL4/rust-sel4"),
        note="nightly は release の rust-toolchain.toml に合わせる")
    add("Trivy", workflow_env(root, "TRIVY_VERSION"),
        lambda: latest_release("aquasecurity/trivy"))
    add("actionlint", image_tag_version(root, "rhysd/actionlint"),
        lambda: latest_release("rhysd/actionlint"))
    add("hadolint", workflow_env(root, "HADOLINT_VERSION"),
        lambda: latest_release("hadolint/hadolint"))
    return rows


def render(rows: list[tuple[str, str, str, str, str]]) -> str:
    lines = ["| 依存 | 固定 | 上流 | 状態 | 備考 |", "|---|---|---|---|---|"]
    lines += [f"| {' | '.join(row)} |" for row in rows]
    return "\n".join(lines) + "\n"


def upstream(root: Path, report: Path, today: date) -> int:
    rows = upstream_rows(root, today)
    errors = consistency(root)
    try:
        errors += manifest(root)
    except Exception as error:  # noqa: BLE001
        errors.append(f"manifest check failed: {type(error).__name__}: {error}")
    text = render(rows)
    if errors:
        text += "\n固定値の不整合:\n\n" + "".join(f"- {error}\n" for error in errors)
    report.write_text(text)
    sys.stdout.write(text)
    needs_action = errors or any(row[3] in {"更新あり", "確認失敗"} for row in rows)
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as stream:
            stream.write(f"needs-action={'true' if needs_action else 'false'}\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("consistency", help="offline checks of duplicated pins")
    commands.add_parser("manifest", help="compare submodules with the seL4 release manifest")
    upstream_parser = commands.add_parser("upstream", help="report upstream versions")
    upstream_parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "upstream":
        return upstream(root, args.report, date.today())
    errors = consistency(root) if args.command == "consistency" else manifest(root)
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    print(f"Summary: command={args.command} errors={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
