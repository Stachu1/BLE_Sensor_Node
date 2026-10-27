/*
 * shtc3.h - minimal Sensirion SHTC3 driver
 *
 * U2 is fitted on BSN-N54-A, next to the HDC2010 (U3).
 *
 * Datasheet: docs/datasheets/sensors/sensirion_SHTC3_datasheet.pdf
 */
#ifndef SHTC3_H
#define SHTC3_H

#include <stdbool.h>
#include <stdint.h>
#include <zephyr/device.h>

/* Wakes the sensor and reads its ID register. Returns true only if the ID matches an SHTC3. */
bool Shtc3_probe(const struct device *i2c, uint16_t *id);

/*
 * Sends the sleep command. After power-on the SHTC3 idles at about 45 uA until
 * it is told to sleep (0.3 uA), so call this at boot even if U2 is never used.
 * Returns false if nothing acknowledged (U2 not fitted, or already asleep).
 */
bool Shtc3_sleep(const struct device *i2c);

/* Wake, measure (normal mode, T first, no clock stretching), sleep. Blocks for about 13 ms. */
bool Shtc3_measure(const struct device *i2c, int16_t *temp_cC, uint16_t *rh_cP);

#endif /* SHTC3_H */
