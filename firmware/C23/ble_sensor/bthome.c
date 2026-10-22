/*
 * bthome.c - BTHome v2 advertising payload
 */
#include "bthome.h"

#include <string.h>

#define AD_FLAGS                0x01
#define AD_NAME_SHORT           0x08
#define AD_NAME_COMPLETE        0x09
#define AD_SERVICE_DATA_16      0x16

#define FLAGS_LE_GENERAL_NO_BREDR 0x06

#define BTHOME_UUID             0xFCD2
#define BTHOME_DEVICE_INFO      0x40 /* v2, no encryption, regular interval */

/* Object IDs, which must be sent in ascending order */
#define OBJ_PACKET_ID           0x00 /* uint8 */
#define OBJ_BATTERY             0x01 /* uint8, % */
#define OBJ_TEMPERATURE         0x02 /* sint16, 0.01 degC */
#define OBJ_HUMIDITY            0x03 /* uint16, 0.01 % */
#define OBJ_VOLTAGE             0x0C /* uint16, 0.001 V */

#define CR2032_FULL_MV          3000
#define CR2032_EMPTY_MV         2200

static uint8_t *putU16(uint8_t *p, uint16_t v)
{
    *p++ = (uint8_t)v;
    *p++ = (uint8_t)(v >> 8);
    return p;
}

uint8_t BtHome_batteryPercent(uint16_t vdds_mV)
{
    if (vdds_mV >= CR2032_FULL_MV)
    {
        return 100;
    }
    if (vdds_mV <= CR2032_EMPTY_MV)
    {
        return 0;
    }
    return (uint8_t)(((uint32_t)(vdds_mV - CR2032_EMPTY_MV) * 100u) / (CR2032_FULL_MV - CR2032_EMPTY_MV));
}

size_t BtHome_buildAdv(uint8_t *buf, const BtHome_Reading *r, const char *name)
{
    uint8_t *p = buf;
    uint8_t *svcLen;
    size_t nameLen, room;

    *p++ = 2;
    *p++ = AD_FLAGS;
    *p++ = FLAGS_LE_GENERAL_NO_BREDR;

    svcLen = p++;
    *p++ = AD_SERVICE_DATA_16;
    p = putU16(p, BTHOME_UUID);
    *p++ = BTHOME_DEVICE_INFO;
    *p++ = OBJ_PACKET_ID;
    *p++ = r->packetId;
    *p++ = OBJ_BATTERY;
    *p++ = BtHome_batteryPercent(r->vdds_mV);
    if (r->sensorValid)
    {
        *p++ = OBJ_TEMPERATURE;
        p = putU16(p, (uint16_t)r->temp_cC);
        *p++ = OBJ_HUMIDITY;
        p = putU16(p, r->rh_cP);
    }
    *p++ = OBJ_VOLTAGE;
    p = putU16(p, r->vdds_mV);
    *svcLen = (uint8_t)(p - svcLen - 1);

    nameLen = strlen(name);
    room = BTHOME_ADV_MAX_LEN - (size_t)(p - buf);
    if (room > 2)
    {
        bool complete = nameLen <= room - 2;
        if (!complete)
        {
            nameLen = room - 2;
        }
        *p++ = (uint8_t)(nameLen + 1);
        *p++ = complete ? AD_NAME_COMPLETE : AD_NAME_SHORT;
        memcpy(p, name, nameLen);
        p += nameLen;
    }
    return (size_t)(p - buf);
}
