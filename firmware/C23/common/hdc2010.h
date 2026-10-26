/*
 * hdc2010.h - minimal TI HDC2010 driver (on-demand measurements)
 *
 * Datasheet: docs/datasheets/sensors/ti_HDC2010_datasheet.pdf
 */
#ifndef HDC2010_H
#define HDC2010_H

#include <stdbool.h>
#include <stdint.h>
#include <ti/drivers/I2C.h>

#define HDC2010_MANUFACTURER_ID 0x5449 /* "TI" */
#define HDC2010_DEVICE_ID       0x07D0

typedef struct
{
    int16_t  temp_cC;  /* temperature in 0.01 degC */
    uint16_t rh_cP;    /* relative humidity in 0.01 %RH */
} Hdc2010_Sample;

/* Reads the manufacturer and device ID registers. Returns false on an I2C error. */
bool Hdc2010_readIds(I2C_Handle i2c, uint8_t addr, uint16_t *manufId, uint16_t *devId);

/*
 * Soft reset, then configure: 14-bit T and RH, on-demand mode, DRDY/INT pin
 * enabled active-high, DRDY interrupt enabled. The INT line (DIO21) goes high
 * when a conversion finishes and clears when the status register is read.
 */
bool Hdc2010_init(I2C_Handle i2c, uint8_t addr);

/* Auto measurement mode rates (register 0x0E, AMM[2:0]) */
#define HDC2010_AMM_120S        1
#define HDC2010_AMM_60S         2
#define HDC2010_AMM_10S         3
#define HDC2010_AMM_5S          4
#define HDC2010_AMM_1S          5
#define HDC2010_AMM_0S5         6
#define HDC2010_AMM_0S2         7

/*
 * Call after Hdc2010_init. The sensor then measures on its own at the given
 * rate (HDC2010_AMM_*) and raises INT when each result is ready. INT stays high
 * until the status register is read (Hdc2010_readStatus).
 */
bool Hdc2010_startAuto(I2C_Handle i2c, uint8_t addr, uint8_t rate);

/* Starts one T+RH conversion (about 1.3 ms at 14 bit). */
bool Hdc2010_trigger(I2C_Handle i2c, uint8_t addr);

/* Reads the DRDY_STATUS bit. Reading also clears it and releases the INT pin. */
bool Hdc2010_readStatus(I2C_Handle i2c, uint8_t addr, bool *dataReady);

/* Reads the result registers. Call this after DRDY or after waiting at least 2 ms. */
bool Hdc2010_readSample(I2C_Handle i2c, uint8_t addr, Hdc2010_Sample *out);

#endif /* HDC2010_H */
