#
# Tool locations for the BSN-C23 firmware builds.
#
# Defaults match a standard Windows install under C:/ti (see README.md).
# Override any of these on the command line or in the environment, e.g.
#   make TI_ROOT=/home/me/ti SYSCONFIG_TOOL=/home/me/ti/sysconfig_1.26.4/sysconfig_cli.sh
# Paths must not contain spaces.
#

TI_ROOT             ?= C:/ti
SDK_DIR             ?= $(TI_ROOT)/simplelink_lowpower_f3_sdk_9_23_00_27
SYSCONFIG_TOOL      ?= $(TI_ROOT)/sysconfig_1.26.4/sysconfig_cli.bat
TICLANG_ARMCOMPILER ?= $(TI_ROOT)/ti-cgt-armllvm_4.0.4.LTS
CCS_ROOT            ?= $(TI_ROOT)/ccs2101/ccs
DSLITE              ?= $(CCS_ROOT)/ccs_base/DebugServer/bin/DSLite
# SEGGER J-Link Commander (V7.92 or later supports the CC2340R5)
JLINK               ?= C:/Program Files/SEGGER/JLink_V962/JLink.exe
JLINK_DEVICE        ?= CC2340R5
JLINK_SPEED         ?= 4000

FW_ROOT             := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
COMMON_DIR          := $(FW_ROOT)/common
CCXML               ?= $(FW_ROOT)/targetConfigs/CC2340R5_XDS110.ccxml
