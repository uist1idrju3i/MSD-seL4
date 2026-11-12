# SPDX-License-Identifier: BSD-3-Clause
"""Strict, bounded AArch32 system declarations; no capDL emission here."""

from pathlib import Path, PurePosixPath
import re
import tomllib

PAGE = 4096
RIGHTS = ("read", "write", "grant", "grantreply")
NAME = re.compile(r"[a-z][a-z0-9_]{0,47}\Z")
KINDS = {"endpoint", "notification", "frame", "region", "device"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, required, optional=()):
    require(isinstance(value, dict), "expected a table")
    require(set(required) <= value.keys(), f"missing keys: {set(required) - value.keys()}")
    require(value.keys() <= set(required) | set(optional), f"unknown keys: {value.keys() - set(required) - set(optional)}")


def integer(value, low, high, label):
    require(type(value) is int and low <= value <= high, f"invalid {label}: {value!r}")
    return value


def name(value):
    require(isinstance(value, str) and NAME.fullmatch(value), f"invalid name: {value!r}")
    return value


def text(value):
    require(isinstance(value, str) and value.strip() and not any(c in value for c in "\n\r|"), "invalid reason")


def extent(start, size):
    integer(start, PAGE, 0xfffff000, "address")
    integer(size, PAGE, PAGE * 4096, "size")
    require(start % PAGE == 0 and size % PAGE == 0 and start + size <= 2**32, "unaligned or overflowing range")


def overlaps(a, size, b, end):
    return a < end and b < a + size


def frames(obj):
    count = obj.get("size", PAGE) // PAGE
    return [f"o_{obj['name']}" if count == 1 else f"o_{obj['name']}_{i}" for i in range(count)]


