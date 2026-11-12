#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Check parser JSON against declarations, without importing the emitter."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import elf
import report
from schema import PAGE, RIGHTS, frames, load, require


def verify(system, spec, elf_dir):
    entries = spec["objects"]
    names = [entry["name"] for entry in entries]
    require(len(names) == len(set(names)), "duplicate parsed object name")
    byname = {entry["name"]: entry["object"] for entry in entries}
    objects = {o["name"]: o for o in system["objects"]}
    expected_names = set()

    def object_at(index):
        require(type(index) is int and 0 <= index < len(entries), "invalid object reference")
        return names[index], entries[index]["object"]

    def slots(data):
        result = dict(data["slots"])
        require(len(result) == len(data["slots"]), "duplicate parsed slot")
        return result

    def cap(value, kind, target, rights=None, badge=None, cached=True, executable=False):
        require(set(value) == {kind}, f"unexpected cap type: {value}")
        data = value[kind]
        if type(data) is int:
            data = {"object": data}
        n, _ = object_at(data["object"])
        require(n == target, f"cap target: expected {target}, got {n}")
        expected = {"object": data["object"]}
        if rights is not None:
            expected["rights"] = {key: r in rights for r, key in zip(RIGHTS, ("read", "write", "grant", "grant_reply"))}
        if badge is not None:
            expected["badge"] = badge
        if kind == "Frame":
            expected.update(cached=cached, executable=executable)
        require(data == expected, f"cap attributes differ for {target}: {data}")

    expected_tcbs = {f"p_{p['name']}_tcb" for p in system["pds"]}
    expected_cnodes = {f"p_{p['name']}_cspace" for p in system["pds"]}
    require({n for n, o in byname.items() if "Tcb" in o} == expected_tcbs, "unexpected TCB set")
    require({n for n, o in byname.items() if "CNode" in o} == expected_cnodes, "unexpected CNode set")
    require(not spec["irqs"] and not spec["untyped_covers"] and not spec["asid_slots"], "unexpected IRQ/untyped/ASID authority")
    allowed_kinds = {"Tcb", "CNode", "PageTable", "Frame", "Endpoint", "Notification"}
    require(all(set(o) <= allowed_kinds for o in byname.values()), "unexpected authority object")
    for obj in system["objects"]:
        for i, n in enumerate(frames(obj) if "size" in obj else [f"o_{obj['name']}"]):
            expected_names.add(n)
            kind = {"endpoint": "Endpoint", "notification": "Notification"}.get(obj["type"], "Frame")
            require(n in byname and set(byname[n]) == {kind}, f"missing or mistyped object {n}")
            if kind == "Frame":
                frame = byname[n][kind]
                paddr = obj["paddr"] + i * PAGE if obj["type"] == "device" else None
                require(frame["paddr"] == paddr and frame["size_bits"] == 12, f"wrong physical frame {n}")
                require(frame["init"]["entries"] == [], "unexpected static frame fill")
    for pd in system["pds"]:
        prefix = f"p_{pd['name']}"
        tcb = byname[f"{prefix}_tcb"]["Tcb"]
        tcbslots = slots(tcb)
        require(set(tcbslots) == {0, 1, 4}, "extra or missing TCB cap")
        cncap = tcbslots[0]
        require(set(cncap) == {"CNode"}, "TCB CSpace is not a CNode")
        cspace_name, cspace = object_at(cncap["CNode"]["object"])
        require(cspace_name == f"{prefix}_cspace" and set(cspace) == {"CNode"}, "wrong TCB CSpace")
        cap(tcbslots[1], "PageTable", f"{prefix}_vspace")
        cap(tcbslots[4], "Frame", f"{prefix}_ipc", ["read", "write"])
        actual = slots(cspace["CNode"])
        expected = {}
        expected_mappings = {}

        def mapping(addr, value):
            require(addr not in expected_mappings, "overlapping declared/ELF mappings")
            expected_mappings[addr] = value

        path = (elf_dir / pd["elf"]).resolve()
        require(path.is_relative_to(elf_dir.resolve()), "ELF escapes fill directory")
        entry, pages = elf.read(path)
        for addr, page in pages.items():
            mapping(addr, (f"{prefix}_elf_{addr:x}", ["read", "write"] if page["flags"] & 2 else ["read"], True, bool(page["flags"] & 1)))
        for i in range(pd["stack"]["size"] // PAGE):
            mapping(pd["stack"]["vaddr"] + i * PAGE, (f"{prefix}_stack_{i}", ["read", "write"], True, False))
        mapping(pd["ipc_buffer"], (f"{prefix}_ipc", ["read", "write"], True, False))
        fault = 0
        for grant in pd["grants"]:
            obj = objects[grant["object"]]
            kind = {"endpoint": "Endpoint", "notification": "Notification"}.get(obj["type"], "Frame")
            targets = frames(obj) if kind == "Frame" else [f"o_{obj['name']}"]
            for i, target in enumerate(targets):
                expected[grant["slot"] + i] = (kind, target, grant["rights"], grant.get("badge", 0) if kind != "Frame" else None, obj["type"] != "device")
                if kind == "Frame":
                    mapping(grant["vaddr"] + i * PAGE, (target, grant["rights"], obj["type"] != "device", False))
            if pd.get("fault_endpoint") == grant["name"]:
                fault = grant["slot"]
        require(set(actual) == set(expected), f"CSpace slots differ for {pd['name']}: actual={sorted(actual)} expected={sorted(expected)}")
        for slot, (kind, target, rights, badge, cached) in expected.items():
            cap(actual[slot], kind, target, rights, badge, cached)
        bits = max(1, max(expected, default=0).bit_length())
        require(cspace["CNode"]["size_bits"] == bits and cncap["CNode"]["guard"] == 0 and cncap["CNode"]["guard_size"] == 32 - bits, "wrong CSpace guard/size")
        extra = tcb["extra"]
        expected_extra = {"ipc_buffer_addr": pd["ipc_buffer"], "affinity": 0, "prio": pd["priority"],
                          "max_prio": pd["priority"], "fpu_disabled": True, "ip": entry,
                          "sp": pd["stack"]["vaddr"] + pd["stack"]["size"], "gprs": [], "master_fault_ep": fault}
        require(all(extra[k] == v for k, v in expected_extra.items()), "TCB configuration differs")
        require(extra["resume"] is True, "TCB must resume")
        expected_names.update({f"{prefix}_tcb", f"{prefix}_cspace", f"{prefix}_vspace"})
        expected_names.update(value[0] for value in expected_mappings.values())
        expected_names.update(f"{prefix}_pt_{addr >> 20}" for addr in expected_mappings)
        root = byname[f"{prefix}_vspace"]["PageTable"]
        require(root["is_root"] and root["level"] == 0, "not an ARM11 root page directory")
        mappings = {}
        for pdslot, ptcap in slots(root).items():
            require(type(pdslot) is int and 0 <= pdslot < 4096, "invalid PD slot")
            target = f"{prefix}_pt_{pdslot}"
            cap(ptcap, "PageTable", target)
            pt = byname[target]["PageTable"]
            require(not pt["is_root"] and pt["level"] == 3, "not an ARM11 leaf page table")
            for ptslot, framecap in slots(pt).items():
                require(type(ptslot) is int and 0 <= ptslot < 256, "invalid PT slot")
                addr = (pdslot << 20) | (ptslot << 12)
                require(addr in expected_mappings, "extra mapped cap")
                n, rights, cached, execute = expected_mappings[addr]
                cap(framecap, "Frame", n, rights, cached=cached, executable=execute)
                if n.startswith(prefix + "_"):
                    frame = byname[n]["Frame"]
                    require(frame["paddr"] is None and frame["size_bits"] == 12, "private frame must be RAM")
                    fills = []
                    if addr in pages:
                        fills = [{"range": {"start": offset, "end": offset + size},
                                  "content": {"Data": {"file": pd["elf"], "file_offset": source}}}
                                 for offset, size, source in sorted(pages[addr]["fills"])]
                    require(frame["init"]["entries"] == fills, "private frame fill differs from ELF")
                mappings[addr] = n
        require(set(mappings) == set(expected_mappings), "missing mapped cap")
    require(set(byname) == expected_names, "extra or missing object")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("system", type=Path)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--cdl", type=Path)
    parser.add_argument("--elf-dir", type=Path)
    parser.add_argument("--object-sizes", type=Path)
    parser.add_argument("--parser", default="parse-capDL")
    args = parser.parse_args()
    try:
        system = load(args.system)
        require(args.table.read_bytes() == report.render(system).encode("utf-8"), "capability table is stale")
        if args.cdl:
            require(args.object_sizes is not None, "--cdl requires --object-sizes from the matching kernel")
            with tempfile.TemporaryDirectory() as directory:
                dest = Path(directory) / "spec.json"
                result = subprocess.run([args.parser, f"--object-sizes={args.object_sizes}", f"--json={dest}", str(args.cdl)], capture_output=True, text=True)
                require(result.returncode == 0, f"parse-capDL failed: {result.stderr}")
                verify(system, json.loads(dest.read_text()), args.elf_dir or args.system.parent)
        print("capdl-check: table and parsed authority match" if args.cdl else "capdl-check: table matches (no capDL checked)")
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(f"capdl-check: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
