#
# BSN-N52 BLE sensor (Zephyr + BLE controller). See ../README.md.
#
#   make jflash                 product build (no console), HDC2010 at 0.2 Hz, one advert per DRDY
#   make LOG=1 jflash           printk over RTT (debug.conf)
#   make DRDY=7 jflash          HDC2010 auto mode rate, same codes as C23 DRDY (see below)
#
# DRDY is the HDC2010 auto-measurement code: 1 = 120 s, 2 = 60 s, 3 = 10 s, 4 = 5 s, 5 = 1 s, 6 = 0.5 s, 7 = 0.2 s.
# DRDY=0 takes one reading at boot, sends one advert and then never wakes again (floor with the stack idle).
#
LOG  ?= 0
DRDY ?= 4

OPTS := -DDRDY=$(DRDY) $(if $(filter 1,$(LOG)),-DEXTRA_CONF_FILE=debug.conf)

include ../common/west.mak