def validate(system):
    keys(system, {"version", "kernel_printing", "objects", "pds"})
    require(type(system["version"]) is int and system["version"] == 1, "unsupported schema version")
    require(type(system["kernel_printing"]) is bool, "kernel_printing must be explicit")
    require(isinstance(system["objects"], list) and len(system["objects"]) <= 128, "invalid objects")
    require(isinstance(system["pds"], list) and 1 <= len(system["pds"]) <= 16, "expected 1..16 PDs")
    names = set()
    objects = {}
    physical = []
    for obj in system["objects"]:
        keys(obj, {"name", "type", "reason"}, {"size", "paddr", "dma_capable", "dma", "allow_grant"})
        n = name(obj["name"])
        require(n not in names, f"duplicate name: {n}")
        names.add(n)
        text(obj["reason"])
        kind = obj["type"]
        require(isinstance(kind, str) and kind in KINDS, "unsupported object type (no untyped, CNode, TCB or IRQ)")
        allowed = {"name", "type", "reason"}
        if kind == "endpoint":
            allowed.add("allow_grant")
            require(type(obj.get("allow_grant", False)) is bool, "allow_grant must be boolean")
        if kind in {"frame", "region", "device"}:
            allowed.add("size")
            require("size" in obj, "frame size must be explicit")
            extent(PAGE, obj["size"])
            if kind == "frame":
                require(obj["size"] == PAGE, "frame must be 4 KiB; use region for multiple frames")
        if kind == "device":
            allowed |= {"paddr", "dma_capable", "dma"}
            require("paddr" in obj and "dma_capable" in obj, "device needs paddr and dma_capable")
            extent(obj["paddr"], obj["size"])
            require(type(obj["dma_capable"]) is bool, "dma_capable must be boolean")
            a, size = obj["paddr"], obj["size"]
            reserved = [(0x3f00b000, 0x3f00c000), (0x40000000, 0x40001000)]
            if system["kernel_printing"]:
                reserved += [(0x3f201000, 0x3f202000), (0x3f215000, 0x3f216000)]
            require(not any(overlaps(a, size, b, e) for b, e in reserved), "device overlaps kernel-owned device")
            require(not any(overlaps(a, size, b, e) for b, e in physical), "overlapping device declarations")
            physical.append((a, a + size))
            require(obj["dma_capable"] or (a == 0x3f201000 and size == PAGE),
                    "only the reviewed polling PL011 page may deny DMA")
            require(obj.get("dma") == "all-memory" if obj["dma_capable"] else "dma" not in obj,
                    'DMA-capable devices require dma = "all-memory"')
        require(obj.keys() <= allowed, f"keys do not apply to {kind}")
        objects[n] = obj
    expanded = [target for obj in objects.values() for target in
                (frames(obj) if "size" in obj else [f"o_{obj['name']}"])]
    require(len(expanded) == len(set(expanded)), "expanded object name collision")
    require(len(expanded) <= 4096, "too many static frames/objects")
    for pd in system["pds"]:
        keys(pd, {"name", "elf", "stack", "ipc_buffer", "priority", "reason", "grants"}, {"fault_endpoint"})
        n = name(pd["name"])
        require(n not in names, f"duplicate name: {n}")
        names.add(n)
        text(pd["reason"])
        path = pd["elf"]
        require(isinstance(path, str) and re.fullmatch(r"[A-Za-z0-9_./-]+\.elf", path), "invalid ELF path")
        require(not PurePosixPath(path).is_absolute() and all(p not in {"", ".", ".."} for p in path.split("/")), "ELF must be relative without traversal")
        keys(pd["stack"], {"vaddr", "size"})
        extent(pd["stack"]["vaddr"], pd["stack"]["size"])
        extent(pd["ipc_buffer"], PAGE)
        require(pd["stack"]["vaddr"] + pd["stack"]["size"] <= 0x80000000 and pd["ipc_buffer"] < 0x80000000,
                "private virtual memory must be below 2 GiB")
        integer(pd["priority"], 0, 255, "priority")
        require(isinstance(pd["grants"], list) and len(pd["grants"]) <= 256, "invalid grants")
        occupied = [(pd["stack"]["vaddr"], pd["stack"]["vaddr"] + pd["stack"]["size"])]
        require(not overlaps(pd["ipc_buffer"], PAGE, *occupied[0]), "IPC buffer overlaps stack")
        occupied.append((pd["ipc_buffer"], pd["ipc_buffer"] + PAGE))
        slots, labels = set(), set()
        for grant in pd["grants"]:
            keys(grant, {"name", "slot", "object", "type", "rights", "reason"}, {"badge", "vaddr"})
            label = name(grant["name"])
            require(label not in labels, "duplicate slot name")
            labels.add(label)
            slot = integer(grant["slot"], 1, 4095, "slot")
            require(isinstance(grant["object"], str) and grant["object"] in objects, "unknown grant object")
            obj = objects[grant["object"]]
            require(grant["type"] == obj["type"], "grant type mismatch")
            rights = grant["rights"]
            require(isinstance(rights, list) and rights and all(isinstance(r, str) and r in RIGHTS for r in rights), "invalid explicit rights")
            require(len(set(rights)) == len(rights), "duplicate right")
            text(grant["reason"])
            if obj["type"] == "endpoint":
                require(obj.get("allow_grant", False) or not ({"grant", "grantreply"} & set(rights)), "endpoint grant rights not allowed")
            else:
                require(set(rights) <= {"read", "write"}, "grant rights only apply to endpoints")
            count = obj.get("size", PAGE) // PAGE
            for index in range(slot, slot + count):
                require(index <= 4095 and index not in slots, "duplicate or overflowing slot")
                slots.add(index)
            if obj["type"] in {"frame", "region", "device"}:
                require("vaddr" in grant and "badge" not in grant, "frame grant needs vaddr and no badge")
                extent(grant["vaddr"], obj["size"])
                require(grant["vaddr"] + obj["size"] <= 0x80000000, "grant mapping must be below 2 GiB")
                require(not any(overlaps(grant["vaddr"], obj["size"], b, e) for b, e in occupied), "overlapping PD mappings")
                occupied.append((grant["vaddr"], grant["vaddr"] + obj["size"]))
            else:
                require("vaddr" not in grant, "endpoint/notification cannot have vaddr")
                integer(grant.get("badge", 0), 0, 0xfffffff, "badge")
        if "fault_endpoint" in pd:
            candidates = [g for g in pd["grants"] if g["name"] == pd["fault_endpoint"]]
            require(len(candidates) == 1 and candidates[0]["type"] == "endpoint", "fault endpoint must name an endpoint slot")
            rights = set(candidates[0]["rights"])
            require("write" in rights and bool(rights & {"grant", "grantreply"}), "fault endpoint needs write and grant/grantreply")
    return system


def load(path):
    with Path(path).open("rb") as stream:
        return validate(tomllib.load(stream))
