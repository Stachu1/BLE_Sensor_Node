/*
 * hwtest.c - BSN-C23 bring-up self-test (no BLE stack)
 *
 * Runs a one-shot self-test at boot, prints a PASS/FAIL summary on the UART
 * (TP2, 115200 8N1), then prints one sensor line per period until power-off.
 *
 *  1. Reset reason, factory BLE address, part ID
 *  2. Clocks: HFXT (48 MHz) good, LF clock good (LFOSC, X2 not fitted)
 *  3. Supply: VDDS from the battery monitor, die temperature
 *  4. I2C: bus scan, HDC2010 IDs, SHTC3 probe (U2 DNP on rev A)
 *  5. HDC2010 measurement, plausibility check, and the DRDY/INT line (DIO21)
 *     checked both as a level and as an edge interrupt
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>

#include <ti/devices/DeviceFamily.h>
#include DeviceFamily_constructPath(inc/hw_types.h)
#include DeviceFamily_constructPath(inc/hw_memmap.h)
#include DeviceFamily_constructPath(inc/hw_ckmd.h)
#include DeviceFamily_constructPath(inc/hw_fcfg.h)

#include <ti/drivers/BatteryMonitor.h>
#include <ti/drivers/GPIO.h>
#include <ti/drivers/I2C.h>
#include <ti/drivers/Power.h>
#include <ti/drivers/Temperature.h>
#include <ti/drivers/power/PowerCC23X0.h>

#include "ti_drivers_config.h"

#include "bsn_board.h"
#include "bsn_log.h"
#include "hdc2010.h"
#include "shtc3.h"

#if !BSN_LOG_ENABLE
#error "hwtest reports only over the UART; build it with logging enabled"
#endif

#define FW_VERSION          "hwtest 0.1.0"
#define SAMPLE_PERIOD_S     2

/* Plausibility windows for an indoor lab bench */
#define VDDS_MIN_MV         1800
#define VDDS_MAX_MV         3800
#define TEMP_MIN_CC         (-1000)
#define TEMP_MAX_CC         5000

static volatile uint32_t hdcIntCount;
static unsigned int passCount, failCount;

static void hdcIntCallback(uint_least8_t index)
{
    (void)index;
    hdcIntCount++;
}

static void check(bool ok, const char *name, const char *detail)
{
    if (ok)
    {
        passCount++;
    }
    else
    {
        failCount++;
    }
    LOG("[%s] %-22s %s\r\n", ok ? "PASS" : "FAIL", name, detail);
}

static const char *resetReasonStr(PowerLPF3_ResetReason r)
{
    switch (r)
    {
        case PowerLPF3_RESET_POR:          return "power-on";
        case PowerLPF3_RESET_PIN:          return "reset pin";
        case PowerLPF3_RESET_VDDS:         return "VDDS brown-out";
        case PowerLPF3_RESET_VDDR:         return "VDDR brown-out";
        case PowerLPF3_RESET_LFXT:         return "LF clock loss";
        case PowerLPF3_RESET_SWD:          return "SWD (debugger)";
        case PowerLPF3_RESET_TSD:          return "thermal shutdown";
        case PowerLPF3_RESET_LOCKUP:       return "CPU lockup";
        case PowerLPF3_RESET_CPU:          return "CPU reset request";
        case PowerLPF3_RESET_SYSTEM:       return "system reset request";
        case PowerLPF3_RESET_WATCHDOG:     return "watchdog";
        case PowerLPF3_RESET_SHUTDOWN_IO:  return "wake from shutdown (IO)";
        case PowerLPF3_RESET_SHUTDOWN_SWD: return "wake from shutdown (SWD)";
        default:                           return "unknown";
    }
}

static void testDevice(void)
{
    const uint8_t *a = fcfg->deviceInfo.bleAddr;

    LOG("Reset reason : %s\r\n", resetReasonStr(PowerLPF3_getResetReason()));
    /* The address is stored little-endian; print it the way scanner apps show it */
    LOG("BLE address  : %02X:%02X:%02X:%02X:%02X:%02X\r\n", a[5], a[4], a[3], a[2], a[1], a[0]);
    LOG("Part ID      : 0x%08lX\r\n", (unsigned long)fcfg->deviceInfo.partId.val32);
}

