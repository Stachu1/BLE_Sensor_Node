/*
 * test_host.c - host-side unit tests for the BSN-C23 drivers and BTHome payload
 *
 * Runs the real driver sources against a fake I2C bus that emulates the
 * HDC2010 register file and the SHTC3 command set. Build and run: ./run.sh
 */
#include <stdio.h>
#include <string.h>

#include <ti/drivers/I2C.h>

#include "bsn_board.h"
#include "bthome.h"
#include "hdc2010.h"
#include "shtc3.h"

static int failures;

#define CHECK(cond) do { if (!(cond)) { printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); failures++; } } while (0)
#define CHECK_EQ(a, b) do { long _a = (long)(a), _b = (long)(b); if (_a != _b) { \
    printf("FAIL %s:%d: %s == %ld, expected %ld\n", __FILE__, __LINE__, #a, _a, _b); failures++; } } while (0)

/* ---------------- fake bus ---------------- */

static uint8_t hdcRegs[256];
static uint8_t hdcPtr;
static int hdcTriggers;
static bool shtPresent;
static uint16_t shtLastCmd;
static uint8_t shtResult[6];

static uint8_t crc8(const uint8_t *d, size_t n)
{
    uint8_t c = 0xFF;
    while (n--)
    {
        c ^= *d++;
        for (int b = 0; b < 8; b++)
        {
            c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x31) : (uint8_t)(c << 1);
        }
    }
    return c;
}

static void shtWord(uint8_t *dst, uint16_t v)
{
    dst[0] = (uint8_t)(v >> 8);
    dst[1] = (uint8_t)v;
    dst[2] = crc8(dst, 2);
}

bool I2C_transfer(I2C_Handle h, I2C_Transaction *t)
{
    const uint8_t *w = t->writeBuf;
    uint8_t *r = t->readBuf;
    (void)h;

    if (t->targetAddress == HDC2010_I2C_ADDR)
    {
        if (t->writeCount >= 1)
        {
            hdcPtr = w[0];
            for (size_t i = 1; i < t->writeCount; i++)
            {
                hdcRegs[(uint8_t)(hdcPtr + i - 1)] = w[i];
                if (hdcPtr + i - 1 == 0x0F && (w[i] & 1))
                {
                    hdcTriggers++;
                }
            }
        }
        for (size_t i = 0; i < t->readCount; i++)
        {
            r[i] = hdcRegs[(uint8_t)(hdcPtr + i)];
        }
        return true;
    }
    if (t->targetAddress == SHTC3_I2C_ADDR && shtPresent)
    {
        if (t->writeCount == 2)
        {
            shtLastCmd = (uint16_t)((w[0] << 8) | w[1]);
        }
        if (t->readCount == 3 && shtLastCmd == 0xEFC8)
        {
            shtWord(r, 0x0887); /* example ID from the datasheet, matches mask 0x083F == 0x0807 */
        }
        else if (t->readCount == 6 && shtLastCmd == 0x7866)
        {
            memcpy(r, shtResult, 6);
        }
        return true;
    }
    return false; /* NACK */
}

/* ---------------- tests ---------------- */

static void testHdc2010(void)
{
    Hdc2010_Sample s;
    uint16_t manuf, dev;
    bool ready;

    hdcRegs[0xFC] = 0x49; hdcRegs[0xFD] = 0x54; hdcRegs[0xFE] = 0xD0; hdcRegs[0xFF] = 0x07;
    CHECK(Hdc2010_readIds(NULL, HDC2010_I2C_ADDR, &manuf, &dev));
    CHECK_EQ(manuf, HDC2010_MANUFACTURER_ID);
    CHECK_EQ(dev, HDC2010_DEVICE_ID);

    CHECK(Hdc2010_init(NULL, HDC2010_I2C_ADDR));
    CHECK_EQ(hdcRegs[0x0E], 0x06); /* DRDY/INT_EN, active high, level mode, no soft reset left set */
    CHECK_EQ(hdcRegs[0x07], 0x80); /* DRDY interrupt enabled */
    CHECK_EQ(hdcRegs[0x0F], 0x00); /* 14 bit T and RH, no trigger */

    CHECK(Hdc2010_trigger(NULL, HDC2010_I2C_ADDR));
    CHECK_EQ(hdcTriggers, 1);

    hdcRegs[0x04] = 0x80;
    CHECK(Hdc2010_readStatus(NULL, HDC2010_I2C_ADDR, &ready));
    CHECK(ready);

    /* raw 0x6666 -> 26214/65536*165-40 = 25.998 C (floor 25.99); RH 0x8000 -> 50.00 % */
    hdcRegs[0] = 0x66; hdcRegs[1] = 0x66; hdcRegs[2] = 0x00; hdcRegs[3] = 0x80;
    CHECK(Hdc2010_readSample(NULL, HDC2010_I2C_ADDR, &s));
    CHECK_EQ(s.temp_cC, 2599);
    CHECK_EQ(s.rh_cP, 5000);

    /* range ends */
    memset(hdcRegs, 0, 4);
    Hdc2010_readSample(NULL, HDC2010_I2C_ADDR, &s);
    CHECK_EQ(s.temp_cC, -4000);
    CHECK_EQ(s.rh_cP, 0);
    memset(hdcRegs, 0xFF, 4);
    Hdc2010_readSample(NULL, HDC2010_I2C_ADDR, &s);
    CHECK_EQ(s.temp_cC, 12499);
    CHECK_EQ(s.rh_cP, 9999);

    /* below zero: raw 0x3D00 = 15616 -> -0.684 C */
    hdcRegs[0] = 0x00; hdcRegs[1] = 0x3D;
    Hdc2010_readSample(NULL, HDC2010_I2C_ADDR, &s);
    CHECK_EQ(s.temp_cC, -69);
}

