#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
build="${1:?usage: build.sh <build-dir> <positive|negative|silent>}"
mode="${2:?test mode required}"
case "${mode}" in positive) number=0 ;; negative) number=1 ;; silent) number=2 ;; *) exit 2 ;; esac
mkdir -p "${build}"
build="$(cd "${build}" && pwd)"
python3 "${repo}/projects/capdl/configure.py" "${repo}/projects/capdl/system.toml" "${build}/config"
"${repo}/tools/prepare-sel4-source.sh" "${build}/sel4-src"
cmake -S "${repo}/projects/capdl" -B "${build}" -G Ninja \
    -DKERNEL_PATH="${build}/sel4-src" -DCAPDL_TEST_MODE="${number}" \
    -DCROSS_COMPILER_PREFIX=arm-linux-gnueabi- \
    -DCMAKE_TOOLCHAIN_FILE="${repo}/vendor/seL4/gcc.cmake"
ninja -C "${build}" serial client

include_dirs=(kernel/gen_config libsel4/arch_include/arm libsel4/autoconf
    libsel4/gen_config libsel4/include libsel4/sel4_arch_include/aarch32
    sel4-src/libsel4/arch_include/arm sel4-src/libsel4/include
    sel4-src/libsel4/mode_include/32 sel4-src/libsel4/sel4_arch_include/aarch32
    sel4-src/libsel4/sel4_plat_include/bcm2837)
includes=()
for dir in "${include_dirs[@]}"; do includes+=("-I${build}/${dir}"); done
printf '#include <sel4/sel4.h>\n' | arm-linux-gnueabi-gcc "${includes[@]}" -E -dM -xc - > "${build}/macros.txt"
python3 "${repo}/projects/capdl/object-sizes.py" "${build}/macros.txt" "${build}/object-sizes.yaml"
python3 "${repo}/tools/capdl/generate.py" "${repo}/projects/capdl/system.toml" \
    --elf-dir "${build}" --cdl "${build}/system.cdl"
python3 "${repo}/tools/capdl/check.py" "${repo}/projects/capdl/system.toml" \
    --elf-dir "${build}" --cdl "${build}/system.cdl" --object-sizes "${build}/object-sizes.yaml" \
    --table "${repo}/research/sel4/serial-client-capabilities.md"
parse-capDL --object-sizes="${build}/object-sizes.yaml" --json="${build}/spec.json" "${build}/system.cdl"

export CARGO_HOME="${repo}/build/capdl-rust/cargo-home"
export CARGO_TARGET_DIR="${repo}/build/capdl-rust/target"
export RUSTUP_TOOLCHAIN
RUSTUP_TOOLCHAIN="$(python3 -c 'import sys,tomllib; print(tomllib.load(open(sys.argv[1],"rb"))["toolchain"]["channel"])' "${repo}/projects/rust-smoke/rust-toolchain.toml")"
mkdir -p "${CARGO_HOME}"
cargo fetch --locked --manifest-path "${repo}/projects/rust-smoke/Cargo.toml"
manifest="$(cargo metadata --locked --format-version 1 --manifest-path "${repo}/projects/rust-smoke/Cargo.toml" |
    python3 -c 'import json,sys; print(next(p["manifest_path"] for p in json.load(sys.stdin)["packages"] if p["name"]=="sel4"))')"
rust_sel4="$(cd "$(dirname "${manifest}")/../.." && pwd)"
SEL4_INCLUDE_DIRS="$(printf "${build}/%s:" "${include_dirs[@]}")"
export SEL4_INCLUDE_DIRS="${SEL4_INCLUDE_DIRS%:}"
cargo build --locked --release --manifest-path "${rust_sel4}/Cargo.toml" -p sel4-capdl-initializer \
    -Z build-std=core,alloc,compiler_builtins -Z build-std-features=compiler-builtins-mem \
    -Z json-target-spec --target "${rust_sel4}/support/targets/armv7a-sel4-roottask-minimal.json"
cargo build --locked --release --manifest-path "${rust_sel4}/Cargo.toml" -p sel4-capdl-initializer-add-spec
arm-linux-gnueabi-strip --strip-debug "${CARGO_TARGET_DIR}/armv7a-sel4-roottask-minimal/release/sel4-capdl-initializer.elf" -o "${build}/initializer-stripped.elf"
"${CARGO_TARGET_DIR}/release/sel4-capdl-initializer-add-spec" \
    --initializer-elf "${build}/initializer-stripped.elf" --spec-json "${build}/spec.json" \
    --fill-dir "${build}" --object-names-level 2 --initializer-verbosity 0 --out-file "${build}/capdl_root"
ninja -C "${build}"
cmp "${build}/capdl_root" "${build}/elfloader-tool/rootserver"
for setting in KernelPlatform=bcm2837 KernelSel4Arch=aarch32 KernelVerificationBuild=ON \
    KernelBinaryVerificationBuild=ON KernelMaxNumNodes=1 KernelPrinting=OFF \
    KernelAArch32FPUEnableContextSwitch=OFF KernelIsMCS=OFF KernelArmTLSReg=tpidru \
    KernelIPCBufferLocation=threadID_register; do
    grep -Eqx "${setting%%=*}:[A-Z_]+=${setting#*=}" "${build}/CMakeCache.txt" ||
        { echo "error: unexpected configuration ${setting}" >&2; exit 1; }
done
image="${build}/images/capdl_root-image-arm-bcm2837"
entry="$(readelf -h "${image}" | awk '/Entry point address/ {print $4}')"
aarch64-linux-gnu-gcc -nostdlib -static -Wl,-Ttext=0x80000 -Wl,--build-id=none \
    -DELFLOADER_ENTRY="${entry}" -o "${build}/aarch32-entry.elf" "${repo}/projects/smoke/qemu/aarch32-entry.S"
sha256sum "${build}/serial.elf" "${build}/client.elf" "${build}/kernel/kernel.elf" \
    "${build}/capdl_root" "${image}" "${build}/aarch32-entry.elf" > "${build}/binaries.sha256"
printf '%s\n' "${mode}" > "${build}/mode.txt"
