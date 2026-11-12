# SPDX-License-Identifier: BSD-3-Clause
"""Host tests for boot instrumentation and kernel-size extraction."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


run = module("verify_run", "tools/capdl/verify-run.py")
sizes = module("object_sizes", "projects/capdl/object-sizes.py")


class Boot(unittest.TestCase):
    def test_copy_preserves_payload_and_rejects_bad_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "source", Path(directory) / "target"
            source.write_bytes(b"ELF\0spec payload\0")
            script = str(ROOT / "tools/capdl/copy-rootserver.sh")
            subprocess.run([script, str(source), "-o", str(target)], check=True)
            self.assertEqual(source.read_bytes(), target.read_bytes())
            target.unlink()
            for args in ([], [str(source), "-o", str(target), "extra"], [str(source), "bad", str(target)]):
                self.assertNotEqual(subprocess.run([script, *args], capture_output=True).returncode, 0)
                self.assertFalse(target.exists())

    def test_positive_and_negative(self):
        positive = run.REQUEST + "\r\n" + run.REPLY + "\r\n"
        self.assertTrue(run.verify(positive, "positive", 124))
        self.assertTrue(run.verify(positive + run.FAULT + "\n", "negative", 124))
        self.assertFalse(run.verify(positive, "negative", 124))
        self.assertFalse(run.verify(positive + run.FAULT, "positive", 124))

    def test_empty_errors_and_order(self):
        positive = run.REQUEST + "\n" + run.REPLY + "\n"
        for text in ("", run.REQUEST, positive + "ERROR\n", positive * 2, run.REPLY + "\n" + run.REQUEST):
            self.assertFalse(run.verify(text, "positive", 124))
        for status in (0, 1, 137, 139):
            self.assertFalse(run.verify(positive, "positive", status))
        self.assertFalse(run.verify(positive, "silent", 124))

    def test_actual_constants_required(self):
        values = (4, 9, 4, 4, 14, 10)
        text = "\n".join(f"#define {name} {n}" for name, n in zip(sizes.NAMES.values(), values))
        self.assertIn("seL4_TCBObject: 9\n", sizes.render(text))
        for text in ("", "#define seL4_TCBBits bad"):
            with self.assertRaises(KeyError):
                sizes.render(text)

    def test_generated_component_constants(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable, str(ROOT / "projects/capdl/configure.py"),
                            str(ROOT / "projects/capdl/system.toml"), directory], check=True)
            client = (Path(directory) / "client-config.h").read_text()
            serial = (Path(directory) / "serial-config.h").read_text()
            self.assertIn("MSD_CAP_FAULT 2u", client)
            self.assertNotIn("MSD_VADDR_UART", client)
            self.assertIn("MSD_VADDR_UART 0x40000000u", serial)

    def test_repeat_preserves_existing_results(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "results.csv"
            dest.write_text("previous results\n")
            command = [sys.executable, str(ROOT / "tools/capdl/repeat.py"),
                       "--positive", directory, "--negative", directory, "--csv", str(dest)]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(dest.read_text(), "previous results\n")
            dest.unlink()
            self.assertNotEqual(subprocess.run(command + ["--repetitions", "0"], capture_output=True).returncode, 0)
            self.assertFalse(dest.exists())
            (Path(directory) / "runs" / "repeat-positive-1").mkdir(parents=True)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
