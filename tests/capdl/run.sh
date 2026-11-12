#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
set -eu
repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"
python3 -m unittest discover -s "$repo_root/tests/capdl" -v
python3 "$repo_root/tools/capdl/check.py" "$repo_root/projects/capdl/system.toml" \
    --table "$repo_root/research/sel4/serial-client-capabilities.md"