static void testShtc3(void)
{
    uint16_t id;
    int16_t t;
    uint16_t h;

    shtPresent = false;
    CHECK(!Shtc3_probe(NULL, &id));

    shtPresent = true;
    CHECK(Shtc3_probe(NULL, &id));
    CHECK_EQ(id, 0x0887);

    /* CRC example from the SHTC3 datasheet: 0xBEEF -> 0x92 */
    {
        uint8_t ex[2] = {0xBE, 0xEF};
        CHECK_EQ(crc8(ex, 2), 0x92);
    }

    /* T raw 0x6666 -> -45 + 175*0.4 = 24.99 C; RH raw 0x4000 -> 25.00 % */
    shtWord(&shtResult[0], 0x6666);
    shtWord(&shtResult[3], 0x4000);
    CHECK(Shtc3_measure(NULL, &t, &h));
    CHECK_EQ(t, 2499);
    CHECK_EQ(h, 2500);

    /* corrupted CRC must be rejected */
    shtResult[2] ^= 0xFF;
    CHECK(!Shtc3_measure(NULL, &t, &h));
}

static void testBtHome(void)
{
    static const uint8_t expected[] = {
        0x02, 0x01, 0x06,                         /* flags */
        0x11, 0x16, 0xD2, 0xFC, 0x40,             /* service data, UUID 0xFCD2, v2 unencrypted */
        0x00, 0x07,                               /* packet id 7 */
        0x01, 0x5D,                               /* battery 93 % */
        0x02, 0x27, 0x0A,                         /* temperature 25.99 C */
        0x03, 0xA0, 0x11,                         /* humidity 45.12 % */
        0x0C, 0x86, 0x0B,                         /* voltage 2.950 V */
        0x08, 0x09, 'B', 'S', 'N', '-', 'C', '2', '3'
    };
    uint8_t buf[BTHOME_ADV_MAX_LEN + 8];
    BtHome_Reading r = {.packetId = 7, .vdds_mV = 2950, .sensorValid = true,
                        .temp_cC = 2599, .rh_cP = 4512};
    size_t n;

    n = BtHome_buildAdv(buf, &r, "BSN-C23");
    CHECK_EQ(n, sizeof(expected));
    CHECK(memcmp(buf, expected, sizeof(expected)) == 0);

    /* negative temperature is little-endian two's complement */
    r.temp_cC = -1938;
    BtHome_buildAdv(buf, &r, "BSN-C23");
    CHECK_EQ(buf[13], 0x6E);
    CHECK_EQ(buf[14], 0xF8);

    /* without a sensor reading only packet id, battery and voltage are sent */
    r.sensorValid = false;
    n = BtHome_buildAdv(buf, &r, "BSN-C23");
    CHECK_EQ(buf[3], 0x0B);
    CHECK_EQ(n, 24);

    /* long names are shortened to fit 31 bytes */
    r.sensorValid = true;
    memset(buf, 0xEE, sizeof(buf));
    n = BtHome_buildAdv(buf, &r, "A-very-long-device-name");
    CHECK_EQ(n, BTHOME_ADV_MAX_LEN);
    CHECK_EQ(buf[22], 0x08);  /* shortened local name */
    CHECK_EQ(buf[31], 0xEE);  /* nothing written past the limit */

    CHECK_EQ(BtHome_batteryPercent(3300), 100);
    CHECK_EQ(BtHome_batteryPercent(2600), 50);
    CHECK_EQ(BtHome_batteryPercent(2000), 0);
}

int main(void)
{
    testHdc2010();
    testShtc3();
    testBtHome();
    printf(failures ? "%d FAILURE(S)\n" : "all host tests passed\n", failures);
    return failures != 0;
}
