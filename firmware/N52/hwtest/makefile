#
# BSN-N52 bring-up self-test. See ../README.md and ../BRINGUP.md.
#
#   make jflash            build, program and run (J-Link). stflash for an ST-Link
#   make run               flash with hwtest.py, wait for the tests, print the report (PROBE=stlink for an ST-Link)
#   make report            read the report from RAM of a running hwtest
#   make CARRIER=1 jflash  end in a continuous RF carrier (tone at 2440.25 MHz) instead of BLE advertising
#   make SKIP_DCDC=1       skip the DC/DC test (if a board boot-loops in it)
#
CARRIER   ?= 0
SKIP_DCDC ?= 0

OPTS := $(if $(filter 1,$(CARRIER)),-DEXTRA_CONF_FILE=carrier.conf) \
        $(if $(filter 1,$(SKIP_DCDC)),-DCONFIG_HWTEST_SKIP_DCDC=y)

include ../common/west.mak

.PHONY: run report

run: all
	$(HWTEST_PY) run --probe $(PROBE)

report:
	$(HWTEST_PY) report --probe $(PROBE)
