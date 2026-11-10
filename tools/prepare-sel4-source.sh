#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Copy vendor/seL4 to a build directory and apply patches/seL4/*.patch.
# vendor/seL4 itself is never modified. Fails if a patch is already part of
# the vendored seL4, so that fixed-upstream patches get removed.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
out_dir="${1:?usage: prepare-sel4-source.sh <output-dir>}"
sel4_dir="${repo_root}/vendor/seL4"

shopt -s nullglob
patches=("${repo_root}"/patches/seL4/*.patch)

rm -rf -- "${out_dir}"
mkdir -p -- "${out_dir}"
git -C "${sel4_dir}" archive --format=tar HEAD | tar -x -C "${out_dir}"

for p in "${patches[@]}"; do
    if patch -p1 -d "${sel4_dir}" --dry-run --reverse --force --batch -s <"${p}" >/dev/null 2>&1; then
        printf 'error: %s is already in vendor/seL4; remove the patch\n' "${p#"${repo_root}"/}" >&2
        exit 1
    fi
    patch -p1 -d "${out_dir}" --forward --batch -s <"${p}"
    printf 'applied %s %s\n' "$(sha256sum "${p}" | cut -d' ' -f1)" "${p#"${repo_root}"/}"
done | tee "${out_dir}/MSD_SEL4_PATCHES"
