#
# Shared build rules for the BSN-N52 Zephyr projects (nRF Connect SDK v3.4.0 + west), same scheme as
# firmware/N54/common/west.mak.
#
# A project makefile sets OPTS (the -D options for CMake), then includes this file. The options are compared with
# the last build: if any changed, the build directory is wiped (west build -p always), because Kconfig fragments
# are only picked up on a fresh configure.
#
# Targets:
#   all (default)  configure and build -> build/zephyr/zephyr.hex
#   flash          program with nrfutil through the J-Link, then reset and run
#   menuconfig     interactive Kconfig for the current build
#   clean
#   + the probe targets in flash.mak (jflash, stflash, jerase, jstatus, soc, recover)
#
# Recipes use POSIX shell commands: on Windows, run make from Git Bash.
#

BUILD := build
HEX   := $(BUILD)/zephyr/zephyr.hex
BOARD := bsn_n52/nrf52805

include $(dir $(lastword $(MAKEFILE_LIST)))flash.mak

# The custom board lives in firmware/N52/boards. CMake on Windows wants a C:/ path, not /c/.
BOARD_ROOT := $(shell cd "$(N52_DIR)" && pwd -W)

ALL_OPTS := -DBOARD_ROOT=$(BOARD_ROOT) $(OPTS)
LAST     := $(strip $(shell cat $(BUILD)/.bsn_opts 2>/dev/null))
PRISTINE := $(if $(filter-out $(LAST),$(strip $(ALL_OPTS)))$(filter-out $(strip $(ALL_OPTS)),$(LAST)),always,auto)

.PHONY: all flash menuconfig clean

# If CMake has to re-run in an existing build directory, the NCS nrf_security Kconfig strings can come back
# mis-quoted ("malformed string literal ... MBEDTLS_CONFIG_FILE") and configure aborts. A pristine build always
# works, so fall back to one.
all:
	$(NCS_ENV) && { west build -b $(BOARD) -d $(BUILD) -p $(PRISTINE) --no-sysbuild . -- $(ALL_OPTS) || \
	    west build -b $(BOARD) -d $(BUILD) -p always --no-sysbuild . -- $(ALL_OPTS); }
	@echo '$(strip $(ALL_OPTS))' > $(BUILD)/.bsn_opts

flash: all
	$(NCS_ENV) && west flash -d $(BUILD) -r nrfutil

menuconfig:
	$(NCS_ENV) && west build -d $(BUILD) -t menuconfig

clean:
	rm -rf $(BUILD)
