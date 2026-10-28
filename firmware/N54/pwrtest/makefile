#
# BSN-N54 static current test. See ../README.md.
#
#   make flash MODE=standby                 System ON idle forever: the sleep floor
#   make flash MODE=shutdown                System OFF: the board baseline
#   make flash MODE=bareoff                 System OFF with every GPIO reset to default first
#   make flash MODE=active                  CPU spinning at 128 MHz
#   make flash MODE=sensor PERIOD_MS=97     HDC2010 polled by the MCU timer
#   make flash MODE=sensor_irq HDC_AMM=7    HDC2010 auto mode, DRDY wakes the MCU from System ON idle
#
# Same modes and options as firmware/C23/pwrtest (no idle or shutdown_wake mode).
# Always built without the UART.
#
MODE        ?= standby
PERIOD_MS   ?= 1000
HDC_AMM     ?= 5
SHTC3_SLEEP ?= 1
override LOG := 0

OPTS := -DMODE=$(MODE) -DPERIOD_MS=$(PERIOD_MS) -DHDC_AMM=$(HDC_AMM) -DSHTC3_SLEEP=$(SHTC3_SLEEP)

include ../common/west.mak
