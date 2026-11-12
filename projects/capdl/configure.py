#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Generate component constants from the same validated system declaration."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/capdl"))
from schema import load


def main():
    system, dest = load(sys.argv[1]), Path(sys.argv[2])
    dest.mkdir(parents=True, exist_ok=True)
    for pd in system["pds"]:
        lines = ["/* SPDX-License-Identifier: BSD-3-Clause */", "#pragma once",
                 f'#define MSD_IPC_BUFFER 0x{pd["ipc_buffer"]:x}u']
        for grant in pd["grants"]:
            lines.append(f'#define MSD_CAP_{grant["name"].upper()} {grant["slot"]}u')
            if "vaddr" in grant:
                lines.append(f'#define MSD_VADDR_{grant["name"].upper()} 0x{grant["vaddr"]:x}u')
        (dest / f'{pd["name"]}-config.h').write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
