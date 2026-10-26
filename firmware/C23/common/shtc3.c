/*
 * shtc3.c - minimal Sensirion SHTC3 driver
 */
#include "shtc3.h"
#include "bsn_board.h"

#include <unistd.h>

#define CMD_WAKEUP      0x3517
#define CMD_SLEEP       0xB098
#define CMD_READ_ID     0xEFC8
#define CMD_MEAS_T_RH   0x7866 /* normal mode, read T first, clock stretching disabled */

#define ID_MASK         0x083F
#define ID_SHTC3        0x0807

static bool sendCmd(I2C_Handle i2c, uint16_t cmd)
{
    uint8_t buf[2] = {(uint8_t)(cmd >> 8), (uint8_t)cmd};
    I2C_Transaction t = {0};

    t.targetAddress = SHTC3_I2C_ADDR;
    t.writeBuf      = buf;
    t.writeCount    = sizeof(buf);
    return I2C_transfer(i2c, &t);
}

static bool readWords(I2C_Handle i2c, uint8_t *dst, size_t len)
{
    I2C_Transaction t = {0};

    t.targetAddress = SHTC3_I2C_ADDR;
    t.readBuf       = dst;
    t.readCount     = len;
    return I2C_transfer(i2c, &t);
}

/* CRC-8, polynomial 0x31, init 0xFF (datasheet section 5.10) */
static uint8_t crc8(const uint8_t *data, size_t len)
{
    uint8_t crc = 0xFF;
    size_t i;
    int b;

    for (i = 0; i < len; i++)
    {
        crc ^= data[i];
        for (b = 0; b < 8; b++)
        {
            crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x31) : (uint8_t)(crc << 1);
        }
    }
    return crc;
}

bool Shtc3_probe(I2C_Handle i2c, uint16_t *id)
{
    uint8_t b[3];

    if (!sendCmd(i2c, CMD_WAKEUP))
    {
        return false;
    }
    usleep(240);
    if (!sendCmd(i2c, CMD_READ_ID) || !readWords(i2c, b, sizeof(b)) || crc8(b, 2) != b[2])
    {
        return false;
    }
    *id = (uint16_t)((b[0] << 8) | b[1]);
    sendCmd(i2c, CMD_SLEEP);
    return (*id & ID_MASK) == ID_SHTC3;
}

bool Shtc3_sleep(I2C_Handle i2c)
{
    return sendCmd(i2c, CMD_SLEEP);
}

bool Shtc3_measure(I2C_Handle i2c, int16_t *temp_cC, uint16_t *rh_cP)
{
    uint8_t b[6];
    uint32_t rawT, rawH;

    if (!sendCmd(i2c, CMD_WAKEUP))
    {
        return false;
    }
    usleep(240);
    if (!sendCmd(i2c, CMD_MEAS_T_RH))
    {
        return false;
    }
    usleep(12100); /* max measurement duration, normal mode */
    if (!readWords(i2c, b, sizeof(b)) || crc8(&b[0], 2) != b[2] || crc8(&b[3], 2) != b[5])
    {
        sendCmd(i2c, CMD_SLEEP);
        return false;
    }
    sendCmd(i2c, CMD_SLEEP);

    rawT = (uint32_t)((b[0] << 8) | b[1]);
    rawH = (uint32_t)((b[3] << 8) | b[4]);

    /* T = -45 + 175 * raw / 2^16, RH = 100 * raw / 2^16, scaled by 100 */
    *temp_cC = (int16_t)(((rawT * 17500u) >> 16) - 4500);
    *rh_cP   = (uint16_t)((rawH * 10000u) >> 16);
    return true;
}
