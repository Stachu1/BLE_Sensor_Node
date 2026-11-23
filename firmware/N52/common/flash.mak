#
# Probe targets shared by every BSN-N52 project (Zephyr apps through west.mak, and the bare-metal ble_beacon_min).
# The including makefile defines HEX (the image to program) and an `all` target that builds it.
#
# Targets:
#   jflash     program HEX with a SEGGER J-Link (JLink.exe command file), verify, reset and run
#   jerase     full chip erase with a J-Link
#   jstatus    J-Link: show VTref, halt, dump registers, resume
#   stflash    program HEX with an ST-Link through pyocd (python -m pip install pyocd), untested on this board
#   soc        does the SoC answer on SWD? (DAP ID, FICR, UICR, expected BLE address). PROBE=stlink for an ST-Link
#   recover    nrfutil device recover: full erase and lift APPROTECT (needs a J-Link)
#
# The J-Link and ST-Link paths go through the same probe code as hwtest.py where possible. JLINK_SPEED sets the SWD
# speed in kHz. After any SWD access the nRF52 only emulates System OFF: unplug the probe and power-cycle the board
# before measuring current.
#

N52_DIR     := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
NCS_ENV     := . "$(N52_DIR)/tools/ncs-env.sh"
HWTEST_PY   := python "$(N52_DIR)/hwtest/scripts/hwtest.py"
JLINK_SPEED ?= 2000
PROBE       ?= jlink
JLINK_CMD    = JLink.exe -NoGui 1 -ExitOnError 1 -Device nRF52805_xxAA -If SWD -Speed $(JLINK_SPEED) -AutoConnect 1 -CommandFile

# Included before the project's own rules: keep `all` the default goal
.DEFAULT_GOAL := all

.PHONY: jflash jerase jstatus stflash soc recover

# r + h before loadfile: a target in System OFF or WFE is woken by the reset. loadfile erases the touched pages,
# programs and verifies.
jflash: all
	@printf 'r\nh\nloadfile %s\nr\ng\nexit\n' "$(HEX)" > $(BUILD)/jflash.jlink
	$(NCS_ENV) && $(JLINK_CMD) $(BUILD)/jflash.jlink

jerase:
	@mkdir -p $(BUILD)
	@printf 'erase\nexit\n' > $(BUILD)/jerase.jlink
	$(NCS_ENV) && $(JLINK_CMD) $(BUILD)/jerase.jlink

jstatus:
	@mkdir -p $(BUILD)
	@printf 'st\nh\nregs\ng\nexit\n' > $(BUILD)/jstatus.jlink
	$(NCS_ENV) && $(JLINK_CMD) $(BUILD)/jstatus.jlink

# Plain python (not the NCS one): pyocd is installed there
stflash: all
	$(HWTEST_PY) flash "$(HEX)" --probe stlink

soc:
	$(HWTEST_PY) soc --probe $(PROBE)

recover:
	$(NCS_ENV) && nrfutil device recover
