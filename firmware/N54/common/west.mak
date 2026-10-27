#
# Shared build rules for the BSN-N54 firmware projects (nRF Connect SDK v3.4.0 + west).
#
# A project makefile sets OPTS (the -D options for CMake, e.g. -DFREQ_MHZ=2440),
# then includes this file. The options are compared with the last build: if any
# changed, the build directory is wiped (west build -p always), because Kconfig
# fragments are only picked up on a fresh configure.
#
# Targets:
#   all (default)  configure and build -> build/zephyr/zephyr.hex
#   flash          program with nrfutil (needs a J-Link), then reset and run
#   recover        erase everything and lift the access-port protection (new or locked chips)
#   jflash         program with the SEGGER J-Link runner instead of nrfutil
#   menuconfig     interactive Kconfig for the current build
#   clean
#
# Recipes use POSIX shell commands: on Windows, run make from Git Bash.
#

BUILD   := build
BOARD   := nrf54l15dk/nrf54l05/cpuapp
NCS_ENV := . ../tools/ncs-env.sh
LOG     ?= 1
LFCLK   ?= rc
RTT     ?= 0

ALL_OPTS := -DLOG=$(LOG) -DLFCLK=$(LFCLK) -DRTT=$(RTT) $(if $(HFXO_CL_FF),-DHFXO_CL_FF=$(HFXO_CL_FF)) $(if $(DCDC),-DDCDC=$(DCDC)) $(OPTS)
LAST     := $(strip $(shell cat $(BUILD)/.bsn_opts 2>/dev/null))
PRISTINE := $(if $(filter-out $(LAST),$(strip $(ALL_OPTS)))$(filter-out $(strip $(ALL_OPTS)),$(LAST)),always,auto)

.PHONY: all flash recover jflash menuconfig clean

# If CMake has to re-run in an existing build directory, the NCS nrf_security Kconfig strings come
# back mis-quoted ("malformed string literal ... MBEDTLS_CONFIG_FILE") and configure aborts.
# A pristine build always works, so fall back to one.
all:
	$(NCS_ENV) && { west build -b $(BOARD) -d $(BUILD) -p $(PRISTINE) --no-sysbuild . -- $(ALL_OPTS) || \
	    west build -b $(BOARD) -d $(BUILD) -p always --no-sysbuild . -- $(ALL_OPTS); }
	@echo '$(strip $(ALL_OPTS))' > $(BUILD)/.bsn_opts

flash: all
	$(NCS_ENV) && west flash -d $(BUILD) -r nrfutil

recover:
	$(NCS_ENV) && nrfutil device recover

jflash: all
	$(NCS_ENV) && west flash -d $(BUILD) -r jlink

menuconfig:
	$(NCS_ENV) && west build -d $(BUILD) -t menuconfig

clean:
	rm -rf $(BUILD)
