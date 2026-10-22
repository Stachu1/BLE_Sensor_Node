/*
 * shtc3.h - minimal Sensirion SHTC3 driver
 *
 * U2 is DNP on BSN-C23-A. The bring-up firmware still probes it so that a
 * board with U2 hand-fitted can be compared against the HDC2010.
 *
 * Datasheet: docs/datasheets/sensors/sensirion_SHTC3_datasheet.pdf
 */
#ifndef SHTC3_H
#define SHTC3_H

#include <stdbool.h>
#include <stdint.h>
#include <ti/drivers/I2C.h>

/* Wakes the sensor and reads its ID register. Returns true only if the ID matches an SHTC3. */
bool Shtc3_probe(I2C_Handle i2c, uint16_t *id);

/* Wake, measure (normal mode, T first, no clock stretching), sleep. Blocks for about 13 ms. */
bool Shtc3_measure(I2C_Handle i2c, int16_t *temp_cC, uint16_t *rh_cP);

#endif /* SHTC3_H */
