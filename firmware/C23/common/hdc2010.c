/*
 * hdc2010.c - minimal TI HDC2010 driver (on-demand measurements)
 */
#include "hdc2010.h"

#include <unistd.h>

#define REG_TEMP_LOW      0x00 /* TEMP_L, TEMP_H, HUM_L, HUM_H are consecutive */
#define REG_DRDY_STATUS   0x04
#define REG_INT_ENABLE    0x07
#define REG_RESET_INT_CFG 0x0E
#define REG_MEAS_CFG      0x0F
#define REG_MANUF_ID_LOW  0xFC /* MANUF_L, MANUF_H, DEV_L, DEV_H are consecutive */

/* 0x0E: SOFT_RES(7) AMM[2:0](6:4) HEAT_EN(3) DRDY/INT_EN(2) INT_POL(1) INT_MODE(0) */
#define CFG_SOFT_RES      0x80
#define CFG_DRDY_INT_EN   0x04
#define CFG_INT_POL_HIGH  0x02

/* 0x0F: TRES[1:0](7:6) HRES[1:0](5:4) MEAS_CONF[1:0](2:1) MEAS_TRIG(0); 00 = 14 bit, T+RH */
#define MEAS_TRIG         0x01

#define INT_DRDY_ENABLE   0x80
#define STATUS_DRDY       0x80

static bool writeReg(I2C_Handle i2c, uint8_t addr, uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = {reg, val};
    I2C_Transaction t = {0};

    t.targetAddress = addr;
    t.writeBuf      = buf;
    t.writeCount    = sizeof(buf);
    return I2C_transfer(i2c, &t);
}

static bool readRegs(I2C_Handle i2c, uint8_t addr, uint8_t reg, uint8_t *dst, size_t len)
{
    I2C_Transaction t = {0};

    t.targetAddress = addr;
    t.writeBuf      = &reg;
    t.writeCount    = 1;
    t.readBuf       = dst;
    t.readCount     = len;
    return I2C_transfer(i2c, &t);
}

bool Hdc2010_readIds(I2C_Handle i2c, uint8_t addr, uint16_t *manufId, uint16_t *devId)
{
    uint8_t b[4];

    if (!readRegs(i2c, addr, REG_MANUF_ID_LOW, b, sizeof(b)))
    {
        return false;
    }
    *manufId = (uint16_t)(b[0] | (b[1] << 8));
    *devId   = (uint16_t)(b[2] | (b[3] << 8));
    return true;
}

bool Hdc2010_init(I2C_Handle i2c, uint8_t addr)
{
    if (!writeReg(i2c, addr, REG_RESET_INT_CFG, CFG_SOFT_RES))
    {
        return false;
    }
    usleep(2000); /* soft reset */

    return writeReg(i2c, addr, REG_RESET_INT_CFG, CFG_DRDY_INT_EN | CFG_INT_POL_HIGH) &&
           writeReg(i2c, addr, REG_INT_ENABLE, INT_DRDY_ENABLE) &&
           writeReg(i2c, addr, REG_MEAS_CFG, 0x00);
}

bool Hdc2010_startAuto(I2C_Handle i2c, uint8_t addr, uint8_t rate)
{
    /* Same INT setup as Hdc2010_init, plus the AMM rate. MEAS_TRIG starts the sequence. */
    return writeReg(i2c, addr, REG_RESET_INT_CFG,
                    (uint8_t)((rate & 0x07) << 4) | CFG_DRDY_INT_EN | CFG_INT_POL_HIGH) &&
           writeReg(i2c, addr, REG_MEAS_CFG, MEAS_TRIG);
}

bool Hdc2010_trigger(I2C_Handle i2c, uint8_t addr)
{
    return writeReg(i2c, addr, REG_MEAS_CFG, MEAS_TRIG);
}

bool Hdc2010_readStatus(I2C_Handle i2c, uint8_t addr, bool *dataReady)
{
    uint8_t s;

    if (!readRegs(i2c, addr, REG_DRDY_STATUS, &s, 1))
    {
        return false;
    }
    *dataReady = (s & STATUS_DRDY) != 0;
    return true;
}

bool Hdc2010_readSample(I2C_Handle i2c, uint8_t addr, Hdc2010_Sample *out)
{
    uint8_t b[4];
    uint32_t rawT, rawH;

    if (!readRegs(i2c, addr, REG_TEMP_LOW, b, sizeof(b)))
    {
        return false;
    }
    rawT = (uint32_t)(b[0] | (b[1] << 8));
    rawH = (uint32_t)(b[2] | (b[3] << 8));

    /* T = raw / 2^16 * 165 - 40, RH = raw / 2^16 * 100 (datasheet eq. 1 and 2), scaled by 100 */
    out->temp_cC = (int16_t)(((rawT * 16500u) >> 16) - 4000);
    out->rh_cP   = (uint16_t)((rawH * 10000u) >> 16);
    return true;
}
