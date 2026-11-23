/*
 * BTHome v2 service data (https://bthome.io/format/), same payload as
 * BLE_Sensor_Node/firmware/C23/ble_sensor/bthome.c: unencrypted, UUID 0xFCD2, objects in ascending id order.
 * Copy of N52/ble_sensor/src/bthome.h so this bare-metal build is self-contained; keep the two in sync.
 */
#ifndef BTHOME_H
#define BTHOME_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* UUID(2) + device info(1) + packet id(2) + battery(2) + temperature(3) + humidity(3) + voltage(3) */
#define BTHOME_SVC_MAX 16

struct bthome_reading {
	uint8_t packet_id; /* increments on every new reading; receivers drop duplicates */
	uint16_t vdds_mV;
	bool sensor_valid;
	int16_t temp_cC;  /* 0.01 degC */
	uint16_t rh_cP;   /* 0.01 %RH */
};

/* Writes the service data payload (without the AD length/type bytes) into buf, returns its length. */
size_t bthome_build_service_data(uint8_t *buf, const struct bthome_reading *r);

/* Rough coin cell state of charge: 3.0 V = 100 %, 2.2 V = 0 % */
uint8_t bthome_battery_percent(uint16_t vdds_mV);

#endif
