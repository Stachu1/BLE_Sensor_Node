/*
 * bsn_vdd.h - supply voltage (VDD) via the SAADC internal VDD input
 */
#ifndef BSN_VDD_H
#define BSN_VDD_H

#include <stdint.h>

/* Returns VDD in mV, or 0 if the ADC is not available. */
uint16_t BsnVdd_read_mV(void);

#endif /* BSN_VDD_H */
