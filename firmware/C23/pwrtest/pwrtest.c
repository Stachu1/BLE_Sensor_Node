/*
 * pwrtest.c - BSN-C23 static current test
 *
 * Puts the board into one fixed power state, chosen at build time, so the
 * current can be read on a slow, precise ammeter in series with the supply.
 * There is no BLE stack and no UART: nothing else runs.
 *
 *   make MODE=standby    sleep forever (standby between RTOS ticks)  -> I_floor
 *   make MODE=idle       standby disallowed, CPU halted in WFI
 *   make MODE=active     CPU spinning at 48 MHz
 *   make MODE=shutdown   shutdown after BOOT_DELAY_S; only reset/power-on wakes it
 *   make MODE=sensor     HDC2010 + VDDS reading every PERIOD_MS, standby in between
 *   make MODE=sensor_irq     HDC2010 in auto mode (HDC_AMM); its DRDY wakes the MCU from standby
 *   make MODE=shutdown_wake  HDC2010 in auto mode; its DRDY wakes the MCU from shutdown,
 *                            which reboots, reads the sample and shuts down again
 *
 * Every mode first sends the SHTC3 (U2) its sleep command: after power-on it
 * idles at about 45 uA. Build with SHTC3_SLEEP=0 to leave it idle.
 *
 * Every mode then waits BOOT_DELAY_S in standby, so a debugger can still
 * attach after a reset and the meter can settle on the boot transient.
 *
 * For MODE=sensor the charge of one sensor event is
 *   Q_sensor = (I_sensor - I_standby) * PERIOD_MS
 * and likewise against the HDC2010 auto-mode period for the two IRQ modes,
 * with I_shutdown as the reference for MODE=shutdown_wake.
 */
#include <stdbool.h>
#include <stdint.h>
#include <unistd.h>

#include <ti/drivers/BatteryMonitor.h>
#include <ti/drivers/GPIO.h>
#include <ti/drivers/I2C.h>
#include <ti/drivers/Power.h>
#include <ti/drivers/dpl/SemaphoreP.h>
#include <ti/drivers/power/PowerCC23X0.h>

#include "ti_drivers_config.h"

#include "bsn_board.h"
#include "hdc2010.h"
#include "shtc3.h"

#define MODE_STANDBY    0
#define MODE_IDLE       1
#define MODE_ACTIVE     2
#define MODE_SHUTDOWN   3
#define MODE_SENSOR     4
#define MODE_SENSOR_IRQ 5
#define MODE_SHUTDOWN_WAKE 6

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

/* Kept in RAM so the debugger can confirm which build is running */
volatile uint32_t pwrMode = PWR_MODE;
volatile uint32_t sensorEvents;
volatile uint32_t sensorErrors;
volatile Hdc2010_Sample lastSample;
volatile uint32_t lastVdds_mV;
volatile bool shtc3Asleep;
volatile uint32_t shutdownRefused;

/* Sends the SHTC3 its sleep command. A NACK just means U2 is not fitted. */
static void sleepShtc3(void)
{
    I2C_Handle i2c;
    I2C_Params params;

    I2C_Params_init(&params);
    i2c = I2C_open(CONFIG_I2C_SENSOR, &params);
    if (i2c != NULL)
    {
        shtc3Asleep = Shtc3_sleep(i2c);
        I2C_close(i2c);
    }
}

#if PWR_MODE == MODE_SENSOR
/* usleep() rejects 1 000 000 us or more (POSIX) and returns at once */
static void sleepMs(uint32_t ms)
{
    if (ms >= 1000)
    {
        sleep(ms / 1000);
    }
    if (ms % 1000)
    {
        usleep((ms % 1000) * 1000UL);
    }
}

