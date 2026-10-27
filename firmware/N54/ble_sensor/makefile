#
# BSN-N54 BLE temperature/humidity broadcaster. See ../README.md.
#
#   make                                     1 s advertising, sensor every 10 s, 0 dBm, UART log
#   make LOG=0                               no UART (always use for current measurements)
#   make LOG=0 ADV_MS=100 TX_DBM=0           advertising interval (ms) and TX power (dBm)
#   make LOG=0 SENSOR_S=0                    read the sensor once at boot, then never wake for it
#   make LOG=0 SENSOR_S=0 ADV=0              start the BLE stack but never advertise
#
# Same option names as firmware/C23/ble_sensor. TX_DBM selects CONFIG_BT_CTLR_TX_PWR_PLUS_n /
# _MINUS_n, so it must be a step the nRF54L supports (e.g. -8, -4, 0, 4, 8).
#
SENSOR_S ?= 10
ADV_MS   ?= 1000
ADV      ?= 1
TX_DBM   ?= 0

TX_KCONFIG := $(if $(filter 0,$(TX_DBM)),0,$(if $(filter -%,$(TX_DBM)),MINUS_$(TX_DBM:-%=%),PLUS_$(TX_DBM)))

OPTS := -DSENSOR_S=$(SENSOR_S) -DADV_MS=$(ADV_MS) -DADV=$(ADV) -DCONFIG_BT_CTLR_TX_PWR_$(TX_KCONFIG)=y

include ../common/west.mak
