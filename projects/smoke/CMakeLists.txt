# SPDX-License-Identifier: BSD-3-Clause
# Minimal root task for the QEMU smoke test. The kernel uses the verified
# configuration ARM_bcm2837_verified without changes.
cmake_minimum_required(VERSION 3.16.0)
project(msd-sel4-smoke NONE)

get_filename_component(repo_root "${CMAKE_CURRENT_LIST_DIR}/../.." REALPATH)
set(KERNEL_PATH "${repo_root}/vendor/seL4" CACHE PATH "")
list(APPEND CMAKE_MODULE_PATH "${repo_root}/vendor/musllibc" "${repo_root}/vendor/sel4runtime")

include("${repo_root}/vendor/seL4/configs/ARM_bcm2837_verified.cmake")
set(ElfloaderImage "elf" CACHE STRING "" FORCE)
set(CMAKE_BUILD_TYPE "Release" CACHE STRING "")
set(LibSel4FunctionAttributes "public" CACHE STRING "" FORCE)

include("${repo_root}/vendor/seL4_tools/cmake-tool/base.cmake")
# The elfloader links the cpio target from util_libs.
add_subdirectory("${repo_root}/vendor/util_libs/libcpio" libcpio)
find_package(sel4runtime REQUIRED)
sel4runtime_import_project()
include(rootserver)

add_executable(smoke main.c)
target_compile_options(smoke PRIVATE -Wall -Wextra -Werror)
target_link_libraries(smoke PRIVATE sel4runtime sel4)
DeclareRootserver(smoke)
