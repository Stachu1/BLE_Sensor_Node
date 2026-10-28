# BSN-N54 static current test. See ../README.md.
cmake_minimum_required(VERSION 3.20.0)

set(MODE standby CACHE STRING "standby | active | shutdown | bareoff | sensor | sensor_irq")
set(PERIOD_MS 1000 CACHE STRING "Sensor period for MODE=sensor")
set(HDC_AMM 5 CACHE STRING "HDC2010 auto-mode rate for MODE=sensor_irq (HDC2010_AMM_*)")
set(SHTC3_SLEEP 1 CACHE STRING "0: leave the SHTC3 idle after power-on")

include(${CMAKE_CURRENT_LIST_DIR}/../common/bsn_common.cmake)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(bsn_n54_pwrtest)

string(TOUPPER ${MODE} MODE_UC)
target_sources(app PRIVATE src/pwrtest.c)
bsn_common_sources(${BSN_COMMON_DIR}/bsn_vdd.c ${BSN_COMMON_DIR}/hdc2010.c ${BSN_COMMON_DIR}/shtc3.c)
target_compile_definitions(app PRIVATE
  PWR_MODE=MODE_${MODE_UC} PERIOD_MS=${PERIOD_MS} HDC_AMM=${HDC_AMM} SHTC3_SLEEP=${SHTC3_SLEEP})
