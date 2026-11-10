/*
 * app_main.c - BSN-C23 BLE temperature/humidity broadcaster
 *
 * Two tasks:
 *  - BLE (BLEAppUtil): starts one legacy non-connectable advertising set and
 *    reloads its payload whenever a new reading arrives.
 *  - Sensor (pthread): every SENSOR_PERIOD_S reads the HDC2010 and VDDS, then
 *    asks the BLE task to update the advertising data. GAP calls must run in
 *    the BLE task context, hence BLEAppUtil_invokeFunctionNoData().
 *
 * DRDY_AMM > 0 (make DRDY=4) is the event-driven variant: the HDC2010 runs in
 * auto mode, each DRDY wakes the sensor task, which reads the result and asks
 * the BLE task to load it and send exactly one advertising event. Advertising
 * is off between events, so there is no periodic advertising and no reload.
 *
 * Payload format: BTHome v2 (see bthome.h).
 */
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <unistd.h>

#include <ti/drivers/BatteryMonitor.h>
#include <ti/drivers/GPIO.h>
#include <ti/drivers/I2C.h>
#include <ti/drivers/dpl/SemaphoreP.h>

#include "ti_ble_config.h"
#include "ti_drivers_config.h"
#include "ti/ble/app_util/framework/bleapputil_api.h"

#include "bsn_board.h"
#include "bsn_log.h"
#include "bthome.h"
#include "hdc2010.h"
#include "shtc3.h"

#define FW_VERSION          "ble_sensor 0.1.0"
#define SENSOR_STACK_SIZE   1536

/* Build-time overrides for current measurements (see makefile) */
#ifndef SENSOR_PERIOD_S
#define SENSOR_PERIOD_S     10 /* 0: read once at boot, then the sensor task parks */
#endif
#ifndef ADV_INTERVAL_MS
#define ADV_INTERVAL_MS     0  /* 0: keep the interval from ble_sensor.syscfg */
#endif
#ifndef ADV_ENABLE
#define ADV_ENABLE          1  /* 0: start the stack but never advertise (floor with the stack idle) */
#endif
#ifndef ADV_TX_DBM
#define ADV_TX_DBM          0
#endif
#ifndef DRDY_AMM
#define DRDY_AMM            0  /* 1..7: one advert per HDC2010 DRDY at this auto rate (HDC2010_AMM_*) */
#endif

/* Advertising data; the stack transmits straight from this buffer */
static uint8_t advData[BTHOME_ADV_MAX_LEN];
static uint8_t advHandle;
static volatile bool advRunning;
/* packetId of the reading currently in the advertising data */
static volatile uint8_t advLoadedId;

/* Latest reading. The sensor task replaces it with a single struct copy (no
 * blocking call in between, no time slicing), and the BLE task reads it. */
static BtHome_Reading reading;

static void Adv_eventHandler(uint32 event, BLEAppUtil_msgHdr_t *pMsgData);

static BLEAppUtil_EventHandler_t advEventHandler =
{
    .handlerType   = BLEAPPUTIL_GAP_ADV_TYPE,
    .pEventHandler = Adv_eventHandler,
    .eventMask     = BLEAPPUTIL_ADV_START_AFTER_ENABLE | BLEAPPUTIL_ADV_END_AFTER_DISABLE
};

static BLEAppUtil_AdvInit_t advInit =
{
    .advDataLen      = 0, /* set before use */
    .advData         = advData,
    .scanRespDataLen = 0,
    .scanRespData    = NULL,
    .advParam        = &advParams1
};

#if DRDY_AMM
/* One advertising event per enable, then the set stops by itself */
static const BLEAppUtil_AdvStart_t advStartOne =
{
    .enableOptions       = GAP_ADV_ENABLE_OPTIONS_USE_MAX_EVENTS,
    .durationOrMaxEvents = 1
};
#elif ADV_ENABLE
static const BLEAppUtil_AdvStart_t advStart =
{
    .enableOptions       = GAP_ADV_ENABLE_OPTIONS_USE_MAX,
    .durationOrMaxEvents = 0
};
#endif

BLEAppUtil_GeneralParams_t appMainParams =
{
    .taskPriority         = 1,
    .taskStackSize        = 2048, /* basic_ble uses 1024; logging needs more */
    .profileRole          = (BLEAppUtil_Profile_Roles_e)(HOST_CONFIG),
    .addressMode          = DEFAULT_ADDRESS_MODE,
    .deviceNameAtt        = attDeviceName,
    .pDeviceRandomAddress = pRandomAddress,
};

BLEAppUtil_PeriCentParams_t appMainPeriCentParams;

static void Adv_eventHandler(uint32 event, BLEAppUtil_msgHdr_t *pMsgData)
{
    static bool logged;

    (void)pMsgData;

    /* Logging only. These events can be dropped under queue pressure, and every
     * payload reload produces another disable/enable pair. */
    if (event == BLEAPPUTIL_ADV_START_AFTER_ENABLE && !logged)
    {
        logged = true;
        LOG("[BLE] advertising started (interval %u ms)\r\n",
            (unsigned int)(advParams1.primIntMin * 5 / 8));
    }
}

