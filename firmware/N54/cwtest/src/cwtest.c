/*
 * cwtest.c - BSN-N54 continuous-wave (unmodulated carrier) RF test
 *
 * Transmits an unmodulated carrier forever, for checking output power,
 * frequency offset, harmonics and spurious emissions. There is no BLE stack:
 * the RADIO is ramped up into TX and left there, as in the NCS radio_test
 * sample ("start_tx_carrier").
 *
 * Frequency and output power are set at build time (see makefile):
 *   make FREQ_MHZ=2440 TX_DBM=0
 *
 * PATTERN selects what is sent:
 *   0  TXEN only: the RADIO idles in TXIDLE (the radio_test "unmodulated carrier")
 *   1  back-to-back packets of all-1 bits: a single tone at carrier + deviation
 *   2  back-to-back packets of all-0 bits: a single tone at carrier - deviation
 * The true carrier is the midpoint of the PATTERN=1 and PATTERN=2 tones, which
 * does not depend on what the RADIO sends while idle. Whitening and CRC are off;
 * only the preamble and address (40 of every 2088 bits) break the pattern.
 *
 * The configuration is printed once on the UART (TP9, 115200 8N1). After that
 * the UART is idle, so it adds nothing to the spectrum.
 */
#include <stdint.h>
#include <string.h>

#include <zephyr/drivers/clock_control.h>
#include <zephyr/drivers/clock_control/nrf_clock_control.h>
#include <zephyr/kernel.h>

#include <hal/nrf_radio.h>
#include <nrfx.h>
#if NRF_ERRATA_STATIC_CHECK(54L, 20)
#include <hal/nrf_power.h>
#endif

#include "bsn_board.h"
#include "bsn_log.h"
#include "bsn_vdd.h"

#define FW_VERSION          "cwtest 0.1.0"

#ifndef CW_FREQ_MHZ
#define CW_FREQ_MHZ         2440
#endif
#ifndef CW_PATTERN
#define CW_PATTERN          0
#endif
#ifndef CW_TX_DBM
#define CW_TX_DBM           0  /* the BLE controller default, i.e. what ble_sensor transmits */
#endif

/* RADIO.FREQUENCY covers 2360..2500 MHz (MAP = 1 below 2400 MHz) */
#if CW_FREQ_MHZ < 2360 || CW_FREQ_MHZ > 2500
#error "CW_FREQ_MHZ must be within 2360..2500"
#endif

/* nRF54L05 TXPOWER table (nrf54l05_types.h), highest first */
static const struct
{
    int8_t dBm;
    nrf_radio_txpower_t reg;
} txTable[] =
{
    {  8, RADIO_TXPOWER_TXPOWER_Pos8dBm },
    {  7, RADIO_TXPOWER_TXPOWER_Pos7dBm },
    {  6, RADIO_TXPOWER_TXPOWER_Pos6dBm },
    {  5, RADIO_TXPOWER_TXPOWER_Pos5dBm },
    {  4, RADIO_TXPOWER_TXPOWER_Pos4dBm },
    {  3, RADIO_TXPOWER_TXPOWER_Pos3dBm },
    {  2, RADIO_TXPOWER_TXPOWER_Pos2dBm },
    {  1, RADIO_TXPOWER_TXPOWER_Pos1dBm },
    {  0, RADIO_TXPOWER_TXPOWER_0dBm },
    { -1, RADIO_TXPOWER_TXPOWER_Neg1dBm },
    { -2, RADIO_TXPOWER_TXPOWER_Neg2dBm },
    { -3, RADIO_TXPOWER_TXPOWER_Neg3dBm },
    { -4, RADIO_TXPOWER_TXPOWER_Neg4dBm },
    { -5, RADIO_TXPOWER_TXPOWER_Neg5dBm },
    { -6, RADIO_TXPOWER_TXPOWER_Neg6dBm },
    { -7, RADIO_TXPOWER_TXPOWER_Neg7dBm },
    { -8, RADIO_TXPOWER_TXPOWER_Neg8dBm },
    { -9, RADIO_TXPOWER_TXPOWER_Neg9dBm },
    {-10, RADIO_TXPOWER_TXPOWER_Neg10dBm },
    {-12, RADIO_TXPOWER_TXPOWER_Neg12dBm },
    {-14, RADIO_TXPOWER_TXPOWER_Neg14dBm },
    {-16, RADIO_TXPOWER_TXPOWER_Neg16dBm },
    {-18, RADIO_TXPOWER_TXPOWER_Neg18dBm },
    {-20, RADIO_TXPOWER_TXPOWER_Neg20dBm },
    {-28, RADIO_TXPOWER_TXPOWER_Neg28dBm },
    {-40, RADIO_TXPOWER_TXPOWER_Neg40dBm },
};

/* Round down to the nearest table entry, clamped to the table range */
static unsigned int txLookup(int dBm)
{
    unsigned int i;

    for (i = 0; i < ARRAY_SIZE(txTable) - 1; i++)
    {
        if (txTable[i].dBm <= dBm)
        {
            break;
        }
    }
    return i;
}

