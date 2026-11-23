#include "bthome.h"

#define BTHOME_UUID 0xFCD2
#define BTHOME_DEVICE_INFO 0x40 /* v2, no encryption, regular interval */

/* Object IDs, must be sent in ascending order */
#define OBJ_PACKET_ID 0x00   /* uint8 */
#define OBJ_BATTERY 0x01     /* uint8, % */
#define OBJ_TEMPERATURE 0x02 /* sint16, 0.01 degC */
#define OBJ_HUMIDITY 0x03    /* uint16, 0.01 % */
#define OBJ_VOLTAGE 0x0C     /* uint16, 0.001 V */

#define CELL_FULL_MV 3000
#define CELL_EMPTY_MV 2200

static uint8_t *put_u16(uint8_t *p, uint16_t v)
{
	*p++ = (uint8_t)v;
	*p++ = (uint8_t)(v >> 8);
	return p;
}

uint8_t bthome_battery_percent(uint16_t mv)
{
	if (mv >= CELL_FULL_MV) {
		return 100;
	}
	if (mv <= CELL_EMPTY_MV) {
		return 0;
	}
	return (uint8_t)(((uint32_t)(mv - CELL_EMPTY_MV) * 100u) / (CELL_FULL_MV - CELL_EMPTY_MV));
}

size_t bthome_build_service_data(uint8_t *buf, const struct bthome_reading *r)
{
	uint8_t *p = buf;

	p = put_u16(p, BTHOME_UUID);
	*p++ = BTHOME_DEVICE_INFO;
	*p++ = OBJ_PACKET_ID;
	*p++ = r->packet_id;
	*p++ = OBJ_BATTERY;
	*p++ = bthome_battery_percent(r->vdds_mV);
	*p++ = OBJ_TEMPERATURE;
	p = put_u16(p, r->sensor_valid ? (uint16_t)r->temp_cC : (uint16_t)-32768);
	*p++ = OBJ_HUMIDITY;
	p = put_u16(p, r->sensor_valid ? r->rh_cP : 0);
	*p++ = OBJ_VOLTAGE;
	p = put_u16(p, r->vdds_mV);
	return (size_t)(p - buf);
}