static void testClocks(void)
{
    uint32_t v = 0;
    bool hfOk = false, lfOk = false;
    int i;

    /* The Power driver turns HFXT off in standby and restarts it on wake-up
     * without waiting, so keep the device out of standby while polling. */
    Power_setConstraint(PowerLPF3_DISALLOW_STANDBY);

    for (i = 0; i < 100 && !hfOk; i++)
    {
        hfOk = (HWREG(CKMD_BASE + CKMD_O_HFXTSTAT) & CKMD_HFXTSTAT_GOOD) != 0;
        if (!hfOk)
        {
            usleep(1000);
        }
    }
    check(hfOk, "HFXT 48 MHz (X1)",
          (HWREG(CKMD_BASE + CKMD_O_RIS) & CKMD_RIS_HFXTFAULT) ? "fault flag set" : "");

    /* The driver qualifies LFOSC in the background (up to a few hundred ms) and
     * then switches LFTICK from the HFOSC-derived "fake" source to LFCLK. */
    for (i = 0; i < 100 && !lfOk; i++)
    {
        v = HWREG(CKMD_BASE + CKMD_O_LFCLKSEL);
        lfOk = (v & CKMD_LFCLKSEL_MAIN_M) == CKMD_LFCLKSEL_MAIN_LFOSC &&
               (HWREG(CKMD_BASE + CKMD_O_LFCLKSTAT) & CKMD_LFCLKSTAT_LFTICKSRC_M) ==
                   CKMD_LFCLKSTAT_LFTICKSRC_LFCLK;
        if (!lfOk)
        {
            usleep(10000);
        }
    }
    check(lfOk, "LF clock (LFOSC)",
          (v & CKMD_LFCLKSEL_MAIN_M) == CKMD_LFCLKSEL_MAIN_LFOSC ? "" : "LFOSC not selected");

    Power_releaseConstraint(PowerLPF3_DISALLOW_STANDBY);
}

static void testSupply(void)
{
    char d[48];
    uint16_t mv = BatteryMonitor_getVoltage();
    int16_t die = Temperature_getTemperature();

    snprintf(d, sizeof(d), "%u mV", mv);
    check(mv >= VDDS_MIN_MV && mv <= VDDS_MAX_MV, "VDDS", d);
    LOG("Die temp     : %d C\r\n", die);
}

static void scanBus(I2C_Handle i2c)
{
    uint8_t addr, dummy;
    unsigned int found = 0;
    I2C_Transaction t = {0};

    LOG("I2C scan     :");
    for (addr = 0x08; addr < 0x78; addr++)
    {
        t.targetAddress = addr;
        t.readBuf       = &dummy;
        t.readCount     = 1;
        if (I2C_transfer(i2c, &t))
        {
            LOG(" 0x%02X", addr);
            found++;
        }
    }
    LOG(found ? "\r\n" : " none (check pull-ups R1/R2, U3 solder joints)\r\n");
}

static bool testHdc2010(I2C_Handle i2c)
{
    char d[64];
    uint16_t manuf = 0, dev = 0;
    bool idOk, ready = false, intLevelSeen = false;
    uint32_t edgesBefore;
    Hdc2010_Sample s;
    int i;

    idOk = Hdc2010_readIds(i2c, HDC2010_I2C_ADDR, &manuf, &dev) &&
           manuf == HDC2010_MANUFACTURER_ID && dev == HDC2010_DEVICE_ID;
    snprintf(d, sizeof(d), "manuf 0x%04X dev 0x%04X", manuf, dev);
    check(idOk, "HDC2010 ID (U3 @0x40)", d);
    if (!idOk)
    {
        return false;
    }

    check(Hdc2010_init(i2c, HDC2010_I2C_ADDR), "HDC2010 config", "");

    /* After config the INT pin is driven low (active-high polarity) */
    check(GPIO_read(CONFIG_GPIO_HDC_INT) == 0, "HDC INT idle low", "");

    edgesBefore = hdcIntCount;
    check(Hdc2010_trigger(i2c, HDC2010_I2C_ADDR), "HDC2010 trigger", "");
    /* usleep() rounds up to RTOS ticks, so each pass waits about 1-2 ms */
    for (i = 0; i < 25 && !intLevelSeen; i++)
    {
        usleep(1000);
        intLevelSeen = GPIO_read(CONFIG_GPIO_HDC_INT) != 0;
    }
    check(intLevelSeen, "HDC INT level (DIO21)", intLevelSeen ? "" : "never went high within 50 ms");
    check(hdcIntCount != edgesBefore, "HDC INT edge IRQ", "");

    Hdc2010_readStatus(i2c, HDC2010_I2C_ADDR, &ready);
    check(ready, "HDC2010 DRDY status", "");
    check(GPIO_read(CONFIG_GPIO_HDC_INT) == 0, "HDC INT cleared", "");

    if (!Hdc2010_readSample(i2c, HDC2010_I2C_ADDR, &s))
    {
        check(false, "HDC2010 read", "I2C error");
        return false;
    }
    snprintf(d, sizeof(d), CENTI_FMT " C  " CENTI_FMT " %%RH",
             CENTI_ARG(s.temp_cC), CENTI_ARG(s.rh_cP));
    check(s.temp_cC > TEMP_MIN_CC && s.temp_cC < TEMP_MAX_CC && s.rh_cP > 0 && s.rh_cP < 10000,
          "HDC2010 plausible", d);
    return true;
}

