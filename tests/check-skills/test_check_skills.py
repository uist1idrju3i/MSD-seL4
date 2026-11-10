"""Negative controls for skill inventory drift."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "check_skills", Path(__file__).resolve().parents[2] / ".github/scripts/check-skills.py"
)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class SkillsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / ".agents/skills/example"
        self.skill.mkdir(parents=True)
        self.content = "---\nname: example\ndescription: Example skill\n---\n# Example\n"
        (self.skill / "SKILL.md").write_text(self.content)
        (self.root / ".claude/skills").mkdir(parents=True)
        self.mirror = self.root / ".claude/skills/example"
        self.mirror.symlink_to("../../.agents/skills/example")
        (self.root / "AGENTS.md").write_text("| `example` | Example |\n")
        (self.root / "CLAUDE.md").write_text("@AGENTS.md\n")

    def errors(self):
        return CHECKER.check(self.root)

    def test_valid_local_and_vendor(self):
        self.assertEqual([], self.errors())
        vendor = self.root / "vendor/upstream/skill"
        vendor.mkdir(parents=True)
        (self.skill / "SKILL.md").rename(vendor / "SKILL.md")
        self.skill.rmdir()
        self.skill.symlink_to("../../vendor/upstream/skill")
        self.assertEqual([], self.errors())

    def test_missing_and_extra_mirrors(self):
        self.mirror.unlink()
        self.assertTrue(self.errors())
        self.mirror.symlink_to("../../.agents/skills/example")
        (self.mirror.parent / "orphan").symlink_to("../../.agents/skills/example")
        self.assertTrue(self.errors())

    def test_mirror_must_not_be_a_copy_or_alias(self):
        self.mirror.unlink()
        self.mirror.mkdir()
        (self.mirror / "SKILL.md").write_text(self.content)
        self.assertTrue(self.errors())
        (self.mirror / "SKILL.md").unlink()
        self.mirror.rmdir()
        self.mirror.symlink_to("../../.agents/skills/../skills/example")
        self.assertTrue(self.errors())

    def test_broken_and_escaping_canonical_links(self):
        (self.skill / "SKILL.md").unlink()
        self.skill.rmdir()
        self.skill.symlink_to("../../vendor/missing")
        self.assertTrue(self.errors())
        self.skill.unlink()
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "SKILL.md").write_text(self.content)
        self.skill.symlink_to("../../outside")
        self.assertTrue(self.errors())

    def test_metadata(self):
        for content in ("# No metadata", self.content.replace("example", "wrong"),
                        self.content.replace("description: Example skill", "description:"),
                        self.content.replace("name: example", "name: example\nname: example")):
            with self.subTest(content=content):
                (self.skill / "SKILL.md").write_text(content)
                self.assertTrue(self.errors())

    def test_registration_and_claude_instructions(self):
        for content in ("", "| `example` | One |\n| `example` | Two |\n"):
            (self.root / "AGENTS.md").write_text(content)
            self.assertTrue(self.errors())
        (self.root / "AGENTS.md").write_text("| `example` | Example |\n")
        (self.root / "CLAUDE.md").write_text("Independent instructions")
        self.assertTrue(self.errors())

    def test_missing_inventory(self):
        self.assertTrue(CHECKER.check(self.root / "missing"))


if __name__ == "__main__":
    unittest.main()
