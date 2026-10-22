/*
 * bsn_board.h - BSN-C23-A board definition (TI CC2340R52E0RGER, VQFN-24)
 *
 * Source of truth: hardware/C23/BSN-C23.kicad_sch. Keep this file in sync
 * with the schematic and with the pin assignments in the .syscfg files.
 *
 *  Signal      DIO     Pin   Test point  Notes
 *  ---------   -----   ---   ----------  ----------------------------------
 *  I2C SDA     DIO12   5     TP1         R1 4.7k pull-up to VDD
 *  I2C SCL     DIO24   12    TP8         R2 4.7k pull-up to VDD
 *  HDC_INT     DIO21   10    TP7         HDC2010 DRDY/INT (push-pull)
 *  UART TXD    DIO13   6     TP2         CC2340 TX -> USB-UART RX
 *  UART RXD    DIO20   9     TP6         CC2340 RX <- USB-UART TX
 *  SWDIO       DIO16   7     TP3
 *  SWDCK       DIO17   8     TP5
 *  nRESET      RSTN    13    TP4         R3 100k pull-up, C18 100n
 *  VDD                       TP9         CR2032 / bench supply
 *  GND                       TP10
 *  (unused)    DIO6, DIO8, DIO11
 *
 *  Clocks: X1 48 MHz HFXT (ECS-480-8-33B, 8 pF, internal cap array, C14/C15 DNP)
 *          X2 32.768 kHz is DNP on rev A -> LF clock must be LFOSC.
 *
 *  I2C devices:
 *    U3 HDC2010  0x40 (ADDR tied to GND)  fitted
 *    U2 SHTC3    0x70                     DNP on rev A, probed anyway
 *
 *  No LED, no button: UART and BLE are the only status outputs.
 */
#ifndef BSN_BOARD_H
#define BSN_BOARD_H

#define BSN_BOARD_NAME      "BSN-C23"
#define BSN_HW_REVISION     "A"

#define BSN_DIO_SDA         12
#define BSN_DIO_SCL         24
#define BSN_DIO_HDC_INT     21
#define BSN_DIO_UART_TX     13
#define BSN_DIO_UART_RX     20

#define HDC2010_I2C_ADDR    0x40
#define SHTC3_I2C_ADDR      0x70

#endif /* BSN_BOARD_H */
