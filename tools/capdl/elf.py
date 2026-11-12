# SPDX-License-Identifier: BSD-3-Clause
"""Read only static little-endian ARM ELF32 PT_LOADs, using the standard library."""

import struct

from schema import PAGE, require


def read(path):
    data = path.read_bytes()
    require(len(data) >= 52, "truncated ELF header")
    h = struct.unpack_from("<16sHHIIIIIHHHHHH", data)
    require(h[0][:7] == b"\x7fELF\x01\x01\x01" and h[1:4] == (2, 40, 1), "expected static ARM ELF32 little-endian executable")
    require(h[8] == 52 and h[9] == 32 and 0 < h[10] <= 128, "invalid ELF program header table")
    require(not h[7] & 0x400, "hard-float ELF unsupported")
    require(h[7] & 0xff000000 == 0x05000000 and h[4] % 4 == 0, "expected EABI5 ARM-state entry")
    require(h[5] + h[9] * h[10] <= len(data), "truncated program headers")
    pages, ranges = {}, []
    executable_entry = False
    for i in range(h[10]):
        kind, offset, addr, _physical, filesz, memsz, flags, align = struct.unpack_from("<8I", data, h[5] + i * 32)
        require(kind not in {2, 3}, "dynamic linking unsupported")
        if kind != 1 or memsz == 0:
            continue
        require(filesz <= memsz and offset + filesz <= len(data), "invalid ELF file extent")
        require(addr >= PAGE and addr + memsz <= 0x80000000 and memsz <= PAGE * 4096, "invalid ELF memory extent")
        require(flags & 4 and not flags & ~7, "PT_LOAD must be readable with known flags")
        require(align in {0, 1} or (align & (align - 1) == 0 and offset % align == addr % align), "invalid ELF alignment")
        require(not any(addr < end and start < addr + memsz for start, end in ranges), "overlapping ELF segments")
        ranges.append((addr, addr + memsz))
        executable_entry |= bool(flags & 1 and addr <= h[4] < addr + memsz)
        for base in range(addr // PAGE * PAGE, (addr + memsz + PAGE - 1) // PAGE * PAGE, PAGE):
            page = pages.setdefault(base, {"flags": 0, "fills": []})
            require(len(pages) <= 4096, "too many ELF pages")
            page["flags"] |= flags
            require(page["flags"] & 3 != 3, "writable executable ELF page")
            start, end = max(addr, base), min(addr + filesz, base + PAGE)
            if start < end:
                page["fills"].append((start - base, end - start, offset + start - addr))
    require(pages and len(pages) <= 4096 and executable_entry, "ELF needs executable entry and 1..4096 pages")
    return h[4], pages
