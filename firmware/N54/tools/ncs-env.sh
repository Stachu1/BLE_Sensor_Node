# Source from Git Bash to get the NCS v3.4.0 toolchain (west, cmake, ninja, the Zephyr SDK) on PATH:
#   . tools/ncs-env.sh
# Also puts SEGGER J-Link (JLink.exe, for the jlink runner) on PATH.
# Paths follow C:/ncs/toolchains/<id>/environment.json. Override NCS_ROOT / NCS_TOOLCHAIN if installed elsewhere.
NCS_ROOT="${NCS_ROOT:-/c/ncs/v3.4.0}"
NCS_TOOLCHAIN="${NCS_TOOLCHAIN:-/c/ncs/toolchains/dcbdc366a1}"
JLINK_DIR="${JLINK_DIR:-/c/Program Files/SEGGER/JLink_V982}"
T="$NCS_TOOLCHAIN"
export PATH="$JLINK_DIR:$T:$T/mingw64/bin:$T/bin:$T/opt/bin:$T/opt/bin/Scripts:$T/opt/nanopb/generator-bin:$T/nrfutil/bin:$T/opt/zephyr-sdk/gnu/arm-zephyr-eabi/bin:$PATH"
export PYTHONPATH="$T/opt/bin;$T/opt/bin/Lib;$T/opt/bin/Lib/site-packages"
export NRFUTIL_HOME="$T/nrfutil/home"
export ZEPHYR_TOOLCHAIN_VARIANT=zephyr/gnu
export ZEPHYR_SDK_INSTALL_DIR="$T/opt/zephyr-sdk"
export ZEPHYR_BASE="$NCS_ROOT/zephyr"
unset T