/* Runs in the BLE task context */
static void Adv_reload(char *pData)
{
    bStatus_t st;
    size_t len;

    (void)pData;
    if (!advRunning)
    {
        return;
    }
    st = GapAdv_prepareLoadByHandle(advHandle, GAP_ADV_FREE_OPTION_DONT_FREE);
    if (st != SUCCESS)
    {
        LOG("[BLE] prepareLoad failed: 0x%02X\r\n", st);
        return;
    }
    len = BtHome_buildAdv(advData, &reading, (const char *)attDeviceName);
    st = GapAdv_loadByHandle(advHandle, GAP_ADV_DATA_TYPE_ADV, (uint16)len, advData);
    if (st == SUCCESS)
    {
        advLoadedId = reading.packetId;
    }
    else
    {
        /* An unfinished prepare/load would block every later reload */
        GapAdv_abortLoad();
        LOG("[BLE] loadByHandle failed: 0x%02X\r\n", st);
    }
}

#if DRDY_AMM
/* Runs in the BLE task context. Advertising is off here (the single event of the
 * previous DRDY ended seconds ago), so loading the data disables nothing. */
static void Adv_sendOne(char *pData)
{
    bStatus_t st;
    size_t len;

    (void)pData;
    if (!advRunning)
    {
        return;
    }
    st = GapAdv_prepareLoadByHandle(advHandle, GAP_ADV_FREE_OPTION_DONT_FREE);
    if (st != SUCCESS)
    {
        LOG("[BLE] prepareLoad failed: 0x%02X\r\n", st);
        return;
    }
    len = BtHome_buildAdv(advData, &reading, (const char *)attDeviceName);
    st = GapAdv_loadByHandle(advHandle, GAP_ADV_DATA_TYPE_ADV, (uint16)len, advData);
    if (st != SUCCESS)
    {
        GapAdv_abortLoad();
        LOG("[BLE] loadByHandle failed: 0x%02X\r\n", st);
        return;
    }
    advLoadedId = reading.packetId;
    st = BLEAppUtil_advStart(advHandle, &advStartOne);
    if (st != SUCCESS)
    {
        LOG("[BLE] advStart failed: 0x%02X\r\n", st);
    }
}

static SemaphoreP_Struct drdyStruct;
static SemaphoreP_Handle drdy;

static void drdyCallback(uint_least8_t index)
{
    (void)index;
    SemaphoreP_post(drdy);
}
#endif

static void criticalErrorHandler(int32 errorCode, void *pInfo)
{
    (void)pInfo;
    LOG("[BLE] critical error 0x%08lX\r\n", (unsigned long)errorCode);
}

static void App_StackInitDoneHandler(gapDeviceInitDoneEvent_t *initDone)
{
    bStatus_t st;

    LOG("[BLE] stack ready, address %s\r\n", BLEAppUtil_convertBdAddr2Str(initDone->devAddr));

    advInit.advDataLen = (uint16)BtHome_buildAdv(advData, &reading, (const char *)attDeviceName);
#if ADV_INTERVAL_MS > 0
    /* Interval in 0.625 ms units */
    advParams1.primIntMin = (uint32)ADV_INTERVAL_MS * 8 / 5;
    advParams1.primIntMax = advParams1.primIntMin;
#endif
    /* The stack rounds down to the nearest PA table entry */
    advParams1.txPower = ADV_TX_DBM;

    st = BLEAppUtil_registerEventHandler(&advEventHandler);
    if (st == SUCCESS)
    {
        st = BLEAppUtil_initAdvSet(&advHandle, &advInit);
    }
#if ADV_ENABLE && !DRDY_AMM
    if (st == SUCCESS)
    {
        st = BLEAppUtil_advStart(advHandle, &advStart);
    }
#endif
    if (st == SUCCESS)
    {
        advRunning = true;
        advLoadedId = reading.packetId;
    }
    else
    {
        LOG("[BLE] advertising setup failed: 0x%02X\r\n", st);
    }
}

