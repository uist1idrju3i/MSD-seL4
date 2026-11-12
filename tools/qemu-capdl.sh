#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build="${1:-${repo}/build/capdl-positive}"
mode="${2:-positive}"
run_id="${3:-run-$(date +%s)-$$}"
[[ "${run_id}" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
case "${mode}" in positive|negative|silent) ;; *) exit 2 ;; esac
timeout_s="${QEMU_TIMEOUT:-10}"
[[ "${timeout_s}" =~ ^[1-9][0-9]*$ ]] || exit 2
if [[ "${QEMU_CAPDL_SKIP_BUILD:-0}" != 1 ]]; then
    "${repo}/projects/capdl/build.sh" "${build}" "${mode}"
fi
build="$(cd "${build}" && pwd)"
test "$(cat "${build}/mode.txt")" = "${mode}"
sha256sum --check --status "${build}/binaries.sha256"
mkdir -p "${build}/runs"
run="${build}/runs/${run_id}"
mkdir "${run}"
image="${build}/images/capdl_root-image-arm-bcm2837"
set +e
timeout "${timeout_s}" qemu-system-aarch64 -M raspi3b -nographic -monitor none \
    -serial "file:${run}/pl011.log" -serial "file:${run}/aux.log" \
    -kernel "${build}/aarch32-entry.elf" -device "loader,file=${image}" > "${run}/qemu.log" 2>&1
status=$?
set -e
printf '%s\n' "${status}" > "${run}/exit-status.txt"
cat "${run}/pl011.log"
python3 "${repo}/tools/capdl/verify-run.py" "${run}/pl011.log" "${mode}" "${status}" | tee "${run}/result.txt"
