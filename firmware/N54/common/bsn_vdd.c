/*
 * bsn_vdd.c - supply voltage (VDD) via the SAADC internal VDD input
 *
 * The channel is defined in bsn_n54.overlay (zephyr,user io-channels).
 */
#include "bsn_vdd.h"

#include <zephyr/drivers/adc.h>

static const struct adc_dt_spec vdd = ADC_DT_SPEC_GET_BY_IDX(DT_PATH(zephyr_user), 0);

uint16_t BsnVdd_read_mV(void)
{
    static bool ready;
    int16_t raw;
    int32_t mv;
    struct adc_sequence seq = {
        .buffer      = &raw,
        .buffer_size = sizeof(raw),
    };

    if (!ready)
    {
        if (!adc_is_ready_dt(&vdd) || adc_channel_setup_dt(&vdd) != 0)
        {
            return 0;
        }
    }
    if (adc_sequence_init_dt(&vdd, &seq) != 0)
    {
        return 0;
    }
    /* Offset-calibrate on the first read: uncalibrated, the first reading after power-on was 2162 mV at 3.0 V */
    seq.calibrate = !ready;
    ready = true;
    if (adc_read_dt(&vdd, &seq) != 0)
    {
        return 0;
    }
    mv = raw;
    if (adc_raw_to_millivolts_dt(&vdd, &mv) != 0 || mv < 0)
    {
        return 0;
    }
    return (uint16_t)mv;
}
