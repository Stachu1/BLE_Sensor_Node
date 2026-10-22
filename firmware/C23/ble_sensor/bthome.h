/*
 * bthome.h - BTHome v2 advertising payload (https://bthome.io/format/)
 *
 * Unencrypted service data under UUID 0xFCD2. Home Assistant and other
 * BTHome-aware scanners decode it without any custom code.
 */
#ifndef BTHOME_H
#define BTHOME_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Legacy advertising payload limit */
#define BTHOME_ADV_MAX_LEN 31

typedef struct
{
    uint8_t  packetId;   /* increments on every new reading; lets receivers drop duplicates */
    uint16_t vdds_mV;
    bool     sensorValid;
    int16_t  temp_cC;    /* 0.01 degC */
    uint16_t rh_cP;      /* 0.01 %RH */
} BtHome_Reading;

/*
 * Builds the complete advertising data (flags, BTHome service data, local
 * name) into buf. Returns the length used. If the name doesn't fit, it is
 * truncated and sent as a shortened local name.
 */
size_t BtHome_buildAdv(uint8_t *buf, const BtHome_Reading *r, const char *name);

/* Rough CR2032 state of charge from the cell voltage: 3.0 V = 100 %, 2.2 V = 0 % */
uint8_t BtHome_batteryPercent(uint16_t vdds_mV);

#endif /* BTHOME_H */
