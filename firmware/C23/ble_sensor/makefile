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

include ../rules.mak
