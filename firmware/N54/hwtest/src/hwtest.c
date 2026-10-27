/*
 * hwtest.c - BSN-N54 bring-up self-test (no BLE stack)
 *
 * Runs a one-shot self-test at boot, prints a PASS/FAIL summary on the UART
 * (TP9, 115200 8N1), then prints one sensor line per period until power-off.
 *
 *  1. Reset reason, FICR BLE address, part and variant
 *  2. Clocks: HFXO (X1, 32 MHz) and LFXO (X2, 32.768 kHz) start
 *  3. Supply: VDD from the SAADC, die temperature
 *  4. I2C: bus scan, HDC2010 IDs, SHTC3 probe and reading
 *  5. HDC2010 measurement, plausibility check, and the DRDY/INT line (P0.01)
 *     checked both as a level and as an edge interrupt
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include <zephyr/device.h>
#include <zephyr/drivers/clock_control.h>
#include <zephyr/drivers/clock_control/nrf_clock_control.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/hwinfo.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/kernel.h>

#include <hal/nrf_clock.h>
#include <nrfx.h>

#include "bsn_board.h"
#include "bsn_log.h"
#include "bsn_vdd.h"
#include "hdc2010.h"
#include "shtc3.h"

#if !BSN_LOG_ENABLE
#error "hwtest reports only over the UART; build it with logging enabled"
#endif

#define FW_VERSION          "hwtest 0.1.0"
#define SAMPLE_PERIOD_S     2

/* Plausibility windows for an indoor lab bench */
#define VDD_MIN_MV          1700
#define VDD_MAX_MV          3700
#define TEMP_MIN_CC         (-1000)
#define TEMP_MAX_CC         5000

/* Clock start limits: the HFXO starts in well under 1 ms, the LFXO in up to about 0.5 s */
#define HFXO_TIMEOUT_MS     50
#define LFXO_TIMEOUT_MS     2000

static const struct device *const i2c = DEVICE_DT_GET(DT_NODELABEL(sensor_i2c));
static const struct device *const dieTemp = DEVICE_DT_GET_ONE(nordic_nrf_temp);
static const struct gpio_dt_spec hdcInt = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), hdc_int_gpios);

static struct gpio_callback hdcIntCb;
static volatile uint32_t hdcIntCount;
static unsigned int passCount, failCount;

