#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Exercise the installed parser; optionally embed with externally built Rust tools."""

import json
import os
from pathlib import Path
import subprocess
import tempfile

from elftools.elf.elffile import ELFFile

fixtures = Path(__file__).resolve().parent / "fixtures"
with tempfile.TemporaryDirectory() as directory:
    out = Path(directory)
    subprocess.run(["arm-linux-gnueabi-as", str(fixtures / "component.S"),
                    "-o", str(out / "component.o")], check=True)
    subprocess.run(["arm-linux-gnueabi-ld", "-Ttext=0x10000", "-z", "max-page-size=4096",
                    str(out / "component.o"), "-o", str(out / "component.elf")], check=True)
    with (out / "component.elf").open("rb") as stream:
        section = ELFFile(stream).get_section_by_name(".text")
        assert section["sh_offset"] == 0x1000 and section["sh_size"] == 4

    def parse(source, dest, check=True):
        return subprocess.run(["parse-capDL", f"--object-sizes={fixtures / 'sizes.yaml'}",
                               f"--json={dest}", str(source)], check=check,
                              capture_output=True, text=True)

    spec_path = out / "spec.json"
    parse(fixtures / "compat.cdl", spec_path)
    spec = json.loads(spec_path.read_text())
    objects = {entry["name"]: entry["object"] for entry in spec["objects"]}
    assert set(objects) == {"uart", "pd", "pt", "code", "ipc", "cn", "ep", "thread"}
    assert objects["uart"]["Frame"]["paddr"] == 0x3f201000
    assert objects["thread"]["Tcb"]["extra"]["master_fault_ep"] == 0
    assert objects["code"]["Frame"]["init"]["entries"] == [{
        "range": {"start": 0, "end": 4},
        "content": {"Data": {"file": "component.elf", "file_offset": 0x1000}},
    }]
    frames = [cap["Frame"] for obj in objects.values()
              for data in obj.values() for _slot, cap in (data or {}).get("slots", [])
              if "Frame" in cap]
    assert frames and all(isinstance(cap["executable"], bool) for cap in frames)
    assert any(cap["executable"] for cap in frames)
    assert any(not cap["executable"] for cap in frames)
    print("ok - capDL JSON: TCB, CNode, endpoint, frames, device address, ELF fill, executable")

    empty = out / "empty.cdl"
    empty.write_text("arch arm11\nobjects {}\ncaps {}\n")
    parse(empty, out / "empty.json")
    assert json.loads((out / "empty.json").read_text())["objects"] == []
    print("ok - empty capDL spec")
    invalid = out / "invalid.cdl"
    invalid.write_text("not capDL\n")
    assert parse(invalid, out / "invalid.json", check=False).returncode != 0
    print("ok - invalid capDL spec rejected")

    add_spec = os.environ.get("MSD_CAPDL_ADD_SPEC")
    initializer = os.environ.get("MSD_CAPDL_INITIALIZER")
    if add_spec or initializer:
        assert add_spec and initializer, "set both MSD_CAPDL_ADD_SPEC and MSD_CAPDL_INITIALIZER"
        subprocess.run([add_spec, "-e", initializer, "-f", str(spec_path), "-d", str(out),
                        "-n", "2", "-o", str(out / "initializer.elf")], check=True)
        with (out / "initializer.elf").open("rb") as stream:
            segments = list(ELFFile(stream).iter_segments())
            assert any(seg["p_type"] == 0x64c34003 and seg["p_filesz"] > 0 for seg in segments)
        print("ok - JSON accepted and embedded by sel4-capdl-initializer-add-spec")