static void runSensor(void)
{
    I2C_Handle i2c;
    I2C_Params params;
    Hdc2010_Sample s;
    bool ok;

    BatteryMonitor_init();
    I2C_Params_init(&params);
    params.bitRate = I2C_400kHz;
    /* Kept open between readings, as in ble_sensor */
    i2c = I2C_open(CONFIG_I2C_SENSOR, &params);
    ok = (i2c != NULL) && Hdc2010_init(i2c, HDC2010_I2C_ADDR);

    while (1)
    {
        /* Same sequence as ble_sensor's sensor task */
        lastVdds_mV = BatteryMonitor_getVoltage();
        if (ok && Hdc2010_trigger(i2c, HDC2010_I2C_ADDR))
        {
            usleep(2000); /* 14-bit T + RH conversion is about 1.3 ms */
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
        sleepMs(PERIOD_MS);
    }
}
#endif

#if PWR_MODE == MODE_SENSOR_IRQ || PWR_MODE == MODE_SHUTDOWN_WAKE
static I2C_Handle openSensorI2c(void)
{
    I2C_Params params;

    I2C_Params_init(&params);
    params.bitRate = I2C_400kHz;
    return I2C_open(CONFIG_I2C_SENSOR, &params);
}

/* Reads the result, then the status register, which releases INT */
static void readAutoSample(I2C_Handle i2c)
{
    Hdc2010_Sample s;
    bool ready;

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
#endif

#if PWR_MODE == MODE_SENSOR_IRQ
static SemaphoreP_Struct drdyStruct;
static SemaphoreP_Handle drdy;

static void drdyCallback(uint_least8_t index)
{
    (void)index;
    SemaphoreP_post(drdy);
}

/* The HDC2010 measures on its own; its DRDY edge wakes the MCU out of standby */
static void runSensorIrq(void)
{
    I2C_Handle i2c;

    drdy = SemaphoreP_constructBinary(&drdyStruct, 0);
    i2c = openSensorI2c();
    if (i2c == NULL || !Hdc2010_init(i2c, HDC2010_I2C_ADDR))
    {
        sensorErrors++;
        while (1)
        {
            sleep(3600);
        }
    }
    GPIO_setCallback(CONFIG_GPIO_HDC_INT, drdyCallback);
    GPIO_enableInt(CONFIG_GPIO_HDC_INT);
    Hdc2010_startAuto(i2c, HDC2010_I2C_ADDR, HDC_AMM);

    while (1)
    {
        SemaphoreP_pend(drdy, SemaphoreP_WAIT_FOREVER);
        readAutoSample(i2c);
    }
}
#endif

#if PWR_MODE == MODE_SHUTDOWN_WAKE
/* Arms the DRDY wake-up and enters shutdown. Never returns unless refused. */
static void shutdownUntilDrdy(void)
{
    GPIO_setConfig(CONFIG_GPIO_HDC_INT,
                   GPIO_CFG_INPUT | GPIO_CFG_PULL_DOWN_INTERNAL | GPIO_CFG_SHUTDOWN_WAKE_HIGH);
    /* A stale event flag on the wake-up pin makes Power_shutdown() refuse */
    GPIO_clearInt(CONFIG_GPIO_HDC_INT);
    Power_shutdown(0, 0);
    /* Refused, e.g. INT already high or a debugger attached */
    shutdownRefused++;
    while (1)
    {
        sleep(3600);
    }
}

/*
 * Woken from shutdown by DRDY: the MCU has rebooted, but the HDC2010 kept its
 * auto mode configuration. Read the sample (which releases INT) and go back down.
 */
static void shutdownWakeEvent(void)
{
    I2C_Handle i2c = openSensorI2c();

    if (i2c != NULL)
    {
        readAutoSample(i2c);
        I2C_close(i2c);
    }
    shutdownUntilDrdy();
}

/* Power-on: configure the HDC2010 auto mode once, then shut down */
static void runShutdownWake(void)
{
    I2C_Handle i2c = openSensorI2c();

    if (i2c == NULL || !Hdc2010_init(i2c, HDC2010_I2C_ADDR) ||
        !Hdc2010_startAuto(i2c, HDC2010_I2C_ADDR, HDC_AMM))
    {
        sensorErrors++;
        while (1)
        {
            sleep(3600);
        }
    }
    I2C_close(i2c);
    shutdownUntilDrdy();
}
#endif

void *mainThread(void *arg0)
{
#if PWR_MODE == MODE_SHUTDOWN_WAKE
    /* Must be read before the IO latches are released */
    bool ioWake = (PowerLPF3_getResetReason() == PowerLPF3_RESET_SHUTDOWN_IO);
#endif

    (void)arg0;

    GPIO_init(); /* applies the pull-down on the HDC2010 INT line */
    I2C_init();
#if PWR_MODE == MODE_SHUTDOWN_WAKE
    /* IOs stay frozen after a shutdown until released */
    PowerLPF3_releaseLatches();
    if (ioWake)
    {
        shutdownWakeEvent();
    }
#endif
#if SHTC3_SLEEP
    sleepShtc3();
#endif

    sleep(BOOT_DELAY_S);

#if PWR_MODE == MODE_STANDBY
    while (1)
    {
        sleep(3600);
    }
#elif PWR_MODE == MODE_IDLE
    Power_setConstraint(PowerLPF3_DISALLOW_STANDBY);
    while (1)
    {
        sleep(3600);
    }
#elif PWR_MODE == MODE_ACTIVE
    while (1)
    {
        __asm volatile ("nop");
    }
#elif PWR_MODE == MODE_SHUTDOWN
    Power_shutdown(0, 0);
    /* Only reached if shutdown was refused (e.g. a debugger is attached) */
    while (1)
    {
        sleep(3600);
    }
#elif PWR_MODE == MODE_SENSOR
    runSensor();
#elif PWR_MODE == MODE_SENSOR_IRQ
    runSensorIrq();
#elif PWR_MODE == MODE_SHUTDOWN_WAKE
    runShutdownWake();
#else
#error "Unknown PWR_MODE"
#endif
    return NULL;
}
