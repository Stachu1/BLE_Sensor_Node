/*
 * cwtest.c - BSN-C23 continuous-wave (unmodulated carrier) RF test
 *
 * Transmits an unmodulated carrier forever, for checking harmonics and
 * spurious emissions on a spectrum analyser. There is no BLE stack: the
 * carrier is a single RCL TX_TEST command with sendCw = 1 and no stop time.
 *
 * Frequency and output power are set at build time (see makefile):
 *   make FREQ_MHZ=2440 TX_DBM=0
 *
 * The configuration is printed once on the UART (TP2, 115200 8N1). After that
 * the UART is idle, so it adds nothing to the spectrum.
 *
 * Based on the TI LPF3 SDK rfCarrierWave example (BSD-3-Clause).
 */
#include <stdint.h>

#include <ti/drivers/BatteryMonitor.h>
#include <ti/drivers/GPIO.h>
#include <ti/drivers/RCL.h>
#include <ti/drivers/rcl/RCL_Scheduler.h>
#include <ti/drivers/rcl/commands/generic.h>

#include "ti_drivers_config.h"
#include "ti_radio_config.h"

#include "bsn_board.h"
#include "bsn_log.h"

#define FW_VERSION          "cwtest 0.1.0"

#ifndef CW_FREQ_MHZ
#define CW_FREQ_MHZ         2440
#endif
#ifndef CW_TX_DBM
#define CW_TX_DBM           0  /* the BLE stack default, i.e. what ble_sensor transmits */
#endif
#ifndef CW_TX_HALF_DB
#define CW_TX_HALF_DB       0  /* 1 adds 0.5 dB */
#endif

/* Synthesizer range of the CC2340R5 */
#if CW_FREQ_MHZ < 2360 || CW_FREQ_MHZ > 2500
#error "CW_FREQ_MHZ must be within 2360..2500"
#endif

static RCL_CmdGenericTxTest cwCmd = RCL_CmdGenericTxTest_Default();
static RCL_Client rclClient;

void *mainThread(void *arg0)
{
    RCL_Handle rcl;
    RCL_Command_TxPower wanted = {.dBm = CW_TX_DBM, .fraction = CW_TX_HALF_DB};
    RCL_Command_TxPower used;
    RCL_CommandStatus st;

    (void)arg0;

    GPIO_init(); /* applies the pull-down on the HDC2010 INT line */
    BatteryMonitor_init();

    LOG_INIT(CONFIG_UART_LOG);
    LOG("\r\n\r\n==== %s-%s %s (built " __DATE__ " " __TIME__ ") ====\r\n",
        BSN_BOARD_NAME, BSN_HW_REVISION, FW_VERSION);

    RCL_init();
    rcl = RCL_open(&rclClient, &LRF_config);

    /* Round down to the nearest PA table entry, clamped to the table range */
    used = RCL_txPowerLookup(&LRF_txPowerTable, wanted, false, true);

    cwCmd.rfFrequency             = CW_FREQ_MHZ * 1000000U;
    cwCmd.txPower.rawValue        = used.rawValue;
    cwCmd.config.sendCw           = 1;
    cwCmd.config.whitenMode       = RCL_CMD_GENERIC_WH_MODE_DEFAULT;
    cwCmd.config.txWord           = 0;
    cwCmd.config.fsOff            = 1;
    cwCmd.common.scheduling       = RCL_Schedule_Now;
    cwCmd.common.status           = RCL_CommandStatus_Idle;
    cwCmd.common.timing.relHardStopTime = 0; /* never stop */

    LOG("Carrier      : %u MHz, unmodulated\r\n", (unsigned int)CW_FREQ_MHZ);
    LOG("TX power     : %d%s dBm (requested %d%s dBm)\r\n",
        used.dBm, used.fraction ? ".5" : "", CW_TX_DBM, CW_TX_HALF_DB ? ".5" : "");
    LOG("VDDS         : %u mV\r\n", BatteryMonitor_getVoltage());

    st = RCL_Command_submit(rcl, &cwCmd);
    if (st >= RCL_CommandStatus_Finished)
    {
        LOG("[FAIL] submit returned 0x%02X\r\n", st);
        while (1) {}
    }
    LOG("Transmitting. Power-cycle or reflash to stop.\r\n");

    /* Returns only if the radio aborts the command */
    st = RCL_Command_pend(&cwCmd);
    LOG("[FAIL] carrier stopped, status 0x%02X\r\n", st);
    while (1) {}
}
