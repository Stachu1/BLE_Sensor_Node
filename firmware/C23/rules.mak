#
# Shared build rules for the BSN-C23 firmware projects (TI Arm Clang + SysConfig).
#
# A project makefile sets these, then includes this file:
#   NAME        output base name
#   SYSCFG      the .syscfg file
#   SRCS        C sources (any directory)
#   LINKER_CMD  linker command file
#   CFLAGS      extra flags (optional)
#
# EXTRA_CFLAGS can be set on the command line, e.g. make EXTRA_CFLAGS=-DBSN_LOG_ENABLE=0
#
# Targets:
#   all (default)  generate, compile, link, then CRC-patch the CCFG and write .hex
#   flash          chip erase, program, verify and run the image over XDS110
#   erase          chip erase (main flash + CCFG), also recovers a locked-out device
#   probe          list connected XDS110 probes
#   jflash         same as flash, with a SEGGER J-Link
#   jerase         chip erase with a J-Link
#   jstatus        J-Link: show VTref, halt, dump registers, resume
#   syscfg-gui     open the .syscfg in the SysConfig GUI
#   clean
#
# Recipes use POSIX shell commands: on Windows, run make from Git Bash.
#

BUILD := build
GEN   := $(BUILD)/syscfg
OBJ   := $(BUILD)/obj
OUT   := $(BUILD)/$(NAME).out
HEX   := $(BUILD)/$(NAME).hex

CC := "$(TICLANG_ARMCOMPILER)/bin/tiarmclang"

V := @
ifeq ($(VERBOSE),1)
  V :=
endif

SYSCFG_CMD = "$(SYSCONFIG_TOOL)" --compiler ticlang --product "$(SDK_DIR)/.metadata/product.json"

BASE_CFLAGS = \
    -I. -I$(COMMON_DIR) -I$(GEN) \
    @$(GEN)/ti_utils_build_compiler.opt \
    "-I$(SDK_DIR)/source" \
    "-I$(SDK_DIR)/kernel/freertos" \
    "-I$(SDK_DIR)/source/ti/posix/ticlang" \
    "-I$(SDK_DIR)/source/third_party/freertos/include" \
    "-I$(SDK_DIR)/source/third_party/freertos/portable/GCC/ARM_CM0" \
    -DFREERTOS \
    -mcpu=cortex-m0plus -march=thumbv6m -mfloat-abi=soft -mthumb \
    -std=gnu99 -ffunction-sections -fdata-sections \
    -Oz -g -gdwarf-3 -Wall

LFLAGS = \
    -Wl,--diag_wrap=off -Wl,--display_error_number -Wl,-x -Wl,-c \
    "-Wl,--search_path=$(GEN)" \
    "-L$(SDK_DIR)/source" \
    $(GEN)/ti_utils_build_linker.cmd.genlibs \
    $(LINKER_CMD) \
    "-Wl,-m,$(BUILD)/$(NAME).map" \
    -Wl,--rom_model -Wl,--warn_sections \
    "-L$(TICLANG_ARMCOMPILER)/lib" -llibc.a

SYSCFG_STAMP := $(GEN)/.stamp

.PHONY: all build flash erase probe jflash jerase jstatus clean syscfg-gui

# Two passes: the list of generated sources is only known after SysConfig has run.
all: $(SYSCFG_STAMP)
	$(V)$(MAKE) --no-print-directory build

$(SYSCFG_STAMP): $(SYSCFG)
	@echo "SysConfig  $<"
	$(V)mkdir -p $(GEN)
	$(V)$(SYSCFG_CMD) --output $(GEN) $< > $(BUILD)/syscfg.log 2>&1 || (cat $(BUILD)/syscfg.log; exit 1)
	$(V)touch $@

GEN_SRCS := $(wildcard $(GEN)/*.c)
ALL_SRCS := $(SRCS) $(GEN_SRCS)
OBJS     := $(addprefix $(OBJ)/,$(notdir $(ALL_SRCS:.c=.obj)))

vpath %.c $(sort $(dir $(ALL_SRCS)))

build: $(HEX)

$(OBJ)/%.obj: %.c $(SYSCFG_STAMP)
	@echo "CC         $(notdir $<)"
	$(V)mkdir -p $(OBJ)
	$(V)$(CC) $(BASE_CFLAGS) $(CFLAGS) $(EXTRA_CFLAGS) -MMD -MP -c $< -o $@

$(OUT): $(OBJS) $(LINKER_CMD)
	@echo "LD         $(notdir $@)"
	$(V)$(CC) -Wl,-u,_c_int00 $(OBJS) $(LFLAGS) -o $@

$(HEX): $(OUT)
	@echo "CRC/HEX    $(notdir $@)"
	$(V)"$(SDK_DIR)/tools/common/crc_tool/crc_tool" patch-image --elf $(OUT) --symbol-prefix ti_utils_build_GenMap_sym_CRC --output $(OUT)
	$(V)"$(TICLANG_ARMCOMPILER)/bin/tiarmobjcopy" -O ihex $(OUT) $@
	$(V)"$(TICLANG_ARMCOMPILER)/bin/tiarmsize" $(OUT)

-include $(OBJS:.obj=.d)

# Program load does a chip erase first (the CC23xx default), which includes the
# CCFG sector, since the CCFG is part of the image.
# -e verbose, -f flash, -v verify, -u run when done.
flash: all
	"$(DSLITE)" flash -c "$(CCXML)" -e -f -v -u $(OUT)

# Chip erase through the SACI/ROM path. This also recovers a device whose
# firmware has stopped SWD from attaching.
erase:
	"$(DSLITE)" cc23xx-unlock-debug-access -c "$(CCXML)"

# ---- SEGGER J-Link alternatives ----
# The CC2340 only has a chip erase (main flash + CCFG). J-Link erases as part of
# loadfile and writes the image together with its CCFG, whose CRCs crc_tool
# patched above. An image without a valid CCFG would lock the debug port.
JLINK_CMD = "$(JLINK)" -NoGui 1 -ExitOnError 1 -Device $(JLINK_DEVICE) -If SWD -Speed $(JLINK_SPEED) -AutoConnect 1 -CommandFile

# loadfile erases, programs and verifies. No reset afterwards: on the first
# prototype, SEGGER's CC2340 reset (via SEC-AP/SACI) left the core held in the ROM
# and the new image only started after a full power cycle.
jflash: all
	@printf 'r\nloadfile %s\nexit\n' "$(HEX)" > $(BUILD)/jflash.jlink
	$(JLINK_CMD) $(BUILD)/jflash.jlink
	@echo "Programmed. Unplug the J-Link USB, power the board off for 30 s, then power it on again."

jerase:
	@mkdir -p $(BUILD)
	@printf 'erase\nexit\n' > $(BUILD)/jerase.jlink
	$(JLINK_CMD) $(BUILD)/jerase.jlink

# Connects, prints VTref and the core state, leaves the target running
jstatus:
	@mkdir -p $(BUILD)
	@printf 'st\nh\nregs\ng\nexit\n' > $(BUILD)/jstatus.jlink
	$(JLINK_CMD) $(BUILD)/jstatus.jlink

# Lists the debug probes connected over USB
probe:
	"$(DSLITE)" identifyProbe -c "$(CCXML)"

syscfg-gui: $(SYSCFG)
	"$(dir $(SYSCONFIG_TOOL))sysconfig_gui$(suffix $(SYSCONFIG_TOOL))" --compiler ticlang --product "$(SDK_DIR)/.metadata/product.json" $<

clean:
	rm -rf $(BUILD)
