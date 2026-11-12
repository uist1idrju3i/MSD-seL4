#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Use the actual preprocessed libsel4 constants, never the unit-test fixture."""
from pathlib import Path
import re
import sys

NAMES = {"seL4_Slot": "seL4_SlotBits", "seL4_TCBObject": "seL4_TCBBits",
         "seL4_EndpointObject": "seL4_EndpointBits", "seL4_NotificationObject": "seL4_NotificationBits",
         "seL4_PageDirectoryObject": "seL4_PageDirBits", "seL4_PageTableObject": "seL4_PageTableBits"}


def render(text):
    constants = dict(re.findall(r"^#define (\w+) ([0-9]+)$", text, re.MULTILINE))
    return "# SPDX-License-Identifier: BSD-3-Clause\n" + "".join(f"{key}: {constants[value]}\n" for key, value in NAMES.items())


if __name__ == "__main__":
    Path(sys.argv[2]).write_text(render(Path(sys.argv[1]).read_text()), encoding="utf-8")
