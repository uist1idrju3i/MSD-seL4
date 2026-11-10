# SPDX-License-Identifier: BSD-3-Clause
"""Tests for .github/scripts/check-pins.py."""

import importlib.util
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".github/scripts/check-pins.py"
SPEC = importlib.util.spec_from_file_location("check_pins", SCRIPT)
check_pins = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_pins)

SHA_A = "a" * 40
SHA_B = "b" * 40
DIGEST = "sha256:" + "c" * 64
WORKFLOW = f"""jobs:
  one:
    runs-on: ubuntu-26.04
    steps:
      - uses: actions/checkout@{SHA_A} # v7.0.1
      - uses: github/codeql-action/init@{SHA_B} # v4.39.3
      - uses: github/codeql-action/analyze@{SHA_B} # v4.39.3
    env:
      TOOL_DIGEST: "{DIGEST}"
      TOOL_IMAGE: example/tool:1.2.3@{DIGEST}
"""
DOCKERFILE = f"""FROM debian:trixie-slim@{DIGEST}
ARG DEBIAN_SNAPSHOT=20261103T023120Z
ARG RUST_SEL4_NIGHTLY=nightly-2026-08-21
"""


class FixtureRepo:
    def __init__(self, directory: str) -> None:
        self.root = Path(directory)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.write(".github/workflows/ci.yml", WORKFLOW)
        self.write("docker/msd-sel4-dev.Dockerfile", DOCKERFILE)
        self.write(".gitmodules", '[submodule "vendor/x"]\n\tpath = vendor/x\n'
                   "\turl = https://example.com/x.git\n\tshallow = true\n")
        self.write("research/vendor/dependencies.md", f"`vendor/x` {SHA_A}\n")
        subprocess.run(["git", "-C", str(self.root), "update-index", "--add",
                        "--cacheinfo", f"160000,{SHA_A},vendor/x"], check=True)

    def write(self, path: str, text: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)


class ConsistencyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.repo = FixtureRepo(self.directory.name)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def errors(self) -> list[str]:
        return check_pins.consistency(self.repo.root)

    def test_patch_preimages(self) -> None:
        text = (
            "header\n--- a/src/x.c\n+++ b/src/x.c\n@@ -1,3 +1,4 @@\n"
            " keep\n-old\n+new\n \n"
        )
        self.assertEqual(check_pins.patch_preimages(text), [("src/x.c", "keep\nold\n")])

    def test_accepts_consistent_pins(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_rejects_tag_reference(self) -> None:
        self.repo.write(".github/workflows/ci.yml",
                        WORKFLOW.replace(f"checkout@{SHA_A}", "checkout@v7"))
        self.assertTrue(any("full commit SHA" in e for e in self.errors()))

    def test_rejects_missing_version_comment(self) -> None:
        self.repo.write(".github/workflows/ci.yml",
                        WORKFLOW.replace(f"{SHA_A} # v7.0.1", SHA_A))
        self.assertTrue(any("vX.Y.Z" in e for e in self.errors()))

    def test_rejects_split_action_revisions(self) -> None:
        self.repo.write(".github/workflows/other.yml",
                        f"      - uses: github/codeql-action/upload-sarif@{SHA_A} # v4.39.2\n")
        self.assertTrue(any("different revisions" in e for e in self.errors()))

    def test_rejects_short_digest(self) -> None:
        self.repo.write(".github/workflows/ci.yml",
                        WORKFLOW.replace(f'"{DIGEST}"', '"sha256:abcd"'))
        self.assertTrue(any("TOOL_DIGEST" in e for e in self.errors()))

    def test_rejects_mixed_runner_labels(self) -> None:
        self.repo.write(".github/workflows/other.yml", "    runs-on: ubuntu-24.04\n")
        self.assertTrue(any("runner labels" in e for e in self.errors()))

    def test_rejects_unpinned_base_image(self) -> None:
        self.repo.write("docker/msd-sel4-dev.Dockerfile",
                        DOCKERFILE.replace(f"@{DIGEST}", ""))
        self.assertTrue(any("FROM must pin" in e for e in self.errors()))

    def test_rejects_floating_rust(self) -> None:
        self.repo.write("docker/msd-sel4-dev.Dockerfile",
                        DOCKERFILE.replace("nightly-2026-08-21", "nightly"))
        self.assertTrue(any("RUST_SEL4_NIGHTLY" in e for e in self.errors()))

    def test_rejects_deep_submodule(self) -> None:
        text = (self.repo.root / ".gitmodules").read_text()
        self.repo.write(".gitmodules", text.replace("shallow = true", "shallow = false"))
        self.assertTrue(any("shallow = true" in e for e in self.errors()))

    def test_rejects_unrecorded_gitlink(self) -> None:
        self.repo.write("research/vendor/dependencies.md", "`vendor/x` aaaaaaaa\n")
        self.assertTrue(any("record the full commit" in e for e in self.errors()))


class ParserTest(unittest.TestCase):
    def test_manifest(self) -> None:
        text = ('<manifest><project name="seL4.git" revision="1"/>'
                '<project name="seL4_tools.git" revision="2"/></manifest>')
        self.assertEqual(check_pins.parse_manifest(text),
                         {"seL4.git": "1", "seL4_tools.git": "2"})

    def test_peeled_tags_prefer_commit(self) -> None:
        text = (f"{SHA_A}\trefs/tags/17.0.0\n{SHA_B}\trefs/tags/17.0.0^{{}}\n"
                f"{'d' * 40}\trefs/tags/16.0.0\n")
        tags = check_pins.parse_peeled_tags(text)
        self.assertEqual(tags[SHA_B], "17.0.0")
        self.assertNotIn(SHA_A, tags)
        self.assertEqual(tags["d" * 40], "16.0.0")

    def test_rust_sel4_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "projects/rust-smoke").mkdir(parents=True)
            (root / "projects/rust-smoke/Cargo.toml").write_text(
                'sel4 = { git = "https://github.com/seL4/rust-sel4", '
                f'rev = "{SHA_A}" }} # v6.0.0\n')
            self.assertEqual(check_pins.rust_sel4_version(root), "v6.0.0")

    def test_snapshot_age(self) -> None:
        self.assertEqual(check_pins.snapshot_status("20261103T023120Z", date(2026, 12, 3)), "最新")
        self.assertEqual(check_pins.snapshot_status("20261103T023120Z", date(2026, 12, 4)), "更新あり")
        self.assertEqual(check_pins.snapshot_status("bad", date(2026, 12, 4)), "確認失敗")

    def test_compare_versions(self) -> None:
        self.assertEqual(check_pins.compare("0.76.1", "v0.76.2"), "更新あり")
        self.assertEqual(check_pins.compare("1.7.12", "v1.7.12"), "最新")
        self.assertEqual(check_pins.compare("1.7.12", ""), "確認失敗")


if __name__ == "__main__":
    unittest.main()
