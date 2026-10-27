# BSN-N54 BLE temperature/humidity broadcaster. See ../README.md.
cmake_minimum_required(VERSION 3.20.0)

set(SENSOR_S 10 CACHE STRING "Sensor period in s (0: read once at boot)")
set(ADV_MS 1000 CACHE STRING "Advertising interval in ms")
set(ADV 1 CACHE STRING "0: start the BLE stack but never advertise")

include(${CMAKE_CURRENT_LIST_DIR}/../common/bsn_common.cmake)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(bsn_n54_ble_sensor)

target_sources(app PRIVATE src/app_main.c src/bthome.c)
bsn_common_sources(${BSN_COMMON_DIR}/bsn_vdd.c ${BSN_COMMON_DIR}/hdc2010.c ${BSN_COMMON_DIR}/shtc3.c)
target_compile_definitions(app PRIVATE
  SENSOR_PERIOD_S=${SENSOR_S} ADV_INTERVAL_MS=${ADV_MS} ADV_ENABLE=${ADV})
