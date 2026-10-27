/*
 * app_main.c - BSN-N54 BLE temperature/humidity broadcaster
 *
 * Same behaviour and build options as firmware/C23/ble_sensor, so the current
 * measurements line up:
 *  - one legacy non-connectable advertising set on all three channels,
 *    BTHome v2 payload (bthome.c, byte-identical layout to C23, name "BSN-N54")
 *  - every SENSOR_PERIOD_S the HDC2010 and VDD are read and the payload is
 *    reloaded. The Zephyr host updates the data synchronously, so unlike the
 *    C23 build there are no extra 1 s wake-ups.
 *
 * The identity (static random) address from FICR is used, so the address
 * printed at boot is the one a scanner shows.
 */
#include <stdbool.h>
#include <stdint.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>

#include "bsn_board.h"
#include "bsn_log.h"
#include "bsn_vdd.h"
#include "bthome.h"
#include "hdc2010.h"
#include "shtc3.h"

#define FW_VERSION          "ble_sensor 0.1.0"

/* Build-time overrides for current measurements (see makefile) */
#ifndef SENSOR_PERIOD_S
#define SENSOR_PERIOD_S     10 /* 0: read once at boot, then never wake for it */
#endif
#ifndef ADV_INTERVAL_MS
#define ADV_INTERVAL_MS     1000
#endif
#ifndef ADV_ENABLE
#define ADV_ENABLE          1  /* 0: start the stack but never advertise (floor with the stack idle) */
#endif

#define AD_MAX_FIELDS       4

static const struct device *const i2c = DEVICE_DT_GET(DT_NODELABEL(sensor_i2c));
static const struct gpio_dt_spec hdcInt = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), hdc_int_gpios);

static uint8_t advData[BTHOME_ADV_MAX_LEN];
static struct bt_data ad[AD_MAX_FIELDS];

/* Splits the raw advertising data from BtHome_buildAdv into bt_data fields */
static size_t toBtData(const uint8_t *raw, size_t len)
{
    size_t n = 0, i = 0;

    while (i + 1 < len && n < AD_MAX_FIELDS)
    {
        uint8_t fieldLen = raw[i];

        if (fieldLen == 0 || i + 1 + fieldLen > len)
        {
            break;
        }
        ad[n].type     = raw[i + 1];
        ad[n].data_len = fieldLen - 1;
        ad[n].data     = &raw[i + 2];
        n++;
        i += 1 + fieldLen;
    }
    return n;
}

static bool readSensor(bool hdcOk, BtHome_Reading *r)
{
    Hdc2010_Sample s;

    r->vdds_mV = BsnVdd_read_mV();
    r->sensorValid = false;
    /* Reading the data registers also clears DRDY and releases the INT pin */
    if (hdcOk && Hdc2010_trigger(i2c, HDC2010_I2C_ADDR))
    {
        k_usleep(2000); /* 14-bit T + RH conversion is about 1.3 ms */
        if (Hdc2010_readSample(i2c, HDC2010_I2C_ADDR, &s))
        {
            r->temp_cC = s.temp_cC;
            r->rh_cP = s.rh_cP;
            r->sensorValid = true;
        }
    }
    r->packetId++;

    if (r->sensorValid)
    {
        LOG("[SNS] #%u " CENTI_FMT " C " CENTI_FMT " %%RH VDD %u mV\r\n", r->packetId,
            CENTI_ARG(r->temp_cC), CENTI_ARG(r->rh_cP), r->vdds_mV);
    }
    else
    {
        LOG("[SNS] #%u sensor read failed, VDD %u mV\r\n", r->packetId, r->vdds_mV);
    }
    return r->sensorValid;
}

int main(void)
{
    BtHome_Reading reading = {0};
    bt_addr_le_t addr;
    size_t idCount = 1;
    size_t n;
    bool hdcOk;
    int err;
    const struct bt_le_adv_param advParam = BT_LE_ADV_PARAM_INIT(
        BT_LE_ADV_OPT_USE_IDENTITY,
        ADV_INTERVAL_MS * 8 / 5, /* 0.625 ms units */
        ADV_INTERVAL_MS * 8 / 5,
        NULL);

    LOG("\r\n\r\n==== %s-%s %s (built " __DATE__ " " __TIME__ ") ====\r\n",
        BSN_BOARD_NAME, BSN_HW_REVISION, FW_VERSION);

    /* The HDC2010 INT output is high-Z until configured; the pull-down keeps it from floating */
    gpio_pin_configure_dt(&hdcInt, GPIO_INPUT);

    hdcOk = device_is_ready(i2c) && Hdc2010_init(i2c, HDC2010_I2C_ADDR);
    LOG("[SNS] HDC2010 %s\r\n", hdcOk ? "ok" : "NOT FOUND - advertising battery only");
    /* After power-on the SHTC3 idles at about 45 uA until told to sleep */
    if (device_is_ready(i2c) && Shtc3_sleep(i2c))
    {
        LOG("[SNS] SHTC3 put to sleep\r\n");
    }

    err = bt_enable(NULL);
    if (err)
    {
        LOG("[BLE] bt_enable failed: %d\r\n", err);
        return 0;
    }
    bt_id_get(&addr, &idCount);
    LOG("[BLE] stack ready, address %02X:%02X:%02X:%02X:%02X:%02X\r\n",
        addr.a.val[5], addr.a.val[4], addr.a.val[3], addr.a.val[2], addr.a.val[1], addr.a.val[0]);

    readSensor(hdcOk, &reading);
    n = toBtData(advData, BtHome_buildAdv(advData, &reading, CONFIG_BT_DEVICE_NAME));
#if ADV_ENABLE
    err = bt_le_adv_start(&advParam, ad, n, NULL, 0);
    if (err)
    {
        LOG("[BLE] advertising start failed: %d\r\n", err);
        return 0;
    }
    LOG("[BLE] advertising started (interval %u ms)\r\n", (unsigned int)ADV_INTERVAL_MS);
#else
    ARG_UNUSED(advParam);
    ARG_UNUSED(n);
#endif

#if SENSOR_PERIOD_S == 0
    /* Sensor off: keep this reading in the payload, then never wake again */
    while (1)
    {
        k_sleep(K_FOREVER);
    }
#else
    while (1)
    {
        k_sleep(K_SECONDS(SENSOR_PERIOD_S));
        readSensor(hdcOk, &reading);
        n = toBtData(advData, BtHome_buildAdv(advData, &reading, CONFIG_BT_DEVICE_NAME));
#if ADV_ENABLE
        err = bt_le_adv_update_data(ad, n, NULL, 0);
        if (err)
        {
            LOG("[BLE] update failed: %d\r\n", err);
        }
#endif
    }
#endif
    return 0;
}
