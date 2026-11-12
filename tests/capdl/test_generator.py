# SPDX-License-Identifier: BSD-3-Clause
"""Host-only validation/layout tests and opt-in installed-parser mutation tests."""

import copy
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/capdl"))
import check
import elf
import generate
import report
import schema

SYSTEM = ROOT / "projects/capdl/system.toml"
MODEL = schema.load(SYSTEM)


def image():
    data = bytearray(0x200c)
    ident = b"\x7fELF\x01\x01\x01" + bytes(9)
    struct.pack_into("<16sHHIIIIIHHHHHH", data, 0, ident, 2, 40, 1, 0x10000, 52, 0, 0x05000200, 52, 32, 2, 0, 0, 0)
    struct.pack_into("<8I", data, 52, 1, 0x1000, 0x10000, 0x10000, 4, 4, 5, 4096)
    struct.pack_into("<8I", data, 84, 1, 0x2004, 0x12004, 0x12004, 8, 8192, 6, 4096)
    data[0x1000:0x1004] = b"\xfe\xff\xff\xea"
    data[0x2004:0x200c] = b"fixture!"
    return data


class Validation(unittest.TestCase):
    def setUp(self):
        self.model = copy.deepcopy(MODEL)

    def reject(self):
        with self.assertRaises(ValueError):
            schema.validate(self.model)

    def test_valid(self):
        self.assertEqual(schema.validate(self.model), MODEL)

    def test_unknown_keys_at_every_level(self):
        for path in [(), ("objects", 0), ("pds", 0), ("pds", 0, "stack"), ("pds", 0, "grants", 0)]:
            with self.subTest(path=path):
                self.model = copy.deepcopy(MODEL)
                target = self.model
                for key in path:
                    target = target[key]
                target["surprise"] = 1
                self.reject()

    def test_duplicate_names(self):
        for category in ("objects", "pds"):
            with self.subTest(category=category):
                self.model = copy.deepcopy(MODEL)
                self.model[category].append(copy.deepcopy(self.model[category][0]))
                self.reject()
        self.model = copy.deepcopy(MODEL)
        self.model["pds"][0]["name"] = "uart"
        self.reject()

    def test_duplicate_toml_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.toml"
            path.write_text("version = 1\nversion = 1\n")
            with self.assertRaises(ValueError):
                schema.load(path)

    def test_forbidden_authority(self):
        for kind in ("untyped", "cnode", "tcb", "irq"):
            with self.subTest(kind=kind):
                self.model = copy.deepcopy(MODEL)
                self.model["objects"][1]["type"] = kind
                self.reject()
        for kind in ("untyped", "cnode", "tcb"):
            with self.subTest(grant=kind):
                self.model = copy.deepcopy(MODEL)
                self.model["pds"][1]["grants"][0].update(type=kind, object="serial")
                self.reject()

    def test_untyped_or_missing_grant_type(self):
        del self.model["pds"][0]["grants"][0]["type"]
        self.reject()

    def test_grant_rights_require_explicit_permission(self):
        for right in ("grant", "grantreply"):
            with self.subTest(right=right):
                self.model = copy.deepcopy(MODEL)
                self.model["pds"][1]["grants"][0]["rights"].append(right)
                self.reject()
                self.model["objects"][1]["allow_grant"] = True
                schema.validate(self.model)

    def test_kernel_owned_devices(self):
        self.model["kernel_printing"] = True
        self.reject()
        for address in (0x3f00b000, 0x40000000):
            with self.subTest(address=address):
                self.model = copy.deepcopy(MODEL)
                self.model["objects"][0]["paddr"] = address
                self.reject()
        self.model = copy.deepcopy(MODEL)
        self.model["objects"][0].update(paddr=0x3f00a000, size=8192)
        self.reject()

    def test_dma_marker(self):
        self.model["objects"][0]["dma_capable"] = True
        self.reject()
        self.model["objects"][0]["dma"] = "restricted"
        self.reject()
        self.model["objects"][0]["dma"] = "all-memory"
        schema.validate(self.model)
        self.model["objects"][0].update(paddr=0x3f007000, dma_capable=False)
        self.reject()

    def test_missing_rights_and_wrong_type(self):
        for field, value in (("rights", []), ("rights", ["execute"]), ("rights", ["write", "write"]),
                             ("type", "frame"), ("object", "absent"), ("badge", -1), ("badge", 2**28), ("slot", True)):
            with self.subTest(field=field, value=value):
                self.model = copy.deepcopy(MODEL)
                self.model["pds"][1]["grants"][0][field] = value
                self.reject()

    def test_duplicate_slot_and_label(self):
        for field in ("name", "slot"):
            self.model = copy.deepcopy(MODEL)
            self.model["pds"][0]["grants"][1][field] = self.model["pds"][0]["grants"][0][field]
            self.reject()

    def test_invalid_paths_ranges_and_types(self):
        for field, value in (("elf", "../x.elf"), ("elf", "/tmp/x.elf"), ("elf", 'a".elf'),
                             ("priority", 256), ("ipc_buffer", 0x70000000), ("ipc_buffer", 1), ("ipc_buffer", 0xfffff000)):
            with self.subTest(field=field):
                self.model = copy.deepcopy(MODEL)
                self.model["pds"][0][field] = value
                self.reject()

    def test_optional_fault_endpoint(self):
        self.model["pds"][1]["fault_endpoint"] = "missing"
        self.reject()
        self.model["pds"][1]["fault_endpoint"] = "send"
        self.reject()
        self.model["objects"][1]["allow_grant"] = True
        self.model["pds"][1]["grants"][0]["rights"].append("grantreply")
        schema.validate(self.model)

    def test_notification_shared_region_and_empty_grants(self):
        self.model["objects"] += [dict(name="notice", type="notification", reason="通知"),
                                  dict(name="shared", type="region", size=8192, reason="共有")]
        self.model["pds"][0]["grants"] += [dict(name="notice", slot=3, object="notice", type="notification", rights=["read"], badge=2, reason="通知"),
                                          dict(name="shared", slot=4, object="shared", type="region", rights=["read"], vaddr=0x50000000, reason="共有")]
        schema.validate(self.model)
        self.model["pds"][1]["grants"] = []
        schema.validate(self.model)


