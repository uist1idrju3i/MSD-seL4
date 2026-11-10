#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# Check the glob matching of .github/scripts/changed-files.py.
set -eu
repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"
script="$repo_root/.github/scripts/changed-files.py"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

expect() {
	want="$1"; shift
	got="$(env -u GITHUB_OUTPUT python3 "$script" --files-from "$work/files" "$@" | tail -1 | cut -d' ' -f1)"
	if [ "$got" != "relevant=$want" ]; then
		printf 'not ok - %s for %s (got %s)\n' "$want" "$*" "$got" >&2
		exit 1
	fi
	printf 'ok - relevant=%s for %s\n' "$want" "$*"
}

printf 'research/sel4/rust.md\nREADME.md\n' > "$work/files"
expect false 'docker/**' 'tools/**' '**/*.sh' 'site/**'
printf 'tools/qemu-smoke.sh\n' > "$work/files"
expect true 'tools/**'
expect true '**/*.sh'
printf 'vendor/seL4\n' > "$work/files"
expect true 'vendor/**'
# Sample paths avoid docs/ so that check-links does not treat them as stale paths.
printf 'site/index.md\n' > "$work/files"
expect true 'site/**'
expect false 'sit/*'
printf 'site/a/b.md\n' > "$work/files"
expect false 'site/*'
expect true 'site/**'
printf 'All changed-files tests passed.\n'
