#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Build the seL4 kernel in the verified configuration ARM_bcm2837_verified
# and check that the generated configuration still matches it.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
build_dir="${1:-${repo_root}/build/kernel-verified}"
sel4_dir="${repo_root}/vendor/seL4"
cross_prefix="${CROSS_COMPILER_PREFIX:-arm-linux-gnueabi-}"

if [[ ! -f "${sel4_dir}/configs/ARM_bcm2837_verified.cmake" ]]; then
    printf 'vendor/seL4 is missing; run: git submodule update --init --depth 1\n' >&2
    exit 1
fi

rm -rf -- "${build_dir}"
cmake -S "${sel4_dir}" -B "${build_dir}" -G Ninja \
    -DCROSS_COMPILER_PREFIX="${cross_prefix}" \
    -DCMAKE_TOOLCHAIN_FILE="${sel4_dir}/gcc.cmake" \
    -C "${sel4_dir}/configs/ARM_bcm2837_verified.cmake"
ninja -C "${build_dir}" kernel.elf kernel_all_pp_wrapper

cache="${build_dir}/CMakeCache.txt"
expect() {
    local name="$1" value="$2" actual
    actual="$(sed -n "s/^${name}:[A-Z]*=//p" "${cache}")"
    if [[ "${actual}" != "${value}" ]]; then
        printf 'Configuration mismatch: %s=%s (expected %s)\n' "${name}" "${actual}" "${value}" >&2
        exit 1
    fi
}
expect KernelPlatform bcm2837
expect KernelSel4Arch aarch32
expect KernelVerificationBuild ON
expect KernelBinaryVerificationBuild ON
expect KernelMaxNumNodes 1
expect KernelAArch32FPUEnableContextSwitch OFF
expect KernelPrinting OFF
expect KernelIsMCS OFF

file "${build_dir}/kernel.elf"
sha256sum "${build_dir}/kernel.elf"
size_bytes="$(stat -c %s "${build_dir}/kernel.elf")"
printf 'kernel.elf: %s bytes\n' "${size_bytes}"
