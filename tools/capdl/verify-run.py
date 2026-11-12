#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Classify a complete QEMU transcript; markers alone cannot hide an exit error."""
from pathlib import Path
import sys

REQUEST = "MSD-seL4 capdl: serial got badge 1 from client"
REPLY = "MSD-seL4 capdl: client checked reply"
FAULT = "MSD-seL4 capdl: client faulted at 0x3f201000"


def verify(text, mode, status):
    lines = text.replace("\r", "").splitlines()
    expected = [REQUEST, REPLY] + ([FAULT] if mode == "negative" else [])
    return (status == 124 and lines == expected and mode in {"positive", "negative"})


if __name__ == "__main__":
    ok = verify(Path(sys.argv[1]).read_text(), sys.argv[2], int(sys.argv[3]))
    print("qemu-capdl: passed (QEMU raspi3b only; not hardware)" if ok else "qemu-capdl: FAILED")
    sys.exit(0 if ok else 1)
