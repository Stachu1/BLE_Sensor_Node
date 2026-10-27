# BSN-N54 continuous-wave RF test firmware. See ../README.md.
cmake_minimum_required(VERSION 3.20.0)

set(FREQ_MHZ 2440 CACHE STRING "Carrier frequency in MHz (2360..2500)")
set(PATTERN 0 CACHE STRING "0 TXIDLE carrier, 1 all-1 packets, 2 all-0 packets")
set(TX_DBM 0 CACHE STRING "RADIO TXPOWER in dBm (-40..+8, rounded down to the table)")

include(${CMAKE_CURRENT_LIST_DIR}/../common/bsn_common.cmake)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(bsn_n54_cwtest)

target_sources(app PRIVATE src/cwtest.c)
bsn_common_sources(${BSN_COMMON_DIR}/bsn_vdd.c)
target_compile_definitions(app PRIVATE CW_FREQ_MHZ=${FREQ_MHZ} CW_TX_DBM=${TX_DBM} CW_PATTERN=${PATTERN})
