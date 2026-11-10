#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Build the Rust smoke root task against the libsel4 headers of a smoke build
# directory produced by tools/qemu-smoke.sh. Needs rustup and libclang.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
smoke_build="$(cd "${1:?usage: build.sh <smoke build dir>}" && pwd)"

include_dirs=(
    kernel/gen_config
    libsel4/arch_include/arm
    libsel4/autoconf
    libsel4/gen_config
    libsel4/include
    libsel4/sel4_arch_include/aarch32
    sel4-src/libsel4/arch_include/arm
    sel4-src/libsel4/include
    sel4-src/libsel4/mode_include/32
    sel4-src/libsel4/sel4_arch_include/aarch32
    sel4-src/libsel4/sel4_plat_include/bcm2837
)
SEL4_INCLUDE_DIRS="$(printf "${smoke_build}/%s:" "${include_dirs[@]}")"
export SEL4_INCLUDE_DIRS="${SEL4_INCLUDE_DIRS%:}"

cd "${here}"
cargo fetch --locked
sel4_manifest="$(cargo metadata --locked --format-version 1 |
    python3 -c 'import json,sys; print(next(p["manifest_path"] for p in json.load(sys.stdin)["packages"] if p["name"] == "sel4"))')"
target="$(dirname "${sel4_manifest}")/../../support/targets/armv7a-sel4-roottask.json"

cargo build --locked --release \
    -Z build-std=core,alloc,compiler_builtins \
    -Z build-std-features=compiler-builtins-mem \
    -Z json-target-spec \
    --target "${target}"
elf="${here}/target/armv7a-sel4-roottask/release/rust-smoke.elf"
sha256sum "${elf}"
