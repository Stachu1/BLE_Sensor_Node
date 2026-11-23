#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <nrfx.h>

#include "hwtest.h"

volatile struct hwtest_report hwtest_report;

/* Plain register watchdog: a hang in the DC/DC test turns into a reset instead of a dead board. */
static void wdt_start(void)
{
	/* runs while the CPU sleeps, pauses while a debugger halts it */
	NRF_WDT->CONFIG = WDT_CONFIG_SLEEP_Run << WDT_CONFIG_SLEEP_Pos;
	NRF_WDT->CRV = 4 * 32768; /* 4 s */
	NRF_WDT->RREN = WDT_RREN_RR0_Msk;
	NRF_WDT->TASKS_START = 1;
}

void wdt_feed(void)
{
	NRF_WDT->RR[0] = WDT_RR_RR_Reload;
}

static int (*const tests[T_COUNT])(void) = {
	[T_SOC_ID] = test_soc_id,
	[T_VDD] = test_vdd,
	[T_HFXO] = test_hfxo,
	[T_PINS] = test_pins,
	[T_I2C_SCAN] = test_i2c_scan,
	[T_HDC_ID] = test_hdc_id,
	[T_HDC_MEAS] = test_hdc_meas,
	[T_INT_DRDY] = test_int_drdy,
	[T_INT_THRESH] = test_int_thresh,
	[T_DCDC] = test_dcdc,
	[T_RADIO] = test_radio,
};

int main(void)
{
	hwtest_report.magic = 0;
	hwtest_report.version = HWTEST_VERSION;
	hwtest_report.reset_reason = NRF_POWER->RESETREAS;
	NRF_POWER->RESETREAS = 0xFFFFFFFF;

	wdt_start();
	k_msleep(500); /* time to attach RTT */

	for (int i = 0; i < T_COUNT; i++) {
		hwtest_report.status[i] = tests[i]();
		wdt_feed();
	}
	hwtest_report.magic = HWTEST_MAGIC;
	hwtest_report.done = 1;

#ifdef CONFIG_HWTEST_CARRIER
	hwtest_carrier();
#else
	hwtest_adv_update();
#endif

	/* RTT may have been attached late: repeat the report forever (the sensor is idle, so no extra load) */
	for (;;) {
		hwtest_print_report();
#ifdef CONFIG_HWTEST_CARRIER
		printk("RF carrier on: 2440.25 MHz (all-ones GFSK), 0 dBm\n");
#endif
		for (int i = 0; i < 5; i++) {
			k_msleep(1000);
			wdt_feed();
		}
	}
	return 0;
}