class Workspace(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.out = Path(self.directory.name)
        for label in ("serial", "client"):
            (self.out / f"{label}.elf").write_bytes(image())


class Layout(Workspace):
    def test_fills_and_bss(self):
        entry, pages = elf.read(self.out / "serial.elf")
        self.assertEqual(entry, 0x10000)
        self.assertEqual(pages[0x12000]["fills"], [(4, 8, 0x2004)])
        self.assertEqual(pages[0x13000]["fills"], [])
        self.assertEqual(pages[0x14000]["fills"], [])
        cdl = generate.generate(MODEL, self.out)
        self.assertIn('CDL_FrameFill_FileData "serial.elf" 8196', cdl)
        self.assertIn("execute_never, uncached", cdl)

    def test_determinism_and_order_independence(self):
        model = copy.deepcopy(MODEL)
        model["pds"].reverse()
        model["objects"].reverse()
        for pd in model["pds"]:
            pd["grants"].reverse()
            for grant in pd["grants"]:
                grant["rights"].reverse()
        outputs = [generate.generate(MODEL, self.out).encode() for _ in range(5)]
        self.assertEqual(len(set(outputs)), 1)
        self.assertEqual(outputs[0], generate.generate(model, self.out).encode())
        self.assertEqual(report.render(MODEL), report.render(model))

    def test_empty_grants(self):
        model = copy.deepcopy(MODEL)
        model["objects"] = []
        for pd in model["pds"]:
            pd["grants"] = []
        schema.validate(model)
        self.assertIn("cnode (1 bits)", generate.generate(model, self.out))

    def test_bad_elf(self):
        variants = [b"", b"not ELF"]
        for offset, value in ((4, 2), (5, 2), (16, 3), (18, 62)):
            data = image()
            data[offset] = value
            variants.append(data)
        for offset, value in ((36, 0x05000400), (52, 2), (52 + 16, 8192),
                              (52 + 24, 7), (52 + 28, 3), (84 + 8, 0x10000), (28, 0xfffffff0), (24, 0x12004)):
            data = image()
            struct.pack_into("<I", data, offset, value)
            variants.append(data)
        for index, data in enumerate(variants):
            with self.subTest(index=index):
                path = self.out / "bad.elf"
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    elf.read(path)

    def test_missing_elf_and_overlap(self):
        model = copy.deepcopy(MODEL)
        model["pds"][0]["elf"] = "missing.elf"
        with self.assertRaises(OSError):
            generate.generate(model, self.out)
        model["pds"][0]["elf"] = "serial.elf"
        model["pds"][0]["ipc_buffer"] = 0x10000
        with self.assertRaises(ValueError):
            generate.generate(model, self.out)

    def test_cli_and_stale_table(self):
        table = self.out / "table.md"
        cdl = self.out / "system.cdl"
        result = subprocess.run([sys.executable, str(ROOT / "tools/capdl/generate.py"), str(SYSTEM), "--elf-dir", str(self.out), "--cdl", str(cdl), "--table", str(table)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        command = [sys.executable, str(ROOT / "tools/capdl/check.py"), str(SYSTEM), "--table", str(table)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        table.write_text("stale\n")
        result = subprocess.run(command, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"stale", result.stderr)


@unittest.skipUnless(os.environ.get("MSD_CAPDL_PARSER_TESTS") == "1", "parser integration runs in the development image")
class Parser(Workspace):
    def setUp(self):
        super().setUp()
        self.assertIsNotNone(shutil.which("parse-capDL"), "installed parser required")
        self.cdl = self.out / "system.cdl"
        self.table = self.out / "table.md"
        self.cdl.write_text(generate.generate(MODEL, self.out))
        self.table.write_text(report.render(MODEL))
        self.command = [sys.executable, str(ROOT / "tools/capdl/check.py"), str(SYSTEM), "--elf-dir", str(self.out),
                        "--table", str(self.table), "--cdl", str(self.cdl), "--object-sizes", str(ROOT / "tests/capdl/sizes.yaml")]

    def test_parsed_valid(self):
        result = subprocess.run(self.command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def parse_model(self, model):
        schema.validate(model)
        self.cdl.write_text(generate.generate(model, self.out))
        dest = self.out / "parsed.json"
        subprocess.run(["parse-capDL", f"--object-sizes={ROOT / 'tests/capdl/sizes.yaml'}", f"--json={dest}", str(self.cdl)], check=True, capture_output=True)
        spec = check.json.loads(dest.read_text())
        check.verify(model, spec, self.out)
        return spec

    def test_parsed_empty(self):
        model = copy.deepcopy(MODEL)
        model["objects"] = []
        for pd in model["pds"]:
            pd["grants"] = []
        self.parse_model(model)

    def test_parsed_shared_notification_fault_and_dma(self):
        model = copy.deepcopy(MODEL)
        model["objects"][1]["allow_grant"] = True
        model["pds"][1]["grants"][0]["rights"].append("grantreply")
        model["pds"][1]["fault_endpoint"] = "send"
        model["objects"] += [dict(name="notice", type="notification", reason="通知"),
                             dict(name="shared", type="region", size=8192, reason="共有"),
                             dict(name="dma", type="device", paddr=0x3f007000, size=4096, dma_capable=True, dma="all-memory", reason="構造の試験のみ")]
        for pd in model["pds"]:
            pd["grants"] += [dict(name="notice", slot=3, object="notice", type="notification", rights=["write"], badge=3, reason="通知"),
                             dict(name="shared", slot=4, object="shared", type="region", rights=["read"] if pd["name"] == "client" else ["read", "write"], vaddr=0x50000000, reason="共有")]
        model["pds"][0]["grants"].append(dict(name="dma", slot=6, object="dma", type="device", rights=["read", "write"], vaddr=0x60000000, reason="構造だけを試験"))
        self.parse_model(model)

    def test_mutations(self):
        original = self.cdl.read_text()
        changes = {
            "add_cap": ("p_client_cspace { ", "p_client_cspace { 0: o_serial_ep (W, badge: 1) "),
            "drop_cap": ("1: o_serial_ep (W, badge: 1)", ""),
            "rights": ("1: o_serial_ep (W, badge: 1)", "1: o_serial_ep (RW, badge: 1)"),
            "badge": ("1: o_serial_ep (W, badge: 1)", "1: o_serial_ep (W, badge: 2)"),
            "foreign_cspace": ("cspace: p_client_cspace", "cspace: p_serial_cspace"),
            "tcb_cap": ("p_client_cspace { ", "p_client_cspace { 0: p_serial_tcb "),
            "physical_device": ("paddr: 0x3f201000", "paddr: 0x3f00b000"),
            "extra_vspace_cap": ("p_client_pt_0 { ", "p_client_pt_0 { 15: o_uart (RW, execute_never, uncached) "),
        }
        for label, (old, new) in changes.items():
            with self.subTest(label=label):
                self.assertIn(old, original)
                self.cdl.write_text(original.replace(old, new, 1))
                result = subprocess.run(self.command, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertNotIn("parse-capDL failed", result.stderr, result.stderr)

    def test_parser_rejects_invalid_page_table_kind(self):
        self.cdl.write_text(self.cdl.read_text().replace("p_client_pt_0 = pt", "p_client_pt_0 = pd"))
        result = subprocess.run(self.command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("parse-capDL failed", result.stderr)

    def test_json_page_table_levels(self):
        spec = self.parse_model(MODEL)
        for target, level in (("p_client_vspace", 2), ("p_client_pt_0", 0)):
            with self.subTest(target=target):
                changed = copy.deepcopy(spec)
                entry = next(o for o in changed["objects"] if o["name"] == target)
                entry["object"]["PageTable"]["level"] = level
                with self.assertRaises(ValueError):
                    check.verify(MODEL, changed, self.out)


if __name__ == "__main__":
    unittest.main()
