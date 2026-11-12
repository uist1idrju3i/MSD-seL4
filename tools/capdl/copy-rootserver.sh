#!/bin/sh
# SPDX-License-Identifier: BSD-3-Clause
# seL4_tools invokes this in place of strip, after add-spec.
set -eu
test "$#" -eq 3
test "$2" = -o
cp -- "$1" "$3"
