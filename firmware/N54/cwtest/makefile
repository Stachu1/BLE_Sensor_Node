#
# BSN-N54 continuous-wave RF test firmware. See ../README.md.
#
#   make                          2440 MHz, 0 dBm
#   make FREQ_MHZ=2402 TX_DBM=8   any frequency 2360..2500 MHz, TXPOWER table -40..+8 dBm
#   make PATTERN=1 / PATTERN=2    all-1 / all-0 packets: tones at carrier +/- deviation,
#                                 their midpoint is the true carrier (see src/cwtest.c)
#
FREQ_MHZ ?= 2440
TX_DBM   ?= 0
PATTERN  ?= 0

OPTS := -DFREQ_MHZ=$(FREQ_MHZ) -DTX_DBM=$(TX_DBM) -DPATTERN=$(PATTERN)

include ../common/west.mak
