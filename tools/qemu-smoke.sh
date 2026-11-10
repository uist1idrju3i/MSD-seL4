#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Build the smoke root task with ARM_bcm2837_verified and boot it on QEMU
# raspi3b. Passing this test does not show that real CardputerZero boots.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${1:-${repo_root}/build/smoke}"
timeout_s="${QEMU_TIMEOUT:-30}"
cross_prefix="${CROSS_COMPILER_PREFIX:-arm-linux-gnueabi-}"

rm -rf "${build_dir}"
cmake -S "${repo_root}/projects/smoke" -B "${build_dir}" -G Ninja \
    -DKERNEL_PATH="${KERNEL_PATH:-${repo_root}/vendor/seL4}" \
    -DCROSS_COMPILER_PREFIX="${cross_prefix}" \
    -DCMAKE_TOOLCHAIN_FILE="${repo_root}/vendor/seL4/gcc.cmake"
ninja -C "${build_dir}"

image="${build_dir}/images/smoke-image-arm-bcm2837"
cache="${build_dir}/CMakeCache.txt"
for setting in KernelPlatform=bcm2837 KernelSel4Arch=aarch32 \
    KernelVerificationBuild=ON KernelMaxNumNodes=1 \
    KernelAArch32FPUEnableContextSwitch=OFF KernelIsMCS=OFF; do
    grep -Eqx "${setting%%=*}:[A-Z]+=${setting#*=}" "${cache}" ||
        { echo "error: ${setting} not set" >&2; exit 1; }
done

entry="$(readelf -h "${image}" | awk '/Entry point address/ {print $4}')"
aarch64-linux-gnu-gcc -nostdlib -static -Wl,-Ttext=0x80000 -Wl,--build-id=none \
    -DELFLOADER_ENTRY="${entry}" -o "${build_dir}/aarch32-entry.elf" \
    "${repo_root}/projects/smoke/qemu/aarch32-entry.S"

log="${build_dir}/pl011.log"
: >"${log}"
set +e
timeout "${timeout_s}" qemu-system-aarch64 -M raspi3b -nographic -monitor none \
    -serial "file:${log}" -serial "file:${build_dir}/aux.log" \
    -kernel "${build_dir}/aarch32-entry.elf" \
    -device "loader,file=${image}"
set -e
cat "${log}"
grep -q 'MSD-seL4 smoke: OK' "${log}"
echo "qemu-smoke: passed (QEMU raspi3b only; not a hardware result)"