static bool testShtc3(I2C_Handle i2c)
{
    uint16_t id = 0;

    if (!Shtc3_probe(i2c, &id))
    {
        LOG("[INFO] SHTC3 (U2 @0x70)       not present (DNP on rev A)\r\n");
        return false;
    }
    LOG("[INFO] SHTC3 (U2 @0x70)       found, ID 0x%04X\r\n", id);
    return true;
}

static void printSample(I2C_Handle i2c, bool haveHdc, bool haveSht, uint32_t n)
{
    Hdc2010_Sample s;
    int16_t t2;
    uint16_t h2;

    LOG("#%lu VDDS=%u mV die=%d C", (unsigned long)n, BatteryMonitor_getVoltage(),
        Temperature_getTemperature());

    if (haveHdc)
    {
        Hdc2010_trigger(i2c, HDC2010_I2C_ADDR);
        usleep(2000);
        if (Hdc2010_readSample(i2c, HDC2010_I2C_ADDR, &s))
        {
            Hdc2010_readStatus(i2c, HDC2010_I2C_ADDR, &(bool){false}); /* releases INT */
            LOG(" | HDC2010 " CENTI_FMT " C " CENTI_FMT " %%RH",
                CENTI_ARG(s.temp_cC), CENTI_ARG(s.rh_cP));
        }
        else
        {
            LOG(" | HDC2010 read error");
        }
    }
    if (haveSht)
    {
        if (Shtc3_measure(i2c, &t2, &h2))
        {
            LOG(" | SHTC3 " CENTI_FMT " C " CENTI_FMT " %%RH", CENTI_ARG(t2), CENTI_ARG(h2));
        }
        else
        {
            LOG(" | SHTC3 read error");
        }
    }
    LOG(" | INT edges=%lu\r\n", (unsigned long)hdcIntCount);
}

void *mainThread(void *arg0)
{
    I2C_Handle i2c;
    I2C_Params i2cParams;
    bool haveHdc = false, haveSht = false;
    uint32_t n = 0;

    (void)arg0;

    GPIO_init();
    I2C_init();
    BatteryMonitor_init();
    Temperature_init();

    LOG_INIT(CONFIG_UART_LOG);
    LOG("\r\n\r\n==== %s-%s %s (built " __DATE__ " " __TIME__ ") ====\r\n",
        BSN_BOARD_NAME, BSN_HW_REVISION, FW_VERSION);

    GPIO_setCallback(CONFIG_GPIO_HDC_INT, hdcIntCallback);
    GPIO_enableInt(CONFIG_GPIO_HDC_INT);

    testDevice();
    testClocks();
    testSupply();

    I2C_Params_init(&i2cParams);
    i2cParams.bitRate = I2C_400kHz;
    i2c = I2C_open(CONFIG_I2C_SENSOR, &i2cParams);
    check(i2c != NULL, "I2C open", "");
    if (i2c != NULL)
    {
        scanBus(i2c);
        haveHdc = testHdc2010(i2c);
        haveSht = testShtc3(i2c);
    }

    LOG("==== Self-test: %u passed, %u failed -> %s ====\r\n\r\n",
        passCount, failCount, failCount ? "FAIL" : "PASS");

    while (1)
    {
        if (i2c != NULL)
        {
            printSample(i2c, haveHdc, haveSht, n++);
        }
        sleep(SAMPLE_PERIOD_S);
    }
}