static void hdcIntHandler(const struct device *port, struct gpio_callback *cb, uint32_t pins)
{
    ARG_UNUSED(port);
    ARG_UNUSED(cb);
    ARG_UNUSED(pins);
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

static const char *resetReasonStr(uint32_t cause)
{
    if (cause & RESET_PIN)            return "reset pin";
    if (cause & RESET_SOFTWARE)       return "software";
    if (cause & RESET_DEBUG)          return "debugger";
    if (cause & RESET_WATCHDOG)       return "watchdog";
    if (cause & RESET_LOW_POWER_WAKE) return "wake from System OFF";
    if (cause & RESET_CPU_LOCKUP)     return "CPU lockup";
    if (cause & RESET_BROWNOUT)       return "brown-out";
    if (cause == 0)                   return "power-on";
    return "other";
}

static void testDevice(void)
{
    uint32_t cause = 0;
    uint32_t a0 = NRF_FICR->DEVICEADDR[0];
    uint32_t a1 = NRF_FICR->DEVICEADDR[1];

    hwinfo_get_reset_cause(&cause);
    hwinfo_clear_reset_cause();
    LOG("Reset reason : %s (0x%08lX)\r\n", resetReasonStr(cause), (unsigned long)cause);
    /* Zephyr uses this as the static random identity address: top two bits set */
    LOG("BLE address  : %02X:%02X:%02X:%02X:%02X:%02X\r\n",
        (unsigned int)(((a1 >> 8) & 0xFF) | 0xC0), (unsigned int)(a1 & 0xFF),
        (unsigned int)(a0 >> 24), (unsigned int)((a0 >> 16) & 0xFF),
        (unsigned int)((a0 >> 8) & 0xFF), (unsigned int)(a0 & 0xFF));
    LOG("Part         : 0x%08lX variant 0x%08lX\r\n",
        (unsigned long)NRF_FICR->INFO.PART, (unsigned long)NRF_FICR->INFO.VARIANT);
}

/* Requests a clock through the nRF clock control on/off manager and times the start */
static int startClock(clock_control_subsys_t subsys, uint32_t timeoutMs, uint32_t *tookUs)
{
    struct onoff_manager *mgr = z_nrf_clock_control_get_onoff(subsys);
    struct onoff_client cli;
    int64_t t0 = k_uptime_ticks();
    int err, res = 0;

    if (mgr == NULL)
    {
        return -ENODEV;
    }
    sys_notify_init_spinwait(&cli.notify);
    err = onoff_request(mgr, &cli);
    if (err < 0)
    {
        return err;
    }
    do
    {
        err = sys_notify_fetch_result(&cli.notify, &res);
        if (err == -EAGAIN && k_ticks_to_ms_floor64(k_uptime_ticks() - t0) > timeoutMs)
        {
            return -ETIMEDOUT;
        }
    } while (err == -EAGAIN);
    *tookUs = (uint32_t)k_ticks_to_us_ceil64(k_uptime_ticks() - t0);
    return res;
}

static void testClocks(void)
{
    char d[48];
    uint32_t us = 0;
    int err;

    err = startClock(CLOCK_CONTROL_NRF_SUBSYS_HF, HFXO_TIMEOUT_MS, &us);
    if (err == 0)
    {
        snprintf(d, sizeof(d), "started in %lu us", (unsigned long)us);
    }
    else
    {
        snprintf(d, sizeof(d), "error %d", err);
    }
    check(err == 0, "HFXO 32 MHz (X1)", d);

    /* The LF clock already runs from boot (GRTC); check that it runs from the source the build selected */
#if defined(BSN_LFCLK_XTAL)
    const nrf_clock_lfclk_t want = NRF_CLOCK_LFCLK_XTAL;
    const char *lfName = "LFXO 32.768 kHz (X2)";
#else
    const nrf_clock_lfclk_t want = NRF_CLOCK_LFCLK_RC;
    const char *lfName = "LFRC 32.768 kHz";
#endif
    err = startClock(CLOCK_CONTROL_NRF_SUBSYS_LF, LFXO_TIMEOUT_MS, &us);
    if (err == 0)
    {
        nrf_clock_lfclk_t src = NRF_CLOCK_LFCLK_RC;
        bool running = nrf_clock_is_running(NRF_CLOCK, NRF_CLOCK_DOMAIN_LFCLK, &src);

        snprintf(d, sizeof(d), "source %s", src == NRF_CLOCK_LFCLK_XTAL ? "LFXO" :
                 src == NRF_CLOCK_LFCLK_RC ? "LFRC" : "other");
        check(running && src == want, lfName, d);
    }
    else
    {
        snprintf(d, sizeof(d), "error %d", err);
        check(false, lfName, d);
    }
}

static int readDieTemp(void)
{
    struct sensor_value v;

    if (!device_is_ready(dieTemp) || sensor_sample_fetch(dieTemp) != 0 ||
        sensor_channel_get(dieTemp, SENSOR_CHAN_DIE_TEMP, &v) != 0)
    {
        return -999;
    }
    return v.val1;
}

static void testSupply(void)
{
    char d[32];
    uint16_t mv = BsnVdd_read_mV();

    snprintf(d, sizeof(d), "%u mV", mv);
    check(mv >= VDD_MIN_MV && mv <= VDD_MAX_MV, "VDD", d);
    LOG("Die temp     : %d C\r\n", readDieTemp());
}

static void scanBus(void)
{
    uint8_t addr, b;
    bool found = false;

    LOG("I2C scan     :");
    for (addr = 0x08; addr < 0x78; addr++)
    {
        if (i2c_read(i2c, &b, 1, addr) == 0)
        {
            found = true;
            LOG(" 0x%02X", addr);
        }
    }
    LOG(found ? "\r\n" : " none (check pull-ups R2/R3, U3 solder joints)\r\n");
}

static bool testHdc2010(void)
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
    check(gpio_pin_get_dt(&hdcInt) == 0, "HDC INT idle low", "");

    edgesBefore = hdcIntCount;
    check(Hdc2010_trigger(i2c, HDC2010_I2C_ADDR), "HDC2010 trigger", "");
    for (i = 0; i < 50 && !intLevelSeen; i++)
    {
        k_msleep(1);
        intLevelSeen = gpio_pin_get_dt(&hdcInt) != 0;
    }
    check(intLevelSeen, "HDC INT level (P0.01)", intLevelSeen ? "" : "never went high within 50 ms");
    check(hdcIntCount != edgesBefore, "HDC INT edge IRQ", "");

    Hdc2010_readStatus(i2c, HDC2010_I2C_ADDR, &ready);
    check(ready, "HDC2010 DRDY status", "");
    check(gpio_pin_get_dt(&hdcInt) == 0, "HDC INT cleared", "");

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

static bool testShtc3(void)
{
    char d[48];
    uint16_t id = 0;
    int16_t t = 0;
    uint16_t h = 0;
    bool ok;

    ok = Shtc3_probe(i2c, &id);
    if (!ok)
    {
        /* U2 is optional: an empty footprint is not a failure */
        LOG("[INFO] %-22s not present\r\n", "SHTC3 (U2 @0x70)");
        return false;
    }
    snprintf(d, sizeof(d), "ID 0x%04X", id);
    check(true, "SHTC3 ID (U2 @0x70)", d);
    ok = Shtc3_measure(i2c, &t, &h);
    snprintf(d, sizeof(d), CENTI_FMT " C  " CENTI_FMT " %%RH", CENTI_ARG(t), CENTI_ARG(h));
    check(ok && t > TEMP_MIN_CC && t < TEMP_MAX_CC && h > 0 && h < 10000, "SHTC3 plausible", d);
    return ok;
}

static void printSample(bool haveHdc, bool haveSht, uint32_t n)
{
    Hdc2010_Sample s;
    int16_t t2;
    uint16_t h2;
    bool ready;

    LOG("#%lu VDD=%u mV die=%d C", (unsigned long)n, BsnVdd_read_mV(), readDieTemp());

    if (haveHdc)
    {
        Hdc2010_trigger(i2c, HDC2010_I2C_ADDR);
        k_usleep(2000);
        if (Hdc2010_readSample(i2c, HDC2010_I2C_ADDR, &s))
        {
            Hdc2010_readStatus(i2c, HDC2010_I2C_ADDR, &ready); /* releases INT */
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

int main(void)
{
    bool haveHdc = false, haveSht = false;
    uint32_t n = 0;

    LOG("\r\n\r\n==== %s-%s %s (built " __DATE__ " " __TIME__ ") ====\r\n",
        BSN_BOARD_NAME, BSN_HW_REVISION, FW_VERSION);

    gpio_pin_configure_dt(&hdcInt, GPIO_INPUT);
    gpio_init_callback(&hdcIntCb, hdcIntHandler, BIT(hdcInt.pin));
    gpio_add_callback_dt(&hdcInt, &hdcIntCb);
    gpio_pin_interrupt_configure_dt(&hdcInt, GPIO_INT_EDGE_RISING);

    testDevice();
    testClocks();
    testSupply();

    check(device_is_ready(i2c), "I2C ready (i2c30)", "");
    if (device_is_ready(i2c))
    {
        scanBus();
        haveHdc = testHdc2010();
        haveSht = testShtc3();
    }

    LOG("==== Self-test: %u passed, %u failed -> %s ====\r\n\r\n",
        passCount, failCount, failCount ? "FAIL" : "PASS");

    while (1)
    {
        if (device_is_ready(i2c))
        {
            printSample(haveHdc, haveSht, n++);
        }
        k_sleep(K_SECONDS(SAMPLE_PERIOD_S));
    }
    return 0;
}
