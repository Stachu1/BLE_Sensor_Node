#
# BSN-C23 static current test firmware. See ../README.md.
#
#   make MODE=standby             standby | idle | active | shutdown | sensor |
#                                 sensor_irq | shutdown_wake
#   make MODE=sensor PERIOD_MS=1000
#   make MODE=sensor_irq HDC_AMM=5   HDC2010 auto rate: 1 = 120 s, 2 = 60 s, 3 = 10 s,
#                                    4 = 5 s, 5 = 1 s, 6 = 0.5 s, 7 = 0.2 s
#   make SHTC3_SLEEP=0            leave the SHTC3 (U2) idle after power-on (about 45 uA)
#
include ../imports.mak

MODE         ?= standby
PERIOD_MS    ?= 1000
BOOT_DELAY_S ?= 5
SHTC3_SLEEP  ?= 1
HDC_AMM      ?= 5

MODE_standby  := 0
MODE_idle     := 1
MODE_active   := 2
MODE_shutdown := 3
MODE_sensor   := 4
MODE_sensor_irq    := 5
MODE_shutdown_wake := 6
MODE_NUM      := $(MODE_$(MODE))
ifeq ($(MODE_NUM),)
$(error MODE must be one of: standby idle active shutdown sensor sensor_irq shutdown_wake)
endif

NAME       := bsn_c23_pwrtest
SYSCFG     := pwrtest.syscfg
LINKER_CMD := ../hwtest/lpf3_freertos.cmd
SRCS       := pwrtest.c ../hwtest/main_freertos.c $(COMMON_DIR)/hdc2010.c $(COMMON_DIR)/shtc3.c
CFLAGS     := -DPWR_MODE=$(MODE_NUM) -DPERIOD_MS=$(PERIOD_MS) -DBOOT_DELAY_S=$(BOOT_DELAY_S) \
              -DSHTC3_SLEEP=$(SHTC3_SLEEP) -DHDC_AMM=$(HDC_AMM)

# Rebuild pwrtest.c whenever the test parameters change
PARAMS := $(MODE) $(PERIOD_MS) $(BOOT_DELAY_S) $(SHTC3_SLEEP) $(HDC_AMM)
$(shell mkdir -p build && (echo '$(PARAMS)' | cmp -s - build/params || echo '$(PARAMS)' > build/params))

include ../rules.mak

$(OBJ)/pwrtest.obj: build/params
