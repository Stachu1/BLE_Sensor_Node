/*
 * bsn_board.h - BSN-N54-A board definition (Nordic nRF54L05, QFN-48)
 *
 * Source of truth: hardware/N54/BSN-N54.kicad_sch. The pin map lives in
 * bsn_n54.overlay (devicetree); this file only holds the names and the I2C
 * addresses. Keep both in sync with the schematic.
 *
 *  I2C devices (bus i2c30, P0.00 SDA / P0.03 SCL):
 *    U3 HDC2010  0x40 (ADDR tied to GND)  fitted
 *    U2 SHTC3    0x70                     fitted
 *
 *  No LED, no button: UART and BLE are the only status outputs.
 */
#ifndef BSN_BOARD_H
#define BSN_BOARD_H

#define BSN_BOARD_NAME      "BSN-N54"
#define BSN_HW_REVISION     "A"

#define HDC2010_I2C_ADDR    0x40
#define SHTC3_I2C_ADDR      0x70

#endif /* BSN_BOARD_H */
