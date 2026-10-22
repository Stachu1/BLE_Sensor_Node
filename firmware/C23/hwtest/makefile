#
# BSN-C23 hardware self-test firmware. See ../README.md.
#
include ../imports.mak

NAME       := bsn_c23_hwtest
SYSCFG     := hwtest.syscfg
LINKER_CMD := lpf3_freertos.cmd
SRCS       := hwtest.c main_freertos.c \
              $(COMMON_DIR)/bsn_log.c $(COMMON_DIR)/hdc2010.c $(COMMON_DIR)/shtc3.c

include ../rules.mak
