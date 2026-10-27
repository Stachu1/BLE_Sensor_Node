# Included by every app's CMakeLists.txt before find_package(Zephyr).
# Selects the board, adds the BSN-N54-A devicetree overlay and the shared sources.
#
# Build options (passed as -D by the app makefiles):
#   LOG=0   no UART: CONFIG_SERIAL and CONSOLE off, LOG() compiled out (use for current measurements)
#   RTT=1   console over SEGGER RTT (J-Link) instead of UART20
#   LFCLK=rc    LF clock from the internal RC (X2 not fitted, default); LFCLK=xtal uses X2

set(BSN_COMMON_DIR ${CMAKE_CURRENT_LIST_DIR})

if(NOT DEFINED BOARD)
  set(BOARD nrf54l15dk/nrf54l05/cpuapp)
endif()

list(APPEND EXTRA_DTC_OVERLAY_FILE ${BSN_COMMON_DIR}/bsn_n54.overlay)
list(APPEND EXTRA_CONF_FILE ${BSN_COMMON_DIR}/bsn_n54.conf)
if(DEFINED LOG AND LOG EQUAL 0)
  list(APPEND EXTRA_CONF_FILE ${BSN_COMMON_DIR}/log_off.conf)
endif()
if(DEFINED RTT AND RTT EQUAL 1 AND NOT (DEFINED LOG AND LOG EQUAL 0))
  list(APPEND EXTRA_CONF_FILE ${BSN_COMMON_DIR}/rtt.conf)
endif()
# HFXO_CL_FF=<fF>: X1 internal load capacitance for crystal trimming, 4000..17000 in 250 fF steps
# (more capacitance = lower frequency). Overrides the value in bsn_n54.overlay.
if(DEFINED HFXO_CL_FF AND NOT HFXO_CL_FF STREQUAL "")
  file(WRITE ${CMAKE_BINARY_DIR}/hfxo_cl.overlay
       "&hfxo {\n\tload-capacitance-femtofarad = <${HFXO_CL_FF}>;\n};\n")
  list(APPEND EXTRA_DTC_OVERLAY_FILE ${CMAKE_BINARY_DIR}/hfxo_cl.overlay)
endif()
# DCDC=0: main regulator in LDO mode instead of the DC/DC (for checking L1 and the DC/DC)
if(DEFINED DCDC AND DCDC EQUAL 0)
  file(WRITE ${CMAKE_BINARY_DIR}/ldo.overlay
       "&vregmain {\n\tregulator-initial-mode = <NRF5X_REG_MODE_LDO>;\n};\n")
  list(APPEND EXTRA_DTC_OVERLAY_FILE ${CMAKE_BINARY_DIR}/ldo.overlay)
endif()
if(NOT DEFINED LFCLK OR NOT LFCLK STREQUAL "xtal")
  list(APPEND EXTRA_CONF_FILE ${BSN_COMMON_DIR}/lfrc.conf)
endif()

# Call after find_package(Zephyr)
macro(bsn_common_sources)
  target_include_directories(app PRIVATE ${BSN_COMMON_DIR})
  target_sources(app PRIVATE ${ARGN})
  if(DEFINED LOG AND LOG EQUAL 0)
    target_compile_definitions(app PRIVATE BSN_LOG_ENABLE=0)
  endif()
  if(DEFINED LFCLK AND LFCLK STREQUAL "xtal")
    target_compile_definitions(app PRIVATE BSN_LFCLK_XTAL=1)
  endif()
endmacro()
