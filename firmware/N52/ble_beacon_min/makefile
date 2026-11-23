#
# ble_beacon_min: bare-metal build with the NCS toolchain's GCC and Nordic's MDK headers (no west, no Zephyr).
# See ../README.md.
#
#   make                  -> build/beacon.hex (+ beacon.elf, beacon.map)
#   make jflash           build, program and run (J-Link). stflash for an ST-Link, flash for nrfutil
#   make DRDY=7 jflash    HDC2010 auto mode rate, same codes as C23 DRDY (see below)
#
# DRDY is the HDC2010 auto-measurement code: 1 = 120 s, 2 = 60 s, 3 = 10 s, 4 = 5 s, 5 = 1 s, 6 = 0.5 s, 7 = 0.2 s.
# DRDY=0 takes one reading at cold boot, sends one advert and stays in System OFF for good (floor measurement).
# Unplug the probe and power-cycle the board after flashing, before measuring current.
#
DRDY ?= 4

BUILD := build
HEX   := $(BUILD)/beacon.hex
ELF   := $(BUILD)/beacon.elf

include ../common/flash.mak

# Windows-style paths: the compiler is a native Windows program
NCS_ROOT_W ?= C:/ncs/v3.4.0
MDK        := $(NCS_ROOT_W)/modules/hal/nordic/nrfx/bsp/stable/mdk
CMSIS      := $(NCS_ROOT_W)/modules/hal/cmsis_6/CMSIS/Core/Include

SRCS := src/main.c src/startup.c src/bthome.c $(MDK)/system_nrf52805.c

CFLAGS := -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -Os -g -std=gnu11 -Wall -Wextra \
          -ffunction-sections -fdata-sections -ffreestanding -fno-common \
          -DNRF52805_XXAA -DCONFIG_GPIO_AS_PINRESET -DDRDY_AMM=$(DRDY) \
          -I$(MDK) -I$(CMSIS) -Isrc
LDFLAGS := -nostdlib -Wl,--gc-sections -Tlink.ld -Wl,-Map=$(BUILD)/beacon.map

# Rebuild when an option changes
PARAMS := $(DRDY)
$(shell mkdir -p $(BUILD) && (echo '$(PARAMS)' | cmp -s - $(BUILD)/params || echo '$(PARAMS)' > $(BUILD)/params))

.PHONY: all flash clean

all: $(HEX)

$(ELF): $(wildcard src/*.c src/*.h) link.ld $(BUILD)/params
	$(NCS_ENV) && arm-zephyr-eabi-gcc $(CFLAGS) $(SRCS) $(LDFLAGS) -o $@ -lgcc && arm-zephyr-eabi-size $@

$(HEX): $(ELF)
	$(NCS_ENV) && arm-zephyr-eabi-objcopy -O ihex $< $@
	@echo "Built: $@ (DRDY=$(DRDY))"

flash: all
	$(NCS_ENV) && nrfutil device program --firmware $(HEX) --options chip_erase_mode=ERASE_RANGES_TOUCHED_BY_FIRMWARE \
	    && nrfutil device reset

clean:
	rm -rf $(BUILD)