static void *sensorThread(void *arg0)
{
    I2C_Handle i2c;
    I2C_Params i2cParams;
    Hdc2010_Sample s;
    BtHome_Reading next = {0};
    bool hdcOk;
    int t;

    (void)arg0;

    LOG_INIT(CONFIG_UART_LOG);
    LOG("\r\n\r\n==== %s-%s %s (built " __DATE__ " " __TIME__ ") ====\r\n",
        BSN_BOARD_NAME, BSN_HW_REVISION, FW_VERSION);

    I2C_Params_init(&i2cParams);
    i2cParams.bitRate = I2C_400kHz;
    i2c = I2C_open(CONFIG_I2C_SENSOR, &i2cParams);
    hdcOk = (i2c != NULL) && Hdc2010_init(i2c, HDC2010_I2C_ADDR);
    LOG("[SNS] HDC2010 %s\r\n", hdcOk ? "ok" : "NOT FOUND - advertising battery only");
    /* After power-on the SHTC3 idles at about 45 uA until told to sleep. U2 is
     * not on rev B (DNP on rev A, fitted on some boards); a NACK means it is absent. */
    if (i2c != NULL && Shtc3_sleep(i2c))
    {
        LOG("[SNS] SHTC3 fitted, put to sleep\r\n");
    }

#if DRDY_AMM
    /* The rising-edge trigger is set here, not in SysConfig: an interrupt armed on
     * the floating line before the sensor is configured kept the device awake. */
    drdy = SemaphoreP_constructBinary(&drdyStruct, 0);
    if (hdcOk)
    {
        GPIO_setConfig(CONFIG_GPIO_HDC_INT,
                       GPIO_CFG_INPUT | GPIO_CFG_PULL_DOWN_INTERNAL | GPIO_CFG_IN_INT_RISING);
        GPIO_setCallback(CONFIG_GPIO_HDC_INT, drdyCallback);
        GPIO_enableInt(CONFIG_GPIO_HDC_INT);
        hdcOk = Hdc2010_startAuto(i2c, HDC2010_I2C_ADDR, DRDY_AMM);
    }
    if (!hdcOk)
    {
        LOG("[SNS] no HDC2010 auto mode, nothing to send\r\n");
        while (1)
        {
            sleep(3600);
        }
    }
    while (1)
    {
        bool ready;

        SemaphoreP_pend(drdy, SemaphoreP_WAIT_FOREVER);
        next.vdds_mV = BatteryMonitor_getVoltage();
        /* Reading the status register releases INT for the next edge */
        next.sensorValid = Hdc2010_readSample(i2c, HDC2010_I2C_ADDR, &s) &&
                           Hdc2010_readStatus(i2c, HDC2010_I2C_ADDR, &ready);
        if (next.sensorValid)
        {
            next.temp_cC = s.temp_cC;
            next.rh_cP = s.rh_cP;
        }
        next.packetId++;
        reading = next;
        BLEAppUtil_invokeFunctionNoData(Adv_sendOne);
        LOG("[SNS] #%u " CENTI_FMT " C " CENTI_FMT " %%RH VDDS %u mV\r\n", next.packetId,
            CENTI_ARG(next.temp_cC), CENTI_ARG(next.rh_cP), next.vdds_mV);
    }
#endif
    while (1)
    {
        next.vdds_mV = BatteryMonitor_getVoltage();
        next.sensorValid = false;
        /* Reading the data registers also clears DRDY and releases the INT pin */
        if (hdcOk && Hdc2010_trigger(i2c, HDC2010_I2C_ADDR))
        {
            usleep(2000); /* 14-bit T + RH conversion is about 1.3 ms */
            if (Hdc2010_readSample(i2c, HDC2010_I2C_ADDR, &s))
            {
                next.temp_cC = s.temp_cC;
                next.rh_cP = s.rh_cP;
                next.sensorValid = true;
            }
        }
        next.packetId++;
        reading = next;

        if (next.sensorValid)
        {
            LOG("[SNS] #%u " CENTI_FMT " C " CENTI_FMT " %%RH VDDS %u mV\r\n", next.packetId,
                CENTI_ARG(next.temp_cC), CENTI_ARG(next.rh_cP), next.vdds_mV);
        }
        else
        {
            LOG("[SNS] #%u sensor read failed, VDDS %u mV\r\n", next.packetId, next.vdds_mV);
        }

        /* Ask the BLE task to reload the payload, and retry once a second until
         * it has (advertising may not have started yet, or a reload failed). */
        BLEAppUtil_invokeFunctionNoData(Adv_reload);
#if SENSOR_PERIOD_S == 0
        /* Sensor off: keep this reading in the payload, then never wake again */
        while (ADV_ENABLE && advLoadedId != next.packetId)
        {
            sleep(1);
            BLEAppUtil_invokeFunctionNoData(Adv_reload);
        }
        while (1)
        {
            sleep(3600);
        }
#endif
        /* Wake once a second only until the reload went through, then sleep out the
         * period in one go (each extra wake-up costs about 2.4 uC) */
        for (t = 0; t < SENSOR_PERIOD_S && ADV_ENABLE && advLoadedId != next.packetId; t++)
        {
            sleep(1);
            BLEAppUtil_invokeFunctionNoData(Adv_reload);
        }
        if (t < SENSOR_PERIOD_S)
        {
            sleep(SENSOR_PERIOD_S - t);
        }
    }
}

void appMain(void)
{
    pthread_t thread;
    pthread_attr_t attrs;
    struct sched_param pri;

    GPIO_init();
    I2C_init();
    BatteryMonitor_init();

    pthread_attr_init(&attrs);
    pri.sched_priority = 1;
    pthread_attr_setschedparam(&attrs, &pri);
    pthread_attr_setdetachstate(&attrs, PTHREAD_CREATE_DETACHED);
    pthread_attr_setstacksize(&attrs, SENSOR_STACK_SIZE);
    if (pthread_create(&thread, &attrs, sensorThread, NULL) != 0)
    {
        while (1) {} /* out of heap at boot; nothing useful can run */
    }

    BLEAppUtil_init(&criticalErrorHandler, &App_StackInitDoneHandler,
                    &appMainParams, &appMainPeriCentParams);
}
