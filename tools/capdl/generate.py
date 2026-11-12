#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Generate static AArch32 capDL and the declared capability table."""

import argparse
from pathlib import Path
import sys

import elf
import report
from schema import PAGE, RIGHTS, frames, load, require


def generate(system, elf_dir):
    definitions, caps = {}, {}

    def define(n, definition):
        require(n not in definitions, f"generated name collision: {n}")
        definitions[n] = definition

    def cap(n, slot, target):
        require(slot not in caps.setdefault(n, {}), f"duplicate generated slot in {n}")
        caps[n][slot] = target

    objects = {o["name"]: o for o in system["objects"]}
    for obj in system["objects"]:
        kind = obj["type"]
        if kind in {"endpoint", "notification"}:
            define(f"o_{obj['name']}", "ep" if kind == "endpoint" else "notification")
        else:
            for i, n in enumerate(frames(obj)):
                extra = f", paddr: 0x{obj['paddr'] + i * PAGE:x}" if kind == "device" else ""
                define(n, f"frame (4k{extra})")
    for pd in sorted(system["pds"], key=lambda p: p["name"]):
        prefix = f"p_{pd['name']}"
        path = (elf_dir / pd["elf"]).resolve()
        require(path.is_relative_to(elf_dir.resolve()), "ELF escapes fill directory")
        entry, pages = elf.read(path)
        mappings = {}

        def mapping(addr, target, rights, executable=False, cached=True):
            require(addr not in mappings, f"overlapping ELF/stack/IPC/grant mapping in {pd['name']}")
            mappings[addr] = (target, rights, executable, cached)

        for addr, page in sorted(pages.items()):
            n = f"{prefix}_elf_{addr:x}"
            fills = ", ".join(f'{{{offset} {size} CDL_FrameFill_FileData "{pd["elf"]}" {source}}}'
                              for offset, size, source in sorted(page["fills"]))
            define(n, f"frame (4k, fill: [{fills}])" if fills else "frame (4k)")
            mapping(addr, n, "RW" if page["flags"] & 2 else "R", bool(page["flags"] & 1))
        for i in range(pd["stack"]["size"] // PAGE):
            n = f"{prefix}_stack_{i}"
            define(n, "frame (4k)")
            mapping(pd["stack"]["vaddr"] + i * PAGE, n, "RW")
        define(f"{prefix}_ipc", "frame (4k)")
        mapping(pd["ipc_buffer"], f"{prefix}_ipc", "RW")
        fault = 0
        maxslot = max((g["slot"] + objects[g["object"]].get("size", PAGE) // PAGE - 1 for g in pd["grants"]), default=0)
        bits = max(1, maxslot.bit_length())
        define(f"{prefix}_cspace", f"cnode ({bits} bits)")
        for grant in pd["grants"]:
            obj = objects[grant["object"]]
            rights = "".join(letter for r, letter in zip(RIGHTS, "RWGP") if r in grant["rights"])
            if obj["type"] in {"frame", "region", "device"}:
                for i, target in enumerate(frames(obj)):
                    cached = obj["type"] != "device"
                    cache = "cached" if cached else "uncached"
                    cap(f"{prefix}_cspace", grant["slot"] + i, f"{target} ({rights}, execute_never, {cache})")
                    mapping(grant["vaddr"] + i * PAGE, target, rights, cached=cached)
            else:
                cap(f"{prefix}_cspace", grant["slot"], f"o_{obj['name']} ({rights}, badge: {grant.get('badge', 0)})")
            if pd.get("fault_endpoint") == grant["name"]:
                fault = grant["slot"]
        define(f"{prefix}_vspace", "pd")
        for addr, (target, rights, executable, cached) in sorted(mappings.items()):
            index = addr >> 20
            pt = f"{prefix}_pt_{index}"
            if pt not in definitions:
                define(pt, "pt")
                cap(f"{prefix}_vspace", index, pt)
            execute = "executable" if executable else "execute_never"
            cache = "cached" if cached else "uncached"
            cap(pt, (addr >> 12) & 255, f"{target} ({rights}, {execute}, {cache})")
        sp = pd["stack"]["vaddr"] + pd["stack"]["size"]
        require(sp < 2**32, "stack top must fit ARM word")
        define(f"{prefix}_tcb", f"tcb (addr: {pd['ipc_buffer']}, ip: {entry}, sp: {sp}, prio: {pd['priority']}, max_prio: {pd['priority']}, affinity: 0, fpu_disabled: True, init: [], fault_ep: {fault})")
        caps[f"{prefix}_tcb"] = {
            "cspace": f"{prefix}_cspace (guard: 0, guard_size: {32 - bits})",
            "vspace": f"{prefix}_vspace",
            "ipc_buffer_slot": f"{prefix}_ipc (RW, execute_never)",
        }
    lines = ["/* SPDX-License-Identifier: BSD-3-Clause */", "arch arm11", "objects {"]
    lines += [f"  {n} = {value}" for n, value in sorted(definitions.items())]
    lines += ["}", "caps {"]
    for n, slots in sorted(caps.items()):
        entries = " ".join(f"{slot}: {value}" for slot, value in sorted(slots.items()))
        lines.append(f"  {n} {{ {entries} }}")
    return "\n".join(lines + ["}", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("system", type=Path)
    parser.add_argument("--elf-dir", type=Path, help="ELF/fill root; defaults to the TOML directory")
    parser.add_argument("--cdl", type=Path)
    parser.add_argument("--table", type=Path)
    args = parser.parse_args()
    try:
        require(args.cdl or args.table, "specify --cdl and/or --table")
        system = load(args.system)
        cdl = generate(system, args.elf_dir or args.system.parent) if args.cdl else None
        table = report.render(system) if args.table else None
        if args.cdl:
            args.cdl.write_text(cdl, encoding="utf-8", newline="\n")
        if args.table:
            args.table.write_text(table, encoding="utf-8", newline="\n")
        return 0
    except (ValueError, OSError) as error:
        print(f"capdl: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
