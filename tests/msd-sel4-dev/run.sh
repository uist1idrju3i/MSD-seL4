#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# Check that the development image works for host UIDs other than 1000.
set -eu
image="${MSD_SEL4_DEV_IMAGE:-msd-sel4-dev:local}"
repo_root="$(CDPATH='' cd "$(dirname "$0")/../.." && pwd)"

tag="$("$repo_root/docker/msd-sel4-dev" tag)"
case "$tag" in
	inputs-????????????????) printf 'ok - input tag %s\n' "$tag" ;;
	*) printf 'not ok - unexpected input tag %s\n' "$tag" >&2; exit 1 ;;
esac

for uid in 1000 1001 4242; do
	docker run --rm --user "$uid:$uid" --env HOME=/home/builder "$image" bash -euc '
		rustc --version >/dev/null
		cargo --version >/dev/null
		rustup toolchain list | grep -q "^nightly-2026-08-21"
		rustup +nightly-2026-08-21 component list --installed | grep -q "^rust-src"
		test -n "$(find /usr/lib -name "libclang*.so*" -print -quit)"
		arm-linux-gnueabi-gcc --version >/dev/null
		touch "$HOME/.write-test"
		cargo_home="$(mktemp -d)"
		CARGO_HOME="$cargo_home" cargo --version >/dev/null
	'
	printf 'ok - tools and HOME work as UID %s\n' "$uid"
done
printf 'All msd-sel4-dev tests passed.\n'
