#!/bin/sh
# Prints the RTT console (channel 0) of the running RTT=1 image over the J-Link.
# Run from the app folder: the control block address is taken from build/zephyr/zephyr.elf,
# so a stale block left in RAM by a previous image is not picked up. The target keeps running.
# The log is also kept in build/rtt.log. Stop with Ctrl+C.
#   sh ../tools/rtt_log.sh
. "$(dirname "$0")/ncs-env.sh"
ADDR=$(arm-zephyr-eabi-nm build/zephyr/zephyr.elf | awk '/ _SEGGER_RTT$/ {print $1}')
[ -n "$ADDR" ] || { echo "_SEGGER_RTT not in build/zephyr/zephyr.elf: build with RTT=1" >&2; exit 1; }
LOGFILE="$(pwd -W 2>/dev/null || pwd)/build/rtt.log"
rm -f build/rtt.log
# JLinkRTTLogger can only write to a file, so run it in the background and follow the file
JLinkRTTLogger.exe -Device NRF54L05_M33 -If SWD -Speed 4000 -RTTAddress "0x$ADDR" -RTTChannel 0 "$LOGFILE" >/dev/null 2>&1 &
LOGGER=$!
trap 'kill $LOGGER 2>/dev/null' EXIT INT TERM
# The logger only creates the file once it has found the RTT block: give up after 10 s
n=0
while [ ! -f build/rtt.log ]; do
    n=$((n + 1))
    if [ $n -gt 50 ] || ! kill -0 $LOGGER 2>/dev/null; then
        echo "No RTT data: is the image running? (after flashing, power-cycle the board)" >&2
        exit 1
    fi
    sleep 0.2
done
tail -f build/rtt.log
