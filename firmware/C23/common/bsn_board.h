/*
 * bsn_board.h - BSN-C23-B board definition (TI CC2340R52E0RGER, VQFN-24)
 *
 * Source of truth: hardware/C23/BSN-C23.kicad_sch. Keep this file in sync
 * with the schematic and with the pin assignments in the .syscfg files.
 * The rev A firmware is at the tag fw/BSN-C23-A.
 *
 *  Signal      DIO     Pin   Test point  Notes
 *  ---------   -----   ---   ----------  ----------------------------------
 *  I2C SDA     DIO12   5     TP3         R5 4.7k pull-up to VDD
 *  I2C SCL     DIO24   12    TP9         R6 4.7k pull-up to VDD
 *  HDC_INT     DIO13   6     TP4         HDC2010 DRDY/INT (push-pull), DIO21 on rev A
 *  UART TXD    DIO6    19    TP2         CC2340 TX -> USB-UART RX, DIO13 on rev A
 *  UART RXD    DIO20   9     TP8         CC2340 RX <- USB-UART TX
 *  BOOT        DIO3    14    TP1         R4 100k pull-up, low at reset = ROM bootloader
 *  LED         DIO4    15                D1 + R2 1k, both DNP by default
 *  SWDIO       DIO16   7     TP5         also on J3 (TC2030-NL)
 *  SWDCK       DIO17   8     TP7         also on J3
 *  nRESET      RSTN    13    TP6         R3 100k pull-up, C15 100n, also on J3
 *  VDD                       TP11        CR2032 / bench supply, J4 pin 1
 *  GND                       TP10, TP12
 *  (unused)    DIO8, DIO11, DIO21
 *
 *  UART TX on DIO6 with RX on DIO20 is the ROM bootloader's serial IO set 0,
 *  so the board can be flashed over a plain USB-UART adapter (BOOT low at reset).
 *
 *  Supply: R1 0R from VBAT to VDD, J1 (DNP) across it for the ammeter.
 *
 *  Clocks: X1 48 MHz HFXT (ECS-480-8-33B, 8 pF, internal cap array, no external load caps)
 *          No 32.768 kHz crystal -> LF clock must be LFOSC.
 *
 *  I2C devices:
 *    U2 HDC2010  0x40 (ADDR tied to GND)  fitted
 *    SHTC3       0x70                     not on rev B (DNP on rev A), still probed:
 *                                         a NACK means it is absent and costs nothing
 */
#ifndef BSN_BOARD_H
#define BSN_BOARD_H

#define BSN_BOARD_NAME      "BSN-C23"
#define BSN_HW_REVISION     "B"

#define BSN_DIO_SDA         12
#define BSN_DIO_SCL         24
#define BSN_DIO_HDC_INT     13
#define BSN_DIO_UART_TX     6
#define BSN_DIO_UART_RX     20
#define BSN_DIO_BOOT        3
#define BSN_DIO_LED         4

#define HDC2010_I2C_ADDR    0x40
#define SHTC3_I2C_ADDR      0x70

#endif /* BSN_BOARD_H */
