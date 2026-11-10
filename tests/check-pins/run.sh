#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
set -eu
repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"
exec python3 -m unittest discover -s "$repo_root/tests/check-pins" -p 'test_*.py' -v
