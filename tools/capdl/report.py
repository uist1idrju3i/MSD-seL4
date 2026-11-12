# SPDX-License-Identifier: BSD-3-Clause
"""Render the declared authority, not an inferred runtime access policy."""

from schema import RIGHTS, frames


def render(system):
    objects = {o["name"]: o for o in system["objects"]}
    lines = ["<!-- SPDX-License-Identifier: BSD-3-Clause -->", "# system の capability 表（自動生成）", "",
             "`tools/capdl/generate.py` で生成します。手では編集しません。", "",
             "| PD | slot（名前） | object | type | rights | badge | device / vaddr | DMA | 理由 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for pd in sorted(system["pds"], key=lambda p: p["name"]):
        for grant in sorted(pd["grants"], key=lambda g: g["slot"]):
            obj = objects[grant["object"]]
            names = frames(obj) if obj["type"] in {"frame", "region", "device"} else [f"o_{obj['name']}"]
            for i, target in enumerate(names):
                device = f"0x{obj['paddr'] + i * 4096:08x}" if obj["type"] == "device" else "なし"
                if "vaddr" in grant:
                    device += f" / 0x{grant['vaddr'] + i * 4096:08x}"
                rights = ", ".join(r for r in RIGHTS if r in grant["rights"])
                badge = str(grant.get("badge", 0)) if obj["type"] in {"endpoint", "notification"} else "なし"
                lines.append(f"| {pd['name']} | {grant['slot'] + i} ({grant['name']}) | {target} | {obj['type']} | {rights} | {badge} | {device} | {obj.get('dma', 'なし')} | {grant['reason']} |")
        if not pd["grants"]:
            lines.append(f"| {pd['name']} | なし | なし | なし | なし | なし | なし | なし | {pd['reason']} |")
    return "\n".join(lines) + "\n"
