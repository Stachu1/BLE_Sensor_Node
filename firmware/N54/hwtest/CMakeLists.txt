# BSN-N54 bring-up self-test. See ../README.md.
cmake_minimum_required(VERSION 3.20.0)

include(${CMAKE_CURRENT_LIST_DIR}/../common/bsn_common.cmake)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(bsn_n54_hwtest)

target_sources(app PRIVATE src/hwtest.c)
bsn_common_sources(${BSN_COMMON_DIR}/bsn_vdd.c ${BSN_COMMON_DIR}/hdc2010.c ${BSN_COMMON_DIR}/shtc3.c)
