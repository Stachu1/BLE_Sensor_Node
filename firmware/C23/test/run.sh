#!/bin/sh
# Builds and runs the host unit tests. Needs a host C compiler: CC=gcc, CC=clang
# or CC="zig cc" (pip install ziglang, then CC="python -m ziglang cc").
set -e
cd "$(dirname "$0")"
CC=${CC:-cc}
mkdir -p build
$CC -std=c99 -Wall -Wextra -O1 -Istubs -I../common -I../ble_sensor \
    test_host.c ../common/hdc2010.c ../common/shtc3.c ../ble_sensor/bthome.c \
    -o build/test_host
./build/test_host