#if CW_PATTERN != 0
/* Static-length payload, no LENGTH field: every on-air payload bit is the fill bit */
#define PKT_LEN             255
static uint8_t pkt[PKT_LEN];

static void patternSetup(uint8_t fill)
{
    nrf_radio_packet_conf_t conf = {
        .lflen   = 0,
        .s0len   = 0,
        .s1len   = 0,
        .maxlen  = PKT_LEN,
        .statlen = PKT_LEN,
        .balen   = 4,
        .big_endian = true,
        .whiteen = false,
    };

    memset(pkt, fill, sizeof(pkt));
    nrf_radio_packet_configure(NRF_RADIO, &conf);
    nrf_radio_crc_configure(NRF_RADIO, RADIO_CRCCNF_LEN_Disabled, NRF_RADIO_CRC_ADDR_INCLUDE, 0);
    /* The address bits follow the same pattern as the payload */
    nrf_radio_prefix0_set(NRF_RADIO, fill);
    nrf_radio_base0_set(NRF_RADIO, fill ? 0xFFFFFFFFUL : 0UL);
    nrf_radio_txaddress_set(NRF_RADIO, 0);
    nrf_radio_packetptr_set(NRF_RADIO, pkt);
    nrf_radio_shorts_set(NRF_RADIO, NRF_RADIO_SHORT_READY_START_MASK | NRF_RADIO_SHORT_END_START_MASK);
}
#endif

/* HFXO on and tuned; the RADIO needs it for an accurate carrier */
static int hfxoStart(void)
{
    struct onoff_manager *mgr = z_nrf_clock_control_get_onoff(CLOCK_CONTROL_NRF_SUBSYS_HF);
    struct onoff_client cli;
    int err, res;

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
    } while (err == -EAGAIN);
    if (err == 0 && res != 0)
    {
        return res;
    }

#if NRF_ERRATA_STATIC_CHECK(54L, 20)
    /* Same as radio_test: constant latency mode for the radio on affected revisions */
    if (NRF_ERRATA_DYNAMIC_CHECK(54L, 20))
    {
        nrf_power_task_trigger(NRF_POWER, NRF_POWER_TASK_CONSTLAT);
    }
#endif
    return 0;
}

int main(void)
{
    unsigned int tx = txLookup(CW_TX_DBM);
    int err;

    LOG("\r\n\r\n==== %s-%s %s (built " __DATE__ " " __TIME__ ") ====\r\n",
        BSN_BOARD_NAME, BSN_HW_REVISION, FW_VERSION);

    err = hfxoStart();
    if (err != 0)
    {
        LOG("[FAIL] HFXO start: %d\r\n", err);
        return 0;
    }

    /* Same register sequence as radio_test's radio_unmodulated_tx_carrier() */
    nrf_radio_shorts_set(NRF_RADIO, 0);
    nrf_radio_int_disable(NRF_RADIO, ~0U);
    nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_DISABLED);
    nrf_radio_task_trigger(NRF_RADIO, NRF_RADIO_TASK_DISABLE);
    while (!nrf_radio_event_check(NRF_RADIO, NRF_RADIO_EVENT_DISABLED))
    {
    }
    nrf_radio_event_clear(NRF_RADIO, NRF_RADIO_EVENT_DISABLED);

    nrf_radio_mode_set(NRF_RADIO, NRF_RADIO_MODE_BLE_1MBIT);
    nrf_radio_txpower_set(NRF_RADIO, txTable[tx].reg);
    nrf_radio_frequency_set(NRF_RADIO, CW_FREQ_MHZ);

#if CW_PATTERN == 1
    patternSetup(0xFF);
    LOG("Carrier      : %u MHz, PATTERN=1 all-1 packets (tone at carrier + deviation)\r\n",
        (unsigned int)CW_FREQ_MHZ);
#elif CW_PATTERN == 2
    patternSetup(0x00);
    LOG("Carrier      : %u MHz, PATTERN=2 all-0 packets (tone at carrier - deviation)\r\n",
        (unsigned int)CW_FREQ_MHZ);
#else
    LOG("Carrier      : %u MHz, PATTERN=0 TXIDLE\r\n", (unsigned int)CW_FREQ_MHZ);
#endif
    LOG("TX power     : %d dBm (requested %d dBm), TXPOWER 0x%03X\r\n",
        txTable[tx].dBm, CW_TX_DBM, (unsigned int)txTable[tx].reg);
    LOG("VDD          : %u mV\r\n", BsnVdd_read_mV());

    /* PATTERN=0: TXEN without START, the RADIO sits in TXIDLE after ramp-up.
     * PATTERN=1/2: the READY->START and END->START shorts send packets back to back. */
    nrf_radio_task_trigger(NRF_RADIO, NRF_RADIO_TASK_TXEN);
    LOG("Transmitting. Power-cycle or reflash to stop.\r\n");

    /* The HFXO request is never released, so the carrier runs forever */
    while (1)
    {
        k_sleep(K_FOREVER);
    }
    return 0;
}
