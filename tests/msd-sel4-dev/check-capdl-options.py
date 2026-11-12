#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Compare documented options with the pinned source copies (no network)."""

import argparse
from pathlib import Path
import re
import tomllib

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("capdl", type=Path)
parser.add_argument("rust_sel4", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
doc = (root / "research/sel4/capdl.md").read_text()
source = (args.capdl / "capDL-tool/Main.hs").read_text()
options = re.findall(r'Option\s+\[[^\]]*\]\s+\["([\w-]+)"\]', source)
assert options, "no parse-capDL options extracted"
missing = [name for name in options if f"`--{name}`" not in doc]
source = (args.rust_sel4 / "crates/sel4-capdl-initializer/add-spec/src/main.rs").read_text()
fields = re.findall(r'#\[arg\(long[^\n]*\)\]\n\s*pub (\w+):', source)
assert fields, "no add-spec options extracted"
missing += [name for name in fields if f"`--{name.replace('_', '-')}`" not in doc]
manifest = tomllib.loads((args.rust_sel4 / "crates/sel4-capdl-initializer/Cargo.toml").read_text())
missing += [name for name in manifest["features"] if f"`{name}`" not in doc]
assert not missing, f"undocumented options: {missing}"
print(f"ok - documented {len(options)} parse-capDL options, {len(fields)} add-spec options, "
      f"{len(manifest['features'])} initializer features; missing=0")
