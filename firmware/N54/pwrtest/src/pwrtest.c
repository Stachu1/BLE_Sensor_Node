/*
 * pwrtest.c - BSN-N54 static current test
 *
 * Puts the board into one fixed power state, chosen at build time, so the
 * current can be read on a slow, precise ammeter in series with the supply.
 * There is no BLE stack and no UART: nothing else runs.
 *
 *   make MODE=standby     System ON idle forever (GRTC on LFXO)        -> I_floor
 *   make MODE=active      CPU spinning
 *   make MODE=shutdown    System OFF after BOOT_DELAY_S; only reset/power-on wakes it
 *   make MODE=sensor      HDC2010 + VDD reading every PERIOD_MS, idle in between
 *   make MODE=sensor_irq  HDC2010 in auto mode (HDC_AMM); its DRDY wakes the MCU from idle
 *
 * Every mode first sends the SHTC3 (U2) its sleep command: after power-on it
 * idles at about 45 uA. Build with SHTC3_SLEEP=0 to leave it idle.
 *
 * Every mode then waits BOOT_DELAY_S idle, so a debugger can still attach
 * after a reset and the meter can settle on the boot transient.
 *
 * For MODE=sensor the charge of one sensor event is
 *   Q_sensor = (I_sensor - I_standby) * PERIOD_MS
 * and likewise against the HDC2010 auto-mode period for MODE=sensor_irq.
 */
#include <stdbool.h>
#include <stdint.h>

#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/poweroff.h>

#include "bsn_board.h"
#include "bsn_vdd.h"
#include "hdc2010.h"
#include "shtc3.h"

#define MODE_STANDBY    0
#define MODE_ACTIVE     2
#define MODE_SHUTDOWN   3
#define MODE_SENSOR     4
#define MODE_SENSOR_IRQ 5

#ifndef PWR_MODE
#define PWR_MODE        MODE_STANDBY
#endif
#ifndef PERIOD_MS
#define PERIOD_MS       1000
#endif
#ifndef HDC_AMM
#define HDC_AMM         HDC2010_AMM_1S
#endif
#ifndef SHTC3_SLEEP
#define SHTC3_SLEEP     1
#endif
#ifndef BOOT_DELAY_S
#define BOOT_DELAY_S    5
#endif

static const struct device *const i2c = DEVICE_DT_GET(DT_NODELABEL(sensor_i2c));
static const struct gpio_dt_spec hdcInt = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), hdc_int_gpios);

/* Kept in RAM so the debugger can confirm which build is running */
volatile uint32_t pwrMode = PWR_MODE;
volatile uint32_t sensorEvents;
volatile uint32_t sensorErrors;
volatile Hdc2010_Sample lastSample;
volatile uint32_t lastVdds_mV;
volatile bool shtc3Asleep;

#if PWR_MODE == MODE_SENSOR
static void runSensor(void)
{
    Hdc2010_Sample s;
    bool ok = device_is_ready(i2c) && Hdc2010_init(i2c, HDC2010_I2C_ADDR);

    while (1)
    {
        /* Same sequence as ble_sensor's sensor read */
        lastVdds_mV = BsnVdd_read_mV();
        if (ok && Hdc2010_trigger(i2c, HDC2010_I2C_ADDR))
        {
            k_usleep(2000); /* 14-bit T + RH conversion is about 1.3 ms */
            if (Hdc2010_readSample(i2c, HDC2010_I2C_ADDR, &s))
            {
                lastSample = s;
            }
            else
            {
                sensorErrors++;
            }
        }
        else
        {
            sensorErrors++;
        }
        sensorEvents++;
        k_msleep(PERIOD_MS);
    }
}
#endif

#if PWR_MODE == MODE_SENSOR_IRQ
static K_SEM_DEFINE(drdy, 0, 1);
static struct gpio_callback drdyCb;

static void drdyHandler(const struct device *port, struct gpio_callback *cb, uint32_t pins)
{
    ARG_UNUSED(port);
    ARG_UNUSED(cb);
    ARG_UNUSED(pins);
    k_sem_give(&drdy);
}

/* The HDC2010 measures on its own; its DRDY edge wakes the MCU out of idle */
static void runSensorIrq(void)
{
    Hdc2010_Sample s;
    bool ready;

    if (!device_is_ready(i2c) || !Hdc2010_init(i2c, HDC2010_I2C_ADDR))
    {
        sensorErrors++;
        while (1)
        {
            k_sleep(K_FOREVER);
        }
    }
    gpio_init_callback(&drdyCb, drdyHandler, BIT(hdcInt.pin));
    gpio_add_callback_dt(&hdcInt, &drdyCb);
    gpio_pin_interrupt_configure_dt(&hdcInt, GPIO_INT_EDGE_RISING);
    Hdc2010_startAuto(i2c, HDC2010_I2C_ADDR, HDC_AMM);

    while (1)
    {
        k_sem_take(&drdy, K_FOREVER);
        /* Reads the result, then the status register, which releases INT */
        if (Hdc2010_readSample(i2c, HDC2010_I2C_ADDR, &s) &&
            Hdc2010_readStatus(i2c, HDC2010_I2C_ADDR, &ready))
        {
            lastSample = s;
        }
        else
        {
            sensorErrors++;
        }
        sensorEvents++;
    }
}
#endif

int main(void)
{
    /* The HDC2010 INT output is high-Z until configured; the pull-down keeps it from floating */
    gpio_pin_configure_dt(&hdcInt, GPIO_INPUT);

#if SHTC3_SLEEP
    /* A NACK just means U2 is not fitted */
    if (device_is_ready(i2c))
    {
        shtc3Asleep = Shtc3_sleep(i2c);
    }
#endif

    k_sleep(K_SECONDS(BOOT_DELAY_S));

#if PWR_MODE == MODE_STANDBY
    while (1)
    {
        k_sleep(K_FOREVER);
    }
#elif PWR_MODE == MODE_ACTIVE
    while (1)
    {
        __asm volatile ("nop");
    }
#elif PWR_MODE == MODE_SHUTDOWN
    /* Does not return. A debugger attached keeps the debug domain powered (emulated System OFF). */
    sys_poweroff();
#elif PWR_MODE == MODE_SENSOR
    runSensor();
#elif PWR_MODE == MODE_SENSOR_IRQ
    runSensorIrq();
#else
#error "Unknown PWR_MODE"
#endif
    return 0;
}
