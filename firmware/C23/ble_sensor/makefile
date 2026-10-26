#
# BSN-C23 BLE temperature/humidity broadcaster. See ../README.md.
#
# Stack sources and flags follow the SDK basic_ble example.
#
include ../imports.mak

NAME       := bsn_c23_ble_sensor
SYSCFG     := ble_sensor.syscfg
LINKER_CMD := cc2340_freertos.cmd

BLE      := $(SDK_DIR)/source/ti/ble
LIB_OPT  := $(BLE)/stack_util/lib_opt/src

SRCS := app_main.c bthome.c main_freertos.c osal_icall_ble.c \
    $(COMMON_DIR)/bsn_log.c $(COMMON_DIR)/hdc2010.c $(COMMON_DIR)/shtc3.c \
    $(BLE)/app_util/framework/src/bleapputil_task.c \
    $(BLE)/app_util/framework/src/bleapputil_init.c \
    $(BLE)/app_util/framework/src/bleapputil_process.c \
    $(BLE)/app_util/framework/src/bleapputil_stack_callbacks.c \
    $(BLE)/app_util/framework/src/bleapputil_timers.c \
    $(BLE)/app_util/config/src/ble_user_config.c \
    $(BLE)/app_util/config/src/hci_supported_cmd.c \
    $(BLE)/app_util/common/src/util.c \
    $(BLE)/stack_util/lib_opt/rom_init.c \
    $(BLE)/stack_util/icall/app/src/icall.c \
    $(BLE)/stack_util/icall/app/src/icall_user_config.c \
    $(BLE)/stack_util/icall/app/src/icall_POSIX.c \
    $(BLE)/stack_util/health_toolkit/src/debugInfo.c \
    $(BLE)/stack_util/health_toolkit/src/ble_sys_stat.c \
    $(SDK_DIR)/source/ti/common/nv/crc.c \
    $(SDK_DIR)/source/ti/common/nv/nvocmp.c \
    $(wildcard $(LIB_OPT)/ctrl_opt_*.c) \
    $(wildcard $(LIB_OPT)/host_opt_*.c)

CFLAGS := \
    -DICALL_NO_APP_EVENTS \
    -DNVOCMP_NVPAGES=6 -DNVOCMP_POSIX_MUTEX -DNVOCMP_NWSAMEITEM=1 \
    "-I$(SDK_DIR)/source/ti" \
    "-I$(SDK_DIR)/source/ti/common/cc26xx" \
    "-I$(SDK_DIR)/source/ti/drivers/rcl" \
    "@$(BLE)/stack_util/config/build_components.opt" \
    "@$(BLE)/stack_util/config/factory_config.opt" \
    "-I$(SDK_DIR)/source/third_party/mbedtls/include" \
    "-I$(SDK_DIR)/source/third_party/mbedtls/ti" \
    -DMBEDTLS_CONFIG_FILE=\"configs/config-hsm.h\" \
    -DMBEDTLS_PSA_CRYPTO_CONFIG_FILE=\"configs/config-psa-crypto-hsm.h\"

# Build-time options, mainly for current measurements:
#   make LOG=0 SENSOR_S=0 ADV_MS=100 TX_DBM=0
#   LOG=0       compile out all UART logging
#   SENSOR_S    sensor period in s; 0 = read once at boot, then never wake for it
#   ADV_MS      advertising interval in ms (20..10240); 0 = keep ble_sensor.syscfg
#   TX_DBM      TX power, rounded down to the PA table
#   ADV=0       start the BLE stack but never advertise
LOG      ?= 1
SENSOR_S ?= 10
ADV_MS   ?= 0
TX_DBM   ?= 0
ADV      ?= 1
CFLAGS += -DBSN_LOG_ENABLE=$(LOG) -DSENSOR_PERIOD_S=$(SENSOR_S) -DADV_INTERVAL_MS=$(ADV_MS) \
          -DADV_TX_DBM=$(TX_DBM) -DADV_ENABLE=$(ADV)

# Rebuild whatever depends on the options when they change
PARAMS := $(LOG) $(SENSOR_S) $(ADV_MS) $(TX_DBM) $(ADV)
$(shell mkdir -p build && (echo '$(PARAMS)' | cmp -s - build/params || echo '$(PARAMS)' > build/params))

include ../rules.mak

$(OBJ)/app_main.obj $(OBJ)/bsn_log.obj: build/params
