#
# BSN-C23 continuous-wave RF test firmware. See ../README.md.
#
#   make                          2440 MHz, 0 dBm
#   make FREQ_MHZ=2402 TX_DBM=8   any frequency 2360..2500 MHz, PA table -20..+8 dBm
#
include ../imports.mak

FREQ_MHZ   ?= 2440
TX_DBM     ?= 0
TX_HALF_DB ?= 0

NAME       := bsn_c23_cwtest
SYSCFG     := cwtest.syscfg
LINKER_CMD := ../hwtest/lpf3_freertos.cmd
SRCS       := cwtest.c ../hwtest/main_freertos.c $(COMMON_DIR)/bsn_log.c
# rcl/commands/generic.h and LRFLPF3_Interface_Generic.h both typedef RCL_ConfigAddress
CFLAGS     := -DCW_FREQ_MHZ=$(FREQ_MHZ) -DCW_TX_DBM=$(TX_DBM) -DCW_TX_HALF_DB=$(TX_HALF_DB) \
              -Wno-typedef-redefinition

# Rebuild cwtest.c whenever the RF parameters change
PARAMS := $(FREQ_MHZ) $(TX_DBM) $(TX_HALF_DB)
$(shell mkdir -p build && (echo '$(PARAMS)' | cmp -s - build/params || echo '$(PARAMS)' > build/params))

include ../rules.mak

$(OBJ)/cwtest.obj: build/params
